"""Effectful predicate screens for func_150428D4; no form is an accepted match."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_text_measurer_candidates as screen


def candidates():
    reference = dict(screen.candidates())['capture-declaration-after-record']
    start = reference.index('                    useFont = 0;')
    end = reference.index('                    index++;', start)
    space = '''(*width = (s32)((u32)*width + 4),
                         lineHeight < 12 ? (lineHeight = 12) : 0, 0)'''
    metrics = '''(func_150415E0(glyph, &metrics.width, &metrics.height,
                             &metrics.baseline, &metrics.mode, &metrics.factor),
                         *width = (s32)((f32)*width + (f32)metrics.width * metrics.factor),
                         extent = (s32)((f32)(s32)((f32)metrics.height * metrics.factor) - metrics.baseline) + 1,
                         lineHeight < extent ? (lineHeight = extent) : 0,
                         (f32)*baseline < metrics.baseline ? (*baseline = (s32)metrics.baseline) : 0, 0)'''
    newline = '''(maximumWidth < *width ? (maximumWidth = *width) : 0,
                         *width = 0,
                         lineHeight < 12 ? (lineHeight = 12) : 0,
                         *height = (s32)((u32)*height + (u32)lineHeight),
                         lineHeight = 0, 0)'''
    predicates = {
        'or-effects': '(glyph == 0x60 && ' + space + ''') ||
                        (glyph != 0x60 && (glyph < 0xA1 || glyph >= 0xA8) &&
                         ((glyph >= 0xA8 && glyph < 0x100 && ''' + metrics + ''') ||
                          (glyph < 0xA1 && (text[index] != 0xA || ''' + newline + '))))',
        'and-effects': '(glyph != 0x60 || ' + space + ''') &&
                        (glyph < 0xA1 || glyph >= 0xA8) &&
                        (!(glyph >= 0xA8 && glyph < 0x100) || ''' + metrics + ''') &&
                        glyph < 0xA1 && (text[index] != 0xA || ''' + newline + ')',
        'ternary-effects': 'glyph == 0x60 ? ' + space + ''' :
                        (glyph < 0xA1 || glyph >= 0xA8) ?
                        (glyph >= 0xA8 && glyph < 0x100 ? ''' + metrics + ''' :
                         glyph < 0xA1 ? (text[index] != 0xA || ''' + newline + ') : 0) : 0',
    }
    for tag, predicate in predicates.items():
        named = reference[:start] + '                    useFont = ' + predicate + ';\n' + reference[end:]
        named = named.replace('width, useFont; } metrics;', 'width; } metrics;')
        direct = named.replace('    s32 useFont;\n', '').replace(
            '                    useFont = ' + predicate + ';\n                    index++;\n                    if (useFont) {',
            '                    if (' + predicate + ') {\n                        index++;').replace(
            '                    }\n                }\n            } while (text[index] != 0);',
            '                    } else {\n                        index++;\n                    }\n                }\n            } while (text[index] != 0);')
        for suffix, body in (('named', named), ('direct', direct)):
            name = tag + '-' + suffix
            yield name, body
            locals_body = body.replace(
                '    struct { f32 factor; s32 mode; f32 baseline; s32 height, width; } metrics;',
                '    s32 glyphWidth;\n    s32 glyphHeight;\n    f32 glyphBaseline;\n    s32 mode;\n    f32 factor;')
            for field, local in (('factor', 'factor'), ('mode', 'mode'), ('baseline', 'glyphBaseline'),
                                 ('height', 'glyphHeight'), ('width', 'glyphWidth')):
                locals_body = locals_body.replace('metrics.' + field, local)
            yield name + '-locals', locals_body
            if tag == 'or-effects':
                # Only these disjoint glyph branches may both be evaluated; retain the newline OR.
                yield 'disjoint-bitwise-' + suffix, locals_body.replace(' ||\n', ' |\n')
                if suffix == 'named':
                    yield name + '-void-address', locals_body.replace('                    useFont = ',
                        '                    (void *)&useFont;\n                    useFont = ', 1)
                    yield 'memory-lvalue-named', locals_body.replace('useFont = ',
                        '*(s32 *)(void *)&useFont = ').replace('if (useFont)', 'if (*(s32 *)(void *)&useFont)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-text-measurer-logic'
    out.mkdir(exist_ok=True)
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        meta, words = screen.compile_candidate(root, out, name, body)
        meta.update(installable=False,
                    t0_resets=[i for i, word in enumerate(words) if word == 0x00004025],
                    t0_spills=[i for i, word in enumerate(words) if word & 0xFFFF0000 == 0xAFA80000],
                    t0_reloads=[i for i, word in enumerate(words) if word & 0xFFFF0000 == 0x8FA80000])
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'receipts.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
