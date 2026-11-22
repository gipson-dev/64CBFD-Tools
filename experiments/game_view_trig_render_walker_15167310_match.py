"""Typed render walker: all SDK consumers, derived guards and strict ELF gates."""
from pathlib import Path
import hashlib,json,os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_view_trig_render_walker_15167310_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION='func_15167310'
root,out=ROOT,OUT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 live=installed();report=json.loads((OUT/'header-audit.json').read_text());assert sha(OUT/'header-audit.json')==MANIFEST['header_audit_sha256']
 assert report['owners']==305 and not report['changed_auxiliary_symbol_consumers']
 allowed=dict(MANIFEST['proposals']);allowed['conker/retail_word_patches.us.csv']=MANIFEST['guards_sha256'];allowed['conker/build/conker.us.elf']=MANIFEST['predicted_ELF_sha256']
 for r in report['records']:
  assert sha(ROOT/r['qualified_object'])==r['after_sha256']
  allowed[r['object']]=r['after_sha256']
 allowed[MANIFEST['object']]=MANIFEST['padded_sha256']
 for n,d in report['private_headers'].items():assert sha(OUT/'proposal'/n)==d,n
 for n,d in MANIFEST['proposals'].items():assert sha(OUT/'proposal'/n)==d,n
 assert sha(OUT/'selected-body.c')==hashlib.sha256(MANIFEST['body'].encode()).hexdigest()
 for n,d in MANIFEST['inputs'].items():
  frozen=OUT/'baseline'/n
  if frozen.exists():assert sha(frozen)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 return live
def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 where=OUT/'selected'
 def compile_phase(text,phase,headers):
  for name in('structs.h','functions.h','variables.h'):
   h=(headers/name).read_text()
   if name!='structs.h':h=h.replace('#include "structs.h"','#include "'+phase+'-structs.h"')
   (where/(phase+'-'+name)).write_bytes(h.encode())
  for name in('functions.h','variables.h'):text=text.replace('#include "'+name+'"','#include "'+phase+'-'+name+'"')
  return compile_owner(ROOT,where,text,phase,('-O2','-g3'))
 before,bd=compile_phase(MANIFEST['old_source'],'before',OUT/'baseline/conker/include')
 after,ad=compile_phase(MANIFEST['selected_source'],'candidate',OUT/'proposal/conker/include')
 assert same_functions(before,after,(FUNCTION,))==41 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 result=normalize_owner();assert result['guards']==45 and result['neighbors']==41
 assert sha(OUT/'private-word-patches.csv')==MANIFEST['guards_sha256']and sha(OUT/'qualified-owner/game_1944C0.c.o')==MANIFEST['padded_sha256']
 return result

"""Derived cache-store schedule, descriptor-base roles and linked array-end fold."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
root,out=ROOT,OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
NAME='func_15167310';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rename(w,m):
 op=w>>26
 if op in(2,3):return w
 fields=(21,16,11)if op==0 else(16,)if op==15 else(21,16);result=w
 for shift in fields:result=(result&~(31<<shift))|(m.get(w>>shift&31,w>>shift&31)<<shift)
 return result
def commute(w):return(w&~((31<<21)|(31<<16)))|((w>>16&31)<<21)|((w>>21&31)<<16)
def normalize(raw,refs):
 assert hashlib.sha256(raw).hexdigest()=='e25e472fbc23d897367f829f2ce120ae5a2aabd5b98fbe3bacf1ef623bab36a7'
 words=list(struct.unpack('>124I',raw));assert words[0]==0x27BDFF98
 order=list(range(35))+[37,36,38,40,39,35]+list(range(41,52))+[55,52,53,54,58,59,60,56,57]+[61,62,63,65]+list(range(66,72))+[74,75]+list(range(76,101))+[None,102,101]+list(range(103,124))
 assert len(order)==122 and set(order)-{None}==set(range(124))-{64,72,73}
 inverse={i:j for j,i in enumerate(order)if i is not None};result=[];relocs={}
 mappings={61:{10:11},62:{11:10},65:{10:11,11:21},76:{14:13},77:{14:13},79:{15:14},81:{15:14,24:15},84:{25:24},85:{25:24,8:25},86:{8:25},88:{9:8},91:{9:8},92:{10:9},93:{10:9},98:{12:10},99:{12:10,13:12},100:{13:12},103:{14:13},105:{15:14},108:{15:14,24:15},110:{24:15}}
 for j,i in enumerate(order):
  if i is None:
   assert j==98;result.append(rename(words[54],{19:13}));relocs[4*j]=refs[4*54];continue
  if i==83:mappings[i]={24:15}
  old=words[i];word=rename(old,mappings.get(i,{}))
  if i==35:assert old==0xE6600000;word=(old&0xFFFF0000)|0xFFFC
  if i==63:assert old==0x256B0000;word=(old&~((31<<21)|(31<<16)))|(10<<21)|(21<<16)
  if i==75:word=rename(commute(old),{13:30})
  if i==77:word=(word&0x03FFFFFF)|(4<<26)
  if i==78:assert old==0x26B501A0;word=0
  if i==102:
   assert old==0x27CE0340;word=(old&0xFC000000)|(13<<21)|(13<<16);relocs[4*j]=[('R_MIPS_LO16','D_800DD190')]
  if old>>26 in(1,4,5,6,7,20,21,22,23):
   target=i+1+((old&65535)^32768)-32768
   mapped=98 if i in(69,77)else inverse[target]
   word=(word&0xFFFF0000)|((mapped-j-1)&65535)
  result.append(word)
  if 4*i in refs:relocs[4*j]=[(kind,'D_8008B4A8'if i in(52,60)else name)for kind,name in refs[4*i]]
 return struct.pack('>122I',*result),relocs,order
def normalize_owner():
 raw,refs=payload(out/'selected/candidate.o',NAME);normal,nrefs,order=normalize(raw,refs)
 original=(out/'baseline/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[];at=0
 assert not any(line.startswith(('game_1944C0,'+NAME+',').encode())for line in original.splitlines())
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  omit=i in(64,72,73);replacement=0 if omit else struct.unpack_from('>I',normal,4*at)[0];newrefs=[]if omit else nrefs.get(4*at,[]);insert='';insertrefs=''
  if not omit:
   at+=1
   if at==98:insert='0x%08X'%struct.unpack_from('>I',normal,4*at)[0];insertrefs='R_MIPS_HI16:D_800DD190';at+=1
  spec=lambda values:';'.join(kind+':'+name for kind,name in values)or'-'
  if not omit and w==replacement and refs.get(4*i,[])==newrefs and not insert:continue
  rows.append(dict(filename='game_1944C0',function=NAME,offset='0x%03X'%(4*i),expected='0x%08X'%w,replacement='0x%08X'%replacement,expected_relocations=spec(refs.get(4*i,[])),replacement_relocations=spec(newrefs),
   note='Preserve trig-cache store address, descriptor/head roles and linked two-row end',insert_after=insert,insert_after_relocations=insertrefs,omit='true'if omit else'false'))
 assert at==122
 buf=io.StringIO(newline='');csv.DictWriter(buf,fieldnames=fields).writerows(rows);guards=out/'private-word-patches.csv';guards.write_bytes(original+buf.getvalue().encode())
 where=out/'qualified-owner';where.mkdir(exist_ok=True);obj=where/'game_1944C0.c.o'
 def assemble(text,path):
  p=path.with_suffix('.s');p.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(path),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 assemble(pc.emit_padded_assembly(out/'selected/candidate.o',root/'conker/retail_layout.us.txt','game_1944C0',word_patches_path=guards),obj);assert payload(obj,NAME)==(normal,nrefs)
 truth=out/'original-target.o';assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(out/'baseline/conker/asm/nonmatchings/game_1944C0/func_15167310.s').read_text()+'\n.size '+NAME+',.-'+NAME+'\n',truth)
 target,trefs=payload(truth,NAME);diff=[(i,f'{a:08X}',f'{b:08X}')for i,(a,b)in enumerate(zip(struct.unpack('>122I',normal),struct.unpack('>122I',target)))if a!=b]
 (out/'normalization-differences.json').write_text(json.dumps(dict(words=diff,expected_refs=nrefs,actual_refs=trefs),indent=2)+'\n');assert(normal,nrefs)==(target,trefs),(len(diff),diff[:16])
 assert same_functions(out/'baseline/conker/build/src/game_1944C0.c.o',obj,(NAME,))==41
 result=dict(raw_words=124,retail_words=122,frame=104,guards=len(rows),omissions=3,insertions=1,neighbors=41,all_words_and_named_relocations_equal=True,
  trailing_frame_bytes_original_purpose_unrecovered=16,qualified_object_sha256=sha(obj),source_installed=installed(),matching_credit=0,guard_rows=rows)
 (out/'normalization.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='guard_rows'}),flush=True);return result


"""Actual target Make recipe with the audited SDK and guarded proposal."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
root,out=ROOT,OUT;conker=root/'conker'
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
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
  args=[(out/'proposal/conker'/source).relative_to(conker).as_posix()if a==source else(out/'private-word-patches.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
  if args[0]=='../ido/ido5.3_recomp/cc':args[1:1]=['-I',(out/'proposal/conker/include').relative_to(conker).as_posix()]
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
 assert payload(Path(str(target)+'.compact'),'func_15167310')==payload(out/'selected/candidate.o','func_15167310')
 assert same_functions(out/'baseline/conker/build/src/game_1944C0.c.o',target,('func_15167310',))==41
 assert normalized_pools(target)==normalized_pools(out/'baseline/conker/build/src/game_1944C0.c.o')
 r=dict(actual_Make_commands=len(commands),qualified_complete_owner_equal=True,compact_target_words=124,normalized_words=122,all_41_neighbors_and_pools_fixed=True,qualified_object_sha256=sha(target),source_installed=installed(),matching_credit=0)
 (out/'actual-Make.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r


"""Link every audited header consumer and predict every byte independently."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
root,out=ROOT,OUT;base=out/'baseline'
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.check_game_data_layout import audit_layout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def qualify():
 prepare();inspect_source();replay_make()
 report=json.loads((out/'header-audit.json').read_text());assert report['owners']==305 and not report['changed_auxiliary_symbol_consumers']
 where=out/'image-qualification';where.mkdir(exist_ok=True);script=where/'conker.ld'
 text=(base/'conker/build/conker.ld').read_text()
 for r in report['records']:
  path=out/'qualified-owner/game_1944C0.c.o'if r['source']=='conker/src/game_1944C0.c'else root/r['qualified_object']
  if r['source']!='conker/src/game_1944C0.c':assert sha(path)==r['after_sha256']
  old=r['object'].removeprefix('conker/');assert text.count(old)>=1,old;text=text.replace(old,path.relative_to(root/'conker').as_posix())
 script.write_text(text);image=where/'linked.elf'
 q=subprocess.run(['mips-linux-gnu-ld','-T',script.relative_to(root/'conker').as_posix(),*['-T'+n for n in('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')],'--no-check-sections','--no-warn-mismatch','-o',image.relative_to(root/'conker').as_posix()],cwd=root/'conker',capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before);at=elf_slot_offset(predicted,0x15167310,488);predicted[at:at+488]=(root/'conker/conker.us.bin').read_bytes()[0x1947C0:0x1949A8]
 rows=[(at,r)for at,n,r,_ in symbol_rows(predicted)if n=='func_15167310'];assert len(rows)==1;at,r=rows[0];assert r[1:3]==(0x15167310,12);struct.pack_into('>I',predicted,at+8,488)
 from types import FunctionType
 from tools.experiments import game_actor_state_tick_integration as symbols
 permutations=[('D_800DD1D0','D_80096530'),('func_15002878','D_800E0DFC')]
 predicted=FunctionType(symbols.reorder_symbols.__code__,dict(symbols.reorder_symbols.__globals__,SYMBOL_ORDER=permutations))(predicted)
 actual=image.read_bytes()
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==actual
 assert len(actual)==len(predicted),(len(actual),len(predicted))
 diffs=[i for i,(a,b)in enumerate(zip(actual,predicted))if a!=b]
 (out/'image-differences.json').write_text(json.dumps(dict(count=len(diffs),offsets=diffs[:120]),indent=2)+'\n')
 assert not diffs,('Unpredicted ELF bytes',len(diffs),diffs[:12])
 (where/'predicted.elf').write_bytes(predicted)
 r=dict(strict_predicted_ELF_equal=True,changed_bytes=sum(a!=b for a,b in zip(before,actual)),header_consumers=305,exclusions=0,metadata_permutations=permutations,ELF_sha256=sha(image),protected_data_audit=audit_layout(image,root/'conker'),source_installed=installed(),matching_credit=0)
 (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
