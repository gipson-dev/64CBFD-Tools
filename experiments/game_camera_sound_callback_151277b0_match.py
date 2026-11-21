"""Guarded camera sound callback recovery, natural Make and strict image gates."""
from pathlib import Path
import hashlib,json,os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_camera_sound_callback_151277b0_manifest.json').read_text())
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
    return dict(installed=installed(),unchanged_neighbors=44,guards=42,words=124,frame=48)

from pathlib import Path
import json,re,struct,sys
root=ROOT;out=OUT
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY=0x151277B0
def census():
 rom=(root/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom);calls=[];constructed=[];pointers=[]
 for i,w in enumerate(words):
  if w>>26 in(2,3)and(w&0x3FFFFFF)<<2==ENTRY&0xFFFFFFF:calls.append({'ROM':4*i,'kind':'JAL'if w>>26==3 else'J'})
  if w>>26==15 and w&65535==0x1512 and i+1<len(words):
   rt=w>>16&31;n=words[i+1]
   if n>>26 in(9,13)and n>>21&31==rt and n>>16&31==rt and n&65535==0x77B0:constructed.append({'ROM':4*i,'words':[w,n]})
 for name,(address,data)in sections(out/'baseline/conker/build/conker.us.elf').items():
  if not address or name.startswith(('.mdebug','.symtab','.strtab')):continue
  for at in range(0,len(data)-3,4):
   if struct.unpack_from('>I',data,at)[0]==ENTRY:pointers.append({'section':name,'address':address+at})
 assert not calls and not pointers,(calls,pointers)
 assert constructed==[{'ROM':0x153FB8,'words':[0x3C0E1512,0x25CE77B0]}],constructed
 # Original constructor stores the seventh stack argument (callback) in field +14.
 assert struct.unpack_from('>I',rom,0xFB54)[0]==0x8FAD0044
 assert struct.unpack_from('>I',rom,0xFB90)[0]==0xAE0D0014
 baseline=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 registration_words=[int(word,16)for address,word in re.findall(r'/\* [0-9A-F]+ ([0-9A-F]+) ([0-9A-F]{8}) \*/',(out/'baseline/conker/asm/nonmatchings/game_14FF90/func_15126378.s').read_text())if 0x15126B04<=int(address,16)<0x15126B54]
 assert tuple(registration_words)==struct.unpack_from('>20I',rom,0x153FB4)
 at=elf_slot_offset(baseline,0x15126B04,80);parent_window_current=baseline[at:at+80]==rom[0x153FB4:0x154004]
 assert not parent_window_current,'Parent unexpectedly restored: expand adoption audit'
 for address,start,end in((0x10011848,0x11848,0x118A8),(0x1000FB54,0xFB54,0xFB94)):
  at=elf_slot_offset(baseline,address,end-start);assert baseline[at:at+end-start]==rom[start:end],hex(address)
 r={'function':'func_151277B0','direct_original_calls':calls,'adjacent_original_address_materializations':constructed,
  'aligned_loaded_pointer_literals':pointers,'registration':'func_15126378 passes the constructed pointer to func_1000FA64 as argument 7; original constructor stores it at sound record +0x14.',
  'dispatch':'func_10011624 loads record +0x14 and invokes seven-argument JALR at 0x1001187C; both return branches are covered separately.',
  'registration_parent_is_restored_in_baseline':parent_window_current,
  'scope':'Fresh original-code and frozen loaded-ELF census. Registration parent remains a C placeholder, so its window is original-ROM/sealed-ASM evidence, not current gameplay. Init constructor/dispatcher windows are literal in the frozen ELF. No exclusion of all computed references or full constructor/dispatcher reconstruction.',
  'source_installed':installed(),'matching_credit':0}
 (out/'caller-census.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

def qualify():
    prepare()
    census()
    from tools.tests import game_camera_sound_callback_151277b0_register_proof as allocation
    allocation.run()
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
    SOURCE='conker/src/game_14FF90.c';OBJECT='conker/build/src/game_14FF90.c.o';FUNCTION='func_151277B0'
    compact=out/'qualified-source/candidate.o';selected=(out/'qualified-source/selected-owner.c').read_text()
    guards=out/'qualified-guards.csv'
    assert sha(root/'conker/retail_word_patches.us.csv') in (MANIFEST['inputs']['conker/retail_word_patches.us.csv'],MANIFEST['guard_sha256'])
    assert len(re.findall(r',func_151277B0,',guards.read_text()))==42
    def assemble(name,text):
        p=where/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True)
        return obj
    truth=assemble('retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(root/'conker/asm/nonmatchings/game_14FF90/func_151277B0.s').read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    from tools.tests.game_camera_sound_callback_151277b0_register_proof import prove
    SYMS={'func_100111C8':0x100111C8,'D_800BE9E4':0x800BE9E4}
    proof=prove(bound_blob(*payload(compact,FUNCTION),SYMS),bound_blob(*payload(truth,FUNCTION),SYMS))
    assert len(proof['changed_GPR_only_words'])==42
    text=pc.emit_padded_assembly(compact,root/'conker/retail_layout.us.txt','game_14FF90',word_patches_path=guards)
    padded=assemble('padded',text)
    assert payload(padded,FUNCTION)==payload(truth,FUNCTION)
    assert same_functions(base/OBJECT,padded,(FUNCTION,))==44
    old=pg.parse_object(base/OBJECT);new=pg.parse_object(padded)
    for n,f in old[1].items():
        expected=dict(f)
        if n==FUNCTION:expected['size']=496
        assert new[1][n]==expected,(n,f,new[1][n])
    (where/'after-diagnostics.txt').write_text((out/'qualified-source/candidate-diagnostics.txt').read_text())
    make=route.actual_Make(root,where,padded,compact,guards,SOURCE,OBJECT,selected,'target',45)
    linked_owner=where/'qualified-owner/game_14FF90.c.o';linked_owner.parent.mkdir(exist_ok=True)
    shutil.copyfile(padded,linked_owner);assert linked_owner.read_bytes()==padded.read_bytes()
    with patch.multiple(linker,FILENAME='game_14FF90',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        image=linker.link_image(root,where,linked_owner,'image')
    before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
    at=elf_slot_offset(predicted,0x151277B0,496);predicted[at:at+496]=(root/'conker/conker.us.bin').read_bytes()[0x154c60:0x154e50]
    matches=[(at,row)for at,n,row,_ in symbol_rows(predicted)if n==FUNCTION];assert len(matches)==1
    at,row=matches[0];previous_size=old[1][FUNCTION]['size'];assert row[1:3]==(0x151277B0,previous_size)
    struct.pack_into('>I',predicted,at+8,496)
    actual=image.read_bytes();assert len(actual)==len(predicted)
    differences=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
    (where/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected image bytes',len(differences),differences[:20])
    (where/'predicted.elf').write_bytes(predicted)
    functions,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    r=dict(raw_register_equivalence_proved=True,padded_equal_original=True,words=124,frame=48,guards=42,insertions=0,omissions=0,
     owner_functions=45,unchanged_owner_functions=44,actual_Make=make,strict_predicted_ELF_equal=True,
     changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,function_slots=len(functions),
     ELF_sha256=hashlib.sha256(actual).hexdigest(),previous_symbol_size=previous_size,symbol_definitions_preserved_except_target_size=True,
     protected_data_audit=audit_layout(image,root/'conker'),
     source_installed=installed(),matching_credit=0)
    (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    return r
