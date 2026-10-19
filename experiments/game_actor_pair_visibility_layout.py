"""Source-derived pair-query schedules, scoped register lifetimes and ABI copies."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_pair_visibility_home_candidates as homes
from tools.experiments.game_route_projection_layout_normalizer import fields as ordinary_fields, relocate

source = homes.source
SELECTED = dict(homes.candidates())['interleaved-points']
RAW_SHA = '3d97c584f9960d550b19e817dffc484a3cc5f1b2637fb1d8e195b40cfc3aefba'
NORMALIZED_SHA = 'e11f8cd6230774b9ebd8afdee091d3f0c8317e3b78480d6e677ab1924fa8f4c4'
BINDINGS = {
    0x28: [('R_MIPS_26', 'func_1505EEF4')], 0x44: [('R_MIPS_26', 'func_1505EEF4')],
    0xFC: [('R_MIPS_HI16', 'D_800E0BD0')], 0x10C: [('R_MIPS_LO16', 'D_800E0BD0')],
    0x110: [('R_MIPS_HI16', 'D_800872C4')], 0x120: [('R_MIPS_LO16', 'D_800872C4')],
    0x1E0: [('R_MIPS_HI16', 'D_800E0BD0')], 0x1E4: [('R_MIPS_LO16', 'D_800E0BD0')],
    0x1E8: [('R_MIPS_HI16', 'D_800872C4')], 0x1F8: [('R_MIPS_LO16', 'D_800872C4')],
    0x2D4: [('R_MIPS_26', 'func_150AC9C0')], 0x32C: [('R_MIPS_26', 'func_15086D94')],
    0x358: [('R_MIPS_HI16', 'D_800D23B0')], 0x360: [('R_MIPS_LO16', 'D_800D23B0')],
    0x3B0: [('R_MIPS_HI16', 'D_800D23B0')], 0x3B4: [('R_MIPS_LO16', 'D_800D23B0')],
}
REMOVED = {0x36C, 0x39C, 0x3D4, 0x3EC}


def cycle(*registers):
    return dict(zip(registers, (*registers[1:], registers[0])))


def fields(word):
    op, rs, fn = word >> 26, word >> 21 & 31, word & 63
    if op == 0 and fn in (4, 36):
        return (21, 16, 11), ()
    if op == 13:
        return (21, 16), ()
    if op == 17 and rs == 0:
        return (16,), (11,)
    return ordinary_fields(word)


def origins():
    # Hoist the common nested-pointer load into its likely delay slot; retain the dead duplicate.
    order = list(range(0, 0xDC, 4))
    order += [0xF8, 0xE8, 0xE0, 0xDC, 0xE4, 0xEC, 0xF0, 0xF4, ('dead-nested', 0xF8)]
    order += list(range(0xFC, 0x12C, 4))
    order += [0x12C, 0x130, 0x148, 0x134, 0x138, 0x14C, 0x13C, 0x140, 0x144, 0x150, 0x154]
    order += list(range(0x158, 0x248, 4))
    # Preserve the rounded expression tree while scheduling its independent products and arguments.
    order += [0x250, 0x254, 0x248, 0x24C, ('spill-z', 0x70), 0x25C, 0x264, 0x260, 0x270,
        0x258, 0x294, 0x278, 0x298, 0x268, 0x26C, 0x284, 0x274, 0x280, 0x288, 0x29C,
        0x28C, 0x2A0, 0x2A4, 0x290, ('reload-z', 0x254), 0x2A8, 0x2AC, 0x2B0, 0x2B4,
        0x27C, 0x2B8, 0x2C0, 0x2BC, 0x2C4, 0x2C8, 0x2CC, 0x2D0, 0x2D4, 0x2D8]
    order += list(range(0x2DC, 0x2F0, 4))
    order += [0x324, *range(0x2F4, 0x320, 4), 0x2F0, ('bridge-dx', 0x26C), 0x320, 0x330, 0x32C, 0x328]
    order += list(range(0x334, 0x354, 4))
    # Each discarded ANDI feeds only a variable shift, which already masks the count to five bits.
    order += [0x354, 0x358, 0x35C, 0x360, 0x364, 0x368, 0x378, 0x370, 0x374, 0x37C,
        0x38C, 0x380, 0x384, 0x388, 0x390, 0x3A0, 0x394, 0x398, 0x3A4, 0x3A8]
    order += [*range(0x3AC, 0x3D4, 4), 0x3D8, 0x3E8, 0x3DC, 0x3E0, 0x3E4, 0x3F8,
        0x3F0, 0x3F4, 0x3FC, 0x400, *range(0x404, 0x414, 4)]
    retained = [value for value in order if isinstance(value, int)]
    if len(order) != 261 or len(set(retained)) != 257 or set(retained) != set(range(0, 1044, 4)) - REMOVED:
        raise ValueError('Pair-query source origins are not closed')
    return order


def allocation(old):
    gp, fp = {}, {}
    if old <= 0x2D8:
        gp.update(cycle(11, 12, 13, 14, 15, 25))
    if 0x78 <= old <= 0x244:
        gp.update(cycle(5, 7, 6))
    if 0x12C <= old <= 0x154:
        gp.update(cycle(24, 11, 12, 13, 14, 15, 25))
    if 0x84 <= old <= 0xC0:
        fp.update(cycle(6, 8, 10))
    elif 0xDC <= old <= 0xF4:
        fp.update(cycle(4, 16))
        fp.update(cycle(10, 18))
    elif 0x12C <= old <= 0x154:
        fp.update(cycle(4, 10, 8, 6))
    elif 0x15C <= old <= 0x164:
        fp.update(cycle(6, 4))
        fp.update(cycle(8, 10))
    elif 0x168 <= old <= 0x178:
        fp.update(cycle(10, 6))
        fp.update(cycle(4, 8))
    elif 0x17C <= old <= 0x1B8:
        fp.update(cycle(4, 8, 10, 6))
    elif 0x1CC <= old <= 0x1D8:
        fp.update(cycle(6, 10))
    elif 0x208 <= old <= 0x244:
        fp.update(cycle(6, 8, 10))
    if old in (0x258, 0x264, 0x26C, 0x280, 0x28C, 0x298, 0x2F0, 0x328):
        fp.update(cycle(6, 18))
    if old in (0x268, 0x294):
        fp.update(cycle(6, 18))
        fp.update(cycle(4, 8))
    if old == 0x274:
        fp.update(cycle(8, 10))
    if old == 0x290:
        fp.update(cycle(4, 8, 10))
    if old in (0x2B0, 0x2B4, 0x2D0, 0x2FC, 0x304):
        fp.update(cycle(4, 8))
    if old in (0x334, 0x340):
        fp.update(cycle(6, 8))
    if old >= 0x354:
        gp.update(cycle(2, 3, 4, 5, 6) if 0x394 <= old <= 0x3A8 or 0x3F0 <= old <= 0x400 else cycle(3, 4, 5, 6))
        if old in (0x368, 0x370):
            gp.update(cycle(25, 11))
        if 0x38C <= old <= 0x3A8:
            gp.update(cycle(24, 25))
        if old in (0x394, 0x398, 0x3A0, 0x3A4, 0x3A8):
            gp.update(cycle(10, 12, 13))
        if old in (0x3AC, 0x3B8):
            gp.update(cycle(14, 13))
        if 0x3C0 <= old <= 0x3E8:
            gp.update(cycle(15, 14, 10, 24))
            gp.update(cycle(11, 25))
            gp.update(cycle(13, 12))
        if 0x3F0 <= old <= 0x400:
            gp.update(cycle(11, 15, 13, 12, 14, 10, 24))
    return gp, fp


def rename(word, gp, fp):
    for shifts, mapping in zip(fields(word), (gp, fp)):
        original = word
        for shift in shifts:
            reg = original >> shift & 31
            word = word & ~(31 << shift) | mapping.get(reg, reg) << shift
    return word


def normalize(raw, bindings):
    if len(raw) != 1044 or hashlib.sha256(raw).hexdigest() != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Unknown complete pair-query source instructions/bindings')
    words = struct.unpack('>261I', raw)
    for at in REMOVED:
        if words[at // 4] >> 26 != 12 or words[at // 4] & 65535 != 31:
            raise ValueError('Unknown pair-query redundant explicit shift mask')
    order = origins()
    destination = {value: i * 4 for i, value in enumerate(order) if isinstance(value, int)}
    anchors = dict(destination)
    anchors[0xF8], anchors[0x248] = destination[0xFC], destination[0x250]
    result = []
    for i, item in enumerate(order):
        new = i * 4
        if isinstance(item, tuple):
            role, at = item
            word = words[at // 4]
            if role == 'dead-nested':
                word = rename(word, *allocation(at))
            elif role == 'spill-z':
                word = word & ~((31 << 16) | 65535) | (words[0x254 // 4] >> 16 & 31) << 16 | 0x48
            elif role == 'reload-z':
                word = word & 0xFFFF0000 | 0x48
            elif role == 'bridge-dx':
                word = rename(word, {}, cycle(6, 18))
            else:
                raise ValueError('Unknown source-derived pair-query insertion')
            result.append(word)
            continue
        old, word = item, words[item // 4]
        if old == 0xD8:
            if word >> 26 != 5:
                raise ValueError('Unknown pair-query height branch')
            word = word & 0x03FFFFFF | 21 << 26
        op, rs = word >> 26, word >> 21 & 31
        if op in (4, 5, 6, 7, 20, 21) or op == 17 and rs == 8:
            target = old + 4 + (((word & 65535) ^ 32768) - 32768) * 4
            word = word & 0xFFFF0000 | ((anchors[target] - new - 4) // 4) & 65535
        if op in (35, 49, 57) and rs == 29 and word & 65535 in (0x4C, 0x50):
            word = word & 0xFFFF0000 | {0x4C: 0x5C, 0x50: 0x58}[word & 65535]
        if old == 0x324:
            if words[old // 4] != 0x8FA7004C:
                raise ValueError('Unknown pair-query float DX ABI reload')
            word = word & 0x03E0FFFF | 49 << 26 | 18 << 16
        if old in (0x37C, 0x3D8):
            word = word & ~(31 << 21) | 9 << 21
        if old in (0x3A0, 0x3F8):
            word = word & ~(31 << 21) | 5 << 21
        word = rename(word, *allocation(old))
        if old in (0xB0, 0x1A8):
            a, b = word >> 11 & 31, word >> 16 & 31
            word = word & ~((31 << 11) | (31 << 16)) | a << 16 | b << 11
        result.append(word)
    moved = {destination[at]: entries for at, entries in bindings.items()}
    if len(moved) != 16:
        raise ValueError('Lost pair-query source relocation')
    result = struct.pack('>261I', *result)
    if hashlib.sha256(result).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Changed pair-query source-derived layout recipe')
    return result, moved


def private_guards(before, raw, bindings):
    normalized, moved = normalize(raw, bindings)
    old, new = struct.unpack('>261I', raw), struct.unpack('>261I', normalized)
    reader = csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(row['filename'] == source.OWNER and
            row['function'] == source.FUNCTION for row in reader):
        raise ValueError('Unknown pair-query guard predecessor')
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    rows, cursor, order = [], 0, origins()
    for i, word in enumerate(old):
        at, omitted = i * 4, i * 4 in REMOVED
        inserted = not omitted and cursor + 1 < 261 and isinstance(order[cursor + 1], tuple)
        origin = None if omitted else order[cursor]
        if not omitted and not isinstance(origin, int):
            raise ValueError('Pair-query insertion is not paired with a retained output')
        rows.append(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % at,
            expected='0x%08X' % word, replacement='0x%08X' % (0 if omitted else new[cursor]),
            expected_relocations=spec(bindings.get(at, [])),
            replacement_relocations='-' if omitted else spec(moved.get(cursor * 4, [])),
            note='Omit explicit count mask; MIPS SLLV retains the same five low count bits' if omitted else
                'Normalize derived pair-query allocation and schedule; source word 0x%X' % origin,
            insert_after='0x%08X' % new[cursor + 1] if inserted else '',
            insert_after_relocations='-' if inserted else '', omit='true' if omitted else 'false'))
        if not omitted:
            cursor += 2 if inserted else 1
    if cursor != 261 or sum(row['omit'] == 'true' for row in rows) != 4 or sum(bool(row['insert_after']) for row in rows) != 4:
        raise ValueError('Changed pair-query guard origin accounting')
    output = io.StringIO(newline='')
    csv.DictWriter(output, fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before + output.getvalue().encode()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--diff', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / homes.BUILD / 'layout'
    values = source.freeze(root, out)
    obj, _, row = source.compile_candidate(root, out, 'selected', SELECTED)
    raw, bindings = source.payload(obj)
    normalized, moved = normalize(raw, bindings)
    names = {name: int(name[2:], 16) if name.startswith('D_') else int(name[5:], 16)
        for entries in moved.values() for _, name in entries}
    words = relocate(normalized, moved, names)
    truth = struct.unpack_from('>261I', values['conker/conker.us.bin'], source.ROM)
    differences = [(i * 4, '%08X' % a, '%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b]
    receipt = dict(raw={k: v for k, v in row.items() if k != 'bindings'}, differences=len(differences),
        normalized_SHA256=hashlib.sha256(normalized).hexdigest(), unique_retained_source_origins=257, derived_words=4,
        relocation_bindings=len(moved))
    (out / 'layout.json').write_text(json.dumps(dict(receipt, remaining=differences), indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    if args.diff:
        print(json.dumps(differences, indent=2))
