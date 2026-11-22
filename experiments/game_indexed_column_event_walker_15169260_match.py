"""Indexed-column event walker: complete owner, guarded opening and literal-image gates."""
from pathlib import Path
import hashlib,json,os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_indexed_column_event_walker_15169260_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION='func_15169260'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def installed():
 return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']and sha(ROOT/'conker/retail_word_patches.us.csv')==MANIFEST['guards_sha256']

def prepare():
 live=installed();permitted={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],
  'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256']}
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
 where=OUT/'sdk-frame-last';before,bd=compile_owner(ROOT,where,MANIFEST['old_source'],'before')
 after,ad=compile_owner(ROOT,where,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,))==41
 assert diagnostic_rows(bd)==diagnostic_rows(ad)and normalized_pools(before)==normalized_pools(after)
 raw,refs=payload(after,FUNCTION);assert len(raw)==500 and int.from_bytes(raw[:4],'big')==0x27BDFFA8
 assert hashlib.sha256(raw).hexdigest()=='2b546bc5c2bd16d198ccc25275c5f5a075efecb80cef37c507f2cf7177bc99a6'
 return dict(raw_words=125,frame=88,neighbors=41,pools_equal=True,diagnostics_equal=True)

"""Closed saved-role allocation, empty-list sharing and linked row-end fold."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
root,out=ROOT,OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
NAME='func_15169260';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rename(w,mapping):
 op=w>>26
 if op in(2,3):return w
 fields=(21,16,11)if op==0 else(16,)if op==15 else(21,16);r=w
 for shift in fields:r=(r&~(31<<shift))|(mapping.get(w>>shift&31,w>>shift&31)<<shift)
 return r
def commute(w):return(w&~((31<<21)|(31<<16)))|((w>>16&31)<<21)|((w>>21&31)<<16)
def normalize(raw,refs):
 assert hashlib.sha256(raw).hexdigest()=='2b546bc5c2bd16d198ccc25275c5f5a075efecb80cef37c507f2cf7177bc99a6'
 ws=list(struct.unpack('>125I',raw));assert ws[0]==0x27BDFFA8
 order=[0,2,3,4,5,7,8,9,1,10,11,12,13,14,15,16,17,6,19,18]+list(range(20,33))
 order +=[37,74,39,33,34,35,76,36,75,38,40,41,43,42]+list(range(45,74))+[None]+[77,78,80,79]+list(range(82,103))+list(range(104,113))
 order +=[113,114,115,117,118,116,119,122,120,121,123,124]
 assert len(order)==123 and set(order)-{None}==set(range(125))-{44,81,103}
 inverse={i:j for j,i in enumerate(order)if i is not None};result=[];rr={};saved={18:20,19:18,20:19,22:23,23:30,30:22}
 for j,i in enumerate(order):
  if i is None:result.append(0x82880000);continue # Original unreachable signed depth load.
  old=ws[i];w=rename(old,saved)
  if old>>26 in(35,43)and old>>21&31==29 and(old>>16&31)in saved:
   reg=old>>16&31;slot=0x38 if reg==30 else 0x18+4*(reg-16);assert old&65535==slot
   mapped=saved[reg];w=(w&0xFFFF0000)|(0x38 if mapped==30 else 0x18+4*(mapped-16))
  if i==30:w=rename(w,{10:9})
  if i==31:w=rename(w,{15:14})
  if i==37:w=rename(w,{9:10})
  if i==74:w=rename(w,{14:15})
  if i==39:w=commute(rename(w,{9:10,10:9}))
  if i==76:w=commute(rename(w,{14:15,15:14}))
  if i in(98,99):w=rename(w,{24:15})
  if i==105:w=rename(w,{25:9})
  if 107<=i<=112:w=rename(w,{10:25,12:11,11:10})
  if i==36:w=(w&0x03FFFFFF)|(20<<26)
  if i in(43,80):w=(w&0x03FFFFFF)|(4<<26)
  if old>>26 in(1,4,5,6,7,20,21,22,23):
   target=i+1+((old&65535)^32768)-32768
   target={36:77,43:70,80:97}.get(i,target)
   assert target in inverse,(i,target);w=(w&0xFFFF0000)|((inverse[target]-j-1)&65535)
  result.append(w)
  if 4*i in refs:rr[4*j]=[(k,'D_800DD190'if i in(101,102)else n)for k,n in refs[4*i]]
 return struct.pack('>123I',*result),rr,order
def normalize_owner():
 raw,refs=payload(out/'sdk-frame-last/candidate.o',NAME);normal,nrefs,order=normalize(raw,refs);base=out/'baseline';original=(base/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[]
 assert not any(line.startswith(('game_1944C0,'+NAME+',').encode())for line in original.splitlines())
 # Row positions refer to the input stream; replacement order is sequential,
 # while omitted words and the one unreachable insertion adjust output extent.
 positions=[i for i in range(125)if i not in(44,81,103)];at=0
 for i,(word,)in enumerate(struct.iter_unpack('>I',raw)):
  omit=i in(44,81,103);replacement=0 if omit else struct.unpack_from('>I',normal,at*4)[0];newrefs=[]if omit else nrefs.get(at*4,[])
  insert='';insertrefs=''
  if not omit:
   at+=1
   if at==76:insert='0x82880000';insertrefs='-';at+=1
  spec=lambda v:';'.join(k+':'+n for k,n in v)or'-'
  if not omit and word==replacement and refs.get(4*i,[])==newrefs and not insert:continue
  rows.append(dict(filename='game_1944C0',function=NAME,offset='0x%03X'%(4*i),expected='0x%08X'%word,replacement='0x%08X'%replacement,expected_relocations=spec(refs.get(4*i,[])),replacement_relocations=spec(newrefs),note='Preserve closed saved-register roles, shared empty-node unwind, and linked row-end address',insert_after=insert,insert_after_relocations=insertrefs,omit='true'if omit else'false'))
 assert at==123
 buf=io.StringIO(newline='');csv.DictWriter(buf,fieldnames=fields).writerows(rows);guards=out/'private-word-patches.csv';guards.write_bytes(original+buf.getvalue().encode())
 where=out/'qualified-owner';where.mkdir(exist_ok=True);assembly=where/'game_1944C0.c.o.padded.s';obj=where/'game_1944C0.c.o'
 assembly.write_text(pc.emit_padded_assembly(out/'sdk-frame-last/candidate.o',root/'conker/retail_layout.us.txt','game_1944C0',word_patches_path=guards))
 def assemble(path,target):
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(target),str(path)],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 assemble(assembly,obj);assert payload(obj,NAME)==(normal,nrefs)
 p=out/'original-target.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(root/'conker/asm/nonmatchings/game_1944C0/func_15169260.s').read_text()+'\n.size '+NAME+',.-'+NAME+'\n');original_obj=p.with_suffix('.o');assemble(p,original_obj)
 actual,actual_refs=payload(original_obj,NAME)
 diffs=[(i,f'{a:08X}',f'{b:08X}')for i,(a,b)in enumerate(zip(struct.unpack('>123I',normal),struct.unpack('>123I',actual)))if a!=b]
 (out/'normalization-differences.json').write_text(json.dumps(dict(words=diffs,expected_refs=nrefs,actual_refs=actual_refs),indent=2)+'\n')
 assert(normal,nrefs)==(actual,actual_refs),(len(diffs),diffs[:16])
 assert same_functions(base/'conker/build/src/game_1944C0.c.o',obj,(NAME,))==41
 r=dict(raw_words=125,retail_words=123,frame=88,guards=len(rows),omissions=3,insertions=1,qualified_neighbors=41,all_normalized_words_and_relocations_equal=True,local_frame_gap_original_use_unrecovered=True,source_installed=installed(),matching_credit=0,guard_rows=rows,qualified_object_sha256=sha(obj))
 (out/'normalization.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='guard_rows'}),flush=True);return r


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
  args=[(out/'sdk-frame-last/selected-owner.c').relative_to(conker).as_posix()if a==source else(out/'private-word-patches.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
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
 assert payload(Path(str(target)+'.compact'),'func_15169260')==payload(out/'sdk-frame-last/candidate.o','func_15169260')
 assert same_functions(out/'baseline/conker/build/src/game_1944C0.c.o',target,('func_15169260',))==41
 assert normalized_pools(target)==normalized_pools(out/'baseline/conker/build/src/game_1944C0.c.o')
 r=dict(actual_Make_commands=len(commands),qualified_complete_owner_equal=True,compact_target_words=125,normalized_words=123,all_41_neighbors_and_pools_fixed=True,qualified_object_sha256=sha(target),source_installed=installed(),matching_credit=0)
 (out/'actual-Make.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r


"""Independent complete-image prediction for the uninstalled walker."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
root,out=ROOT,OUT;base=out/'baseline'
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.check_game_data_layout import audit_layout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def qualify():
 prepare();inspect_source();normalize_owner();replay_make()
 where=out/'image-qualification';where.mkdir(exist_ok=True);script=where/'conker.ld';owner=out/'qualified-owner/game_1944C0.c.o'
 text=(base/'conker/build/conker.ld').read_text();old='build/src/game_1944C0.c.o';assert text.count(old)==1;script.write_text(text.replace(old,owner.relative_to(root/'conker').as_posix()))
 image=where/'linked.elf';q=subprocess.run(['mips-linux-gnu-ld','-T',script.relative_to(root/'conker').as_posix(),*['-T'+n for n in ('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')],'--no-check-sections','--no-warn-mismatch','-o',image.relative_to(root/'conker').as_posix()],cwd=root/'conker',capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before);at=elf_slot_offset(predicted,0x15169260,492);predicted[at:at+492]=(root/'conker/conker.us.bin').read_bytes()[0x196710:0x1968FC]
 rows=[(at,r)for at,n,r,_ in symbol_rows(predicted)if n=='func_15169260'];assert len(rows)==1;at,r=rows[0];assert r[1:3]==(0x15169260,24);struct.pack_into('>I',predicted,at+8,492)
 actual=image.read_bytes()
 if installed():assert (ROOT/'conker/build/conker.us.elf').read_bytes()==actual
 assert actual==predicted,('Unexpected image bytes',sum(a!=b for a,b in zip(actual,predicted)),len(actual)-len(predicted))
 (where/'predicted.elf').write_bytes(predicted)
 r=dict(strict_predicted_ELF_equal=True,changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,metadata_permutations=[],ELF_sha256=sha(image),protected_data_audit=audit_layout(image,root/'conker'),source_installed=installed(),matching_credit=0)
 (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
 return r
