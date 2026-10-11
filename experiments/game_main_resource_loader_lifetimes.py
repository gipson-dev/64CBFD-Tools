"""Measure full-loader cursor and error lifetimes without changing installed C."""
import argparse
import itertools
import json
import re
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_main_resource_loader_candidates as loader

BANKED = loader.QUALIFIED
SELECTED = BANKED.replace('    u32 *first;\n', '').replace(
    '    first = &D_800C4020[identity];\n    *first = block[0];',
    '    D_800C4020[identity] = block[0];').replace('*first', 'D_800C4020[identity]')
for _table in ('primary', 'secondary'):
    SELECTED = SELECTED.replace('func_1503D438((u32 *)((u8 *)*'+_table+' + offset),',
        'func_1503D438(&(*'+_table+')[index],')
SELECTED = SELECTED.replace('    s32 failed;\n', '').replace(
    's32 identity, s32 unused,', 's32 identity, s32 failed,')
SELECTED = SELECTED.replace('s32 extras, s32 flags) {\n',
    's32 extras, s32 flags) {\n    /* Ignore the incoming second word; later reuse it as the status value. */\n')


def install(before):
    if before.count(BANKED) != 1:
        raise ValueError('stale installed main resource loader recovery')
    return before.replace(BANKED, SELECTED)


def candidates():
    early = dict(loader.candidates())['gated-loops']
    for lifetime, cursor, count, cleanup in itertools.product(
            ('early', 'late'), ('offset', 'mixed'), ('assignment', 'temporary'),
            ('direct', 'temporary')):
        body = early
        if lifetime == 'late':
            body = body.replace('    failed = 0;\n', '').replace(
                '    if (extras != 0)', '    failed = 0;\n    if (extras != 0)')
        if cursor == 'mixed':
            for table in ('primary', 'secondary'):
                body = body.replace('func_1503D438((u32 *)((u8 *)*'+table+' + offset),',
                    'func_1503D438(&(*'+table+')[index],')
        if count == 'temporary':
            body = body.replace('    u32 boundary;', '    u32 boundary;\n    u32 initialCount;').replace(
                '    if ((*count = block[3] >> 2) > 0) {',
                '    initialCount = block[3] >> 2;\n    *count = initialCount;\n    if ((u16)initialCount > 0) {')
        if cleanup == 'temporary':
            body = body.replace('    u8 **cleanupSlot;', '    u8 **cleanupSlot;\n    u8 *cleanupValue;')
            body = body.replace('        if (*cleanupSlot != NULL) {\n            func_10004074(*cleanupSlot);',
                '        cleanupValue = *cleanupSlot;\n        if (cleanupValue != NULL) {\n            func_10004074(cleanupValue);')
        yield '-'.join((lifetime, cursor, count, cleanup)), body


def compact_candidates():
    base = dict(candidates())['early-mixed-assignment-direct']
    for direct_first, cleanup in itertools.product((False, True), ('slot', 'primary', 'offset')):
        body = base
        if direct_first:
            body = body.replace('    u32 *first;\n', '').replace(
                '    first = &D_800C4020[identity];\n    *first = block[0];',
                '    D_800C4020[identity] = block[0];').replace('*first', 'D_800C4020[identity]')
        if cleanup == 'primary':
            body = body.replace('    u8 **cleanupSlot;\n', '').replace('cleanupSlot', 'primary').replace(
                'primary = &D_800C5C08', 'primary = (u32 **)&D_800C5C08').replace(
                'primary = &D_800C6070', 'primary = (u32 **)&D_800C6070')
        if cleanup == 'offset':
            body = body.replace('    u8 **cleanupSlot;\n', '').replace('cleanupSlot', 'offset').replace(
                'offset = &D_800C5C08', 'offset = (s32)&D_800C5C08').replace(
                'offset = &D_800C6070', 'offset = (s32)&D_800C6070').replace(
                '*offset', '*(u8 **)offset')
        yield 'compact-%d-%s' % (direct_first, cleanup), body
        yield 'compact-%d-%s-register-error' % (direct_first, cleanup), body.replace(
            '    s32 failed;', '    register s32 failed;')


def storage_candidates():
    base = dict(compact_candidates())['compact-1-primary']
    for lifetime, temporary in itertools.product(('early', 'initializer', 'late'),
            ('separate', 'boundary', 'output', 'block')):
        body = base
        if lifetime == 'initializer':
            body = body.replace('    s32 failed;', '    s32 failed = 0;').replace('    failed = 0;\n', '')
        if lifetime == 'late':
            body = body.replace('    failed = 0;\n', '').replace(
                '    if (extras != 0)', '    failed = 0;\n    if (extras != 0)')
        if temporary != 'separate':
            value = 'boundary' if temporary == 'boundary' else 'output' if temporary == 'output' else 'block'
            expression = value if temporary == 'boundary' else '(u32)'+value
            body = body.replace('    *count = block[3] >> 2;', '    *count = '+expression+' >> 2;')
            if temporary == 'block':
                continue
            body = body.replace('    if ((*count = block[3] >> 2) > 0) {',
                '    '+value+' = block[3] >> 2;\n    *count = '+value+';\n    if ((u16)'+value+' > 0) {')
        yield 'storage-%s-%s' % (lifetime, temporary), body
    body = base.replace('    u8 **mainSlot;\n', '').replace('    s32 output;', '    s32 output;\n    u8 **mainSlot;')
    yield 'storage-slot-first', body
    yield 'storage-output-last', base.replace('    s32 output;\n', '').replace(
        '    u32 boundary;', '    u32 boundary;\n    s32 output;')


def parameter_candidates():
    for base_name in ('early-mixed-assignment-direct', 'late-mixed-assignment-direct'):
        base = dict(candidates())[base_name]
        for variable in ('failed', 'index', 'offset', 'boundary'):
            declaration = '    %s %s;\n' % ('u32' if variable == 'boundary' else 's32', variable)
            body = base.replace(declaration, '').replace(variable, 'unused')
            if variable == 'boundary':
                body = body.replace('s32 unused,', 'u32 unused,')
            yield 'parameter-%s-%s' % (base_name, variable), body
        for direct_first, cleanup in itertools.product((False, True), ('slot', 'primary')):
            body = dict(compact_candidates())['compact-%d-%s' % (direct_first, cleanup)]
            if base_name.startswith('late'):
                body = body.replace('    failed = 0;\n', '').replace(
                    '    if (extras != 0)', '    failed = 0;\n    if (extras != 0)')
            body = body.replace('    s32 failed;\n', '').replace('failed', 'unused')
            yield 'parameter-%s-compact-%d-%s' % (base_name, direct_first, cleanup), body


def control_candidates():
    base = dict(candidates())['early-mixed-assignment-direct']
    for compact, count_form, loop_form, resets in itertools.product((False, True),
            ('assignment', 'load', 'reload-header', 'u32-temp', 's32-temp'),
            ('do', 'for', 'break'), ('before', 'inside')):
        body = dict(compact_candidates())['compact-1-primary'] if compact else base
        if count_form == 'load':
            body = body.replace('    if ((*count = block[3] >> 2) > 0) {',
                '    *count = block[3] >> 2;\n    if (*count > 0) {')
        if count_form == 'reload-header':
            body = body.replace('    if ((*count = block[3] >> 2) > 0) {',
                '    *count = block[3] >> 2;\n    if ((u16)(block[3] >> 2) > 0) {')
        if count_form.endswith('-temp'):
            kind = count_form.split('-')[0]
            body = body.replace('    u32 boundary;', '    u32 boundary;\n    '+kind+' initialCount;').replace(
                '    if ((*count = block[3] >> 2) > 0) {',
                '    initialCount = block[3] >> 2;\n    *count = initialCount;\n    if ((u16)initialCount > 0) {')
        if loop_form == 'for':
            body = body.replace('        do {', '        for (;;) {').replace(
                '        } while (index < *count);',
                '            if (index >= *count) { break; }\n        }').replace(
                '        } while ((u32)index < boundary);',
                '            if ((u32)index >= boundary) { break; }\n        }')
        if loop_form == 'break':
            body = body.replace('        do {', '        while (1) {').replace(
                '        } while (index < *count);',
                '            if (index < *count) { continue; }\n            break;\n        }').replace(
                '        } while ((u32)index < boundary);',
                '            if ((u32)index < boundary) { continue; }\n            break;\n        }')
        if resets == 'inside':
            body = body.replace('    index = 0;\n    if (', '    if (').replace(
                ' > 0) {\n        offset = 0;', ' > 0) {\n        index = 0;\n        offset = 0;').replace(
                '    index = 0;\n    offset = 0;\n    if (boundary != 0) {',
                '    if (boundary != 0) {\n        index = 0;\n        offset = 0;')
        yield 'control-%d-%s-%s-%s' % (compact, count_form, loop_form, resets), body


def compact_more_candidates():
    base = dict(compact_candidates())['compact-1-primary']
    for lifetime, table in itertools.product(('early', 'late'), ('main', 'count', 'secondary', 'primary')):
        body = base
        if lifetime == 'late':
            body = body.replace('    failed = 0;\n', '').replace(
                '    if (extras != 0)', '    failed = 0;\n    if (extras != 0)')
        if table == 'main':
            body = body.replace('    u8 **mainSlot;\n', '').replace(
                '    mainSlot = &D_800D19A0[identity];\n', '').replace('*mainSlot', 'D_800D19A0[identity]')
        if table == 'count':
            body = body.replace('    u16 *count;\n', '').replace(
                '    count = &D_800C4778[identity];\n', '').replace('*count', 'D_800C4778[identity]')
        if table == 'secondary':
            body = body.replace('    u32 **secondary;\n', '').replace(
                '    secondary = &D_800C48F0[identity];\n', '').replace('*secondary', 'D_800C48F0[identity]')
        if table == 'primary':
            body = body.replace('    u32 **primary;\n', '').replace(
                '    primary = &D_800C4488[identity];\n', '').replace('*primary', 'D_800C4488[identity]')
            body = body.replace('        primary = (u32 **)&D_800C5C08[identity];',
                '        block = (u32 *)&D_800C5C08[identity];').replace(
                '        primary = (u32 **)&D_800C6070[identity];',
                '        block = (u32 *)&D_800C6070[identity];')
            start = body.index('        block = (u32 *)&D_800C5C08')
            body = body[:start]+body[start:].replace('D_800C4488[identity]', '*(u8 **)block')
        yield 'compact-more-%s-%s' % (lifetime, table), body


def allocation_measurements(root, out):
    options = ('do_opt_saved_regs', 'noprecolor', 'noheurAB', 'no_r23', 'nogenvreg',
        'norlodrstropt', 'nordstore', 'no_const_in_reg', 'docopy')
    bodies = dict(candidates())
    for name in ('early-mixed-assignment-direct', 'late-mixed-assignment-direct'):
        for option in options:
            flags = ('-O2', '-g3', '-Wo,-loopunroll,0', '-Wo,-'+option)
            with patch.dict(loader.compiler.PROFILES, allocation=flags):
                meta, _ = loader.compile_candidate(root, out, name+'-'+option, bodies[name], 'allocation')
            meta['extra_flags'] = ['-Wo,-'+option]
            yield meta


def representation_candidates():
    base = dict(compact_candidates())['compact-1-primary']
    for lifetime, block_kind, cleanup_value in itertools.product(('early', 'late'),
            ('pointer', 'u32', 's32'), ('direct', 'block', 'boundary')):
        body = base
        if lifetime == 'late':
            body = body.replace('    failed = 0;\n', '').replace(
                '    if (extras != 0)', '    failed = 0;\n    if (extras != 0)')
        if block_kind != 'pointer':
            body = body.replace('    u32 *block;', '    '+block_kind+' block;').replace(
                'block = func_1502B6BC(', 'block = ('+block_kind+')func_1502B6BC(')
            body = re.sub(r'\bblock\[(\d+)\]', r'((u32 *)block)[\1]', body)
            body = body.replace('block == NULL', 'block == 0')
        if cleanup_value != 'direct':
            value = cleanup_value
            assignment = '(u32 *)*primary' if value == 'block' and block_kind == 'pointer' else '(u32)*primary'
            body = body.replace('        if (*primary != NULL) {\n            func_10004074(*primary);',
                '        '+value+' = '+assignment+';\n        if ('+value+' != 0) {\n            func_10004074((void *)'+value+');')
        yield 'representation-%s-%s-%s' % (lifetime, block_kind, cleanup_value), body


def header_candidates():
    fields = ('first', 'firstBytes', 'primary', 'primaryBytes', 'word4', 'word5',
        'extra', 'extraBytes', 'word8', 'word9', 'secondary', 'secondaryBytes')
    declaration = '    struct {\n'+''.join('        u32 '+field+';\n' for field in fields)+'    } *block;'
    base = dict(candidates())['early-mixed-assignment-direct']
    for compact, typed, count_gate in itertools.product((False, True), (False, True),
            ('assignment', 'temp-before-index', 'temp-after-index', 'boolean')):
        body = dict(compact_candidates())['compact-1-primary'] if compact else base
        body = body.replace('    u32 *block;', declaration)
        for i, field in enumerate(fields):
            body = body.replace('block[%d]' % i, 'block->'+field)
        if typed:
            for field in ('primary', 'extra', 'secondary'):
                body = body.replace('        u32 '+field+';', '        u32 *'+field+';').replace(
                    '(u32 *)block->'+field, 'block->'+field)
        if count_gate.startswith('temp-'):
            body = body.replace('    u32 boundary;', '    u32 boundary;\n    u32 initialCount;')
            old = '    index = 0;\n    if ((*count = block->primaryBytes >> 2) > 0) {'
            rows = '    initialCount = block->primaryBytes >> 2;\n    *count = initialCount;\n'
            if count_gate == 'temp-before-index':
                rows += '    index = 0;\n'
            else:
                rows = '    index = 0;\n'+rows
            body = body.replace(old, rows+'    if ((u16)initialCount > 0) {')
        if count_gate == 'boolean':
            body = body.replace('if ((*count = block->primaryBytes >> 2) > 0)',
                'if ((*count = block->primaryBytes >> 2) != 0)')
        yield 'header-%d-%d-%s' % (compact, typed, count_gate), body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--compact', action='store_true')
    parser.add_argument('--storage', action='store_true')
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--parameters', action='store_true')
    parser.add_argument('--control', action='store_true')
    parser.add_argument('--more', action='store_true')
    parser.add_argument('--allocation', action='store_true')
    parser.add_argument('--representation', action='store_true')
    parser.add_argument('--header', action='store_true')
    parser.add_argument('--selected', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-main-resource-loader-lifetimes'
    out.mkdir(exist_ok=True)
    measurements = []
    if args.allocation:
        for meta in allocation_measurements(root, out):
            measurements.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
        (out/'allocation-measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')
        return
    forms = [('selected', SELECTED)] if args.selected else header_candidates() if args.header else representation_candidates() if args.representation else compact_more_candidates() if args.more else control_candidates() if args.control else parameter_candidates() if args.parameters else storage_candidates() if args.storage else compact_candidates() if args.compact else candidates()
    for name, body in forms:
        if args.filter not in name:
            continue
        for profile in ('retail', 'o2', 'o1g3') if args.profiles else ('retail',):
            meta, _ = loader.compile_candidate(root, out, name+'-'+profile, body, profile)
            measurements.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
