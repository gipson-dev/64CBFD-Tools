"""List unlink/free: typed two-argument ABI, one independently checked dead home."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_list_owner_make import actual_Make
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.experiments.game_list_historical_image import historical_dependencies

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-list-unlink-1517e134-private'
BASE=OUT/'baseline';WHERE=OUT/'qualification'
SPEC=json.loads(Path(__file__).with_name('game_list_unlink_1517e134_manifest.json').read_text())
FUNCTION,SOURCE,CALLER=SPEC['function'],SPEC['source'],SPEC['caller']
ENTRY,ROM=SPEC['entry'],SPEC['rom'];OBJECT='conker/build/src/game/generated_1AB530.c.o'
sha=lambda b:hashlib.sha256(b).hexdigest()

def derive(raw,refs):
    if sha(raw)!=SPEC['raw_sha256']:raise ValueError('Changed unlink payload')
    if json.loads(json.dumps(refs))!=SPEC['refs']:raise ValueError('Changed unlink bindings')
    words=struct.unpack('>31I',raw)
    assert words[0]==0x27BDFFE8 and words[4]==0xAFA5001C
    # The only deleted instruction writes incoming SP+4. The address never escapes,
    # no instruction reads it, and no retained instruction reads the unused A1.
    stack=[];reads_a1=[]
    for i,w in enumerate(words):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op in(35,43)and rs==29:stack.append((i,op,rt,w&65535))
        if rs==5 or(op in(4,5,20,21,43)and rt==5):reads_a1.append(i)
        if rs==29:assert(op in(35,43)or w in(0x27BDFFE8,0x27BD0018)),(i,hex(w))
        if op==0 and rt==29:raise AssertionError('SP-derived value escapes')
        if op==0 and rd==29:assert w==0,(i,hex(w))
        if op in(4,5,20,21):
            displacement=((w&65535)^32768)-32768;target=i+1+displacement
            assert i>4 and target>4,(i,target)
    assert reads_a1==[4] and stack==[(3,43,31,20),(4,43,5,28),(22,35,31,20),(27,35,31,20)],stack
    assert 16 not in refs
    return raw[:16]+raw[20:],{at-(4 if at>16 else 0):rs for at,rs in refs.items()}

def bind(raw,refs,code_shift=0,data_shift=0):
    anchors={n:int(n.split('_')[1],16)+(code_shift if n.startswith('func_')else data_shift)for rows in refs.values()for _,n in rows}
    return tuple(bound_blob(raw,refs,anchors))

def assemble(name,text):
    p=WHERE/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],check=True,capture_output=True)
    return obj

def prepare():
    WHERE.mkdir(parents=True,exist_ok=True)
    for n,d in SPEC['inputs'].items():assert sha((ROOT/n).read_bytes())==d,n
    snapshot={'source_sha256':sha((ROOT/SOURCE).read_bytes()),'guards_sha256':sha((ROOT/'conker/retail_word_patches.us.csv').read_bytes())}
    compatible=snapshot in SPEC.get('compatible_installed_snapshots',[])
    for n,old,new in((SOURCE,'old_source','selected'),(CALLER,'old_caller','selected_caller')):
        assert(compatible and n==SOURCE)or(ROOT/n).read_text()in(SPEC[old],SPEC[new]),n
    before,bd=compile_owner(ROOT,WHERE,SPEC['old_source'],'before')
    after,ad=compile_owner(ROOT,WHERE,SPEC['selected'],'candidate');assert not bd and not ad,(bd,ad)
    raw,refs=payload(after,FUNCTION);derived,bindings=derive(raw,refs)
    full=(ROOT/'conker/asm/1AB530.s').read_text();a=full.index('glabel '+FUNCTION+'\n');b=full.index('endlabel '+FUNCTION,a)+len('endlabel '+FUNCTION)
    original=assemble('original','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+full[a:b]+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    assert payload(original,FUNCTION)==payload(before,FUNCTION)==(derived,bindings)
    truth=struct.unpack_from('>30I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM);assert bind(derived,bindings)==truth
    assert same_functions(before,after,(FUNCTION,))==7 and normalized_pools(before)==normalized_pools(after)
    oldc,cd=compile_owner(ROOT,WHERE,SPEC['old_caller'],'caller-before');newc,dd=compile_owner(ROOT,WHERE,SPEC['selected_caller'],'caller-after')
    assert not cd and not dd,(cd,dd)
    assert same_functions(oldc,newc,())==16 and normalized_pools(oldc)==normalized_pools(newc)
    (WHERE/'after-diagnostics.txt').write_text('');(WHERE/'caller-after-diagnostics.txt').write_text('')
    return after,raw,refs,truth,newc

def qualify():
    after,raw,refs,truth,newc=prepare();old=(BASE/'conker/retail_word_patches.us.csv').read_bytes()
    assert sha(old)==SPEC['guards_before_sha256']
    proposed=old+SPEC['append_guards'].encode();assert sha(proposed)==SPEC['guards_after_sha256']
    guards=WHERE/'proposed-guards.csv';guards.write_bytes(proposed)
    snapshot={'source_sha256':sha((ROOT/SOURCE).read_bytes()),'guards_sha256':sha((ROOT/'conker/retail_word_patches.us.csv').read_bytes())}
    assert snapshot in SPEC.get('compatible_installed_snapshots',[])or snapshot['guards_sha256']in(SPEC['guards_before_sha256'],SPEC['guards_after_sha256'])
    objects=[]
    for label,text in(('layout',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt','generated_1AB530',word_patches_path=guards)),
        ('asm',pg.emit_padded_assembly(after,ROOT/'conker/asm/1AB530.s',filename='generated_1AB530',word_patches_path=guards))):
        objects.append(assemble(label,text))
    assert objects[0].read_bytes()==objects[1].read_bytes()==(BASE/OBJECT).read_bytes()
    caller_object='conker/build/src/game_16DC80.c.o'
    caller=assemble('caller-pad',pc.emit_padded_assembly(newc,ROOT/'conker/retail_layout.us.txt','game_16DC80',word_patches_path=guards))
    assert caller.read_bytes()==(BASE/caller_object).read_bytes()
    route=actual_Make(ROOT,WHERE,objects[0],after,guards,SOURCE,OBJECT,SPEC['selected'],'target',8)
    caller_route=actual_Make(ROOT,WHERE,caller,newc,guards,CALLER,caller_object,SPEC['selected_caller'],'caller',16)
    with historical_dependencies(ROOT,WHERE,SOURCE,SPEC)as script:
        with patch.multiple(linker,FILENAME='generated_1AB530',OBJECT=OBJECT,LINKER=script):
            image=linker.link_image(ROOT,WHERE,objects[0],'image')
    expected=(BASE/'conker/build/conker.us.elf').read_bytes();assert image.read_bytes()==expected
    fs,_,_=load_elf_functions(image,'mips-linux-gnu-objdump');assert len(fs)==6051
    report=dict(raw_words=31,normalized_words=30,frame=24,omitted_unused_home_words=1,unchanged_owner_neighbors=7,
        typed_caller_functions_unchanged=16,complete_owner_and_caller_objects_equal=True,actual_Make=route,caller_actual_Make=caller_route,
        strict_predicted_ELF_equal=True,changed_bytes=0,exclusions=0,function_slots=len(fs),protected_data_audit=audit_layout(image,ROOT/'conker'),
        ELF_sha256=sha(expected),source_installed=snapshot in SPEC.get('compatible_installed_snapshots',[])or(ROOT/SOURCE).read_text()==SPEC['selected'],credit=0)
    (WHERE/'integration.json').write_text(json.dumps(report,indent=2)+'\n');return report
