"""Continue table-debris frame and allocation recovery from immutable semantic captures."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_table_debris as previous
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols, SYMBOL

BUILD = 'conker/build/game-table-debris-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS
PATHS, BASELINE = previous.PATHS, previous.BASELINE
LOOKUP, RANDOM, SUBMIT, TABLE = previous.LOOKUP, previous.RANDOM, previous.SUBMIT, previous.TABLE
DECLARATIONS, build, freeze = previous.DECLARATIONS, previous.build, previous.freeze
SELECTED = previous.SELECTED


def measure(root, out, label='selected', selected=None):
    return previous.measure(root, out, label, SELECTED if selected is None else selected)


def loop_forms():
    scalar = previous.SELECTED
    array = dict(previous.shape_forms())['chain-count-array']
    for name, body in (('scalar', scalar), ('array', array)):
        yield name + '-count-s16', body.replace('    s32 count;', '    s16 count;')
        yield name + '-count-u8', body.replace('    s32 count;', '    u8 count;')
        yield name + '-index-s16', body.replace('    s32 index;', '    s16 index;')
        yield name + '-index-u8', body.replace('    s32 index;', '    u8 index;')
        yield name + '-const-count', body.replace('    s32 count;', '    const s32 count = 6;').replace('    count = 6;\n', '')
        literal = body.replace('    s32 count;\n', '').replace('    count = 6;\n', '').replace('index < count', 'index < 6')
        yield name + '-goto', literal.replace('    do {', 'loop:\n    {').replace(
            '    } while (index < 6);', '    }\n    if (index < 6) {\n        goto loop;\n    }')
        yield name + '-for', literal.replace('    index = 0;\n', '').replace('    do {',
            '    for (index = 0; index < 6; index += 1) {').replace('        index += 1;\n', '').replace('    } while (index < 6);', '    }')
        yield name + '-while', literal.replace('    do {', '    while (index < 6) {').replace('    } while (index < 6);', '    }')
        yield name + '-inverted-goto', literal.replace('    do {', 'loop:\n    {').replace(
            '    } while (index < 6);', '    }\n    if (index >= 6) {\n        goto done;\n    }\n    goto loop;\ndone:')


def object_forms():
    array = dict(previous.shape_forms())['chain-count-array']
    for name, body in (('scalar', previous.SELECTED), ('array', array)):
        coefficient = body.replace('    f32 horizontal;\n    f32 vertical;\n    f32 rotationScale;', '    f32 motion[3];')
        for old, new in (('horizontal', 'motion[0]'), ('vertical', 'motion[1]'), ('rotationScale', 'motion[2]')):
            coefficient = coefficient.replace(old, new)
        yield name + '-coefficient-array', coefficient
        yield name + '-const-coefficients', body.replace('    f32 horizontal;', '    const f32 horizontal = D_800A6FAC;').replace(
            '    f32 vertical;', '    const f32 vertical = D_800A6FA8;').replace('    f32 rotationScale;',
            '    const f32 rotationScale = D_800A6FA4;').replace('    horizontal = D_800A6FAC;\n', '').replace(
            '    vertical = D_800A6FA8;\n', '').replace('    rotationScale = D_800A6FA4;\n', '')
        yield name + '-declaration-count', body.replace('    s32 count;', '    s32 count = 6;').replace('    count = 6;\n', '')
    pointer = array.replace('    f32 origin[3];', '    f32 coordinates[3];\n    f32 *origin;').replace(
        '    packet.control5C =', '    origin = coordinates;\n    packet.control5C =', 1)
    yield 'array-real-origin-pointer', pointer
    yield 'array-reverse-position-operands', array.replace('entry->offset[0] + origin[0]', 'origin[0] + entry->offset[0]').replace(
        'entry->offset[1] + origin[1]', 'origin[1] + entry->offset[1]').replace('entry->offset[2] + origin[2]', 'origin[2] + entry->offset[2]')


def table_forms():
    array = dict(previous.shape_forms())['chain-count-array']
    for name, initial in (('scalar', previous.SELECTED), ('array', array)):
        indexed = initial.replace('    TableDebris19E040 *entry;\n', '').replace('    entry = D_800A6ED8;\n', '').replace(
            '        entry += 1;\n', '').replace('entry->', 'D_800A6ED8[index].')
        yield name + '-indexed-table', indexed
        yield name + '-indexed-literal-bound', indexed.replace('    s32 count;\n', '').replace(
            '    count = 6;\n', '').replace('index < count', 'index < 6')
        yield name + '-early-coefficient-declarations', initial.replace(
            '    f32 horizontal;\n    f32 vertical;\n    f32 rotationScale;\n', '').replace(
            '    DebrisPacket19E040 packet;', '    f32 horizontal;\n    f32 vertical;\n    f32 rotationScale;\n    DebrisPacket19E040 packet;')
    for local in ('asset', 'index', 'count'):
        body = array.replace('    s32 ' + local + ';\n', '').replace(
            '    DebrisPacket19E040 packet;', '    s32 ' + local + ';\n    DebrisPacket19E040 packet;')
        yield 'array-first-' + local, body


def literal_forms():
    array = dict(previous.shape_forms())['chain-count-array']
    for name, initial in (('scalar', previous.SELECTED), ('array', array)):
        body = initial
        for local, symbol, literal in (('horizontal', 'D_800A6FAC', '0.09f'),
                ('vertical', 'D_800A6FA8', '0.23f'), ('rotationScale', 'D_800A6FA4', '0.1f')):
            body = body.replace('    f32 ' + local + ';\n', '').replace('    ' + local + ' = ' + symbol + ';\n', '')
            body = body.replace(local, literal)
        yield name + '-literal-motion', body
        yield name + '-literal-motion-separate-scale', body.replace(
            '    packet.scale[0] = packet.scale[1] = packet.scale[2] = 2.0f;',
            '    packet.scale[0] = 2.0f;\n    packet.scale[1] = 2.0f;\n    packet.scale[2] = 2.0f;')
        yield name + '-literal-motion-packet-after-origin', body.replace('    DebrisPacket19E040 packet;\n', '').replace(
            '    f32 originX;' if name == 'scalar' else '    f32 origin[3];',
            ('    f32 originX;' if name == 'scalar' else '    f32 origin[3];') + '\n    DebrisPacket19E040 packet;')


def slot_forms():
    initial = dict(literal_forms())['scalar-literal-motion-separate-scale']
    declarations = {'asset': '    s32 asset;', 'index': '    s32 index;', 'count': '    s32 count;',
        'entry': '    TableDebris19E040 *entry;'}
    for first in declarations:
        for second in declarations:
            if first == second:
                continue
            body = initial.replace(declarations[first] + '\n', '').replace(declarations[second] + '\n', '')
            body = body.replace('    DebrisPacket19E040 packet;', declarations[first] + '\n    DebrisPacket19E040 packet;\n' + declarations[second])
            yield 'slots-' + first + '-' + second, body


def initialization_forms():
    initial = dict(slot_forms())['slots-index-count']
    for before in ('originX =', 'packet.control5C =', 'packet.rotation[0] ='):
        body = initial.replace('    entry = D_800A6ED8;\n', '').replace('    ' + before,
            '    entry = D_800A6ED8;\n    ' + before, 1)
        yield 'entry-before-' + before.split()[0].replace('.', '-').replace('[', '').replace(']', ''), body
        yield 'entry-and-index-before-' + before.split()[0].replace('.', '-').replace('[', '').replace(']', ''), body.replace(
            '    index = 0;\n', '').replace('    originY =', '    index = 0;\n    originY =', 1)


def count_forms():
    initial = dict(initialization_forms())['entry-before-originX']
    for before in ('entry =', 'originX =', 'packet.control5C =', 'packet.rotation[0] ='):
        yield 'count-before-' + before.split()[0].replace('.', '-').replace('[', '').replace(']', ''), initial.replace(
            '    count = 6;\n', '').replace('    ' + before, '    count = 6;\n    ' + before, 1)
    yield 'count-at-declaration', initial.replace('    s32 count;', '    s32 count = 6;').replace('    count = 6;\n', '')


SELECTED = dict(count_forms())['count-before-entry']
DECLARATIONS = previous.DECLARATIONS.replace('extern f32 D_800A6FA4, D_800A6FA8, D_800A6FAC;\n', '')
RAW_SHA256 = 'b819068d7c34b241235c8488ac0da42757752cdd0aa0d9eb058683e76a61e309'
POOL_ANCHOR, POOL = 'D_800A6FA4', bytes.fromhex('3dcccccd3e6b851f3db851ec00000000')
RELOCATIONS = {124: [('R_MIPS_HI16', 'D_800A6ED8')], 160: [('R_MIPS_LO16', 'D_800A6ED8')],
    120: [('R_MIPS_HI16', 'D_800A6F98')], 144: [('R_MIPS_LO16', 'D_800A6F98')],
    148: [('R_MIPS_HI16', 'D_800A6F9C')], 172: [('R_MIPS_LO16', 'D_800A6F9C')],
    176: [('R_MIPS_HI16', 'D_800A6FA0')], 196: [('R_MIPS_LO16', 'D_800A6FA0')],
    236: [('R_MIPS_HI16', '.rodata')], 240: [('R_MIPS_LO16', '.rodata')],
    248: [('R_MIPS_HI16', '.rodata')], 252: [('R_MIPS_LO16', '.rodata')],
    256: [('R_MIPS_HI16', '.rodata')], 312: [('R_MIPS_LO16', '.rodata')],
    332: [('R_MIPS_26', 'func_1518C900')], 472: [('R_MIPS_26', 'func_150ADA68')],
    500: [('R_MIPS_26', 'func_150ADA68')], 532: [('R_MIPS_26', 'func_15168BE4')]}


def recovered_owner(before, selected=None):
    result = previous.recovered_owner(before, SELECTED if selected is None else selected)
    if result.count(previous.DECLARATIONS) != 1:
        raise ValueError('Unexpected table-debris declarations')
    return result.replace(previous.DECLARATIONS, DECLARATIONS, 1)


def proposed_makefile(before):
    marker = '$(BUILD_DIR)/$(SRC_DIR)/game/generated_113D60.c.o: RETAIL_RODATA_SYMBOL := D_800A1350\n'
    addition = ('# Table debris emits its original three motion literals at one fixed anchor.\n'
        '$(BUILD_DIR)/$(SRC_DIR)/game/generated_19E040.c.o: RETAIL_RODATA_SYMBOL := D_800A6FA4\n'
        '$(BUILD_DIR)/$(SRC_DIR)/game/generated_19E040.c.o: Makefile\n')
    if hashlib.sha256(before).hexdigest() != BASELINE['makefile'] or before.decode().count(marker) != 1:
        raise ValueError('Unknown table-debris Makefile predecessor')
    return before.decode().replace(marker, marker + addition, 1).encode()


def checked_object(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    relative = {at - f['value']: rows for at, rows in rel.items() if f['value'] <= at < f['value'] + f['size']}
    pools = {name: data for name, (_, data) in sections(obj).items() if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and data}
    if f['size'] != 632 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relative != RELOCATIONS or pools != {'.rodata': POOL}:
        raise ValueError('Unknown table-debris compiler words, bindings or literal pool')
    return raw, relative


def qualify(root, out):
    freeze(root, out)
    owner = recovered_owner((out / 'before-edge_wrapper_owner').read_text())
    obj, diagnostics = build.compile_owner(root, out, owner, 'qualified')
    raw, rel = checked_object(obj)
    if diagnostics:
        raise ValueError('Table-debris compiler diagnostic: ' + diagnostics)
    rom = (root / 'conker/conker.us.bin').read_bytes()
    if rom[0x24BA64:0x24BA70] != POOL[:12]:
        raise ValueError('Table-debris motion pool no longer equals retail')
    manifest = out / 'before-guards'
    if (',' + FUNCTION + ',').encode() in manifest.read_bytes():
        raise ValueError('Direct table debris must not acquire word guards')
    padded = out / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj, root / PATHS['edge_wrapper_original'], filename=OWNER,
        word_patches_path=manifest, rodata_symbol=POOL_ANCHOR))
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded.with_suffix('.o')), str(padded)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded.with_suffix('.o'), OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>158I', data, f['value']))
    truth = list(struct.unpack_from('>158I', rom, ROM))
    if f['size'] != 632 or words != truth:
        raise ValueError('Table debris is not an exact unguarded pool-aliased match')
    row = dict(words=158, frame=232, packet_home=132, raw_sha256=RAW_SHA256,
        literal_pool_bytes=16, retail_literal_bytes=12, zero_pool_padding_bytes_not_emitted=4,
        literal_pool_alias=POOL_ANCHOR, target_word_guards=0, linked_differences=0, diagnostics='')
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded.with_suffix('.o'), words, row


def slot_expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown table-debris predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown table-debris predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 632)
    result[at:at + 632] = rom[ROM:ROM + 632]
    struct.pack_into('>I', result, row[0] + 8, 632)
    return bytes(result)


SERIALIZATION_GROUPS = [
    (('D_800A6FA0', 'D_80090B50'), ('D_80090B50', 'D_800A6FA0')),
    (('D_800A6FA4', 'D_800A1304', 'D_80090B54', 'D_800AAC14', 'D_800AA3E4'),
     ('D_800A1304', 'D_80090B54', 'D_800AAC14', 'D_800AA3E4', 'D_800A6FA4')),
    (('D_800A6ED8', 'D_80090A88', 'D_80090928'), ('D_80090A88', 'D_80090928', 'D_800A6ED8')),
    (('D_80099F3C', 'D_800A3E0C'), ('D_800A3E0C', 'D_80099F3C')),
    (('D_8009952C', 'D_80095B2C', 'D_800A3D9C'), ('D_800A3D9C', 'D_8009952C', 'D_80095B2C')),
    (('D_800A6F98', 'D_80090298'), ('D_80090298', 'D_800A6F98'))]


def serialize_symbols(initial):
    """Account for six exact pre-install GNU-ld cycles, never omit metadata."""
    if hashlib.sha256(initial).hexdigest() != '987a85e64b514e5e29ab12633a47401dc43400ca0de34b7cc944b4a9b64e30b2':
        raise ValueError('Unknown table-debris structural prediction')
    names = {n for original, _ in SERIALIZATION_GROUPS for n in original}
    rows = {name: (at, fields, string_at) for at, name, fields, string_at in symbol_rows(initial) if name in names}
    actual_data = {'D_80090B50', 'D_80090B54', 'D_80090A88', 'D_80090928', 'D_800A3E0C', 'D_800A3D9C'}
    definitions = {n: (int(n[2:], 16), 0, 16, 0, 6 if n in actual_data else 65521) for n in names}
    if set(rows) != names:
        raise ValueError('Missing table-debris serialization symbols')
    result = bytearray(initial)
    for original, ordered in SERIALIZATION_GROUPS:
        slots = [rows[n][0] for n in original]
        first = rows[original[0]][2]
        base = first - rows[original[0]][1][0]
        cursor = first
        for index, name in enumerate(original):
            at, fields, string_at = rows[name]
            encoded = name.encode() + b'\0'
            if at != slots[0] + index * SYMBOL.size or string_at != cursor or fields[1:] != definitions[name] or initial[cursor:cursor + len(encoded)] != encoded:
                raise ValueError('Changed table-debris record or name span')
            cursor += len(encoded)
        encoded = b''.join(n.encode() + b'\0' for n in ordered)
        if len(encoded) != cursor - first:
            raise ValueError('Table-debris symbol name extent changed')
        result[first:cursor] = encoded
        cursor = first
        for at, name in zip(slots, ordered):
            SYMBOL.pack_into(result, at, cursor - base, *definitions[name])
            cursor += len(name) + 1
    if canonical_symbols(result) != canonical_symbols(initial) or sum(a != b for a, b in zip(initial, result)) != 121:
        raise ValueError('Table-debris serialization accounting changed')
    return bytes(result)


def expected_inputs(root, out):
    before = (out / 'before-elf').read_bytes()
    image = serialize_symbols(slot_expected_image(before, (root / 'conker/conker.us.bin').read_bytes()))
    return dict(elf=image, edge_wrapper_owner=recovered_owner((out / 'before-edge_wrapper_owner').read_text()).encode(),
        makefile=proposed_makefile((out / 'before-makefile').read_bytes()))


def prelink_prediction(root, out):
    _, padded, _, _ = qualify(root, out)
    capture = out / 'link-inputs.json'
    if not capture.exists():
        live = {k: hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()}
        if live != BASELINE:
            raise ValueError('Pre-install link inputs must be captured before installation')
        (out / 'before-linkscript').write_bytes((root / 'conker/build/conker.ld').read_bytes())
        (out / 'before-owner.o').write_bytes((root / 'conker/build/src/game/generated_19E040.c.o').read_bytes())
        capture.write_text(json.dumps({n: hashlib.sha256((out / n).read_bytes()).hexdigest()
            for n in ('before-linkscript', 'before-owner.o')}, indent=2) + '\n')
    for name, digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed table-debris pre-install link capture')
    link = (out / 'before-linkscript').read_text()
    needle = 'build/src/game/generated_19E040.c.o(.text);'
    if link.count(needle) != 1:
        raise ValueError('Expected exactly one table-debris text selector')
    proposed = out / 'prediction.ld'
    proposed.write_text(link.replace(needle, str(padded.relative_to(root / 'conker')) + '(.text);', 1))
    baseline = out / 'baseline-link.ld'
    baseline.write_text(link.replace(needle, str((out / 'before-owner.o').relative_to(root / 'conker')) + '(.text);', 1))
    for name, script in (('prelink-baseline', baseline), ('prelink-prediction', proposed)):
        result = subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / (name + '.elf')).relative_to(root / 'conker'))], cwd=root / 'conker', capture_output=True, text=True)
        if result.returncode:
            raise ValueError(result.stderr)
    before = (out / 'before-elf').read_bytes()
    if (out / 'prelink-baseline.elf').read_bytes() != before:
        raise ValueError('Current linked inputs do not reproduce the frozen predecessor')
    predicted = (out / 'prelink-prediction.elf').read_bytes()
    initial = slot_expected_image(before, (root / 'conker/conker.us.bin').read_bytes())
    if predicted != serialize_symbols(initial):
        raise ValueError('Pre-install link differs from fully accounted byte prediction')
    row = dict(initial_slot_sha256=hashlib.sha256(initial).hexdigest(),
        predicted_sha256=hashlib.sha256(predicted).hexdigest(),
        slot_changes=sum(a != b for a, b in zip(before, initial)),
        additional_serialization_bytes=sum(a != b for a, b in zip(initial, predicted)),
        all_named_definitions_unchanged_except_target_extent=True)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def trace_frame(root, out, name, body):
    from tools.experiments import game_table_fade_frame as frame
    freeze(root, out)
    prefix = previous.recovered_owner((out / 'before-edge_wrapper_owner').read_text(), body).split('extern s32 D_800BE9F0;', 1)[0]
    prefix = prefix.replace('#include <ultra64.h>\n', '')
    adapter = SimpleNamespace(DECLARATIONS=prefix, FUNCTION=FUNCTION, freeze=freeze, measure=measure, build=build)
    with patch.object(frame, 'source', adapter):
        result = frame.trace(root, out, name, body)
    return {k: v for k, v in result.items() if k not in ('records', 'baseline')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loops', action='store_true')
    parser.add_argument('--objects', action='store_true')
    parser.add_argument('--tables', action='store_true')
    parser.add_argument('--literals', action='store_true')
    parser.add_argument('--slots', action='store_true')
    parser.add_argument('--initialization', action='store_true')
    parser.add_argument('--counts', action='store_true')
    parser.add_argument('--trace-frame', choices=('scalar', 'array', 'accepted'))
    parser.add_argument('--qualify', action='store_true')
    parser.add_argument('--predict', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.predict:
        print(json.dumps(prelink_prediction(root, root / BUILD), indent=2))
        raise SystemExit
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
        raise SystemExit
    if args.trace_frame:
        body = SELECTED if args.trace_frame == 'accepted' else previous.SELECTED if args.trace_frame == 'scalar' else dict(previous.shape_forms())['chain-count-array']
        print(json.dumps(trace_frame(root, root / BUILD, 'frame-' + args.trace_frame, body), indent=2))
        raise SystemExit
    for name, body in (count_forms() if args.counts else initialization_forms() if args.initialization else slot_forms() if args.slots else literal_forms() if args.literals else table_forms() if args.tables else loop_forms() if args.loops else object_forms() if args.objects else (('selected', SELECTED),)):
        _, _, row = measure(root, root / BUILD, name, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame', 'differences', 'stack_pointers', 'diagnostics', 'raw_sha256')}), flush=True)
