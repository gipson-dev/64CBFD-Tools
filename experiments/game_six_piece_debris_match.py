"""Match the six-piece packet producer against the genuine, already-restored ring."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_six_piece_debris as previous
from tools.tests import randomized_ring_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.pad_generated_object import emit_padded_assembly
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments import game_quad_edge_match as allocation
from tools.experiments.game_six_piece_debris_proof import prove
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols, SYMBOL
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-six-piece-debris-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS
LOOKUP, RANDOM, SUBMIT, RING = previous.LOOKUP, previous.RANDOM, previous.SUBMIT, previous.RING
PATHS, BASELINE, build = previous.PATHS, dict(previous.BASELINE, **checkpoint.AFTER), previous.build
DECLARATIONS = previous.DECLARATIONS.replace('s32 func_150ADA20(void);\n', '').replace('s32 func_151718F0(', 'void func_151718F0(')
SELECTED = previous.SELECTED


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed debris-match predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed debris-match manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed debris-match fixture: ' + key)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15170B90() {\n    return 0;\n}':
        raise ValueError('Unknown debris-match placeholder')
    result = before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]
    return result.replace('extern s32 D_800BE9F0;', DECLARATIONS + 'extern s32 D_800BE9F0;', 1)


def measure(root, out, label='selected', selected=None, flags=('-O2', '-g3')):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-edge_wrapper_owner').read_text(), selected), label, flags=flags)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM))
    pools, raw = sections(obj), parse_object(obj)
    row = dict(label=label, flags=flags, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, pool_bytes=sum(len(pools.get(n, (0, b''))[1]) for n in ('.rodata', '.data')),
        raw_sha256=hashlib.sha256(raw[0][f['value']:f['value'] + f['size']]).hexdigest(),
        stack_pointers=[(i * 4, w >> 16 & 31, w & 65535) for i, w in enumerate(words)
            if w >> 26 == 9 and w >> 21 & 31 == 29 and w >> 16 & 31 != 29],
        relocations={at - f['value']: rows for at, rows in raw[2].items() if f['value'] <= at < f['value'] + f['size']},
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def forms():
    initial = previous.SELECTED
    early = initial.replace('    coefficient = D_800A6F94;\n', '').replace(
        '    packet.rotation[0]', '    coefficient = D_800A6F94;\n    packet.rotation[0]', 1)
    array = early.replace('    f32 originX;\n    f32 originY;\n    f32 originZ;', '    f32 origin[3];')
    vector = early.replace('    f32 originX;\n    f32 originY;\n    f32 originZ;', '    struct { f32 x, y, z; } origin;')
    for old, new in zip(('originX', 'originY', 'originZ'), ('origin[0]', 'origin[1]', 'origin[2]')):
        array = array.replace(old, new)
    for old, new in zip(('originX', 'originY', 'originZ'), ('origin.x', 'origin.y', 'origin.z')):
        vector = vector.replace(old, new)
    for name, body in (('initial', initial), ('early-coefficient', early), ('origin-array', array), ('origin-vector', vector)):
        yield name, body
    flags = early.replace('u8 flags, s32 context)', 's32 flags, s32 context)').replace(
        '    s32 asset;', '    s32 asset;\n    u8 savedFlags;').replace('    index = 0;',
        '    savedFlags = flags;\n    index = 0;').replace('(&packet, flags, context)',
        '(&packet, savedFlags, context)').replace('0, 10, flags, context)', '0, 10, savedFlags, context)')
    ternary = early.replace('            kind = baseKind;\n            if (options & 1) {\n'
        '                kind = (s32)((u32)baseKind + (u32)index);\n            }',
        '            kind = options & 1 ? (s32)((u32)baseKind + (u32)index) : baseKind;')
    branch = early.replace('            kind = baseKind;\n            if (options & 1) {\n'
        '                kind = (s32)((u32)baseKind + (u32)index);\n            }',
        '            if (options & 1) {\n                kind = (s32)((u32)baseKind + (u32)index);\n'
        '            } else {\n                kind = baseKind;\n            }')
    scoped = early.replace('    DebrisKinds19E040 kinds;\n', '').replace('        if (options & 2) {',
        '        if (options & 2) {\n            DebrisKinds19E040 kinds;')
    for name, body in (('word-flags-snapshot', flags), ('ternary-kind', ternary), ('branch-kind', branch), ('scoped-kinds', scoped)):
        yield name, body


def screens(root, out):
    for name, body in forms():
        _, _, row = measure(root, out, name, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame', 'differences', 'raw_sha256')}), flush=True)


def stack_forms():
    ternary = dict(forms())['ternary-kind']
    inline = ternary.replace('    f32 x;\n    f32 y;\n    f32 z;\n', '').replace(
        '        x = vector[0];\n        y = vector[1];\n        z = vector[2];\n', '')
    for i, name in enumerate(('x', 'y', 'z')):
        inline = inline.replace('= ' + name + ' +', '= vector[%d] +' % i).replace(
            '= ' + name + ' *', '= vector[%d] *' % i).replace('fabsf(' + name + ')', 'fabsf(vector[%d])' % i)
    named = inline.replace('    DebrisPacket19E040 packet;', '    s32 randomHalf;\n    DebrisPacket19E040 packet;').replace(
        '        packet.spin[2] = (f32)(func_150ADA20() >> 16)',
        '        randomHalf = func_150ADA20() >> 16;\n        packet.spin[2] = (f32)randomHalf')
    for name, body in (('ternary-scoped', ternary), ('inline-vectors', inline), ('named-final-rng', named)):
        yield name, body
        yield name + '-scoped', body.replace('    DebrisKinds19E040 kinds;\n', '').replace(
            '        if (options & 2) {', '        if (options & 2) {\n            DebrisKinds19E040 kinds;')
    plain = named.replace('    DebrisKinds19E040 kinds;\n', '')
    for after in ('originX', 'originY', 'originZ', 'coefficient', '*vector', 'index', 'kind', 'asset'):
        line = next(line for line in plain.splitlines() if line.strip().endswith(' ' + after + ';'))
        yield 'kinds-after-' + after.lstrip('*'), plain.replace(line, line + '\n    DebrisKinds19E040 kinds;', 1)


def stack_screens(root, out):
    for name, body in stack_forms():
        _, _, row = measure(root, out, name, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame', 'differences', 'stack_pointers', 'raw_sha256')}), flush=True)


def lifetime_forms():
    scoped = dict(stack_forms())['ternary-scoped-scoped']
    for width in ('u8', 's16'):
        yield 'index-' + width, scoped.replace('    s32 index;', '    ' + width + ' index;')
    for axes in ((0,), (1,), (2,), (0, 1), (1, 2), (0, 2)):
        body = scoped
        for axis in axes:
            name = ('x', 'y', 'z')[axis]
            body = body.replace('    f32 ' + name + ';\n', '').replace(
                '        ' + name + ' = vector[%d];\n' % axis, '')
            body = body.replace('= ' + name + ' +', '= vector[%d] +' % axis).replace(
                '= ' + name + ' *', '= vector[%d] *' % axis).replace('fabsf(' + name + ')', 'fabsf(vector[%d])' % axis)
        yield 'inline-axis-' + ''.join(map(str, axes)), body
    reuse = scoped.replace('    f32 y;\n    f32 z;\n', '')
    lo, hi = reuse.index('        x = vector[0];'), reuse.index('        packet.velocity[0] +=')
    fields = '''        x = vector[0];
        packet.position[0] = x + originX;
        packet.velocity[0] = x * coefficient;
        x = vector[1];
        packet.position[1] = x + originY;
        packet.velocity[1] = fabsf(x) * coefficient + 7.0f;
        x = vector[2];
        packet.position[2] = x + originZ;
        packet.velocity[2] = x * coefficient;
        packet.kind = kind;
'''
    yield 'reused-component', reuse[:lo] + fields + reuse[hi:]


def lifetime_screens(root, out):
    for name, body in lifetime_forms():
        _, _, row = measure(root, out, name, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame', 'differences', 'stack_pointers', 'raw_sha256')}), flush=True)


def object_forms():
    reused = dict(lifetime_forms())['reused-component']
    packet = reused.replace('    DebrisPacket19E040 packet;\n', '').replace(
        '    f32 originX;', '    f32 originX;\n    DebrisPacket19E040 packet;')
    for name, body in (('packet-after-origin', packet), ('component-first', reused.replace('    f32 x;\n', '').replace(
            '    DebrisPacket19E040 packet;', '    f32 x;\n    DebrisPacket19E040 packet;'))):
        yield name, body
        yield name + '-initialized-kinds', body.replace('            DebrisKinds19E040 kinds;\n            kinds = D_800A6F80;',
            '            DebrisKinds19E040 kinds = D_800A6F80;')
        for locals_ in (('kind',), ('asset',), ('kind', 'asset')):
            inner = body
            for local in locals_:
                inner = inner.replace('    s32 ' + local + ';\n', '')
            yield name + '-inner-' + '-'.join(locals_), inner.replace('    do {', '    do {\n' +
                ''.join('        s32 ' + local + ';\n' for local in locals_), 1)
    yield 'packet-after-origin-inner-component', packet.replace('    f32 x;\n', '').replace(
        '    do {', '    do {\n        f32 x;', 1)


def object_screens(root, out):
    for name, body in object_forms():
        _, _, row = measure(root, out, name, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame', 'differences', 'stack_pointers', 'raw_sha256')}), flush=True)


SELECTED = dict(object_forms())['packet-after-origin'].replace('    f32 x;', '    f32 component;').replace(
    '        x = vector', '        component = vector').replace('= x +', '= component +').replace(
    '= x *', '= component *').replace('fabsf(x)', 'fabsf(component)').replace(
    ' * The copied packet\'s reserved bytes intentionally retain stack residue. */',
    ' * Reserved packet bytes intentionally retain stack residue. Guards normalize\n'
    ' * independent schedules, FP registers and the unescaped kind staging home. */')
RAW_SHA256 = 'd91b415ed3e526a91af1f8336972e45b26c6d016050b168fb302f6e46dc20fb4'
ORDER = (*range(24), 33, 34, 26, 27, 28, 29, 30, 31, 32, 35, 36, 38, 39, 37,
    40, 41, 43, 46, 42, 47, 44, 45, 48, 49, 24, 25, *range(50, 59), 60, 59,
    *range(61, 70), 71, 70, *range(72, 93), 100, 107, 95, 101, 102, 103, 93,
    96, 104, 109, 94, 98, 97, 108, 110, 99, 113, 105, 111, 112, 106, *range(114, 205))
REGISTERS = {29: (15, 16), 30: (24, 14), 31: (25, 12), 32: (0, 16, 26),
    34: (1, 16), 36: (1, 10), 37: (0, 14, 28), 42: (0, 12, 30), 58: (29, 16), 60: (29, 10),
    93: (18, 12), 94: (18, 14), 95: (20, 2, 10), 96: (0, 12, 0), 97: (28, 12, 6),
    98: (20, 0, 16), 101: (29, 6), 102: (20, 14, 6), 103: (1, 18), 107: (30, 14, 8),
    108: (29, 10), 110: (18, 16, 4), 111: (29, 8), 113: (29, 4)}
RELOCATIONS = {96: [('R_MIPS_HI16', 'D_800A6F94')], 100: [('R_MIPS_LO16', 'D_800A6F94')],
    132: [('R_MIPS_HI16', 'D_800A6F88')], 136: [('R_MIPS_LO16', 'D_800A6F88')],
    140: [('R_MIPS_HI16', 'D_800A6F8C')], 144: [('R_MIPS_LO16', 'D_800A6F8C')],
    152: [('R_MIPS_HI16', 'D_800A6F90')], 156: [('R_MIPS_LO16', 'D_800A6F90')],
    196: [('R_MIPS_HI16', 'D_800A6E90')], 280: [('R_MIPS_LO16', 'D_800A6E90')],
    304: [('R_MIPS_HI16', 'D_800A6F80')], 308: [('R_MIPS_LO16', 'D_800A6F80')],
    360: [('R_MIPS_26', 'func_1518C900')], 448: [('R_MIPS_26', 'func_150ADA20')],
    480: [('R_MIPS_26', 'func_150ADA20')], 512: [('R_MIPS_26', 'func_150ADA20')],
    544: [('R_MIPS_26', 'func_150ADA20')], 572: [('R_MIPS_26', 'func_150ADA20')],
    600: [('R_MIPS_26', 'func_150ADA20')], 640: [('R_MIPS_26', 'func_15168BE4')],
    728: [('R_MIPS_26', 'func_151718F0')]}


def raw_target(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    return text[f['value']:f['value'] + f['size']], {at - f['value']: rows for at, rows in rel.items()
        if f['value'] <= at < f['value'] + f['size']}


def normalize(raw, rel):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or rel != RELOCATIONS:
        raise ValueError('Unknown debris-match compiler words or bindings')
    if sorted(ORDER) != list(range(205)):
        raise ValueError('Debris plan must retain every compiled operation exactly once')
    words = struct.unpack('>205I', raw)
    output, moved = [], {}
    for new, old in enumerate(ORDER):
        word = allocation.allocate(words[old], REGISTERS[new]) if new in REGISTERS else words[old]
        if new == 73:
            if word != 0x27B50094:
                raise ValueError('Unknown unescaped debris staging home')
            word = 0x27B5009C
        output.append(word)
        if old * 4 in rel:
            moved[new * 4] = list(rel[old * 4])
    prove(list(words), rel, output, moved)
    return struct.pack('>205I', *output), moved


def link_target(out, name, raw, rel, entry=ENTRY, bindings=None):
    bindings = bindings or dict(D_800A6F88=0x800A6F88, D_800A6F8C=0x800A6F8C,
        D_800A6F90=0x800A6F90, D_800A6F94=0x800A6F94, D_800A6E90=0x800A6E90,
        D_800A6F80=0x800A6F80, func_1518C900=LOOKUP, func_150ADA20=RANDOM,
        func_15168BE4=SUBMIT, func_151718F0=RING)
    assembly, missing = emit_function(raw, dict(value=0, size=len(raw)), rel, FUNCTION, bindings)
    if missing:
        raise ValueError('Unbound debris symbols: ' + repr(missing))
    path = out / (name + '.s')
    path.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
    path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(path.with_suffix('.ld')), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in bindings.items()], '-o', str(path.with_suffix('.elf')),
        str(path.with_suffix('.o'))], check=True, capture_output=True)
    return list(struct.unpack_from('>%dI' % (len(raw) // 4), sections(path.with_suffix('.elf'))['.text'][1]))


def guard_manifest(before, raw, rel):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown debris guard predecessor')
    normalized, moved = normalize(raw, rel)
    replacements = struct.unpack('>205I', normalized)
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=next(csv.reader(io.StringIO(before.decode()))), lineterminator='\n')
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    for i, expected in enumerate(struct.unpack('>205I', raw)):
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % expected, replacement='0x%08X' % replacements[i],
            expected_relocations=spec(rel.get(i * 4, [])), replacement_relocations=spec(moved.get(i * 4, [])),
            note='Retain debris compiler fingerprint' if expected == replacements[i] and rel.get(i * 4) == moved.get(i * 4) else
                'Normalize checked debris scheduling, FP lifetimes and unescaped staging home',
            insert_after='', insert_after_relocations='', omit='false'))
    return before + output.getvalue().encode()


def qualify(root, out):
    obj, raw_words, row = measure(root, out, 'qualified')
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['pool_bytes']) != (205, 288, 44, '', 0):
        raise ValueError('Unknown debris-match compiler shape: ' + repr({k: row[k] for k in ('words', 'frame', 'differences', 'diagnostics', 'raw_sha256')}))
    raw, rel = raw_target(obj)
    normalized, moved = normalize(raw, rel)
    words = link_target(out, 'normalized', normalized, moved)
    truth = list(struct.unpack_from('>205I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if words != truth:
        raise ValueError('Derived debris does not match the full retail body')
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guard_manifest((out / 'before-guards').read_bytes(), raw, rel))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['edge_wrapper_original'], filename=OWNER, word_patches_path=manifest))
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, path.with_suffix('.o'), OWNER)
    f = functions[FUNCTION]
    if f['size'] != 820 or list(struct.unpack_from('>205I', data, f['value'])) != words:
        raise ValueError('Debris production padding differs')
    row.update(guarded_words=205, guarded_differences=0, proof=prove(list(struct.unpack('>205I', raw)), rel,
        list(struct.unpack('>205I', normalized)), moved))
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, path.with_suffix('.o'), raw_words, words, row


def slot_expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown debris predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown debris predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 820)
    result[at:at + 820] = rom[ROM:ROM + 820]
    struct.pack_into('>I', result, row[0] + 8, 820)
    return bytes(result)


def serialize_symbols(initial):
    """Close two measured GNU-ld serialization cycles; preserve the failed slot prediction."""
    if hashlib.sha256(initial).hexdigest() != 'b0429fedef05f574cc9e06c7ab12621564ee7e6d37fda29fa2bce33a6895c682':
        raise ValueError('Unknown initial debris image for symbol serialization')
    groups = [
        (('func_150CBCE0', 'D_800A3E2C'), ('D_800A3E2C', 'func_150CBCE0')),
        (('D_800A6E90', 'D_800A2460', 'osCreateThread'), ('D_800A2460', 'osCreateThread', 'D_800A6E90')),
    ]
    definitions = {'func_150CBCE0': (0x150CBCE0, 12, 18, 0, 5),
        'D_800A3E2C': (0x800A3E2C, 0, 16, 0, 6),
        'D_800A6E90': (0x800A6E90, 0, 16, 0, 65521),
        'D_800A2460': (0x800A2460, 0, 16, 0, 65521),
        'osCreateThread': (0x100037F0, 200, 18, 0, 3)}
    rows = {name: (at, fields, name_at) for at, name, fields, name_at in symbol_rows(initial) if name in definitions}
    if set(rows) != set(definitions):
        raise ValueError('Missing debris serialization symbols')
    result = bytearray(initial)
    for original, ordered in groups:
        slots = [rows[name][0] for name in original]
        first_string = rows[original[0]][2]
        string_base = first_string - rows[original[0]][1][0]
        cursor = first_string
        for index, name in enumerate(original):
            at, fields, name_at = rows[name]
            encoded = name.encode() + b'\0'
            if at != slots[0] + index * SYMBOL.size or name_at != cursor or fields[1:] != definitions[name] or initial[cursor:cursor + len(encoded)] != encoded:
                raise ValueError('Changed debris symbol record/name span')
            cursor += len(encoded)
        names = b''.join(name.encode() + b'\0' for name in ordered)
        if len(names) != cursor - first_string:
            raise ValueError('Debris symbol names changed extent')
        result[first_string:cursor] = names
        cursor = first_string
        for at, name in zip(slots, ordered):
            SYMBOL.pack_into(result, at, cursor - string_base, *definitions[name])
            cursor += len(name) + 1
    if canonical_symbols(result) != canonical_symbols(initial) or sum(a != b for a, b in zip(result, initial)) != 84:
        raise ValueError('Debris symbol cycles changed definitions or byte accounting')
    return bytes(result)


def expected_image(before, rom):
    return serialize_symbols(slot_expected_image(before, rom))


def expected_inputs(root, out):
    raw, rel = raw_target(out / 'qualified.o')
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        edge_wrapper_owner=recovered_owner((out / 'before-edge_wrapper_owner').read_text()).encode(),
        guards=guard_manifest((out / 'before-guards').read_bytes(), raw, rel))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--stack-screen', action='store_true')
    parser.add_argument('--lifetime-screen', action='store_true')
    parser.add_argument('--object-screen', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps({k: v for k, v in qualify(root, root / BUILD)[-1].items() if k != 'different_words'}, indent=2))
    elif args.object_screen:
        object_screens(root, root / BUILD)
    elif args.lifetime_screen:
        lifetime_screens(root, root / BUILD)
    elif args.stack_screen:
        stack_screens(root, root / BUILD)
    elif args.screen:
        screens(root, root / BUILD)
    else:
        print(json.dumps({k: v for k, v in measure(root, root / BUILD)[-1].items() if k != 'different_words'}, indent=2))
