"""Recover the owner-bound position, scale, byte value and timer updater."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import csv
import io

from tools.experiments import game_indexed_threshold_mask as previous
from tools.tests import indexed_threshold_mask_checkpoint as checkpoint
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-actor-scale-timer'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11FF10','func_150F3214',0x150F3214,0x1206C4,360
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
changed={previous.PATHS[k]:v for k,v in checkpoint.AFTER.items()}
for key,path in PATHS.items():
    if path in changed:BASELINE[key]=changed[path]
for key,path,sha in (
    ('threshold_mask_recovery','tools/experiments/game_indexed_threshold_mask.py','831497a13475fee112958209260b013fc145bd6c9205133b5601d0bb94c84b24'),
    ('threshold_mask_checkpoint','tools/tests/indexed_threshold_mask_checkpoint.py','314a0e98232b5c3d99565591deb06df20491f0671aefb632021397b389c2fa01'),
    ('threshold_mask_tests','tools/tests/test_game_indexed_threshold_mask.py','32468e255349178c2f2576164acb74ebb47aba5a7ef44e60ec07f043b3abce21'),
    ('scale_timer_table','conker/asm/data/22E730.rodata.s','04adc08432aaa1052219d977d68d9769ac85e1efca4aa89b8b35b8cddedf8413')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='''extern f32 D_800A1950[];
extern f32 D_800BE9A4;
f32 sqrtf(f32);
void func_15143134(f32 *, f32 *, u8 *);
'''
SELECTED='''/* Refresh a linked actor's position, scale, byte value, and timer. */
s32 func_150F3214(u8 *actor) {
    u8 *data;
    u8 *owner;
    u8 *model;
    f32 scale;
    f32 time;
    s32 result;

    owner = *(u8 **)(actor + 0x110);
    data = actor + 0x110;
    if (*(s32 *)owner == 0 || data[4] != owner[0x3B] ||
        (model = *(u8 **)(owner + 0x1D4)) == NULL) {
        return 0;
    }
    func_15143134(D_800A1950, (f32 *)(actor + 0x34), model + 0x3C0);
    scale = sqrtf(*(f32 *)(data + 8)) * *(f32 *)(data + 0x10);
    *(f32 *)(actor + 0x30) = scale;
    *(f32 *)(actor + 0x2C) = scale;
    time = *(f32 *)(data + 8);
    actor[0x5C] = (u32)(*(f32 *)(data + 0x14) -
                        *(f32 *)(data + 0x18) * time * time);
    *(f32 *)(data + 8) += D_800BE9A4;
    result = 1;
    if (*(f32 *)(data + 0xC) < *(f32 *)(data + 8)) {
        result = 0;
    }
    return result;
}'''
INITIAL=SELECTED
SYMBOLS={'D_800A1950':0x800A1950,'func_15143134':0x15143134,'D_800BE9A4':0x800BE9A4}
GUARDS=((0x78,0x46002082,0x46040082),(0x98,0x460A6402,0x460C5402))
BINDINGS={52:[('R_MIPS_HI16','D_800A1950')],56:[('R_MIPS_LO16','D_800A1950')],
    84:[('R_MIPS_26','func_15143134')],284:[('R_MIPS_HI16','D_800BE9A4')],292:[('R_MIPS_LO16','D_800BE9A4')]}
RAW_SHA='3efe468b63f0a9436c368dacf6e7bf31fa889355cf20c0f965d8efcfa68a42e9'


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import actor_scale_timer_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed scale-timer live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed scale-timer frozen input: '+key)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150F3214() {\n    return 0;\n}':raise ValueError('Unknown scale-timer predecessor')
    anchor='#include <ultra64.h>'
    if before.count(anchor)!=1:raise ValueError('Unknown scale-timer declarations')
    return (before[:lo]+body+before[hi:]).replace(anchor,anchor+'\n'+TYPE,1)


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete scale-timer words/bindings')


def guard_text(before):
    rows=list(csv.DictReader(io.StringIO(before)))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in rows):raise ValueError('Existing scale-timer guards')
    suffix=''.join('%s,%s,0x%X,0x%08X,0x%08X,-,-,Preserve retail commutative scale-timer MUL.S operand order,,,false\n'%
        (OWNER,FUNCTION,*g) for g in GUARDS)
    return before+suffix


def padded_object(root,out,obj,label,guards):
    text=emit_padded_assembly(obj,out/'before-record_gate_original',filename=OWNER,word_patches_path=guards)
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    obj,words,row=measure(root,out)
    checked_parts(*parts(obj))
    truth=list(struct.unpack_from('>90I',(out/'before-retail_rom').read_bytes(),ROM))
    if [(i*4,b,a) for i,(a,b) in enumerate(zip(truth,words)) if a!=b]!=list(GUARDS):
        raise ValueError('Unaccounted scale-timer raw differences')
    before=(out/'before-record_gate_owner').read_text();old,diag=compile_owner(root,out,before,'owner-before')
    if diag:raise ValueError('Scale-timer baseline diagnostics')
    if normalized_pools(old)!=normalized_pools(obj):raise ValueError('Changed scale-timer owner pools')
    neighbors=same_functions(old,obj,(FUNCTION,))
    guards=out/'expected-guards.csv';guards.write_bytes(guard_text((out/'before-guards').read_bytes().decode()).encode())
    padded=padded_object(root,out,obj,'candidate',guards)
    if same_functions(padded_object(root,out,old,'owner-before',out/'before-guards'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Changed scale-timer padded neighbors')
    data,fs=build.link_owner(root,out,padded,OWNER)
    matched=list(struct.unpack_from('>90I',data,fs[FUNCTION]['value']))
    if matched!=truth:raise ValueError('Incomplete guarded scale-timer match')
    row.update(new_guards=2,padded_differences=0,unchanged_raw_padded_neighbors=neighbors,owner_pools_unchanged=True)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,[words,matched],row


def linked(root,out,obj,label,entry=ENTRY,symbols=None):
    data,fs,rs=parse_object(obj);s=symbols or SYMBOLS
    text,unknown=emit_function(data,fs[FUNCTION],rs,FUNCTION,s)
    if unknown:raise ValueError('Unknown scale-timer bindings '+repr(unknown))
    stem=out/label;asm=stem.with_suffix('.s');asm.write_text(text);compiled=stem.with_suffix('.o')
    script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',FUNCTION,
        *['--defsym=%s=0x%X'%p for p in s.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
    count=fs[FUNCTION]['size']//4
    return list(struct.unpack_from('>%dI'%count,projection.sections(elf)['.text'][1]))


def measure(root,out,label='candidate',body=None):
    if body is None:body=SELECTED
    freeze(root,out);before=(out/'before-record_gate_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before,body),label)
    if diag:raise ValueError('Scale-timer compiler diagnostics: '+repr(diag))
    raw,bindings=parts(obj);words=linked(root,out,obj,label+'-linked')
    truth=list(struct.unpack_from('>90I',(out/'before-retail_rom').read_bytes(),ROM))
    frames=[(-(w&65535))&65535 for w in words[:24] if w>>16==0x27BD and w&0x8000]
    row=dict(words=len(words),frame=frames[0] if frames else 0,raw_sha=hashlib.sha256(raw).hexdigest(),
        differences=sum(a!=b for a,b in zip(words,truth)),extent_gap=len(words)-90,bindings=bindings,installed=False)
    (out/(label+'-audit.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def forms():
    yield 'initial',INITIAL
    tail='''    result = 1;
    if (*(f32 *)(data + 0xC) < *(f32 *)(data + 8)) {
        result = 0;
    }
    return result;'''
    direct=INITIAL.replace('    s32 result;\n','').replace(tail,'''    if (*(f32 *)(data + 0xC) < *(f32 *)(data + 8)) {
        return 0;
    }
    return 1;''')
    for label,body in (('direct',direct),('initial',INITIAL)):
        inline=body.replace('    f32 time;\n','').replace('    time = *(f32 *)(data + 8);\n','').replace(
            '*(f32 *)(data + 0x18) * time * time','*(f32 *)(data + 0x18) * *(f32 *)(data + 8) * *(f32 *)(data + 8)')
        yield label+'-inline',inline
        yield label+'-inline-reverse',inline.replace('sqrtf(*(f32 *)(data + 8)) * *(f32 *)(data + 0x10)',
            '*(f32 *)(data + 0x10) * sqrtf(*(f32 *)(data + 8))')
    yield 'direct',direct


def more_forms():
    body=dict(forms())['direct-inline']
    chained=body.replace('    f32 scale;\n','').replace('''    scale = sqrtf(*(f32 *)(data + 8)) * *(f32 *)(data + 0x10);
    *(f32 *)(actor + 0x30) = scale;
    *(f32 *)(actor + 0x2C) = scale;''','''    *(f32 *)(actor + 0x2C) = *(f32 *)(actor + 0x30) =
        sqrtf(*(f32 *)(data + 8)) * *(f32 *)(data + 0x10);''')
    yield 'chained',chained
    yield 'chained-reverse',chained.replace('sqrtf(*(f32 *)(data + 8)) * *(f32 *)(data + 0x10)',
        '*(f32 *)(data + 0x10) * sqrtf(*(f32 *)(data + 8))')
    for label,b in (('direct-inline',body),('chained',chained)):
        yield label+'-integer-model',b.replace('    u8 *model;','    s32 model;').replace(
            '(model = *(u8 **)(owner + 0x1D4)) == NULL','(model = *(s32 *)(owner + 0x1D4)) == 0').replace(
            'model + 0x3C0','(u8 *)(model + 0x3C0)')
        yield label+'-data-argument',b.replace('    u8 *data;\n','').replace('    data = actor + 0x110;\n','').replace(
            'data[4]','actor[0x114]').replace('(data + 8)','(actor + 0x118)').replace(
            '(data + 0xC)','(actor + 0x11C)').replace('(data + 0x10)','(actor + 0x120)').replace(
            '(data + 0x14)','(actor + 0x124)').replace('(data + 0x18)','(actor + 0x128)')


def lifetime_forms():
    direct=dict(forms())['direct-inline']
    yield 'live-four-args',direct.replace('model + 0x3C0);','model + 0x3C0, actor);')
    yield 'live-typed-parameter',direct.replace('s32 func_150F3214(u8 *actor)',
        's32 func_150F3214(void *argument)').replace('    u8 *data;',
        '    u8 *actor = argument;\n    u8 *data;')
    yield 'live-saved-data',direct.replace('    u8 *data;', '    u8 *saved;\n    u8 *data;').replace(
        '    func_15143134(', '    saved = data;\n    func_15143134(')
    yield 'live-declarations',direct.replace('    u8 *data;\n    u8 *owner;\n    u8 *model;\n    f32 scale;',
        '    f32 scale;\n    u8 *model;\n    u8 *data;\n    u8 *owner;')
    yield 'live-time-return',INITIAL.replace('    s32 result;\n','').replace('''    result = 1;
    if (*(f32 *)(data + 0xC) < *(f32 *)(data + 8)) {
        result = 0;
    }
    return result;''','''    if (*(f32 *)(data + 0xC) < *(f32 *)(data + 8)) return 0;
    return 1;''').replace('sqrtf(*(f32 *)(data + 8)) * *(f32 *)(data + 0x10)',
        '*(f32 *)(data + 0x10) * sqrtf(*(f32 *)(data + 8))')


def local_forms():
    body=dict(forms())['direct-inline']
    model=body.replace('    u8 *model;\n','').replace(
        '(model = *(u8 **)(owner + 0x1D4)) == NULL','*(u8 **)(owner + 0x1D4) == NULL').replace(
        'model + 0x3C0','*(u8 **)(owner + 0x1D4) + 0x3C0')
    owner=body.replace('    u8 *owner;\n','').replace('    owner = *(u8 **)(actor + 0x110);\n','').replace(
        'owner','(*(u8 **)(actor + 0x110))')
    yield 'local-inline-model',model
    yield 'local-inline-owner',owner
    yield 'local-inline-both',model.replace('    u8 *owner;\n','').replace(
        '    owner = *(u8 **)(actor + 0x110);\n','').replace('owner','(*(u8 **)(actor + 0x110))')
    for label,b in (('model',model),('owner',owner)):
        yield 'local-'+label+'-time',b.replace('    f32 scale;','    f32 scale;\n    f32 time;').replace(
            '    actor[0x5C]', '    time = *(f32 *)(data + 8);\n    actor[0x5C]').replace(
            '*(f32 *)(data + 0x18) * *(f32 *)(data + 8) * *(f32 *)(data + 8)',
            '*(f32 *)(data + 0x18) * time * time')


def typed_forms():
    typed='''typedef struct {
    u8 *owner;
    u8 ownerId, padding[3];
    f32 time, limit, multiplier, byteBase, decay;
} ActorScaleTimer;
'''
    body=dict(forms())['direct-inline'].replace('    u8 *data;', '    ActorScaleTimer *data;').replace(
        '    data = actor + 0x110;', '    data = (ActorScaleTimer *)(actor + 0x110);').replace(
        'data[4]', 'data->ownerId')
    for at,member in (('8','time'),('0xC','limit'),('0x10','multiplier'),('0x14','byteBase'),('0x18','decay')):
        body=body.replace('*(f32 *)(data + '+at+')','data->'+member)
    yield 'typed',typed+body
    yield 'typed-owner',typed+body.replace('    owner = *(u8 **)(actor + 0x110);\n','').replace(
        '    data = (ActorScaleTimer *)(actor + 0x110);','    data = (ActorScaleTimer *)(actor + 0x110);\n    owner = data->owner;')
    yield 'typed-local-time',typed+body.replace('    f32 scale;','    f32 scale;\n    f32 time;').replace(
        '    actor[0x5C]', '    time = data->time;\n    actor[0x5C]').replace('data->decay * data->time * data->time','data->decay * time * time')
    yield 'typed-chained',typed+body.replace('    f32 scale;\n','').replace('''    scale = sqrtf(data->time) * data->multiplier;
    *(f32 *)(actor + 0x30) = scale;
    *(f32 *)(actor + 0x2C) = scale;''','''    *(f32 *)(actor + 0x2C) = *(f32 *)(actor + 0x30) =
        sqrtf(data->time) * data->multiplier;''')


def final_forms():
    body=dict(local_forms())['local-inline-both']
    yield 'final-reverse-scale',body.replace('sqrtf(*(f32 *)(data + 8)) * *(f32 *)(data + 0x10)',
        '*(f32 *)(data + 0x10) * sqrtf(*(f32 *)(data + 8))')
    yield 'final-separate-scale',body.replace('    scale = sqrtf(*(f32 *)(data + 8)) * *(f32 *)(data + 0x10);',
        '    scale = sqrtf(*(f32 *)(data + 8));\n    scale *= *(f32 *)(data + 0x10);')
    typed=dict(typed_forms())['typed']
    typed=typed.replace('    u8 *owner;\n    u8 *model;\n','').replace(
        '    owner = *(u8 **)(actor + 0x110);\n','').replace(
        '(model = *(u8 **)(owner + 0x1D4)) == NULL','*(u8 **)(data->owner + 0x1D4) == NULL').replace(
        '*(s32 *)owner','*(s32 *)data->owner').replace('owner[0x3B]','data->owner[0x3B]').replace(
        'model + 0x3C0','*(u8 **)(data->owner + 0x1D4) + 0x3C0')
    yield 'final-typed',typed
    yield 'final-typed-reverse',typed.replace('sqrtf(data->time) * data->multiplier',
        'data->multiplier * sqrtf(data->time)')
    yield 'final-time',body.replace('    f32 scale;','    f32 scale;\n    f32 time;').replace(
        '    actor[0x5C]', '    time = *(f32 *)(data + 8);\n    actor[0x5C]').replace(
        '*(f32 *)(data + 0x18) * *(f32 *)(data + 8) * *(f32 *)(data + 8)',
        '*(f32 *)(data + 0x18) * time * time')


SELECTED='''/* Refresh a linked actor's position, scale, byte value, and timer. */
s32 func_150F3214(u8 *actor) {
    u8 *data;
    f32 scale;

    data = actor + 0x110;
    if (*(s32 *)(*(u8 **)(actor + 0x110)) == 0 ||
        data[4] != (*(u8 **)(actor + 0x110))[0x3B] ||
        *(u8 **)(*(u8 **)(actor + 0x110) + 0x1D4) == NULL) {
        return 0;
    }
    func_15143134(D_800A1950, (f32 *)(actor + 0x34),
                 *(u8 **)(*(u8 **)(actor + 0x110) + 0x1D4) + 0x3C0);
    scale = sqrtf(*(f32 *)(data + 8)) * *(f32 *)(data + 0x10);
    *(f32 *)(actor + 0x30) = scale;
    *(f32 *)(actor + 0x2C) = scale;
    actor[0x5C] = (u32)(*(f32 *)(data + 0x14) -
                        *(f32 *)(data + 0x18) * *(f32 *)(data + 8) * *(f32 *)(data + 8));
    *(f32 *)(data + 8) += D_800BE9A4;
    if (*(f32 *)(data + 0xC) < *(f32 *)(data + 8)) {
        return 0;
    }
    return 1;
}'''


if __name__=='__main__':
    import sys
    root=Path(__file__).resolve().parents[2]
    if len(sys.argv)==1:
        print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
        raise SystemExit(0)
    if '--lifetimes' in sys.argv:
        TYPE=TYPE.replace('void func_15143134(f32 *, f32 *, u8 *);','void func_15143134();')
        candidates=lifetime_forms()
    else:candidates=final_forms() if '--final' in sys.argv else typed_forms() if '--typed' in sys.argv else local_forms() if '--locals' in sys.argv else more_forms() if '--more' in sys.argv else forms() if '--screen' in sys.argv else [('candidate',SELECTED)]
    for label,body in candidates:
        row=measure(root,root/BUILD,label,body)[-1]
        print(label,json.dumps(row),flush=True)
