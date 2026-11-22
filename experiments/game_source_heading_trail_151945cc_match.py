"""Guarded source-heading trail with exact frame, snapshots and image gates."""
from pathlib import Path
import hashlib,json,os,sys,struct
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_source_heading_trail_151945cc_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];root,out=ROOT,OUT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
norm=lambda b:b.replace(b'\r\n',b'\n')
def installed():return norm((ROOT/MANIFEST['source']).read_bytes())==MANIFEST['selected_source'].encode()
def prepare():
 for n,d in MANIFEST['inputs'].items():
  if (OUT/'baseline'/n).exists():assert sha(OUT/'baseline'/n)==d,('frozen baseline changed',n)
  permitted={d}
  if n==MANIFEST['source']:permitted.add(MANIFEST['selected_sha256'])
  if n==MANIFEST['object']:permitted.add(MANIFEST['padded_sha256'])
  if n=='conker/build/conker.us.elf':permitted.add(MANIFEST['predicted_ELF_sha256'])
  if n=='conker/retail_word_patches.us.csv':permitted.add(MANIFEST['selected_guards_sha256'])
  assert sha(ROOT/n)in permitted,n
 return installed()
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
SOURCE=MANIFEST['source'];FUNCTION=MANIFEST['function'];ENTRY=0x151945CC;ROM=0x1C1A7C;WORDS=114
TYPES=MANIFEST['types'];BODY=MANIFEST['body']
def proposal(selected=BODY):
 old=(out/'baseline'/SOURCE).read_text();a,b=function_span(old,FUNCTION)
 return old[:a]+TYPES+'\n/* Emit a classified trail from the captured source heading and actor position. */\n'+selected+old[b:]
def inspect(selected=BODY,label='first-source'):
 where=out/label;where.mkdir(exist_ok=True)
 a,ad=compile_owner(root,where,(out/'baseline'/SOURCE).read_text(),'before')
 source=proposal(selected);b,bd=compile_owner(root,where,source,'candidate')
 assert diagnostic_rows(ad)==diagnostic_rows(bd),(diagnostic_rows(ad),diagnostic_rows(bd))
 neighbors=same_functions(a,b,(FUNCTION,));assert normalized_pools(a)==normalized_pools(b)
 raw,refs=payload(b,FUNCTION);symbols={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 ws=bound_blob(raw,refs,symbols);retail=struct.unpack_from('>114I',(root/'conker/conker.us.bin').read_bytes(),ROM)
 changes=[dict(word=i,C=f'{x:08x}',original=f'{y:08x}')for i,(x,y)in enumerate(zip(ws,retail))if x!=y]
 frames=[65536-(w&65535)for w in ws if w&0xFFFF0000==0x27BD0000 and w&0x8000]
 r=dict(words=len(ws),frame=max(frames,default=0),differences=len(changes)+abs(len(ws)-WORDS),changed_words=changes,bindings=refs,unchanged_neighbors=neighbors,relocation_sites=len(refs),raw_sha256=hashlib.sha256(raw).hexdigest(),source_installed=False,matching_credit=0)
 (where/'selected-owner.c').write_text(source);(out/(label+'.json')).write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:v for k,v in r.items()if k not in('changed_words','bindings')}));return r
"""A closed rotation of one redundant argument move; no memory reordering."""
from pathlib import Path
import csv,io,json,struct,sys
root=ROOT;out=OUT
screen=sys.modules[__name__]
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
def qualify_guards():
 report=screen.inspect(label='qualified-source');assert report['words']==114 and report['frame']==176 and report['differences']==9 and report['unchanged_neighbors']==28
 raw,refs=payload(out/'qualified-source/candidate.o',screen.FUNCTION)
 words=list(struct.unpack('>114I',raw));symbols={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 bound=bound_blob(raw,refs,symbols);retail=list(struct.unpack_from('>114I',(root/'conker/conker.us.bin').read_bytes(),screen.ROM))
 assert words[15]==retail[24]==0x02002825
 assert bound[23]==retail[23] and refs[23*4]==[('R_MIPS_26','func_1504715C')]
 assert bound[16:23]==retail[15:22] and bound[24]==retail[22]
 # S0 captures A1 and neither can change before the first surface call.
 assert words[4]==0x00A08025
 def writes(w):
  op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  if op==0:return {rd}if fn not in(8,9,24,25,26,27)else set()
  if op in(9,10,11,12,13,14,15,32,33,35,36,37):return {rt}
  return set()
 assert all(not(writes(w)&{5,16})for w in words[5:15])
 assert all(not(writes(w)&{5,16})for w in words[16:23]+[words[24]])
 assert all(at not in refs for at in([i*4 for i in range(15,23)]+[24*4]))
 assert bound[:15]==retail[:15]and bound[25:]==retail[25:]
 old=(out/'baseline/conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
 assert not any(row['function']==screen.FUNCTION for row in reader)
 changes=[i for i in range(114)if bound[i]!=retail[i]];assert changes==list(range(15,23))+[24]
 stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n')
 # Existing guard field names remain the repository's schema.
 rows=[]
 for i in changes:
  row={k:''for k in fields};row.update(filename='generated_1C1150',function=screen.FUNCTION,offset='0x%03X'%(4*i),expected='0x%08X'%words[i],replacement='0x%08X'%retail[i],expected_relocations='-',replacement_relocations='-',note='Normalize the redundant A1 actor move to the retail call delay slot',omit='false')
  writer.writerow(row);rows.append(row)
 assert old.endswith(b'\r\n')or old.endswith(b'\n')
 guard=out/'private-guards.csv';guard.write_bytes(old+stream.getvalue().encode())
 r=dict(words=114,frame=176,guards=9,rotation_indices=changes,A1_equals_S0_through_rotation=True,ordered_memory_instructions_unchanged=True,all_relocations_unchanged=True,guard_prefix_bytes_preserved=len(old),source_installed=False,matching_credit=0)
 (out/'guards.json').write_text(json.dumps(r,indent=2)+'\n');(out/'guard-rows.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(r));return r

def qualify():
    prepare()
    """Closed scheduling guards, complete owner, natural Make and literal image."""
    from pathlib import Path
    from unittest.mock import patch
    import hashlib,json,re,shutil,struct,subprocess,sys
    root=ROOT;out=OUT
    screen=sys.modules[__name__]
    from tools import pad_generated_object as pg
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
    from tools.experiments import game_embedded_dual_phase_position_update_match as linker
    from tools.experiments import game_list_owner_make as route
    from tools.check_game_data_layout import audit_layout
    from tools.match_progress import load_elf_functions
    from tools.experiments.game_actor_classifier_candidates import ELF_HEADER,SECTION_HEADER,read_c_string
    base=out/'baseline';where=out/'image-qualification';where.mkdir(exist_ok=True)
    SOURCE=screen.SOURCE;FUNCTION=screen.FUNCTION;OBJECT='conker/build/src/game/generated_1C1150.c.o'
    qualify_guards();compact=out/'qualified-source/candidate.o';guards=out/'private-guards.csv'
    oldguards=(base/'conker/retail_word_patches.us.csv').read_bytes();assert guards.read_bytes().startswith(oldguards)
    assert (root/'conker/retail_word_patches.us.csv').read_bytes()in(oldguards,guards.read_bytes())
    def assemble(name,text):
     p=where/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
     q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,text=True)
     assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr);return obj
    full=(root/'conker/asm/1C1150.s').read_text();body='glabel '+FUNCTION+full.split('glabel '+FUNCTION,1)[1].split('endlabel '+FUNCTION,1)[0]+'endlabel '+FUNCTION
    truth=assemble('retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+body+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    padded=assemble('padded',pg.emit_padded_assembly(compact,root/'conker/asm/1C1150.s',filename='generated_1C1150',word_patches_path=guards,rodata_symbol='jtbl_800A8258_game'))
    assert payload(padded,FUNCTION)==payload(truth,FUNCTION)
    assert same_functions(base/OBJECT,padded,(FUNCTION,))==28
    old=pg.parse_object(base/OBJECT);new=pg.parse_object(padded)
    for n,f in old[1].items():
     expected=dict(f)
     if n==FUNCTION:expected['size']=456
     assert new[1][n]==expected,(n,f,new[1][n])
    selected=(out/'qualified-source/selected-owner.c').read_text()
    (where/'after-diagnostics.txt').write_text((out/'qualified-source/candidate-diagnostics.txt').read_text())
    make=route.actual_Make(root,where,padded,compact,guards,SOURCE,OBJECT,selected,'target',29)
    owner=where/'qualified-owner/generated_1C1150.c.o';owner.parent.mkdir(exist_ok=True);shutil.copyfile(padded,owner)
    with patch.multiple(linker,FILENAME='generated_1C1150',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
     image=linker.link_image(root,where,owner,'image')
    before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
    at=elf_slot_offset(predicted,screen.ENTRY,456);predicted[at:at+456]=(root/'conker/conker.us.bin').read_bytes()[screen.ROM:screen.ROM+456]
    matches=[(at,row)for at,n,row,_ in symbol_rows(predicted)if n==FUNCTION];assert len(matches)==1
    at,row=matches[0];assert row[1:3]==(screen.ENTRY,12);struct.pack_into('>I',predicted,at+8,456)
    permutation_file=out/'metadata-permutations.json'
    permutations=MANIFEST['metadata_permutations']
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
      row=symbols[n][1]
      struct.pack_into('>IIIBBH',predicted,first_at+16*i,offset,*row[1:]);offset+=len(n)+1
     string_bytes+=len(old_names)
    actual=image.read_bytes();assert len(actual)==len(predicted)
    differences=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
    (where/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected image bytes',len(differences),differences[:20])
    (where/'predicted.elf').write_bytes(predicted)
    functions,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    r=dict(words=114,frame=176,raw_differences=9,guards=9,insertions=0,omissions=0,owner_functions=29,unchanged_owner_functions=28,
     normalized_padded_payload_equals_original=True,original_guard_prefix_preserved=True,actual_Make=make,
     strict_predicted_ELF_equal=True,changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,function_slots=len(functions),
     ELF_sha256=hashlib.sha256(actual).hexdigest(),metadata_permutations=permutations,
     metadata_symbol_records=sum(len(a)for a,b in permutations),metadata_string_bytes=string_bytes,
     protected_data_audit=audit_layout(image,root/'conker'),source_installed=installed(),matching_credit=0)
    (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    return r
