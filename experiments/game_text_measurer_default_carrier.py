"""Real default-false and split flag carriers; all remain non-installable."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_text_measurer_font_controls as fonts
from tools.experiments import game_text_measurer_logic_candidates as logic


def candidates():
    seed = fonts.initializer()
    start = seed.index('                    s32 useFont = ')
    end = seed.index('                    index++;', start)
    _, _, _, space, metrics, newline = logic._inputs()
    space = space.rsplit(', 0)', 1)[0] + ', useFont)'
    metrics = metrics.rsplit(', 0)', 1)[0] + ', useFont)'
    newline = newline.rsplit(', 0)', 1)[0] + ', useFont)'
    left = '(glyph == 0x60 ? ' + space + ' : glyph < 0xA1 ? (text[index] != 0xA || ' + newline + ') : useFont)'
    right = '(glyph >= 0xA8 && glyph < 0x100 ? ' + metrics + ' : useFont)'
    record = '                    struct { f32 factor; s32 mode; f32 baseline; s32 height, width; } metrics;\n'
    body = seed[:start] + ('                    s32 useFont = 0;\n' + record +
        '                    useFont = ' + left + ' | ' + right + ';\n') + seed[end:]
    yield 'whole-shared-default', body
    right_false = right.replace(', useFont)', ', 0)').replace(': useFont)', ': 0)')
    whole = '                    useFont = ' + left + ' | ' + right_false + ';\n'
    literal = body.replace(right, right_false)
    yield 'whole-metrics-false', literal
    split = literal.replace(whole, '                    useFont = ' + left + ';\n'
                                  '                    useFont = useFont | ' + right_false + ';\n')
    yield 'split-direct-font', split
    address_declaration = '    u8 **fontAddress = &D_80085994;\n'
    address = split.replace('    s32 extent;', address_declaration + '    s32 extent;').replace('D_80085994[', '(*fontAddress)[')
    yield 'split-font-address', address
    yield 'split-inline-address', address.replace(address_declaration, '').replace(
        '(*fontAddress)[', '(*(u8 **)(void *)&D_80085994)[')
    yield 'split-address-after-record', address.replace(address_declaration, '').replace(record,
        record + '                    u8 **fontAddress = &D_80085994;\n')
    yield 'split-address-font-only', address.replace(address_declaration, '').replace(
        '                    if (useFont) {', '                    if (useFont) {\n                        u8 **fontAddress = &D_80085994;')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = dict(candidates())
    parser.add_argument('--filter', choices=tuple(sources))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-text-measurer-default-carrier'
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
    (out / 'receipts.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
