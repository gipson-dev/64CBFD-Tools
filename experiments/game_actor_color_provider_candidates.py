"""Recover the complete fourteen-argument renderer color provider."""
import csv
import io
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502CC34, 0x5A0E4, 50
FUNCTION, SOURCE = 'func_1502CC34', 'conker/src/game/generated_58F80.c'
ORIGINAL = 's32 func_1502CC34() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 D_800D9B68[], D_800D9B78[];
void func_1502EC34(u8 *, s32 *, s32 *, s32 *, s32 *);
'''
SYMBOLS = dict(D_800D9B68=0x800D9B68, D_800D9B78=0x800D9B78, func_1502EC34=0x1502EC34)
SELECTED = '''void func_1502CC34(u8 *actor, s32 view, s32 alpha, s32 *parameters,
    s32 *primitiveR, s32 *primitiveG, s32 *primitiveB,
    s32 *environmentR, s32 *environmentG, s32 *environmentB,
    s32 *fogR, s32 *fogG, s32 *fogB, s32 *fogA) {
    u8 *primitive = D_800D9B68 + (u32)view * 3;
    u8 *environment = D_800D9B78 + (u32)view * 3;

    *primitiveR = primitive[0];
    *primitiveG = primitive[1];
    *primitiveB = primitive[2];
    *environmentR = environment[0];
    *environmentG = environment[1];
    *environmentB = environment[2];
    *fogR = 0;
    *fogG = 0;
    *fogB = 0;
    *fogA = parameters[3];
    if (actor[0xA4] != 0) {
        func_1502EC34(actor, fogR, fogG, fogB, fogA);
    }
}'''


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before):
    from tools.experiments import game_actor_renderer_matching as renderer
    changed = renderer.recovery.copied_owner(before, renderer.SELECTED)
    if changed.count(ORIGINAL) != 1:
        raise ValueError('stale color provider owner')
    return changed.replace(ORIGINAL, DECLARATIONS + '\n' + SELECTED)


def guard_bytes(before, object_path):
    from tools.experiments import game_actor_renderer_matching as renderer
    reader = csv.DictReader(io.StringIO(before.decode()))
    if any(row['function'] in (FUNCTION, renderer.FUNCTION) for row in reader):
        raise ValueError('color or renderer guard rows already installed')
    tail = io.StringIO()
    writer = csv.DictWriter(tail, fieldnames=reader.fieldnames, lineterminator='\n')
    writer.writerows(renderer.guard_rows(object_path))
    return before + tail.getvalue().encode()
