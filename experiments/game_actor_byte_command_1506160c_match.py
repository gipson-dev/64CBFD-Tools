"""Actor byte-command source, shared-header closure and literal-image gates."""
from pathlib import Path
import hashlib,json,os,shutil,struct,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_actor_byte_command_1506160c_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION='func_1506160C'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def installed():return all((ROOT/n).is_file()and sha(ROOT/n)==d for n,d in MANIFEST['proposals'].items())

def prepare():
 live=installed();objects={r['object']:r for r in json.loads((OUT/'header-audit.json').read_text())['records']}
 for n,d in MANIFEST['inputs'].items():
  frozen=OUT/'baseline'/n
  if frozen.exists():assert sha(frozen)==d,('Frozen baseline changed',n)
  if live and n in objects:continue # Every retained byte/binding checked below.
  expected=MANIFEST['proposals'].get(n,d)if live else d
  if live and n=='conker/build/conker.us.elf':expected=MANIFEST['ELF_sha256']
  assert sha(ROOT/n)==expected,('Input changed',n)
 for n,d in MANIFEST['proposals'].items():assert sha(OUT/'proposal'/n)==d,n
 for n,d in MANIFEST['receipts'].items():assert sha(OUT/n)==d,('Reused receipt changed',n)
 return live

def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.experiments.game_path_heading_turn_roles import bound_blob
 from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 results=[]
 for label,source in [('before',MANIFEST['old_source']),('after',MANIFEST['proposal_texts'][MANIFEST['source']])]:
  where=OUT/'fresh-owner'/label;where.mkdir(parents=True,exist_ok=True)
  for name in ('functions.h','variables.h'):
   p=OUT/('proposal'if label=='after'else'baseline')/'conker/include'/name
   (where/('packet-'+name)).write_bytes(p.read_bytes())
   source=source.replace('#include "'+name+'"','#include "packet-'+name+'"')
  if label=='after':(where/'actor_commands.h').write_text(MANIFEST['proposal_texts']['conker/include/actor_commands.h'])
  results.append(compile_owner(ROOT,where,source,'owner'))
 (before,bd),(after,ad)=results
 assert same_functions(before,after,(FUNCTION,))==88
 assert diagnostic_rows(bd)==diagnostic_rows(ad)and normalized_pools(before)==normalized_pools(after)
 raw,refs=payload(after,FUNCTION);assert len(raw)==432
 assert hashlib.sha256(raw).hexdigest()=='634bdc6aa824905d87a4429a8d66f26c5c5853fc63488d232d975412e505dbd6'
 symbols={n:r[1]for _,n,r,_ in symbol_rows((OUT/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 assert bound_blob(raw,refs,symbols)==list(struct.unpack_from('>108I',(ROOT/'conker/conker.us.bin').read_bytes(),0x8EABC))
 return dict(words=108,frame=0,guards=0,neighbors=88,pools_equal=True,diagnostics_equal=True)

def audit_headers():
 from tools.experiments.game_channel_command_poller_header_audit import audit_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 report=json.loads((OUT/'header-audit.json').read_text());assert report['owners']==214
 live=installed()
 for row in report['records']:
  before=OUT/'baseline'/row['object'];after=ROOT/row['qualified_object']
  assert sha(before)==row['before_sha256']and sha(after)==row['after_sha256']
  if row['source']==MANIFEST['source']:assert same_functions(before,after,(FUNCTION,))==88
  else:assert json.loads(json.dumps(audit_owner(before,after)))=={k:v for k,v in row.items()if k not in ('source','object','qualified_object','before_sha256','after_sha256','commands')},row['source']
  if live:
   actual=ROOT/row['object']
   if row['source']==MANIFEST['source']:assert actual.read_bytes()==after.read_bytes()
   else:
    comparison=audit_owner(after,actual);assert not any(comparison['symbol_changes'].values())
    assert all(r['section']=='.mdebug'for r in comparison['changed_sections']),row['source']
 assert sum(r['commands']for r in report['records'])==692
 return dict(owners=214,fingerprinted_recipe_receipts_reused=214,fresh_structural_audits=214,production_objects_checked=live)

"""Link every qualified shared-header object; compare a literal independent ELF."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
root,out=ROOT,OUT;base=out/'baseline'
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_actor_classifier_candidates import ELF_HEADER,SECTION_HEADER,read_c_string
from tools.check_game_data_layout import audit_layout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def qualify():
 prepare();inspect_source();audit_headers()
 report=json.loads((out/'header-audit.json').read_text());scope=json.loads((out/'header-scope.json').read_text());assert report['owners']==scope['owners']==214
 metadata=json.loads((out/'baseline-metadata-proof.json').read_text());assert metadata['stale_consumers']==6 and metadata['unchanged_original_live_headers_reproduce_preexisting_metadata_changes']
 stale={r['source']for r in metadata['records']}
 known_sizes={'D_800A5770':(4,8),'D_800CC298':(4,0),'D_800DBFF4':(0,4),'D_800E0950':(1,20),'D_800BE358':(8,128)}
 ld=(base/'conker/build/conker.ld').read_text();assert '/DISCARD/ :'in ld and '*(*);'in ld
 symbol_changes=[]
 for row in report['records']:
  before=base/row['object'];after=root/row['qualified_object'];assert sha(before)==row['before_sha256']and sha(after)==row['after_sha256']
  old=row['object'].removeprefix('conker/');new=row['qualified_object'].removeprefix('conker/');assert old in ld,old;ld=ld.replace(old,new)
  if row['source']=='conker/src/game_83300.c':continue
  changes=row['symbol_changes']
  if changes['removed']or changes['added']:
   assert row['source']in stale|{'conker/src/debugger_258ED0.c'}
   old={r[0]:r[1:]for r in changes['removed']};new={r[0]:r[1:]for r in changes['added']}
   assert set(old)<=set(known_sizes)and set(new)-set(old)<= {'D_8008B37C'}
   for name,fields in old.items():
    a,b=known_sizes[name];assert fields==[0,a,16,0,0]and new[name]==[0,b,16,0,0],(row['source'],name,fields,new[name])
   if 'D_8008B37C'in new:assert new['D_8008B37C']==[0,0,16,0,0]
   symbol_changes.append(row['source'])
 where=out/'image-qualification';where.mkdir(exist_ok=True);script=where/'conker.ld';script.write_text(ld);image=where/'linked.elf'
 q=subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(image.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,text=True)
 assert q.returncode==0,q.stdout+q.stderr
 before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
 at=elf_slot_offset(predicted,0x1506160C,432);predicted[at:at+432]=(root/'conker/conker.us.bin').read_bytes()[0x8EABC:0x8EC6C]
 rows=symbol_rows(predicted);symbols={n:(at,r)for at,n,r,_ in rows if n}
 at,r=symbols['func_1506160C'];assert r[1:3]==(0x1506160C,24);struct.pack_into('>I',predicted,at+8,432)
 # The existing undefined-symbol linker scripts assign these addresses
 # absolutely. GNU ld retains zero-size SHN_ABS metadata regardless of the
 # corrected input-object extern sizes; no final ELF symbol edit is needed.
 for name in(*known_sizes,'D_8008B37C'):
  _,r=symbols[name];assert r[1:]==(int(name[2:],16),0,16,0,65521),(name,r)
 permutations=json.loads((out/'metadata-permutations.json').read_text())if(out/'metadata-permutations.json').exists()else[]
 header=ELF_HEADER.unpack_from(predicted);hh=[SECTION_HEADER.unpack_from(predicted,header[6]+i*header[11])for i in range(header[12])]
 nh=hh[header[13]];names=predicted[nh[4]:nh[4]+nh[5]];st=[h for h in hh if read_c_string(names,h[0])=='.strtab'];assert len(st)==1
 for old,new in permutations:
  assert set(old)==set(new)and len(set(old))==len(old);first,r=symbols[old[0]];start=offset=r[0]
  for i,n in enumerate(old):
   a,r=symbols[n];assert a==first+16*i and r[0]==offset;offset+=len(n)+1
  assert {n for _,n,r,_ in rows if start<=r[0]<offset}==set(old)
  a=st[0][4]+start;oldbytes=b''.join(n.encode()+b'\0'for n in old);newbytes=b''.join(n.encode()+b'\0'for n in new)
  assert len(oldbytes)==len(newbytes)and predicted[a:a+len(oldbytes)]==oldbytes;predicted[a:a+len(oldbytes)]=newbytes;offset=start
  for i,n in enumerate(new):struct.pack_into('>IIIBBH',predicted,first+16*i,offset,*symbols[n][1][1:]);offset+=len(n)+1
 actual=image.read_bytes();assert len(actual)==len(predicted)
 if installed():assert (root/'conker/build/conker.us.elf').read_bytes()==actual
 diffs=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b];(where/'unpredicted-differences.json').write_text(json.dumps(diffs)+'\n')
 if diffs:
  changed=[dict(index=i,before=a[1],after=b[1])for i,(a,b)in enumerate(zip(rows,symbol_rows(actual)))if a[1]!=b[1]]
  (out/'metadata-order-observation.json').write_text(json.dumps(changed,indent=2)+'\n')
 assert not diffs,('Unexpected complete-image differences',len(diffs),diffs[:12])
 (where/'predicted.elf').write_bytes(predicted)
 r=dict(words=108,frame=0,direct_target_guards=0,qualified_header_consumers=214,all_other_loaded_code_data_and_bindings_fixed=True,
  actual_Make_commands=sum(r['commands']for r in report['records']),strict_predicted_ELF_equal=True,
  changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,
  object_gate_symbol_size_change=[0,4],linked_absolute_gate_metadata_unchanged=True,discarded_debug_metadata_consumers=symbol_changes,metadata_permutations=permutations,
  ELF_sha256=sha(image),protected_data_audit=audit_layout(image,root/'conker'),source_installed=installed(),matching_credit=0)
 (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
