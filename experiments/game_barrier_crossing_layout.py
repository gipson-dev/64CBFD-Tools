"""Derive the crossing's closed FP lifetimes and two copy/schedule changes."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_barrier_crossing_home_fit as source
from tools.experiments.game_route_projection_layout_normalizer import relocate

RAW_SHA256 = '31eba81202d9ffdd1af9de1239885d648a65a8d769f7b0dada7b0d8ba3a2841a'
NORMALIZED_SHA256 = '9414e6459422fd632051c6a4b4a510d94d4d8b3aa01ea013df6b09f1ec5356b9'
BINDINGS = {0x34: [('R_MIPS_26', 'func_15085DA8')],
    0x3C: [('R_MIPS_HI16', 'D_80087290')], 0x40: [('R_MIPS_LO16', 'D_80087290')],
    0x58: [('R_MIPS_HI16', 'D_800D2350')], 0x60: [('R_MIPS_LO16', 'D_800D2350')]}
SIDE_ROLES = {14: 12, 20: 14, 2: 18, 18: 16, 12: 2, 16: 20}


def fp(word, *, fd=None, fs=None, ft=None):
    for value, shift in ((fd, 6), (fs, 11), (ft, 16)):
        if value is not None:
            word = (word & ~(31 << shift)) | value << shift
    return word


def rename(word, roles):
    op, fmt, fn = word >> 26, word >> 21 & 31, word & 63
    if op != 17 or fmt not in (16, 20):
        return word
    fs, ft, fd = word >> 11 & 31, word >> 16 & 31, word >> 6 & 31
    if fmt == 20 and fn == 32:
        return fp(word, fd=roles.get(fd, fd))
    if fmt == 16 and fn in (0, 1, 2, 3, 4, 6, 7):
        return fp(word, fd=roles.get(fd, fd), fs=roles.get(fs, fs),
            ft=roles.get(ft, ft) if fn < 4 else None)
    if fmt == 16 and fn in (60, 62):
        return fp(word, fs=roles.get(fs, fs), ft=roles.get(ft, ft))
    raise ValueError('Unsupported crossing FP lifetime opcode: %08X' % word)


def origins():
    order = list(range(207))
    order.pop(0x154 // 4)
    order.insert(0x1C8 // 4, None)
    for a, b in ((0x208, 0x218), (0x210, 0x220), (0x21C, 0x224)):
        order[a // 4], order[b // 4] = order[b // 4], order[a // 4]
    if len(set(order) - {None}) != 206:
        raise ValueError('Crossing source-origin accounting failed')
    return order


def normalize(raw, bindings):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != BINDINGS:
        raise ValueError('Changed crossing raw instructions or bindings')
    old = list(struct.unpack('>207I', raw))
    if old[0] != 0x27BDFF70 or old[0x54 // 4] != 0xE7A40050 or old[0x64 // 4] != 0xC7BC0054:
        raise ValueError('Crossing frame/scalar homes are not recovered in C')
    if old[0x154 // 4] != 0x46006006 or old[0x1A0 // 4] != 0x46000407:
        raise ValueError('Unknown redundant signed-end copy')
    order = origins()
    positions = {origin: dest for dest, origin in enumerate(order) if origin is not None}
    words = []
    for dest, origin in enumerate(order):
        if origin is None:
            # C's nz = swap was copy-propagated; preserve its retail live role.
            copy = old[0x1BC // 4]
            if copy != 0x46007006:
                raise ValueError('Unknown original-normal temporary copy')
            words.append(fp(copy, fd=14, fs=0))
            continue
        at = origin * 4
        word = old[origin]
        if 0xE8 <= at <= 0x1C4:
            if at == 0x1A0:
                word = fp(word, fs=12)
            word = rename(word, SIDE_ROLES)
        elif at == 0x1C8:
            word = rename(word, {18: 16})
        elif 0x1CC <= at <= 0x22C:
            roles = {14: 12, 12: 0, 18: 16, 16: 20}
            if at >= 0x1DC:
                roles[0] = 14
            word = rename(word, roles)
        elif 0x230 <= at <= 0x2A4:
            word = rename(word, {18: 16, 16: 20})
        target = dest * 4
        # Exchange the two finite signed-coordinate products as closed triples.
        if target == 0x208:
            word = fp(word, fs=8)
        elif target == 0x210:
            word = fp(word, fd=10, fs=8)
        elif target == 0x218:
            word = fp(word, fs=6)
        elif target == 0x220:
            word = fp(word, fd=8, fs=6)
        elif target == 0x21C:
            word = fp(word, fd=4, fs=10, ft=12)
        elif target == 0x224:
            word = fp(word, fd=10, fs=14, ft=8)
        op = word >> 26
        if at == 0xA4:
            rs, rt = word >> 21 & 31, word >> 16 & 31
            if (op, rs, rt) != (4, 3, 31):
                raise ValueError('Unknown commutative neighbor-sentinel branch')
            word = (word & ~((31 << 21) | (31 << 16))) | rt << 21 | rs << 16
        if op in (1, 4, 5, 6, 7, 20, 21, 22, 23) or op == 17 and word >> 21 & 31 == 8:
            immediate = word & 65535
            offset = immediate if immediate < 32768 else immediate - 65536
            old_target = origin + 1 + offset
            if old_target not in positions:
                raise ValueError('Branch into omitted crossing word')
            word = (word & 0xFFFF0000) | ((positions[old_target] - dest - 1) & 65535)
        words.append(word)
    moved = {positions[at // 4] * 4: value for at, value in bindings.items()}
    if moved != bindings:
        raise ValueError('Unexpected crossing binding movement')
    result = struct.pack('>207I', *words)
    if hashlib.sha256(result).hexdigest() != NORMALIZED_SHA256:
        raise ValueError('Changed crossing derived FP/copy/schedule recipe')
    return result, moved


def private_guards(before, raw, bindings):
    normalized, moved = normalize(raw, bindings)
    old, new = struct.unpack('>207I', raw), struct.unpack('>207I', normalized)
    reader = csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(row['filename'] == source.OWNER and
            row['function'] == source.FUNCTION for row in reader):
        raise ValueError('Unknown crossing guard predecessor')
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    rows, cursor, order = [], 0, origins()
    for i, word in enumerate(old):
        at, omitted = i * 4, i * 4 == 0x154
        inserted = not omitted and cursor + 1 < 207 and order[cursor + 1] is None
        origin = None if omitted else order[cursor]
        rows.append(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % at,
            expected='0x%08X' % word, replacement='0x%08X' % (0 if omitted else new[cursor]),
            expected_relocations=spec(bindings.get(at, [])),
            replacement_relocations='-' if omitted else spec(moved.get(cursor * 4, [])),
            note='Omit redundant signed-end copy; NEG reads the live end register' if omitted else
                'Normalize proven crossing FP/copy/schedule; source word 0x%X' % (origin * 4),
            insert_after='0x%08X' % new[cursor + 1] if inserted else '',
            insert_after_relocations='-' if inserted else '', omit='true' if omitted else 'false'))
        if not omitted:
            cursor += 2 if inserted else 1
    if cursor != 207 or sum(r['omit'] == 'true' for r in rows) != 1 or sum(bool(r['insert_after']) for r in rows) != 1:
        raise ValueError('Changed crossing guard origin accounting')
    output = io.StringIO(newline='')
    csv.DictWriter(output, fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before + output.getvalue().encode()


def main():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    out = root / source.BUILD
    obj, _, row = source.compile_candidate(root, out)
    raw, bindings = source.payload(obj)
    normalized, moved = normalize(raw, bindings)
    truth = source.freeze(root, out)['conker/conker.us.bin'][source.ROM:source.ROM + 828]
    anchors = {name: int(name[2:], 16) if name.startswith('D_') else int(name[5:], 16)
        for entries in moved.values() for _, name in entries}
    linked = relocate(normalized, moved, anchors)
    differences = [hex(i * 4) for i, (a, b) in enumerate(zip(linked,
        struct.unpack('>207I', truth))) if a != b]
    (out / 'normalized.bin').write_bytes(normalized)
    print(json.dumps(dict(raw=row, normalized_SHA256=hashlib.sha256(normalized).hexdigest(),
        normalized_differences=differences), indent=2))


if __name__ == '__main__':
    main()
