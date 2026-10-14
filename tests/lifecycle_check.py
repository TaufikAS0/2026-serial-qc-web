"""Actual Windows lifecycle integration, isolated temporary data/port; no COM."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from serialweb.lifecycle import ROOT, InstanceLock


def check():
    assert os.name == 'nt', 'Windows-only integration'
    port = 18770
    tmp = tempfile.TemporaryDirectory(prefix='serialweb-lifecycle-')
    directory = Path(tmp.name)
    base = f'http://127.0.0.1:{port}'
    def cli(action):
        return subprocess.run([sys.executable, str(ROOT/'launcher.py'), action, '--data', str(directory), '--port', str(port)], cwd=ROOT, capture_output=True, text=True, timeout=25, check=True)
    def get(path):
        with urllib.request.urlopen(base + path, timeout=2) as r:return json.load(r)
    def post(action, body):
        token = get('/api/session')['token']
        req=urllib.request.Request(base+'/api/action/'+action, json.dumps(body).encode(), headers={'Content-Type':'application/json','X-Serial-Token':token})
        with urllib.request.urlopen(req,timeout=3) as r:return json.load(r)
    def wait(predicate, seconds=15):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            try:
                if predicate():return
            except Exception:pass
            time.sleep(.1)
        raise AssertionError('Lifecycle wait timed out')
    evidence=[]
    try:
        cli('start');assert get('/api/health')['status']=='ok';evidence.append('start: health OK')
        pid=json.loads((directory/'supervisor.json').read_text())['pid']
        cli('start');assert json.loads((directory/'supervisor.json').read_text())['pid']==pid;evidence.append('double start: same supervisor')
        post('connect',{'fixture':'MOCK'})
        post('mock-fault',{'fault':'timeout'})
        profile=json.loads((ROOT/'examples/raw-ping.json').read_text(encoding='utf-8'));profile['repeats']=100
        post('run',{'profile':profile})
        wait(lambda:get('/api/state')['active'] is not None)
        # Kill only the backend child of this isolated supervisor, never arbitrary processes.
        command=f"Get-CimInstance Win32_Process -Filter 'ParentProcessId = {pid}' | Where-Object {{$_.CommandLine -like '*serialweb.lifecycle*serve*'}} | Select-Object -ExpandProperty ProcessId"
        result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,check=True)
        child_pids=[int(x.strip()) for x in result.stdout.splitlines() if x.strip().isdigit()]
        assert len(child_pids)==1, result.stdout
        subprocess.run(['taskkill','/PID',str(child_pids[0]),'/F'],capture_output=True,check=True)
        wait(lambda:get('/api/state')['connected'] is False and get('/api/history')[0]['status']=='INCOMPLETE')
        assert get('/api/state')['tx_bytes']==0;evidence.append('forced backend crash: restarted; disconnected; zero TX; run INCOMPLETE')
        cli('restart');assert get('/api/state')['connected'] is False;evidence.append('restart: healthy/disconnected')
        # Backend singleton independent of supervisor.
        second=subprocess.run([sys.executable,str(ROOT/'launcher.py'),'serve','--data',str(directory),'--port',str(port)],cwd=ROOT,capture_output=True,timeout=5)
        assert second.returncode!=0;evidence.append('duplicate backend: blocked')
        cli('stop');assert not (directory/'supervisor.json').exists();evidence.append('stop: supervisor exited')
        cli('stop');evidence.append('stop idempotent')
        cli('start');assert get('/api/state')['connected'] is False;evidence.append('start after stop: no auto send')
        return evidence
    finally:
        cli('stop')
        tmp.cleanup()


if __name__=='__main__':
    print(json.dumps(check(),indent=2))
