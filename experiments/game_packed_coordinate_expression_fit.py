"""Screen defined low-coordinate expressions against the complete retail wrapper."""
import json
from pathlib import Path
import re
import struct
import subprocess

from tools.experiments import game_packed_coordinate_preset as source
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-packed-coordinate-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS, CALLEE = source.OWNER, source.FUNCTION, source.ENTRY, source.ROM, source.WORDS, source.CALLEE
PATHS, BASELINE = source.PATHS, source.BASELINE
SELECTED = source.INITIAL.replace('(s16)arg0', '(s16)(arg0 & 0xFFFF)')
freeze = source.freeze


def recovered_owner(before, selected=SELECTED):
    return source.recovered_owner(before, selected)


def candidates():
    initial = source.INITIAL
    low = '(s16)arg0'
    variants = {
        'mask-low': initial.replace(low, 'arg0 & 0xFFFF'),
        'shift-pair-low': initial.replace(low, '(arg0 << 16) >> 16'),
        'mask-cast-low': initial.replace(low, '(s16)(arg0 & 0xFFFF)'),
        'shift-pair-cast-low': initial.replace(low, '(s16)((arg0 << 16) >> 16)'),
        'modulo-low': initial.replace(low, 'arg0 % 0x10000'),
        'no-coordinate-casts': initial.replace('(s16)(arg0 >> 16)', 'arg0 >> 16').replace(low, 'arg0 & 0xFFFF'),
        'unsigned-literals': re.sub(r'(?<!\w)(0|4|8)(?=,)', r'\1U', source.SELECTED),
        'high-mask': source.SELECTED.replace('(s16)(arg0 >> 16)', '(s16)((arg0 >> 16) & 0xFFFF)'),
    }
    return variants


def qualify(root, out):
    obj, words, row = source.measure(root, out, 'qualified', SELECTED)
    if (row['words'], row['differences'], row['diagnostics']) != (85, 0, ''):
        raise ValueError('Masked-coordinate preset is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, fs = source.build.link_owner(root, out, padded, OWNER)
    f = fs[FUNCTION]
    if f['size'] != 340 or list(struct.unpack_from('>85I', data, f['value'])) != words:
        raise ValueError('Masked-coordinate production padder differs')
    row.update(guards_added=0, frame=208, direct_C=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def main():
    root = Path.cwd()
    out = root / source.BUILD
    rows = []
    for name, body in candidates().items():
        row = source.measure(root, out, 'expression-' + name, body)[-1]
        rows.append(row)
        print(json.dumps({key: row[key] for key in ('label', 'words', 'differences', 'diagnostics')}), flush=True)
    (out / 'expression-fit.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(qualify(root, root / BUILD)[-1]), flush=True)


if __name__ == '__main__':
    main()
