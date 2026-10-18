"""Recover the complete route projection, look-ahead and ranking caller privately."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from unittest.mock import patch

from tools.experiments import game_route_record_integration as previous
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools

BUILD = 'conker/build/game-route-actor-update'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_B3020', 'func_15087350', 0x15087350, 0xB4800, 604
INPUTS = dict(previous.INPUTS, **previous.AFTER)
prior, checkpoint = previous.prior, previous.checkpoint
RAW_SHA = '03e0bcd8128c750b74ad4594a9ce0cf24b83faf78b5b1276e4ae1425aaf436e8'
BINDING_SHA = '401747e4fa7527b029b18bc9f3754e4322e42aa48d90ad2f9f7ffd81b308b7ab'
SELECTED = '''/* Project an actor onto its route, update look-ahead state, then rank players. */
void func_15087350(s32 recordIndex, s32 active, f32 lookAhead) {
    extern f32 D_8009D9E0, D_8009D9E4, D_8009D9E8;
    extern f64 D_8009D9F0;
    extern f32 D_8009D9F8, D_8009D9FC;
    extern s8 D_800D2390, D_800D23A9;
    extern s32 D_800BE9E4;
    extern u16 D_800D18A0;
    extern f32 D_800D239C, D_800D23A0, D_800D23A4, D_800CC310;
    extern u8 **D_800D2104;
    extern void func_15088F30(u8 *, f32 *, f32 *, f32 *);
    extern f32 func_150498A4(f32 *, s32, f32, f32 *);
    extern f32 func_150497E0(f32 *, s32, f32);
    extern s32 func_15088A08(u8 *, f32);
    extern void func_15042D78(s32);
    extern void func_1508802C(u8 *, u8 *, s32);
    f32 startZ;
    f32 positionX;
    f32 positionZ;
    f32 slopeX;
    f32 slopeZ;
    f32 intercept;
    f32 error;
    f32 absoluteError;
    f32 previousError;
    f32 chordLength;
    f32 x[4];
    f32 y[4];
    f32 z[4];
    u8 *actor;
    s8 refresh;
    u8 copy[0x84];
    s8 order[32];
    f32 scores[17];
    u32 recordOffset;
    s8 iterations;
    s32 again;
    s32 i;
    s32 last;
    s32 sorted;
    s8 temporary;
    u8 *record;
    u8 *cursor;
    f32 step;
    f32 valueX;
    f32 valueZ;
    f32 inverse;
    f32 gain;
    f32 angle;
    f32 temporaryScore;

    iterations = 0;
    if (D_800872A0 == 0) {
        return;
    }
    recordOffset = (u32)recordIndex * 0x84u;
    record = D_800872A0 + recordOffset;
    actor = D_800CC2D0 + (s8)record[0x31] * 0x32C;
    positionX = *(f32 *)(actor + 0x14);
    positionZ = *(f32 *)(actor + 0x1C);
    D_800D2390 = 0;
    if ((s8)record[0x30] == 0) {
        *(f32 *)record = 0.5f;
    } else {
        step = (*(f32 *)(record + 4) - *(f32 *)record) * 0.125f;
        if (D_8009D9E0 < step) {
            step = D_8009D9E0;
        }
        if (step < D_8009D9E4) {
            step = D_8009D9E4;
        }
        *(f32 *)record += step;
    }
    previousError = D_8009D9E8;
    gain = 0.75f;
    refresh = 1;
    do {
        again = 0;
        if (refresh != 0) {
            func_15088F30(record, x, y, z);
            slopeX = x[2] - x[1];
            slopeZ = z[2] - z[1];
            chordLength = sqrtf(slopeX * slopeX + slopeZ * slopeZ);
        }
        valueX = func_150498A4(x, 0, *(f32 *)(record + 8), &slopeX);
        valueZ = func_150498A4(z, 0, *(f32 *)(record + 8), &slopeZ);
        inverse = -1.0f / sqrtf(slopeX * slopeX + slopeZ * slopeZ);
        slopeX *= inverse;
        slopeZ *= inverse;
        *(f32 *)(record + 0xC) = slopeX;
        *(f32 *)(record + 0x10) = slopeZ;
        intercept = -(valueX * slopeX + valueZ * slopeZ);
        error = (slopeX * positionX + slopeZ * positionZ) + intercept;
        if (error < -50.0f || 50.0f < error) {
            absoluteError = error;
            if (error < 0.0f) {
                absoluteError = -error;
            }
            if (previousError < absoluteError) {
                gain *= 0.5f;
            }
            previousError = absoluteError;
            step = (error * gain) / chordLength;
            if (step < -0.5f) {
                step = -0.5f;
            }
            if (0.5f < step) {
                step = 0.5f;
            }
            refresh = func_15088A08(record, -step);
            again = 1;
        }
        iterations++;
        if (iterations >= 11) {
            again = 0;
        }
    } while (again != 0);
    func_15042D78(0x80);
    record[0x32] = record[0x33];
    record[0x33] = D_800BE9E4;
    *(f32 *)(record + 0x14) = (((*(f32 *)(actor + 0x2C) * slopeX +
        *(f32 *)(actor + 0x34) * slopeZ) + intercept) - error) * 4.0f / (f32)(s8)record[0x32];
    if ((s8)record[0x30] != 0) {
        bcopy(record, copy, 0x84);
        func_15088A08(copy, lookAhead + lookAhead);
        func_15088F30(copy, x, y, z);
        D_800D239C = func_150497E0(x, 0, *(f32 *)(copy + 8));
        D_800D23A0 = func_150497E0(y, 0, *(f32 *)(copy + 8));
        D_800D23A4 = func_150497E0(z, 0, *(f32 *)(copy + 8));
        if (recordIndex < D_800D2398) {
            if (active == 0) {
                angle = (f32)((f64)D_800CC310 * D_8009D9F0);
                D_800D239C = sinf(angle) * 300.0f + *(f32 *)(actor + 0x14);
                D_800D23A0 = *(f32 *)(actor + 0x18);
                D_800D23A4 = cosf(angle) * 300.0f + *(f32 *)(actor + 0x1C);
            }
            *(s16 *)(D_800D2104[actor[0x13F]] + 8) = (s32)D_800D239C;
            *(s16 *)(D_800D2104[actor[0x13F]] + 10) = (s32)D_800D23A0;
            *(s16 *)(D_800D2104[actor[0x13F]] + 12) = (s32)D_800D23A4;
            *(f32 *)(actor + 0x44) = (f32)active;
            if (D_800D2390 == 1) {
                *(f32 *)(actor + 0x20) = 75.0f;
            } else if (D_800D2390 == 2) {
                *(f32 *)(actor + 0x20) = 55.0f;
            } else if (D_800D2390 == 3) {
                *(f32 *)(actor + 0x20) = 65.0f;
            }
            actor[0x21E] = 0;
        }
    } else {
        *(f32 *)record = 0.0f;
        func_15088F30(record, x, y, z);
        valueX = func_150497E0(x, 0, *(f32 *)(record + 8));
        startZ = func_150497E0(z, 0, *(f32 *)(record + 8));
        *(f32 *)record = 1.0f;
        func_15088F30(record, x, y, z);
        slopeX = func_150497E0(x, 0, *(f32 *)(record + 8)) - valueX;
        valueZ = func_150497E0(z, 0, *(f32 *)(record + 8));
        slopeZ = valueZ - startZ;
        chordLength = sqrtf(slopeX * slopeX + slopeZ * slopeZ);
        if (1.0f < chordLength) {
            inverse = 1.0f / chordLength;
            slopeX *= inverse;
            slopeZ *= inverse;
            *(f32 *)record = ((slopeX * positionX + slopeZ * positionZ) -
                (slopeX * valueX + slopeZ * startZ)) * inverse;
        } else {
            *(f32 *)record = 0.0f;
        }
    }
    record[0x48] = active;
    D_800D23A9 = 1;
    if ((s8)record[0x30] == 0 && record[0x48] > 0 &&
        !(D_800D18A0 & (1u << ((u32)(s8)record[0x31] & 31)))) {
        *(u32 *)(record + 0x1C) += (u32)D_800BE9E4;
    }
    if ((s8)record[0x30] >= 2 && (*(u8 **)(actor + 0x31C))[0x84] == 0) {
        func_1508802C(record, actor, 0xD);
    }
    if (recordOffset == 0) {
        last = D_800D2398 - 1;
        cursor = D_800872A0;
        for (i = 0; i < D_800D2398; i++) {
            order[i] = i;
            scores[i] = *(f32 *)(cursor + 8) + (f32)*(s16 *)(cursor + 0x24);
            if ((s8)cursor[0x2A] != 0x7F) {
                scores[i] += D_8009D9F8 - (f32)(s8)cursor[0x2A] * 1000.0f;
            }
            if (D_800D18A0 & (1u << ((u32)(s8)cursor[0x31] & 31))) {
                scores[i] -= D_8009D9FC;
            }
            cursor += 0x84;
        }
        do {
            sorted = 1;
            for (i = 0; i < last; i++) {
                if (scores[i] < scores[i + 1]) {
                    temporary = order[i + 1];
                    temporaryScore = scores[i + 1];
                    order[i + 1] = order[i];
                    order[i] = temporary;
                    scores[i + 1] = scores[i];
                    scores[i] = temporaryScore;
                    sorted = 0;
                }
            }
        } while (!sorted);
        for (i = 0; i < D_800D2398; i++) {
            D_800872A0[order[i] * 0x84 + 0x29] = i + 1;
        }
    }
}
'''


def freeze(root, out):
    with patch.object(checkpoint, 'INPUTS', INPUTS):
        return checkpoint.freeze(root, out)


def recovered_owner(before, body=SELECTED):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15087350() {\n    return 0;\n}':
        raise ValueError('Unknown complete-route-caller placeholder')
    return before[:lo] + body.rstrip() + before[hi:]


def measure(root, out, name='initial', body=SELECTED, baseline=None, normal=False):
    values = freeze(root, out)
    obj, diagnostics = prior.compile_profile(root, out,
        recovered_owner(values['conker/src/game/generated_B3020.c'].decode(), body), name, normal)
    image, functions = prior.link_owner(root, out, obj, OWNER)
    function = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (function['size'] // 4), image, function['value']))
    text, definitions, relocations = parse_object(obj)
    definition = definitions[FUNCTION]
    raw = text[definition['value']:definition['value'] + definition['size']]
    bindings = {at - definition['value']: value for at, value in relocations.items()
                if definition['value'] <= at < definition['value'] + definition['size']}
    truth = struct.unpack_from('>604I', values['conker/conker.us.bin'], ROM)
    row = dict(name=name, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        raw_sha256=hashlib.sha256(raw).hexdigest(), bindings=bindings, diagnostics=diagnostics,
        installed=False, matching_credit=0)
    if baseline is not None:
        row['neighbors'] = previous.source.installed.source.model.same_functions(baseline, obj, (FUNCTION,))
        if row['neighbors'] != 72 or normalized_pools(baseline) != normalized_pools(obj):
            raise ValueError('Route-update candidate changed another owner body or pool')
    (out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    values = freeze(root, out)
    baseline, diagnostics = prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected baseline diagnostics')
    obj, words, row = measure(root, out, 'qualified', baseline=baseline)
    checked(obj)
    if (row['words'], row['frame'], row['differences'], row['diagnostics']) != (588, 480, 599, ''):
        raise ValueError('Changed complete route-update semantic checkpoint')
    return obj, words, row


def checked(obj):
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {at - f['value']: entries for at, entries in relocations.items()
                if f['value'] <= at < f['value'] + f['size']}
    check_payload(raw, bindings)
    return raw, bindings


def check_payload(raw, bindings):
    digest = hashlib.sha256(json.dumps(bindings, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if len(raw) != 2352 or hashlib.sha256(raw).hexdigest() != RAW_SHA or digest != BINDING_SHA:
        raise ValueError('Unknown complete route-update raw code or bindings')


def forms():
    bases = [('initial', SELECTED)]
    for label, names in (('loop-step-value', ('step',)),
                         ('disjoint-float-carrier', ('step', 'absoluteError', 'angle', 'temporaryScore'))):
        body = SELECTED
        for name in names:
            marker = '    f32 ' + name + ';\n'
            if body.count(marker) != 1:
                raise ValueError('Unknown route-update temporary declaration: ' + name)
            body = re.sub(r'\b' + name + r'\b', 'valueX', body.replace(marker, ''))
        bases.append((label, body))
    yield from bases
    for label, body in bases:
        for declaration in ('    s32 i;\n', '    s32 last;\n', '    s32 sorted;\n',
                            '    s8 temporary;\n', '    u8 *cursor;\n'):
            if body.count(declaration) != 1:
                raise ValueError('Unknown late route-update variable: ' + declaration)
            body = body.replace(declaration, '')
        marker = '    if (recordOffset == 0) {\n'
        if body.count(marker) != 1:
            raise ValueError('Unknown ranking scope')
        head, tail = body.split(marker)
        for old, new in (('i', 'recordIndex'), ('last', 'active'), ('sorted', 'again'),
                         ('temporary', 'refresh'), ('cursor', 'actor')):
            tail = re.sub(r'\b' + old + r'\b', new, tail)
        yield label + '-late-role-reuse', head + marker + tail


def screen(root, out):
    values = freeze(root, out)
    before = values['conker/src/game/generated_B3020.c'].decode()
    rows = []
    for normal in (False, True):
        baseline, diagnostics = prior.compile_profile(root, out, before, 'screen-before-' + str(normal), normal)
        if diagnostics:
            raise ValueError('Unexpected profile baseline diagnostics')
        for label, body in forms():
            row = measure(root, out, label + ('-normal' if normal else '-no-unroll'), body, baseline, normal)[2]
            rows.append(row)
            print(json.dumps({key: row[key] for key in ('name', 'words', 'frame', 'differences', 'raw_sha256', 'diagnostics', 'neighbors')}), flush=True)
    (out / 'screens.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.screens:
        screen(root, root / BUILD)
    else:
        print(json.dumps(qualify(root, root / BUILD)[2], indent=2))
