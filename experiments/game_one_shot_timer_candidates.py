"""Recover the gated timer's unsigned64 clock expression and O32 call."""
import argparse
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1501BB20, 0x48FD0, 38
FUNCTION, SOURCE = 'func_1501BB20', 'conker/src/game/generated_48FD0.c'
DECLARATIONS = '''extern u8 D_80084064;
extern u64 D_8002BD10;
extern OSTimer D_800BE6E0;
extern OSMesgQueue D_8003B218;
'''
SYMBOLS = dict(D_80084064=0x80084064, D_8002BD10=0x8002BD10,
               D_800BE6E0=0x800BE6E0, D_8003B218=0x8003B218,
               __ll_mul=0x10026968, __ull_div=0x10026868, osSetTimer=0x10024A40)
ORIGINAL = 's32 func_1501BB20() {\n    return 0;\n}'
SELECTED = '''void func_1501BB20(void) {
    if (D_80084064 != 0) {
        osSetTimer(&D_800BE6E0, (25 * D_8002BD10) / 1000000, 0,
            &D_8003B218, (OSMesg)6);
        D_80084064 = 0;
    }
}'''


def recovered_owner(source):
    if source.count(ORIGINAL) == 1:
        source = source.replace(ORIGINAL, SELECTED)
    elif source.count(SELECTED) != 1:
        raise ValueError('Expected the known timer placeholder or complete body')
    if DECLARATIONS not in source:
        source = source.replace('#include <ultra64.h>\n', '#include <ultra64.h>\n' + DECLARATIONS, 1)
    return source


def compile_candidate(root, out, name, body=SELECTED):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
                        RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, 'o2g3')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controls', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-one-shot-timer'
    out.mkdir(exist_ok=True)
    bodies = [('direct', SELECTED)]
    if args.controls:
        bodies += [('clock-first', SELECTED.replace('25 * D_8002BD10', 'D_8002BD10 * 25')),
            ('typed-constant', SELECTED.replace('25 * D_8002BD10', '25ULL * D_8002BD10')),
            ('local-countdown', SELECTED.replace('        osSetTimer', '        u64 countdown = (25 * D_8002BD10) / 1000000;\n        osSetTimer')
                .replace('osSetTimer(&D_800BE6E0, (25 * D_8002BD10) / 1000000,', 'osSetTimer(&D_800BE6E0, countdown,'))]
    for name, body in bodies:
        meta, _ = compile_candidate(root, out, name, body)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], meta['pool_bytes'], flush=True)


if __name__ == '__main__':
    main()
