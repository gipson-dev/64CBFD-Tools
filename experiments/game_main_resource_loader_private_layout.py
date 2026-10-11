"""Measure complete-loader local order and initial count/store scheduling."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_main_resource_loader_count_lifetimes as count


BANKED = count.SELECTED
DECLARATIONS = '''    s32 output;
    u32 *block;
    s32 index;
    s32 offset;
    u32 boundary;
    u8 **cleanupSlot;'''


def candidates():
    body = BANKED
    yield 'banked', body
    for declaration in ('u32 *block', 's32 index', 's32 offset', 'u32 boundary', 'u8 **cleanupSlot'):
        moved = body.replace('    s32 output;\n', '').replace('    '+declaration+';',
            '    '+declaration+';\n    s32 output;')
        yield 'output-after-'+declaration.split()[-1].replace('*', ''), moved
    assert body.count(DECLARATIONS) == 1
    for name, order in (
            ('output-boundary-middle', ('u32 *block', 's32 index', 's32 output', 'u32 boundary', 's32 offset', 'u8 **cleanupSlot')),
            ('output-before-boundary', ('u32 *block', 's32 index', 's32 offset', 's32 output', 'u32 boundary', 'u8 **cleanupSlot')),
            ('boundary-before-output', ('u32 *block', 's32 index', 's32 offset', 'u32 boundary', 's32 output', 'u8 **cleanupSlot'))):
        yield name, body.replace(DECLARATIONS, '\n'.join('    '+item+';' for item in order))
    old = '''    index = 0;
    if ((D_800C4778[identity] = block[3] >> 2) > 0) {'''
    assert body.count(old) == 1
    for variable in ('index', 'offset', 'boundary'):
        for reset in ('before', 'inside'):
            new = '    '+variable+' = block[3] >> 2;\n    D_800C4778[identity] = '+variable+';\n'
            if reset == 'before':
                new += '    index = 0;\n'
            new += '    if ((u16)'+variable+' > 0) {'
            if reset == 'inside':
                new += '\n        index = 0;'
            if variable == 'index' and reset == 'before':
                continue
            yield 'initial-'+variable+'-reset-'+reset, body.replace(old, new)
    for kind in ('u32', 's32', 'u16'):
        for reset in ('before', 'inside'):
            new = '    initialCount = block[3] >> 2;\n    D_800C4778[identity] = initialCount;\n'
            if reset == 'before':
                new += '    index = 0;\n'
            new += '    if ((u16)initialCount > 0) {'
            if reset == 'inside':
                new += '\n        index = 0;'
            candidate = body.replace('    u32 boundary;', '    u32 boundary;\n    '+kind+' initialCount;')
            yield 'initial-'+kind+'-reset-'+reset, candidate.replace(old, new)
    for reset in ('before', 'inside'):
        new = '    D_800C4778[identity] = block[3] >> 2;\n'
        if reset == 'before':
            new += '    index = 0;\n'
        new += '    if (D_800C4778[identity] > 0) {'
        if reset == 'inside':
            new += '\n        index = 0;'
        yield 'separate-store-reset-'+reset, body.replace(old, new)
    old_event = '''            offset = 0;
            for (index = 0; index < D_800C4778[identity]; index++) {
                func_1510CE60(*(u32 *)((u8 *)D_800C4488[identity] + offset), 0, 0, 0x3E, 0);
                offset += 4;
            }'''
    event = '''            index = 0;
            offset = 0;
            if (D_800C4778[identity] > 0) {
                do {
                    func_1510CE60(*(u32 *)((u8 *)D_800C4488[identity] + offset), 0, 0, 0x3E, 0);
                    index++;
                    offset += 4;
                } while (index < D_800C4778[identity]);
            }'''
    assert body.count(old_event) == 1
    yield 'event-do', body.replace(old_event, event)
    separate = body.replace(old, '    D_800C4778[identity] = block[3] >> 2;\n'
        '    index = 0;\n    if (D_800C4778[identity] > 0) {')
    middle = ('u32 *block', 's32 index', 's32 output', 'u32 boundary', 's32 offset', 'u8 **cleanupSlot')
    ordered = separate.replace(DECLARATIONS, '\n'.join('    '+item+';' for item in middle))
    for name, base in (('separate', separate), ('ordered-separate', ordered)):
        yield name+'-event-do', base.replace(old_event, event)
        if name == 'ordered-separate':
            yield name, base
        first = base.replace('    u8 **cleanupSlot;', '    u8 **cleanupSlot;\n    u32 *first;').replace(
            '    D_800C4020[identity] = block[0];',
            '    first = &D_800C4020[identity];\n    *first = block[0];')
        start = first.index('    if (D_800C4020[identity] != 0)')
        yield name+'-first-pointer', first[:start]+first[start:].replace('D_800C4020[identity]', '*first')
        main = base.replace('    u8 **cleanupSlot;', '    u8 **cleanupSlot;\n    u8 **mainSlot;').replace(
            '    failed = 0;', '    mainSlot = &D_800D19A0[identity];\n    failed = 0;', 1)
        yield name+'-main-pointer', main.replace('D_800D19A0[identity]', '*mainSlot').replace(
            'mainSlot = &*mainSlot;', 'mainSlot = &D_800D19A0[identity];')
        initial = base.replace('    u8 **cleanupSlot;', '    u8 **cleanupSlot;\n    u32 initialSize;').replace(
            '    D_800C4778[identity] = block[3] >> 2;',
            '    initialSize = block[3];\n    D_800C4778[identity] = initialSize >> 2;')
        yield name+'-initial-size', initial
    best = ordered.replace(old_event, event)
    for size, variable, tables in (
            (4, 'wordIndex', (('D_800D19A0', 'u8 *'), ('D_800C4020', 'u32'),
                ('D_800C4488', 'u32 *'), ('D_800C48F0', 'u32 *'), ('D_800C4BE0', 'u32'),
                ('D_800C5338', 'u32 *'), ('D_800C5048', 'u32'), ('D_800C6360', 'u8 *'),
                ('D_800C5C08', 'u8 *'), ('D_800C6070', 'u8 *'))),
            (2, 'halfIndex', tuple((table, 'u16') for table in
                ('D_800C4310', 'D_800C57A0', 'D_800C4778', 'D_800C5628', 'D_800C4ED0')))):
        for declaration in ('u32 *block', 's32 output', 'u8 **cleanupSlot'):
            indexed = best.replace('    '+declaration+';', '    '+declaration+';\n    s32 '+variable+';')
            indexed = indexed.replace('    failed = 0;', '    '+variable+' = identity * '+str(size)+';\n    failed = 0;', 1)
            for table, kind in tables:
                pointer = kind+('*' if kind.endswith('*') else ' *')
                indexed = indexed.replace(table+'[identity]',
                    '(*('+pointer+')((u8 *)'+table+' + '+variable+'))')
            yield variable+'-after-'+declaration.split()[-1].replace('*', ''), indexed
            if size == 4 and declaration == 'u8 **cleanupSlot':
                worded = indexed
                for kind in ('u32', 'register s32'):
                    yield 'wordIndex-'+kind.replace(' ', '-'), indexed.replace(
                        '    s32 wordIndex;', '    '+kind+' wordIndex;')
                yield 'wordIndex-unsigned-shift', indexed.replace(
                    'wordIndex = identity * 4;', 'wordIndex = (u32)identity << 2;')
                yield 'wordIndex-parameter', indexed.replace('    s32 wordIndex;\n', '').replace(
                    's32 identity, s32 failed,', 's32 identity, s32 wordIndex,').replace(
                    '    u8 **cleanupSlot;', '    u8 **cleanupSlot;\n    s32 failed;')
    for name, failure in (('literal', 'return 1;'), ('status-or', 'return failed | 1;'),
            ('status-add', 'return failed + 1;'), ('assign-return', 'return failed = 1;')):
        direct = best.replace('        failed = 1;\n        goto done;', '        '+failure).replace('done:\n', '')
        yield 'request-error-'+name, direct
    old_boundary = '''    if (D_800C4020[identity] != 0) {
        boundary = D_800C4020[identity];
    } else {
        boundary = (u32)D_800C4488[identity];
    }'''
    yield 'boundary-cached-load', best.replace(old_boundary,
        '    boundary = D_800C4020[identity];\n    if (boundary == 0) {\n'
        '        boundary = (u32)D_800C4488[identity];\n    }')
    for name, base in (('ordered', best), ('worded', worded)):
        if name == 'worded':
            main_expression = '(*(u8 **)((u8 *)D_800D19A0 + wordIndex))'
            assert main_expression in base
            for declaration in ('u32 *block', 's32 output', 's32 wordIndex'):
                main = base.replace('    '+declaration+';', '    '+declaration+';\n    u8 **mainSlot;')
                main = main.replace('    failed = 0;',
                    '    mainSlot = (u8 **)((u8 *)D_800D19A0 + wordIndex);\n    failed = 0;', 1)
                yield 'worded-main-after-'+declaration.split()[-1].replace('*', ''), main.replace(main_expression, '*mainSlot')
        for declaration in ('u32 *block', 's32 output', 'u8 **cleanupSlot'):
            cleaned = base.replace('    '+declaration+';', '    '+declaration+';\n    u8 *cleanupValue;')
            cleaned = cleaned.replace('        if (*cleanupSlot != NULL) {\n            func_10004074(*cleanupSlot);',
                '        cleanupValue = *cleanupSlot;\n        if (cleanupValue != NULL) {\n            func_10004074(cleanupValue);')
            yield name+'-cleanup-value-after-'+declaration.split()[-1].replace('*', ''), cleaned
        for spelling in ('before', 'condition'):
            if spelling == 'before':
                new = '        block = (u32 *)*cleanupSlot;\n        if (block != NULL) {\n            func_10004074(block);'
            else:
                new = '        if ((block = (u32 *)*cleanupSlot) != NULL) {\n            func_10004074(block);'
            yield name+'-cleanup-block-'+spelling, base.replace(
                '        if (*cleanupSlot != NULL) {\n            func_10004074(*cleanupSlot);', new)


def measure(root, out, name, body):
    meta, words = count.measure(root, out, name, body)
    meta['request_output_stack'] = next((word & 65535 for word in words[:50]
        if word >> 26 == 9 and word >> 21 & 31 == 29 and word >> 16 & 31 == 4), None)
    meta['private_stack_offsets'] = sorted({word & 65535 for index, word in enumerate(words)
        if index > 20 and word >> 26 in (0x23, 0x2B) and word >> 21 & 31 == 29
        and 0x3C < word & 65535 < meta['frame']})
    store = next((i for i, word in enumerate(words)
        if word >> 26 == 0x29 and word >> 21 & 31 == 21 and word & 65535 == 0), None)
    meta['initial_count_store_register'] = None if store is None else words[store] >> 16 & 31
    meta['masked_initial_count_store'] = store is not None and any(
        word >> 26 == 0xC and word & 65535 == 65535 and
        word >> 16 & 31 == meta['initial_count_store_register'] for word in words[max(0, store-5):store])
    return meta, words


SELECTED = dict(candidates())['wordIndex-after-cleanupSlot']
MAIN = '(*(u8 **)((u8 *)D_800D19A0 + wordIndex))'


def install(before):
    if before.count(BANKED) != 1:
        raise ValueError('stale main resource loader original-frame checkpoint')
    return before.replace(BANKED, SELECTED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-main-resource-loader-private-layout'
    out.mkdir(exist_ok=True)
    measurements = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, _ = measure(root, out, name, body)
        measurements.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            meta['request_output_stack'], meta['private_stack_offsets'],
            meta['masked_initial_count_store'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
