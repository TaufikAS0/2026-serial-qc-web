import tempfile
import unittest
from pathlib import Path
from serialweb.app import create_app
from serialweb.network import validate_network, allowed_peer, save_network, load_network


class LanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.network = validate_network('192.168.1.122', '192.168.1.0/24')
        self.app = create_app(Path(self.tmp.name), network=self.network)
        self.client = self.app.test_client()
        self.base = 'http://192.168.1.122:8770'
        self.env = {'REMOTE_ADDR': '192.168.1.88'}
    def tearDown(self):
        self.app.engine.disconnect(); self.app.engine.store.db.close(); self.tmp.cleanup()
    def get(self, path, **kw):
        return self.client.get(path, base_url=self.base, environ_overrides=self.env, **kw)
    def test_lan_page_session_and_mock_control(self):
        page = self.get('/'); self.assertEqual(page.status_code,200); page.close()
        token = self.get('/api/session').json['token']
        result = self.client.post('/api/action/connect',base_url=self.base,environ_overrides=self.env,json={'fixture':'MOCK'},headers={'X-Serial-Token':token,'Origin':self.base})
        self.assertEqual(result.status_code,200)
        self.assertTrue(self.app.engine.connected)
    def test_cross_origin_still_denied(self):
        self.assertEqual(self.get('/api/state',headers={'Origin':'http://evil.test'}).status_code,403)
        self.assertEqual(self.get('/api/state',headers={'Host':'evil.test:8770'}).status_code,403)
    def test_wrong_network_denied(self):
        self.env={'REMOTE_ADDR':'192.168.2.10'}
        self.assertEqual(self.get('/api/state').status_code,403)
    def test_lan_cannot_stop_windows_service(self):
        token=self.get('/api/session').json['token']
        result=self.client.post('/api/action/service-stop',base_url=self.base,environ_overrides=self.env,json={},headers={'X-Serial-Token':token})
        self.assertEqual(result.status_code,403)
    def test_private_address_validation(self):
        for host,subnet in [('0.0.0.0','0.0.0.0/0'),('8.8.8.8','8.8.8.0/24'),('192.168.1.2','192.168.2.0/24')]:
            with self.assertRaises(ValueError):validate_network(host,subnet)
    def test_config_round_trip(self):
        path=Path(self.tmp.name);self.assertIsNone(load_network(path));save_network(path,'192.168.1.122','192.168.1.0/24');self.assertEqual(load_network(path),self.network)
        self.assertTrue(allowed_peer('127.0.0.1',None));self.assertFalse(allowed_peer('192.168.1.88',None))
