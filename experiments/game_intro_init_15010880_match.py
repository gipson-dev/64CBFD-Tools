"""Fail-closed owner and relocation-aware initializer qualification."""
import csv,hashlib,io,json,os,shutil,struct,subprocess
from pathlib import Path
from tools import pad_generated_object as pg
import sys
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-intro-init-15010880-durable';NAME='func_15010880';OWNER='game_3DC30'
MANIFEST=json.loads(Path(__file__).with_name('game_intro_init_15010880_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()

def apply(text,changes,reverse=False):
 lines=text.splitlines(keepends=True)
 for item in reversed(changes):
  old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
  if lines[at:at+len(expected)]!=expected:raise ValueError('Initializer source context changed')
  lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
 return ''.join(lines)

def sources():
 s=MANIFEST['source'];g=MANIFEST['guards'];current=(ROOT/s['path']).read_text();h=sha(current)
 if h==s['before_sha256']:before,installed=current,False
 elif h==s['after_sha256']:before,installed=apply(current,s['changes'],True),True
 else:raise ValueError('Unknown initializer source state')
 after=apply(before,s['changes']);assert sha(before)==s['before_sha256'] and sha(after)==s['after_sha256']
 current=(ROOT/g['path']).read_text();suffix=g['append']
 if installed:
  if not current.endswith(suffix):raise ValueError('Initializer guard suffix missing')
  old=current[:-len(suffix)];new=current
 else:old=current;new=current+suffix
 if sha(old)!=g['before_sha256'] or sha(new)!=g['after_sha256']:raise ValueError('Initializer guard state changed')
 return {'source':(before,after),'guards':(old,new)},installed

def assemble(text,label):
 asm=OUT/(label+'.s');obj=asm.with_suffix('.o');asm.write_text(text)
 args=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(ROOT/'conker')),str(asm.relative_to(ROOT/'conker'))]
 p=subprocess.run(args,cwd=ROOT/'conker',capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr)
 return obj

def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 for path,h in MANIFEST['inputs'].items():
  if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise ValueError('Initializer input changed: '+path)
 texts,installed=sources()
 for path,h in MANIFEST['baseline'].items():
  dest=OUT/'frozen'/path;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():
   if installed:raise ValueError('Retained pre-install baseline required: '+path)
   if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise ValueError('Baseline changed: '+path)
   shutil.copyfile(ROOT/path,dest)
  if hashlib.sha256(dest.read_bytes()).hexdigest()!=h:raise ValueError('Frozen baseline changed: '+path)
 (OUT/'typed-proposal.c').write_text(texts['source'][1]);(OUT/'proposed-guards.csv').write_text(texts['guards'][1])
 before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'typed')
 if same_functions(before,after,(NAME,))!=2 or normalized_pools(before)!=normalized_pools(after) or bd!=ad:raise ValueError('Initializer owner or diagnostics changed')
 asm=(ROOT/'conker/asm/nonmatchings/game_3DC30/func_15010880.s').read_text()
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 raw,refs=payload(after,NAME);truth,trefs=payload(retail,NAME)
 if len(raw)!=336 or len(truth)!=336:raise ValueError('Initializer extent changed')
 words=list(struct.unpack('>84I',raw));order=list(range(84));order[33:44]=[35,36,37,43,33,34,38,39,40,41,42]
 normalized=struct.pack('>84I',*(words[i] for i in order));nrefs={j*4:refs[i*4] for j,i in enumerate(order) if i*4 in refs}
 if (normalized,nrefs)!=(truth,trefs):raise ValueError('Initializer scheduling or bindings changed')
 old=list(csv.DictReader(io.StringIO(texts['guards'][0])));new=list(csv.DictReader(io.StringIO(texts['guards'][1])))
 if new[:len(old)]!=old or new[len(old):]!=MANIFEST['guard_rows'] or len(new)-len(old)!=11:raise ValueError('Initializer guard history changed')
 emitted=pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv');padded=assemble(emitted,'padded')
 if payload(padded,NAME)!=(truth,trefs) or same_functions(ROOT/'conker/build/src/game_3DC30.c.o',padded,(NAME,))!=2:raise ValueError('Initializer padded owner differs')
 addresses={r[1]:r[2][1] for r in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())};linked=bound_blob(truth,trefs,addresses)
 if struct.pack('>84I',*linked)!=(ROOT/'conker/conker.us.bin').read_bytes()[0x3dd30:0x3de80]:raise ValueError('Initializer retail bytes differ')
 print('Initializer: 84 retail words, 11 scheduling guards, two unchanged neighbors; installed='+str(installed),flush=True)
 return texts,installed
if __name__=='__main__':prepare()
