"""Recover the complete counter-gated actor update directly from semantic C."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_white_text_fade as previous
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-actor-counter-motion'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_E5E90','func_150B9560',0x150B9560,0xE6A10,156
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
for key,path,sha in (
    ('motion_owner','conker/src/game/generated_E5E90.c','663bb803d6652eb22368a6de5665a1eff2ac415a9b0a4a5ab8db5aabfc8f54f5'),
    ('motion_original','conker/asm/E5E90.s','0876b25394911af7ad6fd2f6dadf9ab1c6d37677abb57c0f3954f639a469609d'),
    ('motion_constants','conker/asm/data/244870.rodata.s','cc2110479c261f6e32fb9bfeab23f5827d5d8c22515f6a9d6e469353884d592e'),
    ('motion_table','conker/asm/data/22E730.rodata.s','04adc08432aaa1052219d977d68d9769ac85e1efca4aa89b8b35b8cddedf8413'),
    ('motion_caller','conker/asm/nonmatchings/game_169510/func_1513CFE4.s','cbdedd2bb802ac4c33454cdd7c62417b531e263524f5a79757fd5697e3d82815'),
    ('white_source','tools/experiments/game_white_text_fade.py','d6c3009def779cecd928124b136c20c22d26e750f74981f78055e0b31a5b63ec'),
    ('white_tests','tools/tests/test_game_white_text_fade.py','d491d6baebeae57f63ecc4ccb3a519c3bc5dd053472b83b74914ad09b70f1f32'),
    ('reveal_checkpoint','tools/tests/text_reveal_checkpoint.py','d98f4d3103b5b0bead72194c693443dba2c390418062d27e2c886defc4b81420'),
    ('reveal_tests','tools/tests/test_game_text_reveal_renderer.py','3736c2cc9facc562a29cab0f36c390c26c4babf6c4f76159a2963f5ad9be5ce8')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='extern f32 D_8009FDD4, D_8009FDD8, D_8009FDDC, D_800BE9A4;\n'
SELECTED='''/* Apply the actor's counter-gated motion updates. */
s32 func_150B9560(u8 *actor) {
    f32 *step = (f32 *)(actor + 0x110);
    f32 factor;

    if (*(s16 *)(actor + 0x1C) < 80) {
        *step += D_8009FDD4 * D_800BE9A4;
        *(f32 *)(actor + 0x38) -= *step;
    }
    if (*(s16 *)(actor + 0x1C) >= 115) {
        factor = D_8009FDD8;
        *(f32 *)(actor + 0x2C) *= factor;
        *(f32 *)(actor + 0x30) *= factor;
    } else if (*(s16 *)(actor + 0x1C) < 65) {
        *(f32 *)(actor + 0x30) += D_8009FDDC;
    }
    return 1;
}'''
RAW_SHA='ca4fe8840677bb4a178792680924a963f940a18e218c82fe18ce025917422863'
BINDINGS={12:[('R_MIPS_HI16','D_8009FDD4')],16:[('R_MIPS_LO16','D_8009FDD4')],
    20:[('R_MIPS_HI16','D_800BE9A4')],24:[('R_MIPS_LO16','D_800BE9A4')],
    80:[('R_MIPS_HI16','D_8009FDD8')],84:[('R_MIPS_LO16','D_8009FDD8')],
    128:[('R_MIPS_HI16','D_8009FDDC')],132:[('R_MIPS_LO16','D_8009FDDC')]}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import actor_counter_motion_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed counter-motion live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed counter-motion frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150B9560() {\n    return 0;\n}' or before.count('#include <ultra64.h>\n')!=1:
        raise ValueError('Unknown actor counter-motion predecessor')
    return (before[:lo]+body+before[hi:]).replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+TYPE,1)


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete counter-motion words/bindings')


def padded_object(root,out,obj,label):
    text=emit_padded_assembly(obj,out/'before-motion_original',word_patches_path=out/'before-guards',filename=OWNER)
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-motion_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Counter-motion compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Counter-motion owner pools changed')
    neighbors=same_functions(old,obj,(FUNCTION,));padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Counter-motion padded neighbors changed')
    images=[]
    for path in (obj,padded):
        data,fs=build.link_owner(root,out,path,OWNER)
        images.append(list(struct.unpack_from('>39I',data,fs[FUNCTION]['value'])))
    truth=list(struct.unpack_from('>39I',(out/'before-retail_rom').read_bytes(),ROM))
    if images[0]!=truth or images[1]!=truth:raise ValueError('Incomplete actor counter-motion match')
    row=dict(words=39,frame=0,bindings=8,new_guards=0,unchanged_raw_padded_neighbors=neighbors,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
