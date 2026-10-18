"""Non-installable recovery of the three-argument route-record setup routine."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_route_vector_integration as installed
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools

BUILD = 'conker/build/game-route-record-setup'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_B3020', 'func_150870D0', 0x150870D0, 0xB4580, 160
INPUTS = dict(installed.INPUTS, **installed.AFTER)
INPUTS['conker/asm/CB3D0.s'] = 'dcbd723600e63455ecdcef33eef8929dac0bf75a81ee39d960d044d34a743f06'
ORDERED_PUBLIC_SHA = 'a0c35f94f0c22578199715fddb6fad1dbfe7f555055fbb0ff9ea2974162b0adb'
ROLE_BYTE_CANDIDATE_SHA = '2d704a6832fa19bafad2b9e47674ef74d658e15ef2f11a9e653453e2189a57f8'
RAW_SHA = 'af81faf7636c002ae13313f4948e2ebb51de922efc04d205b12d84346f3b67a6'
BINDINGS = {offset: [(kind, name)] for offset, kind, name in (
    (52, 'R_MIPS_HI16', 'D_800872A0'), (60, 'R_MIPS_LO16', 'D_800872A0'),
    (56, 'R_MIPS_26', 'func_15086D48'), (88, 'R_MIPS_HI16', 'D_800D2350'),
    (92, 'R_MIPS_LO16', 'D_800D2350'), (80, 'R_MIPS_HI16', 'D_800D23A8'),
    (84, 'R_MIPS_LO16', 'D_800D23A8'), (244, 'R_MIPS_26', 'func_150888A8'),
    (264, 'R_MIPS_26', 'func_150888A8'), (340, 'R_MIPS_26', 'func_150888A8'),
    (372, 'R_MIPS_HI16', 'D_800D2398'), (380, 'R_MIPS_LO16', 'D_800D2398'),
    (376, 'R_MIPS_HI16', 'D_800D2399'), (384, 'R_MIPS_LO16', 'D_800D2399'),
    (400, 'R_MIPS_HI16', 'D_800D2394'), (412, 'R_MIPS_LO16', 'D_800D2394'),
    (432, 'R_MIPS_26', 'allocate_memory'), (444, 'R_MIPS_HI16', 'D_800872A0'),
    (448, 'R_MIPS_LO16', 'D_800872A0'), (460, 'R_MIPS_HI16', 'D_8008FD90'),
    (472, 'R_MIPS_LO16', 'D_8008FD90'), (476, 'R_MIPS_HI16', 'D_800872A0'),
    (480, 'R_MIPS_LO16', 'D_800872A0'), (492, 'R_MIPS_26', 'func_15088824'),
    (584, 'R_MIPS_HI16', 'D_800D239A'), (588, 'R_MIPS_LO16', 'D_800D239A'))}
SELECTED = '''/* Build a closed route and allocate its player/extra record table. */
void func_150870D0(s32 key, s32 playerCount, s32 extraCount) {
    extern s8 D_800D23A8;
    extern s8 D_800D239A;
    extern void *allocate_memory(u32, s32, s32, s32);
    extern void func_15088824(u8 *);
    u8 seed[4];
    u8 cursor[3];
    s32 mode;
    s32 limit;
    s32 i;
    s32 total;
    u32 offset;
    u32 length;
    u8 selected;
    u8 candidate;
    u8 next;
    u8 previous;
    u8 after;
    u8 start;
    u8 *table;
    u8 *route;
    u8 *other;
    u8 *record;

    D_800872A0 = 0;
    seed[3] = func_15086D48(key);
    if (seed[3] != 0xFF) {
        selected = 0xFF;
        mode = D_800D23A8;
        table = D_800D2350;
        limit = (mode * 0xFF) & 0xFF;
        route = table + seed[3] * 0x10;
        for (i = 0; i != 5; i++) {
            candidate = route[i + 9];
            if (candidate != 0xFF) {
                other = table + candidate * 0x10;
                if (other[0xE] == 0 &&
                    ((mode == 0 && other[0xF] >= limit) ||
                     (mode != 0 && limit >= other[0xF]))) {
                    limit = other[0xF];
                    selected = candidate;
                }
            }
        }
        if (selected != 0xFF) {
            seed[1] = func_150888A8(seed[3], selected, 0);
            seed[0] = func_150888A8(selected, seed[3], 0);
        }
        if (selected != 0xFF && seed[0] != 0xFF && seed[1] != 0xFF) {
            previous = seed[0];
            after = seed[1];
            length = 0;
            start = seed[3];
            cursor[1] = selected;
            next = after;
            do {
                cursor[0] = cursor[1];
                cursor[1] = next;
                cursor[2] = next;
                next = func_150888A8(cursor[0], cursor[1], 0);
                length++;
            } while (start != cursor[0]);
            cursor[2] = next;
            D_800D2399 = extraCount;
            D_800D2398 = playerCount;
            total = (s32)((u32)playerCount + (u32)extraCount);
            D_800D2394 = 0;
            D_800872A0 = allocate_memory((u32)total * 0x84u, 1, 0, 0);
            if (total > 0) {
                offset = 0;
                i = 0;
                do {
                    record = D_800872A0 + offset;
                    func_15088824(record);
                    record[0x2B] = previous;
                    record[0x2D] = selected;
                    record[0x2E] = after;
                    record[0x2C] = seed[3];
                    if (i < D_800D2398) {
                        record[0x31] = i;
                    }
                    record[0x26] = length;
                    offset += 0x84;
                    record[0x30] = i >= D_8008FD90;
                    i++;
                } while (i != total);
            }
            D_800D239A = 1;
        }
    }
}
'''


def freeze(root, out):
    with patch.object(installed.source.checkpoint, 'INPUTS', INPUTS):
        return installed.source.checkpoint.freeze(root, out)


def recovered_owner(before, body=SELECTED):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_150870D0() {\n    return 0;\n}':
        raise ValueError('Unknown route-record setup placeholder')
    return before[:lo] + body.rstrip() + before[hi:]


def forms():
    yield 'initial', SELECTED
    yield 'signed-length', SELECTED.replace('    u32 length;', '    s32 length;')
    yield 'signed-offset', SELECTED.replace('    u32 offset;', '    s32 offset;')
    yield 'int-selected', SELECTED.replace('    u8 selected;', '    s32 selected;')


def lifetime_forms():
    reuse = SELECTED.replace('    s32 total;\n', '').replace('total', 'playerCount')
    pointer = SELECTED.replace('candidate = route[i + 9];', 'candidate = route[9];').replace(
        '                    selected = candidate;\n                }\n            }\n        }',
        '                    selected = candidate;\n                }\n            }\n            route++;\n        }')
    both = reuse.replace('candidate = route[i + 9];', 'candidate = route[9];').replace(
        '                    selected = candidate;\n                }\n            }\n        }',
        '                    selected = candidate;\n                }\n            }\n            route++;\n        }')
    for label, body in (('reuse-count', reuse), ('pointer-scan', pointer), ('reuse-pointer', both)):
        yield label, body
        direct = body.replace('    s32 mode;\n', '').replace('        mode = D_800D23A8;\n', '').replace(
            'mode * 0xFF', 'D_800D23A8 * 0xFF').replace('mode == 0', 'D_800D23A8 == 0').replace(
            'mode != 0', 'D_800D23A8 != 0')
        yield label + '-global-mode', direct


def layout_forms():
    base = dict(lifetime_forms())['reuse-pointer-global-mode']
    declaration = '''    /* Represent six observed byte homes within the recovered scratch workspace. */
    struct {
        u8 reserved0[4];
        u8 cursor[4];
        u8 seed[4];
        u8 reservedC[20];
    } scratch;'''
    header, statements = base.split('\n\n', 1)
    header = header.replace('    u8 seed[4];\n    u8 cursor[3];', declaration)
    statements = statements.replace('seed[', 'scratch.seed[').replace('cursor[', 'scratch.cursor[')
    body = header + '\n\n' + statements
    yield 'retail-scratch', body
    captured = body.replace('            scratch.seed[0] = func_150888A8(selected, scratch.seed[3], 0);',
        '            scratch.seed[0] = func_150888A8(selected, scratch.seed[3], 0);\n'
        '            previous = scratch.seed[0];\n            after = scratch.seed[1];').replace(
        '        if (selected != 0xFF && scratch.seed[0] != 0xFF && scratch.seed[1] != 0xFF) {\n'
        '            previous = scratch.seed[0];\n            after = scratch.seed[1];',
        '        if (selected != 0xFF && previous != 0xFF && after != 0xFF) {')
    yield 'retail-scratch-captured-seeds', captured
    yield 'retail-scratch-byte-limit', body.replace('    s32 limit;', '    u8 limit;')
    yield 'retail-scratch-int-selected', body.replace('    u8 selected;', '    s32 selected;')


def seed_forms():
    base = dict(layout_forms())['retail-scratch']
    early = base.replace('    scratch.seed[3] = func_15086D48(key);\n    if (scratch.seed[3] != 0xFF) {',
        '    start = func_15086D48(key);\n    scratch.seed[3] = start;\n    if (start != 0xFF) {').replace(
        'route = table + scratch.seed[3] * 0x10;', 'route = table + start * 0x10;')
    yield 'early-start', early
    for mask in (1, 2, 3):
        body = early
        for bit, name in ((1, 'previous'), (2, 'after')):
            if mask & bit:
                body = body.replace('    u8 ' + name + ';', '    s32 ' + name + ';')
        yield 'early-start-word-seeds-%d' % mask, body
    yield 'early-start-comma-gate', early.replace(
        '        if (selected != 0xFF && scratch.seed[0] != 0xFF && scratch.seed[1] != 0xFF) {\n'
        '            previous = scratch.seed[0];\n            after = scratch.seed[1];',
        '        if (selected != 0xFF &&\n'
        '            (previous = scratch.seed[0], after = scratch.seed[1], previous != 0xFF) && after != 0xFF) {')


def seed_store_forms():
    base = dict(seed_forms())['early-start-word-seeds-3']
    old = ('            scratch.seed[1] = func_150888A8(scratch.seed[3], selected, 0);\n'
           '            scratch.seed[0] = func_150888A8(selected, scratch.seed[3], 0);')
    for label, new in (
        ('delayed-first-seed',
         '            after = (u8)func_150888A8(scratch.seed[3], selected, 0);\n'
         '            scratch.seed[0] = func_150888A8(selected, scratch.seed[3], 0);\n'
         '            scratch.seed[1] = after;'),
        ('delayed-both-seeds',
         '            after = (u8)func_150888A8(scratch.seed[3], selected, 0);\n'
         '            previous = (u8)func_150888A8(selected, scratch.seed[3], 0);\n'
         '            scratch.seed[1] = after;\n            scratch.seed[0] = previous;')):
        if base.count(old) != 1:
            raise ValueError('Unknown first two selector calls')
        yield label, base.replace(old, new)


def ordered_forms():
    candidates = [('ordered-public', dict(seed_forms())['early-start-word-seeds-3']),
                  *[(name + '-ordered', body) for name, body in seed_store_forms()]]
    for name, body in candidates:
        body = body.replace('    s32 i;', '    s32 humanLimit;\n    s32 i;').replace(
            '                    record[0x2B] = previous;',
            '                    record[0x2B] = previous;\n                    start = scratch.seed[3];').replace(
            'record[0x2C] = scratch.seed[3];', 'record[0x2C] = start;').replace(
            '                    record[0x26] = length;',
            '                    humanLimit = D_8008FD90;\n                    record[0x26] = length;').replace(
            'record[0x30] = i >= D_8008FD90;', 'record[0x30] = i >= humanLimit;')
        yield name, body


def role_forms():
    base = dict(ordered_forms())['ordered-public']
    body = base.replace('    u8 next;\n', '').replace('next', 'i').replace(
        'i = func_150888A8(scratch.cursor[0], scratch.cursor[1], 0);',
        'i = (u8)func_150888A8(scratch.cursor[0], scratch.cursor[1], 0);')
    yield 'reuse-index-as-next', body
    yield 'reuse-index-explicit-byte', body.replace('            i = after;', '            i = (u8)after;')
    for label, form in (('start-word', base), ('reuse-index-start-word', body)):
        yield label, form.replace('    u8 start;', '    s32 start;').replace(
            'start = func_15086D48(key);', 'start = (u8)func_15086D48(key);')


def capture_forms():
    base = dict(role_forms())['reuse-index-as-next']
    yield 'role-byte-limit', base.replace('    s32 limit;', '    u8 limit;')
    yield 'role-word-candidate', base.replace('    u8 candidate;', '    s32 candidate;')
    for label, form in ordered_forms():
        if label == 'ordered-public':
            continue
        body = form.replace('    u8 next;\n', '').replace('next', 'i').replace(
            'i = func_150888A8(scratch.cursor[0], scratch.cursor[1], 0);',
            'i = (u8)func_150888A8(scratch.cursor[0], scratch.cursor[1], 0);')
        yield label + '-reuse-index', body
        yield label + '-reuse-index-byte-limit', body.replace('    s32 limit;', '    u8 limit;')


def selected():
    return dict(role_forms())['reuse-index-as-next'].replace('    u8 candidate;', '    s32 candidate;')


def checked(obj):
    text, functions, relocations = parse_object(obj)
    function = functions[FUNCTION]
    raw = text[function['value']:function['value'] + function['size']]
    bindings = {at - function['value']: entries for at, entries in relocations.items()
                if function['value'] <= at < function['value'] + function['size']}
    if len(raw) != 640 or hashlib.sha256(raw).hexdigest() != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Unknown complete route-record model or bindings')
    return raw, bindings


def qualify(root, out):
    values = freeze(root, out)
    baseline, diagnostics = installed.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    obj, words, row = measure(root, out, 'qualified', selected(), baseline)
    checked(obj)
    if diagnostics or row['diagnostics'] or (row['words'], row['frame'], row['differences']) != (160, 96, 43):
        raise ValueError('Changed route-record model qualification')
    row['recovered_scratch_footprint_not_original_C_type_claim'] = True
    row['installation_permitted'] = False
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def measure(root, out, name='initial', body=SELECTED, baseline=None):
    values = freeze(root, out)
    obj, diagnostics = installed.prior.compile_profile(root, out,
        recovered_owner(values['conker/src/game/generated_B3020.c'].decode(), body), name)
    image, functions = installed.prior.link_owner(root, out, obj, OWNER)
    function = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (function['size'] // 4), image, function['value']))
    text, definitions, relocations = parse_object(obj)
    definition = definitions[FUNCTION]
    raw = text[definition['value']:definition['value'] + definition['size']]
    bindings = {at - definition['value']: value for at, value in relocations.items()
                if definition['value'] <= at < definition['value'] + definition['size']}
    truth = struct.unpack_from('>160I', values['conker/conker.us.bin'], ROM)
    row = dict(name=name, words=len(words), frame=(-words[0]) & 65535,
               differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
               raw_sha256=hashlib.sha256(raw).hexdigest(), bindings=bindings, diagnostics=diagnostics,
               saved=[(w >> 16 & 31, w & 65535) for w in words if w >> 26 == 43 and w >> 21 & 31 == 29],
               installed=False, matching_credit=0)
    if baseline is not None:
        row['neighbors'] = installed.source.model.same_functions(baseline, obj, (FUNCTION,))
        if row['neighbors'] != 72 or normalized_pools(baseline) != normalized_pools(obj):
            raise ValueError('Route-record candidate changed another owner function or pool')
    (out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms', action='store_true')
    parser.add_argument('--lifetimes', action='store_true')
    parser.add_argument('--layouts', action='store_true')
    parser.add_argument('--seeds', action='store_true')
    parser.add_argument('--seed-stores', action='store_true')
    parser.add_argument('--ordered', action='store_true')
    parser.add_argument('--roles', action='store_true')
    parser.add_argument('--captures', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    if args.qualify:
        print(json.dumps(qualify(root, out)[2], indent=2))
        raise SystemExit(0)
    values = freeze(root, out)
    baseline, diagnostics = installed.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected setup baseline diagnostics')
    candidates = capture_forms() if args.captures else role_forms() if args.roles else ordered_forms() if args.ordered else seed_store_forms() if args.seed_stores else seed_forms() if args.seeds else layout_forms() if args.layouts else lifetime_forms() if args.lifetimes else forms() if args.forms else [('initial', SELECTED)]
    for name, body in candidates:
        row = measure(root, out, name, body, baseline)[2]
        print(json.dumps({key: row[key] for key in ('name', 'words', 'frame', 'differences', 'saved', 'diagnostics', 'neighbors')}), flush=True)
