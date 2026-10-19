"""Checked scheduler source origins, equivalent induction forms and live roles."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_pair_scheduler_home_candidates as homes
from tools.experiments.game_route_projection_layout_normalizer import fields as ordinary_fields, relocate

source, SELECTED = homes.source, homes.SELECTED
RAW_SHA = 'ad992aec1fad04999e4966bb07af529738e8312aaabcd1815eae3b6ea152d630'
NORMALIZED_SHA = '0125e76a6571dfb00ddaa90a4606682fd5006f7ce3068338a393823950956712'
BINDINGS = {
    0x8: [('R_MIPS_HI16', 'D_800D23B0')], 0xC: [('R_MIPS_LO16', 'D_800D23B0')],
    0x4C: [('R_MIPS_HI16', 'D_8008FD90')], 0x64: [('R_MIPS_LO16', 'D_8008FD90')],
    0x6C: [('R_MIPS_HI16', 'D_800CC2D0')], 0x88: [('R_MIPS_LO16', 'D_800CC2D0')],
    0x74: [('R_MIPS_HI16', 'D_8009DA68')], 0x78: [('R_MIPS_LO16', 'D_8009DA68')],
    0x98: [('R_MIPS_HI16', 'D_8008FD8C')], 0xA0: [('R_MIPS_LO16', 'D_8008FD8C')],
    0x20C: [('R_MIPS_26', 'func_1508C1A4')],
    0x224: [('R_MIPS_HI16', 'D_8008FD90')], 0x228: [('R_MIPS_LO16', 'D_8008FD90')],
    0x244: [('R_MIPS_HI16', 'D_800CC2D0')], 0x254: [('R_MIPS_LO16', 'D_800CC2D0')],
    0x27C: [('R_MIPS_HI16', 'D_800D18A0')], 0x280: [('R_MIPS_LO16', 'D_800D18A0')],
    0x298: [('R_MIPS_HI16', 'D_8008FD8C')], 0x29C: [('R_MIPS_LO16', 'D_8008FD8C')],
    0x380: [('R_MIPS_26', 'func_1508C1A4')],
    0x38C: [('R_MIPS_HI16', 'D_800CC2D0')], 0x390: [('R_MIPS_LO16', 'D_800CC2D0')],
}
MASKS = {0xFC, 0x1CC, 0x1F0, 0x300, 0x31C}
REMOVED = MASKS | {0x288}


def origins():
    # Materialize the source's coalesced X copies and loop/address induction.
    order = list(range(0, 0x6C, 4))
    order += [0x74, 0x70, 0x90, 0x78, 0x7C, 0x6C, 0x80, 0x84, 0x8C, 0x88,
        0x94, 0x9C, 0x98, 0xA0, 0xA4, 0xA8, 0x12C, ('copy-z', 0x12C),
        0xB0, 0xAC, ('init-test', 0x178), 0xB4, 0xB8, 0xBC, 0xC0]
    order += [0xC4, 0xC8, 0xCC, 0xD0, 0xD8, 0xD4, 0xE0, 0xDC,
        *range(0xE4, 0xFC, 4), *range(0x100, 0x11C, 4), 0x120, 0x124, 0x11C, 0x128,
        0x130, 0x134, 0x138, 0x13C, 0x140, 0x144, 0x148, 0x14C,
        ('rank-shift', 0xD4), 0x154, 0x150, ('choice-base', 0xA4),
        ('rank-choice', 0xE0), ('rank-cost', 0xDC), 0x158, 0x15C, 0x160, 0x164, 0x168,
        0x16C, 0x170, 0x188, 0x178, 0x17C, 0x180, 0x184, 0x174, 0x18C, 0x190,
        0x194, 0x198, 0x19C, 0x1A0, 0x1A4, 0x1A8, ('candidate-test', 0xC4), 0x1AC, 0x1B0]
    # Keep both ordered clears and reconstruct the two-argument call copies.
    order += [0x1B4, 0x1B8, 0x1C0, 0x1C4, 0x1C8, 0x1BC, 0x1D0, 0x1D4, 0x1D8, 0x1DC,
        0x1E0, 0x1E4, 0x1E8, 0x1EC, 0x1F4, 0x200, 0x1F8, 0x1FC,
        ('second-arg', 0x204), 0x204, 0x208, 0x20C, 0x210, 0x214, 0x218, 0x21C, 0x220,
        0x224, 0x228, 0x22C, 0x230, 0x234, 0x238, ('actor-x', 0x9C)]
    # Hoist stable background addresses, retaining every live count reload.
    order += [0x240, 0x248, 0x24C, 0x250, *range(0x258, 0x278, 4),
        0x244, 0x254, 0x278, 0x298, 0x38C, 0x27C, 0x280, 0x390,
        ('count-address', 0x29C), 0x284, 0x28C, 0x290, 0x294, 0x29C,
        *range(0x2A0, 0x300, 4), 0x304, 0x308, 0x30C, 0x310, 0x314, 0x318, 0x328,
        0x320, 0x324, 0x32C, 0x34C, 0x348, 0x330, 0x338, 0x350, 0x354, 0x334, 0x340,
        0x384, 0x33C, 0x358, 0x344, 0x35C, 0x360, 0x364,
        0x368, 0x36C, 0x370, 0x374, 0x378, 0x37C, 0x380, 0x23C,
        0x388, ('refresh-forbidden-hi', 0x27C), ('refresh-forbidden-lo', 0x280),
        0x394, 0x398, 0x39C, *range(0x3A0, 0x3FC, 4)]
    retained = [at for at in order if isinstance(at, int)]
    if len(order) != 261 or len(set(retained)) != 249 or set(retained) != set(range(0, 1020, 4)) - REMOVED:
        raise ValueError(('Scheduler origins are not closed', len(order), len(set(retained)),
            sorted(set(range(0, 1020, 4)) - set(retained)), sorted(set(retained) & REMOVED)))
    return order


def fields(word):
    op, fn = word >> 26, word & 63
    if op == 0:
        if fn in (4, 35, 36, 39, 43): return (21, 16, 11), ()
        if fn == 25: return (21, 16), ()
        if fn == 18: return (11,), ()
    if op in (10, 13): return (21, 16), ()
    if op in (53, 61): return (21,), (16,)
    return ordinary_fields(word)


def rename(word, gp=None, fp=None, overrides=None):
    result = word
    for shifts, mapping in zip(fields(word), (gp or {}, fp or {})):
        for shift in shifts:
            reg = word >> shift & 31
            result = result & ~(31 << shift) | mapping.get(reg, reg) << shift
    for shift, reg in (overrides or {}).items():
        if shift not in fields(word)[0] + fields(word)[1]:
            raise ValueError('Not a scheduler operand field')
        result = result & ~(31 << shift) | reg << shift
    return result


def allocation(old):
    gp, fp, overrides = {}, {}, {}
    if 0x44 <= old <= 0x238:
        gp.update({21: 19, 19: 18, 18: 20, 20: 21})
    if old in (0x44, 0x50, 0x54, 0x58): gp[3] = 6
    if old in (0x4C, 0x64, 0x68, 0x70, 0xC4, 0xCC): gp[4] = 3
    if old == 0x6C: gp[10] = 30
    if old == 0x88: gp[10] = 30
    if old == 0x9C: fp[16] = 12
    if old == 0xAC: gp[3] = 24
    if old in (0x98, 0xA0, 0xC4): gp[8] = 9
    if old == 0xCC: gp[5] = 4
    if old == 0xD0: gp[2] = 25
    if old == 0xD8: gp[4] = 3; overrides[11] = 7
    if old == 0xD4: gp[7] = 10
    if old == 0xDC: gp.update({2: 25, 4: 7, 6: 8})
    if old == 0xE0: gp.update({2: 25, 7: 10, 9: 11})
    if old == 0xE4: gp.update({9: 11, 24: 12})
    if old in (0xE8, 0xEC): gp.update({6: 8, 25: 13})
    if old == 0xF0: gp.update({24: 12, 25: 13})
    if old in (0xF4, 0x118, 0x168, 0x1A8): gp[5] = 4
    if 0xF8 <= old <= 0x120:
        gp.update({3: 6, 7: 10, 4: 7, 11: 14, 12: 15, 13: 4, 14: 24, 15: 25, 24: 12, 25: 13})
        if old == 0x100: overrides[21] = 4
        if old == 0x118: gp[5] = 4
    if old == 0x11C: overrides.update({11: 14, 16: 12})
    if old == 0x12C: overrides.update({11: 12, 6: 14})
    if old == 0x130: gp[25] = 13
    if old == 0x138: fp[14] = 2
    if old == 0x148: fp[14] = 2
    if old == 0x170 or old == 0x1A4: gp.update({16: 2, 3: 25})
    if old in (0x174, 0x17C, 0x184, 0x194): gp[2] = 3
    if old in (0x178, 0x180, 0x188, 0x190): gp[16] = 2
    if old == 0x178: overrides[21] = 2
    if old == 0x180: gp[5] = 4
    if old == 0x190: gp[3] = 25
    if old == 0x1B0: gp[4] = 7
    if old in (0x1B8, 0x1C0, 0x1D0, 0x1E0, 0x220): gp[5] = 6
    if old in (0x1C8, 0x1D4, 0x1EC, 0x1F8, 0x218, 0x21C): gp[11] = 12
    if old == 0x1D0: overrides[21] = 6
    if old in (0x1D8, 0x1E4): gp[12] = 14
    if old == 0x1F4: gp[12] = 14; overrides[21] = 20
    if old == 0x200: gp[12] = 14
    if old in (0x1F8, 0x1FC, 0x210): gp[2] = 3
    if old in (0x1FC, 0x208): gp[14] = 15
    if old in (0x224, 0x228, 0x234): gp[4] = 3
    if 0x240 <= old <= 0x3C4:
        gp.update({21: 19, 19: 18, 18: 20, 20: 21, 16: 19, 17: 16, 23: 11, 10: 17, 8: 9})
    if 0x258 <= old <= 0x278: gp[15] = 14
    if old in (0x244, 0x254): gp[10] = 15
    if old == 0x298: gp[8] = 23
    if old == 0x29C: overrides.update({21: 23, 16: 9})
    if old == 0x284: gp[10] = 15; gp[15] = 14
    if old in (0x290, 0x2F0, 0x378): gp[9] = 10
    if old == 0x2B4: gp[3] = 6
    if old in (0x2BC, 0x2C4, 0x2CC, 0x2D4, 0x2DC): gp[16] = 4
    if old in (0x2C0, 0x2C4): gp[24] = 12
    if old in (0x2E8, 0x2EC): gp[11] = 13
    if old in (0x2F4, 0x2F8): gp[13] = 15
    if old == 0x2F8: gp[3] = 6
    if old == 0x2FC: gp[15] = 24
    if old == 0x304: gp[12] = 25; overrides[21] = 5
    if old == 0x308: gp.update({12: 25, 14: 12})
    if old == 0x30C: gp.update({15: 24, 14: 12, 24: 13})
    if old == 0x310: gp[24] = 13
    if old in (0x314, 0x320): gp[25] = 14
    if old == 0x318: gp[11] = 15; overrides[16] = 18
    if old == 0x320: gp.update({11: 15, 2: 3})
    if old == 0x324: gp.update({2: 3, 13: 25})
    if old == 0x328: gp[12] = 24; overrides[21] = 19
    if old == 0x32C: gp.update({12: 24, 15: 12})
    if old == 0x338: gp.update({13: 25, 15: 12, 14: 13})
    if old == 0x340: gp.update({2: 3, 14: 13})
    if old == 0x344: gp[15] = 12
    if old == 0x348: gp[24] = 14
    if old == 0x34C: gp[11] = 24
    if old == 0x350: gp.update({11: 24, 12: 25}); overrides[21] = 5
    if old == 0x354: gp.update({24: 14, 25: 15}); overrides[21] = 19
    if old == 0x358: gp.update({25: 15, 12: 25, 13: 8})
    if old == 0x35C: gp.update({15: 12, 13: 8, 14: 13})
    if old == 0x360: gp[14] = 13
    if old == 0x368: overrides[21] = 18
    if old in (0x36C, 0x370): gp[24] = 14
    if old == 0x370: gp[11] = 24
    if old in (0x374, 0x378): gp.update({11: 24, 25: 15})
    if old == 0x388: gp[12] = 2
    if old in (0x394, 0x398, 0x39C): gp.update({12: 2, 15: 2})
    if old in (0x3A0, 0x3A4): gp[13] = 25
    if old in (0x3A8, 0x3AC): gp[14] = 12
    if old in (0x3B0, 0x3BC): gp[11] = 14
    if old in (0x3B4, 0x3C0): gp[24] = 13
    if old in (0x3BC, 0x3C0): gp[25] = 24
    if old in (0x3C0, 0x3C4): gp[12] = 15
    return gp, fp, overrides


def normalize(raw, bindings):
    if len(raw) != 1020 or hashlib.sha256(raw).hexdigest() != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Unknown scheduler raw instructions/bindings')
    words = struct.unpack('>255I', raw)
    for at in MASKS:
        if words[at // 4] >> 26 != 12 or words[at // 4] & 65535 != 31:
            raise ValueError('Unknown scheduler explicit shift mask')
    order = origins()
    destination = {item: i * 4 for i, item in enumerate(order) if isinstance(item, int)}
    anchors = dict(destination)
    anchors.update({0x98: destination[0x98], 0x1BC: destination[0x1C0], 0x298: destination[0x2A0],
        0x174: destination[0x188], 0x1AC: order.index(('candidate-test', 0xC4)) * 4})
    result, moved = [], {}
    for i, item in enumerate(order):
        new = i * 4
        if isinstance(item, tuple):
            role, old = item
            word = words[old // 4]
            if role == 'copy-z': word = rename(word, fp={2: 12, 14: 16})
            elif role == 'init-test': word = rename(word, overrides={21: 2, 16: 24, 11: 1})
            elif role == 'rank-shift': word = rename(word, overrides={16: 5, 11: 14})
            elif role == 'choice-base': word = rename(word, overrides={16: 24})
            elif role == 'rank-choice': word = rename(word, overrides={21: 5, 16: 24, 11: 2})
            elif role == 'rank-cost': word = rename(word, overrides={21: 14, 16: 15, 11: 3})
            elif role == 'candidate-test': word = rename(word, overrides={21: 4, 16: 9, 11: 1})
            elif role == 'second-arg': word = rename(word, overrides={21: 6, 11: 5})
            elif role == 'actor-x': word = rename(word, fp={16: 12})
            elif role == 'count-address':
                word = rename(words[0x280 // 4], overrides={21: 23, 16: 23})
                moved[new] = bindings[0x29C]
            elif role in ('refresh-forbidden-hi', 'refresh-forbidden-lo'):
                word = rename(word, {23: 11})
                moved[new] = bindings[old]
            else: raise ValueError('Unknown scheduler derived role')
            result.append(word)
            continue
        old, word = item, words[item // 4]
        if old == 0x94: word = word & 0xFFFF0000 | 0x90
        if old == 0x128: word = rename(word, overrides={21: 0, 16: 5}) & 0xFFFF0000 | 2
        if old == 0x150: word = rename(word, overrides={16: 15}) & 0xFFFF0000 | 0x80
        if old == 0x16C: word = rename(words[0x194 // 4], overrides={21: 3})
        if old == 0x17C: word = word & 0xFFFF0000 | 4
        if old == 0x180: word = word & 0xFFFF0000 | 1
        if old == 0x184: word &= 0xFFFF0000
        if old in (0xBC, 0x1AC): word = rename(word, overrides={21: 1, 16: 0})
        if old in (0x238, 0x360): word = word & 0x03FFFFFF | 21 << 26
        if old == 0x378: word = word & 0x03FFFFFF | 20 << 26
        if old in (0x364, 0x37C): word = words[0x29C // 4]
        op, rs = word >> 26, word >> 21 & 31
        if op in (4, 5, 6, 7, 20, 21) or op == 17 and rs == 8:
            original = words[old // 4]
            target = old + 4 + (((original & 65535) ^ 32768) - 32768) * 4
            word = word & 0xFFFF0000 | ((anchors[target] - new - 4) // 4) & 65535
        if old in (0x29C, 0x364, 0x37C):
            word = rename(word, overrides={21: 23, 16: 9}) & 0xFFFF0000
        else:
            word = rename(word, *allocation(old))
        if old in (0x1C0, 0x284):
            a, b = word >> 21 & 31, word >> 16 & 31
            word = word & ~((31 << 21) | (31 << 16)) | a << 16 | b << 21
        result.append(word)
        if old in bindings and old != 0x29C: moved[new] = bindings[old]
    result = struct.pack('>261I', *result)
    if hashlib.sha256(result).hexdigest() != NORMALIZED_SHA or len(moved) != 24:
        raise ValueError('Changed scheduler source-origin recipe')
    return result, moved


def private_guards(before, raw, bindings):
    normalized, moved = normalize(raw, bindings)
    old, new = struct.unpack('>255I', raw), struct.unpack('>261I', normalized)
    reader = csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(row['filename'] == source.OWNER and
            row['function'] == source.FUNCTION for row in reader):
        raise ValueError('Unknown scheduler guard predecessor')
    order, inserted, last = origins(), set(), -2
    # CSV has one insert-after cell per row. Group consecutive derived forms
    # with adjacent retained outputs without changing the recipe's output order.
    for i, item in enumerate(order):
        if isinstance(item, tuple):
            at = max(i, last + 2)
            inserted.add(at)
            last = at
    if len(inserted) != 12 or 0 in inserted or max(inserted) >= 261:
        raise ValueError('Unknown scheduler guard insertion grouping')
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    rows, cursor = [], 0
    for i, word in enumerate(old):
        at, omitted = i * 4, i * 4 in REMOVED
        added = not omitted and cursor + 1 in inserted
        if not omitted and cursor in inserted:
            raise ValueError('Unpaired scheduler output insertion')
        rows.append(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % at,
            expected='0x%08X' % word, replacement='0x%08X' % (0 if omitted else new[cursor]),
            expected_relocations=spec(bindings.get(at, [])),
            replacement_relocations='-' if omitted else spec(moved.get(cursor * 4, [])),
            note='Omit redundant five-bit shift mask or mirrored first cursor' if omitted else
                'Normalize checked scheduler origin %s' % (order[cursor],),
            insert_after='0x%08X' % new[cursor + 1] if added else '',
            insert_after_relocations=spec(moved.get((cursor + 1) * 4, [])) if added else '',
            omit='true' if omitted else 'false'))
        if not omitted: cursor += 2 if added else 1
    if cursor != 261 or sum(bool(row['insert_after']) for row in rows) != 12:
        raise ValueError('Scheduler output/guard extent differs')
    output = io.StringIO(newline='')
    csv.DictWriter(output, fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before + output.getvalue().encode()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--diff', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / (homes.BUILD + '/layout')
    values = source.freeze(root, out)
    obj, _, row = source.compile_candidate(root, out, 'selected', SELECTED)
    raw, bindings = source.payload(obj)
    normalized, moved = normalize(raw, bindings)
    anchors = {name: int(name[2:], 16) if name.startswith('D_') else int(name[5:], 16)
        for entries in moved.values() for _, name in entries}
    words = relocate(normalized, moved, anchors)
    truth = struct.unpack_from('>261I', values['conker/conker.us.bin'], source.ROM)
    different = [(i * 4, '%08X' % a, '%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b]
    receipt = dict(raw={k: v for k, v in row.items() if k != 'bindings'}, differences=len(different),
        normalized_SHA256=hashlib.sha256(normalized).hexdigest(), retained_origins=249,
        derived_words=12, bindings=len(moved))
    (out / 'layout.json').write_text(json.dumps(dict(receipt, remaining=different), indent=2) + '\n')
    print(json.dumps(receipt, indent=2), flush=True)
    if args.diff: print(json.dumps(different, indent=2))
