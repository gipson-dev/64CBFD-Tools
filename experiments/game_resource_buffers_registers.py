"""Screen complete buffer preparation selector and copy-destination lifetimes."""
import argparse
import csv
import io
import itertools
import json
from pathlib import Path
from tools.experiments import game_resource_buffers_matching as previous

BASE = previous.QUALIFIED


def parent_mode(body, before_pair=False):
    body = body.replace('actor[0x65]', 'mode')
    gate = '    pair = actor + channel * 8;' if before_pair else '    if (mode != 0) {'
    assert body.count(gate) == 1
    return body.replace(gate, '    mode = actor[0x65];\n' + gate)


def loop_destination(body, variable):
    old = '''                        config = *(u8 **)(cursor + 0x28C);
                        if (config != NULL) {
                            bcopy(D_800D19A0[identity], config, size);'''
    new = old.replace('config', variable)
    assert body.count(old) == 1
    if variable == 'destination':
        new = '                        u8 *destination;\n' + new
    return body.replace(old, new)


def address_forms(body):
    for word in (False, True):
        shaped = body.replace('u8 *actor,', 'u32 actor,' if word else 'void *actor,')
        shaped = shaped.replace('actor[0x65]', '((u8 *)actor)[0x65]')
        if word:
            shaped = shaped.replace('pair = actor + channel * 8;', 'pair = (u8 *)(actor + channel * 8);').replace(
                'cursor = actor + (channel << 3);', 'cursor = (u8 *)(actor + (channel << 3));')
        else:
            shaped = shaped.replace('actor +', '(u8 *)actor +')
        yield 'word' if word else 'void', shaped


def narrowed_candidates():
    mode = dict(candidates())['reuse-mode']
    for name, body in (('base', BASE), ('first', loop_destination(BASE, 'first')), ('mode', mode)):
        for kind, shaped in address_forms(body):
            yield 'address-' + name + '-' + kind, shaped
        for expression in ('(u8 *)(channel * 8 + (u32)actor)', '(u8 *)((channel << 3) + (u32)actor)'):
            shaped = body.replace('pair = actor + channel * 8;', 'pair = ' + expression + ';')
            yield 'order-' + name + '-' + str(len(expression)), shaped
    for decode in ('first', 'cursor'):
        body = previous.separate_source(BASE).replace('    u8 *config;\n', '')
        opening, rest = body.split('    first = *(u8 **)(pair + 0x28C);', 1)
        opening = opening.replace('config', decode).replace('].' + decode, '].config')
        rest = rest.replace('config = allocate_memory', 'shared = allocate_memory').replace(
            '= config;', '= shared;').replace('if (config == NULL)', 'if (shared == NULL)')
        old = '''                        config = *(u8 **)(cursor + 0x28C);
                        if (config != NULL) {
                            bcopy(D_800D19A0[identity], config, size);'''
        new = '''                        mode = (s32)*(u8 **)(cursor + 0x28C);
                        if (mode != 0) {
                            bcopy(D_800D19A0[identity], (void *)mode, size);'''
        assert rest.count(old) == 1
        yield 'compact-' + decode + '-shared-mode', opening + '    first = *(u8 **)(pair + 0x28C);' + rest.replace(old, new)


def expression_candidates():
    loop = '''                        config = *(u8 **)(cursor + 0x28C);
                        if (config != NULL) {
                            bcopy(D_800D19A0[identity], config, size);'''
    inline = '''                        if (*(u8 **)(cursor + 0x28C) != NULL) {
                            bcopy(D_800D19A0[identity], *(u8 **)(cursor + 0x28C), size);'''
    for opening in (False, True):
        body = BASE.replace(loop, inline)
        if opening:
            old = '''                    first = *(u8 **)(pair + 0x28C);
                    if (first != NULL) {
                        bcopy(D_800D19A0[identity], first, size);'''
            new = '''                    if (*(u8 **)(pair + 0x28C) != NULL) {
                        bcopy(D_800D19A0[identity], *(u8 **)(pair + 0x28C), size);'''
            assert body.count(old) == 1
            body = body.replace(old, new)
        yield 'expression-%d' % opening, body


def declaration_candidates():
    body = dict(expression_candidates())['expression-0']
    original = '''    u8 *config;
    s32 mode;
    s32 identity;
    u8 *pair;
    u8 *first;
    s32 failed;
    s32 size;
    s32 offset;
    u8 *cursor;'''
    rows = original.splitlines()
    for order in itertools.permutations((0, 1, 4, 8)):
        changed = rows.copy()
        for slot, source in zip((0, 1, 4, 8), order):
            changed[slot] = rows[source]
        yield 'declarations-' + ''.join(map(str, order)), body.replace(original, '\n'.join(changed))
    for mode in ('u32', 'u8', 's16'):
        yield 'type-mode-' + mode, body.replace('    s32 mode;', '    ' + mode + ' mode;')
    yield 'type-config-void', body.replace('    u8 *config;', '    void *config;').replace(
        'mode = config[0x10]', 'mode = ((u8 *)config)[0x10]')


def integer_candidates():
    for integer in ('first', 'config'):
        body = BASE.replace('    u8 *' + integer + ';', '    s32 ' + integer + ';')
        body = body.replace(integer + ' = *(u8 **)', integer + ' = *(s32 *)')
        body = body.replace(integer + ' == NULL', integer + ' == 0').replace(integer + ' != NULL', integer + ' != 0')
        body = body.replace('= ' + integer + ';', '= (u8 *)' + integer + ';')
        body = body.replace(', ' + integer + ', size)', ', (void *)' + integer + ', size)')
        if integer == 'first':
            body = body.replace('first == config', 'first == (s32)config').replace(
                'first != D_800D19A0[identity]', 'first != (s32)D_800D19A0[identity]').replace(
                'func_10004074(first)', 'func_10004074((void *)first)')
        else:
            body = body.replace('config = D_800CC0E8', 'config = (s32)D_800CC0E8').replace(
                'config = D_800D19A0', 'config = (s32)D_800D19A0').replace(
                'config = allocate_memory', 'config = (s32)allocate_memory').replace(
                'mode = config[0x10]', 'mode = ((u8 *)config)[0x10]').replace(
                'first == config', 'first == (u8 *)config')
        yield 'integer-' + integer, body


OFFSETS = (0x20,0x24,0x28,0x2C,0x68,0x6C,0x70,0x78,0x84,0x88,0x90,
    0x9C,0xB0,0xBC,0xC8,0xCC,0xDC,0xEC,0xF0,0x10C,0x11C,0x19C,0x1A0,
    0x1C0,0x1C8,0x1CC,0x290,0x298,0x29C)
COPY_SCHEDULE = {0x290,0x298,0x29C}


def guard_text(raw, retail, relocations):
    differences = tuple(i*4 for i,(a,b) in enumerate(zip(raw,retail)) if a != b)
    assert len(raw) == len(retail) == 194 and differences == OFFSETS
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    for offset in OFFSETS:
        before, after = raw[offset//4], retail[offset//4]
        assert not relocations.get(offset)
        if offset not in COPY_SCHEDULE:
            assert before >> 26 == after >> 26
            fields = (31<<21) | (31<<16) | ((31<<11) if before >> 26 == 0 else 0)
            assert before & ~fields == after & ~fields
            note = 'Normalize closed buffer preparation register lifetimes'
        else:
            note = 'Normalize buffer copy destination register and branch-delay schedule'
        writer.writerow(('generated_AEB40','func_15084044','0x%X'%offset,
            '0x%08X'%before,'0x%08X'%after,'-','-',note,'','','false'))
    assert tuple(raw[i//4] for i in (0x290,0x294,0x298,0x29C)) == (
        0x8E05028C,0x02203025,0x50A00006,0x8E6F0000)
    assert tuple(retail[i//4] for i in (0x290,0x294,0x298,0x29C)) == (
        0x8E02028C,0x02203025,0x10400005,0x00402825)
    return stream.getvalue()


def candidates():
    yield 'banked', BASE
    for placement in (False, True):
        parent = parent_mode(BASE, placement)
        yield 'parent-mode-%d' % placement, parent
        for variable in ('first', 'actor', 'destination'):
            yield 'parent-mode-%d-copy-%s' % (placement, variable), loop_destination(parent, variable)
    for variable in ('first', 'actor', 'destination'):
        yield 'copy-' + variable, loop_destination(BASE, variable)
    for copy in ('config', 'first', 'destination'):
        body = previous.separate_source(BASE)
        if copy != 'config':
            body = loop_destination(body, copy)
        body = body.replace('    s32 offset;\n', '').replace('offset', 'channel').replace(
            '''        channel = 0;
        cursor = actor + (channel << 3);
        for (;''', '''        cursor = actor + (channel << 3);
        for (channel = 0;''')
        yield 'shared-channel-copy-' + copy, body
    for variable in ('mode', 'size'):
        body = BASE
        if variable == 'mode':
            old = '''                        config = *(u8 **)(cursor + 0x28C);
                        if (config != NULL) {
                            bcopy(D_800D19A0[identity], config, size);'''
            new = '''                        mode = (s32)*(u8 **)(cursor + 0x28C);
                        if (mode != 0) {
                            bcopy(D_800D19A0[identity], (void *)mode, size);'''
        else:
            old = '    config = D_800D19A0[identity];\n    if (config == NULL)'
            new = '    size = (s32)D_800D19A0[identity];\n    if (size == 0)'
            body = body.replace('*(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = config;',
                '*(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = (u8 *)size;').replace(
                'first == config', 'first == (u8 *)size')
        assert body.count(old) == 1
        yield 'reuse-' + variable, body.replace(old, new)
    for decode in ('first', 'cursor'):
        for allocation in ('first', 'shared'):
            for destination in ('first', 'shared'):
                body = previous.separate_source(BASE).replace('    u8 *config;\n', '')
                opening, rest = body.split('    first = *(u8 **)(pair + 0x28C);', 1)
                opening = opening.replace('config', decode).replace('].' + decode, '].config')
                rest = rest.replace('config = allocate_memory', allocation + ' = allocate_memory').replace(
                    '= config;', '= ' + allocation + ';').replace(
                    'if (config == NULL)', 'if (' + allocation + ' == NULL)')
                old = '''                        config = *(u8 **)(cursor + 0x28C);
                        if (config != NULL) {
                            bcopy(D_800D19A0[identity], config, size);'''
                assert rest.count(old) == 1
                rest = rest.replace(old, old.replace('config', destination))
                yield 'compact-%s-%s-%s' % (decode, allocation, destination), opening + '    first = *(u8 **)(pair + 0x28C);' + rest
    for copy in ('first', 'config'):
        body = previous.separate_source(BASE)
        if copy != 'config':
            body = loop_destination(body, copy)
        body = body.replace('    u8 *cursor;\n', '').replace('cursor', 'actor')
        yield 'compact-actor-' + copy, body


QUALIFIED = dict(candidates())['reuse-mode']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--extra', action='store_true')
    parser.add_argument('--narrowed', action='store_true')
    parser.add_argument('--expressions', action='store_true')
    parser.add_argument('--declarations', action='store_true')
    parser.add_argument('--integers', action='store_true')
    parser.add_argument('--guards', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-resource-buffers-registers'
    if args.guards:
        import struct
        from tools.experiments import game_resource_buffers_candidates as recovery
        meta, raw = previous.compile_candidate(root,out,'qualified',QUALIFIED)
        retail = struct.unpack_from('>194I',(root/'conker/conker.us.bin').read_bytes(),recovery.ROM)
        print(guard_text(raw,retail,meta['relocations']),end='')
        return
    records = []
    forms = integer_candidates() if args.integers else declaration_candidates() if args.declarations else expression_candidates() if args.expressions else narrowed_candidates() if args.narrowed else candidates()
    for name, body in forms:
        if args.extra and not name.startswith(('shared-', 'reuse-', 'compact-')):
            continue
        for profile in (('o2g3', 'o2', 'o1g3') if args.profiles else ('o2g3',)):
            meta, _ = previous.compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
