"""Recover the signed-remainder directional burst and its two factory packets."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_quad_edge_match as previous
from tools.tests import quad_edge_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections

BUILD = 'conker/build/game-directional-burst'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_15170500', 0x15170500, 0x19D9B0, 184
RANDOM, COSINE, SINE = 0x151EF610, 0x150489B0, 0x15048A40
SMALL, LARGE, DEFAULT_ANGLE = 0x1516D4E8, 0x1516D99C, 0x800CC34A
PATHS = dict(previous.PATHS,
    burst_random_original='conker/asm/21CAC0.s',
    burst_random_owner='conker/src/game/generated_21CAC0.c',
    burst_callers_original='conker/asm/1A89B0.s',
    burst_callers_owner='conker/src/game/generated_1A89B0.c')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    burst_random_original='c8dba5dfa661dda396572e3de1f9e761b2f02ba877b64d1b12ce6a2542597f83',
    burst_random_owner='0ec5dc338449c6099427103d2ef429124907e49645c4c6c03ea6e1b1c11ae772',
    burst_callers_original='fafc0f4f919a04f2e0ac4dcf5f68376006198392b69974ede1bf25885f10f085',
    burst_callers_owner='ab5d655e3c32b2aece91f0d8d05290fcda0823f75a1a011eb56af55e3ba987f4')
build = previous.build
DECLARATIONS = '''extern u16 D_800CC34A;
s32 func_151EF610(void);

'''
SELECTED = '''/* Emit a directional burst using the compact or extended record factory. */
void func_15170500(s16 x, s16 y, s16 z, s32 angle, s32 compact,
                  u8 flags, s32 context) {
    f32 yawCosine;
    f32 negativeYawSine;
    s32 polar;
    s32 yawByte;
    f32 polarCosine;
    f32 vx;
    f32 vy;
    f32 vz;
    s32 fx;
    s32 fz;
    s32 fy;

    if (compact == 0) {
        angle = D_800CC34A;
    }
    polar = func_151EF610() % 50;
    yawByte = angle & 0xFF;
    yawCosine = func_150489B0((u8)yawByte);
    negativeYawSine = -func_15048A40((u8)(&yawByte)[0]);
    polarCosine = func_150489B0((u8)(&polar)[0]);
    vx = yawCosine * polarCosine;
    vz = negativeYawSine * polarCosine;
    vy = 0.0f;
    vx *= 2.0f;
    vy *= 2.0f;
    vz *= 2.0f;
    if (compact != 0) {
        fx = (s32)(vx * 256.0f);
        fz = (s32)(vz * 256.0f);
        fy = (s32)(vy * 256.0f);
        func_1516D4E8(x, y, z, 0x2A, 0, 255, 255, 255, 0, 0, 0, 0, 6,
            fx >> 8, fx & 255, fz >> 8, fz & 255, 0, 0, 0, 0, 0, 1,
            0x200, 0x166, 255, fy - 50, 0, 0, flags, context);
    } else {
        fx = (s32)(vx * 256.0f);
        fz = (s32)(vz * 256.0f);
        fy = (s32)(vy * 256.0f);
        func_1516D99C(x, y, z, 0x2A, 0, 255, 255, 255, 0, 0, 0, 0, 6,
            fx >> 8, fx & 255, fz >> 8, fz & 255, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0x200, 0x166, 0, 0, 20, 0, 0, 255, 255, fy - 50,
            200, 9, 1, 0, 1, 50, 20, 0, 0, 0, flags, context);
    }
}
'''

INITIAL = SELECTED
SELECTED = INITIAL.replace('func_15048A40((u8)(&yawByte)[0])', 'func_15048A40((u8)yawByte)').replace(
    '    s32 yawByte;', '    u8 yawByte;').replace('yawByte = angle & 0xFF;', 'yawByte = angle;').replace(
    '    vy = 0.0f;\n', '').replace('    polar =', '    vy = 0.0f;\n    polar =', 1)
_lo, _hi = SELECTED.index('    f32 yawCosine;'), SELECTED.index('\n\n    if (compact')
_declarations = {line.split()[-1].rstrip(';'): line for line in SELECTED[_lo:_hi].splitlines()}
HOME_ORDER = ('yawCosine', 'vx', 'negativeYawSine', 'vy', 'vz', 'fx', 'fz', 'fy', 'polarCosine', 'polar', 'yawByte')
if set(HOME_ORDER) != set(_declarations) or len(HOME_ORDER) != len(_declarations):
    raise ValueError('Directional burst must retain each real local once')
SELECTED = SELECTED[:_lo] + '\n'.join(_declarations[name] for name in HOME_ORDER) + SELECTED[_hi:]


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed directional-burst predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed directional-burst baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed directional-burst fixture: ' + key)


def recovered_owner(before, body=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15170500() {\n    return 0;\n}':
        raise ValueError('Unknown directional-burst placeholder')
    marker = '/* Non-matching placeholders for the text-only asm slice asm/19A8B0.s. */'
    return (before[:lo] + body.rstrip() + before[hi:]).replace(marker, DECLARATIONS + marker, 1)


def measure(root, out, label='selected', body=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text(), body), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>184I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    pools = sections(obj)
    row = dict(label=label, words=len(words), diagnostics=diagnostics,
        frame=(0x10000 - (words[0] & 65535)) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        pool_bytes=sum(len(pools.get(name, (0, b''))[1]) for name in ('.rodata', '.data')),
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    print(json.dumps({k: v for k, v in measure(root, root / BUILD)[-1].items() if k != 'different_words'}, indent=2))
