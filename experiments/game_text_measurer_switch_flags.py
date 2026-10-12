"""Five-field statement dispatch and register-hint controls; no accepted match."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_text_measurer_logic_candidates as logic


def reference():
    body = logic._inputs()[0].replace('width, useFont; } metrics;', 'width; } metrics;')
    return body.replace('                            metrics.useFont = useFont;\n', '').replace(
        '                            useFont = metrics.useFont;\n', '')


def glyph_switch(body):
    return body.replace('                    if (glyph == 0x60) {',
        '                    switch (glyph) {\n                    case 0x60:').replace(
        '                    } else if (glyph < 0xA1 || glyph >= 0xA8) {',
        '                        break;\n                    default:\n                    if (glyph < 0xA1 || glyph >= 0xA8) {').replace(
        '                    }\n                    index++;',
        '                    }\n                    break;\n                    }\n                    index++;')


def newline_switch(body):
    return body.replace('                            if (text[index] == 0xA) {',
        '                            switch (text[index]) {\n                            case 0xA:').replace(
        '                            } else {\n                                useFont = 1;\n                            }',
        '                                break;\n                            default:\n                                useFont = 1;\n                                break;\n                            }')


def candidates():
    body = reference()
    yield 'five-field-if-reference', body
    yield 'five-field-newline-switch', newline_switch(body)
    yield 'five-field-glyph-switch', glyph_switch(body)
    yield 'five-field-both-switches', glyph_switch(newline_switch(body))
    yield 'five-field-register-flag', body.replace('    s32 useFont;', '    register s32 useFont;')
    yield 'five-field-scoped-register-flag', body.replace('    s32 useFont;\n', '').replace(
        '                    useFont = 0;', '                    {\n                    register s32 useFont = 0;').replace(
        '                }\n            } while (text[index] != 0);',
        '                    }\n                }\n            } while (text[index] != 0);')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = dict(candidates())
    parser.add_argument('--filter', choices=tuple(sources))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-text-measurer-switch-flags'
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
