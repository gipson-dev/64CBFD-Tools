"""Recover the indexed floating-threshold mask updater directly from C."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_actor_record_gate_recovery as previous
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-indexed-threshold-mask'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11FF10','func_150F33F8',0x150F33F8,0x1208A8,168
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
for key,path,sha in (
    ('record_gate_recovery','tools/experiments/game_actor_record_gate_recovery.py','69a500bf9dfad8759032b538bea7c0e834e00cbd29b8649b62279d095468f079'),
    ('record_gate_tests','tools/tests/test_game_actor_record_gate_recovery.py','a2b17696c71dbc859101b7fc13876be764c0c581d0f20c6dd0f28d932049477c'),
    ('actor_state_checkpoint','tools/tests/actor_state_checkpoint.py','e121cbaa315d1cfbe7da84dbd5810a0bec89d45acf5b61f89e7fc2969e09bb5d'),
    ('actor_state_tests','tools/tests/test_game_actor_state_update.py','95de69bc15e81a4744234c087f77e55b447c249748b713641d4d12fe3e379801')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='extern f32 D_800A1970;\nextern s16 *D_800D9A40;\n'
SELECTED='''/* Update an indexed state-mask bit from two floating-point thresholds. */
void func_150F33F8(s32 index) {
    u8 *record = (u8 *)((s32)D_800DBFF0 + index * 0x9A0);

    if (*(f32 *)(record + 0x300) < D_800A1970) {
        if (*(f32 *)(record + 0x2FC) > 840.0f) {
            *D_800D9A40 |= 1 << index;
        } else {
            *D_800D9A40 &= ~(1 << index);
        }
    }
}'''
RAW_SHA='f190d637af70139d106d0522a200f0a061c7c1aacd2e724ea3230c607e3e6204'
SYMBOLS={'D_800DBFF0':0x800DBFF0,'D_800A1970':0x800A1970,'D_800D9A40':0x800D9A40}
BINDINGS={16:[('R_MIPS_HI16','D_800DBFF0')],20:[('R_MIPS_LO16','D_800DBFF0')],
    36:[('R_MIPS_HI16','D_800A1970')],48:[('R_MIPS_LO16','D_800A1970')],
    80:[('R_MIPS_HI16','D_800D9A40')],100:[('R_MIPS_HI16','D_800D9A40')],
    104:[('R_MIPS_LO16','D_800D9A40')],132:[('R_MIPS_LO16','D_800D9A40')]}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import indexed_threshold_mask_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed threshold-mask live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed threshold-mask frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150F33F8() {\n    return 0;\n}':raise ValueError('Unknown threshold-mask predecessor')
    anchor='#include <ultra64.h>'
    if before.count(anchor)!=1:raise ValueError('Unknown threshold-mask declaration anchor')
    return (before[:lo]+body+before[hi:]).replace(anchor,anchor+'\n'+TYPE,1)


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete threshold-mask words/bindings')


def padded_object(root,out,obj,label):
    text=emit_padded_assembly(obj,out/'before-record_gate_original',filename=OWNER,word_patches_path=out/'before-guards')
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def raw_object(root,out,obj,label,symbols=None):
    data,fs,rs=parse_object(obj);text,unknown=emit_function(data,fs[FUNCTION],rs,FUNCTION,symbols or SYMBOLS)
    if unknown:raise ValueError('Unknown threshold-mask bindings '+repr(unknown))
    asm=out/(label+'-raw.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-record_gate_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Threshold-mask compiler diagnostics')
    checked_parts(*parts(obj))
    if normalized_pools(old)!=normalized_pools(obj):raise ValueError('Changed threshold-mask owner pools')
    neighbors=same_functions(old,obj,(FUNCTION,));padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Changed threshold-mask padded neighbors')
    images=[]
    for path in (raw_object(root,out,obj,'candidate'),padded):
        data,fs=build.link_owner(root,out,path,OWNER)
        images.append(list(struct.unpack_from('>42I',data,fs[FUNCTION]['value'])))
    truth=list(struct.unpack_from('>42I',(out/'before-retail_rom').read_bytes(),ROM))
    if images!=[truth,truth]:raise ValueError('Incomplete direct threshold-mask match')
    result=dict(words=42,frame=0,raw_differences=0,new_guards=0,bindings=8,
        unchanged_raw_padded_neighbors=neighbors,owner_pools_unchanged=True,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return obj,padded,images,result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
