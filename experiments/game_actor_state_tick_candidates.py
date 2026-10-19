"""Recover the complete actor-state tick without installing an unmatched body."""

import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from unittest.mock import patch

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner, function_span
from tools.pad_generated_object import parse_object


FUNCTION, ENTRY, ROM, WORDS = 'func_1508A6FC', 0x1508A6FC, 0xB7BAC, 678
BUILD = 'conker/build/game-actor-state-tick'
INPUTS = {
    'conker/src/game/generated_B3020.c': '5f5f14255a3c9ec9892795be08f96460e00f5b7d440ab055643dc674adc5cfba',
    'conker/retail_word_patches.us.csv': '6ab62890a80f47ef85a9dc72c3da36c9a89f5b48844be9ba59613674dbca01cb',
    'conker/build/conker.us.elf': 'cb2982f5a28805eb99f092abc2577a6c16a0b0789de32e436f9a9bf69108abe8',
    'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/B3020.s': '26ef139d5592329ed22f9287267c13fefadf7f17290bc5ef1085cbe20e80b187',
    'conker/Makefile': 'cf6de057267055cf5ad789e72426b7433c0bfe37d04ae56c241332cf2f2febf4',
    'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be',
}
DECLARATIONS = '''#include <ultra64.h>
extern s32 D_800D23B0;
extern u8 D_800CC2D0[];
extern u8 D_800E0BB8[];
extern s32 D_800BE9E4;
extern s8 D_800E0BD0;
extern s16 D_800872C4[];
extern s8 D_800872D0[];
extern s8 D_800872E0[];
extern s8 D_800872E8[];
extern f32 D_800872F8[];
extern u8 *D_800BE628;
extern s32 D_80082FA0;
extern u8 D_8009DA20[];
s32 func_150859AC(s16, s32);
s32 func_15085DA8(f32);
void func_1508EC5C(s32, s32);
s32 func_1508DAEC(s32, s32);
void func_1508EBF8(s32, s32);
s32 func_1508CAD8(s32, s32, s32, s32, s32, s32);
f32 func_150ADA68(void);
void func_1508B3F8(void);
void func_1504332C(s32, s32, s32, s32);
s32 func_15042D94(s32, s32, s32, void *, ...);
'''

# Array names include an offset where their domain meaning is not established.
BASELINE = '''/* Advance actor timers, state transitions and steering; return changed slots. */
s32 func_1508A6FC(void) {
    u32 changed;
    s32 previousTimer;
    u32 active;
    u32 seen;
    s32 count;
    s32 *groups;
    s32 *latches;
    s32 *actions;
    s32 *states;
    s32 *elapsed;
    s32 *timers;
    s32 *cooldowns;
    s32 *timeouts;
    s32 *events;
    s32 *groupCounts;
    s32 *scores;
    u8 idle;
    s32 drawIndex;
    u8 *drawActor;
    s32 *reset;
    s32 *timer;
    s32 *cooldown;
    s32 *state;
    s32 *event;
    u8 *eventByte;
    s32 *status;
    s32 *band;
    s32 *action;
    s32 *latch;
    s32 *elapsedTimer;
    s32 *score;
    s32 *timeout;
    s32 *counter;
    u8 *actor;
    u8 *otherActor;
    u8 *context;
    u8 *row;
    s32 slot;
    s32 offset;
    s32 first;
    u32 bit;
    s32 group;
    s32 owner;
    s32 value;
    s32 started;
    s32 expired;
    u8 actorAction;
    s16 limit;
    s8 steering;
    u16 flags;
    s32 halfWidth;

    context = (u8 *)D_800D23B0;
    changed = 0;
    slot = 0;
    active = *(u32 *)(context + 0x14);
    seen = *(u32 *)(context + 0x18);
    count = *(s32 *)(context + 0x10);
    groups = (s32 *)(context + 0xE64);
    latches = (s32 *)(context + 0x35C);
    actions = (s32 *)(context + 0x31C);
    states = (s32 *)(context + 0x19C);
    elapsed = (s32 *)(context + 0x21C);
    timers = (s32 *)(context + 0x29C);
    cooldowns = (s32 *)(context + 0x25C);
    timeouts = (s32 *)(context + 0x41C);
    events = (s32 *)(context + 0x3DC);
    groupCounts = (s32 *)(context + 0xDDC);
    scores = (s32 *)(context + 0x1574);
    if (count > 0) {
        offset = 0;
        reset = (s32 *)(context + 0x1C);
        status = (s32 *)(context + 0x39C);
        band = (s32 *)(context + 0x9C);
        do {
            bit = 1U << slot;
            *reset = 0;
            first = 0;
            value = active & bit;
            if (value == 0) {
                if (!(seen & bit)) {
                    first = 1;
                }
                seen |= bit;
            }
            if (value != 0 || first != 0) {
                actor = D_800CC2D0 + slot * 0x32C;
                group = *(s32 *)((u8 *)groups + offset);
                timer = (s32 *)((u8 *)timers + offset);
                score = (s32 *)((u8 *)scores + offset);
                cooldown = (s32 *)((u8 *)cooldowns + offset);
                timeout = (s32 *)((u8 *)timeouts + offset);
                elapsedTimer = (s32 *)((u8 *)elapsed + offset);
                event = (s32 *)((u8 *)events + offset);
                action = (s32 *)((u8 *)actions + offset);
                eventByte = D_800E0BB8 + slot;
                idle = 1;
                state = (s32 *)((u8 *)states + offset);
                latch = (s32 *)((u8 *)latches + offset);
                if (group != 0 && *(s16 *)((u8 *)D_800D23B0 + 0x16BC) == 0xB9) {
                    actor[0x1E4] = 1;
                }
                previousTimer = *timer;
                *elapsedTimer += D_800BE9E4;
                *timer += D_800BE9E4;
                *cooldown -= D_800BE9E4;
                if (*cooldown <= 0) {
                    *cooldown = 0;
                }
                *timeout -= D_800BE9E4;
                if (*timeout <= 0) {
                    *timeout = 0;
                }
                *score -= D_800BE9E4;
                if (*score < 0) {
                    *score = 0;
                }
                if (*state == 3 && (*cooldown & 0x1F) >= 0x1D) {
                    func_1508EC5C(slot, 0x8000);
                }
                *event = *eventByte;
                *eventByte &= 0x7F;
                if ((u8 *)D_800D23B0 != (u8 *)-0x4DC) {
                    *(s32 *)((u8 *)D_800D23B0 + offset + 0x4DC) =
                        (*(u8 **)(actor + 0x31C))[0x19A];
                }
                *status = func_150859AC((s16)slot, 4);
                *band = func_15085DA8(*(f32 *)(actor + 0x18));
                if (*status == 0 || first != 0 || actor[0x2FD] != 0) {
                    if (*latch == 0) {
                        actorAction = actor[0x20F];
                        if (actorAction != 0xFF) {
                            *(s32 *)((u8 *)D_800D23B0 + offset + 0x59C) = actorAction;
                        } else {
                            *(s32 *)((u8 *)D_800D23B0 + offset + 0x59C) = -1;
                        }
                        *latch = 1;
                        *cooldown = 0;
                        *state = 0;
                        *(s32 *)((u8 *)D_800D23B0 + offset + 0x5C) = 1;
                        *(s32 *)((u8 *)D_800D23B0 + offset + 0x11C) = -1;
                        counter = groupCounts + group;
                        *counter -= 1;
                        value = *event & 0x7F;
                        if (value < count) {
                            owner = groups[value];
                            if (group != owner) {
                                counter = groupCounts + owner;
                                *counter += 1;
                            }
                        }
                        if (*(s16 *)((u8 *)D_800D23B0 + 0x16BC) != 0xB9) {
                            *(s32 *)((u8 *)D_800D23B0 + offset + 0xFF0) = 0;
                            func_1508DAEC(slot, 1);
                        }
                        changed |= bit;
                    }
                } else {
                    *latch = 0;
                }
                value = *action;
                if (value != 0 && *(s16 *)((u8 *)D_800D23B0 + 0x16BC) != 0xB8) {
                    expired = 0;
                    if (*state != 1 && *elapsedTimer < 0x1E) {
                        actorAction = actor[0x232];
                        actor[0x222] = value - 2;
                        if (actorAction != 4 && actorAction != 5) {
                            func_1508EBF8(slot, 4);
                        }
                        if (actorAction == 4) {
                            *elapsedTimer = 0;
                        }
                        if (actorAction == 5) {
                            *elapsedTimer = 0x1E;
                            *(f32 *)((u8 *)D_800D23B0 + offset + 0x1868) = D_800872F8[D_800E0BD0];
                            *(f32 *)((u8 *)D_800D23B0 + offset + 0x17A8) =
                                func_150ADA68() * 50.0f + *(f32 *)(actor + 0x14);
                            *(f32 *)((u8 *)D_800D23B0 + offset + 0x17E8) = *(f32 *)(actor + 0x18) + 40.0f;
                            *(f32 *)((u8 *)D_800D23B0 + offset + 0x1828) =
                                func_150ADA68() * 50.0f + *(f32 *)(actor + 0x1C);
                            value = *action;
                            if (value - 2 >= 2) {
                                otherActor = D_800CC2D0 + value * 0x32C - 0x658;
                                row = (u8 *)D_800D23B0 + offset;
                                *(f32 *)(row + 0x17A8) +=
                                    (*(f32 *)(otherActor + 0x14) - *(f32 *)(actor + 0x14)) * 0.5f;
                                row = (u8 *)D_800D23B0 + offset;
                                *(f32 *)(row + 0x1828) +=
                                    (*(f32 *)(otherActor + 0x1C) - *(f32 *)(actor + 0x1C)) * 0.5f;
                            }
                        }
                    }
                    idle = 0;
                    value = *timer;
                    started = 0;
                    if (D_800872D0[D_800E0BD0] < value) {
                        *timer = 0;
                        previousTimer = -1;
                        value = *timer;
                    }
                    if (value >= 0 && previousTimer < 0) {
                        started = 1;
                    }
                    limit = D_800872C4[D_800E0BD0];
                    if (limit != -1 && *elapsedTimer >= limit) {
                        expired = 1;
                    }
                    row = (u8 *)D_800D23B0 + slot;
                    steering = *(s8 *)(row + 0x1725);
                    *(s8 *)(row + 0x1725) = steering + ((*(s8 *)(row + 0x1705) - steering) >> 2);
                    row = (u8 *)D_800D23B0 + slot;
                    steering = *(s8 *)(row + 0x1735);
                    *(s8 *)(row + 0x1735) = steering + ((*(s8 *)(row + 0x1715) - steering) >> 2);
                    row = (u8 *)D_800D23B0 + slot;
                    if (func_1508CAD8(slot, *action - 2, started, expired,
                        *(s8 *)(row + 0x1725), *(s8 *)(row + 0x1735)) != 0 && *state != 1) {
                        *elapsedTimer = 0;
                    }
                    if (*timer == 0) {
                        ((u8 *)D_800D23B0)[slot + 0x1705] = 0;
                        ((u8 *)D_800D23B0)[slot + 0x1715] = 0;
                        if (D_800872E8[D_800E0BD0] < (s32)(func_150ADA68() * 100.0f)) {
                            if (func_150ADA68() > 0.5f) {
                                ((u8 *)D_800D23B0)[slot + 0x1705] = -50;
                            } else {
                                ((u8 *)D_800D23B0)[slot + 0x1705] = 50;
                            }
                            if (func_150ADA68() > 0.5f) {
                                ((u8 *)D_800D23B0)[slot + 0x1715] = 50;
                            } else {
                                ((u8 *)D_800D23B0)[slot + 0x1715] = 0;
                            }
                        }
                    }
                }
                if (idle != 0 && *(s16 *)((u8 *)D_800D23B0 + 0x16BC) != 0xB8) {
                    *timer = -D_800872E0[D_800E0BD0];
                }
                flags = *(u16 *)(actor + 0x22C);
                *(u16 *)(actor + 0x22C) = flags & 0xFDFF;
                if ((flags & 0x200) || (*event & 0x80)) {
                    *state = 0;
                    *reset = 1;
                }
                if ((*(u8 **)(actor + 0x31C))[0x1AC] != 0) {
                    *cooldown = 0x14;
                }
            } else {
                *status = 0;
                *band = -1;
            }
            slot++;
            band++;
            status++;
            reset++;
            offset += 4;
        } while (slot != count);
    }
    *(u32 *)((u8 *)D_800D23B0 + 0x18) = seen;
    if (D_800BE9E4 != 0) {
        *(f32 *)((u8 *)D_800D23B0 + 0x16B4) = (f32)D_800BE9E4;
    } else {
        *(f32 *)((u8 *)D_800D23B0 + 0x16B4) = 1.0f;
    }
    if ((u8 *)D_800D23B0 != (u8 *)-0x55C) {
        func_1508B3F8();
    }
    if (*(s16 *)((u8 *)D_800D23B0 + 0x16BC) == 0xB9) {
        halfWidth = (s32)(*(f32 *)(D_800BE628 + 0x30) - *(f32 *)(D_800BE628 + 0x2C)) >> 1;
        func_1504332C(0xFF, 0xFF, 0xFF, 0xFF);
        drawActor = D_800CC2D0;
        drawIndex = 0;
        if (D_80082FA0 >= 0) {
            do {
                if (drawActor[0x128] == 0) {
                    row = D_800BE628 + drawIndex * 0x180;
                    func_15042D94((s32)(*(f32 *)(row + 0x2C) + (f32)halfWidth),
                        (s32)(*(f32 *)(row + 0x24) + 6.0f), 1, D_8009DA20, scores[drawIndex] / 60);
                }
                drawIndex++;
                drawActor += 0x32C;
            } while (D_80082FA0 >= drawIndex);
        }
    }
    return changed;
}'''


def candidates():
    forms = [('baseline', BASELINE)]
    forms.append(('word-action', BASELINE.replace('    u8 actorAction;', '    s32 actorAction;')))
    reused = BASELINE.replace('    s32 drawIndex;\n', '').replace('    u8 *drawActor;\n', '')
    reused = reused.replace('drawIndex', 'slot').replace('drawActor', 'actor')
    forms.append(('reuse-draw-cursors', reused))
    captures = ('groups', 'latches', 'actions', 'states', 'elapsed', 'timers',
                'cooldowns', 'timeouts', 'events', 'groupCounts', 'scores')
    initialized = BASELINE
    for name in captures:
        assignment = next(line for line in initialized.splitlines() if line.startswith('    ' + name + ' ='))
        initialized = initialized.replace('    s32 *' + name + ';\n', '')
        initialized = initialized.replace(assignment + '\n', '')
        initialized = initialized.replace('    s32 halfWidth;\n',
            '    s32 halfWidth;\n' + assignment.replace('    ' + name + ' =', '    s32 *' + name + ' ='))
    initialized = initialized.replace('    u8 *context;\n', '')
    initialized = initialized.replace('    context = (u8 *)D_800D23B0;\n', '')
    initialized = initialized.replace('    s32 halfWidth;\n',
        '    s32 halfWidth;\n    u8 *context = (u8 *)D_800D23B0;\n')
    forms.append(('initialized-captures', initialized))
    forms.append(('initialized-word-action', initialized.replace('    u8 actorAction;', '    s32 actorAction;')))
    integer = BASELINE.replace('    u8 *context;', '    s32 context;')
    integer = integer.replace('context = (u8 *)D_800D23B0;', 'context = D_800D23B0;')
    forms.append(('integer-context', integer))
    forms.append(('integer-reused-cursors', integer.replace('    s32 drawIndex;\n', '')
                  .replace('    u8 *drawActor;\n', '').replace('drawIndex', 'slot').replace('drawActor', 'actor')))
    return forms


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, expected in INPUTS.items():
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Actor tick input changed: ' + name)
        copy = output / ('before-' + name.replace('/', '_'))
        if copy.exists() and copy.read_bytes() != data:
            raise ValueError('Actor tick snapshot changed: ' + name)
        if not copy.exists():
            copy.write_bytes(data)
        result[name] = data
    return result


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero actor-tick alignment tail')
    return raw[:end * 4], {at - info['value']: entries for at, entries in bindings.items()
                          if info['value'] <= at < info['value'] + end * 4}


def compile_unit(root, output, name, unit, unroll=False):
    output.mkdir(parents=True, exist_ok=True)
    run, commands = subprocess.run, []

    def profile(argv, **kwargs):
        if argv[0] == str(root / 'ido/ido5.3_recomp/cc'):
            argv = list(argv)
            if not unroll:
                argv.insert(argv.index('-O2'), '-Wo,-loopunroll,0')
            commands.append(argv)
        return run(argv, **kwargs)

    with patch.object(subprocess, 'run', side_effect=profile):
        obj, diagnostics = compile_owner(root, output, unit, name)
    if len(commands) != 1:
        raise ValueError('Unexpected actor-tick compiler invocation')
    (output / (name + '-command.json')).write_text(json.dumps(commands[0], indent=2) + '\n')
    return obj, diagnostics


def compile_candidate(root, output, name, body=BASELINE, unroll=False):
    obj, diagnostics = compile_unit(root, output, name, DECLARATIONS + '\n' + body + '\n', unroll)
    raw, bindings = payload(obj)
    text, functions = link_owner(root, output, obj, 'generated_B3020')
    info = functions[FUNCTION]
    linked = text[info['value']:info['value'] + len(raw)]
    words = struct.unpack('>%dI' % (len(linked) // 4), linked)
    truth = struct.unpack_from('>678I', (root / 'conker/conker.us.bin').read_bytes(), ROM)
    differences = [(i, '%08X' % a, '%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b]
    record = dict(name=name, body_words=len(words), frame=(-words[0]) & 65535,
                  aligned_differences=len(differences) + abs(len(words) - WORDS),
                  differences=differences, relocations=sum(map(len, bindings.values())),
                  raw_sha256=hashlib.sha256(raw).hexdigest(), diagnostics=diagnostics,
                  unroll=unroll, installed=False, matching_credit=0)
    (output / (name + '-receipt.json')).write_text(json.dumps(record, indent=2) + '\n')
    return record, words


def owner_screen(root, output):
    from tools.experiments.game_graphics_task_submit import same_functions
    from tools.tests.game_owner_pool import normalized_pools

    values = freeze(root, output)
    before = values['conker/src/game/generated_B3020.c'].decode()
    lo, hi = function_span(before, FUNCTION)
    # Keep the unrecovered callee's existing old-style zero-return definition.
    declarations = DECLARATIONS.split('\n', 1)[1].replace(
        's32 func_1508CAD8(s32, s32, s32, s32, s32, s32);', 's32 func_1508CAD8();')
    unit = before[:lo] + declarations + '\n' + BASELINE + before[hi:]
    records = []
    for name, normal in (('primary', False), ('normal', True)):
        old, old_diagnostics = compile_unit(root, output, 'before-' + name, before, normal)
        new, new_diagnostics = compile_unit(root, output, 'after-' + name, unit, normal)
        if old_diagnostics or new_diagnostics:
            raise ValueError('Unexpected actor-tick owner diagnostics')
        if same_functions(old, new, (FUNCTION,)) != 72 or normalized_pools(old) != normalized_pools(new):
            raise ValueError('Actor-tick research changed another owner body/pool')
        raw, bindings = payload(new)
        isolated, _ = compile_candidate(root, output, 'isolated-' + name, unroll=normal)
        if raw != payload(output / ('isolated-' + name + '.o'))[0]:
            raise ValueError('Complete-owner actor tick differs from isolated source')
        if bindings != payload(output / ('isolated-' + name + '.o'))[1]:
            raise ValueError('Complete-owner actor tick changed isolated bindings')
        records.append(dict(profile=name, preserved_neighbors=72, pools_unchanged=True,
                            isolated_words_and_bindings_equal=True,
                            body_words=isolated['body_words'], frame=isolated['frame']))
    for path, data in values.items():
        if (root / path).read_bytes() != data:
            raise ValueError('Actor-tick screen modified production input: ' + path)
    (output / 'owner-receipt.json').write_text(json.dumps(records, indent=2) + '\n')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal', action='store_true')
    parser.add_argument('--names', nargs='*')
    parser.add_argument('--owner', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    freeze(root, output)
    if args.owner:
        print(json.dumps(owner_screen(root, output / 'owner'), indent=2))
        return
    forms = candidates()
    if args.names:
        if not set(args.names) <= dict(forms).keys():
            parser.error('unknown actor-tick candidate')
        forms = [(n, b) for n, b in forms if n in args.names]
    for name, body in forms:
        row, _ = compile_candidate(root, output, name + ('-normal' if args.normal else ''), body, args.normal)
        print(json.dumps({k: v for k, v in row.items() if k != 'differences'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
