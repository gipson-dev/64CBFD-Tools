"""Recover the owner-gated record burst and its two stack packet layouts."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_actor_scale_timer as previous
from tools.tests import actor_scale_timer_checkpoint as checkpoint
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-owner-burst-emitter'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11FF10','func_150F2D14',0x150F2D14,0x1201C4,1152
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
changed={previous.PATHS[k]:v for k,v in {**checkpoint.AFTER,**checkpoint.FOLLOWUP}.items()}
for key,path in PATHS.items():
    if path in changed:BASELINE[key]=changed[path]
for key,path,sha in (
    ('scale_timer_recovery','tools/experiments/game_actor_scale_timer.py','cfbb23bfd4ae1a32889accd74b182ea5bae445e419ff943c112f699b4d947dc6'),
    ('scale_timer_installation','tools/experiments/game_actor_scale_timer_installation.py','4b9469bdbce4b5525a0835b5595b134025b0602ab40da2a9a9b49fe4dffdc823'),
    ('scale_timer_checkpoint','tools/tests/actor_scale_timer_checkpoint.py','b16503a996464531b8536d351c6ced8f811592c3a41f8f054d6be0f3f3568408'),
    ('scale_timer_tests','tools/tests/test_game_actor_scale_timer.py','2db2161a25ffd79aeb7d4d31b902f12984ded8e170475c41f3bd9cc52fdba0d6'),
    ('owner_burst_table','conker/asm/data/22EF80.rodata.s','0711a45ed594246cf7054df44d7e73dd1506372423061bf7e6d8f6b147eb7b79')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='''typedef struct { f32 x, y, z; } BurstVector2D14;
typedef struct {
    u8 *owner;
    u8 ownerId, reserved05[3];
    f32 time, limit, multiplier, byteBase, decay;
    BurstVector2D14 vector1C, vector28;
} BurstPayload2D14;
typedef struct {
    u8 byte00, byte01;
    s16 half02, half04;
    u8 reserved06[2];
    u32 word08, word0C;
    u8 bytes10[4];
    f32 float14, float18;
    BurstVector2D14 position, vector28, scale;
    u32 word40;
    u8 byte44, byte45, byte46, byte47;
    u32 word48;
    u8 byte4C, reserved4D[3];
    u32 word50;
    s16 half54, half56;
} BurstDescriptor2D14;
extern u8 D_800C35EA, D_800CC2D0[], D_800A4AA0[];
extern f32 D_800A195C[], D_800A1968, D_800A196C;
extern BurstVector2D14 D_800A5480;
void func_1502EA98(u8 *, u8, u8, u8, u8, s32, u8);
f32 func_150ADA68(void);
void func_15145EA4(BurstVector2D14 **, BurstVector2D14 **, u8 *, s32);
s32 func_15146078(BurstVector2D14 *, BurstVector2D14 *, BurstVector2D14 *);
u8 *func_1513D2F0(BurstDescriptor2D14 *, void *, u8, u8, u8, u8, u8,
                   s32, s32, s32, u8, s32);
'''
SELECTED='''/* Emit timed records while the linked owner and byte epoch remain valid. */
void func_150F2D14(u8 *actor) {
    Generated11FF10Payload *savedData;
    BurstDescriptor2D14 request;
    BurstPayload2D14 payload;
    BurstVector2D14 *inputs[2];
    BurstVector2D14 *outputs[2];
    BurstVector2D14 delta;
    f32 multiplier;
    u8 *created;
    u8 *owner;
    Generated11FF10Payload *data;

    data = (Generated11FF10Payload *)(actor + 0x28);
    savedData = data;
    if (D_800C35EA != 1) {
        owner = data->owner;
        if (*(s32 *)owner == 0 || data->owner_id != owner[0x3B]) {
            *(s16 *)(actor + 0xE) = -1;
            return;
        }
        if (owner[0x222] != data->state && owner[0x222] != 0) {
            data->mode = 3;
            data->value = 0.0f;
        }
        data->state = owner[0x222];
        if (owner[0x222] != 0) {
            func_1502EA98(D_800CC2D0 + owner[0x222] * 0x32C,
                           255, 0, 0, 0x50, 0, 15);
        }
        if (*(u8 **)(owner + 0x1D4) != NULL && (s8)data->mode > 0) {
            data->value += D_800A1968 * D_800BE9A4;
            if (data->value > 1.0f) {
                multiplier = D_800A196C;
                do {
                    payload.owner = owner;
                    payload.ownerId = owner[0x3B];
                    payload.time = 0.0f;
                    payload.limit = func_150ADA68() * 6.0f + 13.0f;
                    payload.multiplier = multiplier;
                    payload.byteBase = func_150ADA68() * 40.0f + 60.0f;
                    payload.decay = payload.byteBase / (payload.limit * payload.limit);
                    inputs[0] = (BurstVector2D14 *)D_800A1950;
                    inputs[1] = (BurstVector2D14 *)D_800A195C;
                    outputs[0] = &request.position;
                    outputs[1] = &delta;
                    func_15145EA4(inputs, outputs, *(u8 **)(owner + 0x1D4) + 0x3C0, 2);
                    delta.x -= request.position.x;
                    delta.y -= request.position.y;
                    delta.z -= request.position.z;
                    if (func_15146078(&delta, &payload.vector1C, &payload.vector28) == 0) {
                        return;
                    }
                    request.byte44 = (u32)payload.byteBase;
                    request.byte00 = 0x79;
                    request.byte01 = 0xC;
                    request.half02 = 0x4405;
                    request.half04 = 0x12C;
                    request.word08 = 0;
                    request.word0C = 0;
                    request.bytes10[0] = 0xD5;
                    request.bytes10[1] = 0xDB;
                    request.bytes10[2] = 0xFF;
                    request.bytes10[3] = 0xFF;
                    request.float18 = 0.0f;
                    request.float14 = 0.0f;
                    request.vector28 = D_800A5480;
                    request.scale.x = 1.0f;
                    request.scale.y = 1.0f;
                    request.scale.z = 1.0f;
                    request.word40 = 0x04EC0000;
                    request.byte45 = 0xFF;
                    request.byte46 = 0;
                    request.byte47 = 6;
                    request.word48 = 0;
                    request.byte4C = 0xFF;
                    request.word50 = 0;
                    request.half54 = 1;
                    request.half56 = 0xFF;
                    created = func_1513D2F0(&request, D_800A4AA0, 0x26, 0, 0, 0x25,
                                            0, 0, 0, sizeof(payload), actor[0xC], actor[1]);
                    if (created != NULL) {
                        memcpy(created + 0x110, &payload, sizeof(payload));
                    }
                    data->mode--;
                    data->value -= 1.0f;
                } while (data->value > 1.0f && (s8)savedData->mode > 0);
            }
        }
    }
}'''
BASE_BODY=SELECTED
SELECTED=BASE_BODY.replace('                    data->mode--;','                    data->mode = (s8)data->mode - 1;')
RAW_SHA='de1b59b226ecb144ea4a7ff1d460c2f757bb7180907431cbe75357fb2a8b2f18'
SYMBOLS={'D_800C35EA':0x800C35EA,'D_800CC2D0':0x800CC2D0,'func_1502EA98':0x1502EA98,
    'D_800A1968':0x800A1968,'D_800BE9A4':0x800BE9A4,'D_800A195C':0x800A195C,
    'D_800A1950':0x800A1950,'D_800A196C':0x800A196C,'func_150ADA68':0x150ADA68,
    'func_15145EA4':0x15145EA4,'func_15146078':0x15146078,'D_800A5480':0x800A5480,
    'D_800A4AA0':0x800A4AA0,'func_1513D2F0':0x1513D2F0,'memcpy':0x10022EC0}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        from tools.tests import owner_burst_checkpoint as latest
        data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed owner-burst live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed owner-burst frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150F2D14() {\n    return 0;\n}':raise ValueError('Unknown owner-burst predecessor')
    anchor='#include <ultra64.h>'
    if before.count(anchor)!=1:raise ValueError('Unknown owner-burst declarations')
    return (before[:lo]+body+before[hi:]).replace(anchor,anchor+'\n'+TYPE,1)


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def padded_object(root,out,obj,label):
    text=emit_padded_assembly(obj,out/'before-record_gate_original',filename=OWNER,word_patches_path=out/'before-guards')
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    obj,words,row=measure(root,out)
    if (len(words),row['frame'],row['differences'],row['raw_sha'])!=(288,344,85,RAW_SHA):
        raise ValueError('Changed uninstalled owner-burst candidate')
    before=(out/'before-record_gate_owner').read_text();old,diag=compile_owner(root,out,before,'owner-before')
    if diag:raise ValueError('Owner-burst baseline diagnostics')
    if normalized_pools(old)!=normalized_pools(obj):raise ValueError('Changed owner-burst owner pools')
    neighbors=same_functions(old,obj,(FUNCTION,));padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Changed owner-burst padded neighbors')
    data,fs=build.link_owner(root,out,padded,OWNER)
    padded_words=list(struct.unpack_from('>288I',data,fs[FUNCTION]['value']))
    if padded_words!=words:raise ValueError('Unexpected owner-burst padding rewrite')
    row.update(unchanged_raw_padded_neighbors=neighbors,owner_pools_unchanged=True,new_guards=0,
        padded_differences=85,matching_credit=0)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,[words,padded_words],row


def linked(root,out,obj,label,entry=ENTRY,symbols=None):
    data,fs,rs=parse_object(obj);s=symbols or SYMBOLS
    text,unknown=emit_function(data,fs[FUNCTION],rs,FUNCTION,s)
    if unknown:raise ValueError('Unknown owner-burst bindings '+repr(unknown))
    stem=out/label;asm=stem.with_suffix('.s');asm.write_text(text);compiled=stem.with_suffix('.o')
    script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',FUNCTION,
        *['--defsym=%s=0x%X'%p for p in s.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
    count=fs[FUNCTION]['size']//4
    return list(struct.unpack_from('>%dI'%count,projection.sections(elf)['.text'][1]))


def measure(root,out,label='candidate',body=SELECTED):
    freeze(root,out);before=(out/'before-record_gate_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before,body),label)
    if diag:raise ValueError('Owner-burst compiler diagnostics: '+repr(diag))
    raw,bindings=parts(obj);words=linked(root,out,obj,label+'-linked')
    truth=list(struct.unpack_from('>288I',(out/'before-retail_rom').read_bytes(),ROM))
    frames=[(-(w&65535))&65535 for w in words[:24] if w>>16==0x27BD and w&0x8000]
    row=dict(words=len(words),frame=frames[0] if frames else 0,raw_sha=hashlib.sha256(raw).hexdigest(),
        differences=sum(a!=b for a,b in zip(words,truth)),extent_gap=len(words)-288,bindings=bindings,installed=False)
    (out/(label+'-audit.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def forms():
    corrected=BASE_BODY.replace('owner[0x222] != data->state','data->state != owner[0x222]').replace(
        '                    data->mode--;','                    data->mode = (s8)data->mode - 1;')
    yield 'signed-state',corrected
    local=corrected.replace('    f32 multiplier;\n','').replace(
        '                multiplier = D_800A196C;','                f32 multiplier = D_800A196C;')
    yield 'block-multiplier',local
    yield 'block-created',local.replace('    u8 *created;\n','').replace(
        '                do {','                do {\n                    u8 *created;')
    yield 'initial-state-signed',BASE_BODY.replace('                    data->mode--;',
        '                    data->mode = (s8)data->mode - 1;')


def workspace_forms():
    definition='''typedef struct {
    BurstVector2D14 delta;
    BurstVector2D14 *outputs[2], *inputs[2];
    u8 reserved1C[4];
    BurstPayload2D14 payload;
    BurstDescriptor2D14 request;
} BurstWorkspace2D14;
'''
    body=dict(forms())['signed-state']
    declarations='''    BurstDescriptor2D14 request;
    BurstPayload2D14 payload;
    BurstVector2D14 *inputs[2];
    BurstVector2D14 *outputs[2];
    BurstVector2D14 delta;'''
    if body.count(declarations)!=1:raise ValueError('Unknown owner-burst workspace screen')
    body=body.replace(declarations,'    BurstWorkspace2D14 work;')
    import re
    body=re.sub(r'\b(request|payload|inputs|outputs|delta)\b',r'work.\1',body)
    yield 'workspace',definition+body
    yield 'workspace-block',definition+body.replace('    f32 multiplier;\n','').replace(
        '                multiplier = D_800A196C;','                f32 multiplier = D_800A196C;')
    yield 'workspace-tight',definition.replace('    u8 reserved1C[4];\n','')+body


def lifetime_forms():
    body=dict(forms())['signed-state']
    for label,targets in (('all',('f32 multiplier','u8 *created','u8 *owner','Generated11FF10Payload *data')),
            ('pointers',('u8 *created','u8 *owner','Generated11FF10Payload *data')),('multiplier',('f32 multiplier',))):
        b=body
        for target in targets:b=b.replace('    '+target+';','    register '+target+';')
        yield 'register-'+label,b
    yield 'state-local',body.replace('    u8 *created;','    u8 *created;\n    u8 state;').replace(
        '        if (data->state != owner[0x222] && owner[0x222] != 0) {',
        '        state = owner[0x222];\n        if (state != data->state && state != 0) {')


def alignment_forms():
    aligned=TYPE.replace('} BurstDescriptor2D14;',
        '} BurstDescriptorFields2D14;\ntypedef union { BurstDescriptorFields2D14 fields; u64 alignment; } BurstDescriptor2D14;')
    body=dict(forms())['signed-state'].replace('request.','request.fields.')
    yield 'descriptor-align8',body,aligned
    state=dict(lifetime_forms())['state-local'].replace('request.','request.fields.')
    yield 'descriptor-align8-state',state,aligned


if __name__=='__main__':
    import sys
    root=Path(__file__).resolve().parents[2]
    if len(sys.argv)==1:
        print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
        raise SystemExit(0)
    if '--align' in sys.argv:
        for label,body,kind in alignment_forms():
            TYPE=kind;row=measure(root,root/BUILD,label,body)[-1]
            print(label,json.dumps({k:v for k,v in row.items() if k!='bindings'}),flush=True)
        raise SystemExit(0)
    candidates=lifetime_forms() if '--lifetimes' in sys.argv else workspace_forms() if '--workspace' in sys.argv else forms() if '--screen' in sys.argv else [('candidate',SELECTED)]
    for label,body in candidates:
        row=measure(root,root/BUILD,label,body)[-1]
        print(label,json.dumps({k:v for k,v in row.items() if k!='bindings'}),flush=True)
