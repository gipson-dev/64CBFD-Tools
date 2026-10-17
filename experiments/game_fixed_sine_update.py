"""Recover the complete fixed-state actor sine updater directly from C."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_sine_phase_update as previous
from tools.tests import sine_phase_update_checkpoint as checkpoint
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-fixed-sine-update'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11F780','func_150F23E0',0x150F23E0,0x11F890,160
PATHS=dict(previous.PATHS)
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,**checkpoint.EXTRA_AFTER)
for key,path,sha in (
    ('fixed_owner','conker/src/game/generated_11F780.c','2a0a2a01c621241a9c495441157e350556798df089b43b885347960ac8b3d0c5'),
    ('fixed_table','conker/asm/data/22E370.rodata.s','42925f1b2e64e1ad241cff05afa857ab4dc3b9e812a2764ef360885fdc2c2612'),
    ('fixed_caller','conker/asm/15F680.s','f697fe44a7ea8c4c6a7a7016236764a088a6922f559686ee4d3731d5c264413b'),
    ('phase_checkpoint','tools/tests/sine_phase_update_checkpoint.py','9fdb57258f8c6dd4f9c03a365fb4768910ff5a219042080d9f28b29fe7652592'),
    ('phase_tests','tools/tests/test_game_sine_phase_update.py','fb932f59cc95201256f47bfb5f35f47e24066c1333520a5ea58013f4f70f932a')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
SELECTED='''/* Update actor offsets from fixed sine state, then advance both phases. */
s32 func_150F23E0(u8 *actor) {
    f32 *state = (f32 *)(actor + 0x170);

    *(f32 *)(actor + 0x20) = state[4] * sinf(state[0]);
    *(f32 *)(actor + 0x28) = state[5] * sinf(state[1]);
    state[0] = func_15144B68(state[2] * D_800BE9A4 + state[0]);
    state[1] = func_15144B68(state[3] * D_800BE9A4 + state[1]);
    return 1;
}'''
RAW_SHA='846afc8acc047da0650dcba607e22f53fe7824e1f0b821177bf360824ba34f96'
BINDINGS={20:[('R_MIPS_26','sinf')],48:[('R_MIPS_26','sinf')],
    64:[('R_MIPS_HI16','D_800BE9A4')],76:[('R_MIPS_LO16','D_800BE9A4')],
    92:[('R_MIPS_26','func_15144B68')],104:[('R_MIPS_HI16','D_800BE9A4')],
    108:[('R_MIPS_LO16','D_800BE9A4')],124:[('R_MIPS_26','func_15144B68')]}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import fixed_sine_update_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed fixed-sine live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed fixed-sine frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150F23E0() {\n    return 0;\n}':raise ValueError('Unknown fixed-sine predecessor')
    return before[:lo]+body+before[hi:]


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete fixed-sine words/bindings')


def padded_object(root,out,obj,label):
    text=emit_padded_assembly(obj,out/'before-phase_original',word_patches_path=out/'before-guards',filename=OWNER)
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-fixed_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Fixed-sine compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Fixed-sine owner pools changed')
    neighbors=same_functions(old,obj,(FUNCTION,));padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Fixed-sine padded neighbors changed')
    images=[]
    for path in (obj,padded):
        data,fs=build.link_owner(root,out,path,OWNER)
        images.append(list(struct.unpack_from('>40I',data,fs[FUNCTION]['value'])))
    truth=list(struct.unpack_from('>40I',(out/'before-retail_rom').read_bytes(),ROM))
    if images!=[truth,truth]:raise ValueError('Incomplete direct fixed-sine match')
    row=dict(words=40,frame=32,bindings=8,new_guards=0,raw_differences=0,
        unchanged_raw_padded_neighbors=neighbors,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
