"""Qualify packed RGB C with a closed start-register rename and dead return tail."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_packed_color_callback as previous
from tools.experiments import game_packed_color_control_fit as fit
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD = 'conker/build/game-packed-color-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS
PATHS, BASELINE, SELECTED = previous.PATHS, previous.BASELINE, fit.SELECTED
freeze, build = previous.freeze, previous.build
RAW_SHA256 = '54a6c0585a754b466ed25df0c9f704eff49b1c7453f5ea9f2af686f37307e716'
RELOCATIONS = {24: [('R_MIPS_HI16', 'D_800BE9E4')], 28: [('R_MIPS_LO16', 'D_800BE9E4')],
    72: [('R_MIPS_HI16', 'D_800BE9E4')], 76: [('R_MIPS_LO16', 'D_800BE9E4')],
    112: [('R_MIPS_HI16', 'D_800BE9E4')], 132: [('R_MIPS_LO16', 'D_800BE9E4')],
    196: [('R_MIPS_HI16', 'D_800A6E00')], 200: [('R_MIPS_LO16', 'D_800A6E00')],
    268: [('R_MIPS_HI16', 'D_800A6E0C')], 272: [('R_MIPS_LO16', 'D_800A6E0C')]}
GUARDS = ((0xC0, 0x90870026, 0x90850026, None),
    (0xCC, 0x24EC0008, 0x24AC0008, None),
    (0xD0, 0x00EC082A, 0x00AC082A, None),
    (0xD8, 0x00E01825, 0x00A01825, None),
    (0xDC, 0x00ED2821, 0x00AD2821, None),
    (0x3D0, 0x03E00008, 0x03E00008, 0),
    (0x3D4, 0, 0x03E00008, 0))


def recovered_owner(before, selected=SELECTED):
    return previous.recovered_owner(before, selected)


def measure(root, out, label, selected=SELECTED):
    return fit.measure(root, out, label, selected)


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown packed-color words or relocations')
    words = list(struct.unpack('>246I', raw))
    if words[-3:] != [0x00001025, 0x03E00008, 0]:
        raise ValueError('Changed packed-color reachable return')
    # No direct branch or local jump can enter the preserved dead tail.
    for index, word in enumerate(words):
        op = word >> 26
        if op in (2, 3) or (op == 0 and (word & 63) in (8, 9) and word != 0x03E00008):
            raise ValueError('Unknown packed-color jump')
        if op in (1, 4, 5, 6, 7, 20, 21, 22, 23):
            target = index + 1 + ((word & 0xFFFF) ^ 0x8000) - 0x8000
            if not 0 <= target < len(words):
                raise ValueError('Packed-color branch enters dead tail')
    data = bytearray()
    sites = {offset: (expected, replacement, inserted) for offset, expected, replacement, inserted in GUARDS}
    for index, word in enumerate(words):
        site = sites.get(index * 4)
        if site:
            expected, replacement, inserted = site
            if word != expected or index * 4 in relocations:
                raise ValueError('Changed packed-color physical guard site')
            word = replacement
        else:
            inserted = None
        data.extend(struct.pack('>I', word))
        if inserted is not None:
            data.extend(struct.pack('>I', inserted))
    return bytes(data), dict(relocations)


def guard_manifest(before):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown packed-color guard predecessor')
    fields = next(csv.reader(io.StringIO(before.decode())))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    for offset, expected, replacement, inserted in GUARDS:
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % offset,
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations='-', replacement_relocations='-',
            note='Preserve closed initial ramp-index register lifetime' if inserted is None else
                'Preserve original unreachable duplicate return and reachable delay slot',
            insert_after='' if inserted is None else '0x%08X' % inserted,
            insert_after_relocations='' if inserted is None else '-', omit='false'))
    return before + output.getvalue().encode()


def qualify(root, out):
    obj, raw_words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['diagnostics']) != (246, 7, ''):
        raise ValueError('Unknown packed-color compiler shape')
    data, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    relative = {p - f['value']: entries for p, entries in rel.items() if f['value'] <= p < f['value'] + f['size']}
    normalized, moved = normalize(data[f['value']:f['value'] + f['size']], relative)
    if moved != relative:
        raise ValueError('Packed-color relocations moved')
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guard_manifest((out / 'before-guards').read_bytes()))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=manifest))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    linked, fs = build.link_owner(root, out, padded, OWNER)
    function = fs[FUNCTION]
    words = list(struct.unpack_from('>248I', linked, function['value']))
    truth = list(struct.unpack_from('>248I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if function['size'] != 992 or words != truth:
        raise ValueError('Packed-color production padder is not exact')
    if len(normalized) != 992:
        raise ValueError('Packed-color normalized length changed')
    row['raw_installable'] = row.pop('installable')
    row.update(guarded_words=WORDS, guarded_differences=0, guards_added=7,
        initial_register_words=5, dead_return_tail_words=2, frame=0, raw_C_exact=False)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, raw_words, words, row


def main():
    root = Path.cwd()
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))


if __name__ == '__main__':
    main()
