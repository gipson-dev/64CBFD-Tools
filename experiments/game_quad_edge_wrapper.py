"""Recover the signed-position rectangle wrapper for the quad edge emitter."""
import argparse
import json
import re
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_quad_edge_emitter as previous
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-quad-edge-wrapper'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19E040', 'func_151717FC', 0x151717FC, 0x19ECAC, 61
CALLEE = 0x151700D8
PATHS = dict(previous.PATHS,
    archive_wrapper='../Another Source/CBFD-Recompiled/conker/conker/src/game/game_19E040.c')
BASELINE = dict(previous.BASELINE,
    archive_wrapper='05648d5f4ff84b71b4a6762520f12c18183c4aee440badd5ccedc8d0be86bca4')
build = previous.build
DECLARATIONS = '''typedef struct QuadEmitterOrigin19E040 {
    u8 prefix[0x10];
    s16 x;
    s16 y;
    s16 z;
} QuadEmitterOrigin19E040;
typedef struct QuadVertex19E040 { f32 x, y, z; } QuadVertex19E040;
typedef struct QuadVertices19E040 {
    QuadVertex19E040 frontRight, frontLeft, backLeft, backRight;
} QuadVertices19E040;
void func_151700D8(f32 *, f32, f32, s32, f32, s32, s32, s32, u8, s32);

'''
SELECTED = '''/* Build a rectangle around signed actor coordinates and emit its perimeter. */
void func_151717FC(u8 *actor, f32 halfWidth, f32 halfDepth, f32 offsetX,
                  f32 offsetY, f32 offsetZ, s32 kind, s32 preset,
                  s32 xCount, s32 zCount, f32 scale, u8 flags, s32 context) {
    f32 quad[12];
    f32 frontZ;
    f32 centerY;
    f32 centerX;
    f32 centerZ;
    f32 backZ;
    f32 rightX;
    f32 leftX;

    centerX = (f32)*(s16 *)(actor + 0x10) + offsetX;
    centerY = (f32)*(s16 *)(actor + 0x12) + offsetY;
    centerZ = (f32)*(s16 *)(actor + 0x14) + offsetZ;
    quad[1] = centerY;
    quad[4] = centerY;
    rightX = halfWidth + centerX;
    quad[7] = centerY;
    quad[0] = rightX;
    quad[9] = rightX;
    leftX = centerX - halfWidth;
    backZ = centerZ - halfDepth;
    frontZ = halfDepth + centerZ;
    quad[3] = leftX;
    quad[6] = leftX;
    quad[2] = frontZ;
    quad[5] = frontZ;
    quad[10] = centerY;
    quad[8] = (&backZ)[0];
    quad[11] = (&backZ)[0];
    func_151700D8(quad, centerX, centerZ, preset, scale, kind,
                  xCount, zCount, flags, context);
}
'''


def freeze(root, out):
    with patch.object(previous, 'PATHS', PATHS), patch.object(previous, 'BASELINE', BASELINE):
        previous.freeze(root, out)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151717FC() {\n    return 0;\n}':
        raise ValueError('Unknown rectangle-wrapper placeholder')
    marker = '/* Non-matching placeholders for the text-only asm slice asm/19E040.s. */'
    return (before[:lo] + selected.rstrip() + before[hi:]).replace(marker, DECLARATIONS + marker, 1)


def measure(root, out, label='selected', selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-edge_wrapper_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>61I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), diagnostics=diagnostics, frame=(-words[0]) & 65535,
        pool_bytes=sum(len(sections(obj).get(name, (0, b''))[1]) for name in ('.data', '.rodata')),
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out)
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['pool_bytes']) != (61, 128, 0, '', 0):
        raise ValueError('Rectangle wrapper is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['edge_wrapper_original'],
        filename=OWNER, word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 244 or list(struct.unpack_from('>61I', data, f['value'])) != words:
        raise ValueError('Rectangle-wrapper production padding differs')
    return obj, padded, words, row


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    bodies = {'selected': SELECTED}
    if args.screen:
        halves = SELECTED.replace('u8 *actor', 's16 *actor')
        record = SELECTED.replace('u8 *actor', 'QuadEmitterOrigin19E040 *actor')
        for offset, index, axis in (('10', 8, 'x'), ('12', 9, 'y'), ('14', 10, 'z')):
            halves = halves.replace('*(s16 *)(actor + 0x%s)' % offset, 'actor[%d]' % index)
            record = record.replace('*(s16 *)(actor + 0x%s)' % offset, 'actor->%s' % axis)
        bodies.update(halves=halves, record=record, register=SELECTED.replace('u8 *actor', 'register u8 *actor'))
        bodies.update(signed_address=SELECTED.replace('u8 *actor', 's32 actor'),
            unsigned_address=SELECTED.replace('u8 *actor', 'u32 actor'))
        vertices = SELECTED.replace('f32 quad[12];', 'QUAD_DECLARATION').replace('func_151700D8(quad,', 'func_151700D8((f32 *)quad,')
        rectangle = SELECTED.replace('f32 quad[12];', 'QuadVertices19E040 quad;').replace('func_151700D8(quad,', 'func_151700D8((f32 *)&quad,')
        vertices = re.sub(r'quad\[(\d+)\]', lambda m: 'quad[%d].%s' %
            (int(m[1]) // 3, 'xyz'[int(m[1]) % 3]), vertices).replace('QUAD_DECLARATION', 'QuadVertex19E040 quad[4];')
        rectangle = re.sub(r'quad\[(\d+)\]', lambda m: 'quad.%s.%s' %
            (('frontRight', 'frontLeft', 'backLeft', 'backRight')[int(m[1]) // 3], 'xyz'[int(m[1]) % 3]), rectangle)
        bodies.update(vertices=vertices, rectangle=rectangle)
        bodies.update({name + '-normal-back': body.replace('(&backZ)[0]', 'backZ')
            for name, body in list(bodies.items()) if name in ('vertices', 'rectangle')})
        local = SELECTED.replace('    f32 quad[12];', '    u8 *origin = actor;\n    f32 quad[12];').replace(
            '(actor + 0x', '(origin + 0x')
        bodies['actor-copy'] = local
        bodies['actor-copy-inline-front'] = local.replace('    f32 frontZ;\n', '').replace(
            '    frontZ = halfDepth + centerZ;\n', '').replace('= frontZ;', '= halfDepth + centerZ;')
        prefix, marker, tail = SELECTED.partition('    quad[1] = centerY;')
        for axis in 'XYZ':
            tail = tail.replace('center' + axis, 'offset' + axis)
        updated = prefix + marker.replace('centerY', 'offsetY') + tail
        for offset, axis in (('10', 'X'), ('12', 'Y'), ('14', 'Z')):
            updated = updated.replace(' + offset%s;' % axis,
                ';\n    offset%s = center%s + offset%s;' % (axis, axis, axis), 1)
        bodies['parameter-centers'] = updated
        snapshots = updated
        for offset, axis in (('10', 'X'), ('12', 'Y'), ('14', 'Z')):
            snapshots = snapshots.replace('f32 center%s;' % axis, 's32 position%s;' % axis).replace(
                'center%s = (f32)*(s16 *)(actor + 0x%s);' % (axis, offset),
                'position%s = *(s16 *)(actor + 0x%s);' % (axis, offset)).replace(
                'offset%s = center%s + offset%s;' % (axis, axis, axis),
                'offset%s = (f32)position%s + offset%s;' % (axis, axis, axis))
        bodies['coordinate-snapshots'] = snapshots
        prefix, sep, code = SELECTED.partition('    centerX = ')
        for label, names in (('input-offset-homes', ('offsetX', 'offsetY', 'offsetZ')),
                ('input-float-homes', ('halfWidth', 'halfDepth', 'offsetX', 'offsetY', 'offsetZ', 'scale'))):
            addressed = re.sub(r'\b(' + '|'.join(names) + r')\b', lambda m: '(&%s)[0]' % m[1], code)
            bodies[label] = prefix + sep + addressed
    for label, body in bodies.items():
        if args.filter not in label:
            continue
        print(json.dumps({key: value for key, value in measure(root, root / BUILD, label, body)[-1].items() if key != 'different_words'}), flush=True)
