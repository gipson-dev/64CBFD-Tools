"""Recover the actor-byte rectangle preset dispatcher without the donor ABI errors."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_random_packet_burst as previous
from tools.tests import random_packet_burst_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-rectangle-preset-dispatch'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19E040', 'func_15171600', 0x15171600, 0x19EAB0, 127
CALLEE = 0x151717FC
PATHS = previous.PATHS
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
build, POOL_ANCHOR, POOL = previous.build, previous.POOL_ANCHOR, previous.POOL
DECLARATIONS = '''extern f32 D_800A6FC0, D_800A6FC4;
void func_151717FC(u8 *actor, f32 halfWidth, f32 halfDepth, f32 offsetX,
                  f32 offsetY, f32 offsetZ, s32 kind, s32 preset,
                  s32 xCount, s32 zCount, f32 scale, u8 flags, s32 context);

'''
INITIAL = '''/* Select the rectangle debris preset from the actor's byte-sized type. */
void func_15171600(u8 *actor, u8 flags, s32 context) {
    switch (actor[0x72]) {
        case 0xEB:
            func_151717FC(actor, 400.0f, 500.0f, 0.0f, D_800A6FC0, 0.0f,
                          2, 5, 20, 20, 1.0f, flags, context);
            break;
        case 0xF6:
            func_151717FC(actor, 200.0f, 400.0f, -1800.0f, -1000.0f, -1200.0f,
                          2, 5, 4, 10, 1.0f, flags, context);
            break;
        case 0xF8:
            func_151717FC(actor, 100.0f, 160.0f, -2500.0f, D_800A6FC4, 0.0f,
                          2, 5, 4, 4, 0.5f, flags, context);
            break;
        case 0xF9:
            func_151717FC(actor, 200.0f, 100.0f, 100.0f, -300.0f, 0.0f,
                          1, 5, 4, 4, 1.0f, flags, context);
            break;
    }
}
'''
SELECTED = INITIAL
RAW_SHA256 = '44dec27557512b82f9b476f19212083ea7684fb2b68c4e1a600e65d713d9ce73'
RELOCATIONS = {80: [('R_MIPS_HI16', 'D_800A6FC0')], 88: [('R_MIPS_LO16', 'D_800A6FC0')],
    288: [('R_MIPS_HI16', 'D_800A6FC4')], 292: [('R_MIPS_LO16', 'D_800A6FC4')]}
RELOCATIONS.update({at: [('R_MIPS_26', 'func_151717FC')] for at in (160, 264, 376, 484)})


def freeze(root, out):
    with patch.multiple(previous, PATHS=PATHS, BASELINE=BASELINE):
        previous.freeze(root, out)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15171600() {\n    return 0;\n}':
        raise ValueError('Unknown rectangle-dispatch predecessor')
    marker = 'extern s32 D_800BE9F0;'
    if before.count(marker) != 1:
        raise ValueError('Unknown rectangle-dispatch declaration anchor')
    result = before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]
    return result.replace(marker, DECLARATIONS + marker, 1)


def measure(root, out, label='selected', selected=None):
    with patch.multiple(previous, recovered_owner=recovered_owner, BASELINE=BASELINE,
            FUNCTION=FUNCTION, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, PATHS=PATHS):
        return previous.measure(root, out, label, SELECTED if selected is None else selected)


def checked_object(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    relative = {at-f['value']: rows for at, rows in rel.items() if f['value'] <= at < f['value'] + f['size']}
    pools = {n: d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if f['size'] != 508 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relative != RELOCATIONS or pools != {'.rodata': POOL}:
        raise ValueError('Unknown rectangle-dispatch compiler words, bindings or pool')
    return raw, relative


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    checked_object(obj)
    if (row['words'], row['frame'], row['differences'], row['diagnostics']) != (127, 64, 0, ''):
        raise ValueError('Rectangle dispatcher is not a direct match')
    if (',' + FUNCTION + ',').encode() in (out / 'before-guards').read_bytes():
        raise ValueError('Rectangle dispatcher must not acquire instruction guards')
    return obj, out / 'qualified-padded.o', words, row


def slot_expected_image(before, rom):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown rectangle-dispatch ELF predecessor')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown rectangle-dispatch predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 508)
    result[at:at+508] = rom[ROM:ROM+508]
    struct.pack_into('>I', result, row[0]+8, 508)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=serialize_symbols(slot_expected_image((out / 'before-elf').read_bytes(), (out / 'before-retail_rom').read_bytes())),
        edge_wrapper_owner=recovered_owner((out / 'before-edge_wrapper_owner').read_text()).encode())


def serialize_symbols(initial):
    from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols, SYMBOL
    if hashlib.sha256(initial).hexdigest() != '57c50865c57901ea19d3a535e3e5df5a7e14b662c91b25eabf7a5ba98f9c2c01':
        raise ValueError('Unknown rectangle-dispatch structural prediction')
    names = ('D_800A6FC0', '.L1513145C_game_data', 'D_80098D90')
    ordered = (names[1], names[2], names[0])
    definitions = {names[0]: (0x800A6FC0, 0, 16, 0, 65521),
        names[1]: (0x1513145C, 0, 16, 0, 5), names[2]: (0x80098D90, 0, 17, 0, 65521)}
    rows = {name: (at, fields, string) for at, name, fields, string in symbol_rows(initial) if name in names}
    first = rows[names[0]][2]
    cursor, base, at0 = first, first-rows[names[0]][1][0], rows[names[0]][0]
    for i, name in enumerate(names):
        at, fields, string = rows[name]
        encoded = name.encode()+b'\0'
        if at != at0+i*SYMBOL.size or string != cursor or fields[1:] != definitions[name] or initial[string:string+len(encoded)] != encoded:
            raise ValueError('Changed rectangle-dispatch metadata cycle')
        cursor += len(encoded)
    result = bytearray(initial)
    result[first:cursor] = b''.join(name.encode()+b'\0' for name in ordered)
    cursor = first
    for i, name in enumerate(ordered):
        SYMBOL.pack_into(result, at0+i*SYMBOL.size, cursor-base, *definitions[name])
        cursor += len(name)+1
    if canonical_symbols(result) != canonical_symbols(initial) or sum(a != b for a, b in zip(result, initial)) != 53:
        raise ValueError('Changed rectangle-dispatch serialization accounting')
    return bytes(result)


def prelink_prediction(root, out):
    freeze(root, out)
    structural = slot_expected_image((out / 'before-elf').read_bytes(), (out / 'before-retail_rom').read_bytes())
    rejected = out / 'slot-only-rejected.elf'
    if not rejected.exists():
        rejected.write_bytes(structural)
    if rejected.read_bytes() != structural:
        raise ValueError('Changed rejected rectangle-dispatch slot-only prediction')
    core = previous.previous
    with patch.multiple(core, PATHS=PATHS, BASELINE=BASELINE, qualify=qualify,
            slot_expected_image=slot_expected_image, serialize_symbols=serialize_symbols):
        row = core.prelink_prediction(root, out)
    hashes = {k: hashlib.sha256(v).hexdigest() for k, v in expected_inputs(root, out).items()}
    initial = out / 'initial-prediction.json'
    if not initial.exists():
        if {k: hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()} != BASELINE:
            raise ValueError('Complete rectangle-dispatch prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2)+'\n')
    if json.loads(initial.read_text()) != hashes:
        raise ValueError('Changed rectangle-dispatch initial prediction')
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--prelink', action='store_true')
    args = parser.parse_args()
    row = prelink_prediction(args.root, args.root / BUILD) if args.prelink else qualify(args.root, args.root / BUILD)[3]
    print(json.dumps(row, indent=2))


if __name__ == '__main__':
    main()
