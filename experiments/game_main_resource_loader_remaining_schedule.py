"""Measure the complete loader's remaining private and return scheduling."""
import argparse
import json
import struct
from pathlib import Path

from tools.experiments import game_main_resource_loader_private_layout as layout
from tools.experiments import game_main_resource_loader_candidates as screen


BANKED = layout.SELECTED
CLEANUP = '''        if (*cleanupSlot != NULL) {
            func_10004074(*cleanupSlot);
            *cleanupSlot = NULL;
        }'''
FIRST_COUNT = '''    D_800C4778[identity] = block[3] >> 2;
    index = 0;
    if (D_800C4778[identity] > 0) {'''
REQUEST = '''    if (block == NULL) {
        failed = 1;
        goto done;
    }'''


def scoped_cleanup(body, kind='u8 *', conditional=False):
    assert body.count(CLEANUP) == 2
    pointer = 'cleanupValue'
    load = '(u8 *)*cleanupSlot' if kind == 'void *' else '*cleanupSlot'
    assign = '' if conditional else '            '+pointer+' = '+load+';\n'
    condition = '('+pointer+' = '+load+')' if conditional else pointer
    replacement = ('        {\n            '+kind+pointer+';\n'+assign+
        '            if ('+condition+' != NULL) {\n'
        '                func_10004074('+pointer+');\n'
        '                *cleanupSlot = NULL;\n            }\n        }')
    return body.replace(CLEANUP, replacement)


def request_forms(body):
    yield 'joined', body
    yield 'direct', body.replace(REQUEST, '    if (block == NULL) {\n        return 1;\n    }').replace('done:\n', '')
    yield 'label-literal', body.replace('        failed = 1;\n        goto done;',
        '        goto requestFailed;').replace('done:\n    return failed;\n}',
        '    return failed;\nrequestFailed:\n    return 1;\n}')
    begin = body.index(REQUEST)
    end = body.index('done:\n')
    middle = body[begin+len(REQUEST):end]
    nested = body[:begin]+'    if (block != NULL) {'+''.join('\n    '+line for line in middle.splitlines())
    yield 'nested-success', nested+'\n    } else {\n        return 1;\n    }\n    return failed;\n}'
    yield 'nested-failure-join', nested+'\n    } else {\n        failed = 1;\n    }\n    return failed;\n}'


def candidates():
    yield 'banked', BANKED
    initial = (
        ('before-store', '    index = 0;\n    D_800C4778[identity] = block[3] >> 2;\n    if (D_800C4778[identity] > 0) {'),
        ('inside-positive', '    D_800C4778[identity] = block[3] >> 2;\n    if (D_800C4778[identity] > 0) {\n        index = 0;'),
        ('comma-test', '    D_800C4778[identity] = block[3] >> 2;\n    if ((index = 0, D_800C4778[identity] > 0)) {'))
    for name, replacement in initial:
        yield 'initial-'+name, BANKED.replace(FIRST_COUNT, replacement)
    bases = [('banked', BANKED)]
    for kind in ('u8 *', 'void *'):
        for conditional in (False, True):
            name = 'scoped-'+kind.split()[0]+('-condition' if conditional else '-before')
            body = scoped_cleanup(BANKED, kind, conditional)
            yield name, body
            bases.append((name, body))
    for name, body in bases:
        for request_name, requested in request_forms(body):
            if request_name != 'joined':
                yield name+'-request-'+request_name, requested
    for value in ('output', 'boundary'):
        old = CLEANUP
        replacement = ('        '+value+' = (u32)*cleanupSlot;\n'
            '        if ('+value+' != 0) {\n'
            '            func_10004074((void *)'+value+');\n'
            '            *cleanupSlot = NULL;\n        }')
        yield 'reuse-'+value, BANKED.replace(old, replacement)
    for scope in ('cleanup', 'whole'):
        declaration = '    u8 **cleanupSlot;\n'
        body = BANKED.replace(declaration, '')
        if scope == 'cleanup':
            body = body.replace('    if (failed != 0) {',
                '    if (failed != 0) {\n        u8 **cleanupSlot;')
        else:
            body = body.replace('    wordIndex = identity * 4;',
                '    {\n    u8 **cleanupSlot;\n    wordIndex = identity * 4;').replace(
                'done:\n', '    }\ndone:\n')
        yield 'slot-scope-'+scope, body
    for declaration in ('u32 *block;', 's32 index;', 'u32 boundary;',
            's32 offset;', 'u8 **cleanupSlot;', 's32 wordIndex;'):
        yield 'register-'+declaration.split()[-1].replace('*', '').replace(';', ''), BANKED.replace(
            '    '+declaration, '    register '+declaration)
    for base_name, base in (('banked', BANKED), ('scheduled', SELECTED)):
        initial_main = base.index('    if ('+layout.MAIN+' != NULL)')
        first_cleanup = base.index('    if (failed != 0) {')
        bound = base[:initial_main]+'    cleanupSlot = &'+layout.MAIN+';\n'
        bound += base[initial_main:first_cleanup].replace(layout.MAIN, '*cleanupSlot')
        bound += base[first_cleanup:]
        yield base_name+'-reuse-main-slot', bound
        main_cleanup = bound.index('        if ('+layout.MAIN+' != NULL)')
        rebound = bound[:main_cleanup]+'        cleanupSlot = &'+layout.MAIN+';\n'
        rebound += bound[main_cleanup:].replace(layout.MAIN, '*cleanupSlot')
        yield base_name+'-rebind-main-slot', rebound
    for expression in ('(void *)*cleanupSlot', '*cleanupSlot + 0', '&(*cleanupSlot)[0]'):
        yield 'cleanup-expression-'+str(expression.index('*')), SELECTED.replace(
            'func_10004074(*cleanupSlot);', 'func_10004074('+expression+');')


def measure(root, out, name, body):
    meta, words = layout.measure(root, out, name, body)
    retail = struct.unpack_from('>274I', (root/'conker/conker.us.bin').read_bytes(), screen.ROM)
    meta['different_offsets'] = [i*4 for i, (actual, original) in enumerate(zip(words, retail)) if actual != original]
    return meta, words


SELECTED = BANKED.replace(FIRST_COUNT,
    '    D_800C4778[identity] = block[3] >> 2;\n'
    '    if ((index = 0, D_800C4778[identity] > 0)) {')


def install(before):
    if before.count(BANKED) != 1:
        raise ValueError('stale main resource loader private-layout checkpoint')
    return before.replace(BANKED, SELECTED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-main-resource-loader-remaining-schedule'
    out.mkdir(exist_ok=True)
    measurements = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, _ = measure(root, out, name, body)
        measurements.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            meta['private_stack_offsets'], meta['saved_registers'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
