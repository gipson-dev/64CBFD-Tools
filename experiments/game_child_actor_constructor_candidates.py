"""Recover the complete descriptor-selected child actor constructor."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15083AC8, 0xB0F78, 182
FUNCTION, SOURCE = 'func_15083AC8', 'conker/src/game/generated_AEB40.c'
ORIGINAL = '''u8 *func_15083AC8(u8 *actor, s32 arg1, s32 arg2, s32 arg3,
    s32 arg4, s32 arg5, s32 arg6, s32 arg7, f32 scale) {
    return 0;
}'''
DECLARATIONS = '''extern u8 D_800CC2D0[];
extern u8 *D_800D1C90[];
extern s32 D_80082FA0;
extern u8 D_800C35EA, D_800C3638;
void func_1503D774(s32, s32);
void func_1503D660(s32, s32);
u8 *func_1505ED34(void);
void func_150615DC(u8 *);
u32 func_1515D480(s32);
u32 func_1515D440(void);
s32 func_150839B8();
void func_150837D4(s32, s32, s32);
s32 func_150838EC();
'''
SYMBOLS = dict(D_800CC2D0=0x800CC2D0, D_800D1C90=0x800D1C90,
    D_80082FA0=0x80082FA0, D_800C35EA=0x800C35EA, D_800C3638=0x800C3638,
    func_1503D774=0x1503D774, func_1503D660=0x1503D660,
    func_1505ED34=0x1505ED34, func_150615DC=0x150615DC,
    func_1515D480=0x1515D480, func_1515D440=0x1515D440,
    func_150839B8=0x150839B8, func_150837D4=0x150837D4,
    func_150838EC=0x150838EC)
SELECTED = '''u8 *func_15083AC8(u8 *actor, s32 attachment, s32 identity, s32 kind,
    s32 value, s32 flags, s32 inheritScale, s32 state, f32 scale) {
    u8 *created;
    u8 *cursor;
    s32 i;
    s32 mode;
    s32 active;
    u32 bits;
    u32 maskedBits;
    u32 magnitude;
    s32 parentSlot;

    func_1503D774(identity, 0);
    func_1503D660(identity, 0);
    created = func_1505ED34();
    created[0x3B] = 255 - (s32)((u32)created - (u32)D_800CC2D0) / 0x32C;
    created[0xAB] = kind;
    *(s32 *)(created + 0) = value;
    func_150615DC(created);
    parentSlot = (s32)((u32)actor - (u32)D_800CC2D0) / 0x32C + 1;
    created[0x232] = 1;
    created[0x1CA] = 1;
    created[0x125] = 255;
    /* Preserve retail's ordered status stores, including the repeated flag writes. */
    *(volatile u8 *)(created + 0x65) = parentSlot;
    *(volatile s32 *)(created + 0x5C) = attachment;
    *(volatile u8 *)(created + 0x123) = 1;
    *(volatile u8 *)(created + 4) = identity;
    bits = actor[0x66];
    *(volatile u8 *)(created + 0x66) = bits;
    maskedBits = bits & ~0x10;
    *(volatile u8 *)(created + 0x66) = maskedBits;
    *(volatile u8 *)(created + 0x66) = maskedBits;
    created[0x1DD] = actor[0x1DD];
    created[0x1DE] = actor[0x1DE];
    created[0x1DF] = actor[0x1DE];
    created[0x1E0] = actor[0x1E0];
    created[0x1E1] = actor[0x1E1];
    created[0x1E2] = actor[0x1E2];
    if (inheritScale == 0) {
        *(f32 *)(created + 0x14C) = 1.0f;
        *(f32 *)(created + 0x150) = 1.0f;
        *(f32 *)(created + 0x154) = 1.0f;
        *(f32 *)(created + 0x158) = 1.0f;
    } else {
        *(f32 *)(created + 0x14C) = *(f32 *)(actor + 0x14C);
        *(f32 *)(created + 0x150) = *(f32 *)(actor + 0x150);
        *(f32 *)(created + 0x154) = *(f32 *)(actor + 0x154);
        *(f32 *)(created + 0x158) = *(f32 *)(actor + 0x158);
    }
    created[0x101] = inheritScale;
    created[0xAC] = flags;
    func_1503D774(identity, 0);
    if (flags & 1) {
        *(u32 *)(created + 0xF8) |= 0x4000;
        magnitude = *(volatile u16 *)(D_800D1C90[identity] + 0xE);
        *(f32 *)(created + 0x270) = (f32)magnitude * *(volatile f32 *)(created + 0x14C);
    }
    mode = 0;
    if (flags & 2) {
        mode = 1;
    }
    i = 0;
    cursor = created;
    if (D_80082FA0 >= 0) {
        do {
            *(u32 *)(cursor + 0x304) = func_1515D480(1);
            i++;
            cursor += 4;
        } while (i <= D_80082FA0);
    }
    if (*(u32 *)(created + i * 4 + 0x300) != 0) {
        created[0x301] = 1;
    }
    *(u32 *)(created + 0x314) = func_1515D440();
    if (D_800C35EA == 1) {
        active = 1;
    } else {
        active = 0;
    }
    if (active) {
        D_800C3638 = 0;
    }
    func_150839B8(created, identity, 0);
    func_150837D4((s32)((u32)created - (u32)D_800CC2D0) / 0x32C, identity, 1);
    /* The unrecovered helper takes the float's raw fourth O32 argument word. */
    func_150838EC(created, state, mode, *(u32 *)&scale);
    if (active) {
        D_800C3638 = 1;
    }
    return created;
}'''


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before, body=SELECTED):
    if before.count(ORIGINAL) != 1:
        raise ValueError('stale child constructor owner')
    return before.replace(ORIGINAL, DECLARATIONS + '\n' + body)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-child-actor-constructor'
    records = []
    for name, body in (('selected', SELECTED), ('signed-bits', SELECTED.replace('u32 bits;', 's32 bits;')),
            ('mode-first', SELECTED.replace('    s32 i;\n    s32 mode;', '    s32 mode;\n    s32 i;'))):
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
