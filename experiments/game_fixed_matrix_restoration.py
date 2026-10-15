"""Audit and restore the distinct unrolled, rounding-mode-aware matrix converter."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-fixed-matrix-restoration'
FUNCTION, ENTRY, ROM, WORDS = 'guMtxF2L', 0x150A7790, 0xD4C40, 116
ASSEMBLY = 'conker/asm/nonmatchings/libultra/gu/guMtxF2L/guMtxF2L.s'
PATHS = {
    'elf': 'conker/build/conker.us.elf', 'owner': 'conker/src/libultra/gu/guMtxF2L.c',
    'assembly': ASSEMBLY, 'progress': 'conker/progress.csv',
    'guards': 'conker/retail_word_patches.us.csv', 'layout': 'conker/retail_layout.us.txt',
    'makefile': 'conker/Makefile', 'functions': 'conker/include/functions.h',
    'variables': 'conker/include/variables.h', 'structs': 'conker/include/structs.h',
    'matrix2': 'conker/src/libultra/gu/mtxutil2.c', 'perspective': 'conker/src/libultra/gu/guPerspectiveF.c',
    'identity': 'conker/src/libultra/gu/guMtxIdentF.c', 'family': 'conker/src/game/generated_138520.c',
    'caller': 'conker/src/game_476D0.c', 'sdk_c': 'tools/ultralib/src/gu/mtxutil.c',
    'sdk_asm': 'tools/ultralib/src/mgu/mtxf2l.s',
}
BASELINE = {
    'elf': '03db1e761d60ffc85ded9fb702ea53720b7c1bdeec97cbf00f34eae3dc7677d7',
    'owner': '8dc30adad86698603269a11b22d46df6db940aa95048edecd0cd071470397c54',
    'assembly': 'b494f6f37fa311958af522917925a835292b2e6566c7f33749b2313a45c12f18',
    'progress': '005fd7682d37802a2b7591cfb023648b6a083c8df6b957bdfedd737222cad68e',
    'guards': 'b83e74a2f547c1274f9763a6afea8aa82781e338949247cea91eb63d36fc984a',
    'layout': 'a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5',
    'makefile': '838070597f76ea2f7182c158dfb6710946cfcabcb5435e994f93cdb99340e313',
    'functions': '2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81',
    'variables': '1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8',
    'structs': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'matrix2': '45ad70401c273ef3d4ddf922da65e09ec1a1da82d93d4f0fb352a06d82597fc3',
    'perspective': '387df8e02b81f8b86a10061d63dcf5b3d382ddf81c7396657409da844dcbb70f',
    'identity': '7e8b932a1e97e84c946a008bf45dd222fa3b147987c2beeae1541e8afc104b14',
    'family': '02bdc24e7b996e207b664045d0ed1107cf2d8eb752b0a8f5eff90fe59e3a3f0b',
    'caller': 'eb3b52178dea347045168a4d261d95b830cad348dae3afa7f298500eed4dfc0c',
    'sdk_c': 'ab15f09787860e8cc129f8949158bbf041c7a21ffc71a747ed4a3122204a15ba',
    'sdk_asm': 'ccfba75654f548b1cbb7941e8c34e7de7bcb6b328f1b6c81f8684d6fca3216a1',
}
SOURCE = '''#include <ultra64.h>
#include "functions.h"
#include "variables.h"

/* Original unrolled converter: cvt.w.s follows the current FCSR rounding mode. */
#pragma GLOBAL_ASM("asm/nonmatchings/libultra/gu/guMtxF2L/guMtxF2L.s")
'''
ASM_COMMENT = '/* Convert paired floats using current FCSR rounding; write fractional then integer halves. */\n'


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        values = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in values.items()} != BASELINE:
            raise ValueError('Changed fixed-matrix baseline')
        for key, value in values.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified fixed-matrix manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable fixed-matrix input: ' + key)


def expected_progress(before):
    old = ['us', 'game', 'guMtxF2L', 'guMtxF2L', '353007504', '464', 'c']
    lines = before.splitlines(keepends=True)
    reader = csv.reader(io.StringIO(before.decode(), newline=''))
    chunks, cursor, changed = [], 0, 0
    for row in reader:
        end = reader.line_num
        record = b''.join(lines[cursor:end])
        if row[:4] == old[:4]:
            if row != old:
                raise ValueError('Unexpected fixed-matrix progress row')
            ending = '\r\n' if record.endswith(b'\r\n') else '\n' if record.endswith(b'\n') else ''
            output = io.StringIO(newline='')
            csv.writer(output, lineterminator=ending).writerow(row[:-1] + ['asm'])
            record, changed = output.getvalue().encode(), changed + 1
        chunks.append(record)
        cursor = end
    if changed != 1 or cursor != len(lines):
        raise ValueError('Unexpected fixed-matrix progress row')
    return b''.join(chunks)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    old, diagnostics = build.compile_owner(root, out, (out / 'before-owner').read_text(), 'old-C')
    raw, functions, relocations = parse_object(old)
    info = functions[FUNCTION]
    old_bytes = raw[info['value']:info['value'] + info['size']]
    rom = (root / 'conker/conker.us.bin').read_bytes()
    retail = rom[ROM:ROM + WORDS * 4]
    second = rom[0x21D1B0:0x21D2B0]
    assert old_bytes == second and not relocations and diagnostics == ''
    restored, diagnostics = build.compile_owner(root, out, SOURCE, 'restored')
    raw, functions, relocations = parse_object(restored)
    info = functions[FUNCTION]
    code = raw[info['value']:info['value'] + WORDS * 4]
    assert code == retail and not relocations and diagnostics == ''
    report = dict(old_C_bytes=len(old_bytes), old_C_exact_other_function_words=64,
        restored_slot_words=WORDS, processed_function_extent=info['size'], guards=0,
        relocation_count=0, original_CVT_words=sum((word[0] & 0xFFE0003F) == 0x46000024 for word in struct.iter_unpack('>I', retail)),
        original_slot_SHA256=hashlib.sha256(retail).hexdigest(),
        ownership_correction_not_new_C_match=True, historical_authorship_not_inferred_from_old_GLOBAL_ASM=True)
    (out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
