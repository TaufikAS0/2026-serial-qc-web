"""Per-user hidden Windows supervisor. No serial connections restored."""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
RUN_NAME = 'SerialProtocolTestWeb'


def configuration_id(directory, port):
    import hashlib
    return hashlib.sha256(f'{str(directory.resolve()).lower()}:{port}'.encode()).hexdigest()[:16]


def data_dir():
    return Path(os.environ.get('SERIALWEB_DATA', Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'SerialProtocolTestWeb'))


class InstanceLock:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(path, 'a+b')
        if path.stat().st_size == 0:
            self.file.write(b'0')
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('Instance layanan sudah aktif')

    def close(self):
        self.file.close()


def logger(directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(directory / f'{name}.log', maxBytes=1000000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    result = logging.getLogger(name)
    result.setLevel(logging.INFO)
    result.addHandler(handler)
    return result


def arguments(directory, port):
    return ['-m', 'serialweb.lifecycle', 'supervise', '--data', str(directory), '--port', str(port)]


def autostart(enable, directory, port):
    if os.name != 'nt':
        raise ValueError('Autostart hanya Windows')
    import winreg
    executable = Path(sys.executable).with_name('pythonw.exe')
    # Absolute script bootstrap ensures working directory is irrelevant at login.
    command = subprocess.list2cmdline([str(executable), str(ROOT / 'launcher.py'), 'supervise', '--data', str(directory), '--port', str(port)])
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enable:
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, RUN_NAME)
            except FileNotFoundError:
                pass


def status(directory, port):
    from .network import load_network
    network = load_network(directory)
    active = False
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=1) as reply:
            health = json.load(reply)
            active = health.get('app') == 'serial-protocol-web' and health.get('configuration') == configuration_id(directory, port)
    except Exception:
        pass
    installed = False
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                installed = bool(winreg.QueryValueEx(key, RUN_NAME)[0])
        except FileNotFoundError:
            pass
    pid_path = directory / 'supervisor.json'
    supervisor = json.loads(pid_path.read_text()) if pid_path.exists() else None
    return dict(active=active, autostart=installed, supervisor=supervisor, data_directory=str(directory), url=f'http://127.0.0.1:{port}', lan_url=f"http://{network['host']}:{port}/" if network else None, lan_subnet=network['subnet'] if network else None, retention='200 runs / 64 MB; 1 MB and 500 detailed steps/run; 1000 log events; rotated logs 8 MB total; SQLite ceiling 128 MiB', sleep='Sleep/shutdown menghentikan komunikasi; reconnect dan start manual setelah wake')


def supervise(directory, port):
    lock = InstanceLock(directory / 'supervisor.lock')
    log = logger(directory, 'supervisor')
    marker = directory / 'stop.request'
    marker.unlink(missing_ok=True)
    pid_path = directory / 'supervisor.json'
    pid_path.write_text(json.dumps(dict(pid=os.getpid(), port=port, started=time.time())))
    child = None
    try:
        attempts = 0
        while not marker.exists():
            started = time.monotonic()
            child = subprocess.Popen([sys.executable, '-m', 'serialweb.lifecycle', 'serve', '--data', str(directory), '--port', str(port)], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            log.info('Backend start pid=%s', child.pid)
            while child.poll() is None and not marker.exists():
                time.sleep(.25)
            if marker.exists():
                break
            runtime = time.monotonic() - started
            attempts = 0 if runtime > 60 else attempts + 1
            delay = min(60, 2 ** min(attempts, 6))
            log.warning('Backend exit=%s; retry in %ss; serial remains disconnected', child.returncode, delay)
            for _ in range(delay * 4):
                if marker.exists():
                    break
                time.sleep(.25)
    finally:
        if child and child.poll() is None:
            # Backend sees stop.request, closes port and reconciles its run first.
            try:
                child.wait(4)
            except subprocess.TimeoutExpired:
                child.terminate()
                child.wait(3)
        pid_path.unlink(missing_ok=True)
        lock.close()
        log.info('Supervisor stopped')


def serve(directory, port):
    lock = InstanceLock(directory / 'backend.lock')
    log = logger(directory, 'backend')
    try:
        from .app import create_app
        from waitress import create_server
        import threading
        from .network import load_network
        network = load_network(directory)
        app = create_app(directory, port, network)
        app.logger.handlers = log.handlers
        host = '0.0.0.0' if network else '127.0.0.1'
        server = create_server(app, host=host, port=port, threads=6, max_request_body_size=250000, connection_limit=50)
        log.info('Listening %s:%s; LAN=%s; disconnected', host, port, bool(network))
        def stop_watch():
            while not (directory / 'stop.request').exists():
                time.sleep(.2)
            app.engine.disconnect()
            server.close()
        threading.Thread(target=stop_watch, daemon=True).start()
        server.run()
    except Exception:
        log.exception('Backend failed (port collision/config)')
        raise
    finally:
        lock.close()


def start(directory, port):
    if status(directory, port)['active']:
        return
    executable = Path(sys.executable).with_name('pythonw.exe') if os.name == 'nt' else Path(sys.executable)
    subprocess.Popen([str(executable), str(ROOT / 'launcher.py'), 'supervise', '--data', str(directory), '--port', str(port)], cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if status(directory, port)['active']:
            return
        time.sleep(.25)
    raise RuntimeError('Backend tidak sehat setelah 10s; lihat backend.log/supervisor.log (termasuk collision 8770)')


def stop(directory, port):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'stop.request').touch()
    for _ in range(40):
        if not (directory / 'supervisor.json').exists() and not status(directory, port)['active']:
            return
        time.sleep(.25)
    raise RuntimeError('Stop belum selesai; periksa status/log')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status', 'open', 'install-autostart', 'uninstall-autostart', 'disable-autostart', 'supervise', 'serve', 'enable-lan', 'disable-lan'])
    parser.add_argument('--lan-host')
    parser.add_argument('--lan-subnet')
    parser.add_argument('--data', type=Path, default=data_dir())
    parser.add_argument('--port', type=int, default=8770)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Port harus 1024..65535')
    directory = args.data.resolve()
    if args.action == 'enable-lan':
        from .network import save_network
        if not args.lan_host or not args.lan_subnet:
            parser.error('enable-lan memerlukan --lan-host IPv4 --lan-subnet CIDR')
        save_network(directory, args.lan_host, args.lan_subnet)
        stop(directory, args.port)
        start(directory, args.port)
        print(json.dumps(status(directory, args.port), indent=2))
    elif args.action == 'disable-lan':
        (directory / 'network.json').unlink(missing_ok=True)
        stop(directory, args.port)
        start(directory, args.port)
    elif args.action == 'serve':
        serve(directory, args.port)
    elif args.action == 'supervise':
        supervise(directory, args.port)
    elif args.action == 'start':
        start(directory, args.port)
    elif args.action == 'stop':
        stop(directory, args.port)
    elif args.action == 'restart':
        stop(directory, args.port)
        start(directory, args.port)
    elif args.action == 'open':
        start(directory, args.port)
        webbrowser.open(f'http://127.0.0.1:{args.port}')
    elif args.action == 'status':
        print(json.dumps(status(directory, args.port), indent=2))
    else:
        autostart(args.action == 'install-autostart', directory, args.port)


if __name__ == '__main__':
    main()
