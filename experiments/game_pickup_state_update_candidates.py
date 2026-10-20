"""Recover the player-item/effect and pickup-respawn update without installing it."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner, function_span
from tools.pad_generated_object import parse_object


FUNCTION, ENTRY, ROM, WORDS = 'func_1508DC24', 0x1508DC24, 0xBB0D4, 681
SOURCE, OWNER = 'conker/src/game/generated_B3020.c', 'generated_B3020'
BUILD = 'conker/build/game-pickup-state-update'
INPUTS = {
    SOURCE: 'c70559485e1f832e727d1fcd19603b013d1ac3010cb357a1f5e171ef762d24e8',
    'conker/retail_word_patches.us.csv': 'deb492afd7196d2c0109980a2b05634af1eacad9cb1fbfc33d84d0d17468a05c',
    'conker/build/conker.us.elf': '40623350a4c531d2ef27a110ca30ea329b22e11c1dba97d8554907a674a20132',
    'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/B3020.s': '26ef139d5592329ed22f9287267c13fefadf7f17290bc5ef1085cbe20e80b187',
    'conker/Makefile': '54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf',
    'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be',
}
DECLARATIONS = '''#include <ultra64.h>
extern s32 D_800D23B0;
extern u8 D_800CC2D0[];
extern u8 D_800D121C[];
extern s8 D_80087340;
extern s32 D_800BE9E4;
extern f32 D_8009DA90;
s32 func_1508E780(s32);
s32 func_1508EB90(s32, s32, s32);
void func_1502EA50(u8 *);
void func_1502EA0C(u8 *, s32, s32, s32, s32, s32);
void func_15080620(s32, s32, s32, s32);
s32 func_15033E28(u8 *, u8 **);
u8 *func_15083568(u8 *, s32, f32, s32);
void func_15030158(u8 *, s32);
void func_151027E8(u8 *);
void func_15060F28(u8 *, s32);
u8 *func_151149AC(u8);
f32 func_150ADA68(void);
s32 func_15086D48(s32);
s32 func_15086CBC(s32, f32 *, f32 *, f32 *);
s32 func_1508DAEC(s32, s32);
'''
INITIAL = '''/* Update player item states, attached effects and pickup respawns. */
void func_1508DC24(void) {
    s32 player;
    f32 x;
    f32 y;
    f32 z;
    s32 *owners;
    u8 *selectors;
    s32 *held;
    s32 *overrides;
    s32 *timers;
    s32 *kinds;
    s32 *flags;
    s32 *fixedTargets;
    s32 *grace;
    s32 *savedX;
    s32 *savedY;
    s32 *savedZ;
    u8 *attached[10];
    f32 scale;
    s32 *targets;
    u8 *state;
    u8 *actor;
    u8 *data;
    u8 *item;
    u8 *scan;
    u8 **cursor;
    s32 count;
    s32 desired;
    s32 previous;
    s32 animation;
    s32 found;
    s32 attachedCount;
    s32 i;
    s32 index;
    s32 owner;
    s32 node;
    s32 chosen;
    s16 mode;

    state = (u8 *)D_800D23B0;
    player = 0;
    owners = (s32 *)(state + 0xEB0);
    selectors = state + 0xEF0;
    held = (s32 *)(state + 0xF70);
    overrides = (s32 *)(state + 0xFF0);
    timers = (s32 *)(state + 0x1070);
    kinds = (s32 *)(state + 0x1174);
    flags = (s32 *)(state + 0x11F4);
    fixedTargets = (s32 *)(state + 0x1274);
    grace = (s32 *)(state + 0x12F4);
    savedX = (s32 *)(state + 0x1374);
    savedY = (s32 *)(state + 0x13F4);
    savedZ = (s32 *)(state + 0x1474);
    count = *(s32 *)(state + 0x10);
    actor = D_800CC2D0;
    targets = (s32 *)(state + 0x10F0);
    if (count > 0) {
        scale = 1.0f;
        do {
            mode = *(s16 *)(state + 0x16BC);
            if (mode != 0xB9 || actor[0x128] == 0) {
                data = *(u8 **)(actor + 0x31C);
                previous = data[0x75] & 0x7F;
                desired = overrides[player];
                if (data[0x19B] >= 5) {
                    desired = 0x3A;
                } else if (data[0x19B] > 0) {
                    desired = 0x26;
                }
                if (desired == 0) {
                    index = owners[player];
                    if (index != -1) {
                        desired = kinds[index];
                    } else {
                        desired = *(s32 *)(state + 0x1170);
                    }
                } else if (desired == 0x457) {
                    desired = 0;
                }
                if (mode == 0xB8) {
                    previous = data[0x128] & ~0x20;
                }
                if (desired != previous) {
                    animation = func_1508E780(previous);
                    if (animation != -1) {
                        animation &= ~0x1000;
                        func_1508EB90(player, 0x4C, animation);
                        if (animation == 0x1D) {
                            func_1508EB90(player, 0x4C, 0x1E);
                        }
                        (*(u8 **)(actor + 0x31C))[0x11A] = 0;
                    }
                    animation = func_1508E780(desired);
                    if (animation >= 0x1001) {
                        func_1508EB90(player, 0x4B, animation & ~0x1000);
                    }
                    if (*(s16 *)((u8 *)D_800D23B0 + 0x16BC) == 0xB8) {
                        if (previous == 0x80) {
                            func_1502EA50(actor);
                            actor[0x125] = 0;
                        }
                        (*(u8 **)(actor + 0x31C))[0x128] = desired;
                        if (desired == 1) {
                            *(s16 *)(*(u8 **)(actor + 0x31C) + 0x12C) = 600;
                        } else if (desired == 0x80) {
                            *(s16 *)(*(u8 **)(actor + 0x31C) + 0x12C) = 1800;
                            func_1502EA0C(actor, 0, 0, 255, 191, 4);
                        } else if (desired == 0x10) {
                            *(s16 *)(*(u8 **)(actor + 0x31C) + 0x12C) = 3;
                        }
                    } else {
                        func_15080620(player, 1, desired, 0);
                        if (desired == 0 && previous != 3) {
                            (*(u8 **)(actor + 0x31C))[0x78] = 0;
                        }
                        if (previous == 0x20) {
                            func_1508EB90(player, 0x45, 4);
                        }
                        if (desired == 0x20) {
                            func_1508EB90(player, 0x45, 3);
                        }
                    }
                }
                state = (u8 *)D_800D23B0;
                if (D_80087340 == player && *(s16 *)(state + 0x16BC) != 0xB8) {
                    found = 0;
                    animation = func_1508E780(desired);
                    attachedCount = func_15033E28(actor, attached);
                    if (attachedCount == 0 && (*(u8 **)(actor + 0x31C))[0x11A] == 2 &&
                        animation != 0x55 && animation != 0x2E) {
                        func_15083568(actor, animation, scale, 0);
                        if (animation == 0x1D) {
                            func_15083568(actor, 0x1E, scale, 0);
                        }
                    }
                    if (attachedCount != 0 && desired != 0x20) {
                        i = 0;
                        if (animation != -1) {
                            animation &= ~0x1000;
                            cursor = attached;
                            if (attachedCount > 0) {
                                do {
                                    item = *cursor;
                                    index = item[6];
                                    if ((index != 0x1E || animation != 0x1D) && animation != index &&
                                        index != 0x2A && index != 0x22 && index != 0x2D &&
                                        index != 0x72 && index != 0x73 && index != 0x76 &&
                                        index != 0x77 && index != 0x78 && index != 7) {
                                        func_15030158(item, 0);
                                        (*(u8 **)(actor + 0x31C))[0x11A] = 0;
                                    } else if (animation == index) {
                                        found = 1;
                                    }
                                    i++;
                                    cursor++;
                                } while (i != attachedCount);
                            }
                            if (found == 0 && (*(u8 **)(actor + 0x31C))[0x11A] == 2 &&
                                animation != 0x55 && animation != 0x2E) {
                                func_15083568(actor, animation, scale, 0);
                                if (animation == 0x1D) {
                                    func_15083568(actor, 0x1E, scale, 0);
                                }
                            }
                        } else {
                            cursor = attached;
                            if (attachedCount > 0) {
                                do {
                                    item = *cursor;
                                    index = item[6];
                                    if (index != 0x2A && index != 0x22 && index != 0x2C &&
                                        index != 0x64 && index != 0x2D && index != 0x72 &&
                                        index != 0x73 && index != 0x76 && index != 0x77 &&
                                        index != 0x78 && index != 7) {
                                        func_15030158(item, 0);
                                        (*(u8 **)(actor + 0x31C))[0x11A] = 0;
                                    }
                                    i++;
                                    cursor++;
                                } while (i != attachedCount);
                            }
                        }
                    }
                    if (animation != 0x55) {
                        index = *(s32 *)((u8 *)D_800D23B0 + 0x10);
                        if (index < 25) {
                            scan = D_800CC2D0 + index * 0x32C;
                            do {
                                if (*(s32 *)scan != 0 && scan[0x65] == player + 1 && scan[4] == 0x6E) {
                                    func_151027E8(scan);
                                    func_15060F28(scan, 0);
                                    break;
                                }
                                scan += 0x32C;
                            } while ((u32)scan < (u32)D_800D121C);
                        }
                    }
                    state = (u8 *)D_800D23B0;
                }
                count = *(s32 *)(state + 0x10);
            }
            player++;
            actor += 0x32C;
        } while (player < count);
        player = 0;
    }
    D_80087340++;
    if (D_80087340 >= count) {
        D_80087340 = 0;
    }
    index = 0;
    if (*(s32 *)(state + 0xEA4) > 0) {
        scale = D_8009DA90;
        do {
            item = func_151149AC(selectors[3]);
            if (item != 0) {
                if (grace[index] != 0) {
                    grace[index] -= D_800BE9E4;
                    if (grace[index] <= 0) {
                        timers[index] = 4;
                        grace[index] = 0;
                    }
                }
                if (timers[index] > 0) {
                    timers[index] -= D_800BE9E4;
                    if (timers[index] <= 0) {
                        timers[index] = 0;
                        item[0x6E] = 0;
                        if (grace[index] != 0) {
                            *(s16 *)(item + 0x10) = savedX[index];
                            *(s16 *)(item + 0x12) = savedY[index];
                            *(s16 *)(item + 0x14) = savedZ[index];
                        } else if (!(flags[index] & 4)) {
                            if (flags[index] & 1) {
                                x = (f32)*(s32 *)((u8 *)D_800D23B0 + 0xEA8);
                                do {
                                    chosen = (s32)(func_150ADA68() * scale * x);
                                    for (i = 0; i < *(s32 *)((u8 *)D_800D23B0 + 0xEA8); i++) {
                                        if (chosen == targets[i]) {
                                            chosen = -1;
                                            i = 1000;
                                        }
                                    }
                                } while (chosen == -1);
                            } else {
                                chosen = fixedTargets[index];
                            }
                            targets[index] = chosen;
                            node = func_15086D48(*(s32 *)((u8 *)D_800D23B0 + chosen * 4 + 0x14F4));
                            if (node != -1) {
                                func_15086CBC(node, &x, &y, &z);
                                *(s16 *)(item + 0x10) = (s32)x;
                                *(s16 *)(item + 0x12) = (s32)y + 60;
                                *(s16 *)(item + 0x14) = (s32)z;
                            }
                        }
                    }
                } else if (timers[index] == 0) {
                    owner = *(s32 *)(item + 0x80) - 1;
                    if (owner != -1) {
                        *(s32 *)(item + 0x80) = 0;
                        if (kinds[index] == 0x8AE) {
                            actor = D_800CC2D0 + owner * 0x32C;
                            data = *(u8 **)(actor + 0x31C);
                            data[0x19A] += 3;
                            data = *(u8 **)(actor + 0x31C);
                            if (data[0x19A] >= 7) {
                                data[0x19A] = 6;
                            }
                            timers[index] = *(s32 *)((u8 *)D_800D23B0 + 0xEAC);
                        } else {
                            func_1508DAEC(owner, 0);
                            if (flags[index] & 2) {
                                timers[index] = *(s32 *)((u8 *)D_800D23B0 + 0xEAC);
                            } else {
                                timers[index] = -1;
                                held[index] = owner | 0x2000;
                                targets[index] = -1;
                            }
                            grace[index] = 0;
                            owners[owner] = player;
                            *(s32 *)((u8 *)D_800D23B0 + owner * 4 + 0x5C) = 1;
                        }
                        mode = *(s16 *)((u8 *)D_800D23B0 + 0x16BC);
                        if (mode == 0xB9) {
                            *(s16 *)(*(u8 **)(D_800CC2D0 + owner * 0x32C + 0x31C) + 0x12C) = 600;
                            mode = *(s16 *)((u8 *)D_800D23B0 + 0x16BC);
                        }
                        if (mode == 0xB8) {
                            data = *(u8 **)(D_800CC2D0 + owner * 0x32C + 0x31C);
                            chosen = kinds[index];
                            if (chosen == data[0x128]) {
                                if (chosen == 1) {
                                    *(s16 *)(data + 0x12C) = 600;
                                } else if (chosen == 0x80) {
                                    *(s16 *)(data + 0x12C) = 1800;
                                } else if (chosen == 0x10) {
                                    *(s16 *)(data + 0x12C) = 3;
                                }
                            }
                        }
                    }
                }
            }
            index++;
            selectors += 4;
            player++;
            state = (u8 *)D_800D23B0;
        } while (player < *(s32 *)(state + 0xEA4));
    }
}
'''


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    values = {}
    for name, digest in INPUTS.items():
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Pickup-update input changed: ' + name)
        saved = output / ('before-' + name.replace('/', '_'))
        if saved.exists() and saved.read_bytes() != data:
            raise ValueError('Pickup-update snapshot changed: ' + name)
        if not saved.exists():
            saved.write_bytes(data)
        values[name] = data
    return values


def compile_candidate(root, output, name='selected', body=None, normal=False, whole=False):
    values = freeze(root, output)
    body = SELECTED if body is None else body
    unit = DECLARATIONS + '\n' + body
    if whole:
        before = values[SOURCE].decode()
        lo, hi = function_span(before, FUNCTION)
        unit = before[:lo] + DECLARATIONS.split('\n', 1)[1] + '\n' + body + before[hi:]
    run, commands = subprocess.run, []

    def profile(argv, **kwargs):
        if argv[0] == str(root / 'ido/ido5.3_recomp/cc'):
            argv = list(argv)
            if not normal:
                argv.insert(argv.index('-O2'), '-Wo,-loopunroll,0')
            commands.append(argv)
        return run(argv, **kwargs)

    with patch.object(subprocess, 'run', side_effect=profile):
        obj, diagnostics = compile_owner(root, output, unit, name)
    if len(commands) != 1:
        raise ValueError('Unexpected pickup-update compiler invocation')
    text, functions, bindings = parse_object(obj)
    item = functions[FUNCTION]
    raw = text[item['value']:item['value'] + item['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, w in enumerate(words) if w == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero pickup-update alignment tail')
    raw = raw[:end * 4]
    image, functions = link_owner(root, output, obj, OWNER)
    linked = list(struct.unpack_from('>%dI' % end, image, functions[FUNCTION]['value']))
    truth = struct.unpack_from('>681I', values['conker/conker.us.bin'], ROM)
    report = dict(words=end, frame=(-linked[0]) & 65535 if linked[0] >> 16 == 0x27BD else 0,
        differences=sum(a != b for a, b in zip(linked, truth)) + abs(end - WORDS),
        raw_SHA256=hashlib.sha256(raw).hexdigest(), normal=normal, diagnostics=diagnostics,
        installed=False, matching_credit=0)
    (output / (name + '-command.json')).write_text(json.dumps(commands[0], indent=2) + '\n')
    (output / (name + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    return obj, linked, report


def candidates():
    byte_cursor = INITIAL
    begin = byte_cursor.index('    D_80087340++;')
    opening, tail = byte_cursor[:begin], byte_cursor[begin:]
    for table in ('owners', 'held', 'timers', 'kinds', 'flags', 'fixedTargets',
            'grace', 'savedX', 'savedY', 'savedZ', 'targets'):
        tail = tail.replace(table + '[index]', '(*(s32 *)((u8 *)' + table + ' + index))')
    tail = tail.replace('            index++;', '            index += 4;')
    byte_cursor = opening + tail
    yield 'initial', INITIAL
    yield 'byte-cursor', byte_cursor
    for name, body in (('captured-base', INITIAL), ('byte-cursor-base', byte_cursor)):
        begin = body.index('    D_80087340++;')
        opening, tail = body[:begin], body[begin:]
        tail = tail.replace('    index = 0;', '    index = 0;\n    scan = D_800CC2D0;', 1)
        tail = tail.replace('D_800CC2D0 + owner * 0x32C', 'scan + owner * 0x32C')
        yield name, opening + tail


SELECTED = dict(candidates())['byte-cursor']


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD / 'screen'
    for name, body in candidates():
        _, _, row = compile_candidate(root, output, name, body)
        print(name, row)
