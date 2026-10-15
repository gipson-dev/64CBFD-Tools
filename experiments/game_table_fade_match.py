"""Qualify the recovered frame and two bounded temporary/scheduling groups."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_table_fade_callback as previous
from tools.experiments import game_table_fade_frame as frame
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-table-fade-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS
TABLES, TABLE_ROM, STEP, MOVE, SCALE = previous.TABLES, previous.TABLE_ROM, previous.STEP, previous.MOVE, previous.SCALE
PATHS, BASELINE, freeze, build = previous.PATHS, previous.BASELINE, previous.freeze, previous.build
SELECTED = dict(frame.candidates())['tail-live-operands'].replace(
    '/* Snapshot the preset tables, fade a full word, then update motion and size. */',
    '/* Snapshot the preset tables, fade a full word, then update motion and size.\n'
    ' * Live tail operands retain the frame; guards normalize temporary scheduling. */')
RAW_SHA256 = 'a4e70e3d7f6665707a623eeb4bd88762f9c11f4951cba7a63290fc90ec6113a4'
RELOCATIONS = {16: [('R_MIPS_HI16', 'D_8008CBC4')], 20: [('R_MIPS_LO16', 'D_8008CBC4')],
    44: [('R_MIPS_HI16', 'D_8008CBD0')], 52: [('R_MIPS_LO16', 'D_8008CBD0')],
    80: [('R_MIPS_HI16', 'D_8008CBDC')], 88: [('R_MIPS_LO16', 'D_8008CBDC')],
    100: [('R_MIPS_HI16', 'D_8008CBE8')], 104: [('R_MIPS_LO16', 'D_8008CBE8')],
    176: [('R_MIPS_HI16', 'D_800BE9E4')], 188: [('R_MIPS_LO16', 'D_800BE9E4')],
    236: [('R_MIPS_HI16', 'D_800BE9E4')], 240: [('R_MIPS_LO16', 'D_800BE9E4')],
    308: [('R_MIPS_26', 'func_1516F864')], 320: [('R_MIPS_HI16', 'D_800BE9E4')],
    324: [('R_MIPS_LO16', 'D_800BE9E4')], 384: [('R_MIPS_26', 'func_1516F94C')]}


def recovered_owner(before, selected=SELECTED):
    return previous.recovered_owner(before, selected)


def measure(root, out, label, selected=SELECTED):
    return previous.measure(root, out, label, selected)


def raw_target(obj):
    raw, relative = frame.target(obj)
    return raw, dict(relative)


def registers(word, mapping):
    op = word >> 26
    fields = (21, 16, 11) if op == 0 else () if op in (2, 3) else (21, 16)
    for shift in fields:
        old = word >> shift & 31
        word = word & ~(31 << shift) | mapping.get(old, old) << shift
    return word


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown table-fade words or relocations')
    words = list(struct.unpack('>103I', raw))
    output = list(words)
    # The fade group has a closed pointer/step/coefficient register cycle.
    order = (59, 58, 61, 60, 62)
    for at, old in zip(range(58, 63), order):
        output[at] = registers(words[old], {15: 24, 24: 25, 25: 15})
    word = output[62]
    output[62] = word & ~((31 << 21) | (31 << 16)) | (word >> 16 & 31) << 21 | (word >> 21 & 31) << 16
    # Rename only these five dead temporary lifetimes; final V0 remains V0.
    for at in range(80, 96):
        if at == 89:
            continue  # A1 starts its distinct scale-table-address lifetime here.
        output[at] = registers(words[at], {3: 12, 5: 8, 8: 9, 9: 10, 12: 2})
    moved = {offset: list(entries) for offset, entries in relocations.items() if offset not in (236, 240)}
    moved.update({232: list(relocations[236]), 244: list(relocations[240])})
    return struct.pack('>103I', *output), moved


def guard_manifest(before, raw, relocations):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown table-fade guard predecessor')
    normalized, moved = normalize(raw, relocations)
    fields = next(csv.reader(io.StringIO(before.decode())))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    for index, (expected, replacement) in enumerate(zip(struct.unpack('>103I', raw), struct.unpack('>103I', normalized))):
        offset = index * 4
        old, new = relocations.get(offset, []), moved.get(offset, [])
        if expected == replacement and not old and not new:
            continue
        spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
        note = ('Normalize table-fade independent load schedule and closed temporary cycle' if 232 <= offset <= 248 else
            'Normalize table-fade tail temporary lifetimes' if 320 <= offset <= 380 else
            'Preserve table-fade table and helper relocation bindings')
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % offset,
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations=spec(old), replacement_relocations=spec(new), note=note,
            insert_after='', insert_after_relocations='', omit='false'))
    return before + output.getvalue().encode()


def qualify(root, out):
    obj, raw_words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (103, 15, 104, ''):
        raise ValueError('Unknown table-fade compiler shape')
    raw, rel = raw_target(obj)
    normalized, moved = normalize(raw, rel)
    guards = guard_manifest((out / 'before-guards').read_bytes(), raw, rel)
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guards)
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=manifest))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, fs = build.link_owner(root, out, padded, OWNER)
    f = fs[FUNCTION]
    words = list(struct.unpack_from('>103I', data, f['value']))
    truth = list(struct.unpack_from('>103I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if f['size'] != 412 or len(normalized) != 412 or words != truth:
        raise ValueError('Table-fade production padder is not exact')
    row.update(guarded_words=103, guarded_differences=0, guards_added=len(guards[len((out / 'before-guards').read_bytes()):].splitlines()),
        frame=104, raw_C_exact=False, moved_relocations=moved)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, raw_words, words, row


def main():
    root = Path.cwd()
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))


if __name__ == '__main__':
    main()
