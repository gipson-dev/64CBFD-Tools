"""Qualify the counter preset's closed register cycle and redundant-load omission."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_counter_preset as previous
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD = 'conker/build/game-counter-preset-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS
CALLEE, TABLE = previous.CALLEE, previous.TABLE
PATHS, BASELINE = previous.PATHS, previous.BASELINE
freeze, build = previous.freeze, previous.build
SELECTED = previous.SELECTED.replace(
    '/* Consume a qualifying slot counter before creating its effect preset. */',
    '/* Consume a qualifying slot counter before creating its effect preset.\n'
    ' * Expected-word guards preserve retail index reuse and temporary allocation. */')
RAW_SHA256 = '898c7e35028b16b935e6af23ea92bebb10b329ea42d5ebcac359af50c57f00a0'
RELOCATIONS = {24: [('R_MIPS_HI16', 'D_800DD2A0')], 28: [('R_MIPS_LO16', 'D_800DD2A0')],
    316: [('R_MIPS_26', 'func_1516D99C')]}
REGISTERS = {8: 25, 9: 8, 10: 9, 11: 10, 12: 11, 13: 12, 14: 13, 15: 14, 24: 15, 25: 24}


def recovered_owner(before, selected=SELECTED):
    return previous.recovered_owner(before, selected)


def measure(root, out, label, selected=SELECTED):
    return previous.measure(root, out, label, selected)


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown counter-preset words or relocations')
    words = list(struct.unpack('>85I', raw))
    if words[5:12] != [0x8FAE00D0, 0x3C180000, 0x27180000, 0x29C10004,
            0x10200047, 0x8FAF00D0, 0x01F81021]:
        raise ValueError('Changed counter-preset opening index lifetime')
    output = []
    for index, word in enumerate(words):
        if index == 10:
            continue
        op = word >> 26
        fields = (21, 16, 11) if op == 0 else () if op in (2, 3) else (21, 16)
        for shift in fields:
            register = word >> shift & 31
            # Opening T6 carries the index; only its later lifetime joins the cycle.
            replacement = REGISTERS.get(register, register) if index >= 6 and not (index < 11 and register == 14) else register
            word = word & ~(31 << shift) | replacement << shift
        if index == 9:
            word = word & 0xFFFF0000 | ((word & 65535) - 1)
        output.append(word)
    moved = {offset - (4 if offset > 40 else 0): list(entries) for offset, entries in relocations.items()}
    return struct.pack('>84I', *output), moved


def guard_manifest(before, raw, relocations):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown counter-preset guard predecessor')
    normalized, _ = normalize(raw, relocations)
    old, new = struct.unpack('>85I', raw), struct.unpack('>84I', normalized)
    fields = next(csv.reader(io.StringIO(before.decode())))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    for index, expected in enumerate(old):
        omit = index == 10
        replacement = expected if omit else new[index - (index > 10)]
        entries = relocations.get(index * 4, [])
        if not omit and expected == replacement and not entries:
            continue
        spec = ';'.join(kind + ':' + name for kind, name in entries) or '-'
        note = 'Normalize closed counter-preset temporary-register allocation'
        if omit:
            note = 'Omit redundant index-home reload so pointer add occupies retail branch delay'
        elif index == 9:
            note = 'Adjust counter-preset exit branch across redundant-load omission'
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (index * 4),
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations=spec, replacement_relocations=spec, note=note,
            insert_after='', insert_after_relocations='', omit='true' if omit else 'false'))
    return before + output.getvalue().encode()


def raw_target(obj):
    data, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    relative = {p - f['value']: entries for p, entries in rel.items() if f['value'] <= p < f['value'] + f['size']}
    return data[f['value']:f['value'] + f['size']], relative


def qualify(root, out):
    obj, raw_words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['diagnostics']) != (85, 76, ''):
        raise ValueError('Unknown counter-preset compiler shape')
    raw, rel = raw_target(obj)
    normalized, moved = normalize(raw, rel)
    if moved != {24: RELOCATIONS[24], 28: RELOCATIONS[28], 312: RELOCATIONS[316]}:
        raise ValueError('Changed counter-preset normalized relocations')
    guards = guard_manifest((out / 'before-guards').read_bytes(), raw, rel)
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guards)
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=manifest))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, fs = build.link_owner(root, out, padded, OWNER)
    f = fs[FUNCTION]
    words = list(struct.unpack_from('>84I', data, f['value']))
    truth = list(struct.unpack_from('>84I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if f['size'] != 336 or len(normalized) != 336 or words != truth:
        raise ValueError('Counter-preset production padder is not exact')
    count = len(guards[len((out / 'before-guards').read_bytes()):].splitlines())
    row.update(guarded_words=84, guarded_differences=0, guards_added=count,
        omitted_redundant_loads=1, closed_register_cycle=10, frame=208, raw_C_exact=False)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, raw_words, words, row


def main():
    root = Path.cwd()
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))


if __name__ == '__main__':
    main()
