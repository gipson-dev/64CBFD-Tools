"""Recover the signed-view point projection and handwritten four-output tail ABI."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_view_scissor_setup as previous
from tools.tests import view_scissor_checkpoint as checkpoint
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections
from tools import pad_c_object

BUILD = 'conker/build/game-view-point-projection-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'game_476D0', 'func_1501A764', 0x1501A764, 0x47C14, 87
PATHS = dict(previous.PATHS,
    point_original='conker/asm/nonmatchings/game_476D0/func_1501A764.s',
    point_caller_a='conker/asm/197C20.s', point_caller_b='conker/asm/157840.s',
    point_caller_c='conker/asm/1A11B0.s',
    point_matrix='conker/asm/nonmatchings/generated_D4E10/func_150A7960.s',
    point_tail='conker/asm/nonmatchings/generated_D4E10/func_150A7A00.s',
    point_continuation='conker/asm/nonmatchings/generated_D4E10/func_150A7A14.s',
    point_helper_owner='conker/src/game/generated_D4E10.c')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    point_original='ce66d4e2211b0e28e99139c5833a81312088f4e33b1359f2161d0706b847c622',
    point_caller_a='3a1606560974a5cea3d7c36a32f92113083f5e4f72c26f700fbb0a1d287f1450',
    point_caller_b='332a499df5aa3f6b1a052f679159c2a8be0d4ff95bebc9d7d36f5c77ca8e0bcc',
    point_caller_c='91d5b8f5d542245b976a9515019a337a34b1e2ce1e83bbd543186c1416e2553c',
    point_matrix='c535e043c91c806eafecb0ba5fa1a80570ad20d4c8488be89bebcfe53512c22d',
    point_tail='bc63fc43e4a49509e05f1c5f7073cafcc2c39be1842ed260798901f64f8f13e3',
    point_continuation='5d91f3e745aa02112818a392141ef2ff2d35995a68228c0a86dbbbbeb4ad5411',
    point_helper_owner='68fb4b7b0106aa77100dfdbc354871c48b4944462d657e61122168d5b6496f38')
build = previous.build
DECLARATION = '''/* Handwritten tail entry: matrix/XYZ words and four pointed float outputs. */
void func_150A7A00(f32 matrix[4][4], f32 x, f32 y, f32 z,
                   f32 *outX, f32 *outY, f32 *outZ, f32 *outW);'''
INITIAL = '''/* Transform a point and project it through the selected view and viewport. */
void func_1501A764(s16 view, f32 x, f32 y, f32 z, f32 *outX, f32 *outY, f32 *outZ) {
    f32 transformedX;
    f32 transformedY;
    f32 transformedZ;
    f32 reciprocalW;
    ViewProjection476D0 *record;
    Vp *viewport;

    func_150A7A00((f32 (*)[4])((u8 *)D_800D9D10 + (s32)view * 64),
        x, y, z, &transformedX, &transformedY, &transformedZ, &reciprocalW);
    reciprocalW = 1.0f / reciprocalW;
    record = &VIEW_PROJECTIONS_476D0[view];
    *outX = (record->extentX + 5.0f) * transformedX * reciprocalW + record->originX;
    record = &VIEW_PROJECTIONS_476D0[view];
    *outY = record->originY - (record->extentY + 5.0f) * transformedY * reciprocalW;
    viewport = &VIEW_PROJECTIONS_476D0[view].viewport[D_800BE9C0];
    *outZ = ((f32)viewport->vp.vtrans[2] + transformedZ * reciprocalW * (f32)viewport->vp.vscale[2]) * 32.0f;
}'''
SELECTED = INITIAL


def freeze(root, out):
    with patch.multiple(previous, PATHS=PATHS, BASELINE=BASELINE):
        previous.freeze(root, out)


def recovered_owner(before, body=None):
    body = SELECTED if body is None else body
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501A764() {\n    return 0;\n}':
        raise ValueError('Unknown point-projection predecessor')
    result = before[:lo] + body.split('\n', 1)[1] + before[hi:]
    start = result.index('// void func_1501A764(')
    end = result.index('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501A8C0.s. */', start)
    result = result[:start] + '\n' + result[end:]
    for old, new in (
        ('s32 func_1501A764();', body.splitlines()[1][:-2] + ';'),
        ('void func_150A7A00(f32 arg0, f32 arg1, s32 arg2, f32 arg3, f32 arg4, f32 arg5, f32* arg6, f32* arg7, f32* arg8, f32* arg9);', DECLARATION),
        ('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501A764.s. */', body.splitlines()[0]),
        ('    u8 padding34[0x38];', '    f32 originX, originY;\n    u8 padding3C[4];\n    Vp viewport[2];\n    u8 padding60[0xC];')):
        if result.count(old) != 1:
            raise ValueError('Unknown point-projection declaration/layout anchor')
        result = result.replace(old, new, 1)
    return result


def forms():
    yield 'initial', INITIAL
    yield 'unsigned-matrix-offset', INITIAL.replace('(s32)view * 64', '(u32)(s32)view * 64')
    yield 'inline-record', INITIAL.replace('    ViewProjection476D0 *record;\n', '').replace(
        '    record = &VIEW_PROJECTIONS_476D0[view];\n', '').replace('record->', 'VIEW_PROJECTIONS_476D0[view].')
    yield 'inline-viewport', INITIAL.replace('    Vp *viewport;\n', '').replace(
        '    viewport = &VIEW_PROJECTIONS_476D0[view].viewport[D_800BE9C0];\n', '').replace(
        'viewport->vp.', 'VIEW_PROJECTIONS_476D0[view].viewport[D_800BE9C0].vp.')


def lifetime_forms():
    for label, body in forms():
        if label == 'inline-viewport':
            yield 'inline-all', body.replace('    ViewProjection476D0 *record;\n', '').replace(
                '    record = &VIEW_PROJECTIONS_476D0[view];\n', '').replace('record->', 'VIEW_PROJECTIONS_476D0[view].')
    shared = INITIAL.replace('    Vp *viewport;\n', '').replace(
        '    viewport = &VIEW_PROJECTIONS_476D0[view].viewport[D_800BE9C0];',
        '    record = (ViewProjection476D0 *)((u8 *)&VIEW_PROJECTIONS_476D0[view] + D_800BE9C0 * 16);').replace(
        'viewport->vp.', 'record->viewport[0].vp.')
    yield 'reused-record', shared
    floats = '    f32 transformedX;\n    f32 transformedY;\n    f32 transformedZ;\n    f32 reciprocalW;\n'
    for label, body in (('original', INITIAL), ('shared', shared)):
        yield label + '-record-first', body.replace(floats, '').replace(
            '    ViewProjection476D0 *record;\n', '    ViewProjection476D0 *record;\n' + floats)
        yield label + '-float-array', body.replace(floats, '    f32 point[4];\n').replace(
            'transformedX', 'point[0]').replace('transformedY', 'point[1]').replace(
            'transformedZ', 'point[2]').replace('reciprocalW', 'point[3]')


def arithmetic_forms():
    inline = dict(lifetime_forms())['inline-all']
    for label, body in (('initial', INITIAL), ('inline-viewport', dict(forms())['inline-viewport'])):
        yield label + '-register-record', body.replace('    ViewProjection476D0 *record;',
            '    register ViewProjection476D0 *record;')
        if label == 'initial':
            yield 'register-both', body.replace('    ViewProjection476D0 *record;',
                '    register ViewProjection476D0 *record;').replace('    Vp *viewport;', '    register Vp *viewport;')
    yield 'inline-x-origin-first', inline.replace(
        '(VIEW_PROJECTIONS_476D0[view].extentX + 5.0f) * transformedX * reciprocalW + VIEW_PROJECTIONS_476D0[view].originX',
        'VIEW_PROJECTIONS_476D0[view].originX + (VIEW_PROJECTIONS_476D0[view].extentX + 5.0f) * transformedX * reciprocalW')
    for axes in ('x', 'y', 'xy', 'xyz'):
        body = inline
        for axis, name in (('x', 'transformedX'), ('y', 'transformedY'), ('z', 'transformedZ')):
            if axis in axes:
                if axis in ('x', 'y'):
                    expression = '(VIEW_PROJECTIONS_476D0[view].extent' + axis.upper() + ' + 5.0f) * ' + name + ' * reciprocalW'
                else:
                    expression = name + ' * reciprocalW * (f32)VIEW_PROJECTIONS_476D0[view].viewport[D_800BE9C0].vp.vscale[2]'
                body = body.replace('    f32 transformedX;', '    f32 product' + axis.upper() + ';\n    f32 transformedX;', 1).replace(
                    '    *out' + axis.upper() + ' = ', '    product' + axis.upper() + ' = ' + expression + ';\n    *out' + axis.upper() + ' = ', 1)
                start = body.index('    *out' + axis.upper() + ' = ')
                body = body[:start] + body[start:].replace(expression, 'product' + axis.upper(), 1)
        yield 'inline-products-' + axes, body


def depth_forms():
    body = dict(arithmetic_forms())['inline-x-origin-first']
    trans = '(f32)VIEW_PROJECTIONS_476D0[view].viewport[D_800BE9C0].vp.vtrans[2]'
    scale = '(f32)VIEW_PROJECTIONS_476D0[view].viewport[D_800BE9C0].vp.vscale[2]'
    for label, product in (('point-first', 'transformedZ * reciprocalW * ' + scale),
            ('scale-first', scale + ' * (transformedZ * reciprocalW)')):
        for order, expression in (('product-first', product + ' + ' + trans),
                ('translation-first', trans + ' + ' + product)):
            start = body.index('    *outZ = ')
            yield label + '-' + order, body[:start] + '    *outZ = (' + expression + ') * 32.0f;\n}'


SELECTED = dict(depth_forms())['point-first-product-first']
RAW_SHA256 = 'ef6971669356f325c5497d507a7548892a62e395a02e89082c9808d72478ec29'
RELOCATIONS = {0x54:[('R_MIPS_26', 'func_150A7A00')]}
for hi, lo, name in ((0x1C, 0x20, 'D_800D9D10'), (0x74, 0x7C, 'D_800BE628'), (0x9C, 0x104, 'D_800BE9C0')):
    RELOCATIONS[hi] = [('R_MIPS_HI16', name)]
    RELOCATIONS[lo] = [('R_MIPS_LO16', name)]


def checked_object(obj):
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {a - f['value']:r for a, r in relocations.items() if f['value'] <= a < f['value'] + f['size']}
    pools = {n:d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if len(raw) != 348 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Unknown direct point-projection object/bindings/pools')
    return list(struct.unpack('>87I', raw)), bindings


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified', SELECTED)
    checked_object(obj)
    before = (out / 'before-frustum_owner').read_text()
    old, diag = build.compile_owner(root, out, before, 'neighbor-before')
    a, b = parse_object(old), parse_object(obj)
    if diag or row['diagnostics'] or set(a[1]) != set(b[1]):
        raise ValueError('Changed point-projection diagnostics/function set')
    rel = lambda p, f:{at - f['value']:r for at, r in p[2].items() if f['value'] <= at < f['value'] + f['size']}
    for name, f in a[1].items():
        if name == FUNCTION:
            continue
        g = b[1][name]
        if a[0][f['value']:f['value'] + f['size']] != b[0][g['value']:g['value'] + g['size']] or rel(a, f) != rel(b, g):
            raise ValueError('Changed point-projection owner neighbor: ' + name)
    alternate, diag = previous.previous.compile_owner(root, out, recovered_owner(before), 'qualified-nounroll', True)
    if diag:
        raise ValueError('Changed point-projection no-unroll diagnostics')
    previous.previous.checked_object(alternate)
    assembly = out / 'qualified-padded.s'
    assembly.write_text(pad_c_object.emit_padded_assembly(obj, root / PATHS['layout'], OWNER,
        word_patches_path=out / 'before-guards', function_objects={previous.previous.FUNCTION:alternate}))
    padded = assembly.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(assembly)], capture_output=True, check=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    truth = (out / 'before-retail_rom').read_bytes()
    if f['size'] != 348 or data[f['value']:f['value'] + 348] != truth[ROM:ROM + 348]:
        raise ValueError('Direct point-projection slot differs')
    row.update(byte_exact=True, new_guards=0, unchanged_neighbors=len(a[1]) - 1)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def expected_inputs(root, out):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before = (out / 'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Changed point-projection predecessor image')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown point-projection predecessor extent')
    data = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 348)
    data[at:at + 348] = (out / 'before-retail_rom').read_bytes()[ROM:ROM + 348]
    struct.pack_into('>I', data, row[0] + 8, 348)
    return dict(elf=bytes(data), frustum_owner=recovered_owner((out / 'before-frustum_owner').read_text()).encode())


def prelink_prediction(root, out):
    _, padded, _, _ = qualify(root, out)
    live = lambda:{k:hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()}
    capture = out / 'link-inputs.json'
    if not capture.exists():
        if live() != BASELINE:
            raise ValueError('Point-projection capture must precede installation')
        for name, path in (('before-linkscript', 'conker/build/conker.ld'), ('before-owner.o', 'conker/build/src/' + OWNER + '.c.o')):
            (out / name).write_bytes((root / path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out / n).read_bytes()).hexdigest()
            for n in ('before-linkscript', 'before-owner.o')}, indent=2) + '\n')
    for name, digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed point-projection link capture')
    link = (out / 'before-linkscript').read_text()
    needle = 'build/src/' + OWNER + '.c.o(.text);'
    if link.count(needle) != 1:
        raise ValueError('Unknown point-projection link selector')
    for label, obj in (('baseline', out / 'before-owner.o'), ('prediction', padded)):
        script = out / (label + '.ld')
        script.write_text(link.replace(needle, str(obj.relative_to(root / 'conker')) + '(.text);', 1))
        subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-' + label + '.elf')).relative_to(root / 'conker'))],
            cwd=root / 'conker', capture_output=True, check=True)
    if (out / 'prelink-baseline.elf').read_bytes() != (out / 'before-elf').read_bytes():
        raise ValueError('Point-projection predecessor not reproduced')
    expected = expected_inputs(root, out)
    actual = (out / 'prelink-prediction.elf').read_bytes()
    if actual != expected['elf']:
        raise ValueError('Point-projection link differs outside slot/extent prediction')
    hashes = {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}
    initial = out / 'initial-prediction.json'
    if not initial.exists():
        if live() != BASELINE:
            raise ValueError('Point-projection prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2) + '\n')
    if json.loads(initial.read_text()) != hashes:
        raise ValueError('Changed first point-projection prediction')
    row = dict(after=hashes, changed_ELF_bytes=sum(a != b for a, b in zip((out / 'before-elf').read_bytes(), actual)),
        body_bytes=348, new_guards=0, metadata_exclusions=0)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def installation_patch(root, out):
    expected = expected_inputs(root, out)
    if json.loads((out / 'initial-prediction.json').read_text()) != {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}:
        raise ValueError('Changed point-projection installation prediction')
    path = root / PATHS['frustum_owner']
    before, after = path.read_bytes(), expected['frustum_owner']
    if hashlib.sha256(before).hexdigest() != BASELINE['frustum_owner']:
        raise ValueError('Changed point-projection live source before installation')
    diff = list(difflib.unified_diff(before.decode().splitlines(), after.decode().splitlines(), n=3, lineterm=''))
    return '*** Begin Patch\n*** Update File: ' + str(path) + '\n' + '\n'.join(
        '@@' if line.startswith('@@') else line for line in diff[2:]) + '\n*** End Patch\n'


def measure(root, out, label='selected', body=None, flags=('-O2', '-g3')):
    freeze(root, out)
    content = recovered_owner((out / 'before-frustum_owner').read_text(), body)
    obj, diagnostics = build.compile_owner(root, out, content, label, flags)
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    data, placed = build.link_owner(root, out, obj, OWNER)
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>87I', (out / 'before-retail_rom').read_bytes(), ROM))
    padded = words + [0] * max(0, WORDS - len(words))
    row = dict(label=label, words=len(words), frame=(-words[0]) & 65535, diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(padded, truth)) + max(0, len(words) - WORDS),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        bindings={a - f['value']:r for a, r in relocations.items() if f['value'] <= a < f['value'] + f['size']},
        pools={n:d.hex() for n, (_, d) in sections(obj).items()
            if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d},
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b)
            for i, (a, b) in enumerate(zip(padded, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens', action='store_true')
    parser.add_argument('--lifetimes', action='store_true')
    parser.add_argument('--arithmetic', action='store_true')
    parser.add_argument('--depth', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    parser.add_argument('--prelink', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[3]), flush=True)
        raise SystemExit(0)
    if args.prelink:
        print(json.dumps(prelink_prediction(root, root / BUILD), indent=2), flush=True)
        raise SystemExit(0)
    if args.prepare:
        print(installation_patch(root, root / BUILD), end='')
        raise SystemExit(0)
    for label, body in (depth_forms() if args.depth else arithmetic_forms() if args.arithmetic else lifetime_forms() if args.lifetimes else forms() if args.screens else [('selected', SELECTED)]):
        row = measure(root, root / BUILD, label, body)[2]
        print(json.dumps({k:row[k] for k in ('label', 'words', 'frame', 'differences', 'diagnostics', 'raw_sha256', 'pools')}), flush=True)
