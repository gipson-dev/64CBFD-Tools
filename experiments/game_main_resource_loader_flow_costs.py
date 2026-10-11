"""Measure natural full-loader status joins without changing installed C."""
import argparse
import hashlib
import json
from pathlib import Path

from tools.experiments import game_main_resource_loader_lifetimes as lifetime


def candidates():
    late = lifetime.SELECTED
    early = late.replace('    failed = 0;\n', '').replace(
        '    mainSlot = &D_800D19A0[identity];\n',
        '    mainSlot = &D_800D19A0[identity];\n    failed = 0;\n')
    yield 'banked-late', late
    yield 'early', early
    presence = early.replace('    if (*mainSlot != NULL) {\n        return 0;',
        '    if (*mainSlot != NULL) {\n        return failed;')
    yield 'presence-status', presence
    yield 'request-status', presence.replace('        return 1;', '        return failed | 1;')
    shared = early.replace('    failed = 0;\n', '').replace(
        '    if (identity == 0xFF)', '    failed = 0;\n    if (identity == 0xFF)')
    shared = shared.replace('        return 0;', '        goto done;').replace(
        '        return 1;', '        failed = 1;\n        goto done;').replace(
        '    return failed;\n}', 'done:\n    return failed;\n}')
    yield 'shared-return', shared
    top = early.replace('    failed = 0;\n', '').replace(
        '    if (identity == 0xFF)', '    failed = 0;\n    if (identity == 0xFF)')
    yield 'top-initialization', top
    request_join = early.replace('        return 1;', '        failed = 1;\n        goto done;').replace(
        '    return failed;\n}', 'done:\n    return failed;\n}')
    yield 'request-join', request_join
    yield 'presence-request-join', request_join.replace(
        '    if (*mainSlot != NULL) {\n        return 0;',
        '    if (*mainSlot != NULL) {\n        goto done;')
    old_event = '''            offset = 0;
            for (index = 0; index < *count; index++) {
                func_1510CE60(*(u32 *)((u8 *)*primary + offset), 0, 0, 0x3E, 0);
                offset += 4;
            }'''
    new_event = '''            index = 0;
            offset = 0;
            if (*count > 0) {
                do {
                    func_1510CE60(*(u32 *)((u8 *)*primary + offset), 0, 0, 0x3E, 0);
                    index++;
                    offset += 4;
                } while (index < *count);
            }'''
    for name, body in (('early', early), ('request-join', request_join), ('banked-late', late)):
        assert body.count(old_event) == 1
        yield name+'-event-do', body.replace(old_event, new_event)
    for count_name in ('separate', 'boundary'):
        counted = request_join
        if count_name == 'separate':
            counted = counted.replace('    u32 boundary;', '    u32 boundary;\n    u32 initialCount;')
        value = 'initialCount' if count_name == 'separate' else 'boundary'
        counted = counted.replace('    if ((*count = block[3] >> 2) > 0) {',
            '    '+value+' = block[3] >> 2;\n    *count = '+value+';\n    if ((u16)'+value+' > 0) {')
        yield 'request-join-count-'+count_name, counted
        cleaned = counted.replace('    u8 **cleanupSlot;', '    u8 **cleanupSlot;\n    u8 *cleanupValue;')
        cleaned = cleaned.replace('        if (*cleanupSlot != NULL) {\n            func_10004074(*cleanupSlot);',
            '        cleanupValue = *cleanupSlot;\n        if (cleanupValue != NULL) {\n            func_10004074(cleanupValue);')
        yield 'request-join-count-'+count_name+'-cleanup-value', cleaned
    for variable in ('index', 'offset', 'boundary'):
        kind = 'u32' if variable == 'boundary' else 's32'
        body = request_join.replace('    '+kind+' '+variable+';\n', '').replace(
            's32 failed,', kind+' '+variable+',')
        body = body.replace('    s32 output;', '    s32 output;\n    s32 failed;')
        yield 'request-join-parameter-'+variable, body
    for name, body in (('top-initialization', top), ('shared-return', shared),
            ('request-join', request_join)):
        yield name+'-local-status', body.replace('s32 identity, s32 failed,',
            's32 identity, s32 unused,').replace('    s32 output;',
            '    s32 output;\n    s32 failed;')
    start = early.index('    *mainSlot = (u8 *)block + 0x38;')
    end = early.index('    return failed;\n}')
    nested = early[:start].replace('    if (block == NULL) {\n        return 1;\n    }\n',
        '    if (block != NULL) {\n')
    nested += ''.join('    '+line+'\n' for line in early[start:end].splitlines())
    nested += '        return failed;\n    }\n    return 1;\n}'
    yield 'nested-request', nested
    for name, body in (('early', early), ('shared-return', shared), ('nested-request', nested)):
        for hint in ('parameter', 'cursors', 'all'):
            hinted = body
            if hint in ('parameter', 'all'):
                hinted = hinted.replace('s32 identity, s32 failed,',
                    's32 identity, register s32 failed,')
            if hint in ('cursors', 'all'):
                for declaration in ('s32 index', 's32 offset', 'u32 *block',
                        'u32 **primary', 'u32 **secondary', 'u16 *count'):
                    hinted = hinted.replace('    '+declaration+';',
                        '    register '+declaration+';')
            yield name+'-register-'+hint, hinted


def measure(root, out, name, body):
    meta, words = lifetime.loader.compile_candidate(root, out, name, body)
    meta['saved_registers'] = [reg for reg in range(16, 24)
        if any(word >> 26 == 0x2B and (word >> 21) & 31 == 29 and
            (word >> 16) & 31 == reg for word in words[:20])]
    meta['opening_zero_destinations'] = [word >> 11 & 31 for word in words[:50]
        if word >> 26 == 0 and word & 0x3F == 0x25 and (word >> 16) & 1023 == 0]
    meta['source_sha256'] = hashlib.sha256(body.encode('ascii')).hexdigest()
    return meta, words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-main-resource-loader-flow-costs'
    out.mkdir(exist_ok=True)
    measurements = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, _ = measure(root, out, name, body)
        measurements.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            meta['saved_registers'], meta['opening_zero_destinations'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
