"""Recover the clip-default/orthographic setup without editing production."""
import hashlib
import json
from pathlib import Path
import shlex
import struct
import subprocess

from tools.experiments import game_remaining_donor_candidates as build
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-view-orthographic-setup'
FUNCTION, OWNER, ENTRY, ROM, WORDS = 'func_1510B070', 'generated_138520', 0x1510B070, 0x138520, 46
PATHS = {
    'elf': 'conker/build/conker.us.elf', 'owner': 'conker/src/game/generated_138520.c',
    'guards': 'conker/retail_word_patches.us.csv', 'progress': 'conker/progress.csv',
    'makefile': 'conker/Makefile', 'functions': 'conker/include/functions.h',
    'variables': 'conker/include/variables.h', 'structs': 'conker/include/structs.h',
    'layout': 'conker/retail_layout.us.txt', 'original': 'conker/asm/138520.s',
    'caller_init': 'conker/asm/nonmatchings/game_476D0/func_1501A220.s',
    'caller_scene': 'conker/asm/nonmatchings/game_34F20/func_15007B3C.s',
    'callee': 'conker/src/game/generated_21CCB0.c', 'callee_original': 'conker/asm/21CCB0.s',
    'converter': 'conker/src/libultra/gu/mtxutil2.c', 'sdk': 'conker/include/2.0L/PR/gu.h',
}
BASELINE = {
    'elf': '7328baa3d6e02c46ba323034c3400d9644ff798d76a55cf062fff676155dacde',
    'owner': '02bdc24e7b996e207b664045d0ed1107cf2d8eb752b0a8f5eff90fe59e3a3f0b',
    'guards': 'b83e74a2f547c1274f9763a6afea8aa82781e338949247cea91eb63d36fc984a',
    'progress': 'e3ea336daf5c7c20478bd705eec06b202685d29498d7797a6a546c2476211c78',
    'makefile': '838070597f76ea2f7182c158dfb6710946cfcabcb5435e994f93cdb99340e313',
    'functions': '2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81',
    'variables': '1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8',
    'structs': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'layout': 'a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5',
    'original': 'ad0efe574a623e2a2a9ef2446c7536d7ccf35a12d90388c7cf60aa947e519761',
    'caller_init': 'da7b442df6b30f6a600766a164d4240eacd91716f2aed05a5a5a68fc642ab79f',
    'caller_scene': 'fbe6f895bfe7849d87ef1a8b9a32bdffaaa0b6c64032c99c2e919cce9345e422',
    'callee': '239c3c97e4edb580e44b2d26d583a2967dd2a8ad5503aa75f5e0596ebc35dcac',
    'callee_original': 'a80c543f32b395b6a200ccf83767de07c806ae49f5b5747ef571e2abc95b9693',
    'converter': '45ad70401c273ef3d4ddf922da65e09ec1a1da82d93d4f0fb352a06d82597fc3',
    'sdk': 'bc7761b1d0688b009d82a17776e21782842b652eb5b257088458b9fee8c63cff',
}
DECLARATIONS = '''extern s16 D_800DD2F2, D_800DD2F4;
extern f32 D_800D3670, D_800A2C20;
extern Mtx D_800D9B28;
void func_151EF954(Mtx *matrix, f32 left, f32 right, f32 bottom, f32 top,
                  f32 nearPlane, f32 farPlane, f32 scale);
'''
BODY = '''/* Initialize clip defaults and build the shared orthographic projection. */
void func_1510B070(s32 unused) {
    D_800D9B20 = D_800DD2F2;
    D_800D9B1C = D_800DD2F4;
    D_800D3670 = 100.0f - D_800D9B1C;
    func_151EF954(&D_800D9B28,
        -PROJECTION_VIEWS_138520[0].extentX, PROJECTION_VIEWS_138520[0].extentX,
        -PROJECTION_VIEWS_138520[0].extentY, PROJECTION_VIEWS_138520[0].extentY,
        1.0f, D_800A2C20, 1.0f);
}
'''


def recover(before, body=BODY):
    lo, hi = build.function_span(before, FUNCTION)
    result = before[:lo] + body.rstrip() + before[hi:]
    return result.replace('extern u8 *D_800BE628;\n', 'extern u8 *D_800BE628;\n\n' + DECLARATIONS, 1)


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed orthographic setup baseline')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified orthographic setup manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable orthographic setup input: ' + key)


def compile_sdk(root, out, text, path, label):
    if '#pragma GLOBAL_ASM' in text:
        raise ValueError('Expected plain SDK C, not an assembly-processor input')
    target = 'build/' + path.removeprefix('conker/').removesuffix('.c') + '.c.o'
    plan = subprocess.run(['make', '-n', '-B', target], cwd=root / 'conker', capture_output=True, text=True, check=True)
    commands = [shlex.split(line) for line in plan.stdout.splitlines() if line.startswith('../ido/') and '/cc ' in line]
    if len(commands) != 1 or '-O3' not in commands[0] or '-g3' in commands[0]:
        raise ValueError('Unexpected current SDK compiler profile')
    command = commands[0]
    raw, obj = out / (label + '.c'), out / (label + '.o')
    raw.write_text(text)
    command[command.index('-o') + 1] = str(obj.relative_to(root / 'conker'))
    command[-1] = str(raw.relative_to(root / 'conker'))
    result = subprocess.run(command, cwd=root / 'conker', capture_output=True, text=True)
    diagnostics = result.stdout + result.stderr
    if result.returncode:
        raise ValueError(diagnostics)
    (out / (label + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
    return obj, diagnostics


def variants():
    for pointer in (False, True):
        start = BODY
        if pointer:
            start = start.replace('    D_800D9B20 =', '    f32 *farDefault = &D_800D9B1C;\n\n    D_800D9B20 =', 1)
            start = start.replace('    D_800D9B1C =', '    *farDefault =', 1).replace('100.0f - D_800D9B1C', '100.0f - *farDefault')
        for extents in ('direct', 'xy', 'yx', 'view-xy', 'view-yx'):
            result = start
            if extents != 'direct':
                view = extents.startswith('view-')
                order = extents[-2:]
                declaration = '    f32 width, height;\n'
                if view:
                    declaration += '    ViewProjection138520 *view;\n'
                at = result.index('    D_800D9B20 =')
                result = result[:at] + declaration + result[at:]
                loads = '    view = (ViewProjection138520 *)D_800BE628;\n' if view else ''
                field = lambda axis: ('view->' if view else 'PROJECTION_VIEWS_138520[0].') + 'extent' + axis
                for axis in order:
                    loads += '    %s = %s;\n' % ('width' if axis == 'x' else 'height', field(axis.upper()))
                result = result.replace('    func_151EF954(', loads + '    func_151EF954(', 1)
                result = result.replace('PROJECTION_VIEWS_138520[0].extentX', 'width').replace('PROJECTION_VIEWS_138520[0].extentY', 'height')
                if not view:
                    result = result.replace('width = width;', 'width = PROJECTION_VIEWS_138520[0].extentX;').replace('height = height;', 'height = PROJECTION_VIEWS_138520[0].extentY;')
            yield ('far-pointer-' if pointer else '') + extents, result
            yield ('far-pointer-' if pointer else '') + extents + '-scale', result.replace('    D_800D9B20 =', '    f32 scale = 1.0f;\n\n    D_800D9B20 =', 1).replace('1.0f, D_800A2C20, 1.0f', 'scale, D_800A2C20, scale')


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    rom = (root / 'conker/conker.us.bin').read_bytes()
    retail = struct.unpack_from('>46I', rom, ROM)
    records = []
    for label, body in variants():
        obj, diagnostics = build.compile_owner(root, out, recover(before, body), label)
        data, functions = build.link_owner(root, out, obj, OWNER)
        info = functions[FUNCTION]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
        _, _, relocations = parse_object(obj)
        row = dict(label=label, bytes=info['size'], frame=(-words[0] & 65535), diagnostics=diagnostics,
            differences=[(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, retail)) if a != b],
            word_length_difference=len(words) - 46,
            relocations={at - info['value']: uses for at, uses in relocations.items() if info['value'] <= at < info['value'] + info['size']})
        records.append(row)
        print(label, row['bytes'], row['frame'], len(row['differences']), row['word_length_difference'], diagnostics, flush=True)
    (out / 'screens.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
