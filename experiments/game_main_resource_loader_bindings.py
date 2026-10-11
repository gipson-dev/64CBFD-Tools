"""Measure real table/value bindings in the complete main resource loader."""
import argparse
import json
import re
from pathlib import Path

from tools.experiments import game_main_resource_loader_remaining_schedule as schedule


BANKED = schedule.SELECTED
MAIN = schedule.layout.MAIN
CLEANUP = schedule.CLEANUP
DECLARATIONS = '''    u32 *block;
    s32 index;
    s32 output;
    u32 boundary;
    s32 offset;
    u8 **cleanupSlot;
    s32 wordIndex;'''


def bind_main(body, register=False):
    declaration = '    '+('register ' if register else '')+'u8 **mainSlot;'
    body = body.replace('    s32 wordIndex;', '    s32 wordIndex;\n'+declaration)
    body = body.replace('    failed = 0;',
        '    mainSlot = &'+MAIN+';\n    failed = 0;', 1)
    return body.replace(MAIN, '*mainSlot').replace(
        'mainSlot = &*mainSlot;', 'mainSlot = &'+MAIN+';')


def bind_cleanup(body, register=False, conditional=False):
    assert body.count(CLEANUP) == 2
    declaration = '    '+('register ' if register else '')+'u8 *cleanupValue;'
    body = body.replace('    s32 wordIndex;', '    s32 wordIndex;\n'+declaration)
    load = '' if conditional else '        cleanupValue = *cleanupSlot;\n'
    condition = '(cleanupValue = *cleanupSlot)' if conditional else 'cleanupValue'
    return body.replace(CLEANUP, load+'        if ('+condition+' != NULL) {\n'
        '            func_10004074(cleanupValue);\n            *cleanupSlot = NULL;\n        }')


def cursor_record(body):
    body = body.replace('    s32 index;\n', '').replace('    s32 offset;\n', '')
    body = body.replace('    u32 *block;', '    u32 *block;\n    struct { s32 index; s32 offset; } cursor;')
    start = body.index('\n\n    if (identity')
    return body[:start]+re.sub(r'\b(index|offset)\b', lambda match: 'cursor.'+match[0], body[start:])


def candidates():
    yield 'banked', BANKED
    bases = [('plain', BANKED), ('cursor-record', cursor_record(BANKED))]
    for name, body in bases:
        if name != 'plain':
            yield name, body
        for main in (False, True):
            bound = bind_main(body, main)
            yield name+'-main-'+('register' if main else 'local'), bound
            for register in (False, True):
                yield name+'-main-'+str(int(main))+'-cleanup-'+str(int(register)), bind_cleanup(bound, register)
        for register in (False, True):
            for conditional in (False, True):
                yield name+'-cleanup-'+str(int(register))+'-condition-'+str(int(conditional)), bind_cleanup(body, register, conditional)
    for declaration in ('u32 *block', 's32 index', 's32 output', 'u32 boundary', 's32 offset', 'u8 **cleanupSlot'):
        for kind in ('u8 *', 'register u8 *'):
            body = BANKED.replace('    '+declaration+';', '    '+declaration+';\n    '+kind+'value;')
            body = body.replace(CLEANUP,
                '        value = *cleanupSlot;\n        if (value != NULL) {\n'
                '            func_10004074(value);\n            *cleanupSlot = NULL;\n        }')
            yield 'cleanup-after-'+declaration.split()[-1].replace('*', '')+'-'+kind.split()[0], body
    for conditional in (False, True):
        load = '' if conditional else '        config = *cleanupSlot;\n'
        condition = '(config = *cleanupSlot)' if conditional else 'config'
        yield 'layout-config-'+str(int(conditional)), BANKED.replace(CLEANUP,
            load+'        if ('+condition+' != NULL) {\n'
            '            func_10004074(config);\n            *cleanupSlot = NULL;\n        }')
    declarations = DECLARATIONS.splitlines()
    assert BANKED.count(DECLARATIONS) == 1
    for original in (0, 1, 4, 5, 6):
        declaration = declarations[original]
        shortened = declarations[:original]+declarations[original+1:]
        for position in range(len(declarations)):
            if position == original:
                continue
            ordered = shortened[:position]+[declaration]+shortened[position:]
            yield 'layout-move-'+str(original)+'-to-'+str(position), BANKED.replace(DECLARATIONS, '\n'.join(ordered))


def measure(root, out, name, body):
    return schedule.measure(root, out, name, body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-main-resource-loader-bindings'
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
