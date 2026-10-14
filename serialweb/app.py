import io
import json
import secrets
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from .engine import Engine, ports
from .profiles import validate
from .store import Store, export_csv


def create_app(directory, port=8770, network=None):
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config['MAX_CONTENT_LENGTH'] = 250000
    store = Store(Path(directory))
    engine = Engine(store)
    saved = store.setting('slave')
    if saved:
        engine.slave = saved
    engine.tags = [dict(config=tag, stale=True, error='BELUM DIUJI setelah restart') for tag in store.setting('tags') or []]
    for source in (Path(__file__).parent.parent / 'examples').glob('*.json'):
        profile = validate(json.loads(source.read_text(encoding='utf-8')))
        if profile['name'] not in [p['name'] for p in store.profiles()]:
            store.profile(profile)
    app.engine = engine
    token = secrets.token_urlsafe(32)
    allowed_hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
    if network:
        allowed_hosts.add(f"{network['host']}:{port}")
    allowed_origins = {f'http://{host}' for host in allowed_hosts}

    @app.before_request
    def guard():
        from .network import allowed_peer
        if not allowed_peer(request.remote_addr or '', network):
            return jsonify(error='Alamat client di luar jaringan LAN yang diizinkan'), 403
        if request.host not in allowed_hosts:
            return jsonify(error='Host ditolak'), 403
        if request.headers.get('Origin') and request.headers['Origin'] not in allowed_origins:
            return jsonify(error='Origin ditolak'), 403
        if request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return jsonify(error='Request lintas situs ditolak'), 403
        if request.method != 'GET' and (not secrets.compare_digest(request.headers.get('X-Serial-Token', ''), token) or not request.is_json):
            return jsonify(error='Token/session atau Content-Type tidak valid; refresh halaman'), 403

    @app.after_request
    def headers(result):
        result.headers['Cache-Control'] = 'no-store'
        result.headers['X-Content-Type-Options'] = 'nosniff'
        result.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return result

    @app.errorhandler(Exception)
    def errors(exc):
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            return jsonify(error=exc.description), exc.code
        app.logger.warning('API error: %s', exc)
        return jsonify(error=f'Kolom wajib tidak tersedia: {exc.args[0]}' if isinstance(exc, KeyError) else str(exc)), 400

    @app.get('/')
    def index():
        return app.send_static_file('index.html')

    @app.get('/api/health')
    def health():
        from .lifecycle import configuration_id
        return jsonify(status='ok', app='serial-protocol-web', version=engine.state()['app_version'], configuration=configuration_id(Path(directory), port))

    @app.get('/api/session')
    def session():
        return jsonify(token=token)

    @app.get('/api/state')
    def state():
        state = engine.state()
        state['preferences'] = store.setting('serial')
        import time
        for tag in state['tags']:
            if 'monotonic' in tag:
                tag['age_seconds'] = round(time.monotonic() - tag.pop('monotonic'), 2)
                tag['stale'] = tag['stale'] or tag['age_seconds'] > 5
        return jsonify(state)

    @app.get('/api/ports')
    def port_list():
        return jsonify(ports())

    @app.get('/api/profiles')
    def profiles():
        return jsonify(store.profiles())

    @app.get('/api/history')
    def history():
        return jsonify([{key: value for key, value in run.items() if key not in ('results', 'profile')} | {'profile_name': run['profile']['name']} for run in store.history()])

    @app.get('/api/export/<run_id>/<format>')
    def export(run_id, format):
        run = store.get(run_id)
        if format not in ('csv', 'json'):
            raise ValueError('Format export csv/json')
        data = export_csv(run) if format == 'csv' else json.dumps(run, ensure_ascii=False, indent=2)
        return send_file(io.BytesIO(data.encode('utf-8')), mimetype='text/csv' if format == 'csv' else 'application/json', as_attachment=True, download_name=f'{run_id}.{format}')

    @app.get('/api/log')
    def log_export():
        data = json.dumps(engine.state()['logs'], ensure_ascii=False, indent=2)
        return send_file(io.BytesIO(data.encode()), mimetype='application/json', as_attachment=True, download_name='serial-log.json')

    @app.get('/api/service')
    def service():
        from .lifecycle import status
        info = status(Path(directory), port)
        if request.remote_addr not in ('127.0.0.1', '::1'):
            info['data_directory'] = 'Data tersimpan pada laptop server'
        return jsonify(info)

    @app.post('/api/action/<action>')
    def action(action):
        if action in ('install-autostart', 'uninstall-autostart', 'disable-autostart', 'service-stop', 'service-restart') and request.remote_addr not in ('127.0.0.1', '::1'):
            return jsonify(error='Pengelolaan layanan Windows hanya dari localhost laptop server'), 403
        body = request.get_json()
        result = None
        if action == 'connect':
            engine.connect(body)
        elif action == 'disconnect':
            engine.disconnect()
        elif action == 'terminal':
            engine.terminal(body)
        elif action == 'periodic':
            engine.periodic(body)
        elif action == 'stop':
            engine.stop()
        elif action == 'master':
            engine.master(body)
        elif action == 'slave-config':
            engine.configure_slave(body)
        elif action == 'slave-start':
            engine.start_slave()
        elif action == 'mock-inject':
            engine.inject(body)
        elif action == 'profile':
            store.profile(validate(body))
        elif action == 'run':
            result = engine.run(body['profile'], body.get('identity', 'unknown'))
        elif action == 'mock-fault':
            if engine.owner or body['fault'] not in ('none', 'timeout', 'corrupt', 'echo'):
                raise ValueError('Stop dahulu / fault tidak valid')
            engine.mock_fault = body['fault']
        elif action == 'clear-log':
            with engine.lock:
                engine.events.clear()
        elif action == 'clear-history':
            if engine.owner:
                raise ValueError('Stop dahulu')
            store.clear()
        elif action in ('install-autostart', 'uninstall-autostart', 'disable-autostart'):
            from .lifecycle import autostart
            autostart(action == 'install-autostart', Path(directory), port)
        elif action in ('service-stop', 'service-restart'):
            import subprocess
            import sys
            import os
            from .lifecycle import ROOT
            executable = Path(sys.executable).with_name('pythonw.exe') if os.name == 'nt' else Path(sys.executable)
            subprocess.Popen([str(executable), str(ROOT / 'launcher.py'), action.removeprefix('service-'), '--data', str(directory), '--port', str(port)], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        else:
            raise ValueError('Aksi tidak dikenal')
        return jsonify(ok=True, result=result)

    return app
