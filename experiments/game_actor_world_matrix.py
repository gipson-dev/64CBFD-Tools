"""Recover the actor angle/translation/scale matrix builder from retail."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_special_object_position as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import special_object_position_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-actor-world-matrix'
OWNER, FUNCTION = 'generated_13D350', 'func_1511490C'
ENTRY, ROM, WORDS = 0x1511490C, 0x141DBC, 40
PATHS = dict(previous.PATHS,
    builder_owner='conker/src/game/generated_13D350.c', builder_original='conker/asm/13D350.s',
    scale_owner='conker/src/game_D5160.c', scale_original='conker/asm/nonmatchings/game_D5160/func_150A7CB0.s',
    angles_owner='conker/src/game_D5500.c', angles_original='conker/asm/nonmatchings/game_D5500/func_150A8050.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    builder_owner='df497d2d221b68cc528b5266cdea3a568d9bc6a5b41a0780d5f458fe9ab8b10a',
    builder_original='aae655875cae186bc7377f14463dc61e80cb55f511b1931a0ed03d1308333a2c',
    scale_owner='7791dea54328f5669a310fdbbd96c31d40b97f86a67b07b0d9ce398141f1f42c',
    scale_original='9a9d8d5b1c4e26b19a318e0d1398dc737604f8909347033435c9134d70601743',
    angles_owner='a5cadffdbc2f426499da98c2b655db2c7968be5097b060fb5b5322e687e63288',
    angles_original='0e4eaca677bb05aacd558db2504c29c720d6dea49036a3d4ea65ce21e4ef17f5')
DECLARATION = 'void func_150A7CB0(f32 matrix[4][4], f32 x, f32 y, f32 z);\n'
BASE = '''/* Build the actor's rotated, translated and scaled world matrix. */
void func_1511490C(f32 matrix[4][4], u8 *actor) {
    f32 scale[4][4];

    func_151148A8(matrix, (f32 *)actor);
    matrix[3][0] = *(s16 *)(actor + 0x10);
    matrix[3][1] = *(s16 *)(actor + 0x12) + *(f32 *)(actor + 0x18);
    matrix[3][2] = *(s16 *)(actor + 0x14);
    func_150A7CB0(scale, *(f32 *)(actor + 0x2C), *(f32 *)(actor + 0x30), *(f32 *)(actor + 0x34));
    func_150A7A48(scale, matrix, matrix);
}
'''
SELECTED = BASE.replace('*(s16 *)(actor + 0x12) + *(f32 *)(actor + 0x18)',
                        '*(f32 *)(actor + 0x18) + *(s16 *)(actor + 0x12)')


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed actor world-matrix baseline')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified actor world-matrix manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable world-matrix input: ' + key)


def recover(before, body=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    result = before[:lo] + body.rstrip() + before[hi:]
    marker = '#include <ultra64.h>\n'
    if result.count(marker) != 1 or 'void func_150A7CB0(' in before:
        raise ValueError('Unexpected world-matrix preamble')
    return result.replace(marker, marker + DECLARATION, 1)


def measure(root, out, label, body=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recover((out / 'before-builder_owner').read_text(), body), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>40I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS), diagnostics=diagnostics,
        differing_words=[(i * 4, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    return obj, words, row


def variants():
    yield 'implicit-y-conversion', BASE
    yield 'explicit-y-conversion', BASE.replace('= *(s16 *)(actor + 0x12) +', '= (f32)*(s16 *)(actor + 0x12) +')
    yield 'named-y', BASE.replace('    f32 scale[4][4];', '    f32 scale[4][4];\n    f32 y;').replace(
        '    matrix[3][1] = *(s16 *)(actor + 0x12) +', '    y = *(s16 *)(actor + 0x12);\n    matrix[3][1] = y +')
    yield 'commuted-y', SELECTED
    yield 'explicit-all-conversions', BASE.replace('= *(s16 *)', '= (f32)*(s16 *)')


def pad(root, out, obj, label):
    assembly = emit_padded_assembly(obj, root / PATHS['builder_original'], filename=OWNER,
        word_patches_path=root / PATHS['guards'])
    path = out / (label + '.s')
    path.write_text('.include "' + str(root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], capture_output=True, check=True)
    return padded


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    if (row['words'], row['frame'], row['differences'], row['diagnostics']) != (40, 96, 0, ''):
        raise ValueError('World-matrix body is not a direct match: ' + repr(row))
    padded = pad(root, out, obj, 'qualified-padded')
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 160 or list(struct.unpack_from('>40I', data, f['value'])) != words:
        raise ValueError('World-matrix production padder differs')
    row.update(guards_added=0, profile_unchanged=True, direct_C_match=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[2]
    rows = []
    for label, body in variants():
        _, _, row = measure(root, root / BUILD, label, body)
        rows.append(row)
        print(json.dumps(row), flush=True)
    (root / BUILD / 'screens.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
