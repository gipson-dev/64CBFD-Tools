"""Recover the record rectangle predicate without changing ordered comparisons."""
import argparse
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1501AE94, 0x48344, 44
FUNCTION, SOURCE = 'func_1501AE94', 'conker/src/game_476D0.c'
DECLARATIONS = 'extern s32 D_800BE620, D_800BE624, D_800BE628;\n'
SYMBOLS = dict(D_800BE620=0x800BE620, D_800BE624=0x800BE624, D_800BE628=0x800BE628)
ORIGINAL = 's32 func_1501AE94() {\n    return 0;\n}'
SELECTED = '''s32 func_1501AE94(s32 arg0) {
    f32 maxX = D_800BE620 - 2.0f;
    f32 maxY = D_800BE624;
    f32 *record = (f32 *)((u8 *)D_800BE628 + (u32)arg0 * 0x180);

    if ((record[11] < 2.0f) || (maxX < record[12])) {
        return 0;
    }
    if ((record[9] < 0.0f) || (maxY < record[10])) {
        return 0;
    }
    return 1;
}'''


def recovered_owner(source):
    if source.count(ORIGINAL) == 1:
        source = source.replace(ORIGINAL, SELECTED)
    elif source.count(SELECTED) != 1:
        raise ValueError('Expected the known placeholder or complete rectangle predicate')
    source = source.replace('s32 func_1501AE94();', 's32 func_1501AE94(s32 arg0);')
    return source.replace('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501AE94.s. */\n', '')


def compile_candidate(root, out, name, body=SELECTED):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
                        RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, body, 'o2g3')
    meta['frame'] = (-words[0]) & 65535 if words[0] & 0xFFFF0000 == 0x27BD0000 else 0
    return meta, words


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-rectangle-bounds'
    out.mkdir(exist_ok=True)
    meta, _ = compile_candidate(root, out, 'direct')
    print(meta['body_words'], meta['frame'], meta['differences'], meta['pool_bytes'])


if __name__ == '__main__':
    main()
