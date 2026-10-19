"""Bind the compiler's eight-case switch to its retained retail data owner."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_mode_context_init_candidates as source
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object

CANONICAL_SHA = '75900d393e6234dc3f400483d56b7b91df70214d6d1ab8d83ce58887efca14b4'
ANCHOR = 'jtbl_8009DA24_game'
TARGETS = (124, 88, 76, 112, 100, 160, 136, 148)
NEIGHBORS = {'func_1508E6D0': 0x18, 'func_1508E780': 0x2C}
BINDINGS = {8: [('R_MIPS_HI16', 'D_800D2E48')], 12: [('R_MIPS_LO16', 'D_800D2E48')],
    16: [('R_MIPS_26', 'func_1509B570')], 0x38: [('R_MIPS_HI16', '.rodata')],
    0x40: [('R_MIPS_LO16', '.rodata')], 0xB4: [('R_MIPS_26', 'func_1508BC20')],
    0xCC: [('R_MIPS_HI16', 'D_800E0BD0')], 0xD8: [('R_MIPS_LO16', 'D_800E0BD0')],
    0xDC: [('R_MIPS_HI16', 'D_800872B0')], 0x124: [('R_MIPS_LO16', 'D_800872B0')],
    0x118: [('R_MIPS_HI16', 'D_800872F8')], 0x128: [('R_MIPS_LO16', 'D_800872F8')],
    0x3B4: [('R_MIPS_HI16', 'D_800872F0')], 0x3C0: [('R_MIPS_LO16', 'D_800872F0')]}
for _at in (0x4C, 0x58, 0x64, 0x70, 0x7C, 0x88, 0x94, 0xA0, 0xBC):
    BINDINGS[_at] = [('R_MIPS_HI16', 'D_800D23B0')]
    BINDINGS[_at + (4 if _at in (0xA0, 0xBC) else 8)] = [('R_MIPS_LO16', 'D_800D23B0')]


def normalize(raw, bindings):
    if len(raw) != 988 or bindings != BINDINGS:
        raise ValueError('Unknown mode-context switch bindings')
    words = list(struct.unpack('>247I', raw))
    if words[0x38 // 4] != 0x3C010000 or words[0x40 // 4] not in (0x8C2E0000, 0x8C2E0008):
        raise ValueError('Unknown mode-context table addend')
    words[0x40 // 4] &= 0xFFFF0000
    canonical = struct.pack('>247I', *words)
    if hashlib.sha256(canonical).hexdigest() != CANONICAL_SHA:
        raise ValueError('Changed mode-context source instructions')
    moved = {at: list(entries) for at, entries in bindings.items()}
    moved[0x38], moved[0x40] = [('R_MIPS_HI16', ANCHOR)], [('R_MIPS_LO16', ANCHOR)]
    return canonical, moved


def check_pools(before, after):
    a, b = normalized_pools(before), normalized_pools(after)
    if a['.data'] != b['.data']:
        raise ValueError('Mode-context changed owner data')
    aa, bb = a['.rodata'], b['.rodata']
    new_table = [row for row in bb[1] if row[1] == source.FUNCTION]
    if new_table != [(8 + i * 4, source.FUNCTION, value) for i, value in enumerate(TARGETS)]:
        raise ValueError('Mode-context compiler table targets differ from retail')
    retained = tuple((at - 32 if at >= 40 else at, name, offset) for at, name, offset in bb[1]
        if name != source.FUNCTION)
    if bb[0][:8] + bb[0][40:] != aa[0] or retained != aa[1]:
        raise ValueError('Mode-context changed another relocation-owned pool')
    return dict(new_table_bytes=32, new_table_offset=8, old_pool_bytes=len(aa[0]),
        new_pool_bytes=len(bb[0]), all_existing_pool_bytes_and_owners_fixed=True)


def function_view(obj, name):
    text, functions, bindings = parse_object(obj)
    f = functions[name]
    return text[f['value']:f['value'] + f['size']], {at - f['value']: entries for at, entries in bindings.items()
        if f['value'] <= at < f['value'] + f['size']}


def qualify_neighbors(before, after):
    for name, at in NEIGHBORS.items():
        a, ar = function_view(before, name)
        b, br = function_view(after, name)
        if ar != br or ar.get(at) != [('R_MIPS_LO16', '.rodata')]:
            raise ValueError('Changed context-neighbor relocation identity')
        expected = bytearray(a)
        old, new = struct.unpack_from('>I', a, at)[0], struct.unpack_from('>I', b, at)[0]
        if new != old + 32:
            raise ValueError('Context-neighbor pool addend is not exactly32')
        struct.pack_into('>I', expected, at, new)
        if bytes(expected) != b:
            raise ValueError('Changed another context-neighbor instruction')
    return 2


def guard_bytes(before, normal, primary_before, primary_after):
    check_pools(primary_before, primary_after)
    qualify_neighbors(primary_before, primary_after)
    raw, bindings = source.payload(normal)
    normalized, moved = normalize(raw, bindings)
    reader = csv.DictReader(io.StringIO(before.decode()))
    rows, fields = list(reader), reader.fieldnames
    if any(row['filename'] == source.OWNER and row['function'] == source.FUNCTION for row in rows):
        raise ValueError('Mode-context guards already exist')
    newline = '\r\n' if before.endswith(b'\r\n') else '\n'
    def serialize(row):
        out = io.StringIO(newline='')
        csv.DictWriter(out, fieldnames=fields, lineterminator=newline).writerow(row)
        return out.getvalue().encode()
    result = before
    for name, at in NEIGHBORS.items():
        matches = [row for row in rows if row['filename'] == source.OWNER and row['function'] == name and int(row['offset'], 0) == at]
        if len(matches) != 1:
            raise ValueError('Unknown mode-context neighbor guard')
        row = matches[0]
        a, _ = function_view(primary_before, name)
        b, _ = function_view(primary_after, name)
        if int(row['expected'], 0) != struct.unpack_from('>I', a, at)[0]:
            raise ValueError('Stale mode-context neighbor guard predecessor')
        changed = dict(row, expected='0x%08X' % struct.unpack_from('>I', b, at)[0])
        old_line, new_line = serialize(row), serialize(changed)
        if result.count(old_line) != 1:
            raise ValueError('Ambiguous context-neighbor CSV serialization')
        result = result.replace(old_line, new_line, 1)
    words, replacement = struct.unpack('>247I', raw), struct.unpack('>247I', normalized)
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    for at in (0x38, 0x40):
        result += serialize(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % at,
            expected='0x%08X' % words[at // 4], replacement='0x%08X' % replacement[at // 4],
            expected_relocations=spec(bindings[at]), replacement_relocations=spec(moved[at]),
            note='Bind semantic mode-context switch to its verified retained retail table',
            insert_after='', insert_after_relocations='', omit='false'))
    return result
