"""Effectful predicate screens for func_150428D4; no form is an accepted match."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_text_measurer_candidates as screen


def _inputs():
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
    return reference, start, end, space, metrics, newline


def candidates():
    reference, start, end, space, metrics, newline = _inputs()
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


def carrier_candidates():
    reference, start, end, space, metrics, newline = _inputs()
    ordinary = '(text[index] != 0xA || ' + newline + ')'
    lefts = {
        'simple': 'glyph == 0x60 ? ' + space + ' : glyph < 0xA1 ? ' + ordinary + ' : 0',
        'retail-gates': 'glyph == 0x60 ? ' + space + ''' :
                        (glyph < 0xA1 || glyph >= 0xA8) ?
                        (glyph >= 0xA8 && glyph < 0x100 ? 0 :
                         glyph < 0xA1 ? ''' + ordinary + ' : 0) : 0',
    }
    right = '(glyph >= 0xA8 && glyph < 0x100 ? ' + metrics + ' : 0)'
    for tag, left in lefts.items():
        predicate = '(' + left + ') | ' + right
        named = reference[:start] + '                    useFont = ' + predicate + ';\n' + reference[end:]
        named = named.replace('width, useFont; } metrics;', 'width; } metrics;')
        direct = named.replace('    s32 useFont;\n', '').replace(
            '                    useFont = ' + predicate + ';\n                    index++;\n                    if (useFont) {',
            '                    if (' + predicate + ') {\n                        index++;').replace(
            '                    }\n                }\n            } while (text[index] != 0);',
            '                    } else {\n                        index++;\n                    }\n                }\n            } while (text[index] != 0);')
        for suffix, body in (('named', named), ('direct', direct)):
            yield 'carrier-' + tag + '-' + suffix, body
        if tag == 'simple':
            guards = (('lineHeight < 12', 'lineHeight = 12'),
                      ('maximumWidth < *width', 'maximumWidth = *width'),
                      ('lineHeight < extent', 'lineHeight = extent'),
                      ('(f32)*baseline < metrics.baseline', '*baseline = (s32)metrics.baseline'))
            arms, discard, assignments = named, named, named
            for condition, assignment in guards:
                original = condition + ' ? (' + assignment + ') : 0'
                arms = arms.replace(original, '(' + condition + ' ? (void)(' + assignment + ') : (void)0)')
                discard = discard.replace(original, '(void)(' + original + ')')
                if assignment.startswith('*baseline'):
                    assignments = assignments.replace(original,
                        '(' + condition + ' ? (void)(' + assignment + ') : (void)0)')
                else:
                    destination, value = assignment.split(' = ')
                    assignments = assignments.replace(original,
                        destination + ' = ' + condition + ' ? ' + value + ' : ' + destination)
            yield 'carrier-void-arms', arms
            yield 'carrier-discard-casts', discard
            yield 'carrier-integer-assignments', assignments


def layout_candidates():
    simple = dict(carrier_candidates())['carrier-simple-named']
    record = '    struct { f32 factor; s32 mode; f32 baseline; s32 height, width; } metrics;\n'
    scalars = '    f32 factor;\n    s32 mode;\n    f32 glyphBaseline;\n    s32 glyphHeight;\n    s32 glyphWidth;\n'

    def fields(body):
        body = body.replace(record, scalars)
        for field, name in (('factor', 'factor'), ('mode', 'mode'), ('baseline', 'glyphBaseline'),
                            ('height', 'glyphHeight'), ('width', 'glyphWidth')):
            body = body.replace('metrics.' + field, name)
        return body

    reference, start, end, space, metrics, newline = _inputs()
    ordinary = '(glyph != 0x60 && glyph < 0xA1 && (text[index] != 0xA || ' + newline + '))'
    effects = '(glyph == 0x60 ? ' + space + ' : (glyph >= 0xA8 && glyph < 0x100 ? ' + metrics + ' : 0))'
    predicate = reference[:start] + '                    useFont = ' + ordinary + ' | ' + effects + ';\n' + reference[end:]
    predicate = predicate.replace('width, useFont; } metrics;', 'width; } metrics;')
    ternary = reference[:start] + '                    useFont = (glyph == 0x60 ? 0 : glyph < 0xA1 ? (text[index] != 0xA || ' + newline + ') : 0) | ' + effects + ';\n' + reference[end:]
    ternary = ternary.replace('width, useFont; } metrics;', 'width; } metrics;')
    def direct(body):
        return body.replace('    u8 **fontAddress = &D_80085994;\n', '').replace('(*fontAddress)[', 'D_80085994[')
    yield 'flag-before-record', simple.replace(record + '    s32 useFont;\n', '    s32 useFont;\n' + record)
    yield 'scalar-metrics', fields(simple)
    yield 'scalar-metrics-flag-first', fields(simple.replace(record + '    s32 useFont;\n', '    s32 useFont;\n' + record))
    yield 'ordinary-before-effects', predicate
    yield 'ordinary-before-effects-scalars', fields(predicate)
    yield 'ordinary-before-effects-direct-font', direct(predicate)
    yield 'ternary-before-effects', ternary
    yield 'ternary-before-effects-direct-font', direct(ternary)
    yield 'record-scope-text', simple.replace(record, '').replace('    if (text != NULL) {', '    if (text != NULL) {\n' + record)
    yield 'record-scope-normalize', simple.replace(record, '').replace('                } else {\n                    glyph =',
        '                } else {\n' + record + '                    glyph =', 1)


def compound_candidates():
    reference, start, end, space, metrics, newline = _inputs()
    ordinary = '(text[index] != 0xA || ' + newline + ')'
    predicate = 'glyph == 0x60 ? ' + space + ' : (glyph < 0xA1 || glyph >= 0xA8) ? (glyph >= 0xA8 && glyph < 0x100 ? ' + metrics + ' : glyph < 0xA1 ? ' + ordinary + ' : 0) : 0'
    body = reference[:start] + '                    useFont = 0;\n                    useFont |= (' + predicate + ');\n' + reference[end:]
    body = body.replace('width, useFont; } metrics;', 'width; } metrics;')
    yield 'compound-named', body
    prefix, tail = body.split('    if (text != NULL) {', 1)
    yield 'compound-inline-void-address', prefix + '    if (text != NULL) {' + tail.replace('useFont', '(*(s32 *)(void *)&useFont)')
    record = '    struct { f32 factor; s32 mode; f32 baseline; s32 height, width; } metrics;\n'
    scoped = body.replace('    s32 useFont;\n', '').replace(record, '')
    scoped = scoped.replace('                    useFont = 0;',
        '                    {\n                    s32 useFont = 0;\n' + record)
    scoped = scoped.replace('                }\n            } while (text[index] != 0);',
        '                    }\n                }\n            } while (text[index] != 0);')
    yield 'compound-scoped-initializer', scoped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--carriers', action='store_true')
    modes.add_argument('--layouts', action='store_true')
    modes.add_argument('--compound', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-text-measurer-logic'
    out.mkdir(exist_ok=True)
    records = []
    sources = (compound_candidates() if args.compound else layout_candidates() if args.layouts
               else carrier_candidates() if args.carriers else candidates())
    for name, body in sources:
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
