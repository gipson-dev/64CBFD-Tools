"""Repeated real glyph predicates; none is a complete accepted retail match."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_text_measurer_work_lifetime as work


def candidates():
    base = dict(work.candidates())['forward-ternary-work']
    yield 'forward-control', base
    metric = 'glyph >= 0xA8 && glyph < 0x100 ?'
    yield 'repeated-ordinary-range', base.replace(metric,
        'glyph >= 0xA1 && glyph >= 0xA8 && glyph < 0x100 ?')
    yield 'repeated-range-gate', base.replace(metric,
        '(glyph < 0xA1 || glyph >= 0xA8) && glyph >= 0xA8 && glyph < 0x100 ?')
    # Space jumps to the metric join too, so this real predicate needs a definition before that branch.
    cached = base.replace('                    s32 useFont = 0;',
        '                    s32 useFont = 0;\n                    s32 ordinary = glyph < 0xA1;').replace(
        '                    if (glyph < 0xA1) goto ordinary_glyph;',
        '                    if (ordinary) goto ordinary_glyph;').replace(
        metric, '!ordinary && glyph >= 0xA8 && glyph < 0x100 ?')
    yield 'initialized-ordinary-predicate', cached


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = dict(candidates())
    parser.add_argument('--filter', choices=tuple(sources))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-text-measurer-repeated-predicate'
    out.mkdir(exist_ok=True)
    records = []
    for name, body in sources.items():
        if args.filter and args.filter != name:
            continue
        meta, words = work.source.logic.screen.compile_candidate(root, out, name, body)
        meta.update(installable=False,
            t0_resets=[i for i, w in enumerate(words) if w == 0x00004025],
            t0_spills=[(i, w & 65535) for i, w in enumerate(words) if w & 0xFFFF0000 == 0xAFA80000],
            t0_reloads=[(i, w & 65535) for i, w in enumerate(words) if w & 0xFFFF0000 == 0x8FA80000])
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'receipts.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
