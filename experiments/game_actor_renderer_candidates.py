"""Recover the complete eight-argument renderer before closing its private layout."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502CCFC, 0x5A1AC, 532
FUNCTION, SOURCE = 'func_1502CCFC', 'conker/src/game/generated_58F80.c'
ORIGINAL = 's32 func_1502CCFC() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 D_800CC2D0[], D_800BE9C0, D_800D9900, D_800DD2E4[];
extern u8 *D_800B0DF0;
extern s32 D_800DCD7C;
extern u16 D_800C4778[];
extern Gfx **D_800C48F0[], **D_800C4488[];
extern Gfx D_80084160[], D_80084190[], D_800832C0[], D_80082FC0[], D_80083140[];
extern Mtx D_800C3E98, D_C3E98;
extern u8 D_800D9E28[];
s32 func_150849CC(u8 *, s32 *);
s32 func_1503DA9C(u8 *, s32, s32, s32);
Gfx *func_1502F01C(Gfx *, s32);
Gfx *func_1502F9FC(Gfx *, s32);
void func_1502CC34(u8 *, s32, s32, s32 *, s32 *, s32 *, s32 *,
    s32 *, s32 *, s32 *, s32 *, s32 *, s32 *, s32 *);
Gfx *func_1515D914(Gfx *, s32, s32, s32, s32, s32, s32, s32,
    u8 *, u8 *, s32, u8 *, s32, u8 *);
void func_151EFE88(Mtx *);
void func_1502FD70(u8 *);
Gfx *func_15030F94(Gfx *, u8 *, s32, s32);
'''
SYMBOLS = {name: int(name[2:], 16) for name in (
    'D_800CC2D0', 'D_800BE9C0', 'D_800D9900', 'D_800DD2E4', 'D_800B0DF0',
    'D_800DCD7C', 'D_800C4778', 'D_800C48F0', 'D_800C4488', 'D_80084160',
    'D_80084190', 'D_800832C0', 'D_80082FC0', 'D_80083140', 'D_800C3E98', 'D_800D9E28')}
SYMBOLS.update({name: int(name[5:], 16) for name in (
    'func_150849CC', 'func_1503DA9C', 'func_1502F01C', 'func_1502F9FC',
    'func_1502CC34', 'func_1515D914', 'func_151EFE88', 'func_1502FD70', 'func_15030F94')})
SYMBOLS['D_C3E98'] = 0xC3E98
SELECTED = '''Gfx *func_1502CCFC(Gfx *commands, s32 slot, s32 view, u8 *matrix,
    s32 alpha, s32 *parameters, s32 mode, s32 extra) {
    u8 *actor;
    s32 identity, tier;
    s32 primitiveR, primitiveG, primitiveB;
    s32 environmentR, environmentG, environmentB;
    s32 fogR, fogG, fogB, fogA;
    s32 enabled, lighting, flags, colorState, part;
    s32 page;

    actor = D_800CC2D0 + (u32)slot * 0x32C;
    identity = actor[4];
    if (mode == 3 || mode == 4 || mode == 5) {
        identity = func_150849CC(actor, &tier);
    } else {
        tier = actor[0x1C8];
    }
    if (func_1503DA9C(actor, identity, tier, mode != 3) != 0) {
        return commands;
    }
    page = D_800BE9C0;
    if (*(u8 **)(actor + 0x28C + tier * 8 + page * 4) == NULL) {
        return commands;
    }
    if (extra != 0) {
        gSPDisplayList(commands++, D_80084160);
    } else {
        gDPPipeSync(commands++);
    }
    commands = func_1502F01C(commands, slot);
    commands = func_1502F9FC(commands, slot);
    gSPSegment(commands++, 3, matrix);
    gSPSegment(commands++, 1, *(u8 **)(actor + 0x28C + tier * 8 + page * 4) - 0x38);
    func_1502CC34(actor, view, alpha, parameters, &primitiveR, &primitiveG,
        &primitiveB, &environmentR, &environmentG, &environmentB,
        &fogR, &fogG, &fogB, &fogA);
    if (mode == 5) {
        gSPSegment(commands++, 8, D_800832C0);
    } else if (mode == 3) {
        gSPSegment(commands++, 8, D_800832C0);
    } else if (alpha < 255) {
        gSPSegment(commands++, 8, D_80082FC0);
    } else {
        gSPSegment(commands++, 8, D_80083140);
    }
    gSPClearGeometryMode(commands++, G_CULL_BOTH);
    if (mode == 0) {
        gSPSetGeometryMode(commands++, G_CULL_FRONT);
    } else {
        gSPSetGeometryMode(commands++, G_CULL_BACK);
    }
    enabled = *(s16 *)(D_800B0DF0 + 0x3E);
    lighting = 1;
    if ((actor[0x66] & 0xC) == 0xC) {
        gSPSetGeometryMode(commands++, G_LIGHTING);
        gSPClearGeometryMode(commands++, 0x400000);
    } else if ((actor[0x66] & 0xC) != 8) {
        gSPClearGeometryMode(commands++, G_LIGHTING | 0x400000);
        lighting = 0;
    } else if (D_800DCD7C != 0) {
        gSPSetGeometryMode(commands++, G_LIGHTING | 0x400000);
    } else {
        gSPClearGeometryMode(commands++, G_LIGHTING | 0x400000);
        lighting = 0;
    }
    if (mode == 3) {
        gSPClearGeometryMode(commands++, G_LIGHTING | 0x400000);
        lighting = 0;
    }
    if (lighting != 0) {
        flags = 2;
        if (actor[0x2FE] == 0) {
            flags = 10;
        }
        if (D_800D9900 != 0) {
            flags |= 8;
        }
        commands = func_1515D914(commands, view, (s32)*(f32 *)(actor + 0x14),
            (s32)*(f32 *)(actor + 0x18), (s32)*(f32 *)(actor + 0x1C),
            *(s32 *)(actor + 0x184), *(s32 *)(actor + 0x304 + view * 4),
            actor[0x301], *(u8 **)(actor + 0x314) + D_800BE9C0 * 8,
            actor + 0x302, 2, actor + 0x1DD, flags, D_800D9E28);
    }
    colorState = -1;
    for (part = 0; part < D_800C4778[identity]; part++) {
        if ((*(u32 *)(actor + 0x94) & (1U << (part & 31))) != 0) {
            continue;
        }
        if ((*(u32 *)(actor + 0x98) & (1U << (part & 31))) == 0) {
            if (colorState != 0) {
                gDPPipeSync(commands++);
                colorState = 0;
                if (enabled == 0) {
                    gDPSetFogColor(commands++, fogR, fogG, fogB, fogA);
                } else {
                    gDPSetFogColor(commands++, D_800DD2E4[0], D_800DD2E4[1],
                        D_800DD2E4[2], fogA);
                }
                gDPSetPrimColor(commands++, 0xF2, 0, primitiveR, primitiveG, primitiveB, 0);
                gDPSetEnvColor(commands++, environmentR, environmentG, environmentB, alpha);
            }
        } else if (colorState != 1) {
            gDPPipeSync(commands++);
            gDPSetFogColor(commands++, 0, 0, 0, 255);
            gDPSetPrimColor(commands++, 0xF2, 0, 0, 0, 0, 0);
            gDPSetEnvColor(commands++, 0, 0, 0, 255);
            colorState = 1;
        }
        if (mode == 3) {
            if (D_800C48F0[identity] != NULL) {
                gSPDisplayList(commands++, D_800C48F0[identity][part]);
            }
        } else {
            func_151EFE88(&D_800C3E98);
            gSPMatrix(commands++, &D_C3E98,
                G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);
            gSPDisplayList(commands++, D_800C4488[identity][part]);
        }
    }
    func_1502FD70(actor);
    actor[0x2FE] = 1;
    if (mode == 0) {
        commands = func_15030F94(commands, actor, view, 1);
    }
    if (extra != 0) {
        gSPDisplayList(commands++, D_80084190);
    }
    if (mode == 0) {
        gSPGeometryMode(commands++, G_CULL_FRONT, G_CULL_BACK);
    }
    return commands;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'colors-first', SELECTED.replace('    s32 identity, tier;\n', '').replace(
        '    s32 enabled, lighting, flags, colorState, part;',
        '    s32 identity, tier;\n    s32 enabled, lighting, flags, colorState, part;')
    yield 'unused-matrices', SELECTED.replace('    u8 *actor;',
        '    Mtx unusedMatrices[2];\n    u8 *actor;')
    yield 'ordered-private-colors', SELECTED.replace(
        '    s32 primitiveR, primitiveG, primitiveB;\n'
        '    s32 environmentR, environmentG, environmentB;\n'
        '    s32 fogR, fogG, fogB, fogA;',
        '    s32 fogA, fogB, fogG, fogR;\n'
        '    s32 environmentB, environmentG, environmentR;\n'
        '    s32 primitiveB, primitiveG, primitiveR;')
    yield 'signed-slot', SELECTED.replace('(u32)slot', 'slot')
    yield 'unmasked-part', SELECTED.replace('(part & 31)', 'part')
    yield 'volatile-mode', SELECTED.replace('s32 mode, s32 extra)', 'volatile s32 mode, s32 extra)')
    yield 'volatile-mode-unmasked', SELECTED.replace('s32 mode, s32 extra)',
        'volatile s32 mode, s32 extra)').replace('(part & 31)', 'part')
    yield 'explicit-flag', SELECTED.replace(
        '    if (func_1503DA9C(actor, identity, tier, mode != 3) != 0)',
        '    if (mode == 3) { lighting = 0; } else { lighting = 1; }\n'
        '    if (func_1503DA9C(actor, identity, tier, lighting) != 0)')
    cached = SELECTED.replace('s32 mode, s32 extra)', 'volatile s32 mode, s32 extra)').replace(
        '    s32 identity, tier;', '    s32 identity, tier, selectedMode;').replace(
        '    actor = D_800CC2D0', '    selectedMode = mode;\n    actor = D_800CC2D0').replace(
        'if (mode == 3 || mode == 4 || mode == 5)',
        'if (selectedMode == 3 || selectedMode == 4 || selectedMode == 5)').replace(
        'identity = func_150849CC(actor, &tier);',
        'identity = func_150849CC(actor, &tier);\n        selectedMode = mode;').replace(
        '    if (func_1503DA9C(actor, identity, tier, mode != 3) != 0)',
        '    if (selectedMode == 3) { lighting = 0; } else { lighting = 1; }\n'
        '    if (func_1503DA9C(actor, identity, tier, lighting) != 0)').replace('(part & 31)', 'part')
    yield 'cached-early-mode', cached
    declarations = cached.split('    u8 *actor;\n', 1)[1].split('\n\n', 1)[0]
    colors = ('    s32 primitiveR, primitiveG, primitiveB;\n'
        '    s32 environmentR, environmentG, environmentB;\n'
        '    s32 fogR, fogG, fogB, fogA;')
    for name, replacement in (
            ('private-order', '    s32 tier, identity;\n'
                '    s32 colorState, selectedMode, enabled, lighting, flags, part, page;\n' + colors),
            ('private-order-flags-first', '    s32 tier, identity, colorState, flags;\n'
                '    s32 enabled, lighting, selectedMode, part, page;\n' + colors),
            ('private-order-enabled-first', '    s32 tier, identity, colorState, enabled;\n'
                '    s32 flags, lighting, selectedMode, part, page;\n' + colors),
            ('private-order-tier-last', '    s32 identity, colorState, flags, enabled;\n'
                '    s32 lighting, selectedMode, part, page;\n' + colors + '\n    s32 tier;')):
        yield name, cached.replace(declarations, replacement)


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def copied_owner(before, body=SELECTED):
    if before.count(ORIGINAL) != 1 or before.count('s32 func_1502CCFC();') != 1:
        raise ValueError('stale renderer owner')
    declarations = DECLARATIONS.replace('extern u8 D_800CC2D0[], ', 'extern u8 ').replace(
        'Gfx *func_1502F9FC(Gfx *, s32);', 'Gfx *func_1502F9FC();')
    start = declarations.index('void func_1502CC34(')
    end = declarations.index(';', start) + 1
    declarations = declarations[:start] + declarations[end:]
    changed = before.replace('s32 func_1502CCFC();',
        'Gfx *func_1502CCFC(Gfx *, s32, s32, u8 *, s32, s32 *, s32, s32);').replace(
        's32 func_1502F9FC() {', 'Gfx *func_1502F9FC() {')
    return changed.replace(ORIGINAL, declarations + '\n' + body.replace(
        'actor = D_800CC2D0 +', 'actor = (u8 *)D_800CC2D0 +'))


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-renderer'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
