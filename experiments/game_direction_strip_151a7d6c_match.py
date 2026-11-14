"""Pinned stack/register/scheduling normalization for the strip renderer.

This module proposes guards in the private build directory. It never installs
source or alters the production guard manifest.
"""
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import struct
import subprocess

from tools.experiments import game_direction_strip_151a7d6c_candidates as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pad

RAW_SHA256 = '2dbcf5d06e42583aeec00dd7a6ddb273a4888f04e5555c0d5fd1605678331280'
# Disjoint source homes for cursor, vectors, camera, magnitude, sync, last,
# and the projection parameter. Saved registers and incoming homes stay fixed.
HOMES = {0xC4: 0xC0, 0xB8: 0xB4, 0xBC: 0xB8, 0xC0: 0xBC,
         0xAC: 0xA8, 0xB0: 0xAC, 0xB4: 0xB0, 0x9C: 0x8C,
         0x98: 0x88, 0x97: 0x87, 0x94: 0x84, 0x90: 0x78}
TEMPORARIES = {12: 15, 15: 12, 13: 24, 24: 13, 14: 25, 25: 14}


def registers(word, mapping):
    """Rename only GPR fields; floating register fields are never rewritten."""
    op = word >> 26
    if op == 0:
        fields = (21, 16, 11)
    elif op == 17:
        fields = (16,) if (word >> 21 & 31) in (0, 4) else ()
    elif op in (49, 53, 57, 61):
        fields = (21,)
    elif op in (2, 3):
        fields = ()
    else:
        fields = (21, 16)
    for shift in fields:
        value = word >> shift & 31
        word = (word & ~(31 << shift)) | (mapping.get(value, value) << shift)
    return word


def normalize(raw, refs, expected_refs):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or refs != expected_refs:
        raise ValueError('Strip renderer raw body or bindings changed')
    words = list(struct.unpack('>373I', raw))
    assert words[0] == 0x27BDFF38 and words[-1] == 0x27BD00C8
    for i, word in enumerate(words):
        if word >> 21 & 31 == 29 and word >> 26 in (9, 33, 35, 40, 41, 43, 49, 57):
            offset = word & 65535
            if offset in HOMES:
                words[i] = (word & 0xFFFF0000) | HOMES[offset]
    # The two ordinary-RAM render-table loads are independent. Preserve retail
    # read order, then assign their closed temporary roles and commutative OR.
    assert words[77:79] == [0x8C780018, 0x8C79001C]
    words[77], words[78] = registers(words[78], {25: 13}), registers(words[77], {24: 14})
    for i in (80, 81):
        words[i] = registers(words[i], {14: 25})
    assert words[85] == 0x03193025
    words[85] = 0x01AE3025
    # Three closed temporary exchanges cover the vector math and vertex loop.
    # The independent signed-index narrowing retains its own T7 lifetime.
    for i in (*range(86, 335), *range(337, 345), *range(358, 364)):
        words[i] = registers(words[i], TEMPORARIES)
    for i in range(141, 364):
        words[i] = registers(words[i], {5: 6, 6: 5})
    # Move only the two independent index-narrowing words behind the four
    # existing color/pointer words. No load/store is omitted or duplicated.
    block = words[335:341]
    words[335:341] = [block[i] for i in (2, 3, 4, 5, 0, 1)]
    return struct.pack('>373I', *words), dict(refs)


def main():
    root = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path.cwd())).resolve()
    conker = root / 'conker'
    out = root / source.BUILD
    raw, refs = payload(out / 'selected.o', source.FUNCTION)
    truth_raw, truth_refs = payload(out / 'retail.o', source.FUNCTION)
    # The checked reference binding inventory is independent of the body hash.
    pinned_refs = {int(k): [tuple(v) for v in values] for k, values in
                   json.loads((out / 'selected-report.json').read_text())['bindings'].items()}
    assert refs == truth_refs == pinned_refs
    normalized, bindings = normalize(raw, refs, pinned_refs)
    assert normalized == truth_raw and bindings == truth_refs
    fields = next(csv.reader(io.StringIO((conker / 'retail_word_patches.us.csv').read_text())))
    rows = []
    for i, (before, after) in enumerate(zip(struct.unpack('>373I', raw),
                                           struct.unpack('>373I', normalized))):
        if before == after:
            continue
        assert not refs.get(i * 4)
        rows.append(dict(filename='generated_1D4E00', function=source.FUNCTION,
                         offset='0x%X' % (i * 4), expected='0x%08X' % before,
                         replacement='0x%08X' % after, expected_relocations='-',
                         replacement_relocations='-',
                         note='Preserve strip renderer private homes, closed register roles and independent retail schedule',
                         insert_after='', insert_after_relocations='', omit='false'))
    assert len(rows) == 157
    original = (conker / 'retail_word_patches.us.csv').read_bytes()
    existing = [r for r in csv.DictReader(io.StringIO(original.decode()))
                if r['function'] == source.FUNCTION]
    assert not existing or existing == rows
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields,
                            lineterminator='\r\n' if b'\r\n' in original else '\n')
    writer.writerows([] if existing else rows)
    (out / 'proposed-guards.csv').write_bytes(original + stream.getvalue().encode())
    assembly = pad.emit_padded_assembly(out / 'selected.o', conker / 'asm/1D4E00.s',
                                        filename='generated_1D4E00',
                                        word_patches_path=out / 'proposed-guards.csv')
    (out / 'guarded.s').write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300',
                    '-mabi=32', '-I', 'include', '-o', str(out / 'guarded.o'),
                    str(out / 'guarded.s')], cwd=conker, capture_output=True, check=True)
    symbols = {r[1]: r[2][1] for r in symbol_rows((conker / 'build/conker.us.elf').read_bytes())}
    assert struct.pack('>373I', *bound_blob(*payload(out / 'guarded.o', source.FUNCTION),
                                          symbols)) == (conker / 'conker.us.bin').read_bytes()[source.ROM:source.ROM + 1492]
    assert same_functions(conker / 'build/src/game/generated_1D4E00.c.o',
                          out / 'guarded.o', (source.FUNCTION,)) == 22
    assert normalized_pools(out / 'baseline.o') == normalized_pools(out / 'selected.o')
    controls = 0
    for index in range(373):
        damaged = bytearray(raw)
        damaged[index * 4 + 3] ^= 1
        try:
            normalize(bytes(damaged), refs, pinned_refs)
        except ValueError:
            controls += 1
        else:
            raise AssertionError('Ineffective raw corruption guard')
    damaged_refs = dict(refs)
    damaged_refs[92] = [('R_MIPS_26', 'func_15144B34')]
    try:
        normalize(raw, damaged_refs, pinned_refs)
    except ValueError:
        controls += 1
    else:
        raise AssertionError('Ineffective binding corruption guard')
    report = dict(raw_words=373, padded_words=373, frame=200, guards=len(rows),
                  insertions=0, omissions=0, neighbors=22, corruption_controls=controls,
                  installed=bool(existing))
    (out / 'guard-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
