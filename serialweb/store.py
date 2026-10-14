import csv
import io
import json
import sqlite3
import threading
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(directory / 'history.db', check_same_thread=False)
        self.db.execute('PRAGMA auto_vacuum=FULL')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA journal_size_limit=1000000')
        self.db.execute('PRAGMA max_page_count=32768')
        self.db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, body TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS profiles (name TEXT PRIMARY KEY, body TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, body TEXT)')
        for run in self.history():
            if run['status'] == 'BERJALAN':
                run.update(status='INCOMPLETE', reason='Backend terhenti/restart; command tidak diulang', ended=now())
                self.save(run)

    def save(self, run):
        with self.lock, self.db:
            while len(json.dumps(run).encode('utf-8')) > 1000000 and run.get('results'):
                run['results'].pop(0)
                run['truncated_results'] = run.get('truncated_results', 0) + 1
            self.db.execute('INSERT OR REPLACE INTO runs VALUES (?, ?)', (run['id'], json.dumps(run)))
            self.db.execute('DELETE FROM runs WHERE id NOT IN (SELECT id FROM runs ORDER BY rowid DESC LIMIT 200)')
            while self.db.execute('SELECT COALESCE(SUM(LENGTH(body)),0) FROM runs').fetchone()[0] > 64000000:
                self.db.execute('DELETE FROM runs WHERE rowid=(SELECT MIN(rowid) FROM runs)')
        with self.lock:
            self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')

    def history(self):
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute('SELECT body FROM runs ORDER BY rowid DESC')]

    def get(self, run_id):
        with self.lock:
            row = self.db.execute('SELECT body FROM runs WHERE id=?', (run_id,)).fetchone()
            if not row:
                raise ValueError('Run tidak ditemukan')
            return json.loads(row[0])

    def profiles(self):
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute('SELECT body FROM profiles ORDER BY name')]

    def profile(self, profile):
        with self.lock, self.db:
            if len(self.profiles()) >= 100 and profile['name'] not in [p['name'] for p in self.profiles()]:
                raise ValueError('Batas 100 profil tercapai')
            self.db.execute('INSERT OR REPLACE INTO profiles VALUES (?,?)', (profile['name'], json.dumps(profile)))

    def setting(self, name, value=None):
        with self.lock, self.db:
            if value is not None:
                self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (name, json.dumps(value)))
            row = self.db.execute('SELECT body FROM settings WHERE name=?', (name,)).fetchone()
            return json.loads(row[0]) if row else None

    def clear(self):
        with self.lock, self.db:
            self.db.execute('DELETE FROM runs')
        with self.lock:
            self.db.execute('VACUUM')


def excel(value):
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value if value is not None else '')
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text


def export_csv(run):
    output = io.StringIO(newline='')
    fields = ['run_id', 'profile', 'profile_version', 'started_utc', 'ended_utc', 'timezone', 'app_version', 'identity', 'fixture', 'protocol', 'serial', 'status', 'reason', 'notes', 'step', 'repeat', 'target', 'actual', 'value', 'tx', 'rx', 'latency_ms', 'error', 'retry']
    writer = csv.DictWriter(output, fields)
    writer.writeheader()
    for step in run.get('results') or [{}]:
        row = dict(run_id=run['id'], profile=run['profile']['name'], profile_version=run['profile']['version'], started_utc=run['started'], ended_utc=run.get('ended'), timezone='UTC; UI Asia/Jakarta', app_version=run['app_version'], identity=run.get('identity', 'unknown'), fixture=run['fixture'], protocol=run['profile']['protocol'], serial=run['serial'], status=run['status'], reason=run.get('reason', ''), step=step.get('step'), repeat=step.get('repeat'), target=step.get('assertions'), actual=step.get('rx'), value=step.get('value'), tx=step.get('tx'), rx=step.get('rx'), latency_ms=step.get('latency_ms'), error=step.get('error'), retry=0)
        row['notes'] = run['profile'].get('notes', '')
        writer.writerow({key: excel(value) for key, value in row.items()})
    return '\ufeff' + output.getvalue()
