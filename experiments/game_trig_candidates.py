"""Screen complete single-precision Game trig bodies against retail words."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-single-precision-trig'
BASELINE_ELF = '79eb4f3261dcc2cff366d6e1dcddef48cb1c6e6b923821272d3b56c709a82e10'
TARGETS = {'cosf': (0x15047C00, 0x750B0, 88, 85), 'sinf': (0x15047D60, 0x75210, 104, 104)}
PATHS = {
    'elf': 'conker/build/conker.us.elf', 'progress': 'conker/progress.csv',
    'guards': 'conker/retail_word_patches.us.csv', 'makefile': 'conker/Makefile',
    'functions': 'conker/include/functions.h', 'variables': 'conker/include/variables.h',
    'structs': 'conker/include/structs.h',
}
for _name in TARGETS:
    PATHS[_name] = 'conker/src/libultra/gu/' + _name + '.c'
    PATHS[_name + '-asm'] = 'conker/asm/nonmatchings/libultra/gu/' + _name + '/' + _name + '.s'
BASELINE = {
    'elf': BASELINE_ELF,
    'progress': '005fd7682d37802a2b7591cfb023648b6a083c8df6b957bdfedd737222cad68e',
    'guards': 'b0f5425a5a3fbe2a1a44898f5c5499b781cf0598532b595dae1c81c7534b4d99',
    'makefile': '838070597f76ea2f7182c158dfb6710946cfcabcb5435e994f93cdb99340e313',
    'functions': '2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81',
    'variables': '1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8',
    'structs': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'cosf': '24b2ab8ae34242e239bb94f1652c1684df2d86263b68298374aed2b9d71c1db6',
    'sinf': 'a27d4e88a35dccd6d654edad3dfc1dabd2e05098469d74407a3eb6a9b6a75303',
    'cosf-asm': 'adaa909a91cdbdc98cd4a7c3875d1be983310f6a4e4e3adcc2f46b203bc29c9d',
    'sinf-asm': 'aaa2e4b725d2370cf7cc8f09860753184858f98c2a54635bc4ffad935b5916bd',
}

PREAMBLE = '''#include <ultra64.h>
#include "functions.h"
#include "variables.h"
'''
COS = '''extern f32 D_80085EA0, D_80085EA4, D_80085EA8, D_80085EAC;
extern f32 D_80098D70[];

/* Game's single-precision half-period reduction and sine polynomial. */
f32 cosf(f32 angle) {
    f32 reduced, squared, polynomial, periods, result;
    s32 period, raw, exponent;

    raw = *(s32 *)&angle;
    exponent = (raw >> 22) & 0x1FF;
    if (exponent < 0x136) {
        reduced = angle > 0.0f ? angle : -angle;
        periods = reduced * D_80085EA0 + 0.5f;
        period = (s32)(periods >= 0.0f ? periods + 0.5f : periods - 0.5f);
        periods = period - 0.5f;
        reduced = reduced - periods * D_80085EA4;
        reduced = reduced - periods * D_80085EA8;
        squared = reduced * reduced;
        polynomial = ((D_80098D70[4] * squared + D_80098D70[3]) * squared +
                      D_80098D70[2]) * squared + D_80098D70[1];
        result = reduced + (reduced * squared) * polynomial;
        if ((period & 1) == 0) {
            return result;
        }
        return -result;
    }
    if (angle != angle) {
        return D_8002C920;
    }
    return D_80085EAC;
}
'''
SIN = '''/* Game's single-precision small-angle and full-period sine paths. */
f32 sinf(f32 angle) {
    f32 reduced, squared, polynomial, periods, result;
    s32 period, raw, exponent;

    raw = *(s32 *)&angle;
    exponent = (raw >> 22) & 0x1FF;
    if (exponent < 0xFF) {
        reduced = angle;
        if (exponent >= 0xE6) {
            squared = reduced * reduced;
            polynomial = ((D_80098D90[4] * squared + D_80098D90[3]) * squared +
                          D_80098D90[2]) * squared + D_80098D90[1];
            result = reduced + (reduced * squared) * polynomial;
            return result;
        }
        return angle;
    }
    if (exponent < 0x136) {
        reduced = angle;
        periods = reduced * D_80085EB0;
        period = (s32)(periods >= 0.0f ? periods + 0.5f : periods - 0.5f);
        periods = period;
        reduced = reduced - periods * D_80085EB4;
        reduced = reduced - periods * D_80085EB8;
        squared = reduced * reduced;
        polynomial = ((D_80098D90[4] * squared + D_80098D90[3]) * squared +
                      D_80098D90[2]) * squared + D_80098D90[1];
        result = reduced + (reduced * squared) * polynomial;
        if ((period & 1) == 0) {
            return result;
        }
        return -result;
    }
    if (angle != angle) {
        return D_8002C920;
    }
    return D_80085EBC;
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed Game trig baseline input')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps({key: hashlib.sha256(value).hexdigest() for key, value in data.items()}, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified immutable trig manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable trig input: ' + key)


def body(name, order=0):
    text = COS if name == 'cosf' else SIN
    if order & 1:
        text = text.replace('result = reduced + (reduced * squared) * polynomial;',
                            'result = (reduced * squared) * polynomial + reduced;')
    if order & 2:
        table = 'D_80098D70' if name == 'cosf' else 'D_80098D90'
        # Preserve each polynomial stage; only exchange the final add operands.
        text = text.replace('polynomial = ((', 'polynomial = ' + table + '[1] + ((')
        text = text.replace(') * squared + ' + table + '[1];', ') * squared;')
    return PREAMBLE + '\n' + text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cosine-shapes', action='store_true')
    parser.add_argument('--cosine-locals', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    rom = (root / 'conker/conker.us.bin').read_bytes()
    rows = []
    variants = [(name, str(order), body(name, order), ('-O2', '-g3'))
                for name in TARGETS for order in range(4)]
    if args.cosine_shapes:
        original = body('cosf')
        absolute = 'reduced = angle > 0.0f ? angle : -angle;'
        shapes = {
            'split': 'if (angle > 0.0f) { reduced = angle; } else { reduced = -angle; }',
            'copy-split': 'reduced = angle; if (angle > 0.0f) { reduced = angle; } else { reduced = -angle; }',
            'copy-positive': 'reduced = angle; if (!(reduced > 0.0f)) { reduced = -reduced; }',
            'copy-negative': 'reduced = angle; if (reduced < 0.0f) { reduced = -reduced; }',
            'copy-nonpositive': 'reduced = angle; if (reduced <= 0.0f) { reduced = -reduced; }',
            'empty-positive': 'reduced = angle; if (angle > 0.0f) { } else { reduced = -angle; }',
        }
        variants = [('cosf', label, original.replace(absolute, replacement), ('-O2', '-g3'))
                    for label, replacement in shapes.items()]
        variants += [('cosf', 'early-' + label,
            original.replace('    raw =', '    reduced = angle;\n    raw =').replace(absolute, replacement), ('-O2', '-g3'))
            for label, replacement in shapes.items()]
        variants += [('cosf', 'o2', original, ('-O2',))]
        separate = original.replace('f32 reduced,', 'f32 absolute, reduced,')
        separate = separate.replace(absolute, 'absolute = angle > 0.0f ? angle : -angle;')
        separate = separate.replace('periods = reduced *', 'periods = absolute *')
        separate = separate.replace('reduced = reduced - periods * D_80085EA4;',
                                    'reduced = absolute - periods * D_80085EA4;')
        parameter = original.replace(absolute, 'angle = angle > 0.0f ? angle : -angle;')
        parameter = parameter.replace('periods = reduced *', 'periods = angle *')
        parameter = parameter.replace('reduced = reduced - periods * D_80085EA4;',
                                      'reduced = angle - periods * D_80085EA4;')
        variants += [('cosf', label, text, ('-O2', '-g3'))
                     for label, text in (('separate-absolute', separate), ('parameter-absolute', parameter))]
    if args.cosine_locals:
        original = body('cosf')
        absolute = 'reduced = angle > 0.0f ? angle : -angle;'
        separate = original.replace(absolute, 'absolute = angle > 0.0f ? angle : -angle;')
        separate = separate.replace('periods = reduced *', 'periods = absolute *')
        separate = separate.replace('reduced = reduced - periods * D_80085EA4;',
                                    'reduced = absolute - periods * D_80085EA4;')
        declaration = '    f32 reduced, squared, polynomial, periods, result;\n    s32 period, raw, exponent;'
        variants = []
        orders = ('absolute, reduced, squared, polynomial, periods, result',
                  'reduced, squared, polynomial, periods, result, absolute',
                  'reduced, absolute, squared, polynomial, periods, result',
                  'reduced, squared, polynomial, absolute, periods, result')
        for i, order in enumerate(orders):
            for separate_declarations, split_period in itertools.product((False, True), repeat=2):
                decl = '    f32 ' + order + ';'
                if separate_declarations:
                    decl = '\n'.join('    f32 ' + name + ';' for name in order.split(', '))
                if split_period:
                    decl += '\n    s32 period;\n    s32 raw, exponent;'
                else:
                    decl += '\n    s32 period, raw, exponent;'
                text = separate.replace(declaration, decl)
                if split_period:
                    text = text.replace('periods = period - 0.5f;', 'periods = period;\n        periods -= 0.5f;')
                variants.append(('cosf', 'locals-%d-%d-%d' % (i, separate_declarations, split_period), text, ('-O2', '-g3')))
    for name, label, source, flags in variants:
        entry, offset, slot, code = TARGETS[name]
        obj, diagnostics = build.compile_owner(root, out, source, name + '-' + label, flags)
        data, functions = build.link_owner(root, out, obj, name)
        words = list(struct.unpack('>%dI' % (len(data) // 4), data))
        expected = list(struct.unpack_from('>%dI' % slot, rom, offset))
        differences = [(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, expected)) if a != b]
        rows.append({'name': name, 'order': label, 'profile': flags, 'size': functions[name]['size'],
                     'text_size': len(data), 'slot_words': slot, 'retail_code_words': code,
                     'uncompared_slot_words': max(0, slot - len(words)),
                     'differences': differences, 'diagnostics': diagnostics})
    receipt = 'cosine-locals' if args.cosine_locals else 'cosine-shapes' if args.cosine_shapes else 'candidates'
    (out / (receipt + '.json')).write_text(json.dumps(rows, indent=2) + '\n')
    for row in rows:
        print(row['name'], row['order'], row['size'], row['text_size'], len(row['differences']), row['diagnostics'])


if __name__ == '__main__':
    main()
