"""Restore the owner-relative point update with its retail private layout."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_selector_point_transform as previous
from tools.tests import selector_point_checkpoint as checkpoint
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-halfword-point-update'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11F780','func_150F25A0',0x150F25A0,0x11FA50,256
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
changed={previous.PATHS[k]:v for k,v in checkpoint.AFTER.items()}
for key,path in PATHS.items():
    if path in changed:BASELINE[key]=changed[path]
for key,path,sha in (
    ('selector_checkpoint','tools/tests/selector_point_checkpoint.py','45d21b729ee971cd7b624e4bcfeaf5cf23bd08511c968e7f7b191b1a46ae4b2c'),
    ('selector_tests','tools/tests/test_game_selector_point_transform.py','26d7511ce568965a87f81f4fe6780c4a473114d235c113bd132686a138022dc0'),
    ('callback_table','conker/asm/data/22FB90.rodata.s','e00d83a0d1b9673caec4f42f0a6defee0d4050c764db1000a6bd518beb3265b9'),
    ('rotation_trig_original','conker/asm/DAC30.s','e87dccfd5380ec9dd31b4dfe07176cf3745f0a86f2b748ed4896e531bb41f851')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='void func_150A7960(f32 matrix[4][4], f32 x, f32 y, f32 z, f32 *outX, f32 *outY, f32 *outZ);\n'
SELECTED='''/* Transform the owner-relative point into the destination's signed halfwords. */
s32 func_150F25A0(u8 *record) {
    u8 **owner = (u8 **)(record + 0x18);
    f32 point[3];
    f32 matrix[4][4];

    func_150A8050(matrix, *(f32 *)(*owner + 0x20) * 3.0f, 0.0f,
                 *(f32 *)(*owner + 0x28) * 3.0f);
    matrix[3][0] = *(f32 *)(*owner + 0x38);
    matrix[3][1] = *(f32 *)(*owner + 0x3C);
    matrix[3][2] = *(f32 *)(*owner + 0x40);
    func_150A7960(matrix, 0.0f, -495.0f, 0.0f, &point[0], &point[1], &point[2]);
    *(s16 *)(*(u8 **)(record + 0x14) + 0x0E) = (s32)point[0];
    *(s16 *)(*(u8 **)(record + 0x14) + 0x10) = (s32)point[1];
    *(s16 *)(*(u8 **)(record + 0x14) + 0x12) = (s32)point[2];
    return 1;
}'''
RAW_SHA='a88257f8d4d0f0e76066ffeb2598f56620b3db0c59fda581fc539b59e175c5fb'
BINDINGS={64:[('R_MIPS_26','func_150A8050')],156:[('R_MIPS_26','func_150A7960')]}
SYMBOLS={'func_150A8050':0x150A8050,'func_150A7960':0x150A7960}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import halfword_point_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed halfword-point live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed halfword-point frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION);anchor='extern u8 D_800BE9C0;'
    if before[lo:hi]!='s32 func_150F25A0() {\n    return 0;\n}' or before.count(anchor)!=1:
        raise ValueError('Unknown halfword-point predecessor')
    return (before[:lo]+body+before[hi:]).replace(anchor,anchor+'\n'+TYPE,1)


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete halfword-point words/bindings')


def padded_object(root,out,obj,label):return previous.padded_object(root,out,obj,label)


def raw_object(root,out,obj,label):
    data,fs,rs=parse_object(obj)
    text,unknown=emit_function(data,fs[FUNCTION],rs,FUNCTION,SYMBOLS)
    if unknown:raise ValueError('Unknown halfword-point raw binding '+repr(unknown))
    asm=out/(label+'-raw.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-fixed_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Halfword-point compiler diagnostics')
    checked_parts(*parts(obj))
    if normalized_pools(old)!=normalized_pools(obj):raise ValueError('Changed halfword-point owner pools')
    neighbors=same_functions(old,obj,(FUNCTION,));padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Halfword-point padded neighbors changed')
    rom=(out/'before-retail_rom').read_bytes()
    if struct.unpack_from('>I',rom,0x22FC08)[0]!=ENTRY:raise ValueError('Changed registered halfword-point callback')
    images=[]
    for path in (raw_object(root,out,obj,'candidate'),padded):
        data,fs=build.link_owner(root,out,path,OWNER)
        images.append(list(struct.unpack_from('>64I',data,fs[FUNCTION]['value'])))
    truth=list(struct.unpack_from('>64I',rom,ROM))
    if images!=[truth,truth]:raise ValueError('Incomplete direct halfword-point match')
    row=dict(words=64,frame=136,bindings=2,new_guards=0,raw_differences=0,
        unchanged_raw_padded_neighbors=neighbors,owner_pools_unchanged=True,
        matrix_offset=56,point_offset=120,callback_table_slot=22,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
