"""Recover the asset-selected context initialization and sixteen live-table rows."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_barrier_crossing_candidates as previous
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-mode-context-init'
SOURCE, OWNER = previous.SOURCE, previous.OWNER
FUNCTION, ENTRY, ROM, WORDS = 'func_15089BC0', 0x15089BC0, 0xB7070, 247
ORIGINAL = 's32 func_15089BC0() {\n    return 0;\n}'
TABLE, TABLE_ROM = 0x8009DA24, 0x2424E4
INPUTS = dict(previous.INPUTS)
INPUTS.update({
    SOURCE: 'bb39a1d0311db0d8619824f647f713b0136e6d17fea010d3f18089510068f144',
    'conker/retail_word_patches.us.csv': '4ad2854811c2012c604185e3b8b97c47e50be1f8768527be2105b89878cac9c1',
    'conker/build/conker.us.elf': 'df4f13f43cb75c941a32e7dbf08bb800916a4c98d90fcde1da868e4e2595648d',
    'conker/Makefile': '6e6563d792c110f74f44d615c62f04e87430aa0c0e44b1bd7817ffd6d91a8063',
})
DECLARATIONS = '''extern s32 D_800D2E48;
extern s32 D_800D23B0;
extern s8 D_800E0BD0;
extern f32 D_800872B0[];
extern f32 D_800872F8[];
extern s8 D_800872F0[];
u8 *func_1509B570(s32 key);
void func_1508BC20(void);
'''
SELECTED = '''/* Select the supported asset context, then reset and seed its sixteen rows. */
s32 func_15089BC0(void) {
    s32 key = D_800D2E48;
    u8 *data = func_1509B570(key);
    s32 offset;

    if (data == NULL) {
        return 0;
    }
    switch (key) {
        case 0xB9:
            D_800D23B0 = (s32)data;
            break;
        case 0xB8:
            D_800D23B0 = (s32)data;
            break;
        case 0xBB:
            D_800D23B0 = (s32)data;
            break;
        case 0xBA:
            D_800D23B0 = (s32)data;
            break;
        case 0xB7:
            D_800D23B0 = (s32)data;
            break;
        case 0xBD:
            D_800D23B0 = (s32)data;
            break;
        case 0xBE:
            D_800D23B0 = (s32)data;
            break;
        default:
            D_800D23B0 = 0;
            return 0;
    }
    func_1508BC20();
    ((u8 *)D_800D23B0)[0x1700] = 0;
    ((u8 *)D_800D23B0)[0x1701] = 0;
    ((u8 *)D_800D23B0)[0x1703] = 0;
    ((u8 *)D_800D23B0)[0x1702] = 0;
    ((u8 *)D_800D23B0)[0x1704] = 0;
    *(s16 *)((u8 *)D_800D23B0 + 0x16BC) = key;
    *(f32 *)((u8 *)D_800D23B0 + 0x16B8) = D_800872B0[D_800E0BD0];
    ((u8 *)D_800D23B0)[0x1745] = 0;
    for (offset = 0; offset < 0x40; offset += 4) {
        *(s32 *)((u8 *)D_800D23B0 + 0x16C0 + offset) = 0;
        *(f32 *)((u8 *)D_800D23B0 + 0x1868 + offset) = D_800872F8[D_800E0BD0];
        *(f32 *)((u8 *)D_800D23B0 + 0x17A8 + offset) = 0.0f;
        *(f32 *)((u8 *)D_800D23B0 + 0x17E8 + offset) = 0.0f;
        *(f32 *)((u8 *)D_800D23B0 + 0x1828 + offset) = 0.0f;
    }
    *(s32 *)((u8 *)D_800D23B0 + 0xC) = D_800872F0[D_800E0BD0];
    return 0;
}
'''
INITIAL = SELECTED
SELECTED = INITIAL.replace('    s32 key = D_800D2E48;\n    u8 *data = func_1509B570(key);\n    s32 offset;',
    '    u8 *data;\n    s32 offset;\n    s32 key;\n\n    key = D_800D2E48;\n    data = func_1509B570(key);')
compile_profile, link_owner = previous.compile_profile, previous.link_owner


def freeze(root, out):
    with patch.object(previous, 'INPUTS', INPUTS):
        return previous.freeze(root, out)


def recovered_owner(before, body=None):
    if before.count(ORIGINAL) != 1:
        raise ValueError('Unknown mode-context initializer predecessor')
    return before.replace(ORIGINAL, DECLARATIONS + '\n' + (SELECTED if body is None else body).rstrip())


def payload(obj):
    text, functions, bindings = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, w in enumerate(words) if w == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero mode-context initializer alignment tail')
    return raw[:end * 4], {at - f['value']: v for at, v in bindings.items()
        if f['value'] <= at < f['value'] + end * 4}


def compile_candidate(root, out, name='selected', body=None, normal=True, whole=False):
    body = SELECTED if body is None else body
    values = freeze(root, out)
    unit = recovered_owner(values[SOURCE].decode(), body) if whole else '#include <ultra64.h>\n' + DECLARATIONS + body
    obj, diagnostics = compile_profile(root, out, unit, name, normal)
    raw, bindings = payload(obj)
    image, functions = link_owner(root, out, obj, OWNER)
    at = functions[FUNCTION]['value']
    words = list(struct.unpack_from('>%dI' % (len(raw) // 4), image, at))
    truth = struct.unpack_from('>247I', values['conker/conker.us.bin'], ROM)
    row = dict(words=len(words), frame=(-words[0]) & 65535, diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        raw_SHA256=hashlib.sha256(raw).hexdigest(), bindings=bindings)
    (out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def candidates():
    yield 'selected', SELECTED
    yield 'indexed', SELECTED.replace('offset < 0x40; offset += 4', 'offset < 16; offset++').replace(
        ' + offset)', ' + offset * 4)')
    yield 'unsigned', SELECTED.replace('    s32 offset;', '    u32 offset;')
    yield 'inline-key-control', INITIAL


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--primary', action='store_true')
    p.add_argument('--whole', action='store_true')
    p.add_argument('--screens', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    for name, body in candidates() if args.screens else [('selected', SELECTED)]:
        _, _, row = compile_candidate(root, root / BUILD, name + ('-primary' if args.primary else '') +
            ('-whole' if args.whole else ''), body, not args.primary, args.whole)
        print(json.dumps(dict(name=name, **row)), flush=True)
