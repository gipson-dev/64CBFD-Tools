"""Measure source-level lifetime and loop shapes for the full scratch preparer."""
import itertools
import json
from pathlib import Path

from tools.experiments import game_animation_scratch_prepare_candidates as prepare


def loop(body):
    result = body.replace('        state = node;\n        for (bank = 0; bank != banks; bank++, state += 0x1D0) {',
        '        bank = 0;\n        if (banks > 0) {\n            state = node;\n            do {').replace(
        '            }\n        }\n    }\n}',
        '            }\n            bank++;\n            state += 0x1D0;\n            } while (bank != banks);\n        }\n    }\n}')
    opening, inner = result.split('            do {\n', 1)
    inner, closing = inner.split('            } while (bank != banks);', 1)
    return opening + '            do {\n' + ''.join('    ' + line for line in inner.splitlines(keepends=True)) + \
        '            } while (bank != banks);' + closing


SELECTED = loop(prepare.BASE)


def install(before):
    if before.count(prepare.BASE) != 1:
        raise ValueError('stale complete animation scratch preparation body')
    return before.replace(prepare.BASE, SELECTED)


def candidates():
    yield 'baseline', prepare.BASE
    for guarded, source, aligned, split in itertools.product((False, True), repeat=4):
        body = prepare.BASE
        if source:
            body = body.replace('    u32 address;', '    u32 source;\n    u32 address;').replace(
                'else if (*(u8 **)(fields + 0x28) != NULL)',
                'else if ((source = *(u32 *)(fields + 0x28)) != 0)').replace(
                'address = (u32)*(u8 **)(fields + 0x28) + length * index;',
                'address = source + length * index;')
        if aligned:
            body = body.replace('    u8 offset;', '    u8 *aligned;\n    u8 offset;').replace(
                '                scratch = (u8 *)(((u32)scratch + 15) >> 4 << 4);',
                '                aligned = (u8 *)(((u32)scratch + 15) >> 4 << 4);\n                scratch = aligned;', 1).replace(
                '*(u8 **)(fields + 0x30) = scratch + offset;',
                '*(u8 **)(fields + 0x30) = aligned + offset;').replace(
                'func_1000480C(address, scratch, amount);',
                'func_1000480C(address, aligned, amount);', 1)
        if split:
            body = body.replace('    u8 offset;', '    u8 firstOffset;\n    u8 offset;').replace(
                '                offset = address & 3;\n                address -= offset;',
                '                firstOffset = address & 3;\n                address -= firstOffset;').replace(
                '                amount += offset;', '                amount += firstOffset;').replace(
                '*(u8 **)(fields + 0x30) = scratch + offset;',
                '*(u8 **)(fields + 0x30) = scratch + firstOffset;').replace(
                '*(u8 **)(fields + 0x30) = aligned + offset;',
                '*(u8 **)(fields + 0x30) = aligned + firstOffset;').replace(
                '                if (amount < 0xC8U) {',
                '                offset = firstOffset;\n                if (amount < 0xC8U) {', 1)
        name = 'shape-' + ''.join(str(int(v)) for v in (guarded, source, aligned, split))
        yield name, loop(body) if guarded else body
        if guarded and aligned:
            advanced = body.replace(
                '                aligned = (u8 *)(((u32)scratch + 15) >> 4 << 4);',
                '                scratch += 15;\n                aligned = (u8 *)((u32)scratch >> 4 << 4);')
            yield name + '-advance', loop(advanced)
            yield name + '-advance-fields', loop(advanced.replace(
                'fields = node + bank * 4;', 'fields = bank * 4 + node;'))
        if guarded and aligned and split:
            yield name + '-increment', loop(body.replace('if (end <= frame + 1.0f)',
                'if (end <= (frame += 1.0f))'))
            yield name + '-subtract', loop(body.replace('if (end <= frame + 1.0f)',
                'if (end <= frame - -1.0f)'))


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-animation-scratch-shape'
    records = []
    for name, body in candidates():
        meta, _ = prepare.compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
