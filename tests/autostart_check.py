"""Verify installed main per-user Run command without logging out or rebooting."""
import json
import subprocess
import sys
import time
import winreg
from serialweb.lifecycle import ROOT, RUN_NAME, data_dir, status, autostart


def check():
    directory=data_dir().resolve();port=8770
    autostart(True,directory,port)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        command=winreg.QueryValueEx(key,RUN_NAME)[0]
    autostart(True,directory,port)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        assert winreg.QueryValueEx(key,RUN_NAME)[0]==command
    autostart(False,directory,port);autostart(False,directory,port)
    assert not status(directory,port)['autostart']
    autostart(True,directory,port)
    subprocess.run([sys.executable,str(ROOT/'launcher.py'),'stop'],cwd=ROOT,check=True,timeout=25)
    # Windows CreateProcess receives the exact installed Run value, no shell.
    subprocess.Popen(command,cwd=str(directory),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        if status(directory,port)['active']:
            return {'installed':True,'idempotent_install_uninstall':True,'registry_command_execution':'health OK from unrelated working directory','real_login_reboot':'PENDING; not performed','power_settings_changed':False}
        time.sleep(.25)
    raise AssertionError('Installed Run command did not start healthy backend')


if __name__=='__main__':print(json.dumps(check(),indent=2))
