"""Recover projected packet drawing without importing the donor's shifted ABI."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_four_byte_saturation as previous
from tools.tests import four_byte_saturation_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD = 'conker/build/game-projected-packet-draw'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_C1D70', 'func_15095760', 0x15095760, 0xC2C10, 84
PROJECT, DRAW = 0x1509563C, 0x15095A90
FRAME_INDEX, VIEW_BASE, VIEW_INDEX = 0x80082FA4, 0x800BE628, 0x800BE9C0
PATHS = dict(previous.PATHS,
    projected_packet_archive='../Another Source/CBFD-Recompiled/conker/conker/src/game/game_C1D70.c',
    projected_caller_58F80='conker/asm/58F80.s',
    projected_caller_167C58='conker/asm/nonmatchings/game_1944C0/func_15167C58.s',
    projected_caller_168118='conker/asm/nonmatchings/game_1944C0/func_15168118.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    projected_packet_archive='2d1b9733a8a1cb8d082ce0c2475c19ef0c62ef2473df070c57433b1478e2a4b5',
    projected_caller_58F80='fa4472b7643a9b3ae837eea6d1220122c59f05b34e50d6df608bab0bffc96884',
    projected_caller_167C58='e6381bda9cda2cc176836c1c1d5eca3f236d4687beeeadebf90809c89b6c3168',
    projected_caller_168118='8f22dc37f33749ac2eadf33dc6a6e2f3d07a90cbf3dddf157d6b36b597d665a1')
build = previous.build
DECLARATIONS = '''extern s32 D_80082FA4;
extern u8 *D_800BE628;
extern u8 D_800BE9C0;
extern f32 D_800D2CA8[][4][4];
extern f32 D_800D9B20;
void func_150A7A00(f32 matrix[4][4], f32 x, f32 y, f32 z,
                   f32 *outX, f32 *outY, f32 *outZ, f32 *outW);
s32 func_1509563C(f32 x, f32 y, f32 z, f32 *screenX, f32 *screenY,
                   f32 *depth, f32 *divisor, f32 maximum);

'''
VIEW = '''typedef struct {
    u8 prefix[0xC];
    f32 scaleX, scaleY;
    u8 padding14[0x20];
    f32 translateX, translateY;
    u8 padding3C[4];
    Vp viewports[20];
} ProjectedViewFrame95760;

'''
PROJECTED = '''/* Clip transformed coordinates, then map both outputs before either store. */
s32 func_1509563C(f32 x, f32 y, f32 z, f32 *screenX, f32 *screenY,
                   f32 *depth, f32 *divisor, f32 maximum) {
    f32 transformedW;
    f32 inverse;
    f32 valueX;
    f32 valueY;
    ProjectedViewFrame95760 *view;

    func_150A7A00(D_800D2CA8[D_80082FA4], x, y, z, screenX, screenY, depth, divisor);
    transformedW = *divisor;
    if (maximum <= transformedW || transformedW <= D_800D9B20) {
        return 0;
    }
    inverse = 1.0f / transformedW;
    view = (ProjectedViewFrame95760 *)D_800BE628 + D_80082FA4;
    valueX = (view->scaleX + 5.0f) * *screenX;
    valueY = (view->scaleY + 5.0f) * *screenY;
    valueX = valueX * inverse + view->translateX;
    valueY = view->translateY - valueY * inverse;
    *screenX = valueX;
    *screenY = valueY;
    return 1;
}
'''
INITIAL = '''/* Project a signed coordinate packet, set depth, then draw its screen-space form. */
Gfx *func_15095760(Gfx *output, s16 *packet) {
    f32 screenX;
    f32 screenY;
    f32 depth;
    f32 divisor;
    Vp *viewport;
    Gfx *command;

    if (func_1509563C(packet[0], packet[1], packet[2],
                      &screenX, &screenY, &depth, &divisor, 4000.0f) == 0) {
        return output;
    }
    gDPPipeSync(output++);
    command = output++;
    command->words.w0 = 0xEE000000;
    viewport = (Vp *)(D_800BE628 + D_80082FA4 * 0x180 + D_800BE9C0 * 0x10 + 0x40);
    command->words.w1 = (u32)(s32)((viewport->vp.vtrans[2] +
        (depth / divisor) * viewport->vp.vscale[2]) * 32.0f) << 16;
    return (Gfx *)func_15095A90((s32)output, (s32)packet, screenX, screenY, divisor, 1, 0, 0, 0);
}
'''
SELECTED = INITIAL


def freeze(root, out):
    with patch.multiple(previous, PATHS=PATHS, BASELINE=BASELINE):
        previous.freeze(root, out)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15095760() {\n    return 0;\n}':
        raise ValueError('Unknown projected-packet predecessor')
    marker = '#include <ultra64.h>\n'
    if before.count(marker) != 1:
        raise ValueError('Unknown projected-packet declaration anchor')
    result = before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]
    return result.replace(marker, marker+DECLARATIONS+VIEW, 1).replace(
        's32 func_1509563C() {\n    return 0;\n}', SELECTED_PROJECTOR.rstrip()).replace(
        'typedef struct { u8 prefix[0x40]; Vp viewports[20]; } ProjectedViewFrame95760;\n\n', '')


def forms():
    yield 'initial', INITIAL
    byte_view = INITIAL.replace('    Vp *viewport;', '    u8 *viewport;').replace(
        'viewport = (Vp *)', 'viewport = ').replace(
        'viewport->vp.vtrans[2]', '*(s16 *)(viewport+12)').replace('viewport->vp.vscale[2]', '*(s16 *)(viewport+4)')
    yield 'word-view', byte_view
    offset_view = byte_view.replace(' + 0x40);', ');').replace('(viewport+12)', '(viewport+0x4C)').replace('(viewport+4)', '(viewport+0x44)')
    yield 'byte-offset-view', offset_view
    manual = offset_view.replace('    gDPPipeSync(output++);',
        '    command = output++;\n    command->words.w0 = 0xE7000000;\n    command->words.w1 = 0;')
    yield 'shared-command-pointer', manual
    yield 'shared-pointer-quotient-first', manual.replace('*(s16 *)(viewport+0x4C) +\n        (depth / divisor) * *(s16 *)(viewport+0x44)',
        '(depth / divisor) * *(s16 *)(viewport+0x44) + *(s16 *)(viewport+0x4C)')
    distinct = manual.replace('    Gfx *command;', '    Gfx *syncCommand;\n    Gfx *command;').replace(
        '    command = output++;\n    command->words.w0 = 0xE7000000;\n    command->words.w1 = 0;',
        '    syncCommand = output++;\n    syncCommand->words.w0 = 0xE7000000;\n    syncCommand->words.w1 = 0;')
    yield 'distinct-command-pointers', distinct
    yield 'distinct-quotient-first', distinct.replace('*(s16 *)(viewport+0x4C) +\n        (depth / divisor) * *(s16 *)(viewport+0x44)',
        '(depth / divisor) * *(s16 *)(viewport+0x44) + *(s16 *)(viewport+0x4C)')
    for name, base in (('macro', offset_view), ('shared', manual), ('distinct', distinct)):
        inline = base.replace('    u8 *viewport;\n', '').replace(
            '    viewport = (D_800BE628 + D_80082FA4 * 0x180 + D_800BE9C0 * 0x10);\n', '')
        if name == 'macro':
            quotient_first = inline.replace('*(s16 *)(viewport+0x4C) +\n        (depth / divisor) * *(s16 *)(viewport+0x44)',
                '(depth / divisor) * *(s16 *)(viewport+0x44) + *(s16 *)(viewport+0x4C)')
            yield 'macro-inline-quotient-first', quotient_first.replace('viewport+0x4C',
                'D_800BE628 + D_80082FA4 * 0x180 + D_800BE9C0 * 0x10 + 0x4C').replace('viewport+0x44',
                'D_800BE628 + D_80082FA4 * 0x180 + D_800BE9C0 * 0x10 + 0x44')
            typed = quotient_first.replace('*(s16 *)(viewport+0x4C)',
                '((ProjectedViewFrame95760 *)D_800BE628)[D_80082FA4].viewports[D_800BE9C0].vp.vtrans[2]').replace(
                '*(s16 *)(viewport+0x44)',
                '((ProjectedViewFrame95760 *)D_800BE628)[D_80082FA4].viewports[D_800BE9C0].vp.vscale[2]')
            typed = 'typedef struct { u8 prefix[0x40]; Vp viewports[20]; } ProjectedViewFrame95760;\n\n'+typed
            yield 'typed-frame-view', typed
            sdk = typed.replace('    Gfx *command;\n', '').replace(
                '    command = output++;\n    command->words.w0 = 0xEE000000;\n    command->words.w1 = (u32)(s32)(',
                '    gDPSetPrimDepth(output++, (s32)(').replace(' * 32.0f) << 16;', ' * 32.0f), 0);')
            yield 'typed-frame-sdk-depth', sdk
            for label, body in (('typed-frame-view', typed), ('typed-frame-sdk-depth', sdk)):
                yield label+'-assigned-return', body.replace('    return (Gfx *)func_15095A90',
                    '    output = (Gfx *)func_15095A90').replace('divisor, 1, 0, 0, 0);\n}',
                    'divisor, 1, 0, 0, 0);\n    return output;\n}')
        inline = inline.replace('viewport+0x4C', 'D_800BE628 + D_80082FA4 * 0x180 + D_800BE9C0 * 0x10 + 0x4C').replace(
            'viewport+0x44', 'D_800BE628 + D_80082FA4 * 0x180 + D_800BE9C0 * 0x10 + 0x44')
        yield name+'-inline-viewport', inline
        yield name+'-packet-byte-view', base.replace('Gfx *output, s16 *packet', 'Gfx *output, u8 *packet').replace(
            'packet[0], packet[1], packet[2]', '*(s16 *)(packet+0), *(s16 *)(packet+2), *(s16 *)(packet+4)')
    yield 'late-output-increment', INITIAL.replace('    command = output++;', '    command = output;').replace(
        '    return (Gfx *)func_15095A90', '    output++;\n    return (Gfx *)func_15095A90')


def measure(root, out, label='selected', selected=None):
    freeze(root, out)
    obj, diag = build.compile_owner(root, out, recovered_owner((out / 'before-packet_owner').read_text(), selected), label)
    text, funcs, rel = parse_object(obj)
    f = funcs[FUNCTION]
    data, functions = build.link_owner(root, out, obj, OWNER)
    linked = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (linked['size']//4), data, linked['value']))
    truth = list(struct.unpack_from('>84I', (out / 'before-retail_rom').read_bytes(), ROM))
    row = dict(label=label, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth))+abs(len(words)-WORDS), diagnostics=diag,
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']: v for a, v in rel.items() if f['value'] <= a < f['value']+f['size']},
        pools={n: d.hex() for n, (_, d) in sections(obj).items()
            if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d},
        different_words=[(i*4, '0x%08X'%a, '0x%08X'%b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label+'.json')).write_text(json.dumps(row, indent=2)+'\n')
    return obj, words, row


SELECTED = dict(forms())['typed-frame-sdk-depth']


def projector_forms():
    yield 'staged', PROJECTED
    direct = PROJECTED.replace('    f32 valueX;\n    f32 valueY;\n', '').replace(
        '    valueX = (view->scaleX + 5.0f) * *screenX;\n    valueY = (view->scaleY + 5.0f) * *screenY;\n'
        '    valueX = valueX * inverse + view->translateX;\n    valueY = view->translateY - valueY * inverse;\n'
        '    *screenX = valueX;\n    *screenY = valueY;',
        '    *screenX = (view->scaleX + 5.0f) * *screenX * inverse + view->translateX;\n'
        '    *screenY = view->translateY - (view->scaleY + 5.0f) * *screenY * inverse;')
    yield 'direct-stores', direct
    staged_inputs = PROJECTED.replace('    valueX = (view->scaleX + 5.0f) * *screenX;\n    valueY = (view->scaleY + 5.0f) * *screenY;',
        '    valueX = *screenX;\n    valueY = *screenY;\n    valueX = (view->scaleX + 5.0f) * valueX;\n'
        '    valueY = (view->scaleY + 5.0f) * valueY;')
    yield 'staged-inputs', staged_inputs
    expressions = PROJECTED.replace(
        '    valueX = (view->scaleX + 5.0f) * *screenX;\n    valueY = (view->scaleY + 5.0f) * *screenY;\n'
        '    valueX = valueX * inverse + view->translateX;\n    valueY = view->translateY - valueY * inverse;',
        '    valueX = (view->scaleX + 5.0f) * *screenX * inverse + view->translateX;\n'
        '    valueY = view->translateY - (view->scaleY + 5.0f) * *screenY * inverse;')
    yield 'staged-expressions', expressions
    inputs_expressions = expressions.replace('    valueX = (view->scaleX + 5.0f) * *screenX * inverse + view->translateX;\n'
        '    valueY = view->translateY - (view->scaleY + 5.0f) * *screenY * inverse;',
        '    valueX = *screenX;\n    valueY = *screenY;\n'
        '    valueX = (view->scaleX + 5.0f) * valueX * inverse + view->translateX;\n'
        '    valueY = view->translateY - (view->scaleY + 5.0f) * valueY * inverse;')
    yield 'inputs-expressions', inputs_expressions
    split = staged_inputs.replace('    valueX = valueX * inverse + view->translateX;',
        '    valueX = valueX * inverse;\n    valueX = valueX + view->translateX;').replace(
        '    valueY = view->translateY - valueY * inverse;',
        '    valueY = valueY * inverse;\n    valueY = view->translateY - valueY;')
    yield 'split-outputs', split
    scaled = inputs_expressions.replace('    f32 valueX;', '    f32 scaleX;\n    f32 scaleY;\n    f32 valueX;').replace(
        '    valueX = (view->scaleX + 5.0f) * valueX * inverse + view->translateX;\n'
        '    valueY = view->translateY - (view->scaleY + 5.0f) * valueY * inverse;',
        '    scaleX = view->scaleX + 5.0f;\n    scaleY = view->scaleY + 5.0f;\n'
        '    valueX = scaleX * valueX * inverse + view->translateX;\n'
        '    valueY = view->translateY - scaleY * valueY * inverse;')
    yield 'captured-scales', scaled
    yield 'captured-scales-split', scaled.replace('    valueX = scaleX * valueX * inverse + view->translateX;',
        '    valueX = scaleX * valueX;\n    valueX = valueX * inverse;\n    valueX = valueX + view->translateX;').replace(
        '    valueY = view->translateY - scaleY * valueY * inverse;',
        '    valueY = scaleY * valueY;\n    valueY = valueY * inverse;\n    valueY = view->translateY - valueY;')
    for label, body in (('staged', PROJECTED), ('expressions', expressions), ('inputs', inputs_expressions)):
        yield label+'-reused-reciprocal', body.replace('    f32 inverse;\n', '').replace(
            '    inverse = 1.0f / transformedW;', '    transformedW = 1.0f / transformedW;').replace(' * inverse', ' * transformedW')
        yield label+'-float-view', body.replace('    ProjectedViewFrame95760 *view;', '    f32 *view;').replace(
            'view = (ProjectedViewFrame95760 *)D_800BE628 + D_80082FA4;',
            'view = (f32 *)(D_800BE628 + D_80082FA4 * 0x180);').replace('view->scaleX', 'view[3]').replace(
            'view->scaleY', 'view[4]').replace('view->translateX', 'view[13]').replace('view->translateY', 'view[14]')
    for label, body in (('staged', PROJECTED), ('expressions', expressions)):
        yield label+'-single-result', body.replace('    f32 transformedW;', '    s32 result;\n    f32 transformedW;').replace(
            '        return 0;\n    }\n    inverse', '        result = 0;\n    } else {\n    inverse').replace(
            '    return 1;\n}', '    result = 1;\n    }\n    return result;\n}')
    for label, body in (('staged', PROJECTED), ('direct', direct), ('inputs', staged_inputs)):
        yield label+'-else', body.replace('        return 0;\n    }\n    inverse',
            '        return 0;\n    } else {\n    inverse').replace('    return 1;\n}', '    return 1;\n    }\n}')


def measure_projector(root, out, label, body):
    with patch.dict(globals(), SELECTED_PROJECTOR=body):
        obj, _, draw = measure(root, out, 'projector-'+label)
    data, funcs = build.link_owner(root, out, obj, OWNER)
    f = funcs['func_1509563C']
    words = list(struct.unpack_from('>%dI' % (f['size']//4), data, f['value']))
    truth = struct.unpack_from('>73I', (out / 'before-retail_rom').read_bytes(), 0xC2AEC)
    row = dict(label=label, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth))+abs(len(words)-73), draw_differences=draw['differences'],
        different_words=[(i*4, '0x%08X'%a, '0x%08X'%b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / ('projector-'+label+'.json')).write_text(json.dumps(row, indent=2)+'\n')
    return row


SELECTED_PROJECTOR = dict(projector_forms())['inputs-expressions']
RAW_SHA256 = 'f2976934160d9d249e48dabc657e75f68665b1e8b563b435b26f075d48ddbf06'
PROJECT_RAW_SHA256 = 'e52a1aa70930b4178660143d7bec06b0c020de5e661362546406916e2704ad25'
RELOCATIONS = {92: [('R_MIPS_26', 'func_1509563C')],
    160: [('R_MIPS_HI16', 'D_80082FA4')], 164: [('R_MIPS_LO16', 'D_80082FA4')],
    172: [('R_MIPS_HI16', 'D_800BE628')], 184: [('R_MIPS_LO16', 'D_800BE628')],
    176: [('R_MIPS_HI16', 'D_800BE9C0')], 180: [('R_MIPS_LO16', 'D_800BE9C0')],
    312: [('R_MIPS_26', 'func_15095A90')]}
PROJECT_RELOCATIONS = {16: [('R_MIPS_HI16', 'D_80082FA4')], 20: [('R_MIPS_LO16', 'D_80082FA4')],
    40: [('R_MIPS_HI16', 'D_800D2CA8')], 44: [('R_MIPS_LO16', 'D_800D2CA8')],
    80: [('R_MIPS_26', 'func_150A7A00')], 108: [('R_MIPS_HI16', 'D_800D9B20')],
    128: [('R_MIPS_LO16', 'D_800D9B20')], 184: [('R_MIPS_HI16', 'D_800BE628')],
    188: [('R_MIPS_LO16', 'D_800BE628')], 172: [('R_MIPS_HI16', 'D_80082FA4')],
    176: [('R_MIPS_LO16', 'D_80082FA4')]}
GUARDS = {0xD8: (0xC4680034, 0xC4660010), 0xE8: (0xC46A0038, 0x46103200),
    0xF0: (0xC4720010, 0xC4720034), 0xF4: (0x460C2182, 0x460C2002),
    0xF8: (0x46109100, 0xC4640038), 0xFC: (0x46083000, 0x46024282),
    0x100: (0x46022182, 0x46120000), 0x104: (0xE4800000, 0x460C5082),
    0x108: (0x460C3202, 0xE4800000), 0x10C: (0x46085081, 0x46022081)}


def proposed_guards(before):
    reader = csv.DictReader(io.StringIO(before.decode()))
    if any(r['function'] in (FUNCTION, 'func_1509563C') for r in reader):
        raise ValueError('Unexpected preexisting projection guard history')
    suffix = io.StringIO(newline='')
    writer = csv.writer(suffix, lineterminator='\n')
    for at, (expected, replacement) in GUARDS.items():
        writer.writerow((OWNER, 'func_1509563C', '0x%X'%at, '0x%08X'%expected, '0x%08X'%replacement,
            '-', '-', 'Normalize closed projection output schedule and scratch allocation', '', '', 'false'))
    if not before.endswith(b'\n'):
        raise ValueError('Projection guard predecessor has no terminal newline')
    return before+suffix.getvalue().encode()


def output_dag(words):
    """Exact expression trees retain IEEE operation order within each output."""
    f = {12: ('inverse',), 16: ('five',)}
    names, writes, result = {3: 'view', 4: 'screenX', 5: 'screenY'}, [], None
    for word in words[0xD0//4:0x114//4]:
        op, rs, rt, rd, sa, fn = word>>26, word>>21&31, word>>16&31, word>>11&31, word>>6&31, word&63
        if op == 49:
            f[rt] = ('load', names[rs], word & 65535)
        elif op == 57:
            writes.append((names[rs], word & 65535, f[rt]))
        elif op == 17 and rs == 16 and fn in (0, 1, 2):
            f[sa] = (('add', 'sub', 'mul')[fn], f[rd], f[rt])
        elif word == 0x24020001:
            result = 1
        else:
            raise ValueError('Unknown instruction in closed projection output block')
    return writes, result, f[0], f[2]


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    raw, funcs, rel = parse_object(obj)
    f = funcs[FUNCTION]
    relative = lambda f: {a-f['value']:v for a,v in rel.items() if f['value'] <= a < f['value']+f['size']}
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['raw_sha256'], relative(f), row['pools']) != (
            84, 72, 0, '', RAW_SHA256, RELOCATIONS, {}):
        raise ValueError('Unknown projected draw compiler shape, words, bindings or pools')
    pools = {n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if hashlib.sha256(raw[f['value']:f['value']+f['size']]).hexdigest() != RAW_SHA256 or pools:
        raise ValueError('Changed projected draw physical words or object pools')
    pf = funcs['func_1509563C']
    if hashlib.sha256(raw[pf['value']:pf['value']+pf['size']]).hexdigest() != PROJECT_RAW_SHA256 or relative(pf) != PROJECT_RELOCATIONS:
        raise ValueError('Unknown projection compiler words or bindings')
    data, fs = build.link_owner(root, out, obj, OWNER)
    p = fs['func_1509563C']
    projection = list(struct.unpack_from('>%dI'%(p['size']//4), data, p['value']))
    truth = list(struct.unpack_from('>73I', (out / 'before-retail_rom').read_bytes(), 0xC2AEC))
    if len(projection) != 73 or (-projection[0])&65535 != 40:
        raise ValueError('Unknown projection frame or body length')
    if {i*4:(a,b) for i,(a,b) in enumerate(zip(projection,truth)) if a != b} != GUARDS:
        raise ValueError('Unknown projection normalization sites')
    if output_dag(projection) != output_dag(truth):
        raise ValueError('Projection output normalization changes its expression trees or stores')
    guards = out / 'proposed-guards.csv'
    guards.write_bytes(proposed_guards((out / 'before-guards').read_bytes()))
    padded = out / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj, root / PATHS['packet_original'], filename=OWNER, word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded.with_suffix('.o')), str(padded)], check=True, capture_output=True)
    linked, lf = build.link_owner(root, out, padded.with_suffix('.o'), OWNER)
    for name, rom, count in ((FUNCTION, ROM, 84), ('func_1509563C', 0xC2AEC, 73)):
        start = lf[name]['value']
        if linked[start:start+count*4] != (out / 'before-retail_rom').read_bytes()[rom:rom+count*4]:
            raise ValueError('Projection pair is not linked byte exact')
    row = dict(row, projected_words=73, projected_frame=40, projected_guards=10, draw_guards=0)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2)+'\n')
    return obj, padded.with_suffix('.o'), words, projection, row


def slot_expected_image(before, rom):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown projected-pair predecessor ELF')
    result = bytearray(before)
    rows = {r[1]:r for r in symbol_rows(before)}
    for name, entry, rom_at, size in ((FUNCTION, ENTRY, ROM, 336), ('func_1509563C', PROJECT, 0xC2AEC, 292)):
        row = rows[name]
        if row[2][1:3] != (entry, 12):
            raise ValueError('Unknown projected-pair predecessor extent')
        at = elf_slot_offset(before, entry, size)
        result[at:at+size] = rom[rom_at:rom_at+size]
        struct.pack_into('>I', result, row[0]+8, size)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=slot_expected_image((out / 'before-elf').read_bytes(), (out / 'before-retail_rom').read_bytes()),
        packet_owner=recovered_owner((out / 'before-packet_owner').read_text()).encode(),
        guards=proposed_guards((out / 'before-guards').read_bytes()))


def prelink_prediction(root, out):
    _, padded, _, _, _ = qualify(root, out)
    capture = out / 'link-inputs.json'
    if not capture.exists():
        if {k: hashlib.sha256((root / p).read_bytes()).hexdigest() for k,p in PATHS.items()} != BASELINE:
            raise ValueError('Projected-pair link capture must precede installation')
        (out / 'before-linkscript').write_bytes((root / 'conker/build/conker.ld').read_bytes())
        (out / 'before-owner.o').write_bytes((root / 'conker/build/src/game' / (OWNER+'.c.o')).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out / n).read_bytes()).hexdigest()
            for n in ('before-linkscript', 'before-owner.o')}, indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed projected-pair pre-install link capture')
    link = (out / 'before-linkscript').read_text()
    needle = 'build/src/game/'+OWNER+'.c.o(.text);'
    if link.count(needle) != 1:
        raise ValueError('Expected exactly one projected-pair selector')
    for name,obj in (('baseline', out / 'before-owner.o'), ('prediction', padded)):
        script = out / (name+'.ld')
        script.write_text(link.replace(needle, str(obj.relative_to(root / 'conker'))+'(.text);', 1))
        result = subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-'+name+'.elf')).relative_to(root / 'conker'))],
            cwd=root / 'conker', capture_output=True, text=True)
        if result.returncode:
            raise ValueError(result.stderr)
    before = (out / 'before-elf').read_bytes()
    if (out / 'prelink-baseline.elf').read_bytes() != before:
        raise ValueError('Linked inputs do not reproduce the projected-pair predecessor')
    expected = expected_inputs(root, out)
    predicted = (out / 'prelink-prediction.elf').read_bytes()
    if predicted != expected['elf']:
        raise ValueError('Projected-pair link differs from complete slot/extent prediction')
    hashes = {k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial = out / 'initial-prediction.json'
    if not initial.exists():
        if {k: hashlib.sha256((root / p).read_bytes()).hexdigest() for k,p in PATHS.items()} != BASELINE:
            raise ValueError('Projected-pair prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2)+'\n')
    if json.loads(initial.read_text()) != hashes:
        raise ValueError('Changed projected-pair first prediction')
    row = dict(after=hashes, changed_ELF_bytes=sum(a!=b for a,b in zip(before,predicted)),
        metadata_exclusions=0, slot_bytes=628, draw_guards=0, projected_guards=10)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2)+'\n')
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--screens', action='store_true')
    parser.add_argument('--projector-screens', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    parser.add_argument('--prelink', action='store_true')
    args = parser.parse_args()
    if args.prelink:
        print(json.dumps(prelink_prediction(args.root, args.root / BUILD), indent=2))
        return
    if args.qualify:
        print(json.dumps(qualify(args.root, args.root / BUILD)[-1], indent=2))
        return
    if args.projector_screens:
        for name, body in projector_forms():
            print(json.dumps(measure_projector(args.root, args.root / BUILD, name, body)), flush=True)
        return
    for name, body in forms() if args.screens else (('selected', SELECTED),):
        row = measure(args.root, args.root / BUILD, name, body)[2]
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
