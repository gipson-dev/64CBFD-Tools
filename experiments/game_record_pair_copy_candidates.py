"""Recover the complete identity-gated allocated signed record-pair copy."""
import argparse
import csv
import hashlib
import io
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x1503D804, 0x6ACB4, 96
FUNCTION, SOURCE = 'func_1503D804', 'conker/src/game/generated_6A3D0.c'
ORIGINAL = 's32 func_1503D804() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 *D_800C6360[];
extern u8 *D_800D19A0[];
extern u32 D_800C4020[];
s32 allocate_memory(s32, s32, s32, s32);
'''
SYMBOLS = dict(D_800C6360=0x800C6360, D_800D19A0=0x800D19A0,
    D_800C4020=0x800C4020, allocate_memory=0x10003C40)
PROFILES = dict(compiler.PROFILES, retail=('-O2', '-g3'),
    owner=('-O2', '-g3', '-Wo,-loopunroll,0'))
SELECTED = '''s32 func_1503D804(s32 identity) {
    s32 count;
    s32 kind = -1;
    u8 **slot;
    u8 *base;
    s16 *output;
    s32 index;

    if (identity == 0x24) {
        count = 94;
        kind = 0;
    } else {
        count = 0;
    }
    if (count == 0) {
        return 0;
    }
    slot = &D_800C6360[identity];
    if (*slot != NULL) {
        return 0;
    }
    base = D_800D19A0[identity];
    if (kind != -1) {
        base += ((u32 *)D_800C4020[identity])[kind] * 16;
    }
    output = (void *)allocate_memory(count * 4, 1, 0, 2);
    *slot = (u8 *)output;
    if (output == NULL) {
        return 1;
    }
    output = (s16 *)*slot;
    for (index = 0; index < count; index++) {
        output[index * 2] = *(s16 *)(base + index * 16 + 8);
        output[index * 2 + 1] = *(s16 *)(base + index * 16 + 10);
    }
    return 0;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'kind-in-else', SELECTED.replace('s32 kind = -1;', 's32 kind;').replace(
        '        count = 0;', '        count = 0;\n        kind = -1;')
    yield 'slot-before-kind', SELECTED.replace('    s32 kind = -1;\n    u8 **slot;',
        '    u8 **slot;\n    s32 kind = -1;')
    yield 'base-before-slot', SELECTED.replace('    u8 **slot;\n    u8 *base;',
        '    u8 *base;\n    u8 **slot;')
    yield 'index-before-output', SELECTED.replace('    s16 *output;\n    s32 index;',
        '    s32 index;\n    s16 *output;')
    yield 'count-last', SELECTED.replace('    s32 count;\n', '').replace(
        '    s32 index;', '    s32 index;\n    s32 count;')
    yield 'typed-slot', SELECTED.replace('u8 **slot;', 's16 **slot;').replace(
        'slot = &D_800C6360[identity];', 'slot = (s16 **)&D_800C6360[identity];').replace(
        '*slot = (u8 *)output;', '*slot = output;').replace('output = (s16 *)*slot;', 'output = *slot;')
    yield 'direct-global-publication', SELECTED.replace('    *slot = (u8 *)output;',
        '    D_800C6360[identity] = (u8 *)output;')
    yield 'signed-record-index', SELECTED.replace('((u32 *)D_800C4020[identity])',
        '((s32 *)D_800C4020[identity])')
    byte_output = SELECTED.replace('s16 *output;', 'u8 *output;').replace(
        'output = (s16 *)*slot;', 'output = *slot;').replace(
        'output[index * 2]', '*(s16 *)(output + index * 4)').replace(
        'output[index * 2 + 1]', '*(s16 *)(output + index * 4 + 2)')
    yield 'byte-output-index', byte_output
    for name, body in (('half', SELECTED), ('byte', byte_output)):
        expression = body.replace('    output = (void *)allocate_memory(count * 4, 1, 0, 2);\n    *slot = (u8 *)output;\n    if (output == NULL) {',
            '    if ((*slot = (u8 *)allocate_memory(count * 4, 1, 0, 2)) == NULL) {')
        yield name+'-allocation-expression', expression
        yield name+'-allocation-expression-source-commute', expression.replace(
            'base + index * 16', 'index * 16 + base')
        yield name+'-slot-check', body.replace('    output = (void *)allocate_memory(count * 4, 1, 0, 2);\n    *slot = (u8 *)output;\n    if (output == NULL) {',
            '    *slot = (u8 *)allocate_memory(count * 4, 1, 0, 2);\n    if (*slot == NULL) {')
        direct = expression.replace('    u8 **slot;\n', '').replace(
            '    slot = &D_800C6360[identity];\n', '').replace('*slot', 'D_800C6360[identity]')
        yield name+'-global-expression', direct
        yield name+'-global-expression-commute', direct.replace('base + index * 16', 'index * 16 + base')
        yield name+'-global-expression-last-kind', direct.replace('    s32 kind = -1;\n', '').replace(
            '    s32 index;', '    s32 index;\n    s32 kind = -1;')
    typed = SELECTED.replace('    u8 *base;',
        '    struct { u8 pad[8]; s16 first, second; u8 tail[4]; } *base;').replace(
        '    s16 *output;', '    struct { s16 first, second; } *output;').replace(
        '    base = D_800D19A0[identity];', '    base = (void *)D_800D19A0[identity];').replace(
        'base += ((u32 *)D_800C4020[identity])[kind] * 16;', 'base += ((u32 *)D_800C4020[identity])[kind];').replace(
        'output = (s16 *)*slot;', 'output = (void *)*slot;').replace(
        'output[index * 2] = *(s16 *)(base + index * 16 + 8);', 'output[index].first = base[index].first;').replace(
        'output[index * 2 + 1] = *(s16 *)(base + index * 16 + 10);', 'output[index].second = base[index].second;')
    yield 'record-views', typed
    expression = typed.replace('    output = (void *)allocate_memory(count * 4, 1, 0, 2);\n    *slot = (u8 *)output;\n    if (output == NULL) {',
        '    if ((*slot = (u8 *)allocate_memory(count * 4, 1, 0, 2)) == NULL) {')
    yield 'record-views-expression', expression
    for reused in ('identity', 'kind'):
        yield 'record-views-reuse-'+reused, expression.replace('    s32 index;\n', '').replace(
            'for (index = 0; index < count; index++)', 'for ('+reused+' = 0; '+reused+' < count; '+reused+'++)').replace(
            '[index]', '['+reused+']')
    for first, second in (('count', 'kind'), ('count', 'index'), ('kind', 'index')):
        declarations = {'count':'    s32 count;', 'kind':'    s32 kind = -1;', 'index':'    s32 index;'}
        yield 'record-views-swap-'+first+'-'+second, expression.replace(declarations[first], '@@').replace(
            declarations[second], declarations[first]).replace('@@', declarations[second])
    named = expression.replace('    s32 count;',
        '    typedef struct { u8 pad[8]; s16 first, second; u8 tail[4]; } SourceRecord;\n'
        '    typedef struct { s16 first, second; } PairRecord;\n    s32 count;').replace(
        'struct { u8 pad[8]; s16 first, second; u8 tail[4]; } *base;', 'SourceRecord *base;').replace(
        'struct { s16 first, second; } *output;', 'PairRecord *output;').replace(
        '(void *)D_800D19A0[identity]', '(SourceRecord *)D_800D19A0[identity]').replace(
        '(void *)*slot', '(PairRecord *)*slot')
    yield 'record-views-named', named
    for variable, declaration in (('count', 's32 count;'), ('kind', 's32 kind = -1;'),
            ('slot', 'u8 **slot;'), ('base', 'SourceRecord *base;'),
            ('output', 'PairRecord *output;'), ('index', 's32 index;')):
        yield 'record-register-'+variable, named.replace(declaration, 'register '+declaration)
    yield 'record-register-all', named.replace('    s32 ', '    register s32 ').replace(
        '    u8 **slot;', '    register u8 **slot;').replace(
        '    SourceRecord *base;', '    register SourceRecord *base;').replace(
        '    PairRecord *output;', '    register PairRecord *output;')
    yield 'record-index-first', named.replace('    s32 index;\n', '').replace(
        '    s32 count;', '    s32 index;\n    s32 count;')
    for variable in ('kind', 'count', 'index'):
        for type_name in ('s8', 's16', 'u8', 'u16'):
            yield 'record-width-'+variable+'-'+type_name, named.replace('s32 '+variable, type_name+' '+variable)
    array_view = expression.replace('struct { u8 pad[8]; s16 first, second; u8 tail[4]; } *base;',
        's16 (*base)[8];').replace('struct { s16 first, second; } *output;', 's16 (*output)[2];').replace(
        'output[index].first = base[index].first;', 'output[index][0] = base[index][4];').replace(
        'output[index].second = base[index].second;', 'output[index][1] = base[index][5];')
    yield 'record-array-views', array_view
    vertex = named.replace('SourceRecord *base;', 'Vtx *base;').replace(
        '(SourceRecord *)D_800D19A0[identity]', '(Vtx *)D_800D19A0[identity]').replace(
        'base[index].first', 'base[index].v.tc[0]').replace('base[index].second', 'base[index].v.tc[1]')
    yield 'Vtx-record-view', vertex
    yield 'Vtx-array-output', vertex.replace('PairRecord *output;', 's16 (*output)[2];').replace(
        '(PairRecord *)*slot', '(void *)*slot').replace('output[index].first', 'output[index][0]').replace(
        'output[index].second', 'output[index][1]')
    for position in ('first', 'last'):
        body = vertex if position == 'last' else vertex.replace('    s32 index;\n', '').replace(
            '    s32 count;', '    s32 index;\n    s32 count;')
        yield 'Vtx-index-'+position, body
        yield 'Vtx-global-index-'+position, body.replace('    u8 **slot;\n', '').replace(
            '    slot = &D_800C6360[identity];\n', '').replace('*slot', 'D_800C6360[identity]')
        yield 'Vtx-flat-output-index-'+position, body.replace('PairRecord *output;', 's16 *output;').replace(
            '(PairRecord *)*slot', '(s16 *)*slot').replace('output[index].first', 'output[index*2]').replace(
            'output[index].second', 'output[index*2+1]')
    for scoped in (('output',), ('index',), ('output', 'index')):
        body = named
        declarations = ''
        for variable in scoped:
            declaration = '    PairRecord *output;' if variable == 'output' else '    s32 index;'
            body = body.replace(declaration+'\n', '')
            declarations += declaration+'\n'
        body = body.replace('    output = (PairRecord *)*slot;',
            '    {\n'+declarations+'    output = (PairRecord *)*slot;').replace(
            '    return 0;\n}', '    }\n    return 0;\n}')
        yield 'record-scoped-'+'-'.join(scoped), body
    for base_type in ('u8', 's16', 'u32'):
        byte = byte_output.replace(
            '    output = (void *)allocate_memory(count * 4, 1, 0, 2);\n    *slot = (u8 *)output;\n    if (output == NULL) {',
            '    if ((*slot = (u8 *)allocate_memory(count * 4, 1, 0, 2)) == NULL) {')
        if base_type != 'u8':
            byte = byte.replace('u8 *base;', base_type+' *base;').replace(
                'base = D_800D19A0[identity];', 'base = ('+base_type+' *)D_800D19A0[identity];').replace(
                '* 16;', '* '+('8' if base_type == 's16' else '4')+';').replace(
                'base + index * 16 + 8', '(u8 *)base + index * 16 + 8').replace(
                'base + index * 16 + 10', '(u8 *)base + index * 16 + 10')
        yield base_type+'-source-view', byte


QUALIFIED = dict(candidates())['Vtx-index-first'].replace(
    '    typedef struct { u8 pad[8]; s16 first, second; u8 tail[4]; } SourceRecord;\n', '').replace(
    'PairRecord', 'TextureCoordinatePair').replace('s16 first, second;', 's16 s, t;').replace(
    'output[index].first', 'output[index].s').replace('output[index].second', 'output[index].t')
COUNTER_SOURCE_SHA = '6456ebae21a9227a74bbd15b19dba47cba8319f01c1e02d2d517da09a8df6fa2'
COUNTER_GUARDS_SHA = 'aa80c31e9eef9326b6a64100be34df67037a4d3dff3dfb76f89a15d054e0f6eb'
PAIRS = {0:(0x27BDFFC0, 0x27BDFFC8), 0x94:(0xAFA80038, 0xAFA80034),
    0xA8:(0x8FA80038, 0x8FA80034), 0x174:(0x27BD0040, 0x27BD0038)}
MAKEFILE_ANCHOR = '# This generated slice crosses an original object-profile boundary:\n'
MAKEFILE_RULE = '''# Preserve this slice's no-unroll neighbors; select only the complete
# vertex-coordinate copy from its retail unrolled object.
$(BUILD_DIR)/$(SRC_DIR)/game/generated_6A3D0.c.o: \\
\t\t$(SRC_DIR)/game/generated_6A3D0.c $$(call generated_slice_asm,6A3D0) ../tools/pad_generated_object.py retail_word_patches.us.csv Makefile
\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) $(MIPSBIT) -o $@.compact $<
\t$(CC) -c -32 $(CFLAGS) -O2 -g3 $(MIPSBIT) -o $@.unrolled.compact $<
\t$(PYTHON) ../tools/pad_generated_object.py $@.compact $(call generated_slice_asm,6A3D0) $@.padded.s \\
\t\t--function-object func_1503D804=$@.unrolled.compact --word-patches retail_word_patches.us.csv --filename generated_6A3D0
\t$(AS) $(ASFLAGS) -o $@ $@.padded.s
\trm -f $@.compact $@.unrolled.compact $@.padded.s

'''


def compile_candidate(root, out, name, body=None, profile='retail'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, QUALIFIED if body is None else body, profile)


def install(before, body=None):
    if before.count(ORIGINAL) != 1 or before.count('s32 func_1503D804();') != 1:
        raise ValueError('stale pair-copy body or forward declaration')
    anchor = 'extern u8 *D_800C6360[];'
    if before.count(anchor) != 1 or 's32 allocate_memory(s32, s32, s32, s32);' in before:
        raise ValueError('stale pair-copy allocation declaration')
    return before.replace(ORIGINAL, QUALIFIED if body is None else body).replace(
        's32 func_1503D804();', 's32 func_1503D804(s32);').replace(anchor,
        anchor+'\ns32 allocate_memory(s32, s32, s32, s32);')


def install_makefile(before):
    old = '\t$(BUILD_DIR)/$(SRC_DIR)/game/generated_1A0790.c.o\n'
    if before.count(old) != 1 or before.count(MAKEFILE_ANCHOR) != 1 or MAKEFILE_RULE in before:
        raise ValueError('stale mixed-profile owner recipe')
    return before.replace(old, old.rstrip('\n')+' \\\n\t$(BUILD_DIR)/$(SRC_DIR)/game/generated_6A3D0.c.o\n').replace(
        MAKEFILE_ANCHOR, MAKEFILE_RULE+MAKEFILE_ANCHOR)


def normalized(raw, retail):
    assert len(raw) == len(retail) == WORDS
    assert tuple(i*4 for i,(a,b) in enumerate(zip(raw,retail)) if a != b) == tuple(PAIRS)
    for offset, pair in PAIRS.items():
        assert (raw[offset//4], retail[offset//4]) == pair
    result = list(raw)
    for offset, (_, word) in PAIRS.items():
        result[offset//4] = word
    assert result == list(retail)
    return result


def guard_suffix():
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    for offset, (before, after) in PAIRS.items():
        writer.writerow(('generated_6A3D0', FUNCTION, '0x%X'%offset, '0x%08X'%before,
            '0x%08X'%after, '-', '-', 'Normalize closed vertex-coordinate copy frame and spill pairs', '', '', 'false'))
    return stream.getvalue().encode('ascii')


def counter_source(root):
    """Admit only the exact qualified successor without refreshing frozen audits."""
    from tools.experiments import game_descriptor_resource_loader_candidates as descriptor
    source = descriptor.pair_source(root)
    if ORIGINAL in source:
        return source
    assert source.count(QUALIFIED) == 1
    assert source.count('s32 func_1503D804(s32);') == 1
    assert source.count('s32 allocate_memory(s32, s32, s32, s32);') == 1
    before = source.replace(QUALIFIED, ORIGINAL).replace('s32 func_1503D804(s32);', 's32 func_1503D804();').replace(
        '\ns32 allocate_memory(s32, s32, s32, s32);', '')
    assert hashlib.sha256(before.encode('ascii')).hexdigest() == COUNTER_SOURCE_SHA
    assert install(before) == source
    return before


def require_current_slot(root, actual):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_actor_renderer_install_match import symbol_size_offset

    start = elf_slot_offset(actual, ENTRY, WORDS*4)
    extent = symbol_size_offset(actual, FUNCTION, ENTRY)
    retail = (root/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    assert actual[start:start+WORDS*4] == retail
    assert struct.unpack_from('>I', actual, extent)[0] == WORDS*4
    return start, extent


def counter_elf(root, before):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_actor_renderer_install_match import symbol_size_offset
    from tools.experiments import game_descriptor_resource_loader_candidates as descriptor

    source = counter_source(root)
    actual = descriptor.pair_elf(root, before)
    if descriptor.pair_source(root) == source:
        return actual
    start, extent = require_current_slot(root, actual)
    old_start = elf_slot_offset(before, ENTRY, WORDS*4)
    old_extent = symbol_size_offset(before, FUNCTION, ENTRY)
    assert struct.unpack_from('>I', before, old_extent)[0] == 12
    result = bytearray(actual)
    result[start:start+WORDS*4] = before[old_start:old_start+WORDS*4]
    struct.pack_into('>I', result, extent, 12)
    return bytes(result)


def counter_guards(root):
    from tools.experiments import game_third_resource_loader_lifetime_candidates as third
    current = third.historical_guards(root)
    if hashlib.sha256(current).hexdigest() == COUNTER_GUARDS_SHA:
        return current
    assert current.endswith(guard_suffix())
    source = counter_source(root)
    assert source != (root/SOURCE).read_text()
    assert hashlib.sha256(source.encode('ascii')).hexdigest() == COUNTER_SOURCE_SHA
    require_current_slot(root, (root/'conker/build/conker.us.elf').read_bytes())
    before = current[:-len(guard_suffix())]
    assert hashlib.sha256(before).hexdigest() == COUNTER_GUARDS_SHA
    return before


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-record-pair-copy'
    records = []
    for name, body in [('qualified', QUALIFIED), *candidates()]:
        if args.filter and args.filter not in name:
            continue
        for profile in ('retail', 'owner') if args.profiles else ('retail',):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
