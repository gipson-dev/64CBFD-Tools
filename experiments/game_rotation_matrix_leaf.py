"""Qualify retail rotation layout before choosing C or original assembly."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_actor_world_matrix as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import actor_world_matrix_checkpoint as checkpoint
from tools.experiments.alternative_source_function_isolation import compile_one
from tools import pad_c_object

BUILD = 'conker/build/game-rotation-matrix-leaf'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'game_D5500', 'func_150A8050', 0x150A8050, 0xD5500, 84
PATHS = dict(previous.PATHS,
    sdk_rotation='tools/ultralib/src/gu/rotaterpy.c',
    archive_rotation='../Another Source/CBFD-Recompiled/conker/conker/src/game_D5500.c',
    math_owner='conker/src/game/generated_DAC30.c', math_original='conker/asm/DAC30.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    sdk_rotation='dbf636b3df54049b63f3fd365915d05aaec8b5d0c2a9870e4170ccbdd957b6e8',
    archive_rotation='e17cd6462cefe6063a339fcdebd1f25084ac364c7efd42ab39bda6c52ea2cb50',
    math_owner='e831af23ec9a00c80f5500d0d23f3c525140ca1a965fe98332b09085c28d82ee',
    math_original='e87dccfd5380ec9dd31b4dfe07176cf3745f0a86f2b748ed4896e531bb41f851')
SEMANTIC_C = '''void func_150A8050(f32 matrix[4][4], f32 roll, f32 pitch, f32 heading) {
    f32 factor = D_8009F6C0;
    f32 cosR, sinR, cosP, sinP, cosH, sinH;

    roll *= factor;
    cosR = func_150AD780(roll);
    sinR = func_150AD78C(roll);
    pitch *= factor;
    cosP = func_150AD780(pitch);
    sinP = func_150AD78C(pitch);
    heading *= factor;
    cosH = func_150AD780(heading);
    sinH = func_150AD78C(heading);

    matrix[0][0] = cosP * cosH;
    matrix[0][2] = -sinP;
    matrix[0][3] = 0.0f;
    matrix[1][3] = 0.0f;
    matrix[2][3] = 0.0f;
    matrix[0][1] = cosP * sinH;
    matrix[1][0] = (sinR * sinP) * cosH - cosR * sinH;
    matrix[1][1] = (sinR * sinP) * sinH + cosR * cosH;
    matrix[3][0] = 0.0f;
    matrix[3][1] = 0.0f;
    matrix[3][2] = 0.0f;
    matrix[1][2] = sinR * cosP;
    matrix[2][0] = (cosR * sinP) * cosH + sinR * sinH;
    matrix[2][1] = (cosR * sinP) * sinH - sinR * cosH;
    matrix[2][2] = cosR * cosP;
    matrix[3][3] = 1.0f;
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed rotation-leaf baseline')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified rotation-leaf manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable rotation-leaf input: ' + key)


def c_owner(before, body=SEMANTIC_C):
    lo, hi = build.function_span(before, FUNCTION)
    return before[:lo] + body.rstrip() + before[hi:]


def original_owner(before):
    if build.body(before, FUNCTION) != 'void func_150A8050(f32 mtx[4][4], f32 arg1, f32 arg2, f32 arg3) {\n}':
        raise ValueError('Unexpected empty rotation placeholder')
    return '''#include <ultra64.h>
#include "functions.h"
#include "variables.h"

/* Original rotation kernel: split frame release and six even FP saves. */
#pragma GLOBAL_ASM("asm/nonmatchings/game_D5500/func_150A8050.s")
'''


def restored_progress(before):
    if hashlib.sha256(before).hexdigest() != BASELINE['progress']:
        raise ValueError('Unknown rotation progress predecessor')
    rows = list(csv.reader(io.StringIO(before.decode())))
    stream = io.StringIO()
    csv.writer(stream, lineterminator='\n').writerows(rows)
    if stream.getvalue().encode() != before:
        raise ValueError('Rotation progress round trip changes unrelated bytes')
    selected = [row for row in rows if row[3] == FUNCTION]
    if selected != [['us', 'game', OWNER, FUNCTION, str(ENTRY), '336', 'c']]:
        raise ValueError('Unexpected rotation progress row')
    selected[0][-1] = 'asm'
    stream = io.StringIO()
    csv.writer(stream, lineterminator='\n').writerows(rows)
    return stream.getvalue().encode()


def measure(root, out, label, text, flags=('-O2', '-g3')):
    freeze(root, out)
    if tuple(flags) == ('-O1', '-g3'):
        if 'GLOBAL_ASM' in text:
            raise ValueError('Isolated O1/g3 screen requires pure C')
        path = out / (label + '-input.c')
        path.write_text(text)
        item = dict(path=str(path.relative_to(root / 'conker')),
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), function=FUNCTION,
            compiler_flags=list(flags), c_only=True)
        result = compile_one(root, root / 'conker', out, item)
        if result['status'] != 'object_compiled':
            raise ValueError('Isolated rotation screen failed: ' + repr(result))
        obj, diagnostics = Path(result['object']), Path(result['diagnostics_file']).read_text()
    else:
        obj, diagnostics = build.compile_owner(root, out, text, label, flags)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>84I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    complete = words + [0] if len(words) == 83 and truth[-1] == 0 else words
    row = dict(label=label, body_words=len(words), slot_words=len(complete), flags=flags,
        differences=sum(a != b for a, b in zip(complete, truth)) + abs(len(complete) - WORDS),
        diagnostics=diagnostics, sp_adjustments=[(i * 4, (word & 65535) - (65536 if word & 32768 else 0))
            for i, word in enumerate(words) if word >> 16 == 0x27BD])
    return obj, complete, row


def qualify(root, out):
    freeze(root, out)
    obj, words, row = measure(root, out, 'qualified',
        original_owner((out / 'before-angles_owner').read_text()))
    if (row['body_words'], row['slot_words'], row['differences'], row['diagnostics']) != (84, 84, 0, ''):
        raise ValueError('Original rotation slot is not exact: ' + repr(row))
    if row['sp_adjustments'] != [(4, -48), (144, 16), (320, 32)]:
        raise ValueError('Original rotation split frame changed')
    assembly = pad_c_object.emit_padded_assembly(obj, root / PATHS['layout'], OWNER,
        word_patches_path=root / PATHS['guards'])
    path = out / 'qualified-padded.s'
    path.write_text('.include "' + str(root / 'conker/include/asm_processor_prelude.inc') + '"\n' + assembly)
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], capture_output=True, check=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 336 or list(struct.unpack_from('>84I', data, f['value'])) != words:
        raise ValueError('Rotation production padder differs')
    row.update(instruction_words=83, alignment_nops=1, guards_added=0, original_assembly_not_C=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    before = (out / 'before-angles_owner').read_text()
    rows = []
    for label, flags in (('o2g3', ('-O2', '-g3')), ('o2', ('-O2',)), ('o1g3', ('-O1', '-g3')), ('o1', ('-O1',))):
        _, _, row = measure(root, out, label, c_owner(before), flags)
        rows.append(row)
        print(json.dumps(row), flush=True)
    _, _, row = measure(root, out, 'original', original_owner(before))
    rows.append(row)
    print(json.dumps(row), flush=True)
    (out / 'screens.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
