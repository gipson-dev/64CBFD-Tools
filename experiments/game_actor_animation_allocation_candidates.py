"""Full animation-state allocation and mixed O32 float/home reload contract."""
import itertools
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x150838EC, 0xB0D9C, 51
FUNCTION, SOURCE = 'func_150838EC', 'conker/src/game/generated_AEB40.c'
ORIGINAL = 's32 func_150838EC() {\n    return 0;\n}'
DECLARATIONS = '''extern u32 D_800D1588[];
extern u16 D_800C5A90[];
void *allocate_memory(s32, s32, s32, s32);
void func_1505E650(u8 *, u16, f32, f32, f32, f32, s32);
'''
SYMBOLS = dict(D_800D1588=0x800D1588, D_800C5A90=0x800C5A90,
    allocate_memory=0x10003C40, bzero=0x100226F0, func_1505E650=0x1505E650)
SELECTED = '''s32 func_150838EC(u8 *actor, s32 state, s32 mode, f32 scale) {
    s32 identity;
    u8 *allocated;
    u8 *destination;

    identity = actor[4];
    if (D_800D1588[identity] == 0) {
        return 0;
    }
    if (D_800C5A90[identity] == 0) {
        return 0;
    }
    allocated = allocate_memory(0x3E0, 1, 2, 0);
    destination = actor;
    *(u8 **)(destination + 0x2D0) = allocated;
    if (allocated == NULL) {
        return 1;
    }
    bzero(*(u8 **)(destination + 0x2D0), 0x40);
    func_1505E650(actor, (u16)state, scale, 0.0f, 0.0f, 0.0f, mode);
    return 0;
}'''


def candidates():
    yield 'selected', SELECTED
    for volatile_actor, volatile_state, volatile_mode, volatile_scale in itertools.product((False, True), repeat=4):
        body = SELECTED
        if volatile_actor: body = body.replace('u8 *actor', 'u8 * volatile actor')
        if volatile_state: body = body.replace('s32 state', 'volatile s32 state')
        if volatile_mode: body = body.replace('s32 mode', 'volatile s32 mode')
        if volatile_scale: body = body.replace('f32 scale', 'volatile f32 scale')
        yield 'homes-%d%d%d%d' % (volatile_actor, volatile_state, volatile_mode, volatile_scale), body
    for width in ('u32', 'u16', 's16'):
        yield 'state-'+width, SELECTED.replace('s32 state', width+' state')
    yield 'repeated-actor', SELECTED.replace('    u8 *destination;\n', '').replace(
        '    destination = actor;\n', '').replace('destination +', 'actor +')
    yield 'raw-scale', SELECTED.replace('f32 scale', 'u32 scale').replace(
        'state, scale,', 'state, *(f32 *)&scale,')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before, body=SELECTED):
    if before.count(ORIGINAL) != 1 or before.count('s32 func_150838EC();') != 1:
        raise ValueError('stale actor animation allocation owner')
    declarations = DECLARATIONS.replace('extern u16 D_800C5A90[];\n', '')
    text = before.replace(ORIGINAL, declarations+'\n'+body).replace('s32 func_150838EC();\n', '')
    old = '''    /* The unrecovered helper takes the float's raw fourth O32 argument word. */
    func_150838EC(created, state, mode, *(u32 *)&scale);'''
    if text.count(old) != 1:
        raise ValueError('stale constructor scale forwarding')
    return text.replace(old, '    func_150838EC(created, state, mode, scale);')


def main():
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-actor-animation-allocation'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
