"""Recover the four-edge packed-particle emitter from retail and archival C."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import re

from tools.pad_generated_object import parse_object
from tools.pad_generated_object import emit_padded_assembly
from tools.experiments.game_actor_classifier_candidates import sections

from tools.experiments import game_random_unit_vector as previous
from tools.tests import random_unit_vector_checkpoint as checkpoint

BUILD = 'conker/build/game-quad-edge-emitter'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_151700D8', 0x151700D8, 0x19D588, 266
RANDOM, FACTORY, SCALE = 0x150ADA20, 0x1516D4E8, 0x800A6E84
PATHS = dict(previous.PATHS,
    scale_table_original='conker/asm/data/24B8F0.rodata.s',
    edge_caller_a_original='conker/asm/nonmatchings/game_981E0/func_1506E0EC.s',
    edge_caller_b_original='conker/asm/nonmatchings/game_981E0/func_1506E2CC.s',
    edge_wrapper_original='conker/asm/19E040.s',
    edge_wrapper_owner='conker/src/game/generated_19E040.c')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    scale_table_original='93903e8ffae20b7820cd5993f5364e1f135ed04b5ac27959ca1904591d4885d0',
    edge_caller_a_original='ae3c89f8f1ebf0764a4bd54d63fb454fe06414a7974229f7869c80f81dcd0016',
    edge_caller_b_original='ed759811b370a3725cb0a442025e1a63462c6066e50854b0f0b5b3046412b70f',
    edge_wrapper_original='8d26a8b45ba4d7a75c49e9195d5d485ae9a97f026f7b28dbe6901b20493b7c7c',
    edge_wrapper_owner='091fa97c0b05183ab525144fdc822ba155e81b8a3dfca82897c0e074b5bb37f2')
build = previous.build
DECLARATIONS = '''typedef struct FloatTable3_19A8B0 {
    f32 values[3];
} FloatTable3_19A8B0;
typedef struct ByteTable9_19A8B0 {
    u8 values[9];
} ByteTable9_19A8B0;
extern FloatTable3_19A8B0 D_8008CBF4;
extern FloatTable3_19A8B0 D_8008CC00;
extern ByteTable9_19A8B0 D_8008CC0C;
extern f32 D_800A6E84;

'''
SELECTED = '''/* Emit packed particles along each edge of a four-vertex perimeter. */
void func_151700D8(f32 *vertices, f32 originX, f32 originZ, u8 preset,
                  f32 scale, s32 kind, s32 xCount, s32 zCount, u8 flags,
                  s32 context) {
    s32 edge;
    s32 limit;
    s32 count;
    FloatTable3_19A8B0 initial = D_8008CBF4;
    FloatTable3_19A8B0 ranges = D_8008CC00;
    ByteTable9_19A8B0 colors = D_8008CC0C;
    s32 nextEdge;
    s32 presetByte;
    s32 xHigh;
    s32 xLow;
    s32 zHigh;
    s32 zLow;
    f32 fraction;
    f32 startY;
    f32 startZ;
    f32 x;
    f32 y;
    f32 z;
    f32 startX;
    s32 extent;
    s32 xFixed;
    s32 zFixed;
    s32 delay;
    s32 base;
    s32 nextIndex;
    s32 index;
    s32 width;
    s32 lifetime;
    f32 *next;
    u8 *color;
    f32 *current;
    f32 inverse;

    current = vertices;
    limit = (s32)(ranges.values[kind] * scale);
    edge = 0;
    do {
        index = 0;
        if (edge != 3) {
            nextIndex = edge + 1;
            nextEdge = nextIndex;
        } else {
            nextEdge = edge + 1;
            nextIndex = 0;
        }
        if (edge == 0 || edge == 2) {
            count = xCount;
        } else {
            count = zCount;
        }
        next = (f32 *)((u8 *)vertices + nextIndex * 12);
        color = colors.values + kind * 3;
        xFixed = (s32)(2.0f * ((next[0] + current[0]) * 0.5f - originX));
        zFixed = (s32)(2.0f * ((next[2] + current[2]) * 0.5f - originZ));
        if ((&count)[0] > 0) {
            presetByte = preset;
            base = (s32)(D_800A6E84 * scale);
            width = (s32)(836.0f * scale);
            lifetime = (s32)(143.0f * scale);
            xLow = xFixed & 255;
            xHigh = (xFixed >> 8) & 255;
            zHigh = (zFixed >> 8) & 255;
            zLow = zFixed & 255;
            inverse = 1.0f / (f32)((&count)[0] - 1);
            do {
                startX = current[0];
                startY = current[1];
                startZ = current[2];
                fraction = (f32)index * inverse;
                x = (next[0] - startX) * fraction + startX;
                y = (next[1] - startY) * fraction + startY;
                z = (next[2] - startZ) * fraction + startZ;
                delay = (func_150ADA20() & 0x1F) + 15;
                extent = (u32)func_150ADA20() % (u32)width + base;
                func_1516D4E8((s16)(s32)x, (s16)(s32)y, (s16)(s32)z,
                    13, 0, color[0], color[1], color[2], 0, 0, 0, 0, 2,
                    xHigh, xLow, zHigh, zLow, 0, 0, presetByte, 0, 0, 0,
                    (s16)extent, (s16)extent,
                    delay, (u32)func_150ADA20() % (u32)limit + lifetime,
                    0, 0, flags, context);
                index++;
            } while (index != (&count)[0]);
        }
        edge = nextEdge;
        current += 3;
    } while (edge != 4);
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed edge-emitter predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed edge-emitter baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed edge-emitter fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151700D8() {\n    return 0;\n}':
        raise ValueError('Unknown edge-emitter placeholder')
    marker = '/* Non-matching placeholders for the text-only asm slice asm/19A8B0.s. */'
    result = before[:lo] + selected.rstrip() + before[hi:]
    return result.replace(marker, DECLARATIONS + marker, 1)


def measure(root, out, label='selected', selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    object_sections = sections(obj)
    pools = {name: object_sections.get(name, (0, b''))[1] for name in ('.data', '.rodata')}
    nonempty = [name for name, payload in pools.items() if payload]
    if nonempty:
        if len(nonempty) != 1:
            raise ValueError('Unknown combined literal-pool layout')
        _, functions, relocations = parse_object(obj)
        names = set(functions) | {name for entries in relocations.values() for _, name in entries}
        anchors = {name: int(name.split('_', 1)[1], 16) for name in names
            if re.fullmatch(r'(?:func_|D_)[0-9A-F]{8}', name)}
        script = obj.with_suffix('.ld')
        section = nonempty[0]
        script.write_text('SECTIONS { .text 0x1516D400 : SUBALIGN(4) { *(.text) } '
            '%s 0x8008CBF4 : SUBALIGN(4) { *(%s) } }\n' % (section, section))
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', 'func_1516D400',
            *['--defsym=%s=0x%X' % item for item in anchors.items()], '-o', str(obj.with_suffix('.elf')),
            str(obj)], check=True, capture_output=True)
        data = sections(obj.with_suffix('.elf'))['.text'][1]
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>266I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), diagnostics=diagnostics,
        pool_bytes=sum(map(len, pools.values())), pool_sections={name: len(payload) for name, payload in pools.items()},
        frame=(0x10000 - (words[0] & 65535)) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out)
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['pool_bytes']) != (266, 400, 0, '', 0):
        raise ValueError('Edge emitter is not a direct match: ' + repr({key: value for key, value in row.items() if key != 'different_words'}))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, path.with_suffix('.o'), OWNER)
    f = functions[FUNCTION]
    if f['size'] != 1064 or list(struct.unpack_from('>266I', data, f['value'])) != words:
        raise ValueError('Edge-emitter production padding differs')
    return obj, words, row


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--lifetimes', action='store_true')
    args = parser.parse_args()
    bodies = {'selected': SELECTED}
    if args.screen:
        body = SELECTED.replace('FloatTable3_19A8B0 initial = D_8008CBF4;', 'FloatTable3_19A8B0 initial;').replace(
            'FloatTable3_19A8B0 ranges = D_8008CC00;', 'FloatTable3_19A8B0 ranges;').replace(
            'ByteTable9_19A8B0 colors = D_8008CC0C;', 'ByteTable9_19A8B0 colors;').replace(
            '    current = vertices;', '    initial = D_8008CBF4;\n    ranges = D_8008CC00;\n    colors = D_8008CC0C;\n    current = vertices;')
        literal = SELECTED.replace('FloatTable3_19A8B0 initial = D_8008CBF4;', 'f32 initial[3] = {143.0f, 30.0f, 30.0f};').replace(
            'FloatTable3_19A8B0 ranges = D_8008CC00;', 'f32 ranges[3] = {571.0f, 130.0f, 130.0f};').replace(
            'ByteTable9_19A8B0 colors = D_8008CC0C;', 'u8 colors[9] = {134, 106, 60, 200, 190, 180, 255, 210, 128};').replace(
            'ranges.values[kind]', 'ranges[kind]').replace('colors.values +', 'colors +')
        bodies = {'assignments': body, 'literal-tables': literal,
            'literal-initial': literal.replace('143.0f * scale', 'initial[0] * scale'),
            'const-literal': literal.replace('f32 initial[3]', 'const f32 initial[3]').replace(
                'f32 ranges[3]', 'const f32 ranges[3]').replace('u8 colors[9]', 'const u8 colors[9]').replace('u8 *color;', 'const u8 *color;')}
    if args.lifetimes:
        plain = SELECTED.replace('(&count)[0]', 'count')
        inline = plain.replace('    s32 width;\n', '').replace('    s32 lifetime;\n', '').replace('    f32 inverse;\n', '').replace(
            '            width = (s32)(836.0f * scale);\n', '').replace('            lifetime = (s32)(143.0f * scale);\n', '').replace(
            '            inverse = 1.0f / (f32)(count - 1);\n', '').replace('index * inverse', 'index * (1.0f / (f32)(count - 1))').replace(
            '(u32)width', '(u32)(s32)(836.0f * scale)').replace('+ lifetime', '+ (s32)(143.0f * scale)')
        def addressed(body, edge=False, count=False):
            if edge:
                for old in ('if (edge != 3)', 'if (edge == 0 || edge == 2)', 'edge + 1', 'while (edge != 4)'):
                    body = body.replace(old, old.replace('edge', '(&edge)[0]'))
            if count:
                body = body.replace('if (count > 0)', 'if ((&count)[0] > 0)').replace('count - 1', '(&count)[0] - 1').replace(
                    'index != count', 'index != (&count)[0]')
            return body
        bodies = {'plain-count': plain, 'inline-invariants': inline, 'addressed-edge': addressed(plain, edge=True),
            'addressed-count': addressed(plain, count=True),
            'inline-addressed': addressed(inline, edge=True, count=True)}
    for label, selected in bodies.items():
        _, _, row = measure(root, root / BUILD, label, selected)
        print(json.dumps({key: value for key, value in row.items() if key != 'different_words'}), flush=True)
