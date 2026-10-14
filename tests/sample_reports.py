"""Generate only synthetic reports for publication, never local production history."""
import json
from pathlib import Path
import tempfile
from serialweb.engine import Engine
from serialweb.store import Store, export_csv


ROOT=Path(__file__).resolve().parent.parent


def generate():
    target=ROOT/'examples/reports';target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        store=Store(Path(temporary));engine=Engine(store);engine.connect({'fixture':'MOCK'})
        for name,fault in [('pass','none'),('fail','corrupt')]:
            engine.mock_fault=fault
            profile=json.loads((ROOT/'examples/modbus-read.json').read_text(encoding='utf-8'))
            engine.run(profile,'SIMULASI — DUT sintetis');engine.worker.join(5)
            report=engine.state()['active']
            assert report['fixture']=='MOCK'
            (target/f'simulation-{name}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            (target/f'simulation-{name}.csv').write_text(export_csv(report),encoding='utf-8',newline='')
        engine.disconnect();store.db.close()


if __name__=='__main__':generate()
