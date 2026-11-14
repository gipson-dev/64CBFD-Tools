"""Qualify the linked-effect constructor and its direct C caller."""
import hashlib,json,os,re,shutil,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-linked-effect-constructor-151ceaac-durable';NAME='func_151CEAAC';OWNER='generated_1FA770'
MANIFEST=json.loads(Path(__file__).with_name('game_linked_effect_constructor_151ceaac_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
def apply(text,changes,reverse=False):
 lines=text.splitlines(keepends=True)
 for item in reversed(changes):
  old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
  if lines[at:at+len(expected)]!=expected:raise ValueError('Linked-effect source context changed')
  lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
 return ''.join(lines)
def sources():
 texts={};states=[]
 for name in ('source','caller'):
  item=MANIFEST[name];current=(ROOT/item['path']).read_text()
  if sha(current)==item['before_sha256']:before,installed=current,False
  elif sha(current)==item['after_sha256']:before,installed=apply(current,item['changes'],True),True
  else:raise ValueError('Unknown linked-effect '+name+' state')
  after=apply(before,item['changes'])
  if sha(before)!=item['before_sha256'] or sha(after)!=item['after_sha256']:raise ValueError('Linked-effect '+name+' hash changed')
  texts[name]=(before,after);states.append(installed)
 if len(set(states))!=1:raise ValueError('Linked-effect source and caller states differ')
 return texts,states[0]
def assemble(text,label):
 asm=OUT/(label+'.s');obj=asm.with_suffix('.o');asm.write_text(text)
 args=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(ROOT/'conker')),str(asm.relative_to(ROOT/'conker'))]
 p=subprocess.run(args,cwd=ROOT/'conker',capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr)
 return obj
def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 for path,digest in MANIFEST['inputs'].items():
  if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('Input changed: '+path)
 texts,installed=sources()
 for path,digest in MANIFEST['baseline'].items():
  dest=OUT/'frozen'/path;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():
   if installed or hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('Pre-install baseline missing: '+path)
   shutil.copyfile(ROOT/path,dest)
  if hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:raise ValueError('Frozen baseline changed: '+path)
 (OUT/'caller-after.c').write_text(texts['caller'][1])
 before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'formatted')
 if same_functions(before,after,(NAME,))!=51 or normalized_pools(before)!=normalized_pools(after) or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Linked-effect owner or diagnostics changed')
 ca,cd=compile_owner(ROOT,OUT,texts['caller'][0],'caller-before');cb,ce=compile_owner(ROOT,OUT,texts['caller'][1],'caller-after')
 if same_functions(ca,cb)!=16 or normalized_pools(ca)!=normalized_pools(cb) or diagnostic_rows(cd)!=diagnostic_rows(ce):raise ValueError('Linked-effect caller or diagnostics changed')
 symbols={r[1]:r[2][1] for r in symbol_rows((OUT/'frozen/conker/build/conker.us.elf').read_bytes())};truth=(ROOT/'conker/conker.us.bin').read_bytes()[0x1fbf5c:0x1fc0c0]
 if struct.pack('>89I',*bound_blob(*payload(after,NAME),symbols))!=truth:raise ValueError('Direct C body is not retail-exact')
 full=(ROOT/'conker/asm/1FA770.s').read_text();match=re.search(r'^glabel '+NAME+r'\n.*?^endlabel '+NAME+r'\s*$',full,re.M|re.S)
 if not match:raise ValueError('Original linked-effect assembly missing')
 assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 for kind in ('generated','c'):
  if kind=='generated':text=pg.emit_padded_assembly(after,ROOT/'conker/asm/1FA770.s',filename=OWNER,word_patches_path=ROOT/'conker/retail_word_patches.us.csv')
  else:text=pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=ROOT/'conker/retail_word_patches.us.csv')
  padded=assemble(text,kind+'-padded')
  if struct.pack('>89I',*bound_blob(*payload(padded,NAME),symbols))!=truth or same_functions(ROOT/'conker/build/src/game/generated_1FA770.c.o',padded,(NAME,))!=51:raise ValueError('Padded linked-effect owner differs')
 print('Linked effect: 89 retail words, zero guards, 51 unchanged neighbors and 16 unchanged caller functions; installed='+str(installed),flush=True)
 return texts,installed
if __name__=='__main__':prepare()
