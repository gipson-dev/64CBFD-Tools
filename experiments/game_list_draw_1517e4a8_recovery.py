"""Complete private C recovery; matching/installation credit remains zero."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_list_owner_make import actual_Make
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-list-draw-1517e4a8-private';WHERE=OUT/'qualified-screen';BASE=OUT/'baseline'
SPEC=json.loads(Path(__file__).with_name('game_list_draw_1517e4a8_manifest.json').read_text())
BODY,PREAMBLE=SPEC['body'],SPEC['preamble'];FUNCTION='func_1517E4A8';ENTRY,ROM=0x1517E4A8,0x1AB958
SOURCE='conker/src/game/generated_1AB530.c';HELPER='conker/src/game/generated_C1D70.c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def screen():
    WHERE.mkdir(parents=True,exist_ok=True)
    for n,d in SPEC['inputs'].items():assert sha(ROOT/n)==d,n
    before=(ROOT/SOURCE).read_text();selected=before.replace('Gfx *func_1517E4A8();','Gfx *func_1517E4A8(Gfx *, ListRecord1AB530 *, s32, s32, s32, s32, u8 *);')
    selected=selected.replace('Gfx *func_1517E4A8() {\n    return 0;\n}',PREAMBLE+'\n'+BODY);assert selected!=before
    old,bd=compile_owner(ROOT,WHERE,before,'before');after,ad=compile_owner(ROOT,WHERE,selected,'candidate');assert not bd and not ad,(bd,ad)
    raw,refs=payload(after,FUNCTION);assert hashlib.sha256(raw).hexdigest()==SPEC['raw_sha256']and json.loads(json.dumps(refs))==SPEC['raw_refs']
    words=bind(raw,refs);truth=struct.unpack_from('>361I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    helper=(ROOT/HELPER).read_text();ha,hd=compile_owner(ROOT,WHERE,helper,'helper-before');hb,hbd=compile_owner(ROOT,WHERE,SPEC['selected_helper'],'helper-after')
    assert not hd and not hbd,(hd,hbd)
    assert normalized_pools(old)==normalized_pools(after)and normalized_pools(ha)==normalized_pools(hb)
    report=dict(words=len(words),frame=(-words[0])&65535,positional_differences=sum(a!=b for a,b in zip(words,truth)),
        raw_sha256=hashlib.sha256(raw).hexdigest(),unchanged_owner_neighbors=same_functions(old,after,(FUNCTION,)),
        unchanged_helper_functions=same_functions(ha,hb,()),pools_unchanged=True,diagnostics='',source_installed=False,matching_credit=0)
    (WHERE/'selected-owner.c').write_text(selected);(WHERE/'after-diagnostics.txt').write_text('');(WHERE/'helper-after-diagnostics.txt').write_text('')
    (WHERE/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report

def integration():
    def assemble(name,text):
        p=WHERE/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);return obj
    guards=ROOT/'conker/retail_word_patches.us.csv';results={}
    for label,source,owner,asm,compact,count in(('target',SOURCE,'generated_1AB530','1AB530','candidate.o',8),('helper',HELPER,'generated_C1D70','C1D70','helper-after.o',19)):
        obj=WHERE/compact
        a=assemble(label+'-layout',pc.emit_padded_assembly(obj,ROOT/'conker/retail_layout.us.txt',owner,word_patches_path=guards))
        b=assemble(label+'-asm',pg.emit_padded_assembly(obj,ROOT/('conker/asm/'+asm+'.s'),filename=owner,word_patches_path=guards))
        assert a.read_bytes()==b.read_bytes()
        object_path='conker/build/src/game/'+owner+'.c.o'
        if label=='helper':assert a.read_bytes()==(BASE/object_path).read_bytes()
        selected=(WHERE/'selected-owner.c').read_text()if label=='target'else SPEC['selected_helper']
        result=actual_Make(ROOT,WHERE,a,obj,guards,source,object_path,selected,label,count)
        assert result['commands']==3 and result['natural_live_recipe'];results[label]=result
    report=dict(padders_equal=True,helper_complete_padded_object_unchanged=True,actual_Make=results,source_installed=False,
        production_build_or_whole_image_claim=False,matching_credit=0)
    (WHERE/'integration.json').write_text(json.dumps(report,indent=2)+'\n');return report
