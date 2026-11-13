"""Repeat the private paired-constructor screens and preserve their alias gap."""
import hashlib,json,os,subprocess
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-random-paired-constructor-match'
MANIFEST=json.loads(Path(__file__).with_name('game_random_paired_constructor_manifest.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
def payload(path,name):
 t,fs,refs=parse_object(path);f=fs[name];a=f['value'];return t[a:a+f['size']],{i-a:v for i,v in refs.items()if a<=i<a+f['size']}
def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 if sha((ROOT/'conker/conker.us.bin').read_bytes())!=MANIFEST['rom_sha256']:raise ValueError('Retail image changed')
 if sha((ROOT/'conker/src/game/generated_15D730.c').read_bytes())!=MANIFEST['helper_source_sha256']:raise ValueError('Helper ABI source changed')
 result={}
 for spec in MANIFEST['targets']:
  name=spec['name'];src=(ROOT/spec['source']).read_bytes();asm=(ROOT/spec['assembly']).read_bytes()
  if sha(src)!=spec['source_sha256'] or sha(asm)!=spec['assembly_sha256']:raise ValueError('Target owner or assembly changed: '+name)
  original=src.decode();candidate=original.replace(body(original,name),spec['fragment'].rstrip(),1)
  before,bd=compile_owner(ROOT,OUT,original,name+'-before');after,ad=compile_owner(ROOT,OUT,candidate,name+'-candidate')
  if same_functions(before,after,(name,))!=9 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Neighbor or pool changed')
  if diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Changed diagnostics')
  marker='glabel '+name+'\n';end='endlabel '+name;assembly=asm.decode();frag=marker+assembly.split(marker,1)[1].split(end,1)[0]+end
  path=OUT/(name+'-retail.s');obj=path.with_suffix('.o');path.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+frag+'\n.size '+name+',.-'+name+'\n')
  r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=ROOT/'conker',capture_output=True,text=True)
  if r.returncode:raise ValueError(r.stderr)
  raw,_=payload(after,name);truth,_=payload(obj,name)
  if len(raw)!=788 or len(truth)!=788 or raw[:4]!=bytes.fromhex('27bdff40') or truth[:4]!=bytes.fromhex('27bdff48'):raise ValueError('Unexpected frame or length')
  result[name]={'before':before,'after':after,'retail':obj}
 return result
