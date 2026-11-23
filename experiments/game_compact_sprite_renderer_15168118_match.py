"""Compact sprite renderer: source origins, SDK32, complete callers and literal ELF."""
from pathlib import Path
import hashlib,json,os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_compact_sprite_renderer_15168118_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION='func_15168118'
r,o=ROOT,OUT;b=o/'baseline'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():
 live=sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
 assert (sha(ROOT/MANIFEST['caller_source'])==MANIFEST['selected_caller_sha256'])==live
 return live
def prepare():
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['caller_source']:MANIFEST['selected_caller_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256']}
 for n,d in MANIFEST['inputs'].items():
  frozen=OUT/'baseline'/n
  if frozen.exists():assert sha(frozen)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 for n,d in MANIFEST['additional_inputs'].items():assert sha(ROOT/n)==sha(OUT/'additional-baseline'/n)==d,n
 assert sha(TOOLROOT/'experiments/game_compact_sprite_renderer_15168118_role_plan.json')==MANIFEST['role_plan_sha256']
 return live
def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 where=OUT/'selected-v2'
 for old,new,label,exclude,neighbors in((MANIFEST['old_source'],MANIFEST['selected_source'],'candidate',(FUNCTION,),41),(MANIFEST['old_caller'],MANIFEST['selected_caller'],'caller',(),11)):
  before,bd=compile_owner(ROOT,where,old,'before-'+label,('-O2','-g3'));after,ad=compile_owner(ROOT,where,new,label,('-O2','-g3'))
  assert same_functions(before,after,exclude)==neighbors and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 (where/'body.c').write_text(MANIFEST['body']);(where/'selected-owner.c').write_text(MANIFEST['selected_source']);(where/'selected-caller-owner.c').write_text(MANIFEST['selected_caller'])
 bad=MANIFEST['selected_caller'].replace('(Gfx *)cursor, state, view','(Gfx *)cursor, visibilityOwner, view');assert bad!=MANIFEST['selected_caller']
 compile_owner(ROOT,where,bad,'wrong-record',('-O2','-g3'))
 source='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(OUT/'baseline/conker/asm/nonmatchings/game_1944C0/func_15168118.s').read_text()
 if '.size func_15168118'not in source:source+='\n.size func_15168118,.-func_15168118\n'
 assemble(source,OUT/'original-target.o')
 result=normalize_owner();assert result['guards']==201 and result['neighbors']==41
 assert sha(OUT/'private-word-patches.csv')==MANIFEST['guards_sha256']and sha(OUT/'qualified-owner/game_1944C0.c.o')==MANIFEST['padded_sha256']
 return result

"""Private renderer copy coalescing, register roles and local-object schedule.

The transform preserves every non-copy instruction origin and its opcode,
constant and named binding. Branch labels follow source edges through the
copy removal and schedule, with one proved pure-address-prefix hoist.
"""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
r,o=ROOT,OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_compact_sprite_renderer_15168118_roles import transform,branch,registers
NAME='func_15168118';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SLOTS={143:139,142:86,141:87,144:148,146:150,148:152,150:154,152:156,157:161}
def normalize(raw,refs):
 plan=json.loads((TOOLROOT/'experiments/game_compact_sprite_renderer_15168118_role_plan.json').read_text());assert hashlib.sha256(raw).hexdigest()==plan['raw_sha256']
 trace=json.loads((o/'origin-trace-all.json').read_text());assert trace['cases']==2970 and not trace['different_origins']
 fixed,frels,keep,proof,edges=transform(raw,refs);coalesced=struct.unpack('>337I',fixed);position={old:new for new,old in enumerate(keep)}
 order=plan['order'];assert len(order)==len(set(order))==337 and set(order)==set(keep)
 out_position={old:new for new,old in enumerate(order)};source_edges={v['origin']:v['target']for v in edges}
 # Only one jump enters a block whose leading pure stack-address expression
 # has moved to the preceding common branch delay slot. Both image paths
 # execute that definition, and its register is untouched until the argument.
 differing=[v for v in plan['branch_edges']if v['source_target_reordered']]
 assert differing==[dict(source=33,retail=34,old_target=40,new_target=41,target_origin=41,source_target_reordered=True)]
 result=[];newrefs={}
 for j,i in enumerate(order):
  w=coalesced[position[i]];before=w;entry=plan['fields'][str(i)];op=w>>26;rs=w>>21&31
  for edit in entry['registers']:
   shift=edit['shift'];value=edit['value'];assert shift in(6,11,16,21)and 0<=value<32
   if shift==21:assert op not in(2,3,17)
   if shift in(6,11):assert op in(0,17)
   w=(w&~(31<<shift))|value<<shift
  if branch(before):
   # Derive labels from the source CFG, never from replacement target bytes.
   destination=source_edges[i]
   if i==33:assert destination==40;destination=41
   delta=out_position[destination]-j-1;assert -32768<=delta<=32767
   assert delta&65535==entry['immediate'],('Unexpected source-edge change',i,j)
   w=(w&0xFFFF0000)|(delta&65535)
  elif op==9 and rs==29 or op in(0x20,0x21,0x23,0x24,0x25,0x28,0x29,0x2B,0x31,0x39)and rs==29:
   old=before&65535;new=SLOTS.get(old,old)
   assert entry['immediate']is None or entry['immediate']==new
   w=(w&0xFFFF0000)|new
  else:assert entry['immediate']is None
  assert w>>26==before>>26
  if op in(0,17):assert w&63==before&63
  result.append(w)
  if position[i]*4 in frels:newrefs[j*4]=frels[position[i]*4]
 assert result[:7]==list(coalesced[:7])and result[0]==0x27BDFF58
 # Retail sync address: common branch delay definition, no intervening use
 # or write before its outgoing-argument store (itself a call delay word).
 assert result[32]==0x27AA008B and result[50]==0xAFAA0024
 assert all(10 not in set.union(*registers(w))for w in result[33:50])
 return struct.pack('>337I',*result),newrefs,order
def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(src)],capture_output=True,text=True)
 assert q.returncode==0,q.stdout+q.stderr
def normalize_owner():
 raw,refs=payload(o/'selected-v2/candidate.o',NAME);normal,nrefs,order=normalize(raw,refs)
 target,trefs=payload(o/'original-target.o',NAME);assert(normal,nrefs)==(target,trefs)
 original=(o/'baseline/conker/retail_word_patches.us.csv').read_bytes();columns=next(csv.reader(io.StringIO(original.decode())));rows=[];at=0;omits={193,218,241,263}
 assert not any(v.startswith(('game_1944C0,'+NAME+',').encode())for v in original.splitlines())
 spec=lambda values:';'.join(kind+':'+name for kind,name in values)or'-'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  omit=i in omits;word=0 if omit else struct.unpack_from('>I',normal,4*at)[0];newrefs=[]if omit else nrefs.get(4*at,[])
  if not omit:at+=1
  if not omit and w==word and refs.get(4*i,[])==newrefs:continue
  rows.append(dict(filename='game_1944C0',function=NAME,offset='0x%03X'%(4*i),expected='0x%08X'%w,replacement='0x%08X'%word,expected_relocations=spec(refs.get(4*i,[])),replacement_relocations=spec(newrefs),note='Normalize compact sprite renderer register roles, private-object homes and independent schedule; coalesce four proved argument copies',insert_after='',insert_after_relocations='',omit='true'if omit else'false'))
 assert at==337
 buf=io.StringIO(newline='');csv.DictWriter(buf,fieldnames=columns).writerows(rows);guards=o/'private-word-patches.csv';guards.write_bytes(original+buf.getvalue().encode())
 where=o/'qualified-owner';where.mkdir(exist_ok=True);obj=where/'game_1944C0.c.o'
 assemble(pc.emit_padded_assembly(o/'selected-v2/candidate.o',r/'conker/retail_layout.us.txt','game_1944C0',word_patches_path=guards),obj)
 assert payload(obj,NAME)==(target,trefs)
 assert same_functions(o/'baseline/conker/build/src/game_1944C0.c.o',obj,(NAME,))==41
 report=dict(raw_words=341,retail_words=337,frame=168,guards=len(rows),omissions=4,insertions=0,all_337_remaining_instruction_origins_once=True,no_origin_opcode_constant_or_named_binding_substitution=True,all_branch_labels_derived_from_source_edges_and_one_pure_prefix_hoist=True,neighbors=41,all_words_and_named_relocations_equal=True,qualified_object_sha256=sha(obj),source_installed=installed(),matching_credit=0,guard_rows=rows)
 (o/'normalization.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='guard_rows'}),flush=True);return report


"""Replay both real Make recipes in private output directories."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
r,o=ROOT,OUT
c=r/'conker'
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def build(source,selected,label,expected,compact,function,neighbors):
 shadow=o/('make-'+label);target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
 q=subprocess.run(['make','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()],cwd=c,capture_output=True,text=True,check=True)
 (o/('actual-Make-'+label+'-plan.txt')).write_text(q.stdout+q.stderr);commands=[];diagnostics=[]
 for line in q.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
  args=[selected.relative_to(c).as_posix()if a==source else(o/'private-word-patches.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
  args=[str(TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else a for a in args]
  redirect=None
  if'>'in args:
   assert args[-2]=='>'and args.count('>')==1;redirect=(c/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  p=subprocess.run(args,cwd=c,capture_output=True,text=True);assert p.returncode==0,(args,p.stdout,p.stderr)
  if redirect:redirect.write_text(p.stdout)
  else:diagnostics.append(p.stdout+p.stderr)
  commands.append(args)
 (o/('actual-Make-'+label+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n');(o/('actual-Make-'+label+'-diagnostics.txt')).write_text(''.join(diagnostics))
 assert target.read_bytes()==expected.read_bytes(),('Whole padded owner changed',label,sha(target),sha(expected))
 assert payload(Path(str(target)+'.compact'),function)==payload(compact,function)
 baseline=o/'baseline/conker/build'/Path(source+'.o')
 if not baseline.is_file():baseline=o/'additional-baseline/conker/build'/Path(source+'.o')
 assert same_functions(baseline,target,(function,))==neighbors
 assert normalized_pools(target)==normalized_pools(baseline)
 return dict(commands=len(commands),complete_padded_owner_equal=True,all_neighbors_and_pools_fixed=neighbors,sha256=sha(target),object=str(target.relative_to(o)))
def replay_make():
 a=build('src/game_1944C0.c',o/'selected-v2/selected-owner.c','renderer',o/'qualified-owner/game_1944C0.c.o',o/'selected-v2/candidate.o','func_15168118',41)
 b=build('src/game/generated_1A5440.c',o/'selected-v2/selected-caller-owner.c','caller',o/'additional-baseline/conker/build/src/game/generated_1A5440.c.o',o/'selected-v2/caller.o','func_15178750',10)
 report=dict(renderer=a,caller=b,source_installed=installed(),matching_credit=0)
 (o/'actual-Make-owners.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


"""Independent entire-ELF prediction including the repaired caller owner."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct,subprocess,sys
r,o=ROOT,OUT
b=o/'baseline'
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.check_game_data_layout import audit_layout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PERMUTATIONS=[(['D_800A6CA4','D_800A2674'],['D_800A2674','D_800A6CA4']),(['D_800A6CA0','D_800A2670','D_800AAB38'],['D_800A2670','D_800AAB38','D_800A6CA0']),(['D_8009053C','D_80098CDC'],['D_80098CDC','D_8009053C'])]
def predict_metadata(blob):
 at=struct.unpack_from('>I',blob,32)[0];size,count,names=struct.unpack_from('>HHH',blob,46)
 headers=[struct.unpack_from('>10I',blob,at+i*size)for i in range(count)];h=headers[names];pool=blob[h[4]:h[4]+h[5]]
 strings=[v for v in headers if pool[v[0]:].split(b'\0',1)[0]==b'.strtab'];assert len(strings)==1
 rows=symbol_rows(blob);symbols={n:(p,v)for p,n,v,_ in rows if n};touched=0
 for old,new in PERMUTATIONS:
  assert set(old)==set(new)and len(old)==len(set(old));first,row=symbols[old[0]];start=row[0];end=start
  for i,n in enumerate(old):
   p,v=symbols[n];assert p==first+16*i and v[0]==end;end+=len(n)+1
  assert{n for _,n,v,_ in rows if start<=v[0]<end}==set(old)
  p=strings[0][4]+start;before=b''.join(n.encode()+b'\0'for n in old);after=b''.join(n.encode()+b'\0'for n in new)
  assert len(before)==len(after)and blob[p:p+len(before)]==before;blob[p:p+len(before)]=after;offset=start
  for i,n in enumerate(new):
   v=symbols[n][1];struct.pack_into('>IIIBBH',blob,first+16*i,offset,*v[1:]);offset+=len(n)+1
  touched+=len(before)
 return touched
def qualify():
 prepare();inspect_source();replay_make()
 for n,d in json.loads((o/'additional-inputs.json').read_text()).items():assert sha(r/n)==sha(o/'additional-baseline'/n)==d,n
 checked=json.loads((o/'actual-Make-owners.json').read_text());assert checked['renderer']['complete_padded_owner_equal']and checked['caller']['complete_padded_owner_equal']
 where=o/'image-qualification';where.mkdir(exist_ok=True);script=where/'conker.ld';text=(b/'conker/build/conker.ld').read_text()
 for old,obj in(('build/src/game_1944C0.c.o',o/'qualified-owner/game_1944C0.c.o'),('build/src/game/generated_1A5440.c.o',o/'make-caller/src/game/generated_1A5440.c.o')):
  assert text.count(old)==1,(old,text.count(old));text=text.replace(old,obj.relative_to(r/'conker').as_posix())
 script.write_text(text);image=where/'linked.elf'
 q=subprocess.run(['mips-linux-gnu-ld','-T',script.relative_to(r/'conker').as_posix(),*['-T'+n for n in('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')],'--no-check-sections','--no-warn-mismatch','-o',image.relative_to(r/'conker').as_posix()],cwd=r/'conker',capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 before=(b/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before);at=elf_slot_offset(predicted,0x15168118,1348)
 predicted[at:at+1348]=(r/'conker/conker.us.bin').read_bytes()[0x1955C8:0x195B0C]
 rows=[(p,v)for p,n,v,_ in symbol_rows(predicted)if n=='func_15168118'];assert len(rows)==1;p,v=rows[0];assert v[1:3]==(0x15168118,12);struct.pack_into('>I',predicted,p+8,1348)
 before_metadata=bytes(predicted);touched=predict_metadata(predicted)
 assert Counter((n,*v[1:])for _,n,v,_ in symbol_rows(before_metadata))==Counter((n,*v[1:])for _,n,v,_ in symbol_rows(predicted))
 actual=image.read_bytes()
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==actual
 diff=[i for i,(x,y)in enumerate(zip(actual,predicted))if x!=y]
 (o/'unexpected-image-bytes.json').write_text(json.dumps(dict(bytes=len(diff),length_difference=len(actual)-len(predicted),first_offsets=diff[:40]),indent=2)+'\n')
 assert actual==predicted,('Unexpected full-image bytes',len(diff),len(actual)-len(predicted),diff[:12])
 (where/'predicted.elf').write_bytes(predicted)
 report=dict(strict_predicted_ELF_equal=True,changed_bytes=sum(x!=y for x,y in zip(before,actual)),exclusions=0,metadata_permutations=PERMUTATIONS,metadata_symbol_records=7,metadata_string_bytes=touched,metadata_changed_bytes=sum(x!=y for x,y in zip(before_metadata,predicted)),entire_named_symbol_definition_multiset_preserved=True,ELF_sha256=sha(image),caller_owner_byte_identical=True,protected_data_audit=audit_layout(image,r/'conker'),source_installed=installed(),matching_credit=0)
 (o/'image-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
