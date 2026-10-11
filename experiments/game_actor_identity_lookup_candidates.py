"""Recover the complete presence-gated actor identity lookup."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15083E90, 0xB1340, 72
FUNCTION, SOURCE = 'func_15083E90', 'conker/src/game/generated_AEB40.c'
ORIGINAL = 'u8 *func_15083E90(u8 arg0) {\n    return 0;\n}'
RECORD = ''
DECLARATIONS = 'extern u8 D_800CC2D0[];\n'
SYMBOLS = dict(D_800CC2D0=0x800CC2D0, D_800CC30B=0x800CC30B, D_800CC5FC=0x800CC5FC)
SELECTED = '''u8 *func_15083E90(u8 selector) {
    u8 *actor;
    s32 i;

    if (selector == 0) {
        return NULL;
    }
    actor = D_800CC2D0;
    for (i = 0; i < 26; i++, actor += 0x32C) {
        if ((*(s32 *)actor != 0) && (actor[0x3B] == selector)) {
            return actor;
        }
    }
    return NULL;
}'''


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    meta['frame'] = 0 if words[0] >> 16 != 0x27BD else (-words[0]) & 65535
    return meta, words


def install(before, body=SELECTED):
    if before.count(ORIGINAL) != 1:
        raise ValueError('stale actor identity lookup owner')
    return before.replace(ORIGINAL, body)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-actor-identity-lookup'
    measurements = []
    for name, body in (('selected', SELECTED), ('short-25-slot-bound', SELECTED.replace(
            'i < 26', 'i < 25')), ('index-address', SELECTED.replace(
            'actor = D_800CC2D0;', '').replace('i++, actor += 0x32C', 'i++').replace(
            '        if (', '        actor = D_800CC2D0 + i * 0x32C;\n        if (')),
            ('selector-word', SELECTED.replace('u8 selector', 'u32 selector'))):
        meta, _ = compile_candidate(root, out, name, body)
        measurements.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')


if __name__ == '__main__':
    main()
