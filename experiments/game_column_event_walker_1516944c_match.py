"""Column-event walker: complete owner, guarded opening and literal-image gates."""
from pathlib import Path
import hashlib,json,os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_column_event_walker_1516944c_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION='func_1516944C'
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
 where=OUT/'assign-1';before,bd=compile_owner(ROOT,where,MANIFEST['old_source'],'before')
 after,ad=compile_owner(ROOT,where,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,))==41
 assert diagnostic_rows(bd)==diagnostic_rows(ad)and normalized_pools(before)==normalized_pools(after)
 raw,refs=payload(after,FUNCTION);assert len(raw)==424 and int.from_bytes(raw[:4],'big')==0x27BDFFC0
 assert hashlib.sha256(raw).hexdigest()=='15308276d7eab26843108986f73a18195f465c04a61f60ec8392c01400d66857'
 return dict(raw_words=106,frame=64,neighbors=41,pools_equal=True,diagnostics_equal=True)

"""Closed opening allocation/schedule and one linked row-end address fold."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
root,out=ROOT,OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
NAME='func_1516944C';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def normalize(raw,refs):
 assert hashlib.sha256(raw).hexdigest()=='15308276d7eab26843108986f73a18195f465c04a61f60ec8392c01400d66857'
 ws=list(struct.unpack('>106I',raw));assert ws[88:94]==[0x3C080000,0x25080000,0x27DE01A0,0x25090340,0x17C9FFC4,0x26F701A0]
 assert refs[352]==[('R_MIPS_HI16','D_800DCE50')]and refs[356]==[('R_MIPS_LO16','D_800DCE50')]
 order=list(range(106));order[16],order[22]=order[22],order[16]
 order[23:27]=[24,26,25,23];order[29:32]=[30,31,29];order.remove(91)
 assert len(order)==105 and set(order)==set(range(106))-{91}
 inverse={i:j for j,i in enumerate(order)};result=[];rr={}
 mapping={14:25,15:24,24:14,25:15}
 for j,i in enumerate(order):
  old=w=ws[i]
  if 16<=i<=32:
   op=w>>26;fields=(21,16,11)if op==0 else(16,)if op==15 else(21,16)
   for shift in fields:w=(w&~(31<<shift))|(mapping.get(old>>shift&31,old>>shift&31)<<shift)
  if i==92:w=(w&~(31<<16))|(8<<16)
  if old>>26 in(1,4,5,6,7,20,21,22,23):
   target=i+1+((old&65535)^32768)-32768;assert target in inverse
   w=(w&0xFFFF0000)|((inverse[target]-j-1)&65535)
  result.append(w)
  if i*4 in refs:rr[j*4]=[(k,'D_800DD190'if i in(88,89)else n)for k,n in refs[i*4]]
 return struct.pack('>105I',*result),rr,order

def normalize_owner():
 raw,refs=payload(out/'assign-1/candidate.o',NAME);normal,nrefs,order=normalize(raw,refs);inverse={i:j for j,i in enumerate(order)}
 base=out/'baseline';source=base/'conker/retail_word_patches.us.csv';original=source.read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  omit=i==91;j=i if i<91 else i-1;new=0 if omit else struct.unpack_from('>I',normal,4*j)[0];rr=[]if omit else nrefs.get(4*j,[])
  if not omit and w==new and refs.get(4*i,[])==rr:continue
  spec=lambda r:';'.join(k+':'+n for k,n in r)or'-'
  rows.append(dict(filename='game_1944C0',function=NAME,offset='0x%03X'%(4*i),expected='0x%08X'%w,replacement='0x%08X'%new,expected_relocations=spec(refs.get(4*i,[])),replacement_relocations=spec(rr),note='Preserve closed opening register allocation and schedule; fold the linked row-array end address',insert_after='',insert_after_relocations='',omit='true'if omit else'false'))
 buf=io.StringIO(newline='');csv.DictWriter(buf,fieldnames=fields).writerows(rows);guard=out/'private-word-patches.csv';guard.write_bytes(original+buf.getvalue().encode())
 where=out/'qualified-owner';where.mkdir(exist_ok=True);asm=where/'game_1944C0.c.o.padded.s';padded=where/'game_1944C0.c.o'
 asm.write_text(pc.emit_padded_assembly(out/'assign-1/candidate.o',root/'conker/retail_layout.us.txt','game_1944C0',word_patches_path=guard))
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(padded),str(asm)],capture_output=True,text=True);assert q.returncode==0,q.stderr
 assert payload(padded,NAME)==(normal,nrefs);assert same_functions(base/'conker/build/src/game_1944C0.c.o',padded,(NAME,))==41
 text='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(root/'conker/asm/nonmatchings/game_1944C0/func_1516944C.s').read_text()+'\n.size '+NAME+',.-'+NAME+'\n'
 p=out/'original-target.s';p.write_text(text);original_obj=p.with_suffix('.o');q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(original_obj),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr
 assert payload(original_obj,NAME)==(normal,nrefs)
 r=dict(raw_words=106,retail_words=105,frame=64,guards=len(rows),omissions=1,insertions=0,raw_and_padded_neighbors=41,all_normalized_words_and_named_relocations_equal=True,row_end_invariant='D_800DD190 == D_800DCE50 + 0x340',source_installed=installed(),matching_credit=0,guard_rows=rows,qualified_object_sha256=sha(padded))
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
  args=[(out/'assign-1/selected-owner.c').relative_to(conker).as_posix()if a==source else(out/'private-word-patches.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
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
 assert payload(Path(str(target)+'.compact'),'func_1516944C')==payload(out/'assign-1/candidate.o','func_1516944C')
 assert same_functions(out/'baseline/conker/build/src/game_1944C0.c.o',target,('func_1516944C',))==41
 assert normalized_pools(target)==normalized_pools(out/'baseline/conker/build/src/game_1944C0.c.o')
 r=dict(actual_Make_commands=len(commands),qualified_complete_owner_equal=True,compact_target_words=106,normalized_words=105,all_41_neighbors_and_pools_fixed=True,qualified_object_sha256=sha(target),source_installed=installed(),matching_credit=0)
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
 before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before);at=elf_slot_offset(predicted,0x1516944C,420);predicted[at:at+420]=(root/'conker/conker.us.bin').read_bytes()[0x1968FC:0x196AA0]
 rows=[(at,r)for at,n,r,_ in symbol_rows(predicted)if n=='func_1516944C'];assert len(rows)==1;at,r=rows[0];assert r[1:3]==(0x1516944C,20);struct.pack_into('>I',predicted,at+8,420)
 actual=image.read_bytes()
 if installed():assert (ROOT/'conker/build/conker.us.elf').read_bytes()==actual
 assert actual==predicted,('Unexpected image bytes',sum(a!=b for a,b in zip(actual,predicted)),len(actual)-len(predicted))
 (where/'predicted.elf').write_bytes(predicted)
 r=dict(strict_predicted_ELF_equal=True,changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,metadata_permutations=[],ELF_sha256=sha(image),protected_data_audit=audit_layout(image,root/'conker'),source_installed=installed(),matching_credit=0)
 (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
 return r
