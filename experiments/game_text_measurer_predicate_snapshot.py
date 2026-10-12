"""Explicit assignment and pure-predicate controls, never accepted matches."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_text_measurer_font_controls as fonts
from tools.experiments import game_text_measurer_logic_candidates as logic


def assignment_candidates():
    compound = dict(logic.compound_candidates())
    named = compound['compound-named'].replace('useFont |= (', 'useFont = useFont | (')
    prefix, tail = named.split('    if (text != NULL) {', 1)
    inline = prefix + '    if (text != NULL) {' + tail.replace('useFont', '(*(s32 *)(void *)&useFont)')
    yield 'explicit-named', named
    yield 'explicit-inline-address', inline
    yield 'explicit-scoped', compound['compound-scoped-initializer'].replace('useFont |= (', 'useFont = useFont | (')


def default_candidates():
    seed = fonts.initializer()
    start = seed.index('                    s32 useFont = ')
    end = seed.index('                    index++;', start)
    _, _, _, space, metrics, newline = logic._inputs()
    predicate = '(glyph != 0x60 && glyph < 0xA1 && text[index] != 0xA)'
    effects = ('glyph == 0x60 ? ' + space + ' : glyph >= 0xA8 && glyph < 0x100 ? ' + metrics +
               ' : glyph < 0xA1 && !useFont ? ' + newline + ' : 0')
    body = seed[:start] + ('                    s32 useFont = ' + predicate + ';\n'
        '                    struct { f32 factor; s32 mode; f32 baseline; s32 height, width; } metrics;\n'
        '                    useFont = useFont | (' + effects + ');\n') + seed[end:]
    yield 'pure-ordinary-direct-font', body
    yield 'pure-ordinary-font-address', body.replace('    s32 extent;',
        '    u8 **fontAddress = &D_80085994;\n    s32 extent;').replace('D_80085994[', '(*fontAddress)[')
    yield 'pure-ordinary-discard-effects', body.replace('useFont = useFont | (' + effects + ');',
                                                       '(void)(' + effects + ');')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--assignments', action='store_true')
    modes.add_argument('--defaults', action='store_true')
    names = dict((*assignment_candidates(), *default_candidates()))
    parser.add_argument('--filter', choices=tuple(names))
    args = parser.parse_args()
    sources = dict(assignment_candidates() if args.assignments else default_candidates())
    if args.filter and args.filter not in sources:
        parser.error('filter is not available in the selected mode')
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-text-measurer-predicate-snapshot'
    out.mkdir(exist_ok=True)
    records = []
    for name, body in sources.items():
        if args.filter and args.filter != name:
            continue
        meta, words = logic.screen.compile_candidate(root, out, name, body)
        meta.update(installable=False,
                    t0_resets=[i for i, w in enumerate(words) if w == 0x00004025],
                    t0_spills=[(i, w & 65535) for i, w in enumerate(words) if w & 0xFFFF0000 == 0xAFA80000],
                    t0_reloads=[(i, w & 65535) for i, w in enumerate(words) if w & 0xFFFF0000 == 0x8FA80000])
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / ('assignments.json' if args.assignments else 'defaults.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
