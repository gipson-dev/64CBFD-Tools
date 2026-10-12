"""Recover the mode-selected callback dispatcher, without word guards."""
import argparse
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15008930, 0x35DE0, 40
FUNCTION, SOURCE = 'func_15008930', 'conker/src/game_35D20.c'
ORIGINAL = 's32 func_15008930() {\n    return 0;\n}'
DECLARATIONS = '''typedef void (*GameModeCallback)(void);
extern GameModeCallback D_80082BD0;
extern GameModeCallback D_80082BD4;
extern s32 D_800DD1B0;
'''
SYMBOLS = dict(D_80082BD0=0x80082BD0, D_80082BD4=0x80082BD4, D_800DD1B0=0x800DD1B0)
SELECTED = '''void func_15008930(s32 mode) {
    GameModeCallback *selected;
    GameModeCallback *cursor;
    s32 count;
    s32 index;

    if (mode == 1) {
        selected = &D_80082BD0;
        count = 1;
    } else if (mode == 2) {
        selected = &D_80082BD4;
        count = 1;
    } else {
        count = 0;
    }
    index = 0;
    if (count > 0) {
        cursor = selected;
        do {
            (*cursor)();
            index++;
            cursor++;
        } while (index != count);
    }
    D_800DD1B0 = -1;
}'''


def compile_candidate(root, out, name, body=SELECTED):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
                        RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, 'o2g3')


def recovered_owner(source):
    if source.count(ORIGINAL) != 1 or source.count('s32 func_15008930();') != 1:
        raise ValueError('Expected untouched callback placeholder and declaration')
    source = source.replace('s32 func_15008930();', 'void func_15008930(s32 mode);')
    source = source.replace('/* Generated placeholder declarations. */', '/* Function declarations. */').replace(
        '/* End generated placeholder declarations. */', '/* End function declarations. */')
    source = source.replace('/* Non-matching C placeholders for asm/nonmatchings/game_35D20/func_15008930.s. */\n', '')
    return source.replace('#include "variables.h"\n', '#include "variables.h"\n\n' + DECLARATIONS).replace(ORIGINAL, SELECTED)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-mode-callback-dispatch'
    out.mkdir(exist_ok=True)
    meta, _ = compile_candidate(root, out, 'direct')
    print(meta['body_words'], meta['frame'], meta['differences'], meta['pool_bytes'])


if __name__ == '__main__':
    main()
