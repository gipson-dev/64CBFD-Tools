"""Recover the actual projection-matrix child and qualify its parent family."""
import argparse
import hashlib
import csv
import io
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_view_projection_command_candidates as source
from tools.experiments import game_view_projection_command_matching as matching
from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-view-projection-family'
CHILD, ENTRY, ROM, WORDS = 'func_1510B5F8', 0x1510B5F8, 0x138AA8, 38
PATHS = dict(source.PATHS, perspective='conker/src/libultra/gu/guPerspectiveF.c',
    fixed_matrix='conker/src/libultra/gu/guMtxF2L.c', identity='conker/src/libultra/gu/guMtxIdentF.c')
BASELINE = dict(source.BASELINE,
    perspective='387df8e02b81f8b86a10061d63dcf5b3d382ddf81c7396657409da844dcbb70f',
    fixed_matrix='8dc30adad86698603269a11b22d46df6db940aa95048edecd0cd071470397c54',
    identity='7e8b932a1e97e84c946a008bf45dd222fa3b147987c2beeae1541e8afc104b14')

CHILD_BODY = '''/* Rebuild the float projection and convert it into the live matrix page. */
void func_1510B5F8(s32 index, u16 *normalization, f32 fovY, f32 fovX,
                  f32 nearPlane, f32 farPlane, f32 scale) {
    s32 offset = index * 0x180;

    guPerspectiveF((f32 (*)[4])(D_800BE628 + offset + 0xBC), normalization,
        fovY, fovX, nearPlane, farPlane, scale);
    guMtxF2L((f32 (*)[4])(D_800BE628 + offset + 0xBC),
        (Mtx *)(D_800BE628 + offset + D_800BE9C0 * 0x40 + 0x100));
}
'''


def recover(before, child=None, parent=None):
    if child is None:
        child = SELECTED_CHILD
    result = source.recover(before, PARENT_BODY if parent is None else parent)
    result = result.replace('s32 func_1510B5F8(', 'void func_1510B5F8(')
    lo, hi = build.function_span(result, CHILD)
    result = result[:lo] + child.rstrip() + result[hi:]
    lo, hi = build.function_span(result, 'func_1510B32C')
    wrapper = result[lo:hi]
    for name, replacement in (('arg0', 'index'), ('arg1', 'offsetX'), ('arg2', 'offsetY'), ('arg3', 'scale')):
        wrapper = re.sub(r'\b' + name + r'\b', replacement, wrapper)
    result = result[:lo] + wrapper + result[hi:]
    return result.replace("// Eight guards preserve retail's five-word float ABI and register sequence.",
        '/* Forward FOV offsets and remember the requested view settings. */')


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed projection-family baseline')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified immutable projection-family manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable projection-family input: ' + key)


def variants():
    yield 'offset', CHILD_BODY
    expressions = CHILD_BODY.replace('    s32 offset = index * 0x180;\n', '').replace('offset +', 'index * 0x180 +')
    yield 'expressions', expressions
    yield 'expressions-left', expressions.replace('D_800BE628 + index * 0x180', 'index * 0x180 + D_800BE628')
    yield 'separate-offset', CHILD_BODY.replace('s32 offset = index * 0x180;', 's32 offset;\n    offset = index * 0x180;')
    yield 'late-base', CHILD_BODY.replace('    s32 offset =', '    u8 *current;\n    s32 offset =').replace(
        '    guMtxF2L(', '    current = D_800BE628 + offset;\n    guMtxF2L(').replace(
        'guMtxF2L((f32 (*)[4])(D_800BE628 + offset + 0xBC)', 'guMtxF2L((f32 (*)[4])(current + 0xBC)').replace(
        '(Mtx *)(D_800BE628 + offset +', '(Mtx *)(current +')


SELECTED_CHILD = dict(variants())['expressions']
CHILD_RAW_SHA256 = '2f2a1ed7a1c71d148639a2b5df0964d7a76d24a7f7b449dc5766222409b3cdcb'
CHILD_RELOCATIONS = {
    24: [('R_MIPS_HI16', 'D_800BE628')], 28: [('R_MIPS_LO16', 'D_800BE628')],
    84: [('R_MIPS_26', 'guPerspectiveF')], 92: [('R_MIPS_HI16', 'D_800BE628')],
    108: [('R_MIPS_LO16', 'D_800BE628')], 96: [('R_MIPS_HI16', 'D_800BE9C0')],
    104: [('R_MIPS_LO16', 'D_800BE9C0')], 128: [('R_MIPS_26', 'guMtxF2L')],
}


def child_guard_rows(obj):
    from tools.pad_generated_object import parse_object
    data, functions, relocations = parse_object(obj)
    info = functions[CHILD]
    raw = data[info['value']:info['value'] + info['size']]
    relative = {at - info['value']: value for at, value in relocations.items()
        if info['value'] <= at < info['value'] + info['size']}
    if hashlib.sha256(raw).hexdigest() != CHILD_RAW_SHA256 or relative != CHILD_RELOCATIONS:
        raise ValueError('Unrecognized complete matrix child words/relocations')
    rows = []
    for index, expected, replacement in ((16, 0x006F2021, 0x01E32021), (29, 0x00781021, 0x03031021)):
        assert struct.unpack_from('>I', raw, index * 4)[0] == expected
        rows.append(dict(filename=source.OWNER, function=CHILD, offset='0x%X' % (index * 4),
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations='-', replacement_relocations='-',
            note='Preserve commutative matrix child address operand order',
            insert_after='', insert_after_relocations='', omit='false'))
    return rows


def guard_manifest(before, rows):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards']:
        raise ValueError('Changed projection-family guard baseline')
    lines = before.splitlines(keepends=True)
    reader = csv.DictReader(io.StringIO(before.decode()))
    cursor = 1
    chunks, removed = [lines[0]], []
    for row in reader:
        end = reader.line_num
        record = b''.join(lines[cursor:end])
        if row['filename'] == source.OWNER and row['function'] == 'func_1510B32C':
            removed.append(row)
        else:
            chunks.append(record)
        cursor = end
    if len(removed) != 8 or cursor != len(lines):
        raise ValueError('Unexpected obsolete wrapper guard records')
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames, lineterminator='\n')
    writer.writerows(rows)
    return b''.join(chunks) + output.getvalue().encode()


def parent_variants():
    for mode in range(5):
        body = matching.SELECTED
        if mode < 3:
            body = body.replace('    f32 farOverride;', '    f32 sine;\n    f32 farOverride;', 1)
            body = body.replace('    focalExtent = cosineY *', '    sine = sinf(halfAngle);\n    focalExtent = cosineY *').replace('/ sinf(halfAngle);', '/ sine;')
            if mode == 1:
                body = body.replace('    f32 sine;\n', '').replace('f32 halfAngle,', 'f32 sine, halfAngle,', 1)
            elif mode == 2:
                body = body.replace('    f32 sine;\n', '').replace('focalExtent, nearPlane, farPlane;', 'focalExtent, nearPlane, farPlane, sine;', 1)
        else:
            name = 'focalExtent' if mode == 3 else 'nearPlane'
            body = body.replace('    focalExtent = cosineY *', '    ' + name + ' = sinf(halfAngle);\n    focalExtent = cosineY *').replace('/ sinf(halfAngle);', '/ ' + name + ';')
        yield 'sequenced-%d' % mode, body


PARENT_BODY = dict(parent_variants())['sequenced-3']
PARENT_LOAD_CYCLES = {
    44: (0xC7A8003C, 0xC7A6003C), 47: (0xC446000C, 0xC448000C),
    70: (0xC7AA003C, 0xC7A8003C), 73: (0xC4480010, 0xC44A0010),
}


def parent_guard_rows(obj):
    from tools.pad_generated_object import parse_object
    data, functions, relocations = parse_object(obj)
    info = functions[source.FUNCTION]
    if info['size'] != 516:
        raise ValueError('Expected complete sequenced projection parent')
    words = list(struct.unpack_from('>129I', data, info['value']))
    relative = {at - info['value']: uses for at, uses in relocations.items()
        if info['value'] <= at < info['value'] + info['size']}
    if relative != matching.RELOCATIONS:
        raise ValueError('Unrecognized sequenced projection relocations')
    canonical = list(words)
    for index, (expected, replacement) in PARENT_LOAD_CYCLES.items():
        if words[index] != expected:
            raise ValueError('Unrecognized sequenced projection load cycle')
        canonical[index] = replacement
    fitted = matching.recipe(canonical)
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    rows = []
    for index, (before, after) in enumerate(zip(words, fitted)):
        old_uses, new_uses = relative.get(index * 4, []), matching.OUTPUT_RELOCATIONS.get(index * 4, [])
        if before != after or old_uses != new_uses:
            rows.append(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % (index * 4),
                expected='0x%08X' % before, replacement='0x%08X' % after,
                expected_relocations=spec(old_uses), replacement_relocations=spec(new_uses),
                note='Preserve certified sequenced projection load roles and emitted schedule',
                insert_after='', insert_after_relocations='', omit='false'))
    assert len(rows) == 23
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--parent-screens', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    rom = (root / 'conker/conker.us.bin').read_bytes()
    retail = struct.unpack_from('>38I', rom, ROM)
    rows = []
    if args.parent_screens:
        for label, body in parent_variants():
            obj, diagnostics = build.compile_owner(root, out, recover(before, parent=body), 'parent-' + label)
            data, functions = build.link_owner(root, out, obj, source.OWNER)
            info = functions[source.FUNCTION]
            words = struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value'])
            expected = struct.unpack_from('>129I', rom, source.ROM)
            row = dict(label=label, bytes=info['size'], frame=(-words[0] & 65535), diagnostics=diagnostics,
                differences=[(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, expected)) if a != b])
            rows.append(row)
            print(label, row['bytes'], row['frame'], len(row['differences']), diagnostics, flush=True)
        (out / 'parent-screens.json').write_text(json.dumps(rows, indent=2) + '\n')
        return
    for label, body in variants():
        obj, diagnostics = build.compile_owner(root, out, recover(before, body), label)
        data, functions = build.link_owner(root, out, obj, source.OWNER)
        info = functions[CHILD]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
        row = dict(label=label, bytes=info['size'], diagnostics=diagnostics,
            differences=[(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, retail)) if a != b],
            guards=len(parent_guard_rows(obj)))
        rows.append(row)
        print(label, info['size'], len(row['differences']), diagnostics, flush=True)
    (out / 'screens.json').write_text(json.dumps(rows, indent=2) + '\n')
    before_elf = (out / 'before-elf').read_bytes()
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    dependencies = []
    for name, entry, size in (('guPerspectiveF', 0x15047F00, 564), ('guMtxF2L', 0x150A7790, 464), ('guMtxIdentF', 0x150A7BC0, 80)):
        at = elf_slot_offset(before_elf, entry, size)
        original = rom[entry - 0x15000000 + 0x2D4B0:entry - 0x15000000 + 0x2D4B0 + size]
        current = before_elf[at:at + size]
        a, b = struct.unpack('>%dI' % (size // 4), original), struct.unpack('>%dI' % (size // 4), current)
        dependencies.append(dict(name=name, words=size // 4, word_differences=sum(x != y for x, y in zip(a, b)), slot_exact=current == original))
    (out / 'sdk-dependencies.json').write_text(json.dumps(dependencies, indent=2) + '\n')
    print(json.dumps(dependencies), flush=True)


if __name__ == '__main__':
    main()
