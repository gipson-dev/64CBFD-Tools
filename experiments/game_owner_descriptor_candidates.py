"""Recover the complete owner descriptor constructor and its private holes."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B2060, 0x1DF510, 40
FUNCTION = 'func_151B2060'
SOURCE = 'conker/src/game/generated_1DF510.c'
ORIGINAL = 's32 func_151B2060() {\n    return 0;\n}'
TYPES = '''typedef struct {
    u8 *owner;
    u8 ownerCode, reserved05[3];
    u8 *resource;
    u8 active, state, reserved0E[2];
    u8 cleared[12];
    s32 value;
} OwnerDescriptor151B2060;
'''
DECLARATIONS = '''u8 *func_15083E90(s32);
u8 *func_151491F4(s16, s8, s8, u8, u8, s32, u8, s32);
void *memcpy(void *, const void *, u32);
'''
SYMBOLS = dict(func_15083E90=0x15083E90, bzero=0x100226F0,
    func_151491F4=0x151491F4, memcpy=0x10022EC0)
BASE = '''void func_151B2060(u8 *owner) {
    OwnerDescriptor151B2060 descriptor;
    u8 *created;

    if (owner != NULL) {
        descriptor.owner = owner;
        descriptor.ownerCode = owner[0x3B];
        descriptor.resource = func_15083E90(1);
        descriptor.active = 1;
        descriptor.state = 0;
        bzero(descriptor.cleared, 12);
        descriptor.value = 0;
        created = func_151491F4(300, -1, 0x16, 0, 0x12, 32, 255, 1);
        if (created != NULL) {
            memcpy(created + 0x28, &descriptor, 32);
        }
    }
}'''
SELECTED = BASE.replace('    OwnerDescriptor151B2060 descriptor;\n    u8 *created;',
    '    u8 *created;\n    OwnerDescriptor151B2060 descriptor;')


def candidates():
    yield 'selected', SELECTED
    yield 'descriptor-first', BASE
    yield 'early-return', BASE.replace('    if (owner != NULL) {',
        '    if (owner == NULL) { return; }\n    {')
    yield 'explicit-byte-array-address', BASE.replace('bzero(descriptor.cleared, 12)',
        'bzero(&descriptor.cleared, 12)')
    yield 'sizeof-copy', BASE.replace('&descriptor, 32', '&descriptor, sizeof(descriptor)')
    yield 'sizeof-clear', BASE.replace('descriptor.cleared, 12',
        'descriptor.cleared, sizeof(descriptor.cleared)')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-descriptor'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
