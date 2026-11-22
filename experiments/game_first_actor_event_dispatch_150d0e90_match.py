"""Direct first-actor event dispatcher, complete owner and strict image gates."""
from pathlib import Path
import hashlib,json,os,sys,struct
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_first_actor_event_dispatch_150d0e90_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];root,out=ROOT,OUT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
norm=lambda b:b.replace(b'\r\n',b'\n')
def installed():return norm((ROOT/MANIFEST['source']).read_bytes())==MANIFEST['selected_source'].encode()
def prepare():
 for n,h in MANIFEST['inputs'].items():
  if(OUT/'baseline'/n).exists():assert sha(OUT/'baseline'/n)==h,('frozen baseline changed',n)
  permitted={h}
  if n==MANIFEST['source']:permitted.add(MANIFEST['selected_sha256'])
  if n==MANIFEST['object']:permitted.add(MANIFEST['padded_sha256'])
  if n=='conker/build/conker.us.elf':permitted.add(MANIFEST['predicted_ELF_sha256'])
  assert sha(ROOT/n)in permitted,n
 return installed()
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
SOURCE='conker/src/game/generated_FDD70.c';FUNCTION='func_150D0E90';ENTRY=0x150D0E90;ROM=0xFE340;WORDS=149

def inspect_source():
 where=out/'qualified-source';where.mkdir(exist_ok=True)
 old=(out/'baseline'/SOURCE).read_text();source=MANIFEST['selected_source']
 a,ad=compile_owner(root,where,old,'before');b,bd=compile_owner(root,where,source,'candidate')
 assert diagnostic_rows(ad)==diagnostic_rows(bd),(diagnostic_rows(ad),diagnostic_rows(bd))
 assert normalized_pools(a)==normalized_pools(b)
 neighbors=same_functions(a,b,(FUNCTION,));assert neighbors==4
 raw,refs=payload(b,FUNCTION)
 symbols={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 ws=bound_blob(raw,refs,symbols)
 truth=list(struct.unpack_from('>149I',(root/'conker/conker.us.bin').read_bytes(),ROM))
 assert ws==truth
 assert hashlib.sha256(raw).hexdigest()=='338c78d9dd633b6c0a34a71d78d8056da450e0d30383b880ef8744d7b52e6dd9'
 r=dict(words=len(ws),frame=65536-(ws[0]&65535),differences=0,guards=0,unchanged_neighbors=neighbors,
        relocation_sites=len(refs),bindings=refs,raw_sha256=hashlib.sha256(raw).hexdigest(),
        pools_identical=True,diagnostics_unchanged=True,source_installed=False,matching_credit=0)
 (out/'raw-qualification.json').write_text(json.dumps(r,indent=2)+'\n')
 (out/'program.json').write_text(json.dumps(ws)+'\n')
 (where/'selected-owner.c').write_text(source)
 print(json.dumps({k:v for k,v in r.items()if k!='bindings'}),flush=True);return r

"""Natural Make, exact owner/padding, and a literal independently predicted ELF."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,shutil,struct,subprocess,sys
root,out=ROOT,OUT
screen=sys.modules[__name__]
from tools import pad_generated_object as pg
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments import game_list_owner_make as route
from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_classifier_candidates import ELF_HEADER,SECTION_HEADER,read_c_string
base=out/'baseline';where=out/'image-qualification';where.mkdir(exist_ok=True)
SOURCE=screen.SOURCE;FUNCTION=screen.FUNCTION;OBJECT='conker/build/src/game/generated_FDD70.c.o'

def assemble(name,text):
 p=where/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,text=True)
 assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr);return obj

def qualify():
 prepare();inspect_source();compact=out/'qualified-source/candidate.o';guards=base/'conker/retail_word_patches.us.csv'
 assert guards.read_bytes()==(root/'conker/retail_word_patches.us.csv').read_bytes()
 full=(root/'conker/asm/FDD70.s').read_text();body='glabel '+FUNCTION+full.split('glabel '+FUNCTION,1)[1].split('endlabel '+FUNCTION,1)[0]+'endlabel '+FUNCTION
 truth=assemble('retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+body+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
 padded=assemble('padded',pg.emit_padded_assembly(compact,root/'conker/asm/FDD70.s',filename='generated_FDD70',word_patches_path=guards))
 assert payload(padded,FUNCTION)==payload(truth,FUNCTION)==payload(compact,FUNCTION)
 assert same_functions(base/OBJECT,padded,(FUNCTION,))==4
 old=pg.parse_object(base/OBJECT);new=pg.parse_object(padded)
 for n,f in old[1].items():
  expected=dict(f)
  if n==FUNCTION:expected['size']=596
  assert new[1][n]==expected,(n,f,new[1][n])
 selected=MANIFEST['selected_source']
 (where/'after-diagnostics.txt').write_text((out/'qualified-source/candidate-diagnostics.txt').read_text())
 make=route.actual_Make(root,where,padded,compact,guards,SOURCE,OBJECT,selected,'target',5)
 owner=where/'qualified-owner/generated_FDD70.c.o';owner.parent.mkdir(exist_ok=True);shutil.copyfile(padded,owner)
 with patch.multiple(linker,FILENAME='generated_FDD70',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
  image=linker.link_image(root,where,owner,'image')
 before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
 at=elf_slot_offset(predicted,screen.ENTRY,596);predicted[at:at+596]=(root/'conker/conker.us.bin').read_bytes()[screen.ROM:screen.ROM+596]
 matches=[(at,row)for at,n,row,_ in symbol_rows(predicted)if n==FUNCTION];assert len(matches)==1
 at,row=matches[0];assert row[1:3]==(screen.ENTRY,12);struct.pack_into('>I',predicted,at+8,596)
 permutations=json.loads((out/'metadata-permutations.json').read_text())if(out/'metadata-permutations.json').exists()else[]
 header=ELF_HEADER.unpack_from(predicted);headers=[SECTION_HEADER.unpack_from(predicted,header[6]+i*header[11])for i in range(header[12])]
 name_header=headers[header[13]];names=predicted[name_header[4]:name_header[4]+name_header[5]]
 string_headers=[h for h in headers if read_c_string(names,h[0])=='.strtab'];assert len(string_headers)==1
 rows=symbol_rows(predicted);symbols={n:(at,row)for at,n,row,_ in rows if n};string_bytes=0
 for old_order,new_order in permutations:
  assert set(old_order)==set(new_order)and len(set(old_order))==len(old_order)
  first_at,first_row=symbols[old_order[0]];start=first_row[0];offset=start
  old_names=b''.join(n.encode()+b'\0'for n in old_order)
  for i,n in enumerate(old_order):
   symbol_at,row=symbols[n];assert symbol_at==first_at+16*i and row[0]==offset;offset+=len(n)+1
  assert {n for _,n,row,_ in rows if start<=row[0]<offset}==set(old_order)
  at=string_headers[0][4]+start;assert predicted[at:at+len(old_names)]==old_names
  new_names=b''.join(n.encode()+b'\0'for n in new_order);assert len(new_names)==len(old_names)
  predicted[at:at+len(old_names)]=new_names;offset=start
  for i,n in enumerate(new_order):
   row=symbols[n][1];struct.pack_into('>IIIBBH',predicted,first_at+16*i,offset,*row[1:]);offset+=len(n)+1
  string_bytes+=len(old_names)
 actual=image.read_bytes();assert len(actual)==len(predicted)
 differences=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
 (where/'unpredicted-differences.json').write_text(json.dumps(differences)+'\n')
 if differences:
  arows=symbol_rows(actual);old_names=[n for _,n,_,_ in rows];new_names=[n for _,n,_,_ in arows]
  changes=[dict(index=i,before=old_names[i],after=new_names[i])for i in range(len(old_names))if old_names[i]!=new_names[i]]
  (out/'metadata-order-observation.json').write_text(json.dumps(changes,indent=2)+'\n')
 assert not differences,('unexpected image bytes',len(differences),differences[:12])
 (where/'predicted.elf').write_bytes(predicted)
 r=dict(words=149,frame=72,raw_differences=0,guards=0,insertions=0,omissions=0,owner_functions=5,unchanged_owner_functions=4,
        direct_padded_payload_equals_original=True,guard_manifest_unchanged=True,actual_Make=make,
        strict_predicted_ELF_equal=True,changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,
        ELF_sha256=hashlib.sha256(actual).hexdigest(),metadata_permutations=permutations,
        metadata_symbol_records=sum(len(a)for a,b in permutations),metadata_string_bytes=string_bytes,
        protected_data_audit=audit_layout(image,root/'conker'),source_installed=installed(),matching_credit=0)
 (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
