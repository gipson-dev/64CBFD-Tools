"""Recover six halfword-kind/float-table packets without the reference's width errors."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_six_piece_debris_match as previous
from tools.tests import six_piece_debris_match_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-table-debris'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19E040', 'func_15170F4C', 0x15170F4C, 0x19E3FC, 158
LOOKUP, RANDOM, SUBMIT, TABLE = 0x1518C900, 0x150ADA68, 0x15168BE4, 0x800A6ED8
PATHS = dict(previous.PATHS, float_rng_owner='conker/src/game_DAE50.c',
    float_rng_original='conker/asm/nonmatchings/game_DAE50/func_150ADA68.s',
    table_debris_caller='conker/asm/142560.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    float_rng_owner='ca6779c0fd3e2cd16b2f8ce758865df59310da359987cce07781cc5005733729',
    float_rng_original='5a6e99909e32a7a447765007d4194689565251d4f5d8723adb62a7e141c71bad',
    table_debris_caller='ca734f7ffd435f954360ac879e7762e8adbb56cc72ce60eadebcac3030d1121f')
build = previous.build

DECLARATIONS = '''typedef struct TableDebris19E040 {
    u16 kind;
    u16 reserved02;
    f32 offset[3];
    f32 rotation[3];
} TableDebris19E040;

extern TableDebris19E040 D_800A6ED8[6];
extern f32 D_800A6F98, D_800A6F9C, D_800A6FA0;
extern f32 D_800A6FA4, D_800A6FA8, D_800A6FAC;
f32 func_150ADA68(void);

'''

INITIAL = '''/* Emit six live-table debris packets; keep reserved bytes untouched. */
void func_15170F4C(u8 *actor, u8 flags, s32 context) {
    DebrisPacket19E040 packet;
    f32 originX;
    f32 originY;
    f32 originZ;
    TableDebris19E040 *entry;
    f32 horizontal;
    f32 vertical;
    f32 rotationScale;
    s32 asset;
    s32 index;

    packet.control5C = 2;
    packet.control5D = 1;
    packet.variant = 6;
    packet.duration = 0;
    originX = (f32)*(s16 *)(actor + 0x10);
    originY = (f32)*(s16 *)(actor + 0x12);
    originZ = (f32)*(s16 *)(actor + 0x14);
    packet.rotation[0] = 0.0f;
    packet.rotation[1] = 0.0f;
    packet.rotation[2] = 0.0f;
    packet.scale[0] = 2.0f;
    packet.scale[1] = 2.0f;
    packet.scale[2] = 2.0f;
    packet.lifetime = 60;
    packet.mode = 2;
    packet.alpha = 255;
    packet.zero56 = 0;
    packet.zero57 = 0;
    packet.zero58 = 0;
    packet.coefficient[0] = D_800A6F98;
    packet.coefficient[1] = D_800A6F9C;
    packet.coefficient[2] = D_800A6FA0;
    rotationScale = D_800A6FA4;
    vertical = D_800A6FA8;
    horizontal = D_800A6FAC;
    index = 0;
    entry = D_800A6ED8;
    do {
        asset = func_1518C900(entry->kind);
        packet.kind = entry->kind;
        packet.position[0] = entry->offset[0] + originX;
        packet.position[1] = entry->offset[1] + originY;
        packet.position[2] = entry->offset[2] + originZ;
        packet.velocity[0] = entry->offset[0] * horizontal;
        packet.velocity[1] = fabsf(entry->offset[1]) * vertical;
        packet.velocity[2] = entry->offset[2] * horizontal;
        packet.rotation[0] = entry->rotation[0];
        packet.rotation[1] = entry->rotation[1];
        packet.rotation[2] = entry->rotation[2];
        packet.spin[0] = packet.rotation[0] * rotationScale;
        packet.spin[1] = func_150ADA68() * 4.0f - 2.0f;
        packet.spin[2] = func_150ADA68() * 10.0f - 5.0f;
        packet.asset = asset;
        func_15168BE4(&packet, flags, context);
        index += 1;
        entry += 1;
    } while (index < 6);
    actor[0x6E] = 1;
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed table-debris predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed table-debris manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed table-debris fixture: ' + key)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15170F4C() {\n    return 0;\n}':
        raise ValueError('Unknown table-debris placeholder')
    result = before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]
    result = result.replace('zero5C', 'control5C').replace('zero5D', 'control5D')
    return result.replace('extern s32 D_800BE9F0;', DECLARATIONS + 'extern s32 D_800BE9F0;', 1)


def measure(root, out, label='selected', selected=None, flags=('-O2', '-g3')):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-edge_wrapper_owner').read_text(), selected), label, flags=flags)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM))
    pools, raw = sections(obj), parse_object(obj)
    row = dict(label=label, flags=flags, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, pool_bytes=sum(len(pools.get(n, (0, b''))[1]) for n in ('.rodata', '.data')),
        raw_sha256=hashlib.sha256(raw[0][f['value']:f['value'] + f['size']]).hexdigest(),
        stack_pointers=[(i * 4, w >> 16 & 31, w & 65535) for i, w in enumerate(words)
            if w >> 26 == 9 and w >> 21 & 31 == 29 and w >> 16 & 31 != 29],
        relocations={at - f['value']: rows for at, rows in raw[2].items() if f['value'] <= at < f['value'] + f['size']},
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def forms():
    yield 'initial', INITIAL
    early = INITIAL.replace('    rotationScale = D_800A6FA4;\n    vertical = D_800A6FA8;\n    horizontal = D_800A6FAC;\n', '')
    early = early.replace('    packet.rotation[0] = 0.0f;',
        '    rotationScale = D_800A6FA4;\n    vertical = D_800A6FA8;\n    horizontal = D_800A6FAC;\n    packet.rotation[0] = 0.0f;', 1)
    yield 'early-saved-coefficients', early
    for name, body in (('initial', INITIAL), ('early', early)):
        yield name + '-packet-after-origin', body.replace('    DebrisPacket19E040 packet;\n', '').replace(
            '    f32 originX;', '    f32 originX;\n    DebrisPacket19E040 packet;', 1)
        yield name + '-word-flags', body.replace('u8 *actor, u8 flags, s32 context)', 'u8 *actor, s32 flags, s32 context)')


def profile_screens(root, out):
    from tools.experiments import game_record_constructor_candidates as compiler
    freeze(root, out)
    prefix = recovered_owner((out / 'before-edge_wrapper_owner').read_text()).split('extern s32 D_800BE9F0;', 1)[0]
    prefix = prefix.replace('#include <ultra64.h>\n', '')
    profiles = dict(O2=('-O2', '-g3'), O1=('-O1',), no_unroll=('-O2', '-g3', '-Wo,-loopunroll,0'))
    symbols = {'D_%08X' % at: at for at in (TABLE, *range(0x800A6F98, 0x800A6FB0, 4))}
    symbols.update(func_1518C900=LOOKUP, func_150ADA68=RANDOM, func_15168BE4=SUBMIT)
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=prefix, DECLARATIONS='', SYMBOLS=symbols, PROFILES=profiles):
        for name in profiles:
            row, words = compiler.compile_candidate(root, out, 'profile-' + name, INITIAL, name)
            row['actual_frame'] = next((-(w & 65535)) & 65535 for w in words if w >> 16 == 0x27BD and w & 32768)
            print(json.dumps(row), flush=True)


def lifetime_forms():
    origin = INITIAL.replace('    f32 originX;\n    f32 originY;\n    f32 originZ;', '    f32 origin[3];')
    for index, old in enumerate(('originX', 'originY', 'originZ')):
        origin = origin.replace(old, 'origin[%d]' % index)
    count = INITIAL.replace('    s32 index;', '    s32 index;\n    s32 count;').replace(
        '    index = 0;', '    count = 6;\n    index = 0;').replace('index < 6', 'index < count')
    origin_count = origin.replace('    s32 index;', '    s32 index;\n    s32 count;').replace(
        '    index = 0;', '    count = 6;\n    index = 0;').replace('index < 6', 'index < count')
    for name, body in (('origin-array', origin), ('named-count', count), ('array-count', origin_count)):
        yield name, body
        yield name + '-named-rng', body.replace('    s32 asset;', '    f32 randomValue;\n    s32 asset;').replace(
            '        packet.spin[1] = func_150ADA68() * 4.0f - 2.0f;',
            '        randomValue = func_150ADA68() * 4.0f;\n        packet.spin[1] = randomValue - 2.0f;')
    yield 'first-rng-double-literal', INITIAL.replace('* 4.0f - 2.0f', '* 4.0 - 2.0')


def ordered_forms():
    order = ('packet.control5C', 'packet.control5D', 'packet.variant', 'packet.duration',
        'entry', 'originX', 'index', 'originY', 'rotationScale', 'vertical',
        'packet.rotation[0]', 'packet.rotation[1]', 'originZ', 'packet.rotation[2]',
        'packet.scale[0]', 'packet.scale[1]', 'packet.scale[2]', 'packet.lifetime',
        'packet.mode', 'packet.alpha', 'packet.zero56', 'packet.zero57', 'packet.zero58',
        'horizontal', 'packet.coefficient[0]', 'packet.coefficient[1]', 'packet.coefficient[2]')
    lo, hi = INITIAL.index('    packet.control5C ='), INITIAL.index('    do {')
    statements = {line.strip().split(' = ')[0]: line for line in INITIAL[lo:hi].splitlines()}
    if set(statements) != set(order):
        raise ValueError('Unexpected table-debris initial statements')
    ordered = INITIAL[:lo] + '\n'.join(statements[name] for name in order) + '\n' + INITIAL[hi:]
    for name, initial in (('original-order', ordered), ('chain-scale', INITIAL.replace(
            '    packet.scale[0] = 2.0f;\n    packet.scale[1] = 2.0f;\n    packet.scale[2] = 2.0f;',
            '    packet.scale[0] = packet.scale[1] = packet.scale[2] = 2.0f;'))):
        for count in (False, True):
            body = initial if not count else initial.replace('    s32 index;', '    s32 index;\n    s32 count;').replace(
                '    index = 0;', '    count = 6;\n    index = 0;').replace('index < 6', 'index < count')
            yield name + ('-count' if count else ''), body
            yield name + ('-count' if count else '') + '-packet-after-origin', body.replace(
                '    DebrisPacket19E040 packet;\n', '').replace('    f32 originX;', '    f32 originX;\n    DebrisPacket19E040 packet;')
    yield 'initial-two-local', INITIAL.replace('    f32 horizontal;', '    f32 horizontal;\n    f32 two;').replace(
        '    packet.control5C =', '    two = 2.0f;\n    packet.control5C =', 1).replace('= 2.0f;', '= two;').replace(
        '    two = two;', '    two = 2.0f;').replace('* 4.0f - 2.0f', '* 4.0f - two')


def shape_forms():
    initial = dict(ordered_forms())['chain-scale-count']
    reversed_scale = initial.replace('packet.scale[0] = packet.scale[1] = packet.scale[2] = 2.0f;',
        'packet.scale[2] = packet.scale[1] = packet.scale[0] = 2.0f;')
    yield 'reverse-chain-count', reversed_scale
    yield 'reverse-chain-count-packet-after-origin', reversed_scale.replace('    DebrisPacket19E040 packet;\n', '').replace(
        '    f32 originX;', '    f32 originX;\n    DebrisPacket19E040 packet;')
    for shape in ('array', 'struct'):
        fields = ('origin[0]', 'origin[1]', 'origin[2]') if shape == 'array' else ('origin.x', 'origin.y', 'origin.z')
        body = initial.replace('    f32 originX;\n    f32 originY;\n    f32 originZ;',
            '    f32 origin[3];' if shape == 'array' else '    struct { f32 x, y, z; } origin;')
        for old, new in zip(('originX', 'originY', 'originZ'), fields):
            body = body.replace(old, new)
        yield 'chain-count-' + shape, body
        yield 'chain-count-' + shape + '-first', body.replace('    DebrisPacket19E040 packet;\n', '').replace(
            '    TableDebris19E040 *entry;', '    DebrisPacket19E040 packet;\n    TableDebris19E040 *entry;')
    for local in ('horizontal', 'vertical', 'rotationScale'):
        body = initial.replace('    f32 ' + local + ';\n', '')
        body = body.replace('    DebrisPacket19E040 packet;', '    f32 ' + local + ';\n    DebrisPacket19E040 packet;')
        yield 'chain-count-first-' + local, body
    for names in (('vertical', 'rotationScale'), ('horizontal', 'vertical', 'rotationScale')):
        body = initial
        for name in names:
            body = body.replace('    f32 ' + name + ';', '    register f32 ' + name + ';')
        yield 'register-' + '-'.join(names), body
    for name in ('originX', 'originY', 'originZ'):
        body = initial.replace('    f32 ' + name + ';\n', '').replace(
            '    s32 index;', '    f32 ' + name + ';\n    s32 index;')
        yield 'late-origin-' + name, body
    for name, body in (('initial', INITIAL), ('chain-count', initial)):
        second = body.replace('    s32 asset;', '    f32 randomValue;\n    s32 asset;').replace(
            '        packet.spin[2] = func_150ADA68() * 10.0f - 5.0f;\n        packet.asset = asset;',
            '        randomValue = func_150ADA68() * 10.0f;\n        packet.asset = asset;\n        packet.spin[2] = randomValue - 5.0f;')
        yield name + '-named-second-rng', second
        yield name + '-named-second-first-local', second.replace('    f32 randomValue;\n', '').replace(
            '    DebrisPacket19E040 packet;', '    f32 randomValue;\n    DebrisPacket19E040 packet;')


SELECTED = dict(ordered_forms())['chain-scale-count']


def qualify(root, out):
    result = measure(root, out)
    row = result[2]
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['pool_bytes']) != (158, 0xE8, 0, '', 0):
        raise ValueError('Table debris is not a direct match; installation rejected')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--lifetimes', action='store_true')
    parser.add_argument('--orders', action='store_true')
    parser.add_argument('--shapes', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.profiles:
        profile_screens(root, root / BUILD)
        raise SystemExit
    for name, body in (shape_forms() if args.shapes else ordered_forms() if args.orders else lifetime_forms() if args.lifetimes else forms() if args.screen else (('selected', SELECTED),)):
        _, _, row = measure(root, root / BUILD, name, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame', 'differences', 'stack_pointers', 'diagnostics', 'raw_sha256')}), flush=True)
