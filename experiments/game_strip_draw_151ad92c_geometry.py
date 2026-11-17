"""Complete geometry-loop qualification; full renderer adoption stays open."""
from pathlib import Path
import hashlib,json,os
from tools.experiments import game_strip_draw_151ad92c_lifetime as common
ROOT,PACKET,NAME,ENTRY,SOURCE=common.ROOT,common.PACKET,common.NAME,common.ENTRY,common.SOURCE
QUALIFICATION=PACKET/'geometry-qualified';FROZEN=QUALIFICATION/'baseline'
OUT=Path(os.environ.get('CBFD_STRIP_DRAW_GEOMETRY_WORK',QUALIFICATION/'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_strip_draw_151ad92c_geometry_manifest.json').read_text())
_prior_out=[]
def check_inputs():
 common.check_inputs();rows=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(rows)==PIN['frozen_input_count']
 for name,h in rows.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 return len(rows)
def enter_engines():
 check_inputs();assert not _prior_out;_prior_out.append(common.OUT);common.OUT=OUT
 return common.bind_engines()
def leave_engines():
 common.restore_engines();assert len(_prior_out)==1;common.OUT=_prior_out.pop()
def compile_and_check():
 check_inputs();report=common.compile_and_check();assert report['raw_sha256']==PIN['raw_sha256']and report['raw_words']==PIN['words'];return report
