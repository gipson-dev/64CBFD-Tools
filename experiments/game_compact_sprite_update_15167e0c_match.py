"""Compact sprite lifetime/motion: closed roles, complete owner and literal ELF."""
from pathlib import Path
import hashlib,json,os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_compact_sprite_update_15167e0c_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION='func_15167E0C'
root,out=ROOT,OUT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256']}
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
 where=OUT/'selected';before,bd=compile_owner(ROOT,where,MANIFEST['old_source'],'before',('-O2','-g3'));after,ad=compile_owner(ROOT,where,MANIFEST['selected_source'],'candidate',('-O2','-g3'))
 (where/'body.c').write_text(MANIFEST['body'])
 assert same_functions(before,after,(FUNCTION,))==41 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 result=normalize_owner();assert result['guards']==38 and result['neighbors']==41
 assert sha(OUT/'private-word-patches.csv')==MANIFEST['guards_sha256']and sha(OUT/'qualified-owner/game_1944C0.c.o')==MANIFEST['padded_sha256']
 return result

"""Bijective fixed-point load schedule and closed compiler register roles."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
root,out=ROOT,OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
NAME='func_15167E0C';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rename(w,m):
 op=w>>26
 if op in(2,3):return w
 shifts=(21,16,11)if op==0 else(16,)if op==15 else(21,16);result=w
 for shift in shifts:result=(result&~(31<<shift))|(m.get(w>>shift&31,w>>shift&31)<<shift)
 return result
def fields(w,rs=None,rt=None,rd=None):
 for shift,value in((21,rs),(16,rt),(11,rd)):
  if value is not None:w=(w&~(31<<shift))|(value<<shift)
 return w
def normalize(raw,refs):
 assert hashlib.sha256(raw).hexdigest()=='769368be309fa38aef2884b9af49ee8e64b4833a69f446ca609dc09385cbd4c2'
 a=list(struct.unpack('>195I',raw));assert a[0]==0x27BDFFE0
 order=list(range(62))+[66,63,73,67,68,69,70,71,72,64,62,75,74,65,82,76,77,78,79,80,81]+list(range(83,195));assert sorted(order)==list(range(195))
 mappings={50:{14:2},51:{24:15},54:{9:25},55:{25:24},56:{14:2,15:14},57:{3:2,15:14,24:15},58:{25:24,9:25},59:{14:13},60:{11:3},61:{13:12},63:{11:3,12:11},73:{12:11,13:12},69:{2:10,10:9},70:{10:9},71:{2:10},72:{15:14},64:{11:10},62:{25:2},75:{14:13,15:14},74:{10:9},65:{25:2,9:25},82:{9:25,10:9,3:2},78:{2:24,24:15},79:{24:15},80:{2:24},81:{12:11},83:{11:10,12:11},86:{2:13,13:12},87:{13:12},89:{2:13}}
 result=[];newrefs={}
 for j,i in enumerate(order):
  word=rename(a[i],mappings.get(i,{}))
  if i in(40,44):
   assert a[i]&65535==31;word=(a[i]&0xFFFF0000)|27
  if i==68:assert a[i]==0x00651021;word=fields(a[i],rs=2,rt=5,rd=10)
  if i==77:assert a[i]==0x00651021;word=fields(a[i],rs=3,rt=5,rd=24)
  if i==85:assert a[i]==0x00651021;word=fields(a[i],rs=2,rt=5,rd=13)
  result.append(word)
  if i*4 in refs:newrefs[j*4]=refs[i*4]
 return struct.pack('>195I',*result),newrefs,order
def normalize_owner():
 raw,refs=payload(out/'selected/candidate.o',NAME);normal,nrefs,order=normalize(raw,refs)
 original=(out/'baseline/conker/retail_word_patches.us.csv').read_bytes();columns=next(csv.reader(io.StringIO(original.decode())));rows=[]
 assert not any(v.startswith(('game_1944C0,'+NAME+',').encode())for v in original.splitlines())
 for i,((old,),(word,))in enumerate(zip(struct.iter_unpack('>I',raw),struct.iter_unpack('>I',normal))):
  if old==word and refs.get(i*4,[])==nrefs.get(i*4,[]):continue
  spec=lambda vs:';'.join(k+':'+n for k,n in vs)or'-'
  rows.append(dict(filename='game_1944C0',function=NAME,offset='0x%03X'%(4*i),expected='0x%08X'%old,replacement='0x%08X'%word,expected_relocations=spec(refs.get(4*i,[])),replacement_relocations=spec(nrefs.get(4*i,[])),note='Normalize compact sprite fixed-point schedule and closed register roles; completion byte home 1F to 1B',insert_after='',insert_after_relocations='',omit='false'))
 buf=io.StringIO(newline='');csv.DictWriter(buf,fieldnames=columns).writerows(rows);guards=out/'private-word-patches.csv';guards.write_bytes(original+buf.getvalue().encode())
 where=out/'qualified-owner';where.mkdir(exist_ok=True);obj=where/'game_1944C0.c.o'
 def assemble(text,path):
  src=path.with_suffix('.s');src.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(path),str(src)],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 assemble(pc.emit_padded_assembly(out/'selected/candidate.o',root/'conker/retail_layout.us.txt','game_1944C0',word_patches_path=guards),obj);assert payload(obj,NAME)==(normal,nrefs)
 truth=out/'original-target.o';assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(out/'baseline/conker/asm/nonmatchings/game_1944C0/func_15167E0C.s').read_text()+'\n.size '+NAME+',.-'+NAME+'\n',truth)
 target,trefs=payload(truth,NAME);diff=[(i,f'{x:08X}',f'{y:08X}')for i,(x,y)in enumerate(zip(struct.unpack('>195I',normal),struct.unpack('>195I',target)))if x!=y]
 (out/'normalization-differences.json').write_text(json.dumps(dict(words=diff,refs_equal=nrefs==trefs),indent=2)+'\n');assert(normal,nrefs)==(target,trefs),(len(diff),diff[:12])
 assert same_functions(out/'baseline/conker/build/src/game_1944C0.c.o',obj,(NAME,))==41
 r=dict(raw_words=195,retail_words=195,frame=32,guards=len(rows),omissions=0,insertions=0,neighbors=41,raw_completion_byte_home=31,retail_completion_byte_home=27,
  all_words_and_named_relocations_equal=True,qualified_object_sha256=sha(obj),source_installed=installed(),matching_credit=0,guard_rows=rows)
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
  args=[(out/'selected/selected-owner.c').relative_to(conker).as_posix()if a==source else(out/'private-word-patches.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
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
 assert payload(Path(str(target)+'.compact'),'func_15167E0C')==payload(out/'selected/candidate.o','func_15167E0C')
 assert same_functions(out/'baseline/conker/build/src/game_1944C0.c.o',target,('func_15167E0C',))==41
 assert normalized_pools(target)==normalized_pools(out/'baseline/conker/build/src/game_1944C0.c.o')
 r=dict(actual_Make_commands=len(commands),qualified_complete_owner_equal=True,compact_target_words=195,normalized_words=195,all_41_neighbors_and_pools_fixed=True,qualified_object_sha256=sha(target),source_installed=installed(),matching_credit=0)
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
 before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before);at=elf_slot_offset(predicted,0x15167E0C,780);predicted[at:at+780]=(root/'conker/conker.us.bin').read_bytes()[0x1952BC:0x1955C8]
 rows=[(at,r)for at,n,r,_ in symbol_rows(predicted)if n=='func_15167E0C'];assert len(rows)==1;at,r=rows[0];assert r[1:3]==(0x15167E0C,12);struct.pack_into('>I',predicted,at+8,780)
 actual=image.read_bytes()
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==actual
 assert actual==predicted,('Unexpected image bytes',sum(a!=b for a,b in zip(actual,predicted)),len(actual)-len(predicted))
 (where/'predicted.elf').write_bytes(predicted)
 r=dict(strict_predicted_ELF_equal=True,changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,metadata_permutations=[],ELF_sha256=sha(image),protected_data_audit=audit_layout(image,root/'conker'),source_installed=installed(),matching_credit=0)
 (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
