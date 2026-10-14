"""Recover matrix loop setup and conversion-buffer register lifetimes."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_matrix_reflection_register_schedule as previous
from tools.pad_generated_object import parse_object

BASE = previous.qualified_body()
SELECTED_NAME = 'secondary-ioc-snapshot1'


def setup_body(order, snapshot=False, separate_mode=False):
    body = BASE
    marker = '        cursor = output;\n        offset = 0;\n        i = 0;\n        if (count > 0) {'
    assert body.count(marker) == 1
    lines = {'c': '        cursor = output;\n', 'o': '        offset = 0;\n', 'i': '        i = 0;\n'}
    replacement = ''.join(lines[key] for key in order)
    if snapshot:
        replacement = '        firstMode = count;\n' + replacement + '        if (firstMode > 0) {'
    else:
        replacement += '        if (count > 0) {'
    body = body.replace(marker, replacement)
    if separate_mode:
        body = body.replace('    s32 firstMode;', '    s32 firstMode;\n    s32 secondMode;')
        body = body.replace('    offset = mode;\n', '    secondMode = mode;\n')
        body = body.replace('if (offset != 2)', 'if (secondMode != 2)')
    return body


def candidates():
    yield 'baseline240', BASE
    for order, snapshot in itertools.product(itertools.permutations('coi'), (False, True)):
        name = ''.join(order)
        yield 'secondary-%s-snapshot%d' % (name, snapshot), setup_body(order, snapshot)
    for snapshot in (False, True):
        yield 'separate-mode-snapshot%d' % snapshot, setup_body('ioc', snapshot, True)
    yield 'primary-cursor-first', BASE.replace('        offset = 0;\n        cursor = output;\n',
        '        cursor = output;\n        offset = 0;\n', 1)
    for name, declaration in (('matrix', '    f32 (*matrix)[4];\n'),
            ('actorFlags', '    u32 actorFlags;\n'), ('cursor', '    u8 *cursor;\n')):
        body = BASE
        assert body.count(declaration) == body.count('    s32 offset;\n') == 1
        body = body.replace(declaration, '    s32 offset;\n', 1)
        at = body.index('    f32 converted[4][4];')
        body = body[:at] + body[at:].replace('    s32 offset;\n', declaration, 1)
        yield 'layout-offset-for-' + name, body
    for early in ('i', 'firstMode'):
        body = BASE
        declaration = '    s32 %s;\n' % early
        body = body.replace(declaration, '    s32 offset;\n', 1)
        at = body.index('    f32 converted[4][4];')
        start = body.index('    s32 offset;\n', at)
        if start != body.index('    s32 offset;\n'):
            body = body[:start] + body[start:].replace('    s32 offset;\n', declaration, 1)
        else:
            next_at = body.index('    s32 offset;\n', start + 1)
            body = body[:next_at] + body[next_at:].replace('    s32 offset;\n', declaration, 1)
        yield 'layout-offset-swap-' + early, body


def qualified_body():
    return dict(candidates())[SELECTED_NAME]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--diff', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-matrix-reflection-loop-setup'
    out.mkdir(exist_ok=True)
    retail = list(struct.unpack_from('>486I', (root / 'conker/conker.us.bin').read_bytes(), previous.compiler.ROM))
    records = []
    if args.diff:
        meta, words = previous.compile_candidate(root, out, 'selected-diff', qualified_body())
        text, functions, relocations = parse_object(out / 'selected-diff.o')
        target = functions[previous.compiler.FUNCTION]
        payload = text[target['value']:target['value'] + 1944]
        meta.update(object_size=target['size'], raw_sha256=hashlib.sha256(payload).hexdigest())
        (out / 'word-diff.json').write_text(json.dumps([
            dict(index=i, source='%08X' % a, retail='%08X' % b)
            for i, (a, b) in enumerate(zip(words, retail)) if a != b], indent=2) + '\n')
        print(json.dumps(meta, indent=2))
        for i, (a, b) in enumerate(zip(words, retail)):
            if a != b:
                print('%3d %08X %08X' % (i, a, b))
        return
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, words = previous.compile_candidate(root, out, name, body)
        meta.update(prefix_words=next((i for i, (a, b) in enumerate(zip(words, retail)) if a != b),
            min(len(words), len(retail))), conversion_s5=0x27B50084 in words,
            offset_s4=0x26940040 in words)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'],
            'prefix', meta['prefix_words'], 'roles', meta['conversion_s5'], meta['offset_s4'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
