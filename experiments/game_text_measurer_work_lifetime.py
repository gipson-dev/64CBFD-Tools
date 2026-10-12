"""Reuse the real extent word across disjoint address/height lifetimes."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_text_measurer_default_carrier as source


def address_work(body):
    return body.replace('                    if (useFont) {',
        '                    if (useFont) {\n                        extent = (s32)(u32)&D_80085994;').replace(
        'D_80085994[', '(*(u8 **)(u32)extent)[')


def candidates():
    seed = dict(source.candidates())['split-direct-font']
    yield 'direct-control', seed
    yield 'integer-address-work', address_work(seed)
    start = seed.index('                    s32 useFont = 0;')
    end = seed.index('                    index++;', start)
    _, _, _, space, metrics, newline = source.logic._inputs()
    space = space.rsplit(', 0)', 1)[0] + ', useFont)'
    newline = newline.rsplit(', 0)', 1)[0] + ', useFont)'
    record = '                    struct { f32 factor; s32 mode; f32 baseline; s32 height, width; } metrics;\n'
    dispatch = ('                    s32 useFont = 0;\n' + record +
        '                    if (glyph == 0x60) {\n'
        '                        useFont = ' + space + ';\n'
        '                        goto metric_join;\n'
        '                    }\n'
        '                    if (glyph < 0xA1) goto ordinary_glyph;\n'
        'metric_join:\n'
        '                    useFont = useFont | (glyph >= 0xA8 && glyph < 0x100 ? ' + metrics + ' : 0);\n'
        '                    goto dispatch_done;\n'
        'ordinary_glyph:\n'
        '                    useFont = (text[index] != 0xA || ' + newline + ');\n'
        '                    goto metric_join;\n'
        'dispatch_done:\n')
    forward = address_work(seed[:start] + dispatch + seed[end:])
    yield 'forward-ordinary-work', forward
    ternary = forward.replace('                    useFont = (text[index] != 0xA || ' + newline + ');\n',
        '                    useFont = text[index] == 0xA ? ' + newline + ' : 1;\n')
    yield 'forward-ternary-work', ternary
    # Identity assignment is a compiler-shape control, not recovered source.
    excluded = ternary.replace('                    if (glyph < 0xA1) goto ordinary_glyph;',
        '                    if (glyph < 0xA1) goto ordinary_glyph;\n'
        '                    if (glyph < 0xA8) goto excluded_glyph;').replace('dispatch_done:\n',
        'excluded_glyph:\n                    useFont = useFont | 0;\ndispatch_done:\n')
    yield 'excluded-join-control', excluded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = dict(candidates())
    parser.add_argument('--filter', choices=tuple(sources))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-text-measurer-work-lifetime'
    out.mkdir(exist_ok=True)
    records = []
    for name, body in sources.items():
        if args.filter and args.filter != name:
            continue
        meta, words = source.logic.screen.compile_candidate(root, out, name, body)
        meta.update(installable=False,
            t0_resets=[i for i, w in enumerate(words) if w == 0x00004025],
            t0_spills=[(i, w & 65535) for i, w in enumerate(words) if w & 0xFFFF0000 == 0xAFA80000],
            t0_reloads=[(i, w & 65535) for i, w in enumerate(words) if w & 0xFFFF0000 == 0x8FA80000])
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'receipts.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
