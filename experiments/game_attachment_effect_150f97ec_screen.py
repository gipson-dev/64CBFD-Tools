"""Fingerprint a private non-matching attachment-effect C candidate."""
import hashlib,json,os,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-attachment-effect-150f97ec-durable'
MANIFEST=json.loads(Path(__file__).with_name('game_attachment_effect_150f97ec_manifest.json').read_text())
def sha(data):return hashlib.sha256(data).hexdigest()
def input_digest(path,data):
 if path not in ('conker/conker.us.bin','ido/ido5.3_recomp/cc'):data=data.replace(b'\r\n',b'\n')
 return sha(data)
def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 for path,expected in MANIFEST['inputs'].items():
  if input_digest(path,(ROOT/path).read_bytes())!=expected:raise ValueError('Screen input changed: '+path)
 source=(ROOT/MANIFEST['source']).read_text()
 if sha(source.encode())!=MANIFEST['source_sha256']:raise ValueError('Screen owner changed')
 old=MANIFEST['old'];new=MANIFEST['new']
 if source.count(old)!=1:raise ValueError('Screen placeholder context changed')
 candidate=source.replace(old,new)
 if sha(candidate.encode())!=MANIFEST['candidate_sha256']:raise ValueError('Candidate changed')
 before,bd=compile_owner(ROOT,OUT,source,'baseline');after,ad=compile_owner(ROOT,OUT,candidate,'candidate-1')
 if same_functions(before,after,('func_150F97EC',))!=16 or normalized_pools(before)!=normalized_pools(after) or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner neighbors, pools or diagnostics changed')
 symbols={r[1]:r[2][1] for r in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
 ws=bound_blob(*payload(after,'func_150F97EC'),symbols);packed=struct.pack('>%dI'%len(ws),*ws)
 retail=(ROOT/'conker/conker.us.bin').read_bytes()[0x126c9c:0x126e00]
 if sha(packed)!=MANIFEST['bound_sha256'] or len(ws)!=87 or len(retail)!=356:raise ValueError('Private candidate words or bindings changed')
 truth=struct.unpack('>89I',retail);same=sum(a==b for a,b in zip(ws,truth))
 if same!=14:raise ValueError('Private screen score changed')
 print('Attachment effect: retail 89 words, candidate 87, same-position 14, 16 unchanged neighbors; uncredited',flush=True)
 return ws
if __name__=='__main__':prepare()
