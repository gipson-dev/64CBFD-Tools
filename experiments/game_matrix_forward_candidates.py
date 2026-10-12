"""Recover fixed/float matrix preparation and ten-pointer forwarding."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503F404, 0x6C8B4, 43
FUNCTION, SOURCE = 'func_1503F404', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503F404() {\n    return 0;\n}'
LOCAL_DECLARATION = '''extern u8 D_800C3E90;
void *memcpy(void *, const void *, unsigned int);
'''
DECLARATIONS = '#include "variables.h"\n'+LOCAL_DECLARATION+'''
void func_1503E5F8(f32 [4][4], f32 *, f32 *, f32 *, f32 *, f32 *, f32 *, f32 *, f32 *, f32 *);
'''
SYMBOLS = dict(D_800C3E90=0x800C3E90, guMtxL2F=0x151EFEB8,
    memcpy=0x10022EC0, func_1503E5F8=0x1503E5F8)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'),
    compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
BASE = '''void func_1503F404(void *input, f32 *x, f32 *y, f32 *z,
    f32 *rx, f32 *ry, f32 *rz, f32 *sx, f32 *sy, f32 *sz) {
    f32 matrix[4][4];

    if (D_800C3E90 != 0) {
        guMtxL2F(matrix, (Mtx *)input);
    } else {
        memcpy(matrix, input, sizeof(matrix));
    }
    func_1503E5F8(matrix, x, y, z, rx, ry, rz, sx, sy, sz);
}'''
SELECTED = BASE


def candidates():
    yield 'selected', SELECTED
    yield 'mtx-input', BASE.replace('void *input', 'Mtx *input')
    yield 'float-input', BASE.replace('void *input', 'f32 input[4][4]')
    yield 'explicit-copy-size', BASE.replace('sizeof(matrix)', '0x40')


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATIONS,
            SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(source):
    assert source.count(ORIGINAL) == 1 and SELECTED not in source
    assert LOCAL_DECLARATION.rstrip() not in source
    return source.replace(ORIGINAL, SELECTED).replace('#include "variables.h"\n',
        '#include "variables.h"\n'+LOCAL_DECLARATION, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='selected')
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-matrix-forward'
    records = []
    for name, body in candidates():
        if args.filter and args.filter not in name:
            continue
        for profile in (('owner', 'compact', 'o1g3', 'o1') if args.profiles else ('owner',)):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
