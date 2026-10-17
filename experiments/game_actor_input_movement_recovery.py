"""Recover the complete actor input/movement state machine; no partial matching credit."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_owner_burst_match as previous
from tools.experiments import game_owner_burst_literal_candidates as literal
from tools.tests import owner_burst_checkpoint as checkpoint
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-actor-input-movement'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11FF10','func_150F34F4',0x150F34F4,0x1209A4,3836
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
changed={previous.PATHS[k]:v for k,v in checkpoint.AFTER.items()}
for key,path in PATHS.items():
    if path in changed:BASELINE[key]=changed[path]
for key,path,sha in (
    ('movement_predecessor_0','tools/experiments/game_owner_burst_literal_candidates.py','f32caf3ebb77f22c1ee598f99df3f6007a78cab4a27b3813b131b033c9d0950b'),
    ('movement_predecessor_1','tools/experiments/game_owner_burst_allocation_stages.py','5e4c800b3f01576093560ee68add08692118758bfd8fd582bc4715d4adda1222'),
    ('movement_predecessor_2','tools/experiments/game_owner_burst_match.py','2f7049bf5d653470764e54ef4fef2cf4f76d7f6de364be561601afae39943635'),
    ('movement_predecessor_3','tools/experiments/game_owner_burst_installation.py','a11b87aa2c2df3d93de74e5aff397aac452131fbc0cbd3732fa9412b488bcc08'),
    ('movement_predecessor_4','tools/tests/test_game_owner_burst_literal_and_allocation.py','a1285e10338af387ff98a44e2c59a88155d6c8f618ea7935d08f3d140994cee6'),
    ('movement_predecessor_5','tools/tests/test_game_owner_burst_match.py','43eb8aa0f7d535c246f7bf543091068882ef2eae68fd16bd4adc7a3f4c38b2e0'),
    ('movement_predecessor_6','tools/tests/owner_burst_checkpoint.py','068bffd2f7d5393c86d1a65ca6e86f03e1c37891fee111827e0dca80691be778'),
    ('movement_predecessor_7','conker/src/game_83300.c','8ab68786c757c4ebcaa85e806adc337649aa67aefc4a7a2d64d7bd67bf1da846'),
    ('movement_predecessor_8','conker/src/game_981E0.c','e83baa9f46721ba0cdfae136976b6f4d36c1945b75a33998d212250dc7e2b9bb'),
    ('movement_predecessor_9','conker/asm/nonmatchings/game_83300/func_1505A3A8.s','7dfb31e2b68b8dd5e1b63b13aec548f0639c149ebd8167918080ba1b68f77c7d'),
    ('movement_predecessor_10','conker/asm/nonmatchings/game_83300/func_150599C8.s','149967155addaa4b1c8a36564869072344bbfa9895fa38f7938f76569e3a4caa'),
    ('movement_predecessor_11','conker/asm/nonmatchings/game_981E0/func_15073FA0.s','332afa2e9c531c6a80326c5cc9c11a60775e671f455a6670cc4b1dbda814d62a'),
    ('movement_predecessor_12','conker/asm/data/22AAC0.rodata.s','46df90d48dc538b1287c9359d21264cedd7e6cc0f19e277b1c6a8e750a55a1ce'),
):
    if key in PATHS:raise ValueError('Duplicate movement input key')
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.source.build,previous.source.compile_owner,previous.source.parse_object,previous.source.projection

TYPE='''typedef struct {
    s32 active;
    u8 kind, reserved05[0x13];
    f32 positionY;
    u8 reserved1C[4];
    f32 verticalVelocity, acceleration, depth;
    u8 reserved2C[0x10];
    f32 speed, facingAngle, targetSpeed;
    u8 reserved48[0x2E];
    u16 heading, desiredHeading;
    s16 yaw;
    u8 reserved7C[2], turnStep, reserved7F, flag80, reserved81[2], flag83;
    u8 reserved84[2], flag86, reserved87[0x24], flagAB, reservedAC, flagAD;
    u8 reservedAE[0xA];
    f32 valueB8;
    u8 reservedBC[4];
    f32 valueC0, valueC4;
    u8 reservedC8[0x30];
    u32 flags;
    u8 reservedFC[6], mode, cooldown, disabled, reserved105[0x13];
    f32 thresholdY;
    u8 reserved11C[0x20], held, heldBy, reserved13E[0x8C], eligible, reserved1CB;
    f32 previousY;
    u8 reserved1D0[0x48];
    u32 state;
    u8 reserved21C[6], nearest, reserved223[0xF], animation, reserved233[0x29];
    u32 controlFlags;
    u8 reserved260[0xCC];
} MovementActor34F4;
typedef struct { u16 buttons; s8 x, y; } MovementInput34F4;
extern u16 D_800BE710;
extern MovementInput34F4 **D_800BE728, *D_800CC284;
extern s32 D_800CC288, D_80082FA0, D_800CC280, D_800BE9F0;
extern u8 D_800C3E78, D_800DDE3C[], D_800E0B94, D_800CC26D, D_800CBDD3;
extern u8 D_800CC2D0[];
extern u8 D_800CC5FC[], D_800D121C[];
extern f32 D_800DDDC8[], D_800D1550;
extern u32 D_800D1580;
extern MovementActor34F4 *D_800D154C;
extern f32 D_800A1988, D_800A198C, D_800A1990, D_800A1994, D_800A1998;
extern f32 D_800A199C, D_800A19A0, D_800A19A4, D_800A19A8, D_800A19AC;
extern f32 D_800A19B0, D_800A19B4, D_800A19B8, D_800A19BC, D_800A19C0;
extern f32 D_800A19C4, D_800A19C8, D_800A19CC, D_800A19D0, D_800A19D4;
void func_150585F0(MovementActor34F4 *, f32);
void func_15059140(MovementActor34F4 *);
u16 func_1505A630(f32, f32, s32);
f32 func_1505A5CC(MovementInput34F4 *);
void func_15052590(MovementActor34F4 *);
void func_1506E8D8(void);
void func_1506E5FC(void);
void func_1505959C(MovementActor34F4 *, s32);
f32 func_1505A6F8(MovementActor34F4 *, MovementActor34F4 *);
u8 func_150599C8(MovementActor34F4 *, u8, u16);
f32 func_1505A3A8(f32, MovementActor34F4 *, f32, f32, u8);
s32 func_15073FA0(void);
void func_1505E650(MovementActor34F4 *, u16, f32, f32, f32, f32, s32);
f32 func_150F34A0(u8 *, f32);
f32 fabsf(f32);
#pragma intrinsic (fabsf)
'''
SELECTED='''/* Update controller-driven movement, linked records, and animation state. */
void func_150F34F4(MovementActor34F4 *actor) {
    u16 angle;
    f32 input;
    f32 speed;
    f32 contactHeight;
    f32 distance;
    f32 value;
    f32 amount;
    f32 rate;
    f32 magnitude;
    f32 acceleration;
    f32 velocity;
    s32 index;
    s32 count;
    s32 animation;
    MovementActor34F4 *record;
    MovementInput34F4 *controller;

    contactHeight = 0.0f;
    actor->flagAB = 1;
    actor->flag80 = 1;
    actor->nearest = 0;
    D_800CC288 = D_800BE710;
    controller = *D_800BE728;
    D_800CC284 = controller;
    if (D_80082FA0 >= D_800C3E78 && D_800DDE3C[D_800C3E78] != 0 &&
        D_800DDDC8[D_800C3E78] > 0.75f && D_800E0B94 != 2) {
        controller->x = 0;
        D_800CC284->y = 0;
        D_800CC284->buttons = 0;
        D_800CC288 = 0;
    }
    actor->flags |= 0x40;
    actor->previousY = actor->positionY;
    if (actor->cooldown != 0) {
        actor->cooldown--;
    }
    if (actor->disabled != 0) {
        func_150585F0(actor, 0.25f);
        func_15059140(actor);
        actor->facingAngle = (f32)(actor->yaw + 0x4000) * 0.005493164f;
        if (actor->held != 0) {
            record = (MovementActor34F4 *)(D_800CC2D0 + (actor->held - 100) * 0x32C);
            record->heldBy = 0;
            record->animation = 0x21;
            record->state = 0;
            record->disabled = 0;
            record->flags &= ~0x400;
            record->speed = actor->speed;
            actor->held = 0;
        }
    } else if (actor->mode == 0) {
        actor->flagAD = 0;
        angle = func_1505A630((f32)D_800CC284->x, (f32)D_800CC284->y, 0);
        value = func_1505A5CC(D_800CC284);
        if (D_800CC284->buttons & 0x10) {
            value = 0.0f;
        }
        actor->desiredHeading = actor->yaw;
        if (value > 1.0f) {
            actor->desiredHeading = angle + D_800CC280;
        }
        actor->animation = 7;
        actor->state = 0;
        actor->targetSpeed = value * D_800A1988;
        if ((D_800CC288 & 0xC000) || actor->depth > 100.0f) {
            actor->animation = 8;
            actor->mode = 1;
        }
        func_15052590(actor);
        if (D_800CC26D != 0) {
            if (actor->depth > 30.0f) {
                D_800D1580 = 0xFF010074;
                func_1506E8D8();
                func_1505959C((MovementActor34F4 *)(D_800CC2D0 +
                                  D_800CC26D * 0x32C - 100 * 0x32C),
                               D_800C3E78);
                actor->mode = 1;
                actor->held = D_800CC26D;
            }
            actor->verticalVelocity = 23.0f;
        }
        if (actor->positionY < actor->thresholdY) {
            actor->mode = 1;
            actor->flag86 = 1;
            actor->verticalVelocity = -6.0f;
        }
    } else {
        speed = actor->speed;
        if (speed > 60.0f) {
            speed = 60.0f;
        }
        input = (f32)D_800CC284->y * 1.25f;
        if (D_800CC284->buttons & 0x10) {
            input = 0.0f;
        }
        if (actor->held != 0) {
            if (!(D_800CC284->buttons & 0x10)) {
                actor->positionY -= 16.0f * D_800D1550;
            }
        } else {
            distance = 1000.0f;
            record = (MovementActor34F4 *)D_800CC2D0;
            index = 0;
            do {
                if (record->active != 0 && record->eligible != 0 &&
                    record->depth == 0.0f && record->animation != 0x21 &&
                    (record->kind == 0x9C || record->kind == 0x9D)) {
                    value = func_1505A6F8(D_800D154C, record);
                    if (value < distance) {
                        actor->nearest = index;
                        distance = value;
                    }
                }
                index++;
                record++;
            } while (index != 25);
        }
        if (input < -90.0f) {
            input = -90.0f;
        }
        if (input > 90.0f) {
            input = 90.0f;
        }
        if (D_800A198C < actor->positionY) {
            value = actor->verticalVelocity;
            if (value > -30.0f) {
                actor->verticalVelocity = value - 1.5f;
            }
            input = 40.0f;
        }
        value = actor->valueC4;
        actor->valueC4 = value + (((f32)D_800CC284->x - value) *
                                  (D_800A1990 * D_800D1550));
        actor->turnStep = 25;
        angle = actor->heading - (s32)(actor->valueC4 * D_800D1550 *
                  D_800A1994 * ((100.0f - speed) * D_800A1998) * 220.0f);
        actor->heading = angle;
        func_150599C8(actor, 8, angle);
        actor->valueC0 = 0.0f;
        speed = 0.0f;
        rate = D_800A199C;
        if (actor->positionY < actor->thresholdY) {
            if (actor->flag86 == 0) {
                actor->flag86 = 1;
                actor->speed = 0.0f;
                actor->verticalVelocity = -6.0f;
            }
        } else if (actor->flag86 != 0) {
            actor->flag86 = 0;
            actor->verticalVelocity = 9.0f;
        }
        angle = D_800CC284->buttons;
        if (!(angle & 0x10)) {
            if (angle & 0x8000) {
                actor->valueC0 = -22.0f;
                speed = 1.0f;
                rate = D_800A19A0;
                angle = D_800CC284->buttons;
            }
            if (angle & 0x4000) {
                value = actor->verticalVelocity;
                actor->valueC0 = 30.0f;
                if (value < 0.0f) {
                    actor->valueC0 -= value * D_800A19A4;
                }
                speed = 1.5f;
                rate = D_800A19A8;
            }
        }
        func_1505A3A8(actor->valueC0, actor, speed, rate, 1);
        actor->facingAngle = (f32)(actor->yaw + 0x4000) * 0.005493164f;
        actor->acceleration = input * D_800A19AC * (200.0f - actor->speed);
        if (actor->held == 0) {
            if (actor->verticalVelocity > 26.0f) {
                actor->verticalVelocity = 26.0f;
            }
            if (actor->verticalVelocity < -34.0f) {
                actor->verticalVelocity = -34.0f;
            }
        }
        magnitude = fabsf(input * 0.5f);
        if (actor->flag86 != 0) {
            magnitude *= D_800A19B0;
            actor->acceleration *= D_800A19B4;
        }
        acceleration = actor->acceleration;
        velocity = actor->verticalVelocity;
        if (acceleration == 0.0f) {
            if (fabsf(velocity) < 1.5f) {
                actor->verticalVelocity = 0.0f;
            } else if (velocity > 0.0f) {
                actor->acceleration = D_800A19B8;
            } else {
                actor->acceleration = D_800A19BC;
            }
        } else {
            if (magnitude * D_800A19C0 < velocity && acceleration < 0.0f) {
                goto stop_acceleration;
            }
            if (velocity < -magnitude * 1.5f && acceleration > 0.0f) {
stop_acceleration:
                actor->acceleration = 0.0f;
            }
        }
        actor->flagAD = 10;
        if (D_800CC284->buttons & 0x10) {
            value = actor->valueB8;
            actor->verticalVelocity = 0.0f;
            actor->acceleration = 0.0f;
            actor->valueB8 = value + (((f32)D_800CC284->y - value) * D_800A19C4);
        } else {
            value = (actor->verticalVelocity - 0.0f) * -2.0f;
            actor->valueB8 = value;
            if (value > 40.0f) {
                actor->valueB8 = 40.0f;
            } else if (actor->valueB8 < -55.0f) {
                actor->valueB8 = -55.0f;
            }
        }
        speed = actor->verticalVelocity;
        D_800CBDD3 = 1;
        func_15059140(actor);
        D_800CBDD3 = 0;
        if (actor->held != 0 && actor->depth < 50.0f) {
            contactHeight = 50.0f;
        }
        if (!(D_800CC284->buttons & 0x10)) {
            if (D_800CC26D != 0 && actor->held == 0) {
                record = (MovementActor34F4 *)(D_800CC2D0 +
                         D_800CC26D * 0x32C - 100 * 0x32C);
                if (record->depth == 0.0f) {
                    actor->verticalVelocity = 20.0f;
                    actor->positionY = record->positionY + 70.0f;
                    func_1505959C((MovementActor34F4 *)(D_800CC2D0 +
                                      D_800CC26D * 0x32C - 100 * 0x32C),
                                   D_800C3E78);
                    actor->held = D_800CC26D;
                    D_800D1580 = 0xFF010074;
                    func_1506E8D8();
                }
            }
            if (actor->held != 0) {
                if (actor->controlFlags & 2) {
                    actor->controlFlags &= ~2;
                    record = (MovementActor34F4 *)(D_800CC2D0 +
                              (actor->held - 100) * 0x32C);
                    record->heldBy = 0;
                    record->animation = 0x21;
                    record->state = 0;
                    record->disabled = 0;
                    record->flags &= ~0x400;
                    record->speed = actor->speed;
                    actor->held = 0;
                    actor->verticalVelocity = 0.0f;
                    D_800D1580 = 0x76;
                    func_1506E8D8();
                }
            } else if ((D_800CC288 & 0x2000) && actor->cooldown == 0) {
                count = 0;
                if (D_800BE9F0 == 0x3C) {
                    record = (MovementActor34F4 *)D_800CC5FC;
                    do {
                        if (record->active != 0 && record->kind == 0x25) {
                            count++;
                        }
                        record++;
                    } while ((u8 *)record != D_800D121C);
                    if (count < 5) {
                        D_800D1580 = 6;
                        actor->cooldown = 4;
                        func_15073FA0();
                    }
                }
            }
        }
        if (actor->depth <= contactHeight) {
            actor->speed *= D_800A19C8;
            if ((D_800CC284->buttons & 0x4000) || actor->flag86 != 0 ||
                actor->held != 0) {
                if (actor->held != 0) {
                    if (actor->verticalVelocity < -10.0f) {
                        D_800D1580 = 0xFF0100A7;
                        func_1506E5FC();
                        D_800D1580 = 0xFF060372;
                        func_1506E8D8();
                    }
                } else if (actor->positionY < 0.0f) {
                    D_800D1580 = 0xFF010072;
                    func_1506E8D8();
                }
                if (actor->held == 0) {
                    actor->verticalVelocity = 20.0f;
                } else if (actor->flag86 == 0) {
                    actor->verticalVelocity = 38.0f;
                }
                input = -80.0f;
            } else {
                actor->mode = 0;
                actor->verticalVelocity = speed * -1.0f;
                actor->valueB8 = 0.0f;
                actor->depth = D_800A19CC;
            }
        }
        if (!(D_800CC284->buttons & 0x10)) {
            actor->valueB8 += 20.0f;
        } else {
            actor->verticalVelocity = actor->valueB8 * D_800A19D0;
        }
        if (actor->flag86 != 0) {
            actor->flag83 = 0;
            if (fabsf(input) > 8.0f || actor->valueC0 > 7.0f) {
                amount = 1.0f;
            } else {
                amount = 0.5f;
            }
        } else {
            amount = func_150F34A0((u8 *)actor, input);
        }
        animation = 0xF;
        if (actor->valueB8 > 40.0f && input > 20.0f) {
            animation = 0x11;
        }
        value = actor->speed;
        if (value < 20.0f && actor->valueC0 <= 0.0f && input == 0.0f) {
            animation = 0x18;
        }
        if (value < 0.0f) {
            animation = 0x1F;
        }
        if (actor->held != 0) {
            animation = 0x17;
            amount += D_800A19D4;
        }
        func_1505E650(actor, animation & 0xFFFF, amount, 9.0f, 0.0f, 0.0f, 0);
    }
}'''


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed movement predecessor: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed movement frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150F34F4() {\n    return 0;\n}':raise ValueError('Unknown movement stub')
    anchor='#include <ultra64.h>'
    if before.count(anchor)!=1:raise ValueError('Changed movement include')
    return (before[:lo]+body+before[hi:]).replace(anchor,anchor+'\n'+TYPE,1)


def parts(obj):
    data,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    return data[f['value']:f['value']+f['size']],{
        o-f['value']:v for o,v in relocations.items() if f['value']<=o<f['value']+f['size']}


def linked(root,out,obj,label,entry=ENTRY,symbols=None):
    data,functions,relocations=parse_object(obj);anchors=symbols or nm_anchors(root/'conker/build/conker.us.elf')
    assembly,unknown=emit_function(data,functions[FUNCTION],relocations,FUNCTION,anchors)
    if unknown:raise ValueError('Unqualified movement binding: '+repr(unknown))
    stem=out/label;asm=stem.with_suffix('.s');compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
    asm.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    used={s for o,v in relocations.items() if functions[FUNCTION]['value']<=o<functions[FUNCTION]['value']+functions[FUNCTION]['size'] for _,s in v}
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',FUNCTION,
        *['--defsym=%s=0x%X'%(s,anchors[s]) for s in sorted(used)],'-o',str(elf),str(compiled)],capture_output=True,check=True)
    return list(struct.unpack('>%dI'%(functions[FUNCTION]['size']//4),projection.sections(elf)['.text'][1][:functions[FUNCTION]['size']]))


def measure(root,out,label='candidate',body=SELECTED):
    freeze(root,out);before=(out/'before-record_gate_owner').read_text()
    obj,diagnostics=compile_owner(root,out,recovered_owner(before,body),label)
    if diagnostics:raise ValueError('Movement compiler diagnostics: '+repr(diagnostics))
    words=linked(root,out,obj,label+'-linked');raw,bindings=parts(obj)
    truth=list(struct.unpack_from('>959I',(out/'before-retail_rom').read_bytes(),ROM))
    old,diagnostics=compile_owner(root,out,before,'owner-before')
    if diagnostics:raise ValueError('Movement owner-before compiler diagnostics')
    if normalized_pools(old)!=normalized_pools(obj):raise ValueError('Changed movement owner pools')
    neighbors=same_functions(old,obj,(FUNCTION,))
    row=dict(words=len(words),frame=(-words[0])&65535,retail_words=959,retail_frame=128,
        differences=sum(a!=b for a,b in zip(words,truth)),extent_gap=len(words)-959,
        raw_sha=hashlib.sha256(raw).hexdigest(),bindings=bindings,raw_neighbors=neighbors,
        owner_pools_unchanged=True,new_guards=0,installed=False,matching_credit=0)
    try:
        padded=literal.padded_object(root,out,obj,label)
    except ValueError as exc:
        if len(words)<=959:raise
        row.update(padder_rejected=True,padder_error=str(exc))
    else:
        previous_padded=literal.padded_object(root,out,old,'owner-before')
        if same_functions(previous_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Changed padded movement neighbors')
        image,functions=build.link_owner(root,out,padded,OWNER)
        fitted=list(struct.unpack_from('>959I',image,functions[FUNCTION]['value']))
        if fitted!=words+[0]*(959-len(words)):raise ValueError('Movement padder changed executable words')
        row.update(padded_neighbors=neighbors,padded_differences=sum(a!=b for a,b in zip(fitted,truth)))
    (out/(label+'-audit.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    row=measure(root,root/BUILD)[-1]
    print(json.dumps({k:v for k,v in row.items() if k!='bindings'},indent=2),flush=True)
