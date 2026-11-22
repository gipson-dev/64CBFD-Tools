"""Direct sprite-frame updater: complete owner, SDK ABI and literal-image gates."""
from pathlib import Path
import hashlib,json,os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_sprite_frame_update_15168870_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION='func_15168870'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 live=installed();permitted={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256']}
 assert sha(ROOT/'conker/retail_word_patches.us.csv')==MANIFEST['guards_sha256']
 for n,d in MANIFEST['inputs'].items():
  frozen=OUT/'baseline'/n
  if frozen.exists():assert sha(frozen)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(permitted.get(n,d)if live else d),('Phase input changed',n)
 return live
def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 from tools import pad_generated_object as pg
 sys.modules.setdefault('pad_generated_object',pg)
 from tools import pad_c_object as pc
 import subprocess
 where=OUT/'frames-mod32';before,bd=compile_owner(ROOT,where,MANIFEST['old_source'],'before');after,ad=compile_owner(ROOT,where,MANIFEST['selected_source'],'candidate')
 (where/'body.c').write_text(MANIFEST['body'])
 assert same_functions(before,after,(FUNCTION,))==41
 assert diagnostic_rows(bd)==diagnostic_rows(ad)and normalized_pools(before)==normalized_pools(after)
 raw,refs=payload(after,FUNCTION);assert len(raw)==444 and raw[:4]==bytes.fromhex('27bdffe8')
 assert hashlib.sha256(raw).hexdigest()=='4b750550766c8a0122f148357e24ce5fa17dc8331d5e205d50e6c78064753498'
 def assemble(text,path):
  p=path.with_suffix('.s');p.write_text(text)
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(path),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 original=OUT/'original-target.o'
 assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(ROOT/'conker/asm/nonmatchings/game_1944C0/func_15168870.s').read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n',original)
 assert payload(original,FUNCTION)==(raw,refs)
 obj=OUT/'qualified-owner/game_1944C0.c.o';obj.parent.mkdir(exist_ok=True)
 assemble(pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt','game_1944C0',word_patches_path=ROOT/'conker/retail_word_patches.us.csv'),obj)
 assert sha(obj)==MANIFEST['padded_sha256']and payload(obj,FUNCTION)==(raw,refs)
 assert same_functions(OUT/'baseline'/MANIFEST['object'],obj,(FUNCTION,))==41
 (OUT/'private-word-patches.csv').write_bytes((OUT/'baseline/conker/retail_word_patches.us.csv').read_bytes())
 return dict(raw_words=111,retail_words=111,frame=24,guards=0,neighbors=41,pools_equal=True,diagnostics_equal=True)

"""Replay the actual owner Make recipe against frozen source and guard proposals."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
root,out=ROOT,OUT;conker=root/'conker'
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def replay_make():
 source='src/game_1944C0.c';shadow=out/'make-shadow';target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
 q=subprocess.run(['make','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()],cwd=conker,capture_output=True,text=True,check=True)
 (out/'actual-Make-plan.txt').write_text(q.stdout+q.stderr);commands=[];diagnostics=[]
 for line in q.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
  args=[(out/'frames-mod32/selected-owner.c').relative_to(conker).as_posix()if a==source else(out/'private-word-patches.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
  args=[str(TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else a for a in args]
  redirect=None
  if '>'in args:
   assert args[-2]=='>'and args.count('>')==1;redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  r=subprocess.run(args,cwd=conker,capture_output=True,text=True);assert r.returncode==0,(args,r.stdout,r.stderr)
  if redirect:redirect.write_text(r.stdout)
  else:diagnostics.append(r.stdout+r.stderr)
  commands.append(args)
 (out/'actual-Make-commands.json').write_text(json.dumps(commands,indent=2)+'\n');(out/'actual-Make-diagnostics.txt').write_text(''.join(diagnostics))
 assert target.read_bytes()==(out/'qualified-owner/game_1944C0.c.o').read_bytes()
 assert payload(Path(str(target)+'.compact'),'func_15168870')==payload(out/'frames-mod32/candidate.o','func_15168870')
 assert same_functions(out/'baseline/conker/build/src/game_1944C0.c.o',target,('func_15168870',))==41
 assert normalized_pools(target)==normalized_pools(out/'baseline/conker/build/src/game_1944C0.c.o')
 r=dict(actual_Make_commands=len(commands),qualified_complete_owner_equal=True,compact_target_words=111,normalized_words=111,all_41_neighbors_and_pools_fixed=True,qualified_object_sha256=sha(target),source_installed=installed(),matching_credit=0)
 (out/'actual-Make.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r


"""Independent complete-image prediction for the uninstalled walker."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
root,out=ROOT,OUT;base=out/'baseline'
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.check_game_data_layout import audit_layout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def qualify():
 prepare();inspect_source();replay_make()
 where=out/'image-qualification';where.mkdir(exist_ok=True);script=where/'conker.ld';owner=out/'qualified-owner/game_1944C0.c.o'
 text=(base/'conker/build/conker.ld').read_text();old='build/src/game_1944C0.c.o';assert text.count(old)==1;script.write_text(text.replace(old,owner.relative_to(root/'conker').as_posix()))
 image=where/'linked.elf';q=subprocess.run(['mips-linux-gnu-ld','-T',script.relative_to(root/'conker').as_posix(),*['-T'+n for n in ('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')],'--no-check-sections','--no-warn-mismatch','-o',image.relative_to(root/'conker').as_posix()],cwd=root/'conker',capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before);at=elf_slot_offset(predicted,0x15168870,444);predicted[at:at+444]=(root/'conker/conker.us.bin').read_bytes()[0x195D20:0x195EDC]
 rows=[(at,r)for at,n,r,_ in symbol_rows(predicted)if n=='func_15168870'];assert len(rows)==1;at,r=rows[0];assert r[1:3]==(0x15168870,12);struct.pack_into('>I',predicted,at+8,444)
 from types import FunctionType
 from tools.experiments import game_actor_state_tick_integration as symbols
 # Explicit bounded GNU-ld symbol/string permutation; all named fields retained.
 predict_order=FunctionType(symbols.reorder_symbols.__code__,dict(symbols.reorder_symbols.__globals__,SYMBOL_ORDER=[('func_150CBCE0','D_800E0E2C')]))
 predicted=predict_order(predicted)
 actual=image.read_bytes()
 if installed():assert (ROOT/'conker/build/conker.us.elf').read_bytes()==actual
 assert actual==predicted,('Unexpected image bytes',sum(a!=b for a,b in zip(actual,predicted)),len(actual)-len(predicted))
 (where/'predicted.elf').write_bytes(predicted)
 r=dict(strict_predicted_ELF_equal=True,changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,metadata_permutations=[['func_150CBCE0','D_800E0E2C']],ELF_sha256=sha(image),protected_data_audit=audit_layout(image,root/'conker'),source_installed=installed(),matching_credit=0)
 (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
 return r
