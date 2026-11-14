"""Fail-closed qualification for the configured effect factory."""
import csv,hashlib,io,json,os,re,shutil,struct,subprocess,sys
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
OUT=ROOT/'conker/build/game-effect-config-1519c09c-durable';NAME='func_1519C09C';OWNER='generated_1C2C60'
MANIFEST=json.loads(Path(__file__).with_name('game_effect_config_1519c09c_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
def apply(text,changes,reverse=False):
 lines=text.splitlines(keepends=True)
 for item in reversed(changes):
  old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
  if lines[at:at+len(expected)]!=expected:raise ValueError('Effect config source context changed')
  lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
 return ''.join(lines)
def sources():
 item=MANIFEST['source'];current=(ROOT/item['path']).read_text()
 if sha(current)==item['before_sha256']:before,installed=current,False
 elif sha(current)==item['after_sha256']:before,installed=apply(current,item['changes'],True),True
 else:raise ValueError('Unknown effect config source state')
 after=apply(before,item['changes'])
 if sha(before)!=item['before_sha256'] or sha(after)!=item['after_sha256']:raise ValueError('Effect config source hashes changed')
 g=MANIFEST['guards'];current=(ROOT/g['path']).read_text();suffix=g['append']
 if installed:
  if not current.endswith(suffix):raise ValueError('Effect config guard suffix missing')
  old,new=current[:-len(suffix)],current
 else:old,new=current,current+suffix
 if sha(old)!=g['before_sha256'] or sha(new)!=g['after_sha256']:raise ValueError('Effect config guard state changed')
 return {'source':(before,after),'guards':(old,new)},installed
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
 (OUT/'private-guards.csv').write_text(texts['guards'][1]);(OUT/'proposed-guards.csv').write_text(texts['guards'][1])
 (OUT/'guard-rows.json').write_text(json.dumps(MANIFEST['guard_rows'],indent=2)+'\n')
 before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'formatted')
 if same_functions(before,after,(NAME,))!=68 or normalized_pools(before)!=normalized_pools(after) or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Effect config owner neighbors, pools or diagnostics changed')
 raw,refs=payload(after,NAME);symbols={r[1]:r[2][1] for r in symbol_rows((OUT/'frozen/conker/build/conker.us.elf').read_bytes())}
 truth=(ROOT/'conker/conker.us.bin').read_bytes()[0x1c954c:0x1c96b0];bound=bound_blob(raw,refs,symbols)
 if len(bound)!=89 or sum(a==b for a,b in zip(bound,struct.unpack('>89I',truth)))!=79:raise ValueError('Effect config compiled shape changed')
 old=list(csv.DictReader(io.StringIO(texts['guards'][0])));new=list(csv.DictReader(io.StringIO(texts['guards'][1])))
 if new[:len(old)]!=old or new[len(old):]!=MANIFEST['guard_rows'] or len(new)-len(old)!=10:raise ValueError('Effect config guard history changed')
 full=(ROOT/'conker/asm/1C2C60.s').read_text();match=re.search(r'^glabel '+NAME+r'\n.*?^endlabel '+NAME+r'\s*$',full,re.M|re.S)
 if not match:raise ValueError('Original effect config assembly missing')
 assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 for kind in ('generated','c'):
  if kind=='generated':text=pg.emit_padded_assembly(after,ROOT/'conker/asm/1C2C60.s',filename=OWNER,word_patches_path=OUT/'proposed-guards.csv')
  else:text=pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv')
  padded=assemble(text,kind+'-guarded')
  if struct.pack('>89I',*bound_blob(*payload(padded,NAME),symbols))!=truth or same_functions(ROOT/'conker/build/src/game/generated_1C2C60.c.o',padded,(NAME,))!=68:raise ValueError('Padded effect config differs')
 print('Effect config: 89 retail words, 10 checked guards and 68 unchanged neighbors; installed='+str(installed),flush=True)
 return texts,installed
if __name__=='__main__':prepare()
