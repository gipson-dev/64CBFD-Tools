"""Complete child motion with closed FP roles, scheduling and add-operand order."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_transition_frame_lifetimes as previous
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD='conker/build/game-transition-child-motion-match'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_FC5F0','func_150CFC60',0x150CFC60,0xFD110,48
SIZE=WORDS*4
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
build,compile_owner,projection=previous.build,previous.compile_owner,previous.projection
RAW_SHA='02992176864e66405f1fdf98b7bf9438dee515ff46395010ddc0e0c544b88691'
BINDINGS={at:[(kind,name)] for name,hi,lo in (
    ('D_800BE9A4',0,4),('D_800A0878',132,144),('D_800A087C',152,168))
    for at,kind in ((hi,'R_MIPS_HI16'),(lo,'R_MIPS_LO16'))}
PATCHES={0x14:(0xC4800074,0xC4820074),0x20:(0xC4820078,0x44812000),
    0x24:(0x44812000,0xC48C0078),0x30:(0xC44C0000,0xC4400000),
    0x34:(0x460C0482,0x46001482),0x3C:(0x46022182,0x460C2182),
    0x44:(0x460C3282,0x46003282),0x4C:(0x460C5202,0x46005202),
    0x6C:(0x460A1482,0x460A6482),0x74:(0x46009200,0x46121200)}
DECLARATIONS='''extern f32 D_800A0878, D_800A087C, D_800BE9A4;
f32 fabsf(f32);
#pragma intrinsic (fabsf)
'''
SELECTED='''/* Advance the child and damp its velocity after crossing the floor. */
s32 func_150CFC60(u8 *record) {
    f32 velocityY = *(f32 *)(record + 0x74);
    f32 acceleration = *(f32 *)(record + 0x78);
    f32 *motion;

    *(f32 *)(record + 0x10) += *(f32 *)(record + 0x70) * D_800BE9A4;
    *(f32 *)(record + 0x14) += velocityY * D_800BE9A4 + 0.5f * acceleration * D_800BE9A4 * D_800BE9A4;
    *(f32 *)(record + 0x74) = velocityY + acceleration * D_800BE9A4;
    motion = (f32 *)(record + 0x70);
    if (*(f32 *)(record + 0x7C) < *(f32 *)(record + 0x14)) {
        *(f32 *)(record + 0x14) = motion[3];
        velocityY = fabsf(motion[1]);
        motion[0] *= D_800A0878;
        motion[1] = velocityY * D_800A087C;
    }
    return 1;
}'''


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import transition_child_motion_checkpoint as installed
            data=installed.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            raise ValueError('Unknown child motion input: '+key)
        target=out/('before-'+key)
        if not target.exists(): target.write_bytes(data)
        if target.read_bytes()!=data: raise ValueError('Changed child motion fixture: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150CFC60() {\n    return 0;\n}' or before.count('#include <ultra64.h>\n')!=1:
        raise ValueError('Unknown child motion predecessor')
    return (before[:lo]+body+before[hi:]).replace('#include <ultra64.h>\n',
        '#include <ultra64.h>\n'+DECLARATIONS,1)


def guard_bytes(before):
    rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in rows) or not before.endswith(b'\n'):
        raise ValueError('Unknown child motion guard predecessor')
    fields=next(csv.reader(io.StringIO(before.decode())))
    out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n')
    for offset,(expected,replacement) in PATCHES.items():
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%expected,replacement='0x%08X'%replacement,
            expected_relocations='-',replacement_relocations='-',
            note='Normalize child motion closed FP cycle and setup schedule and add operand order',
            insert_after='',insert_after_relocations='',omit='false'))
    return before+out.getvalue().encode()


def recovered_predecessor_screen(before):
    old='''        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Unknown burst input: ' + key)'''
    new='''        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            from tools.tests import transition_child_motion_checkpoint as installed
            data = installed.previous_input(data, path, root)
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Unknown burst input: ' + key)'''
    if before.count(old)!=1: raise ValueError('Unknown predecessor burst screen')
    return before.replace(old,new,1)


def parts(obj):
    data,functions,relocs=parse_object(obj); f=functions[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in relocs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown complete child motion words/bindings')


def normalize(words):
    if len(words)!=48: raise ValueError('Unknown child motion extent')
    result=list(words); cycle={0:2,2:12,12:0}
    for index in range(5,30):
        w=result[index]; op=w>>26
        if op==49:
            rt=(w>>16)&31; result[index]=(w&~(31<<16))|(cycle.get(rt,rt)<<16)
        elif op==17 and (w>>21)&31==16 and w&63 in (0,2):
            for shift in (16,11,6):
                reg=(w>>shift)&31; w=(w&~(31<<shift))|(cycle.get(reg,reg)<<shift)
            result[index]=w
    result[8],result[9]=result[9],result[8]
    w=result[29]
    if w>>26!=17 or (w>>21)&31!=16 or w&63!=0:
        raise ValueError('Unknown child motion velocity add')
    fs,ft=(w>>11)&31,(w>>16)&31
    result[29]=(w&~((31<<11)|(31<<16)))|(ft<<11)|(fs<<16)
    if {i*4:(a,b) for i,(a,b) in enumerate(zip(words,result)) if a!=b}!=PATCHES:
        raise ValueError('Child motion is not the closed FP cycle/setup schedule')
    return result


def padded_object(root,out,obj,label,guards):
    text=emit_padded_assembly(obj,out/'before-tile_original',word_patches_path=guards,filename=OWNER)
    path=out/(label+'-padded.s'); path.write_text(text); target=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(path)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out); before=(out/'before-tile_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag: raise ValueError('Child motion compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj): raise ValueError('Child motion pools changed')
    neighbors=same_functions(old,obj,(FUNCTION,))
    guards=out/'candidate-guards.csv'; guards.write_bytes(guard_bytes((out/'before-guards').read_bytes()))
    padded=padded_object(root,out,obj,'candidate',guards)
    old_padded=padded_object(root,out,old,'owner-before',out/'before-guards')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors: raise ValueError('Child motion padded neighbors changed')
    images=[]
    for p in (obj,padded):
        data,functions=build.link_owner(root,out,p,OWNER); f=functions[FUNCTION]
        images.append(list(struct.unpack_from('>48I',data,f['value'])))
    truth=list(struct.unpack_from('>48I',(out/'before-retail_rom').read_bytes(),ROM))
    if normalize(images[0])!=truth or images[1]!=truth: raise ValueError('Incomplete child motion match')
    row=dict(words=48,frame=0,raw_differences=10,bindings=6,new_guards=10,
        closed_FP_cycle={0:2,2:12,12:0},independent_setup_words=[8,9],retail_add_operand_order_word=29,
        unchanged_raw_padded_neighbors=neighbors)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
