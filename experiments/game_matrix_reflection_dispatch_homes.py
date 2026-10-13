"""Recover direct home loads by preserving the two original dispatch snapshots."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_matrix_reflection_index_lifetime as previous

BASE = dict(previous.cold_loop_candidates())['cold-c1-o1']
SELECTED_NAME = 'actor-gate-inputFixed'


def dispatch_body(volatile=False, later_snapshot=False, reverse=False):
    body = BASE
    assert body.count('    s32 matrixOffset;\n') == 1
    assert body.count('                matrixOffset = i * 64;\n') == 4
    body = body.replace('    s32 matrixOffset;', '    s32 firstMode;')
    body = body.replace('                matrixOffset = i * 64;\n', '')
    body = body.replace('input + matrixOffset', 'input + i * 64')
    body = body.replace('output + matrixOffset', 'output + i * 64')
    if volatile:
        body = body.replace('s32 mode,', 'volatile s32 mode,', 1)
    opening = '    if (mode == 1 || mode == 0) {\n'
    split = '    } else if (mode == 2) {\n'
    ending = '    } else {\n        return;\n    }\n'
    assert body.count(opening) == body.count(split) == body.count(ending) == 1
    prefix, rest = body.split(opening, 1)
    primary, rest = rest.split(split, 1)
    secondary, tail = rest.rsplit(ending, 1)
    if later_snapshot:
        marker = '        } else if (distance < nearDistance) {\n            if (mode == 0) {'
        assert primary.count(marker) == 1
        primary = primary.replace(marker,
            '        } else {\n            firstMode = mode;\n            if (distance < nearDistance) {\n            if (firstMode == 0) {')
        marker = '                (farDistance - nearDistance)));\n        }\n'
        assert primary.count(marker) == 1
        primary = primary.replace(marker, marker + '        }\n')
    dispatch = '''    firstMode = mode;
    if (firstMode == 1) goto primary;
    offset = mode;
    if (firstMode != 0) goto secondary_check;
primary:
'''
    if reverse:
        dispatch = dispatch.replace('if (firstMode != 0) goto secondary_check;',
            'if (firstMode == 0) goto primary;\n    goto secondary_check;')
    return prefix + dispatch + '    {\n' + primary + '    }\n    goto finish;\nsecondary_check:\n' + (
        '    if (offset != 2) return;\n    {\n' + secondary + '    }\nfinish:\n' + tail)


def candidates():
    yield 'cold329', BASE
    for volatile in (False, True):
        for later in (False, True):
            for reverse in (False, True):
                yield 'dispatch-v%d-later%d-reverse%d' % (volatile, later, reverse), dispatch_body(volatile, later, reverse)
    base = dispatch_body(True, True)
    for primary, secondary in ((True, False), (False, True), (True, True)):
        body = base
        marker = '                matrix[3][3] = 1.0f;\n'
        assert body.count(marker) == 2
        for index, enabled in reversed(list(enumerate((primary, secondary)))):
            if enabled:
                at = body.index(marker, body.index('secondary_check:\n')) if index else body.index(marker)
                body = body[:at] + body[at:].replace(marker,
                    marker + '                matrix = (f32 (*)[4])(input + i * 64);\n', 1)
        yield 'address-primary%d-secondary%d' % (primary, secondary), body
        body = body.replace('input + i * 64', 'input + firstMode').replace('output + i * 64', 'output + firstMode')
        body = body.replace('            if (inputFixed != 0) {\n',
            '            if (inputFixed != 0) {\n                firstMode = i * 64;\n')
        body = body.replace('            } else {\n                matrix = (f32 (*)[4])(input + offset);',
            '            } else {\n                firstMode = i * 64;\n                matrix = (f32 (*)[4])(input + offset);')
        yield 'index-primary%d-secondary%d' % (primary, secondary), body
    for late_declaration in (False, True):
        body = base.replace('firstMode', 'i')
        assert body.count('    s32 i;\n') == 2
        body = body.replace('    s32 i;\n', '', 1)
        if late_declaration:
            body = body.replace('    f32 distance;\n', '    f32 distance;\n    f32 value;\n')
        else:
            at = body.index('    s32 offset;\n')
            body = body[:at] + body[at:].replace('    s32 offset;\n', '    s32 offset;\n    f32 value;\n', 1)
        old = '''            distance = matrix[3][1];
            destination[3][1] = distance - ((distance - pivotY) + (distance - pivotY));'''
        assert body.count(old) == 1
        body = body.replace(old, '''            value = matrix[3][1];
            destination[3][1] = value - ((value - pivotY) + (value - pivotY));''')
        yield 'split-float-late%d' % late_declaration, body
    for unsigned in (False, True):
        for primary, secondary in ((True, False), (False, True), (True, True)):
            body = base.replace('    s32 i;', '    u32 i;') if unsigned else base
            left, right = body.split('secondary_check:\n', 1)
            transform = lambda part: re.sub(r'([ \t]*)record\[4\] = ([^;]+);',
                lambda m: m[1] + 'i = ' + m[2] + ';\n' + m[1] + 'record[4] = i;', part)
            if primary:
                left = transform(left)
            if secondary:
                right = transform(right)
            yield 'pixel-u%d-primary%d-secondary%d' % (unsigned, primary, secondary), left + 'secondary_check:\n' + right
    for primary, secondary in ((True, False), (False, True), (True, True)):
        left, right = base.split('secondary_check:\n', 1)
        parts = [left, right]
        for index, enabled in enumerate((primary, secondary)):
            if enabled:
                marker = '                matrix[3][3] = 1.0f;\n'
                assert parts[index].count(marker) == 1
                parts[index] = parts[index].replace(marker,
                    marker + '                matrix = (f32 (*)[4])(input + i * 64);\n')
                parts[index] = parts[index].replace('output + i * 64', 'output + offset')
        current = 'secondary_check:\n'.join(parts)
        yield 'cursor-output-primary%d-secondary%d' % (primary, secondary), current
        if primary and secondary:
            prefix, tail = current.rsplit('finish:\n', 1)
            assert tail.count('outputFixed') == 2
            for carrier in ('inputFixed', 'i', 'offset', 'firstMode'):
                yield 'actor-gate-' + carrier, prefix + 'finish:\n' + tail.replace('outputFixed', carrier)


def qualified_body():
    return dict(candidates())[SELECTED_NAME]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-matrix-reflection-dispatch-homes'
    out.mkdir(exist_ok=True)
    retail = list(struct.unpack_from('>486I', (root / 'conker/conker.us.bin').read_bytes(), previous.previous.previous.ROM))
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, words = previous.previous.previous.compile_candidate(root, out, name, body)
        meta.update(prefix_words=next((i for i, (a, b) in enumerate(zip(words, retail)) if a != b),
            min(len(words), len(retail))))
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], 'prefix', meta['prefix_words'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
