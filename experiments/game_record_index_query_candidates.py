"""Recover the complete byte-selector record-index search."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15083E0C, 0xB12BC, 33
FUNCTION, SOURCE = 'func_15083E0C', 'conker/src/game/generated_AEB40.c'
ORIGINAL = 's32 func_15083E0C() {\n    return 0;\n}'
RECORD = '''typedef struct {
    u8 padding[0x28];
    u8 identity;
    u8 tail[7];
} IndexRecord15083E0C;
'''
DECLARATIONS = '''extern u8 D_800D2100;
extern IndexRecord15083E0C *D_800D20FC;
'''
SYMBOLS = dict(D_800D2100=0x800D2100, D_800D20FC=0x800D20FC)
SELECTED = '''s32 func_15083E0C(u8 selector) {
    s32 i;

    if (selector == 0) {
        return -1;
    }
    for (i = 0; i < D_800D2100; i++) {
        if (D_800D20FC[i].identity == selector) {
            return &D_800D20FC[i] - D_800D20FC;
        }
    }
    return -1;
}'''


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before, body=SELECTED):
    if before.count(ORIGINAL) != 1:
        raise ValueError('stale record index-query owner')
    declarations = DECLARATIONS.replace('extern u8 D_800D2100;\n', '')
    return before.replace(ORIGINAL, RECORD+declarations+'\n'+body)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-record-index-query'
    measurements = []
    for name, body in (('selected', SELECTED), ('index-return', SELECTED.replace(
            'return &D_800D20FC[i] - D_800D20FC;', 'return i;')),
            ('selector-word', SELECTED.replace('u8 selector', 'u32 selector'))):
        meta, _ = compile_candidate(root, out, name, body)
        measurements.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
