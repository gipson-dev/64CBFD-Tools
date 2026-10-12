"""Font qualifier controls for func_150428D4, not recovered declarations."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_text_measurer_logic_candidates as logic


QUALIFIERS = {
    'plain': 'extern u8 *D_80085994;',
    'volatile-pointer': 'extern u8 *volatile D_80085994;',
    'volatile-bytes': 'extern volatile u8 *D_80085994;',
    'volatile-pointer-and-bytes': 'extern volatile u8 *volatile D_80085994;',
}


def initializer():
    reference, start, end, space, metrics, newline = logic._inputs()
    left = 'glyph == 0x60 ? ' + space + ' : glyph < 0xA1 ? (text[index] != 0xA || ' + newline + ') : 0'
    right = '(glyph >= 0xA8 && glyph < 0x100 ? ' + metrics + ' : 0)'
    record = '    struct { f32 factor; s32 mode; f32 baseline; s32 height, width; } metrics;\n'
    body = reference[:start] + ('                    {\n'
        '                    s32 useFont = ' + left + ';\n' + record +
        '                    useFont = useFont | ' + right + ';\n') + reference[end:]
    body = body.replace('    struct { f32 factor; s32 mode; f32 baseline; s32 height, width, useFont; } metrics;\n', '')
    body = body.replace('    s32 useFont;\n', '')
    body = body.replace('    u8 **fontAddress = &D_80085994;\n', '').replace('(*fontAddress)[', 'D_80085994[')
    body = body.replace('                }\n            } while (text[index] != 0);',
                        '                    }\n                }\n            } while (text[index] != 0);')
    return body


def candidates():
    body = initializer()
    for name, declaration in QUALIFIERS.items():
        yield name, body, logic.screen.DECLARATIONS.replace(QUALIFIERS['plain'], declaration)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', choices=tuple(QUALIFIERS))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-text-measurer-font-controls'
    out.mkdir(exist_ok=True)
    records = []
    for name, body, declarations in candidates():
        if args.filter and name != args.filter:
            continue
        meta, words = logic.screen.compile_candidate(root, out, name, body, declarations=declarations)
        meta.update(installable=False, recovered_declaration=False,
                    t0_resets=[i for i, word in enumerate(words) if word == 0x00004025],
                    t0_spills=[(i, word & 65535) for i, word in enumerate(words) if word & 0xFFFF0000 == 0xAFA80000],
                    t0_reloads=[(i, word & 65535) for i, word in enumerate(words) if word & 0xFFFF0000 == 0x8FA80000])
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'receipts.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
