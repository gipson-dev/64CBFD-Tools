"""Fingerprint and prepare the timed-motion guarded C candidate."""
import hashlib,json,os,shutil,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-timed-motion-150f48d0-durable'
MANIFEST=json.loads(Path(__file__).with_name('game_timed_motion_150f48d0_manifest.json').read_text())
def sha(data):return hashlib.sha256(data).hexdigest()
def input_digest(path,data):
 if path not in ('conker/conker.us.bin','conker/build/conker.us.elf','ido/ido5.3_recomp/cc'):data=data.replace(b'\r\n',b'\n')
 return sha(data)
def apply(text,changes,reverse=False):
 lines=text.splitlines(keepends=True)
 for item in reversed(changes):
  old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
  if lines[at:at+len(expected)]!=expected:raise ValueError('Timed-motion source context changed')
  lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
 return ''.join(lines)
def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 for path,expected in MANIFEST['inputs'].items():
  if input_digest(path,(ROOT/path).read_bytes())!=expected:raise ValueError('Timed-motion input changed: '+path)
 item=MANIFEST['source'];current=(ROOT/item['path']).read_text()
 if sha(current.encode())==item['before_sha256']:before,installed=current,False
 elif sha(current.encode())==item['after_sha256']:before,installed=apply(current,item['changes'],True),True
 else:raise ValueError('Unknown timed-motion source state')
 after=apply(before,item['changes'])
 if sha(before.encode())!=item['before_sha256'] or sha(after.encode())!=item['after_sha256']:raise ValueError('Timed-motion source fingerprint changed')
 for path,expected in MANIFEST['baseline'].items():
  dest=OUT/'frozen'/path;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():
   if installed or input_digest(path,(ROOT/path).read_bytes())!=expected:raise ValueError('Timed-motion baseline missing: '+path)
   shutil.copyfile(ROOT/path,dest)
  if input_digest(path,dest.read_bytes())!=expected:raise ValueError('Timed-motion frozen input changed: '+path)
 guard=(ROOT/'conker/retail_word_patches.us.csv').read_bytes().replace(b'\r\n',b'\n')
 expected=MANIFEST['guard_after_sha256'] if installed else MANIFEST['baseline']['conker/retail_word_patches.us.csv']
 if sha(guard)!=expected:raise ValueError('Timed-motion guard state differs from source')
 old,od=compile_owner(ROOT,OUT,before,'before');new,nd=compile_owner(ROOT,OUT,after,'formatted')
 if same_functions(old,new,('func_150F48D0',))!=5 or normalized_pools(old)!=normalized_pools(new) or diagnostic_rows(od)!=diagnostic_rows(nd):raise ValueError('Timed-motion owner neighbors, pools or diagnostics changed')
 symbols={r[1]:r[2][1] for r in symbol_rows((OUT/'frozen/conker/build/conker.us.elf').read_bytes())};ws=bound_blob(*payload(new,'func_150F48D0'),symbols);truth=struct.unpack_from('>90I',(ROOT/'conker/conker.us.bin').read_bytes(),0x121d80)
 if len(ws)!=90 or sum(a==b for a,b in zip(ws,truth))!=68 or sha(struct.pack('>90I',*ws))!=MANIFEST['bound_sha256']:raise ValueError('Timed-motion raw words or bindings changed')
 env=dict(os.environ,CBFD_CONSUMER_ROOT=str(ROOT),PYTHONDONTWRITEBYTECODE='1')
 p=subprocess.run([sys.executable,'-m','tools.tests.game_timed_motion_150f48d0_guards'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
 if p.returncode:raise ValueError(('Timed-motion guard derivation failed',p.stdout,p.stderr))
 if sha((OUT/'proposed-guards.csv').read_bytes().replace(b'\r\n',b'\n'))!=MANIFEST['guard_after_sha256']:raise ValueError('Timed-motion proposed guard bytes changed')
 print('Timed motion: 90 retail words, 22 guarded role/schedule words, five unchanged neighbors; installed='+str(installed),flush=True)
 return installed
if __name__=='__main__':prepare()
