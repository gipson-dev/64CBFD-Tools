"""Restore the actor-state update and its ordered event-value dependency."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_halfword_point_update as previous
from tools.tests import halfword_point_checkpoint as checkpoint
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-actor-state-update'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11F780','func_150F26A0',0x150F26A0,0x11FB50,756
LEAF='func_150F2994'
TARGETS={FUNCTION:(ENTRY,ROM,SIZE),LEAF:(0x150F2994,0x11FE44,192)}
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
changed={previous.PATHS[k]:v for k,v in checkpoint.AFTER.items()}
for key,path in PATHS.items():
    if path in changed:BASELINE[key]=changed[path]
for key,path,sha in (
    ('halfword_checkpoint','tools/tests/halfword_point_checkpoint.py','1d28f03e50d1490ba98160a3aae3e1f72e5148e517722f0ff474a58844fd07f0'),
    ('halfword_tests','tools/tests/test_game_halfword_point_update.py','b0bb7526bc224cb28821f5cda2adf268eed7782dc1ea908b919d623b06f397f9'),
    ('actor_state_table','conker/asm/data/22E0F0.rodata.s','63860fe2a49e0df34f373a9655abb5a2e82ba5d78601498ac256c5a79ad34789')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='''void func_150F2994(u8 *actor, s32 value);
s32 func_15123934(u8 *, s32, s32, s32, s32);
void func_15124B18(u8 *);
void func_15128774(u8 *, u8 *);
void func_151239CC(u8 *, s32);
s32 func_1509BE40(s32, s32, s32, s32);
void func_1509BFB0(s32, s32, s32);
extern u8 *D_800D2E4C;
'''
SELECTED='''/* Update actor movement state and refresh its event-controlled flags. */
void func_150F26A0(u8 *actor) {
    u8 *state = *(u8 **)(actor + 0x3D0);

    if (state[0x102] && !state[0x104]) {
        func_150F2994(actor, 1);
        if (*(s32 *)(actor + 0x2C) != 0x100 && !*(s32 *)(actor + 0x6C8)) {
            if (func_15123934(actor, 0x80, 0, 0, 3)) {
                *(u32 *)(actor + 0x84) |= 0x300400;
                *(u32 *)(actor + 0x84) &= ~6;
                *(s16 *)(actor + 0x1B4) = 1;
                *(s16 *)(actor + 0x1E0) = 3;
                func_15124B18(actor);
            }
            *(f32 *)(actor + 0x348) = 29.0f;
            *(f32 *)(actor + 0x34C) = 29.0f;
            *(f32 *)(actor + 0x374) = 200.0f;
            *(f32 *)(actor + 0x190) = -19.0f;
            if (!actor[0x3E8] && 0.5f * *(f32 *)(actor + 0x374) <
                    *(f32 *)(actor + 0x370) - *(f32 *)(actor + 0x374)) {
                func_15128774(actor, *(u8 **)(actor + 0x3D0));
            }
        }
    } else {
        state[7] = 0xFF;
        if (actor[0x23E] == 0x3B) {
            func_150F2994(actor, 1);
            if (*(s32 *)(actor + 0x2C) != 0x100 && !*(s32 *)(actor + 0x6C8)) {
                if (func_15123934(actor, 8, 0, 0, 3)) {
                    *(u32 *)(actor + 0x84) |= 0x300000;
                    *(u32 *)(actor + 0x84) &= ~4;
                    *(s16 *)(actor + 0x1B4) = 1;
                    *(s16 *)(actor + 0x1E0) = 3;
                }
                *(s32 *)(actor + 0x134) = 0;
                *(f32 *)(actor + 0x348) = 125.0f;
                *(f32 *)(actor + 0x34C) = 125.0f;
                *(f32 *)(actor + 0x374) = 220.0f;
                *(f32 *)(actor + 0x190) = 30.0f;
            }
        } else {
            if ((*(s32 *)(actor + 0x2C) == 8 || *(s32 *)(actor + 0x2C) == 0x80) &&
                    !*(s32 *)(actor + 0x6C8)) {
                func_151239CC(actor, 3);
            }
            if (*(s16 *)(actor + 0x1B4) == 1) {
                *(s16 *)(actor + 0x1B4) = 2;
                func_15124B18(actor);
            }
            func_150F2994(actor, 0);
        }
    }
    if (func_1509BE40(1, 0x405A, 6, 0x9000)) {
        *(u32 *)(actor + 0x84) |= 0x80000000;
    } else {
        *(u32 *)(actor + 0x84) &= 0x7FFFFFFF;
    }
    if (func_1509BE40(1, 0x405E, 6, 0x9000)) {
        *(u32 *)(actor + 0x84) |= 0x10000;
    } else {
        *(u32 *)(actor + 0x84) &= 0xFFFEFFFF;
    }
    if (func_1509BE40(1, 0x405F, 6, 0x2000)) {
        *(u32 *)(actor + 0x84) |= 0x10;
    } else {
        *(u32 *)(actor + 0x84) &= ~0x10;
    }
}'''
EVENTS='''/* Apply the shared event value, including optional player-state events. */
void func_150F2994(u8 *actor, s32 value) {
    s32 i;

    for (i = 0; i < 14; i++) {
        func_1509BFB0(0, i + 0x4016, value);
    }
    func_1509BFB0(0, 0x405D, value);
    func_1509BFB0(0, 0x405F, value);
    if (D_800D2E4C[0x15] & 8) {
        func_1509BFB0(0, 0x4063, value);
        func_1509BFB0(0, 0x4064, value);
        func_1509BFB0(0, 0x4065, value);
    }
}'''
BODIES={FUNCTION:SELECTED,LEAF:EVENTS}
RAW_SHA={FUNCTION:'ba8deca25a2dc583b54bd7b9689adab8af9df126a2ec41138eb0a4aedfa26446',LEAF:'59369cf7cb5169a6f91f2953c2251e43bee5eabc91ad50abcd9118cc7c427662'}
BINDINGS={name:{int(at):[tuple(row) for row in rows] for at,rows in values.items()}
    for name,values in json.loads('{"func_150F26A0":{"52":[["R_MIPS_26","func_150F2994"]],"104":[["R_MIPS_26","func_15123934"]],"164":[["R_MIPS_26","func_15124B18"]],"264":[["R_MIPS_26","func_15128774"]],"304":[["R_MIPS_26","func_150F2994"]],"356":[["R_MIPS_26","func_15123934"]],"500":[["R_MIPS_26","func_151239CC"]],"528":[["R_MIPS_26","func_15124B18"]],"540":[["R_MIPS_26","func_150F2994"]],"560":[["R_MIPS_26","func_1509BE40"]],"624":[["R_MIPS_26","func_1509BE40"]],"688":[["R_MIPS_26","func_1509BE40"]]},"func_150F2994":{"44":[["R_MIPS_26","func_1509BFB0"]],"72":[["R_MIPS_26","func_1509BFB0"]],"88":[["R_MIPS_26","func_1509BFB0"]],"96":[["R_MIPS_HI16","D_800D2E4C"]],"100":[["R_MIPS_LO16","D_800D2E4C"]],"128":[["R_MIPS_26","func_1509BFB0"]],"144":[["R_MIPS_26","func_1509BFB0"]],"160":[["R_MIPS_26","func_1509BFB0"]]}}').items()}
SYMBOLS={"func_150F2994":353315220,"func_15123934":353515828,"func_15124B18":353520408,"func_15128774":353535860,"func_151239CC":353515980,"func_1509BE40":352960064,"func_1509BFB0":352960432,"D_800D2E4C":2148347468}

def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import actor_state_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed actor-state live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed actor-state frozen input: '+key)

def recovered_owner(before,bodies=None):
    for name,body in (bodies or BODIES).items():
        lo,hi=build.function_span(before,name)
        if before[lo:hi]!='s32 '+name+'() {\n    return 0;\n}':raise ValueError('Unknown actor-state predecessor: '+name)
        before=before[:lo]+body+before[hi:]
    anchor='extern u8 D_800BE9C0;'
    if before.count(anchor)!=1:raise ValueError('Unknown actor-state declaration anchor')
    return before.replace(anchor,anchor+'\n'+TYPE,1)

def parts(obj,name=FUNCTION):
    data,fs,rs=parse_object(obj);f=fs[name]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}

def checked_parts(raw,bindings,name=FUNCTION):
    if len(raw)!=TARGETS[name][2] or hashlib.sha256(raw).hexdigest()!=RAW_SHA[name] or bindings!=BINDINGS[name]:
        raise ValueError('Changed complete actor-state words/bindings: '+name)

def padded_object(root,out,obj,label):return previous.padded_object(root,out,obj,label)

def raw_object(root,out,obj,label,name=FUNCTION):
    data,fs,rs=parse_object(obj);text,unknown=emit_function(data,fs[name],rs,name,SYMBOLS)
    if unknown:raise ValueError('Unknown actor-state raw binding '+repr(unknown))
    asm=out/(label+'-'+name+'-raw.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target

def qualify(root,out):
    freeze(root,out);before=(out/'before-fixed_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Actor-state compiler diagnostics')
    for name in TARGETS:checked_parts(*parts(obj,name),name)
    if normalized_pools(old)!=normalized_pools(obj):raise ValueError('Changed actor-state owner pools')
    neighbors=same_functions(old,obj,tuple(TARGETS));padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before'),padded,tuple(TARGETS))!=neighbors:
        raise ValueError('Actor-state padded neighbors changed')
    rom=(out/'before-retail_rom').read_bytes()
    if struct.unpack_from('>I',rom,0x22E198)[0]!=ENTRY:raise ValueError('Changed actor-state registered callback')
    images={}
    for name,(entry,offset,size) in TARGETS.items():
        images[name]=[]
        for path in (raw_object(root,out,obj,'candidate',name),padded):
            data,fs=build.link_owner(root,out,path,OWNER)
            images[name].append(list(struct.unpack_from('>%dI'%(size//4),data,fs[name]['value'])))
        truth=list(struct.unpack_from('>%dI'%(size//4),rom,offset))
        if images[name]!=[truth,truth]:raise ValueError('Incomplete direct actor-state match: '+name)
    row=dict(target_words={n:v[2]//4 for n,v in TARGETS.items()},frames=[40,40],new_guards=0,
        raw_differences=0,unchanged_raw_padded_neighbors=neighbors,owner_pools_unchanged=True,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row

if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)

