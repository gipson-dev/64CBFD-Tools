"""Qualify the direct-C randomized burst and its typed, still-unfinished callee."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pad
NAME='func_1517AA20'; HELPER='func_1517A644'; ENTRY=0x1517AA20; ROM=0x1A7ED0; SIZE=348
SOURCE='conker/src/game/generated_1A7260.c'; BUILD='conker/build/game-randomized-burst-1517aa20-screen'
SELECTED='''/* Emit a randomized burst around the supplied position when its size permits. */
void func_1517AA20(f32 size, s32 x, s32 yArgument, s32 z, s32 count) {
    s32 dx;
    s32 dz;
    s32 i;
    s32 range;
    f32 pieceSize;
    s32 kind;
    s16 y;

    if (size < 12.0f) {
        return;
    }
    range = size * 8.0f;
    size *= 0.5f;
    y = yArgument;
    for (i = 0; i < count; i++) {
        dx = func_150ADA20() & 63;
        dz = func_150ADA20() & 63;
        dx -= 32;
        dz -= 32;
        pieceSize = (f32)(((u32)func_150ADA20() % range) >> 4) + size;
        kind = func_150ADA20();
        func_1517A644(pieceSize, kind & 1, (s16)((u32)x + (u32)dx), y,
                     (s32)((u32)z + (u32)dz));
    }
}'''
TYPED_HELPER='s32 func_1517A644(f32 size, u8 kind, s16 x, s16 y, s32 z) {\n    return 0;\n}'
def proposed(before):
    assert body(before,NAME)=='s32 func_1517AA20() {\n    return 0;\n}'
    assert body(before,HELPER)=='s32 func_1517A644() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace(body(before,HELPER),TYPED_HELPER).replace('#include <ultra64.h>','#include <ultra64.h>\n\ns32 func_150ADA20(void);')
def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    live=(root/SOURCE).read_text();installed='void '+NAME+'(' in live
    before=(out/'production-baseline'/SOURCE).read_text() if installed else live
    proposal=proposed(before);assert not installed or proposal==live
    old,diagnostics=compile_owner(root,out,before,'baseline');obj,new_diagnostics=compile_owner(root,out,proposal,'selected');assert diagnostics==new_diagnostics==''
    raw,refs=payload(obj,NAME);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
    assert len(raw)==SIZE and bound_blob(raw,refs)==list(struct.unpack('>87I',truth))
    assert refs=={at:[('R_MIPS_26',name)] for at,name in ((140,'func_150ADA20'),(148,'func_150ADA20'),(164,'func_150ADA20'),(224,'func_150ADA20'),(276,HELPER))}
    assert same_functions(old,obj,(NAME,HELPER))==9 and normalized_pools(old)==normalized_pools(obj)
    assert payload(obj,HELPER)==(struct.pack('>7I',0xE7AC0000,0xAFA50004,0xAFA60008,0xAFA7000C,0x00001025,0x03E00008,0),{})
    assert len(payload(old,HELPER)[0])==12
    assembly=(root/'conker/asm/1A7260.s').read_text();a=assembly.index('glabel '+NAME+'\n');z=assembly.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (out/'proposed-guards.csv').write_bytes((root/'conker/retail_word_patches.us.csv').read_bytes())
    (out/'guarded.s').write_text(pad.emit_padded_assembly(obj,root/'conker/asm/1A7260.s',filename='generated_1A7260',word_patches_path=out/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=root/'conker',capture_output=True,check=True)
        assert payload(out/(label+'.o'),NAME)==(raw,refs)
    report=dict(words=87,frame=80,guards=0,neighbors=9,typed_unfinished_helper=HELPER,helper_words=7,installed=installed,raw_sha256=hashlib.sha256(raw).hexdigest())
    (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
