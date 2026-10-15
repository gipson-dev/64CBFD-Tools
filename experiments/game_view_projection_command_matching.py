"""Private expected-input recipe for the emitted view command's final schedule."""
import hashlib
import struct

from tools.experiments import game_view_projection_command_candidates as source
from tools.experiments import game_view_projection_command_fitting as fitting
from tools.pad_generated_object import parse_object

SELECTED = fitting.product_view(dict(source.variants())[source.SELECTED_LABEL]).replace(
    '    focalExtent = cosineX *', '    cosineY = cosineX;\n    focalExtent = cosineY *', 1)
RAW_SHA256 = '6211a87ecaf16433a4ecc7ab63855ab0a5ce080409d07f112db4b0300966188b'
RELOCATIONS = {
    8: [('R_MIPS_HI16', 'D_800BE628')], 24: [('R_MIPS_LO16', 'D_800BE628')],
    12: [('R_MIPS_HI16', 'D_800C3648')], 20: [('R_MIPS_LO16', 'D_800C3648')],
    84: [('R_MIPS_HI16', 'D_800A2C24')], 136: [('R_MIPS_LO16', 'D_800A2C24')],
    152: [('R_MIPS_26', 'cosf')], 164: [('R_MIPS_26', 'sinf')],
    180: [('R_MIPS_HI16', 'D_800A2C28')], 240: [('R_MIPS_LO16', 'D_800A2C28')],
    256: [('R_MIPS_26', 'cosf')], 268: [('R_MIPS_26', 'sinf')],
    284: [('R_MIPS_HI16', 'D_800C364C')], 344: [('R_MIPS_LO16', 'D_800C364C')],
    380: [('R_MIPS_HI16', 'D_800D9B20')], 400: [('R_MIPS_LO16', 'D_800D9B20')],
    404: [('R_MIPS_HI16', 'D_800C3650')], 408: [('R_MIPS_LO16', 'D_800C3650')],
    412: [('R_MIPS_HI16', 'D_800D9B1C')], 440: [('R_MIPS_LO16', 'D_800D9B1C')],
    484: [('R_MIPS_26', 'func_1510B5F8')],
}
OUTPUT_RELOCATIONS = dict(RELOCATIONS)
OUTPUT_RELOCATIONS[132] = OUTPUT_RELOCATIONS.pop(84)
OUTPUT_RELOCATIONS[308] = OUTPUT_RELOCATIONS.pop(284)


def recipe(words, scheduling_only=False):
    data = struct.pack('>%dI' % len(words), *words)
    if hashlib.sha256(data).hexdigest() != RAW_SHA256:
        raise ValueError('Unrecognized complete view-command words')
    out = list(words)
    # Move only the independent coefficient HI through the two FOV stores.
    out[21:34] = [*words[22:34], words[21]]
    # The zero FPR and near-override HI have disjoint destinations and uses.
    out[71], out[77] = words[77], words[71]
    if scheduling_only:
        return out
    for index in (88, 104):
        word = words[index]
        assert word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 50
        left, right = word >> 11 & 31, word >> 16 & 31
        out[index] = (word & ~((31 << 11) | (31 << 16))) | (right << 11) | (left << 16)
    assert tuple(words[90:95]) == (0x45010003, 0, 0x10000008, 0x46006386, 0x46100032)
    # Taken: compare fallback in the likely delay and skip its old copy.
    # Not taken: annul that delay, retaining the override's condition/value.
    out[90], out[91] = 0x45030004, words[94]
    return out


def guard_rows(path):
    data, functions, relocations = parse_object(path)
    info = functions[source.FUNCTION]
    if info['size'] != 516:
        raise ValueError('Expected complete 129-word view command')
    words = struct.unpack_from('>129I', data, info['value'])
    relative = {offset - info['value']: uses for offset, uses in relocations.items()
        if info['value'] <= offset < info['value'] + info['size']}
    if relative != RELOCATIONS:
        raise ValueError('Unrecognized complete view-command relocations')
    output = recipe(words)
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    result = []
    for index, (old, new) in enumerate(zip(words, output)):
        before, after = relative.get(index * 4, []), OUTPUT_RELOCATIONS.get(index * 4, [])
        if old == new and before == after:
            continue
        note = ('Move independent view-command address/zero schedule' if index <= 77 else
            'Preserve commutative view-command equality operand order' if index in (88, 104) else
            'Fill likely zero-override delay with the existing fallback comparison')
        result.append(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % (index * 4),
            expected='0x%08X' % old, replacement='0x%08X' % new,
            expected_relocations=spec(before), replacement_relocations=spec(after), note=note,
            insert_after='', insert_after_relocations='', omit='false'))
    assert len(result) == 19
    return result
