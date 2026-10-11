"""Recover six-draw record impulse and angular-rate initialization."""
import argparse
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503EB78, 0x6C028, 74
FUNCTION, SOURCE = 'func_1503EB78', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503EB78(s32 arg0, f32 arg1, f32 arg2, s32 arg3) {\n    return 0;\n}'
PROTOTYPE = 's32 func_1503EB78(s32, f32, f32, s32);'
RECOVERED_PROTOTYPE = 'void func_1503EB78(struct04 *, f32, f32, s32);'
LOCAL_DECLARATIONS = '''extern f32 D_80098920;
extern f32 D_80098924;
s32 func_150ADA20(void);
'''
DECLARATIONS = '#include "variables.h"\n'+LOCAL_DECLARATIONS
SYMBOLS = dict(D_80098920=0x80098920, D_80098924=0x80098924, func_150ADA20=0x150ADA20)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'), compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
BASE = '''void func_1503EB78(struct04 *record, f32 horizontal, f32 vertical, s32 mode) {
    f32 scales[3];
    s32 mask;
    s32 bias;
    s32 index;

    if (mode != 0) {
        mask = 0x80;
        bias = 0x7F;
    } else {
        mask = 0xFF;
        bias = 0;
    }
    scales[0] = horizontal * D_80098920;
    scales[1] = vertical * D_80098920;
    scales[2] = scales[0];
    for (index = 0; index < 3; index++) {
        ((f32 *)record)[18 + index] *= ((func_150ADA20() & mask) + bias) * scales[index] + 2.0f;
    }
    for (index = 0; index < 3; index++) {
        ((f32 *)record)[21 + index] = ((func_150ADA20() & 0xFF) - 0x80) * 0.03125f;
    }
    ((f32 *)record)[24] = D_80098924;
}'''
SCALED = BASE.replace('    scales[0] = horizontal * D_80098920;\n    scales[1] = vertical * D_80098920;\n    scales[2] = scales[0];',
    '    horizontal *= D_80098920;\n    vertical *= D_80098920;\n    scales[0] = horizontal;\n    scales[2] = horizontal;\n    scales[1] = vertical;')
SELECTED = SCALED.replace('    f32 scales[3];\n    s32 mask;', '    s32 mask;\n    f32 scales[3];')
GUARD_ROWS = [('generated_6B320', FUNCTION, offset, expected, replacement, relocation, relocation,
    'Normalize closed impulse coefficient FPR allocation cycle', '', '', 'false')
    for offset, expected, replacement, relocation in (
        ('0x48', '0xC4200000', '0xC4220000', 'R_MIPS_LO16:D_80098920'),
        ('0x54', '0x46006302', '0x46026002', '-'),
        ('0x60', '0x46007382', '0x46027382', '-'),
        ('0x68', '0xE7AC0050', '0xE7A00050', '-'),
        ('0x6C', '0xE7AC0058', '0xE7A00058', '-'))]
CALLS = ('func_1503EB78(arg0, 2.0f, 2.0f, 0);', 'func_1503EB78(arg0, 1.0f, 2.0f, 1);',
    'func_1503EB78(arg0, 2.06f, 3.0f, 1);')


def candidates():
    yield 'selected', SELECTED
    yield 'mask-first', BASE.replace('    f32 scales[3];\n    s32 mask;', '    s32 mask;\n    f32 scales[3];')
    yield 'bias-first', BASE.replace('    f32 scales[3];\n    s32 mask;\n    s32 bias;',
        '    s32 bias;\n    f32 scales[3];\n    s32 mask;')
    yield 'scale-store-order', BASE.replace('    scales[1] = vertical * D_80098920;\n    scales[2] = scales[0];',
        '    scales[2] = scales[0];\n    scales[1] = vertical * D_80098920;')
    yield 'float-record', BASE.replace('struct04 *record,', 'f32 *record,').replace('((f32 *)record)', 'record')
    yield 'index-first', BASE.replace('    s32 index;\n', '').replace('    f32 scales[3];', '    s32 index;\n    f32 scales[3];')
    yield 'cursor', BASE.replace('    s32 index;', '    s32 index;\n    f32 *cursor = (f32 *)record;').replace(
        'index < 3; index++) {\n        ((f32 *)record)[18 + index]', 'index < 3; index++, cursor++) {\n        cursor[18]')
    yield 'sum-first', BASE.replace('((func_150ADA20() & mask) + bias) * scales[index] + 2.0f',
        '2.0f + ((func_150ADA20() & mask) + bias) * scales[index]')
    scaled = BASE.replace('    scales[0] = horizontal * D_80098920;\n    scales[1] = vertical * D_80098920;\n    scales[2] = scales[0];',
        '    horizontal *= D_80098920;\n    vertical *= D_80098920;\n    scales[0] = horizontal;\n    scales[2] = horizontal;\n    scales[1] = vertical;')
    yield 'scaled-arguments', scaled
    yield 'scaled-mask-first', scaled.replace('    f32 scales[3];\n    s32 mask;', '    s32 mask;\n    f32 scales[3];')
    yield 'scaled-index-first', scaled.replace('    s32 index;\n', '').replace('    f32 scales[3];', '    s32 index;\n    f32 scales[3];')
    yield 'vertical-argument', BASE.replace('scales[1] = vertical * D_80098920', 'scales[1] = vertical *= D_80098920')
    yield 'horizontal-combined', BASE.replace('    scales[0] = horizontal * D_80098920;\n    scales[1] = vertical * D_80098920;\n    scales[2] = scales[0];',
        '    scales[2] = scales[0] = horizontal * D_80098920;\n    scales[1] = vertical * D_80098920;')
    yield 'local-factor', BASE.replace('    f32 scales[3];', '    f32 factor;\n    f32 scales[3];').replace(
        '    scales[0] = horizontal * D_80098920;', '    factor = D_80098920;\n    scales[0] = horizontal * factor;').replace(
        'scales[1] = vertical * D_80098920', 'scales[1] = vertical * factor')
    prepared = scaled.replace('    horizontal *= D_80098920;', '    xScale = horizontal * D_80098920;').replace(
        'scales[0] = horizontal;', 'scales[0] = xScale;').replace('scales[2] = horizontal;', 'scales[2] = xScale;')
    for where in ('first', 'last', 'scoped'):
        body = prepared.replace('    f32 scales[3];', '    f32 xScale;\n    f32 scales[3];') if where == 'first' else prepared.replace(
            '    s32 index;', '    s32 index;\n    f32 xScale;') if where == 'last' else prepared.replace(
            '    xScale =', '    {\n    f32 xScale;\n    xScale =').replace('    scales[1] = vertical;', '    scales[1] = vertical;\n    }')
        yield 'final-xscale-'+where, body
        yield 'final-mask-xscale-'+where, body.replace('    f32 scales[3];\n    s32 mask;', '    s32 mask;\n    f32 scales[3];')
    prefix = BASE.split('    scales[0] =', 1)[0]
    suffix = '    for (index = 0; index < 3; index++) {'+BASE.split('    for (index = 0; index < 3; index++) {', 1)[1]
    for name, setup in (
            ('repeated', '    scales[0] = horizontal * D_80098920;\n    scales[2] = horizontal * D_80098920;\n    scales[1] = vertical * D_80098920;\n'),
            ('repeated-vertical', '    scales[0] = horizontal * D_80098920;\n    scales[2] = horizontal * D_80098920;\n    scales[1] = vertical *= D_80098920;\n'),
            ('vertical-before', '    vertical *= D_80098920;\n    scales[0] = scales[2] = horizontal * D_80098920;\n    scales[1] = vertical;\n'),
            ('chained-vertical', '    scales[0] = scales[2] = horizontal * D_80098920;\n    scales[1] = vertical *= D_80098920;\n'),
            ('reverse-chained', '    scales[2] = scales[0] = horizontal * D_80098920;\n    scales[1] = vertical *= D_80098920;\n')):
        yield 'next-'+name, prefix+setup+suffix
        yield 'next-mask-'+name, (prefix+setup+suffix).replace('    f32 scales[3];\n    s32 mask;', '    s32 mask;\n    f32 scales[3];')
    xbody = prepared.replace('    s32 index;', '    s32 index;\n    f32 xScale;')
    for name, body in (('xscale', xbody), ('vertical-first', xbody.replace(
            '    xScale = horizontal * D_80098920;\n    vertical *= D_80098920;',
            '    vertical *= D_80098920;\n    xScale = horizontal * D_80098920;'))):
        yield 'last-'+name+'-mode-index', body.replace('    s32 index;\n', '').replace('index', 'mode')
        yield 'last-'+name+'-mode-mask', body.replace('    s32 mask;\n', '').replace('mask =', 'mode =').replace('& mask', '& mode')
        yield 'last-'+name+'-mode-bias', body.replace('    s32 bias;\n', '').replace('bias =', 'mode =').replace('+ bias', '+ mode')
        yield 'last-'+name, body
        yield 'last-mask-'+name, body.replace('    f32 scales[3];\n    s32 mask;', '    s32 mask;\n    f32 scales[3];')
        yield 'register-'+name, body.replace('    f32 xScale;', '    register f32 xScale;')
        yield 'register-mask-'+name, body.replace('    f32 xScale;', '    register f32 xScale;').replace(
            '    f32 scales[3];\n    s32 mask;', '    s32 mask;\n    f32 scales[3];')
    for name, body in (('scaled', scaled), ('xscale', xbody)):
        for local in ('s32 index;', 's32 mask;', 's32 bias;'):
            yield 'register-'+name+'-'+local.split()[-1][:-1], body.replace('    '+local, '    register '+local)
        for mask_type, bias_type in (('u8', 'u8'), ('u16', 'u16'), ('u8', 's32'), ('s32', 'u8')):
            yield 'width-'+name+'-'+mask_type+'-'+bias_type, body.replace('s32 mask;', mask_type+' mask;').replace(
                's32 bias;', bias_type+' bias;')
        body = body.replace('    s32 index;\n', '').replace('    for (index = 0; index < 3; index++) {',
            '    {\n    s32 index;\n    for (index = 0; index < 3; index++) {', 1).replace(
            '    ((f32 *)record)[24] =', '    }\n    ((f32 *)record)[24] =')
        yield 'scope-index-'+name, body
        yield 'scope-index-mask-'+name, body.replace('    f32 scales[3];\n    s32 mask;', '    s32 mask;\n    f32 scales[3];')
    match_body = scaled.replace('    f32 scales[3];\n    s32 mask;', '    s32 mask;\n    f32 scales[3];')
    for parameter in ('horizontal', 'vertical', 'both'):
        body = match_body
        for name in (('horizontal', 'vertical') if parameter == 'both' else (parameter,)):
            body = body.replace('f32 '+name+',', 'register f32 '+name+',')
        yield 'parameter-register-'+parameter, body


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(source):
    assert source.count(ORIGINAL) == source.count(PROTOTYPE) == 1
    assert SELECTED not in source and LOCAL_DECLARATIONS.rstrip() not in source
    for call in CALLS: assert source.count(call) == 1
    result = source.replace(ORIGINAL, SELECTED).replace(PROTOTYPE, RECOVERED_PROTOTYPE+'\n'+LOCAL_DECLARATIONS.rstrip())
    for name in ('func_1503F078', 'func_1503F0AC', 'func_1503F0D8'):
        old = 'void '+name+'(s32 arg0, u8 arg1) {'
        assert source.count(old) == 1
        result = result.replace(old, 'void '+name+'(struct04 *arg0, s32 arg1) {')
    return result


def guard_successor(data):
    rows = list(csv.DictReader(io.StringIO(data.decode('ascii'))))
    assert not any(row['function'] == FUNCTION for row in rows)
    assert data.endswith(b'\n')
    out = io.StringIO(newline='')
    csv.writer(out, lineterminator='\r\n' if data.endswith(b'\r\n') else '\n').writerows(GUARD_ROWS)
    return data+out.getvalue().encode('ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='selected')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]; out = root/'conker/build/game-record-impulse'
    records = []
    for name, body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in (('owner', 'compact', 'o1g3', 'o1') if args.profiles else ('owner',)):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta); print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
