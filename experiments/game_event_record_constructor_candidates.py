"""Match the two raw-word flag tests and original input-home lifetime."""
import argparse
from pathlib import Path
import re
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15015104, 0x425B4, 52
FUNCTION, SOURCE = 'func_15015104', 'conker/src/game_40490.c'
DECLARATIONS = '''typedef struct EventPayload15015104 struct37;
void func_1510F800(s32);
s32 func_1510FD20(s32, s32);
void *func_15149130(s16,s8,s8,s8,u8,u8,struct37 *,u8,s32);
void *memcpy(void *, const void *, unsigned int);
'''
SYMBOLS = dict(func_1510F800=0x1510F800, func_1510FD20=0x1510FD20,
               func_15149130=0x15149130, memcpy=0x10022EC0)
OLD_FLAGS = '    flags = *(s32 *)(arg0 + 0x20) != 0;\n    data.unkC = flags | (flags ? 2 : 0);'
NEW_FLAGS = '    flags = *(s32 *)(arg0 + 0x20);\n    data.unkC = (flags ? 1 : 0) | (flags ? 2 : 0);'


def function_body(source):
    match = re.search(r's32 func_15015104\([^;{}]+\) \{\n.*?\n\}', source, re.S)
    if not match:
        raise ValueError('Expected complete event record constructor')
    return match.group(0)


def selected(source):
    body = function_body(source)
    if body.count(OLD_FLAGS) == 1:
        return body.replace(OLD_FLAGS, NEW_FLAGS)
    if body.count(NEW_FLAGS) == 1:
        return body
    raise ValueError('Expected the known old or matched flag computation')


def recovered_owner(source):
    body = function_body(source)
    return source.replace(body, selected(source), 1)


def compile_candidate(root, out, name, body):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
                        RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, 'o2g3')


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-event-record-constructor'
    out.mkdir(exist_ok=True)
    meta, _ = compile_candidate(root, out, 'direct', selected((root / SOURCE).read_text()))
    print(meta['body_words'], hex(meta['frame']), meta['differences'], meta['pool_bytes'])


if __name__ == '__main__':
    main()
