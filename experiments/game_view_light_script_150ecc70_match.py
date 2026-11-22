"""View light/range script, complete signed-clamp proof and strict image audit."""
from pathlib import Path
import hashlib,json,os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_view_light_script_150ecc70_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION='func_150ECC70'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return (ROOT/MANIFEST['source']).read_text()==MANIFEST['selected_source']
def prepare():
 permitted={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],
  'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256']}
 for n,d in MANIFEST['inputs'].items():
  frozen=OUT/'baseline'/n
  if frozen.exists():assert sha(frozen)==d,('Frozen baseline changed',n)
  assert sha(ROOT/n)in{d,permitted.get(n,d)},n
 return installed()
def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.experiments.game_path_heading_turn_roles import bound_blob
 from tools.experiments.game_actor_state_tick_integration import symbol_rows,same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 where=OUT/'ternary-order3';where.mkdir(exist_ok=True)
 before,bd=compile_owner(ROOT,where,MANIFEST['old_source'],'before')
 after,ad=compile_owner(ROOT,where,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,))==6
 assert diagnostic_rows(bd)==diagnostic_rows(ad)and normalized_pools(before)==normalized_pools(after)
 raw,refs=payload(after,FUNCTION)
 assert len(raw)==1364 and int.from_bytes(raw[:4],'big')==0x27BDFFC8
 assert hashlib.sha256(raw).hexdigest()=='bcf8616cb989dba7034e1a3453608f2b6e82c34093fec84c49cb8f28e24959eb'
 symbols={n:r[1]for _,n,r,_ in symbol_rows((OUT/'baseline/conker/build/conker.us.elf').read_bytes())if n};symbols['.rodata']=0x800A1578
 (where/'words.json').write_text(json.dumps(bound_blob(raw,refs,symbols))+'\n')
 (where/'selected-owner.c').write_text(MANIFEST['selected_source'])
 return dict(words=341,frame=56,neighbors=6,pools_equal=True,diagnostics_equal=True)
"""Relocation-aware guards for one proven signed-clamp branch-layout region."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
root,out=ROOT,OUT
from tools.experiments import game_view_light_script_150ecc70_clamp_proof as clamp_proof
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
NAME='func_150ECC70'
def normalize():
 clamp_proof.main()
 obj=out/'ternary-order3/candidate.o';raw,refs=payload(obj,NAME);ws=list(struct.unpack('>341I',raw))
 assert hashlib.sha256(raw).hexdigest()=='bcf8616cb989dba7034e1a3453608f2b6e82c34093fec84c49cb8f28e24959eb'
 def assemble(text,name):
  path=out/(name+'.s');path.write_text(text);target=path.with_suffix('.o')
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(target),str(path)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr);return target
 full=(root/'conker/asm/1199D0.s').read_text();body='glabel '+NAME+full.split('glabel '+NAME,1)[1].split('endlabel '+NAME,1)[0]+'endlabel '+NAME
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+body+'\n.size '+NAME+',.-'+NAME+'\n','original-target')
 expected,rr=payload(retail,NAME);truth=list(struct.unpack('>341I',expected))
 symbols={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n};symbols['.rodata']=0x800A1578
 assert bound_blob(expected,rr,symbols)==list(struct.unpack_from('>341I',(root/'conker/conker.us.bin').read_bytes(),0x11A120))
 source=out/'baseline/conker/retail_word_patches.us.csv'
 with source.open(newline='')as f:reader=csv.DictReader(f);rows=list(reader);fields=reader.fieldnames
 assert not any(r['function']==NAME for r in rows)
 spell=lambda r:';'.join(k+':'+v for k,v in r)if r else '-'
 added=[]
 for i,(old,new)in enumerate(zip(ws,truth)):
  oldr,newr=refs.get(4*i,[]),rr.get(4*i,[])
  if old==new and oldr==newr:continue
  assert 121<=i<=150,i
  added.append(dict(filename='generated_1199D0',function=NAME,offset=f'0x{i*4:03X}',expected=f'0x{old:08X}',replacement=f'0x{new:08X}',
   expected_relocations=spell(oldr),replacement_relocations=spell(newr),
   note='Preserve the retail signed range and half-value clamp branch layout; full signed-domain CFG proof',insert_after='',insert_after_relocations='',omit='false'))
 assert len(added)==28
 tail=io.StringIO(newline='');csv.DictWriter(tail,fieldnames=fields).writerows(added)
 original=source.read_bytes();assert original.endswith(b'\n');guards=out/'private-word-patches.csv';guards.write_bytes(original+tail.getvalue().encode())
 padded=assemble(pg.emit_padded_assembly(obj,root/'conker/asm/1199D0.s',filename='generated_1199D0',word_patches_path=guards,rodata_symbol='D_800A1578'),'private-padded')
 assert same_functions(out/'baseline/conker/build/src/game/generated_1199D0.c.o',padded,(NAME,))==6
 def isolated(data,relocs,name):
  text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
  for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
   for k,n in relocs.get(4*i,[]):text+=f'.reloc ., {k}, {n}\n'
   text+=f'.word 0x{w:08X}\n'
  return assemble(text+'.size '+NAME+',.-'+NAME+'\n',name)
 rawobj=isolated(raw,refs,'isolated-raw')
 lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();rows=[v for v in lines[1:]if v.split(',')[1:3]==['generated_1199D0',NAME]];assert len(rows)==1
 layout=out/'target-layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n')
 target_guards=out/'target-word-patches.csv'
 with target_guards.open('w',newline='')as f:
  writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(added)
 generic=assemble(pc.emit_padded_assembly(rawobj,layout,'generated_1199D0',word_patches_path=target_guards),'private-generic')
 assert payload(generic,NAME)==payload(padded,NAME)==payload(retail,NAME)
 normalized=isolated(*payload(padded,NAME),'isolated-normalized');links=0
 names={n for v in rr.values()for k,n in v}
 for rebase in(0,0x7FFC,0x8000,0xFFFC):
  values={n:symbols[n]+rebase for n in names};streams=[]
  for path,label in((normalized,'normalized'),(retail,'retail')):
   script=out/f'link-{rebase:X}-{label}.ld';script.write_text('SECTIONS { .text 0x150ECC70 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{v:X}'for n,v in values.items()],'-o',str(elf),str(path)],capture_output=True,text=True)
   assert q.returncode==0,q.stderr;linked=sections(elf)['.text'][1];assert len(linked)==1376 and not any(linked[1364:]);streams.append(linked);links+=1
  assert streams[0]==streams[1]
 (out/'selected-owner.c').write_bytes((out/'ternary-order3/selected-owner.c').read_bytes())
 r=dict(raw_words=341,normalized_words=341,frame=56,guards=28,insertions=0,omissions=0,body_bytes=1364,slot_padding_bytes=12,
  both_padders_equal=True,GNU_links=links,unchanged_neighbors=6,linked_target_equals_retail=True,baseline_guards_prefix_preserved=True,
  qualification='Closed signed-clamp CFG equivalence, not scheduling-only',source_installed=installed(),matching_credit=0)
 (out/'normalization.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r


"""Actual Make recipe and complete independently predicted ELF, zero exclusions."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,shutil,struct,sys
root,out=ROOT,OUT
from tools.experiments import game_list_owner_make as route
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_classifier_candidates import ELF_HEADER,SECTION_HEADER,read_c_string
def qualify():
 base=out/'baseline';where=out/'image-qualification';where.mkdir(exist_ok=True)
 SOURCE='conker/src/game/generated_1199D0.c';OBJECT='conker/build/src/game/generated_1199D0.c.o';NAME='func_150ECC70'
 prepare();inspect_source();normalize()
 selected=(out/'selected-owner.c').read_text();compact=out/'ternary-order3/candidate.o';padded=out/'private-padded.o';guards=out/'private-word-patches.csv'
 assert same_functions(base/OBJECT,padded,(NAME,))==6
 (where/'after-diagnostics.txt').write_text((out/'ternary-order3/candidate-diagnostics.txt').read_text())
 make=route.actual_Make(root,where,padded,compact,guards,SOURCE,OBJECT,selected,'target',7)
 owner=where/'qualified-owner/generated_1199D0.c.o';owner.parent.mkdir(exist_ok=True);shutil.copyfile(padded,owner)
 with patch.multiple(linker,FILENAME='generated_1199D0',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
  image=linker.link_image(root,where,owner,'image')
 before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
 at=elf_slot_offset(predicted,0x150ECC70,1376);original=(root/'conker/conker.us.bin').read_bytes()[0x11A120:0x11A680]
 assert not any(original[1364:]);predicted[at:at+1376]=original
 entries=[(at,row)for at,n,row,_ in symbol_rows(predicted)if n==NAME];assert len(entries)==1
 at,row=entries[0];assert row[1:3]==(0x150ECC70,12);struct.pack_into('>I',predicted,at+8,1364)
 rows=symbol_rows(predicted);symbols={n:(at,row)for at,n,row,_ in rows if n}
 permutations=MANIFEST['metadata_permutations']
 header=ELF_HEADER.unpack_from(predicted);headers=[SECTION_HEADER.unpack_from(predicted,header[6]+i*header[11])for i in range(header[12])]
 nh=headers[header[13]];names=predicted[nh[4]:nh[4]+nh[5]];strings=[h for h in headers if read_c_string(names,h[0])=='.strtab'];assert len(strings)==1
 for old,new in permutations:
  assert set(old)==set(new)and len(set(old))==len(old)
  first,firstrow=symbols[old[0]];start=offset=firstrow[0]
  for i,n in enumerate(old):
   a,r=symbols[n];assert a==first+16*i and r[0]==offset;offset+=len(n)+1
  assert {n for _,n,r,_ in rows if start<=r[0]<offset}==set(old)
  at=strings[0][4]+start;oldbytes=b''.join(n.encode()+b'\0'for n in old);newbytes=b''.join(n.encode()+b'\0'for n in new)
  assert len(oldbytes)==len(newbytes)and predicted[at:at+len(oldbytes)]==oldbytes
  predicted[at:at+len(oldbytes)]=newbytes;offset=start
  for i,n in enumerate(new):struct.pack_into('>IIIBBH',predicted,first+16*i,offset,*symbols[n][1][1:]);offset+=len(n)+1
 actual=image.read_bytes();assert len(actual)==len(predicted)
 diffs=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
 (where/'unpredicted-differences.json').write_text(json.dumps(diffs)+'\n')
 if diffs:
  changed=[dict(index=i,before=a[1],after=b[1])for i,(a,b)in enumerate(zip(rows,symbol_rows(actual)))if a[1]!=b[1]]
  (out/'metadata-order-observation.json').write_text(json.dumps(changed,indent=2)+'\n')
 assert not diffs,('Unexpected complete-image differences',len(diffs),diffs[:12])
 (where/'predicted.elf').write_bytes(predicted)
 r=dict(raw_words=341,normalized_words=341,frame=56,guards=28,insertions=0,omissions=0,slot_padding_bytes=12,
  actual_Make=make,strict_predicted_ELF_equal=True,changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,
  metadata_permutations=permutations,ELF_sha256=hashlib.sha256(actual).hexdigest(),protected_data_audit=audit_layout(image,root/'conker'),
  unchanged_owner_neighbors=6,source_installed=installed(),matching_credit=0)
 (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
