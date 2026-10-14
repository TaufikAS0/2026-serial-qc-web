"""Bounded mock terminal soak with RSS/SQLite/log measurements. No hardware."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import tempfile
import time
from serialweb.engine import Engine
from serialweb.store import Store


def rss():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    process = ctypes.windll.kernel32.GetCurrentProcess
    process.restype = ctypes.c_void_p
    memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
    memory_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    memory_info.restype = ctypes.c_int
    if not memory_info(process(),ctypes.byref(counters),counters.cb):
        raise ctypes.WinError()
    return counters.WorkingSetSize


def run(seconds):
    tmp=tempfile.TemporaryDirectory();store=Store(Path(tmp.name));engine=Engine(store);engine.connect({'fixture':'MOCK'})
    engine.periodic({'payload':'PING','ending':'CRLF','interval':.05})
    started=time.monotonic();samples=[]
    try:
        while time.monotonic()-started<seconds:
            samples.append({'seconds':round(time.monotonic()-started,1),'rss_bytes':rss(),'events':len(engine.events)})
            time.sleep(max(0,min(5,seconds-(time.monotonic()-started))))
        engine.stop();state=engine.state()
        result={'label':'SIMULASI; NOT HARDWARE ACCEPTANCE','duration_seconds':round(time.monotonic()-started,2),'tx_bytes':state['tx_bytes'],'rx_bytes':state['rx_bytes'],'events':len(engine.events),'dropped':state['dropped'],'rss_start':samples[0]['rss_bytes'],'rss_end':rss(),'rss_peak_samples':max(s['rss_bytes'] for s in samples),'disk_bytes':sum(p.stat().st_size for p in Path(tmp.name).iterdir() if p.is_file()),'samples':samples}
        assert len(engine.events)<=1000 and engine.owner is None
        return result
    finally:
        engine.disconnect();store.db.close();tmp.cleanup()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=120);args=parser.parse_args();print(json.dumps(run(args.seconds),indent=2))
