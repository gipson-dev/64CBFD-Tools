"""Recover the two-index view FOV adjustment's complete retail access shape."""
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_cosine_candidates as cosine
from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-view-fov-transfer'
FUNCTION, OWNER, ENTRY, ROM, WORDS = 'func_1501B0A0', 'game_476D0', 0x1501B0A0, 0x48550, 99
GUARDS = (
    (0x04, 0xAFBF001C, 0x3C010000, '-', 'R_MIPS_HI16:D_800968F4'),
    (0x08, 0xAFA40050, 0xC4200000, '-', 'R_MIPS_LO16:D_800968F4'),
    (0x0C, 0xAFA50054, 0xAFBF001C, '-', '-'),
    (0x10, 0x8FA30050, 0xAFA40050, '-', '-'),
    (0x14, 0x3C0F0000, 0xAFA50054, 'R_MIPS_HI16:D_800BE628', '-'),
    (0x18, 0x8DEF0000, 0x8FA30050, 'R_MIPS_LO16:D_800BE628', '-'),
    (0x1C, 0x00037080, 0x3C0F0000, '-', 'R_MIPS_HI16:D_800BE628'),
    (0x20, 0x01C37023, 0x8DEF0000, '-', 'R_MIPS_LO16:D_800BE628'),
    (0x24, 0x000E71C0, 0x00037080, '-', '-'),
    (0x28, 0x3C010000, 0x01C37023, 'R_MIPS_HI16:D_800968F4', '-'),
    (0x2C, 0x01EE1021, 0x000E71C0, '-', '-'),
    (0x30, 0xC444006C, 0x01EE1021, '-', '-'),
    (0x34, 0xC4200000, 0xC444006C, 'R_MIPS_LO16:D_800968F4', '-'),
)
GUARD_ROWS = ''.join('%s,%s,0x%X,0x%08X,0x%08X,%s,%s,Move independent half-angle coefficient load before indexed view prologue,,,false\n' %
    ((OWNER, FUNCTION) + row) for row in GUARDS)
PATHS = dict(cosine.PATHS)
PATHS.update(owner='conker/src/game_476D0.c', original='conker/asm/nonmatchings/game_476D0/func_1501B0A0.s')
PATHS.update(angle_helper='conker/src/game/done/game_75950.c', command='conker/src/game/generated_138520.c')
BASELINE = dict(cosine.BASELINE,
    elf='b87dd5bcf0d6549080560feb1122f90d7b57614bdd220c29eaa75e2d0fc0cf0b',
    cosf='8947b41f56a8854981be155231dfbb5d4f0b885c4c60d4cdc7bba069f8841b09',
    owner='8bba4f1abbd69d9032a5fe0be73238d84f6b13ecf44716938037ef03f9cb0aae',
    original='443b168b89907f43fc24662aaeff57a6ba7d9178bbef40fd759924806545c1f5',
    angle_helper='eef615727936f3f0c08a6893979022a2ecb39edf834b1fb1c8f86dbe208ba50f',
    command='152336b59dde6dca1da8d07cdb7b9ac5a8585725e0e76221315e404e19923d57')

PREAMBLE = '''typedef struct {
    u8 padding0[0xC];
    f32 extentX, extentY;
    u8 padding14[0x58];
    f32 baseFovX, baseFovY;
    u8 padding74[0x10C];
} ViewProjection476D0;
extern f32 D_800968F4, D_800968F8, D_800968FC;
s32 func_1510B128(s32 index, f32 offsetX, f32 offsetY, f32 scale, f32 fallback);
#define VIEW_PROJECTIONS_476D0 ((ViewProjection476D0 *)D_800BE628)
'''
BODY = '''/* Transfer the reference viewport's projection into this view's FOV offsets. */
void func_1501B0A0(s32 index, s32 reference) {
    f32 halfX, halfY, tangentX, tangentY, extentX, extentY, offsetX, offsetY;

    halfX = VIEW_PROJECTIONS_476D0[index].baseFovX * D_800968F4;
    halfY = VIEW_PROJECTIONS_476D0[index].baseFovY * D_800968F4;
    tangentX = sinf(halfX) / cosf(halfX);
    tangentY = sinf(halfY) / cosf(halfY);
    extentX = ((s32 *)&D_800BE638)[reference] / (tangentX + tangentX);
    extentY = ((s32 *)&D_800BE650)[reference] / (tangentY + tangentY);
    offsetX = func_150484A0(VIEW_PROJECTIONS_476D0[index].extentX, extentX) *
              D_800968F8 - VIEW_PROJECTIONS_476D0[reference].baseFovX;
    offsetY = func_150484A0(VIEW_PROJECTIONS_476D0[index].extentY, extentY) *
              D_800968FC - VIEW_PROJECTIONS_476D0[reference].baseFovY;
    func_1510B128(index, offsetX, offsetY, 1.0f, 0.0f);
}
'''


def recover(before, body=BODY, preamble=PREAMBLE):
    lo, hi = build.function_span(before, FUNCTION)
    result = before[:lo] + body.rstrip() + before[hi:]
    result = result.replace('s32 ' + FUNCTION + '();\n', '')
    result = result.replace('void func_1501B22C(s32 index);',
        preamble + '\nvoid func_1501B0A0(s32 index, s32 reference);\nvoid func_1501B22C(s32 index);', 1)
    result = result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501B0A0.s. */\n', '')
    return result


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if hashlib.sha256(data['elf']).hexdigest() != BASELINE['elf']:
            raise ValueError('Changed view-transfer baseline image')
        for key, value in data.items():
            digest = hashlib.sha256(value).hexdigest()
            if key in BASELINE and digest != BASELINE[key]:
                raise ValueError('Changed view-transfer baseline input: ' + key)
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    pins = json.loads(manifest.read_text())
    missing = set(BASELINE) - set(pins)
    if missing:
        if hashlib.sha256((root / PATHS['elf']).read_bytes()).hexdigest() != BASELINE['elf']:
            raise ValueError('Cannot extend dependency capture after image changes')
        for key in sorted(missing):
            value = (root / PATHS[key]).read_bytes()
            if hashlib.sha256(value).hexdigest() != BASELINE[key] or (out / ('before-' + key)).exists():
                raise ValueError('Changed or already captured dependency: ' + key)
            (out / ('before-' + key)).write_bytes(value)
            pins[key] = BASELINE[key]
        manifest.write_text(json.dumps(pins, indent=2) + '\n')
    if pins != BASELINE:
        raise ValueError('Modified immutable view-transfer manifest')
    for key, digest in pins.items():
        if key in BASELINE and digest != BASELINE[key]:
            raise ValueError('Modified immutable view-transfer manifest: ' + key)
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable view-transfer input: ' + key)


def variants():
    yield 'selected', BODY
    yield 'early-extents', BODY.replace(
        '    tangentX =', '    extentX = ((s32 *)&D_800BE638)[reference];\n    extentY = ((s32 *)&D_800BE650)[reference];\n    tangentX =').replace(
        '((s32 *)&D_800BE638)[reference] /', 'extentX /').replace('((s32 *)&D_800BE650)[reference] /', 'extentY /')
    for x_first, split_trig in itertools.product((False, True), repeat=2):
        result = BODY
        if x_first:
            result = result.replace('halfX = VIEW_PROJECTIONS_476D0[index].baseFovX * D_800968F4;',
                                    'halfX = D_800968F4 * VIEW_PROJECTIONS_476D0[index].baseFovX;')
            result = result.replace('halfY = VIEW_PROJECTIONS_476D0[index].baseFovY * D_800968F4;',
                                    'halfY = D_800968F4 * VIEW_PROJECTIONS_476D0[index].baseFovY;')
        if split_trig:
            result = result.replace('tangentX = sinf(halfX) / cosf(halfX);', 'tangentX = sinf(halfX);\n    tangentX /= cosf(halfX);')
            result = result.replace('tangentY = sinf(halfY) / cosf(halfY);', 'tangentY = sinf(halfY);\n    tangentY /= cosf(halfY);')
        yield 'shape-%d-%d' % (x_first, split_trig), result
    scale = BODY.replace('    f32 halfX,', '    f32 angleScale;\n    f32 halfX,')
    scale = scale.replace('    halfX =', '    angleScale = D_800968F4;\n    halfX =', 1)
    scale = scale.replace(' * D_800968F4;', ' * angleScale;')
    yield 'coefficient-first', scale
    yield 'coefficient-initializer', scale.replace('f32 angleScale;', 'f32 angleScale = D_800968F4;').replace(
        '    angleScale = D_800968F4;\n', '')


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    rom = (root / 'conker/conker.us.bin').read_bytes()
    expected = list(struct.unpack_from('>99I', rom, ROM))
    rows = []
    cases = [(label, body, PREAMBLE) for label, body in variants()]
    cases += [('first-const', BODY, PREAMBLE.replace('extern f32 D_800968F4, D_800968F8, D_800968FC;',
               'extern const f32 D_800968F4;\nextern f32 D_800968F8, D_800968FC;')),
              ('all-const', BODY, PREAMBLE.replace('extern f32 D_800968F4,', 'extern const f32 D_800968F4,'))]
    reuse = BODY.replace('    halfX =', '    halfY = D_800968F4;\n    halfX =', 1)
    reuse = reuse.replace(' * D_800968F4;', ' * halfY;')
    cases.append(('half-y-coefficient', reuse, PREAMBLE))
    for label, body, preamble in cases:
        obj, diagnostics = build.compile_owner(root, out, recover(before, body, preamble), label)
        data, functions = build.link_owner(root, out, obj, OWNER)
        info = functions[FUNCTION]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
        different = [(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, expected)) if a != b]
        row = dict(label=label, code_bytes=info['size'], differences=different,
                   uncompared_slot_words=max(0, WORDS - len(words)), diagnostics=diagnostics)
        rows.append(row)
        print(label, info['size'], len(different), row['uncompared_slot_words'], diagnostics, flush=True)
    (out / 'candidates.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
