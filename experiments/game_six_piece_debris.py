"""Recover six live-table debris packets without importing the reference's ABI errors."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_scaled_random_spray as previous
from tools.tests import scaled_random_spray_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-six-piece-debris'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19E040', 'func_15170B90', 0x15170B90, 0x19E040, 205
LOOKUP, RANDOM, SUBMIT, RING = 0x1518C900, 0x150ADA20, 0x15168BE4, 0x151718F0
PATHS = dict(previous.PATHS,
    debris_constants='conker/asm/data/24BA40.rodata.s',
    debris_vectors='conker/asm/data/24B950.rodata.s',
    debris_consumer='conker/src/game_1944C0.c',
    debris_consumer_original='conker/asm/nonmatchings/game_1944C0/func_15168BE4.s',
    debris_lookup_original='conker/asm/1B9DB0.s',
    debris_reference='../Another Source/CBFD-Recompiled/conker/conker/src/game/game_19E040.c')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    debris_constants='250b8d34c978054afb26383c8a014929e4d6423c4c3c3c7677038d7bebd4d37e',
    debris_vectors='55e54f8a437cdb85d255a9f0a5f7a8d3eaccc82e75a98af76846b86bfb198b4c',
    debris_consumer='328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b',
    debris_consumer_original='622a2774bc390df96a7334efabfba73e93d475f41d05ce2a7d47d2ab526ca37f',
    debris_lookup_original='c058556165e1597b772e427169df34763a395572685a4dc40f75ad947f056edb',
    debris_reference='05648d5f4ff84b71b4a6762520f12c18183c4aee440badd5ccedc8d0be86bca4')
build = previous.build

DECLARATIONS = '''typedef struct DebrisKinds19E040 {
    u8 values[6];
} DebrisKinds19E040;

typedef struct DebrisPacket19E040 {
    f32 position[3];
    f32 rotation[3];
    f32 velocity[3];
    f32 spin[3];
    f32 scale[3];
    s32 lifetime;
    s32 asset;
    u8 reserved44[4];
    f32 coefficient[3];
    u8 mode, alpha, zero56, zero57, zero58, duration, kind, variant;
    u8 zero5C, zero5D;
    u8 reserved5E[2];
} DebrisPacket19E040;

extern DebrisKinds19E040 D_800A6F80;
extern f32 D_800A6E90[18];
extern f32 D_800A6F88, D_800A6F8C, D_800A6F90, D_800A6F94;
s32 func_1518C900(s32 kind);
s32 func_150ADA20(void);
f32 fabsf(f32 value);
#pragma intrinsic (fabsf)
void func_15168BE4(void *packet, u8 flags, s32 context);
s32 func_151718F0(f32 x, f32 y, f32 z, f32 radius, s32 lifetime,
                  f32 speed, s32 kind, s32 count, u8 flags, s32 context);

'''

SELECTED = '''/* Emit six debris pieces, then a ring, and mark the actor's byte flag.
 * The copied packet's reserved bytes intentionally retain stack residue. */
void func_15170B90(u8 *actor, s32 baseKind, s32 variant, s32 options,
                  u8 flags, s32 context) {
    DebrisPacket19E040 packet;
    DebrisKinds19E040 kinds;
    f32 originX;
    f32 originY;
    f32 originZ;
    f32 coefficient;
    f32 *vector;
    f32 x;
    f32 y;
    f32 z;
    s32 index;
    s32 kind;
    s32 asset;

    originX = (f32)*(s16 *)(actor + 0x10);
    originY = (f32)*(s16 *)(actor + 0x12);
    originZ = (f32)*(s16 *)(actor + 0x14);
    packet.rotation[0] = 0.0f;
    packet.rotation[1] = 0.0f;
    packet.rotation[2] = 0.0f;
    packet.scale[0] = 1.0f;
    packet.scale[1] = 1.0f;
    packet.scale[2] = 1.0f;
    packet.lifetime = 60;
    packet.coefficient[0] = D_800A6F88;
    packet.coefficient[1] = D_800A6F8C;
    packet.coefficient[2] = D_800A6F90;
    packet.mode = 2;
    packet.alpha = 255;
    packet.zero56 = 0;
    packet.zero57 = 0;
    packet.zero58 = 0;
    packet.duration = 60;
    packet.variant = variant;
    packet.zero5C = 0;
    packet.zero5D = 0;
    coefficient = D_800A6F94;
    index = 0;
    vector = D_800A6E90;
    do {
        if (options & 2) {
            kinds = D_800A6F80;
            kind = kinds.values[index];
        } else {
            kind = baseKind;
            if (options & 1) {
                kind = (s32)((u32)baseKind + (u32)index);
            }
        }
        asset = func_1518C900(kind);
        x = vector[0];
        y = vector[1];
        z = vector[2];
        packet.position[0] = x + originX;
        packet.position[1] = y + originY;
        packet.position[2] = z + originZ;
        packet.kind = kind;
        packet.velocity[0] = x * coefficient;
        packet.velocity[1] = fabsf(y) * coefficient + 7.0f;
        packet.velocity[2] = z * coefficient;
        packet.velocity[0] += (f32)(func_150ADA20() >> 16) * 0.00006103515625f;
        packet.velocity[1] += (f32)(func_150ADA20() >> 16) * 0.00006103515625f;
        packet.velocity[2] += (f32)(func_150ADA20() >> 16) * 0.00006103515625f;
        packet.spin[0] = (f32)(func_150ADA20() >> 16) * 0.0000762939453125f;
        packet.spin[1] = (f32)(func_150ADA20() >> 16) * 0.0000762939453125f;
        packet.spin[2] = (f32)(func_150ADA20() >> 16) * 0.0000762939453125f;
        packet.asset = asset;
        func_15168BE4(&packet, flags, context);
        index += 1;
        vector += 3;
    } while (index != 6);
    func_151718F0(originX, originY - 80.0f, originZ, 70.0f,
                  500, 0.00457763671875f, 0, 10, flags, context);
    actor[0x6E] = 1;
}
'''

RING_STUB = '''s32 func_151718F0(f32 x, f32 y, f32 z, f32 radius, s32 lifetime,
                  f32 speed, s32 kind, s32 count, u8 flags, s32 context) {
    return 0;
}'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed debris predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed debris manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed debris fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15170B90() {\n    return 0;\n}':
        raise ValueError('Unknown debris placeholder')
    result = before[:lo] + selected.rstrip() + before[hi:]
    lo, hi = build.function_span(result, 'func_151718F0')
    if result[lo:hi] != 's32 func_151718F0() {\n    return 0;\n}':
        raise ValueError('Unknown ring placeholder')
    result = result[:lo] + RING_STUB + result[hi:]
    return result.replace('extern s32 D_800BE9F0;', DECLARATIONS + 'extern s32 D_800BE9F0;', 1)


def measure(root, out, label='selected', selected=SELECTED, flags=('-O2', '-g3')):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-edge_wrapper_owner').read_text(), selected), label, flags=flags)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM))
    pools = sections(obj)
    raw, _, rel = parse_object(obj)
    row = dict(label=label, flags=flags, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, pool_bytes=sum(len(pools.get(n, (0, b''))[1]) for n in ('.rodata', '.data')),
        raw_sha256=hashlib.sha256(raw[f['value']:f['value'] + f['size']]).hexdigest(),
        relocations={at - f['value']: rows for at, rows in rel.items() if f['value'] <= at < f['value'] + f['size']},
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def screens(root, out):
    saved_flags = SELECTED.replace('    s32 asset;', '    s32 asset;\n    u8 savedFlags;').replace(
        '    index = 0;', '    savedFlags = flags;\n    index = 0;').replace(
        '(&packet, flags, context)', '(&packet, savedFlags, context)').replace(
        '0, 10, flags, context)', '0, 10, savedFlags, context)')
    early = saved_flags.replace('    coefficient = D_800A6F94;\n', '').replace(
        '    packet.rotation[0]', '    coefficient = D_800A6F94;\n    packet.rotation[0]', 1)
    ordered = early.replace('    f32 z;', '    f32 z;\n    f32 vertical;').replace(
        '        packet.position[0] = x + originX;\n        packet.position[1] = y + originY;\n        packet.position[2] = z + originZ;',
        '        vertical = fabsf(y) * coefficient;\n        packet.position[1] = y + originY;\n        packet.position[0] = x + originX;').replace(
        '        packet.velocity[1] = fabsf(y) * coefficient + 7.0f;\n', '').replace(
        '        packet.velocity[2] = z * coefficient;',
        '        packet.velocity[2] = z * coefficient;\n        packet.position[2] = z + originZ;\n        packet.velocity[1] = vertical + 7.0f;')
    for name, body in (('saved-flags', saved_flags), ('early-coefficient', early),
            ('ordered', ordered), ('word-flags', ordered.replace('u8 flags, s32 context)', 's32 flags, s32 context)'))):
        _, _, row = measure(root, out, name, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame', 'differences', 'raw_sha256')}), flush=True)


def profile_screens(root, out):
    for name, flags in (('o2', ('-O2',)), ('o1', ('-O1',))):
        _, _, row = measure(root, out, 'profile-' + name, flags=flags)
        print(json.dumps({k: row[k] for k in ('label', 'flags', 'words', 'frame', 'differences', 'raw_sha256')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--profile-screen', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.profile_screen:
        profile_screens(root, root / BUILD)
    elif args.screen:
        screens(root, root / BUILD)
    else:
        print(json.dumps({k: v for k, v in measure(root, root / BUILD)[-1].items() if k != 'different_words'}, indent=2))
