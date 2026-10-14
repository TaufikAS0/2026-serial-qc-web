import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import serial
from unittest.mock import patch
from serialweb.protocol import *
from serialweb.profiles import validate, assert_result
from serialweb.store import Store, export_csv
from serialweb.engine import Engine
from serialweb.app import create_app
from serialweb.lifecycle import InstanceLock

ROOT = Path(__file__).resolve().parent.parent


def profile(name='raw-ping'):
    return json.loads((ROOT / 'examples' / f'{name}.json').read_text(encoding='utf-8'))


class CodecTests(unittest.TestCase):
    def test_official_crc_vector(self):
        # Fixed read regression vector; algorithm defined by serial guide Appendix B.
        self.assertEqual(request(1, 3, 0, 10).hex(), '01030000000ac5cd')
        # Official serial guide Appendix B pp.40-41: 02 07 -> CRC bytes 41 12.
        self.assertEqual(crc(bytes.fromhex('0207')).hex(),'4112')

    def test_read_golden(self):
        data = frame(bytes.fromhex('0103041234abcd'))
        self.assertEqual(response(data, 1, 3, 2), [0x1234, 0xabcd])

    def test_coils_lsb(self):
        self.assertEqual(response(frame(bytes.fromhex('010102cd01')), 1, 1, 10), [True,False,True,True,False,False,True,True,True,False])

    def test_padding_bits_and_integer_input(self):
        with self.assertRaises(ValueError):response(frame(bytes.fromhex('01010180')),1,1,1)
        with self.assertRaises(ValueError):request(True,3,0,1)

    def test_limits(self):
        for args in [(0,3,0,1),(248,3,0,1),(1,5,0,1),(1,3,0,126),(1,1,0,2001),(1,3,65535,2),(1,3,0,0)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                request(*args)

    def test_crc_rejected(self):
        with self.assertRaisesRegex(ValueError,'CRC'):
            checked(bytes.fromhex('01030200000000'))

    def test_exception(self):
        with self.assertRaisesRegex(ValueError,'exception 2'):
            response(frame(bytes([1,0x83,2])),1,3,1)

    def test_wrong_unit_fc_length(self):
        for body in [bytes.fromhex('0203020001'),bytes.fromhex('0104020001'),bytes.fromhex('0103040001')]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                response(frame(body),1,3,1)

    def test_endian_signed_float(self):
        self.assertEqual(decode([0xffff],{'type':'int16'}),-1)
        self.assertEqual(decode([0x1234,0x5678],{'type':'uint32'}),0x12345678)
        self.assertEqual(decode([0x5678,0x1234],{'type':'uint32','word_order':'little'}),0x12345678)
        self.assertEqual(decode([0x3412],{'type':'uint16','byte_order':'little'}),0x1234)
        self.assertEqual(decode([0x3f80,0],{'type':'float32','scale':2,'offset':1}),3)

    def test_nan_rejected(self):
        with self.assertRaises(ValueError): decode([0x7fc0,0],{'type':'float32'})

    def test_slave_reads_exceptions_broadcast(self):
        maps={str(f): {'0':1,'1':0} for f in range(1,5)}
        for fc in range(1,5):
            actual=slave_response(request(1,fc,0,2),1,maps)
            self.assertEqual(response(actual,1,fc,2),[True,False] if fc<3 else [1,0])
        self.assertEqual(checked(slave_response(request(1,3,2,1),1,maps)),bytes([1,0x83,2]))
        self.assertEqual(checked(slave_response(frame(bytes.fromhex('010300000000')),1,maps)),bytes([1,0x83,3]))
        self.assertEqual(checked(slave_response(frame(bytes.fromhex('010600000001')),1,maps)),bytes([1,0x86,1]))
        self.assertEqual(slave_response(frame(bytes.fromhex('000300000001')),1,maps),b'')

    def test_raw_encoding(self):
        self.assertEqual(raw_bytes(dict(format='HEX',payload='00 FF',ending='CRLF')),b'\0\xff\r\n')
        with self.assertRaises(ValueError):raw_bytes(dict(format='HEX',payload='ZZ'))

    def test_profile_validation(self):
        validate(profile())
        for mutate in [lambda p:p.update(version=2),lambda p:p.update(repeats=0),lambda p:p['steps'][0].update(assertions=[]),lambda p:p['steps'][0].update(timeout=0),lambda p:p['steps'][0].update(assertions=[{'kind':'script'}])]:
            p=profile();mutate(p)
            with self.assertRaises(ValueError):validate(p)

    def test_assertions(self):
        assert_result(b'ABC',10,[{'kind':'exact','hex':'414243'},{'kind':'prefix','hex':'41'},{'kind':'contains','hex':'42'},{'kind':'length','value':3},{'kind':'range','min':9,'max':11},{'kind':'tolerance','target':10,'tolerance':0}])
        with self.assertRaises(ValueError):assert_result(b'A',None,[{'kind':'exact','hex':'42'}])


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name));self.e=Engine(self.store);self.e.connect({'fixture':'MOCK'})
    def tearDown(self):
        self.e.disconnect();self.store.db.close();self.tmp.cleanup()
    def done(self):
        self.e.worker.join(5)
        self.assertFalse(self.e.worker.is_alive())
        return self.e.state()['active']
    def test_raw_pass(self):
        self.e.run(profile());result=self.done();self.assertEqual(result['status'],'PASS');self.assertEqual(result['fixture'],'MOCK');self.assertEqual(result['completed'],3)
    def test_modbus_pass(self):
        self.e.run(profile('modbus-read'));self.assertEqual(self.done()['status'],'PASS')
    def test_faults_fail(self):
        for fault in ('corrupt','echo','timeout'):
            self.e.mock_fault=fault;p=profile();p['repeats']=1;p['steps'][0]['timeout']=.05
            self.e.run(p);self.assertEqual(self.done()['status'],'FAIL')
    def test_double_start_conflicts(self):
        self.e.periodic({'payload':'PING','interval':1})
        for fn in [lambda:self.e.run(profile()),lambda:self.e.terminal({'payload':'x'}),lambda:self.e.master({'tags':profile('modbus-read')['steps']}),lambda:self.e.start_slave()]:
            with self.assertRaises(ValueError):fn()
        self.e.stop();self.assertIsNone(self.e.owner)
    def test_cancel(self):
        self.e.mock_fault='timeout';self.e.run(profile());time.sleep(.02);self.e.stop();self.assertEqual(self.done()['status'],'INCOMPLETE')
    def test_disconnect_incomplete(self):
        self.e.mock_fault='timeout';self.e.run(profile());self.e.disconnect();self.assertEqual(self.done()['status'],'INCOMPLETE')
    def test_fixture_mismatch(self):
        p=profile();p['fixture']='REAL'
        with self.assertRaises(ValueError):self.e.run(p)
    def test_serial_settings_mismatch(self):
        p=profile();p['serial']['baud']=19200
        with self.assertRaises(ValueError):self.e.run(p)
    def test_bounded_logs(self):
        for _ in range(1100):self.e.log('RX',b'x')
        self.assertEqual(len(self.e.events),1000);self.assertGreaterEqual(self.e.dropped,100)
    def test_master_values(self):
        self.e.master({'tags':profile('modbus-read')['steps'],'poll':False});self.e.worker.join(2)
        self.assertEqual(self.e.tags[0]['value'],100)
    def test_slave_stream_partial_combined(self):
        self.e.start_slave();a=request(1,3,0,1);b=request(1,4,1,1)
        self.e._receive(a[:3]);time.sleep(.001);self.e._receive(a[3:]+b);time.sleep(.1);self.e.stop()
        tx=[v for v in self.e.events if v['direction']=='TX'];self.assertEqual(len(tx),2)
        self.assertEqual(response(bytes.fromhex(tx[0]['hex']),1,3,1),[100])
    def test_partial_response(self):
        self.e._claim('scenario')
        with patch.object(self.e,'_send') as send:
            answer=frame(bytes.fromhex('0103020064'))
            def deliver():
                self.e._receive(answer[:2]);time.sleep(.01);self.e._receive(answer[2:])
            send.side_effect=lambda _:threading.Thread(target=deliver).start()
            received,_=self.e._exchange(request(1,3,0,1),{'timeout':1},True)
            self.assertEqual(received,answer)
        self.e.owner=None
    def test_noise_not_pass(self):
        self.e._claim('scenario')
        with patch.object(self.e,'_send',side_effect=lambda _:self.e._receive(b'noise'+frame(bytes.fromhex('0103020064')))):
            with self.assertRaises(ValueError):self.e._exchange(request(1,3,0,1),{'timeout':.05},True)
        self.e.owner=None
    def test_stale_cleared(self):
        self.e._receive(b'PONG\r\n');self.e.mock_fault='timeout';p=profile();p['repeats']=1;p['steps'][0]['timeout']=.05
        self.e.run(p);self.assertEqual(self.done()['status'],'FAIL')
    def test_reconnect_reader(self):
        old=self.e.reader;self.e.disconnect();self.e.connect({'fixture':'MOCK'});self.assertFalse(old.is_alive());self.assertTrue(self.e.reader.is_alive())
    def test_busy_real_port(self):
        self.e.disconnect()
        with patch('serialweb.engine.ports',return_value=[{'port':'COM99'}]), patch('serialweb.engine.serial.Serial',side_effect=serial.SerialException('busy')):
            with self.assertRaises(serial.SerialException):self.e.connect({'fixture':'REAL','port':'COM99'})
        self.assertFalse(self.e.connected)
    def test_unplug_closes(self):
        class Missing:
            in_waiting=1
            def read(self,_):raise serial.SerialException('USB unplug')
            def close(self):pass
        import serial
        self.e.handle=Missing()
        self.e.reader.join(1)
        self.assertFalse(self.e.connected);self.assertIn('USB unplug',self.e.error)
    def test_resume_requires_reconnect(self):
        self.e.reader_stop.set();self.e.reader.join(1);self.e.reader_stop=threading.Event()
        with patch('serialweb.engine.time.monotonic',side_effect=[0,10]):self.e._reader()
        self.assertFalse(self.e.connected);self.assertIn('sleep',self.e.error)
    def test_no_send_before_reader_after_resume(self):
        self.e.reader_stop.set();self.e.reader.join(1);self.e.last_reader_tick=time.monotonic()-10
        self.e._claim('periodic')
        with self.assertRaises(InterruptedError):self.e._send(b'COMMAND')
        self.assertEqual(self.e.tx_count,0);self.e.owner=None


class PersistenceApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.app=create_app(Path(self.tmp.name));self.client=self.app.test_client();self.base='http://127.0.0.1:8770';self.token=self.get('/api/session').json['token']
    def tearDown(self):
        self.app.engine.disconnect();self.app.engine.store.db.close();self.tmp.cleanup()
    def get(self,path,**kw):return self.client.get(path,base_url=self.base,**kw)
    def post(self,action,body):return self.client.post('/api/action/'+action,base_url=self.base,json=body,headers={'X-Serial-Token':self.token})
    def test_host_origin_csrf(self):
        self.assertEqual(self.client.get('/api/state',base_url='http://evil.test:8770').status_code,403)
        self.assertEqual(self.get('/api/state',headers={'Origin':'http://evil.test'}).status_code,403)
        self.assertEqual(self.client.post('/api/action/connect',base_url=self.base,json={'fixture':'MOCK'}).status_code,403)
    def test_xss_csp_assets(self):
        page=self.get('/');self.assertEqual(page.status_code,200);self.assertIn("frame-ancestors 'none'",page.headers['Content-Security-Policy']);asset=self.get('/static/app.js');self.assertEqual(asset.status_code,200);asset.close();page.close()
    def test_full_api_report(self):
        self.assertEqual(self.post('connect',{'fixture':'MOCK'}).status_code,200)
        self.assertEqual(self.post('run',{'profile':profile(),'identity':'=HYPERLINK("x")'}).status_code,200)
        self.app.engine.worker.join(3)
        run=self.app.engine.active;csv=self.get('/api/export/'+run['id']+'/csv').data.decode('utf-8-sig')
        self.assertIn("'=HYPERLINK",csv.replace('""','"'));self.assertIn('MOCK',csv)
        self.assertEqual(self.get('/api/export/'+run['id']+'/json').json['status'],'PASS')
        self.assertEqual(len(self.get('/api/history').json),1)
    def test_restart_reconciles(self):
        self.post('connect',{'fixture':'MOCK'});self.app.engine.mock_fault='timeout';self.post('run',{'profile':profile()})
        other=Store(Path(self.tmp.name));self.assertEqual(other.history()[0]['status'],'INCOMPLETE');other.db.close();self.app.engine.stop()
    def test_retention_and_lock(self):
        self.post('connect',{'fixture':'MOCK'});self.post('run',{'profile':profile()});self.app.engine.worker.join(3)
        run=self.app.engine.active
        for index in range(205):
            sample=copy.deepcopy(run);sample['id']=str(index);self.app.engine.store.save(sample)
        self.assertEqual(len(self.app.engine.store.history()),200)
        path=Path(self.tmp.name)/'test.lock';a=InstanceLock(path)
        with self.assertRaises(RuntimeError):InstanceLock(path)
        a.close();b=InstanceLock(path);b.close()
    def test_invalid_profile_api(self):
        self.assertEqual(self.post('profile',{'version':1}).status_code,400)
    def test_mock_injection_guard_and_slave(self):
        self.assertEqual(self.post('mock-inject',{'hex':'010300000001840a'}).status_code,400)
        self.post('connect',{'fixture':'MOCK'});self.post('slave-start',{})
        self.assertEqual(self.post('mock-inject',{'hex':'010300000001840a'}).status_code,200)
        time.sleep(.05);self.app.engine.stop()
        self.assertTrue(any(e['direction']=='TX' for e in self.app.engine.events))
    def test_profile_unknown_columns(self):
        p=profile();p['script']='something'
        self.assertEqual(self.post('profile',p).status_code,400)
    def test_invalid_setup_does_not_connect(self):
        self.assertEqual(self.post('connect',{'fixture':'REAL','port':'COM_NONEXISTENT'}).status_code,400)
        self.assertFalse(self.app.engine.connected)
    def test_profile_map_roundtrip(self):
        p=profile();p['name']='custom';self.post('profile',p);self.assertIn('custom',[p['name'] for p in self.get('/api/profiles').json])
        maps=self.app.engine.slave;maps['maps']['3']['99']=123;self.assertEqual(self.post('slave-config',maps).status_code,200);self.assertEqual(self.app.engine.store.setting('slave')['maps']['3']['99'],123)


if __name__ == '__main__':unittest.main()
