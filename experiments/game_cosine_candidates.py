"""Screen cosine's SDK absolute/reduction copy and comparison literal types."""
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_trig_candidates as trig
from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-single-precision-cosine'
ENTRY, ROM, SLOT, CODE = trig.TARGETS['cosf']
PATHS = dict(trig.PATHS)
BASELINE = dict(trig.BASELINE, elf='e7966de8419027fba66c6d9ae8a2853ec5b3d0ce756303a823daa4b24e8e9fe9',
                sinf='ae271497692ea1a00abd96bcfed9209458cf8ea694b0df385aa5dddf9fc1a679')


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed cosine baseline input')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified immutable cosine manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable cosine input: ' + key)


def body(absolute_zero='0', rounding_zero='0.0f', copy=True):
    result = trig.body('cosf')
    result = result.replace('f32 reduced,', 'f32 absolute, reduced,')
    result = result.replace('reduced = angle > 0.0f ? angle : -angle;',
                            'absolute = angle > ' + absolute_zero + ' ? angle : -angle;')
    if copy:
        result = result.replace('        periods = reduced *', '        reduced = absolute;\n        periods = reduced *')
    else:
        result = result.replace('periods = reduced *', 'periods = absolute *')
        result = result.replace('reduced = reduced - periods * D_80085EA4;', 'reduced = absolute - periods * D_80085EA4;')
    result = result.replace('periods >= 0.0f', 'periods >= ' + rounding_zero)
    result = result.replace('periods = period - 0.5f;', 'periods = period;\n        periods -= 0.5f;')
    return result


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    rom = (root / 'conker/conker.us.bin').read_bytes()
    expected = list(struct.unpack_from('>88I', rom, ROM))
    rows = []
    for i, (absolute, rounding, copy) in enumerate(itertools.product(('0', '0.0f', '0.0'), ('0', '0.0f', '0.0'), (True, False))):
        label = 'cosine-' + str(i)
        obj, diagnostics = build.compile_owner(root, out, body(absolute, rounding, copy), label)
        data, functions = build.link_owner(root, out, obj, 'cosf')
        words = list(struct.unpack('>%dI' % (len(data) // 4), data))
        different = [(offset, hex(a), hex(b)) for offset, (a, b) in enumerate(zip(words, expected)) if a != b]
        row = dict(label=label, absolute_zero=absolute, rounding_zero=rounding, copy=copy,
                   code_bytes=functions['cosf']['size'], text_bytes=len(data), differences=different,
                   uncompared_slot_words=max(0, SLOT - len(words)), diagnostics=diagnostics)
        rows.append(row)
        print(label, absolute, rounding, copy, row['code_bytes'], row['text_bytes'], len(different), row['uncompared_slot_words'], flush=True)
    (out / 'sdk-copy-screens.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
