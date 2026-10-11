"""Recover the complete descriptor-driven child cleanup routine."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x150836CC, 0xB0B7C, 66
FUNCTION, SOURCE = 'func_150836CC', 'conker/src/game/generated_AEB40.c'
ORIGINAL = 's32 func_150836CC() {\n    return 0;\n}'
RECORD = '''typedef struct {
    u8 *records;
    u8 count;
    u8 padding[3];
} AnimationDescriptor15083568;
'''
DECLARATIONS = '''extern AnimationDescriptor15083568 D_80086CC4[];
extern u8 D_800CC2D0[];
void func_150302F0(u8 *, s32);
u8 *func_1505F0AC(u8);
void func_15060F28(u8 *, s32);
'''
SYMBOLS = dict(D_80086CC4=0x80086CC4, D_800CC2D0=0x800CC2D0,
    func_150302F0=0x150302F0, func_1505F0AC=0x1505F0AC, func_15060F28=0x15060F28)
SELECTED = '''void func_150836CC(u8 *actor, s32 animation) {
    AnimationDescriptor15083568 *descriptor;
    u8 *record;
    u8 *records;
    u8 *child;
    s32 i;

    func_150302F0(actor, animation);
    animation--;
    descriptor = &D_80086CC4[(u32)animation];
    records = descriptor->records;
    i = 0;
    if (descriptor->count > 0) {
        record = records;
        do {
            if (record[3] == 0) {
                child = func_1505F0AC(record[0]);
                if (child != NULL) {
                    if ((s32)((u32)actor - (u32)D_800CC2D0) / 0x32C + 1 == child[0x65]) {
                        func_15060F28(child, 0);
                    }
                }
            }
            i++;
            record += 16;
        } while (i < descriptor->count);
    }
}'''


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before, body=SELECTED):
    if before.count(ORIGINAL) != 1:
        raise ValueError('stale animation child cleanup owner')
    declarations = '\n'.join(DECLARATIONS.splitlines()[2:]) + '\n'
    return before.replace(ORIGINAL, declarations+'\n'+body)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-animation-child-cleanup'
    measurements = []
    for name, body in (('selected', SELECTED), ('combined', SELECTED.replace(
            'if (child != NULL) {\n                    if (', 'if (child != NULL && (').replace(
            'child[0x65]) {', 'child[0x65])) {').replace(
            '                    }\n                }', '                }'))):
        meta, _ = compile_candidate(root, out, name, body)
        measurements.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
