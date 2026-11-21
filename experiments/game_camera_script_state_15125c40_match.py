"""Direct camera-script countdown recovery, natural Make and strict image gates."""
from pathlib import Path
import hashlib,json,os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_camera_script_state_15125c40_manifest.json').read_text())
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
        assert sha(ROOT/n)in permitted,n
    old_dir=OUT/'source-screen';new_dir=OUT/'variant-s32-first'
    old_dir.mkdir(exist_ok=True);new_dir.mkdir(exist_ok=True)
    a,ad=compile_owner(ROOT,old_dir,MANIFEST['old_source'],'before')
    b,bd=compile_owner(ROOT,new_dir,MANIFEST['selected_source'],'candidate')
    assert diagnostic_rows(ad)==diagnostic_rows(bd)
    assert same_functions(a,b,(FUNCTION,))==44 and normalized_pools(a)==normalized_pools(b)
    assert hashlib.sha256(payload(b,FUNCTION)[0]).hexdigest()==MANIFEST['raw_sha256']
    (new_dir/'selected-owner.c').write_text(MANIFEST['selected_source'])
    return dict(installed=installed(),unchanged_neighbors=44,guards=0,words=93,frame=40)
def qualify():
    prepare()
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
    base=out/'baseline';where=out/'image-qualification';where.mkdir(exist_ok=True)
    SOURCE='conker/src/game_14FF90.c';OBJECT='conker/build/src/game_14FF90.c.o';FUNCTION='func_15125C40'
    compact=out/'variant-s32-first/candidate.o';selected=(out/'variant-s32-first/selected-owner.c').read_text()
    guards=root/'conker/retail_word_patches.us.csv'
    assert guards.read_bytes()==(base/'conker/retail_word_patches.us.csv').read_bytes()
    assert not re.search(r',func_15125C40,',guards.read_text())
    def assemble(name,text):
        p=where/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True)
        return obj
    truth=assemble('retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(root/'conker/asm/nonmatchings/game_14FF90/func_15125C40.s').read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    assert payload(truth,FUNCTION)==payload(compact,FUNCTION)
    text=pc.emit_padded_assembly(compact,root/'conker/retail_layout.us.txt','game_14FF90',word_patches_path=guards)
    padded=assemble('padded',text)
    assert payload(padded,FUNCTION)==payload(truth,FUNCTION)
    assert same_functions(base/OBJECT,padded,(FUNCTION,))==44
    old=pg.parse_object(base/OBJECT);new=pg.parse_object(padded)
    for n,f in old[1].items():
        expected=dict(f)
        if n==FUNCTION:expected['size']=372
        assert new[1][n]==expected,(n,f,new[1][n])
    (where/'after-diagnostics.txt').write_text((out/'variant-s32-first/candidate-diagnostics.txt').read_text())
    make=route.actual_Make(root,where,padded,compact,guards,SOURCE,OBJECT,selected,'target',45)
    linked_owner=where/'qualified-owner/game_14FF90.c.o';linked_owner.parent.mkdir(exist_ok=True)
    shutil.copyfile(padded,linked_owner);assert linked_owner.read_bytes()==padded.read_bytes()
    with patch.multiple(linker,FILENAME='game_14FF90',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        image=linker.link_image(root,where,linked_owner,'image')
    before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
    at=elf_slot_offset(predicted,0x15125C40,372);predicted[at:at+372]=(root/'conker/conker.us.bin').read_bytes()[0x1530f0:0x153264]
    matches=[(at,row)for at,n,row,_ in symbol_rows(predicted)if n==FUNCTION];assert len(matches)==1
    at,row=matches[0];previous_size=old[1][FUNCTION]['size'];assert row[1:3]==(0x15125C40,previous_size)
    struct.pack_into('>I',predicted,at+8,372)
    actual=image.read_bytes();assert len(actual)==len(predicted)
    differences=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
    (where/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected image bytes',len(differences),differences[:20])
    (where/'predicted.elf').write_bytes(predicted)
    functions,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    r=dict(direct_raw_and_padded_equal_original=True,words=93,frame=40,guards=0,insertions=0,omissions=0,
     owner_functions=45,unchanged_owner_functions=44,actual_Make=make,strict_predicted_ELF_equal=True,
     changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,function_slots=len(functions),
     ELF_sha256=hashlib.sha256(actual).hexdigest(),previous_symbol_size=previous_size,protected_data_audit=audit_layout(image,root/'conker'),
     source_installed=installed(),matching_credit=0)
    (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    return r
