"""Screen the donor's commented scalefactor decoder against the active ABI."""
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build
from tools.pad_generated_object import parse_object

FUNCTION, ENTRY, ROM, WORDS = 'func_151F4F38', 0x151F4F38, 0x2223E8, 533
SELECTED = '''s32 func_151F4F38(void *arg0, s32 arg1, s32 arg2) {
    s32 k;
    s32 i;
    s32 j;

    if (*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C98) != 0 &&
        *(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3CA0) == 2) {
        if (*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3CA8) != 0) {
            i = 0;
            do {
                *(s32 *) ((char *) arg0 + arg1 * 248 + arg2 * 248 + i * 4 + 0x3D08) =
                    D_800AEB5C[0][*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90)]
                        ? func_151F8960((char *) arg0 + 0x1C, (char *) arg0 + 0x2020,
                                        D_800AEB5C[0][*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90)])
                        : 0;
            } while (++i < 8);

            i = 3;
            do {
                j = 0;
                do {
                    *(s32 *) ((char *) arg0 + arg1 * 248 + arg2 * 248 + j * 52 + i * 4 + 0x3D64) =
                        D_800AEB5C[0][*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90)]
                            ? func_151F8960((char *) arg0 + 0x1C, (char *) arg0 + 0x2020,
                                            D_800AEB5C[0][*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90)])
                            : 0;
                } while (++j < 3);
            } while (++i < 6);

            i = 6;
            do {
                j = 0;
                do {
                    *(s32 *) ((char *) arg0 + arg1 * 248 + arg2 * 248 + j * 52 + i * 4 + 0x3D64) =
                        D_800AEB5C[1][*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90)]
                            ? func_151F8960((char *) arg0 + 0x1C, (char *) arg0 + 0x2020,
                                            D_800AEB5C[1][*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90)])
                            : 0;
                } while (++j < 3);
            } while (++i < 12);
        } else {
            k = 0;
            do {
                if (D_800AEB54[k + 6] > (i = D_800AEB54[k + 5])) {
                    do {
                        j = 0;
                        do {
                            *(s32 *) ((char *) arg0 + arg1 * 248 + arg2 * 248 + j * 52 + i * 4 + 0x3D64) =
                                *(D_800AEB5C[0] + k * 16 + *(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90))
                                    ? func_151F8960((char *) arg0 + 0x1C, (char *) arg0 + 0x2020,
                                                    *(D_800AEB5C[0] + k * 16 + *(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90)))
                                    : 0;
                        } while (++j < 3);
                    } while (++i < D_800AEB54[k + 6]);
                }
            } while (++k < 2);
        }

        j = 0;
        do {
            *(s32 *) ((char *) arg0 + arg1 * 248 + arg2 * 248 + j * 52 + 0x3D94) = 0;
        } while (++j < 3);
    } else {
        k = 0;
        do {
            if (*(s32 *) ((char *) arg0 + arg2 * 128 + k * 4 + 0x3BF8) == 0 || arg1 == 0) {
                if (D_800AEB54[k + 1] > (i = D_800AEB54[k])) {
                    do {
                        *(s32 *) ((char *) arg0 + arg1 * 248 + arg2 * 248 + i * 4 + 0x3D08) =
                            D_800AEB5C[k < 2 ? 0 : 1][*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90)]
                                ? func_151F8960((char *) arg0 + 0x1C, (char *) arg0 + 0x2020,
                                                D_800AEB5C[k < 2 ? 0 : 1][*(s32 *) ((char *) arg0 + arg1 * 4 + arg2 * 4 + 0x3C90)])
                                : 0;
                    } while (++i < D_800AEB54[k + 1]);
                }
            } else {
                if (D_800AEB54[k + 1] > (i = D_800AEB54[k])) {
                    do {
                        *(s32 *) ((char *) arg0 + arg2 * 248 + i * 4 + 0x3E00) =
                            *(s32 *) ((char *) arg0 + arg2 * 248 + i * 4 + 0x3D08);
                    } while (++i < D_800AEB54[k + 1]);
                }
            }
        } while (++k < 4);

        *(s32 *) ((char *) arg0 + arg1 * 248 + arg2 * 248 + 0x3D60) = 0;
    }
    return 1;
}'''


def candidates():
    yield 'donor', SELECTED
    declarations = '    s32 k;\n    s32 i;\n    s32 j;'
    for order in itertools.permutations('kij'):
        if order != tuple('kij'):
            yield 'order-' + ''.join(order), SELECTED.replace(declarations,
                '\n'.join('    s32 ' + name + ';' for name in order))
    for mode in ('auto', 'register'):
        for form in ('separate', 'expression'):
            qualifier = 'register ' if mode == 'register' else ''
            result = SELECTED.replace('    s32 j;', '    s32 j;\n    %ss32 bank0;\n    %ss32 bank1;' %
                (qualifier, qualifier))
            repeated = 'k < 2 ? 0 : 1'
            if form == 'separate':
                marker = '                    do {\n                        *(s32 *)'
                position = result.index('    } else {\n        k = 0;')
                head, tail = result[:position], result[position:]
                tail = tail.replace(repeated, 'bank0', 1).replace(repeated, 'bank1', 1)
                tail = tail.replace(marker, '                    do {\n                        bank0 = k < 2 ? 0 : 1;\n                        bank1 = k < 2 ? 0 : 1;\n                        *(s32 *)', 1)
                result = head + tail
            else:
                result = result.replace(repeated, '(bank0 = k < 2 ? 0 : 1)', 1).replace(repeated, '(bank1 = k < 2 ? 0 : 1)', 1)
            yield mode + '-' + form, result


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-scalefactor-band'
    out.mkdir(exist_ok=True)
    current = (root / 'conker/src/game_221290.c').read_text()
    prefix = current[:build.function_span(current, 'func_151F3DE0')[0]]
    prefix = prefix.replace('extern u8 D_800AEB5C[];', 'extern u8 D_800AEB5C[][16];')
    truth = (root / 'conker/conker.us.bin').read_bytes()[ROM:ROM + WORDS * 4]
    records = []
    for name, body in candidates():
        obj, diagnostics = build.compile_owner(root, out, prefix + body, name, ('-g',))
        emitted, functions = build.link_owner(root, out, obj, 'game_221290')
        info = functions[FUNCTION]
        actual = emitted[info['value']:info['value'] + info['size']]
        words = list(struct.unpack('>%dI' % (len(actual) // 4), actual))
        retail = list(struct.unpack('>533I', truth))
        differences = [(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, retail)) if a != b]
        record = dict(candidate=name, words=len(words), retail_words=WORDS, differences=len(differences) + abs(len(words) - WORDS),
            frame=(-words[0]) & 0xFFFF, first_difference=differences[:3], diagnostics=diagnostics)
        records.append(record)
        (out / (name + '-differences.json')).write_text(json.dumps(differences, indent=2) + '\n')
        print(json.dumps(record), flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
