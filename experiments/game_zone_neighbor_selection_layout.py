"""Checked zone-pass source origins, retained roles and address rematerialization."""

import hashlib
import struct
import csv
import io

from tools.experiments import game_zone_neighbor_selection_homes as homes
from tools.experiments import game_zone_neighbor_selection_home_integration as source
from tools.experiments.game_route_projection_layout_normalizer import fields as base_fields


BUILD = homes.BUILD + '/match'
if homes.SELECTED.count('context->threshold') != 2:
    raise ValueError('Unknown zone-query threshold source')
SELECTED = homes.SELECTED.replace('context->threshold', 'query.threshold')
RAW_SHA = 'a9dec5c02b267241ecae64bac15157893d9c320a498f8fd5d654d5a208ab477c'
NORMALIZED_SHA = '9b20e1a7ccc254a4858aed8a140c6fb819f0cfa82624c3651ca05f4b0552c9c6'
BINDINGS = {
    0x44: [('R_MIPS_HI16', 'D_800D23B0')], 0x48: [('R_MIPS_LO16', 'D_800D23B0')],
    0x4C: [('R_MIPS_HI16', 'D_8008FD8C')], 0x50: [('R_MIPS_LO16', 'D_8008FD8C')],
    0x88: [('R_MIPS_HI16', 'D_8008FD8C')], 0x8C: [('R_MIPS_LO16', 'D_8008FD8C')],
    0xA8: [('R_MIPS_HI16', 'D_800D23B0')], 0xAC: [('R_MIPS_LO16', 'D_800D23B0')],
    0xB8: [('R_MIPS_HI16', 'D_8009DA5C')], 0xBC: [('R_MIPS_LO16', 'D_8009DA5C')],
    0xD0: [('R_MIPS_HI16', 'D_800D2350')], 0xD8: [('R_MIPS_LO16', 'D_800D2350')],
    0xE4: [('R_MIPS_HI16', 'D_8008FD90')], 0xE8: [('R_MIPS_LO16', 'D_8008FD90')],
    0xF0: [('R_MIPS_HI16', 'D_800CC2D0')], 0x140: [('R_MIPS_LO16', 'D_800CC2D0')],
    0x1D0: [('R_MIPS_26', 'func_15085DA8')], 0x1E8: [('R_MIPS_26', 'func_15085DF8')],
    0x20C: [('R_MIPS_26', 'bzero')], 0x218: [('R_MIPS_26', 'func_1508B2A8')],
    0x4BC: [('R_MIPS_HI16', 'D_800D23B0')], 0x4C0: [('R_MIPS_LO16', 'D_800D23B0')],
    0x4D8: [('R_MIPS_HI16', 'D_8008FD8C')], 0x4DC: [('R_MIPS_LO16', 'D_8008FD8C')],
    0x4F4: [('R_MIPS_HI16', 'D_800D23B0')], 0x4F8: [('R_MIPS_LO16', 'D_800D23B0')],
    0x548: [('R_MIPS_HI16', 'D_8008FD8C')], 0x54C: [('R_MIPS_LO16', 'D_8008FD8C')],
    0x568: [('R_MIPS_HI16', 'D_800D23B0')], 0x56C: [('R_MIPS_LO16', 'D_800D23B0')],
}
REMOVED = {0xBC, 0xD8, 0x2C8}


def origins():
    order = [*range(0, 0x58, 4), 0x5C, 0x68, 0x64, 0x58,
             *range(0x6C, 0xB8, 4), 0xC4, 0x490, 0xC0, 0xDC,
             0xC8, 0xCC, 0xD4, 0x60, 0x208, 0xE0, 0xE4, 0xE8, 0xEC,
             0x148, 0x144, 0xF8, 0xFC, 0x100, 0x104, 0x108, 0x10C, 0x110,
             0x114, 0x128, 0x14C, 0x13C, 0xF4, 0x118, 0x11C, 0x120, 0x124,
             0x12C, 0x130, 0x134, 0xF0, 0x140, 0x138, 0x150,
             *range(0x154, 0x19C, 4), 0xB8, 0x1A0, 0x1A4, 0x19C, 0x1A8,
             *range(0x1AC, 0x1CC, 4), 0x1D4, 0x1D0, 0x1CC,
             *range(0x1D8, 0x208, 4), ('visited-copy', 0x21C),
             *range(0x20C, 0x220, 4), 0x220, 0xD0, 0x4B0, 0x224, 0x228,
             0x22C, 0x230, 0x234, 0x238, 0x23C, 0x240,
             ('remainder-copy', 0x1F8), *range(0x244, 0x2C8, 4),
             ('delay-nop', 0x160), 0x2CC, 0x2D0, ('end-base', 0xDC),
             0x2D8, 0x2E0, 0x2DC, 0x2D4, *range(0x2E4, 0x490, 4),
             0x494, 0x498, 0x49C, 0x4A0, 0x4A4, ('publication-hi', 0xD0),
             0x4A8, 0x4AC, 0x4B4, *range(0x4B8, 0x5BC, 4)]
    kept = [item for item in order if isinstance(item, int)]
    if len(order) != 369 or len(kept) != 364 or len(set(kept)) != 364 or (
            set(kept) != set(range(0, 1468, 4)) - REMOVED):
        raise ValueError(('Zone-selection origins are not closed', len(order), len(kept)))
    return order


def fields(word):
    op, rs, fn = word >> 26, word >> 21 & 31, word & 63
    if op == 0 and fn == 35:
        return (21, 16, 11), ()
    if op == 1:
        return (21,), ()
    if op in (53, 61):
        return (21,), (16,)
    if op == 17 and rs == 0:
        return (16,), (11,)
    if op in (22, 23):
        return (21,), ()
    return base_fields(word)


REGISTERS = {
    0x44: {16: 3}, 0x48: {21: 3}, 0x58: {16: 4}, 0x60: {16: 4},
    0x70: {16: 15}, 0x78: {16: 24}, 0x7C: {21: 15},
    0x80: {16: 25}, 0x84: {16: 24}, 0x90: {16: 25},
    0x98: {21: 25, 16: 8}, 0x9C: {21: 8}, 0xA4: {16: 8},
    0xB4: {16: 9}, 0xB8: {16: 1}, 0xC0: {21: 9}, 0xDC: {16: 23},
    0xD0: {16: 6}, 0xE0: {16: 10}, 0xEC: {21: 10, 16: 4},
    0xF0: {16: 15}, 0xF4: {11: 14}, 0xF8: {16: 4},
    0xFC: {21: 10, 16: 11}, 0x100: {21: 10, 16: 12},
    0x104: {21: 10, 16: 13}, 0x108: {16: 11, 11: 6},
    0x10C: {16: 12, 11: 8}, 0x110: {16: 13, 11: 10},
    0x114: {11: 6}, 0x118: {21: 14, 11: 14},
    0x11C: {16: 14, 11: 14}, 0x120: {21: 14, 11: 14},
    0x124: {16: 14, 11: 14}, 0x128: {11: 8},
    0x12C: {21: 14, 11: 14}, 0x130: {16: 14, 11: 14},
    0x134: {21: 14, 11: 14}, 0x138: {16: 14, 11: 14},
    0x13C: {11: 10}, 0x140: {21: 15, 16: 15}, 0x150: {21: 14, 16: 15},
    0x208: {16: 22}, 0x220: {16: 24}, 0x224: {21: 24},
    0x228: {21: 24, 16: 2}, 0x22C: {21: 6}, 0x234: {21: 2},
    0x23C: {11: 25}, 0x240: {16: 25}, 0x244: {11: 5},
    0x248: {21: 5, 16: 3}, 0x250: {21: 5, 16: 5},
    0x254: {16: 3, 11: 8}, 0x258: {21: 8},
    0x25C: {16: 9}, 0x260: {16: 11}, 0x264: {16: 9}, 0x268: {16: 11},
    0x2B8: {21: 7, 16: 16}, 0x2C0: {16: 12}, 0x2C4: {16: 12},
    0x2CC: {16: 13}, 0x2D0: {11: 10}, 0x2D8: {16: 13, 11: 14},
    0x2DC: {16: 10}, 0x2E0: {21: 14, 16: 15},
    0x358: {16: 11}, 0x360: {16: 11}, 0x3B8: {11: 10},
    0x3BC: {21: 10}, 0x3C0: {16: 13}, 0x3C8: {16: 13},
    0x490: {16: 30}, 0x494: {21: 30, 16: 17}, 0x498: {16: 11},
    0x4A0: {21: 11}, 0x4A8: {21: 9}, 0x4BC: {16: 13},
    0x4C0: {21: 13, 16: 13}, 0x4C4: {16: 10},
    0x4C8: {21: 13}, 0x4CC: {16: 10},
    0x514: {16: 11}, 0x518: {16: 11}, 0x520: {16: 10},
    0x538: {16: 13}, 0x540: {16: 10}, 0x544: {16: 13},
    0x550: {16: 10}, 0x558: {21: 10},
}
BYTE_WINNERS = {0x2B0, 0x344, 0x3AC, 0x414, 0x480}


def rename(word, mapping=None, overrides=None):
    result = word
    gp, fp = fields(word)
    for shift in gp:
        old = word >> shift & 31
        result = result & ~(31 << shift) | (mapping or {}).get(old, old) << shift
    for shift, reg in (overrides or {}).items():
        if shift not in gp + fp:
            raise ValueError('Not a zone-selection register operand')
        result = result & ~(31 << shift) | reg << shift
    return result


def form(words, item):
    old = item[1] if isinstance(item, tuple) else item
    word, relocation, overrides = words[old // 4], BINDINGS.get(old), {}
    if isinstance(item, tuple):
        role = item[0]
        relocation = None
        if role == 'visited-copy':
            overrides = {21: 22, 16: 0, 11: 4}
        elif role == 'remainder-copy':
            overrides = {21: 2, 16: 0, 11: 7}
        elif role == 'delay-nop':
            if word != 0:
                raise ValueError('Missing no-op source origin')
        elif role == 'end-base':
            overrides = {16: 15}
        elif role == 'publication-hi':
            overrides = {16: 9}
            relocation = BINDINGS[0xD0]
        else:
            raise ValueError('Unknown derived zone-selection form')
    else:
        if old == 0x1C4:
            word &= 0xFFFF0000
            overrides[21] = 1
            relocation = BINDINGS[0xBC]
        if old in (0x22C, 0x4A8):
            word &= 0xFFFF0000
            relocation = BINDINGS[0xD8]
        if old == 0x2C4:
            word = word & 0x03FFFFFF | 4 << 26
        if old in BYTE_WINNERS:
            # Every incoming ID is read with LBU; preserve retail's explicit cast.
            register = word >> 21 & 31
            word = 12 << 26 | register << 21 | 17 << 16 | 255
            if old == 0x2B0:
                overrides[21] = 3
        overrides.update(REGISTERS.get(old, {}))
    mapping = {21: 23, 22: 21} if 0x44 <= old < 0x574 else {}
    return rename(word, mapping, overrides), relocation


def recipe(raw, bindings):
    if len(raw) != 1468 or hashlib.sha256(raw).hexdigest() != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Unknown zone-selection source words/bindings')
    words, order = struct.unpack('>367I', raw), origins()
    destination = {item: i * 4 for i, item in enumerate(order)}
    result, moved = [], {}
    for i, item in enumerate(order):
        old = item[1] if isinstance(item, tuple) else item
        word, relocation = form(words, item)
        op, rs = word >> 26, word >> 21 & 31
        if not isinstance(item, tuple) and (op in (1, 4, 5, 6, 7, 20, 21, 22, 23) or op == 17 and rs == 8):
            target = old + 4 + (((words[old // 4] & 65535) ^ 32768) - 32768) * 4
            if old == 0x224:
                target = 0x494
            if target not in destination:
                raise ValueError('Removed zone-selection branch destination')
            word = word & 0xFFFF0000 | ((destination[target] - i * 4 - 4) // 4 & 65535)
        result.append(word)
        if relocation:
            moved[i * 4] = relocation
    return struct.pack('>369I', *result), moved


def normalize(raw, bindings):
    result, moved = recipe(raw, bindings)
    if hashlib.sha256(result).hexdigest() != NORMALIZED_SHA or len(moved) != 32:
        raise ValueError('Changed zone-selection source-origin recipe')
    return result, moved


def private_guards(before, raw, bindings):
    normalized, moved = normalize(raw, bindings)
    old, new = struct.unpack('>367I', raw), struct.unpack('>369I', normalized)
    reader = csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(row['filename'] == source.OWNER and
            row['function'] == source.FUNCTION for row in reader):
        raise ValueError('Unknown zone-selection guard predecessor')
    inserted, last = set(), -2
    order = origins()
    for i, item in enumerate(order):
        if isinstance(item, tuple):
            at = max(i, last + 2)
            inserted.add(at)
            last = at
    if len(inserted) != 5 or 0 in inserted or max(inserted) >= 369:
        raise ValueError('Changed zone-selection insertion grouping')
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    rows, cursor = [], 0
    for i, word in enumerate(old):
        at, omitted = i * 4, i * 4 in REMOVED
        added = not omitted and cursor + 1 in inserted
        if not omitted and cursor in inserted:
            raise ValueError('Unpaired zone-selection insertion')
        rows.append(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % at,
            expected='0x%08X' % word, replacement='0x%08X' % (0 if omitted else new[cursor]),
            expected_relocations=spec(bindings.get(at, [])),
            replacement_relocations='-' if omitted else spec(moved.get(cursor * 4, [])),
            note='Omit checked zone-pass cached address or coalesced sentinel' if omitted else
                 'Normalize checked zone-pass source origin %s' % (order[cursor],),
            insert_after='0x%08X' % new[cursor + 1] if added else '',
            insert_after_relocations=spec(moved.get((cursor + 1) * 4, [])) if added else '',
            omit='true' if omitted else 'false'))
        if not omitted:
            cursor += 2 if added else 1
    if cursor != 369:
        raise ValueError('Changed zone-selection guard extent')
    stream = io.StringIO(newline='')
    csv.DictWriter(stream, fieldnames=reader.fieldnames,
                   lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before + stream.getvalue().encode()
