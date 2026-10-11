"""Measure complete-loader count expressions and private pointer copies."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_main_resource_loader_flow_costs as flow


def candidates():
    parents = dict(flow.candidates())
    for name in ('banked-late', 'request-join', 'presence-request-join'):
        body = parents[name]
        yield name, body
        direct = body.replace('    u16 *count;\n', '').replace(
            '    count = &D_800C4778[identity];\n', '').replace('*count', 'D_800C4778[identity]')
        yield name+'-direct-count', direct
        start = body.index('    if (extras != 0)')
        yield name+'-direct-event-count', body[:start]+body[start:].replace('*count', 'D_800C4778[identity]')
        yield name+'-refresh-count', body[:start]+'    count = &D_800C4778[identity];\n'+body[start:]
        counted = body.replace('    u16 *count;\n', '')
        start = counted.index('    count = &D_800C4778[identity];')
        end = counted.index('done:\n' if name != 'banked-late' else '    return failed;\n}')
        tail = counted[start:end].replace('    count = &D_800C4778[identity];',
            '    u16 * const count = &D_800C4778[identity];', 1)
        scoped = counted[:start]+'    {\n'+''.join('    '+line+'\n' for line in tail.splitlines())
        scoped += '    }\n'+counted[end:]
        yield name+'-const-count', scoped
        for value in ('index', 'offset'):
            counted = body.replace('    index = 0;\n    if ((*count = block[3] >> 2) > 0) {',
                '    '+value+' = block[3] >> 2;\n    *count = '+value+';\n    if ((u16)'+value+' > 0) {\n        index = 0;')
            yield name+'-initial-'+value, counted
    direct = parents['request-join'].replace('    u16 *count;\n', '').replace(
        '    count = &D_800C4778[identity];\n', '').replace('*count', 'D_800C4778[identity]')
    for declaration in ('u32 *block', 'u8 **mainSlot', 'u32 **primary', 'u32 **secondary',
            's32 index', 's32 offset', 'u32 boundary', 'u8 **cleanupSlot'):
        moved = direct.replace('    s32 output;\n', '').replace('    '+declaration+';',
            '    '+declaration+';\n    s32 output;')
        yield 'direct-output-after-'+declaration.split()[-1].replace('*', ''), moved
    for value in ('initialCount', 'boundary'):
        counted = direct
        if value == 'initialCount':
            counted = counted.replace('    u32 boundary;', '    u32 boundary;\n    u32 initialCount;')
        counted = counted.replace('    if ((D_800C4778[identity] = block[3] >> 2) > 0) {',
            '    '+value+' = block[3] >> 2;\n    D_800C4778[identity] = '+value+';\n    if ((u16)'+value+' > 0) {')
        yield 'direct-initial-'+value, counted
    yield 'direct-local-status', direct.replace('s32 identity, s32 failed,',
        's32 identity, s32 unused,').replace('    s32 output;', '    s32 output;\n    s32 failed;')
    cleaned = direct.replace('    u8 **cleanupSlot;\n', '')
    for table in ('D_800C5C08', 'D_800C6070'):
        old = '''        cleanupSlot = &%s[identity];
        if (*cleanupSlot != NULL) {
            func_10004074(*cleanupSlot);
            *cleanupSlot = NULL;
        }''' % table
        new = '''        if (%s[identity] != NULL) {
            func_10004074(%s[identity]);
            %s[identity] = NULL;
        }''' % (table, table, table)
        assert cleaned.count(old) == 1
        cleaned = cleaned.replace(old, new)
    yield 'direct-cleanup', cleaned
    for name, body in (('direct-main', direct), ('direct-main-cleanup', cleaned)):
        body = body.replace('    u8 **mainSlot;\n', '').replace(
            '    mainSlot = &D_800D19A0[identity];\n', '').replace('*mainSlot', 'D_800D19A0[identity]')
        yield name, body
    main = direct.replace('    u8 **mainSlot;\n', '').replace(
        '    mainSlot = &D_800D19A0[identity];\n', '').replace('*mainSlot', 'D_800D19A0[identity]')
    for base_name, base in (('count', direct), ('main', main)):
        for removed in (('primary',), ('secondary',), ('primary', 'secondary')):
            body = base
            for variable in removed:
                table = 'D_800C4488' if variable == 'primary' else 'D_800C48F0'
                body = body.replace('    u32 **'+variable+';\n', '').replace(
                    '    '+variable+' = &'+table+'[identity];\n', '').replace(
                    '*'+variable, table+'[identity]')
            yield 'direct-'+base_name+'-remove-'+'-'.join(removed), body
    best = main
    for variable, table in (('primary', 'D_800C4488'), ('secondary', 'D_800C48F0')):
        best = best.replace('    u32 **'+variable+';\n', '').replace(
            '    '+variable+' = &'+table+'[identity];\n', '').replace('*'+variable, table+'[identity]')
    early = best.replace('        failed = 1;\n        goto done;', '        return 1;').replace('done:\n', '')
    yield 'early-all-direct', early
    for name, base in (('join', best), ('early', early)):
        first = base.replace('    u32 boundary;', '    u32 boundary;\n    u32 *first;').replace(
            '    D_800C4020[identity] = block[0];', '    first = &D_800C4020[identity];\n    *first = block[0];')
        start = first.index('    if (D_800C4020[identity] != 0)')
        first = first[:start]+first[start:].replace('D_800C4020[identity]', '*first')
        yield name+'-all-direct-first-pointer', first
        cleaned = base.replace('    u8 **cleanupSlot;\n', '')
        for table in ('D_800C5C08', 'D_800C6070'):
            cleaned = cleaned.replace('        cleanupSlot = &'+table+'[identity];\n', '').replace(
                '        if (*cleanupSlot != NULL) {\n            func_10004074(*cleanupSlot);\n            *cleanupSlot = NULL;\n        }',
                '        if ('+table+'[identity] != NULL) {\n            func_10004074('+table+'[identity]);\n            '+table+'[identity] = NULL;\n        }', 1)
        yield name+'-all-direct-cleanup', cleaned


def measure(root, out, name, body):
    meta, words = flow.measure(root, out, name, body)
    meta['private_S5_stores'] = [dict(offset=index*4, stack=word & 65535)
        for index, word in enumerate(words) if index > 20 and word >> 26 == 0x2B
        and (word >> 21) & 31 == 29 and (word >> 16) & 31 == 21
        and word & 65535 < meta['frame']]
    return meta, words


SELECTED = dict(candidates())['direct-main-remove-primary-secondary']


def install(before):
    if before.count(flow.lifetime.SELECTED) != 1:
        raise ValueError('stale main resource loader retail-length checkpoint')
    return before.replace(flow.lifetime.SELECTED, SELECTED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-main-resource-loader-count-lifetimes'
    out.mkdir(exist_ok=True)
    measurements = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, _ = measure(root, out, name, body)
        measurements.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            meta['saved_registers'], meta['private_S5_stores'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
