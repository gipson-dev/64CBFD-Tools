"""File-free closed route-setup layout, including an explicit return-copy coalescing."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_route_record_reload as source
from tools.experiments import game_route_projection_layout_normalizer as instructions

NORMALIZED_SHA = 'b98cd565a4ce4933e954e47e5d308624944833b82f0d81ed2772e12c412a274b'
SAVED_ROLES = {23: 30, 30: 23}
SPECIAL = {25: {15: 14}, 29: {15: 14}, 31: {14: 15}, 32: {14: 15},
    72: {2: 23}, 75: {2: 23}, 76: {2: 23}, 126: {2: 12}, 129: {2: 12},
    130: {12: 13}, 131: {12: 13}, 133: {2: 14}, 135: {2: 14},
    138: {2: 14, 13: 15}, 139: {13: 15}, 140: {13: 15},
    141: {14: 24}, 143: {14: 24}, 145: {15: 25}, 147: {15: 25}}
COMMUTED = (35, 73, 75, 122)
COPY_ORIGIN, RESTORE_ORIGIN, RETURN_BRANCH, RETURN_TARGET = 74, 148, 73, 149
REJOIN_BRANCH, REJOIN_ORIGIN = 57, 72


def origins():
    order = list(range(160))
    order[70:73] = [72, 70, 71]
    order[82:85] = [83, 84, 82]
    order[113:119] = [114, 113, 117, 115, 118, 116]
    if len(order) != 160 or sorted(order) != list(range(160)):
        raise ValueError('Lost or duplicated route-setup source slot')
    return order


def fields(word):
    if word >> 26 == 0 and word & 63 == 25:
        return (21, 16), ()
    if word >> 26 == 0 and word & 63 == 18:
        return (11,), ()
    if word >> 26 == 14:
        return (21, 16), ()
    return instructions.fields(word)


def normalize(raw, bindings):
    if len(raw) != 640 or hashlib.sha256(raw).hexdigest() != source.RAW_SHA or bindings != source.BINDINGS:
        raise ValueError('Unknown complete route-setup input or bindings')
    words = struct.unpack('>160I', raw)
    order = origins()
    destination = {old: new for new, old in enumerate(order)}
    if words[COPY_ORIGIN] != 0x0040F025 or words[RESTORE_ORIGIN] != 0x8FBF003C:
        raise ValueError('Unknown coalesced after-value copy or source RA restore')
    result = []
    for new, old in enumerate(order):
        word = words[old]
        op = word >> 26
        if op in (4, 5, 6, 7, 20, 21):
            target = old + 1 + (((word & 65535) ^ 32768) - 32768)
            if old == REJOIN_BRANCH:
                if op != 4 or target != 70:
                    raise ValueError('Unknown selected-FF join branch')
                # Rejoin at the restored read/gate block, including its unused-byte read.
                target = REJOIN_ORIGIN
            if old == RETURN_BRANCH:
                if op != 4 or target != RESTORE_ORIGIN:
                    raise ValueError('Unknown taken-return branch')
                target = RETURN_TARGET
                word = word & 0x03FFFFFF | (20 << 26)
            if target not in destination:
                raise ValueError('Lost route-setup branch destination')
            delta = destination[target] - new - 1
            if not -32768 <= delta < 32768:
                raise ValueError('Route-setup branch outside signed range')
            word = word & 0xFFFF0000 | (delta & 65535)
        rename = dict(SAVED_ROLES) if 71 <= old <= 147 else {}
        rename.update(SPECIAL.get(old, {}))
        gp, fp = fields(word)
        if fp:
            raise ValueError('Unexpected route-setup FP operation')
        before = word
        for shift in gp:
            register = before >> shift & 31
            word = word & ~(31 << shift) | rename.get(register, register) << shift
        if old in COMMUTED:
            if word >> 26 not in (4, 20) and not (word >> 26 == 0 and word & 63 == 33):
                raise ValueError('Unknown commutative route-setup operation')
            rs, rt = word >> 21 & 31, word >> 16 & 31
            word = word & ~((31 << 21) | (31 << 16)) | rs << 16 | rt << 21
        if old == COPY_ORIGIN:
            # Both copy endpoints coalesce to S7; only the taken return needs RA here.
            if words[old] >> 21 & 31 != 2 or words[old] >> 11 & 31 != 30:
                raise ValueError('Unknown eliminated copy roles')
            word = words[RESTORE_ORIGIN]
        result.append(word)
    moved = {destination[at // 4] * 4: entries for at, entries in bindings.items()}
    normalized = struct.pack('>160I', *result)
    if hashlib.sha256(normalized).hexdigest() != NORMALIZED_SHA or len(moved) != 26:
        raise ValueError('Changed closed route-setup layout recipe')
    return normalized, moved


def relocate(raw, bindings, anchors):
    return instructions.relocate(raw, bindings, anchors)


def private_guards(before, raw, bindings):
    normalized, moved = normalize(raw, bindings)
    reader = csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename'] == source.source.OWNER and r['function'] == source.source.FUNCTION for r in reader):
        raise ValueError('Route-setup guards already present')
    if not before.endswith(b'\n'):
        raise ValueError('Unterminated original guard prefix')
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    rows = []
    for i, (old, new) in enumerate(zip(struct.unpack('>160I', raw), struct.unpack('>160I', normalized))):
        origin = origins()[i]
        note = 'Normalize route-setup source slot %d roles and independent schedule' % origin
        if origin == COPY_ORIGIN:
            note = 'Coalesce redundant after copy; derive taken-return RA restore from source epilogue slot 148'
        rows.append(dict(filename=source.source.OWNER, function=source.source.FUNCTION,
            offset='0x%X' % (i * 4), expected='0x%08X' % old, replacement='0x%08X' % new,
            expected_relocations=spec(bindings.get(i * 4, [])),
            replacement_relocations=spec(moved.get(i * 4, [])), note=note,
            insert_after='', insert_after_relocations='', omit='false'))
    output = io.StringIO(newline='')
    csv.DictWriter(output, fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before + output.getvalue().encode()
