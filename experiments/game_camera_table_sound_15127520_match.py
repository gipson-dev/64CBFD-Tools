"""Camera table-sound callback recovery, natural Make and strict image gates."""
from pathlib import Path
import hashlib,json,os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_camera_table_sound_15127520_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];SOURCE=MANIFEST['source'];FUNCTION=MANIFEST['function']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
norm=lambda b:b.replace(b'\r\n',b'\n')
def installed():return norm((ROOT/SOURCE).read_bytes())==MANIFEST['selected_source'].encode()
def prepare():
    from tools.experiments.game_remaining_donor_candidates import compile_owner
    from tools.experiments.game_actor_state_tick_integration import same_functions
    from tools.experiments.game_selector_table_payload_match import diagnostic_rows
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.tests.game_owner_pool import normalized_pools
    for n in (SOURCE,MANIFEST['object'],'conker/build/conker.us.elf','conker/Makefile','conker/retail_word_patches.us.csv'):
        assert sha(OUT/'baseline'/n)==MANIFEST['inputs'][n],('frozen baseline changed',n)
    assert norm((ROOT/SOURCE).read_bytes())in(MANIFEST['old_source'].encode(),MANIFEST['selected_source'].encode())
    for n,d in MANIFEST['inputs'].items():
        if n==SOURCE:continue
        permitted={d}
        if n==MANIFEST['object']:permitted.add(MANIFEST['padded_sha256'])
        if n=='conker/build/conker.us.elf':permitted.add(MANIFEST['predicted_ELF_sha256'])
        if n=='conker/retail_word_patches.us.csv':permitted.add(MANIFEST['guard_sha256'])
        assert sha(ROOT/n)in permitted,n
    import csv,io
    baseline_guard=OUT/'baseline/conker/retail_word_patches.us.csv'
    with baseline_guard.open(newline='') as stream:
        fields=csv.DictReader(stream).fieldnames
    original=baseline_guard.read_bytes();assert original.endswith(b'\n')
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writerows(MANIFEST['guard_rows'])
    (OUT/'qualified-guards.csv').write_bytes(original+stream.getvalue().encode())
    assert (OUT/'qualified-guards.csv').read_bytes().startswith(original)
    assert sha(OUT/'qualified-guards.csv')==MANIFEST['guard_sha256']
    old_dir=OUT/'qualified-source';new_dir=OUT/'qualified-source'
    old_dir.mkdir(exist_ok=True);new_dir.mkdir(exist_ok=True)
    a,ad=compile_owner(ROOT,old_dir,MANIFEST['old_source'],'before')
    b,bd=compile_owner(ROOT,new_dir,MANIFEST['selected_source'],'candidate')
    assert diagnostic_rows(ad)==diagnostic_rows(bd)
    assert same_functions(a,b,(FUNCTION,))==44 and normalized_pools(a)==normalized_pools(b)
    assert hashlib.sha256(payload(b,FUNCTION)[0]).hexdigest()==MANIFEST['raw_sha256']
    (new_dir/'selected-owner.c').write_text(MANIFEST['selected_source'])
    return dict(installed=installed(),unchanged_neighbors=44,guards=4,words=164,frame=72)


from pathlib import Path
import json,re,struct,sys
root=ROOT;out=OUT
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY=0x15127520
def census():
 rom=(root/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom);calls=[];constructed=[];pointers=[]
 for i,w in enumerate(words):
  if w>>26 in(2,3)and(w&0x3FFFFFF)<<2==ENTRY&0xFFFFFFF:calls.append({'ROM':4*i,'kind':'JAL'if w>>26==3 else'J'})
  if w>>26==15 and w&65535==0x1512 and i+1<len(words):
   rt=w>>16&31;n=words[i+1]
   if n>>26 in(9,13)and n>>21&31==rt and n>>16&31==rt and n&65535==0x7520:constructed.append({'ROM':4*i,'words':[w,n]})
 loaded=sections(out/'baseline/conker/build/conker.us.elf')
 for name,(address,data)in loaded.items():
  if not address or name.startswith(('.mdebug','.symtab','.strtab')):continue
  for at in range(0,len(data)-3,4):
   if struct.unpack_from('>I',data,at)[0]==ENTRY:pointers.append({'section':name,'address':address+at})
 assert not calls and not pointers,(calls,pointers)
 assert constructed==[{'ROM':0x153DAC,'words':[0x3C191512,0x27397520]},{'ROM':0x153EBC,'words':[0x3C0C1512,0x258C7520]}],constructed
 parent=(out/'baseline/conker/asm/nonmatchings/game_14FF90/func_15126378.s').read_text()
 original_words={int(a,16):int(w,16)for a,w in re.findall(r'/\* [0-9A-F]+ ([0-9A-F]+) ([0-9A-F]{8}) \*/',parent)}
 for address,offset in((0x151268FC,0x153DAC),(0x15126A0C,0x153EBC)):
  assert tuple(original_words[address+4*i]for i in range(2))==tuple(words[offset//4:offset//4+2])
 baseline=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 for address,start,end in((0x10011848,0x11848,0x118A8),(0x1000FB54,0xFB54,0xFB94),(0x151CC290,0x1F9740,0x1F976C)):
  at=elf_slot_offset(baseline,address,end-start);assert baseline[at:at+end-start]==rom[start:end],hex(address)
 for address,expected in((0x800894E0,bytes.fromhex('060306040605062006210622')),(0x800A3580,bytes.fromhex('c61c4000'))):
  matches=[data[address-a:address-a+len(expected)]for a,data in loaded.values()if a<=address and address+len(expected)<=a+len(data)]
  assert matches==[expected],hex(address)
 r={'function':'func_15127520','direct_original_calls':calls,'adjacent_original_address_materializations':constructed,'aligned_loaded_pointer_literals':pointers,
  'registration_parent_restored':False,'dispatch_JALR':'0x1001187C','callback_arguments':7,'literal_camera_event_provider_words':11,
  'actual_table_words':[0x603,0x604,0x605,0x620,0x621,0x622],'actual_factor_bits':'c61c4000',
  'scope':'Original registration parent remains a placeholder. Two constructed references are original-ROM/sealed-ASM evidence; Init caller/constructor windows and the camera-event provider are literal in the sealed ELF. Computed references are not excluded.',
  'source_installed':installed(),'matching_credit':0}
 (out/'caller-census.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

def qualify():
    prepare()
    census()
    from tools.tests import game_camera_table_sound_15127520_schedule_proof as schedule
    schedule.run()
    from pathlib import Path
    from unittest.mock import patch
    import hashlib,json,re,shutil,struct,subprocess,sys
    root=ROOT;out=OUT
    from tools import pad_generated_object as pg
    sys.modules.setdefault('pad_generated_object',pg)
    from tools import pad_c_object as pc
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
    from tools.experiments import game_embedded_dual_phase_position_update_match as linker
    from tools.experiments import game_list_owner_make as route
    from tools.check_game_data_layout import audit_layout
    from tools.match_progress import load_elf_functions
    from tools.experiments.game_actor_classifier_candidates import ELF_HEADER,SECTION_HEADER,read_c_string
    base=out/'baseline';where=out/'image-qualification';where.mkdir(exist_ok=True)
    SOURCE='conker/src/game_14FF90.c';OBJECT='conker/build/src/game_14FF90.c.o';FUNCTION='func_15127520'
    compact=out/'qualified-source/candidate.o';selected=(out/'qualified-source/selected-owner.c').read_text()
    guards=out/'qualified-guards.csv'
    assert sha(root/'conker/retail_word_patches.us.csv') in (MANIFEST['inputs']['conker/retail_word_patches.us.csv'],MANIFEST['guard_sha256'])
    assert len(re.findall(r',func_15127520,',guards.read_text()))==4
    def assemble(name,text):
        p=where/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True)
        return obj
    truth=assemble('retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(root/'conker/asm/nonmatchings/game_14FF90/func_15127520.s').read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    from tools.tests.game_camera_table_sound_15127520_schedule_proof import prove
    SYMS={'D_800894E0':0x800894E0,'D_800A3580':0x800A3580,'func_100111C8':0x100111C8,'func_10010F30':0x10010F30,'func_151CC290':0x151CC290}
    proof=prove(bound_blob(*payload(compact,FUNCTION),SYMS),bound_blob(*payload(truth,FUNCTION),SYMS))
    assert proof['changed_words']==4
    text=pc.emit_padded_assembly(compact,root/'conker/retail_layout.us.txt','game_14FF90',word_patches_path=guards)
    padded=assemble('padded',text)
    assert payload(padded,FUNCTION)==payload(truth,FUNCTION)
    assert same_functions(base/OBJECT,padded,(FUNCTION,))==44
    old=pg.parse_object(base/OBJECT);new=pg.parse_object(padded)
    for n,f in old[1].items():
        expected=dict(f)
        if n==FUNCTION:expected['size']=656
        assert new[1][n]==expected,(n,f,new[1][n])
    (where/'after-diagnostics.txt').write_text((out/'qualified-source/candidate-diagnostics.txt').read_text())
    make=route.actual_Make(root,where,padded,compact,guards,SOURCE,OBJECT,selected,'target',45)
    linked_owner=where/'qualified-owner/game_14FF90.c.o';linked_owner.parent.mkdir(exist_ok=True)
    shutil.copyfile(padded,linked_owner);assert linked_owner.read_bytes()==padded.read_bytes()
    with patch.multiple(linker,FILENAME='game_14FF90',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        image=linker.link_image(root,where,linked_owner,'image')
    before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
    at=elf_slot_offset(predicted,0x15127520,656);predicted[at:at+656]=(root/'conker/conker.us.bin').read_bytes()[0x1549d0:0x154c60]
    matches=[(at,row)for at,n,row,_ in symbol_rows(predicted)if n==FUNCTION];assert len(matches)==1
    at,row=matches[0];previous_size=old[1][FUNCTION]['size'];assert row[1:3]==(0x15127520,previous_size)
    struct.pack_into('>I',predicted,at+8,656)
    # GNU ld rotates three closed symbol/name groups after these first references.
    # Preserve every value/size/type/binding and rebuild only their exact ordering.
    permutations=[
     (('func_1000B8B8','D_800B0C48'),('D_800B0C48','func_1000B8B8')),
     (('D_800A3580','D_80082F28','D_80099630','D_800E0930','D_800E0A90'),('D_80082F28','D_80099630','D_800E0930','D_800E0A90','D_800A3580'))]
    head=ELF_HEADER.unpack_from(predicted);headers=[SECTION_HEADER.unpack_from(predicted,head[6]+i*head[11])for i in range(head[12])]
    names_header=headers[head[13]];names=predicted[names_header[4]:names_header[4]+names_header[5]]
    strings=[h for h in headers if read_c_string(names,h[0])=='.strtab'];assert len(strings)==1
    rows=symbol_rows(predicted);symbols={n:(at,row)for at,n,row,_ in rows if n};string_bytes=0
    for original_order,new_order in permutations:
     assert set(original_order)==set(new_order)and len(set(original_order))==len(original_order)
     first_at,first_row=symbols[original_order[0]];string_start=first_row[0]
     old_names=b''.join(n.encode()+b'\0'for n in original_order);offset=string_start
     for i,n in enumerate(original_order):
      symbol_at,row=symbols[n];assert symbol_at==first_at+16*i and row[0]==offset;offset+=len(n)+1
     assert{n for _,n,row,_ in rows if string_start<=row[0]<offset}==set(original_order)
     where_string=strings[0][4]+string_start;assert predicted[where_string:where_string+len(old_names)]==old_names
     new_names=b''.join(n.encode()+b'\0'for n in new_order);assert len(new_names)==len(old_names)
     predicted[where_string:where_string+len(old_names)]=new_names;offset=string_start
     for i,n in enumerate(new_order):
      row=symbols[n][1];struct.pack_into('>IIIBBH',predicted,first_at+16*i,offset,*row[1:]);offset+=len(n)+1
     string_bytes+=len(old_names)
    actual=image.read_bytes();assert len(actual)==len(predicted)
    differences=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
    (where/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected image bytes',len(differences),differences[:20])
    (where/'predicted.elf').write_bytes(predicted)
    functions,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    r=dict(raw_scheduling_equivalence_proved=True,padded_equal_original=True,words=164,frame=72,guards=4,insertions=0,omissions=0,
     owner_functions=45,unchanged_owner_functions=44,actual_Make=make,strict_predicted_ELF_equal=True,
     changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,function_slots=len(functions),
     ELF_sha256=hashlib.sha256(actual).hexdigest(),previous_symbol_size=previous_size,symbol_definitions_preserved_except_target_size=True,
     closed_metadata_permutations=permutations,metadata_symbol_records=7,metadata_string_bytes=string_bytes,
     protected_data_audit=audit_layout(image,root/'conker'),
     source_installed=installed(),matching_credit=0)
    (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    return r
