"""Correct the archived category-0x35 attachment-position draft before import."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_capture_request_slot as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import capture_request_match_checkpoint as checkpoint
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD = 'conker/build/game-special-object-position'
OWNER, FUNCTION = 'generated_142560', 'func_1511F31C'
ENTRY, ROM, WORDS = 0x1511F31C, 0x14C7CC, 51
PATHS = dict(previous.PATHS, position_owner='conker/src/game/generated_142560.c',
             position_original='conker/asm/142560.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    position_owner='80c07766dd4c58f12eabb9fe09244aecf98b9cbb39d51482c1bd42a9891d0381',
    position_original='ca734f7ffd435f954360ac879e7762e8adbb56cc72ce60eadebcac3030d1121f')
DECLARATIONS = '''extern s32 D_800BE9F0;
void func_1511490C(f32 matrix[4][4], u8 *actor);
void func_150A7960(f32 matrix[4][4], f32 x, f32 y, f32 z,
                   f32 *outX, f32 *outY, f32 *outZ);
'''
BODY = '''/* Position category-0x35 attachments from their linked actor's matrix.
 * Two expected-word guards preserve retail's 0x90-byte matrix frame. */
void func_1511F31C(u8 *object) {
    f32 matrix[4][4];
    f32 x;
    f32 y;
    f32 z;
    u8 *actor;

    if (*(u16 *)(object + 0x54) == 0x8005 && D_800BE9F0 == 0x35) {
        actor = func_151149AC(*(u16 *)(object + 0x3E) & 0xFF);
        if (actor != NULL) {
            func_1511490C(matrix, actor);
            func_150A7960(matrix, -3.0f, 223.0f, 549.0f, &x, &y, &z);
            *(s16 *)(object + 0x10) = (s16)(s32)x;
            *(s16 *)(object + 0x12) = (s16)(s32)y;
            *(s16 *)(object + 0x14) = (s16)(s32)z;
        }
    }
}
'''
SELECTED = BODY.replace('    u8 *actor;',
    '    u8 *actor;\n    u16 selector = *(u16 *)(object + 0x3E);').replace(
    'func_151149AC(*(u16 *)(object + 0x3E) & 0xFF)', 'func_151149AC(selector & 0xFF)')
GUARDS = ((0, 0x27BDFF78, 0x27BDFF70), (0xC0, 0x27BD0088, 0x27BD0090))
RAW_SHA256 = 'c039b06951e1d119919b1be2fb1800487ec5d1525b78183f1523984d944d0759'
RELOCATIONS = {32: [('R_MIPS_HI16', 'D_800BE9F0')],
    36: [('R_MIPS_LO16', 'D_800BE9F0')], 52: [('R_MIPS_26', 'func_151149AC')],
    68: [('R_MIPS_26', 'func_1511490C')], 116: [('R_MIPS_26', 'func_150A7960')]}


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed attachment-position baseline')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified attachment-position baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable attachment-position input: ' + key)


def archive_draft(root):
    path = root / '../Another Source/CBFD-Recompiled/conker/conker/src/game/game_142560.c'
    if hashlib.sha256(path.read_bytes()).hexdigest() != '46dc2e2365e4a9f543205120311718de26f50daef46199d595f75c6be9dd1fd8':
        raise ValueError('Changed attachment-position archive')
    return build.body(path.read_text(), FUNCTION)


def recover(before, body=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    result = before[:lo] + body.rstrip() + before[hi:]
    marker = '#include <ultra64.h>\n'
    if result.count(marker) != 1 or 'void func_1511490C(' in before:
        raise ValueError('Unexpected attachment-position preamble')
    return result.replace(marker, marker + '\n' + DECLARATIONS, 1)


def variants(root):
    yield 'corrected', BODY
    yield 'snapshot-selector', BODY.replace('    u8 *actor;', '    u8 *actor;\n    u16 selector = *(u16 *)(object + 0x3E);').replace(
        'func_151149AC(*(u16 *)(object + 0x3E) & 0xFF)', 'func_151149AC(selector & 0xFF)')
    yield 'byte-selector', BODY.replace('*(u16 *)(object + 0x3E) & 0xFF', 'object[0x3F]')
    yield 'archive', archive_draft(root).replace('void * sp48;', 'f32 sp48[4][4];').replace(
        '*(s32 *)((char *)(arg0) + 0x54)', '*(u16 *)((char *)(arg0) + 0x54)').replace(
        '*(s32 *)((char *)(arg0) + 0x3E)', '*(u16 *)((char *)(arg0) + 0x3E)').replace('&sp48,', 'sp48,')
    snapshot = BODY.replace('    u8 *actor;', '    u8 *actor;\n    u16 selector = *(u16 *)(object + 0x3E);').replace(
        'func_151149AC(*(u16 *)(object + 0x3E) & 0xFF)', 'func_151149AC(selector & 0xFF)')
    for kind in ('u32', 's32', 'u8'):
        yield 'selector-' + kind, snapshot.replace('u16 selector', kind + ' selector')
    for kind in ('u16', 'u32', 's32'):
        yield 'kind-' + kind, snapshot.replace('    u8 *actor;',
            '    ' + kind + ' kind = *(u16 *)(object + 0x54);\n    u8 *actor;').replace(
                'if (*(u16 *)(object + 0x54) == 0x8005', 'if (kind == 0x8005')
    yield 'aligned-matrix', snapshot.replace('f32 matrix[4][4];', 'Mtx matrix;').replace(
        'func_1511490C(matrix,', 'func_1511490C((f32 (*)[4])&matrix,').replace(
        'func_150A7960(matrix,', 'func_150A7960((f32 (*)[4])&matrix,')
    for kind in ('s32', 's16'):
        named = snapshot.replace('    u8 *actor;', '    ' + kind + ' coordinate;\n    u8 *actor;')
        for axis, offset in (('x', '10'), ('y', '12'), ('z', '14')):
            named = named.replace('            *(s16 *)(object + 0x' + offset + ') = (s16)(s32)' + axis + ';',
                '            coordinate = (s32)' + axis + ';\n            *(s16 *)(object + 0x' + offset + ') = coordinate;')
        yield 'named-coordinate-' + kind, named
    yield 'pointer-selector', snapshot.replace('    u16 selector = *(u16 *)(object + 0x3E);',
        '    u16 *selectorAddress = (u16 *)(object + 0x3E);\n    u16 selector = *selectorAddress;')


def measure(root, out, label, body=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recover((out / 'before-position_owner').read_text(), body), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>51I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), frame=((-words[0]) & 0xFFFF),
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics,
        differing_words=[(i * 4, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    return obj, words, row


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown attachment-position words or relocations')
    words = list(struct.unpack('>51I', raw))
    for offset, expected, replacement in GUARDS:
        if words[offset // 4] != expected:
            raise ValueError('Changed attachment-position frame site')
        words[offset // 4] = replacement
    return words


def guard_manifest(before):
    if not before.endswith(b'\n') or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unexpected attachment-position guard baseline')
    rows = ''.join('%s,%s,0x%X,0x%08X,0x%08X,-,-,Preserve retail matrix frame allocation and release,,,false\n' %
        (OWNER, FUNCTION, offset, expected, replacement) for offset, expected, replacement in GUARDS)
    return before + rows.encode()


def pad(root, out, obj, label, guards):
    manifest = out / (label + '-guards.csv')
    manifest.write_bytes(guards)
    assembly = emit_padded_assembly(obj, root / PATHS['position_original'], filename=OWNER,
        word_patches_path=manifest)
    path = out / (label + '.s')
    path.write_text('.include "' + str(root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)],
        capture_output=True, check=True)
    return padded


def qualify(root, out):
    obj, raw_words, row = measure(root, out, 'qualified')
    if (row['words'], row['frame'], row['differences'], row['diagnostics']) != (51, 136, 2, ''):
        raise ValueError('Changed attachment-position reconstruction: ' + repr(row))
    raw, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    relative = {at - f['value']: value for at, value in relocations.items()
        if f['value'] <= at < f['value'] + f['size']}
    normalized = normalize(raw[f['value']:f['value'] + f['size']], relative)
    linked_expected = list(raw_words)
    for offset, expected, replacement in GUARDS:
        if linked_expected[offset // 4] != expected:
            raise ValueError('Unexpected linked frame site')
        linked_expected[offset // 4] = replacement
    if any(a != b for i, (a, b) in enumerate(zip(struct.unpack('>51I', raw[f['value']:f['value'] + f['size']]), normalized))
           if i * 4 not in (0, 0xC0)):
        raise ValueError('Normalization changed a non-frame word')
    guards = guard_manifest((out / 'before-guards').read_bytes())
    padded = pad(root, out, obj, 'qualified-padded', guards)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>51I', data, f['value']))
    truth = list(struct.unpack_from('>51I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if words != truth or words != linked_expected or f['size'] != 204:
        raise ValueError('Attachment-position full slot is not exact')
    row.update(linked_differences=0, guards=2, retail_frame=144,
        profile_unchanged=True, not_a_direct_unguarded_C_match=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, raw_words, words, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    rows = []
    for label, body in variants(root):
        _, _, row = measure(root, out, label, body)
        rows.append(row)
        print(json.dumps(row), flush=True)
    (out / 'screens.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
