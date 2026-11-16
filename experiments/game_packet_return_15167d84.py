"""Recover the packet allocator's nullable return without instruction guards.

Bound to the retained 895-input emitter baseline. This repairs an already
matching function's C ABI and earns no additional matching credit.
"""
from pathlib import Path
import csv
import difflib
import hashlib
import io
import json
import os
import re
import struct
import subprocess
import sys

from tools.experiments.game_remaining_donor_candidates import compile_owner, body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object', pg)
from tools import pad_c_object as pc

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2]))
STAGE = ROOT / 'conker/build/game-next-151a11e4-private'
FROZEN = STAGE / 'production-baseline'
OUT = STAGE / 'return-abi-qualified'
NAME, ENTRY, ROM, WORDS = 'func_15167D84', 0x15167D84, 0x195234, 34
SOURCES = ('conker/src/game_1944C0.c',
           'conker/src/game/generated_17CAF0.c',
           'conker/src/game/generated_1CC440.c')
OWNERS = ('game_1944C0', 'game/generated_17CAF0', 'game/generated_1CC440')
SELECTED = '''/* Return the allocated particle so callers can append their extra payload. */
u8 *func_15167D84(void *packet, s32 alternate, s32 extraBytes, s8 marker, u8 mode, s32 owner) {
    u8 *particle;
    s32 kind;

    if (alternate == 0) {
        kind = 5;
    } else {
        kind = 0x42;
    }

    particle = func_15167A68(kind, owner, extraBytes + 0x50, 0, mode, 1);
    if (particle == NULL) return particle;
    bcopy(packet, particle + 0x10, 0x38);
    particle[0x48] = marker;
    return particle;
}'''
RAW_SHA = '2d47ca1d706addb677e8a3cbb8e8fad0ff5f5f4c631f56ea28e3b31c3a5583e5'
sha = lambda b: hashlib.sha256(b).hexdigest()


def symbols():
    answer = {'func_15167A68': 0x15167A68}
    for line in (ROOT / 'conker/symbol_addrs.us.txt').read_text().splitlines():
        if line.split('=', 1)[0].strip() in ('bcopy', 'memcpy'):
            answer[line.split('=', 1)[0].strip()] = int(line.split('=', 1)[1].split(';', 1)[0], 16)
    assert set(answer) == {'func_15167A68', 'bcopy', 'memcpy'}
    return answer


def check_inputs():
    record = json.loads((FROZEN / 'fingerprints.json').read_text())
    plan = json.loads((OUT / 'adoption-plan.json').read_text()) if (OUT / 'adoption-plan.json').exists() else {}
    installed = (ROOT / SOURCES[0]).read_bytes() != (FROZEN / SOURCES[0]).read_bytes()
    for name, wanted in record['inputs'].items():
        assert sha((FROZEN / name).read_bytes()) == wanted, ('frozen input changed', name)
        assert sha((ROOT / name).read_bytes()) == (plan.get(name, wanted) if installed else wanted), name
    return installed


def recovered_owner(before, index):
    if index == 0:
        return before.replace(body(before, NAME), SELECTED)
    assert before.count('void func_15167D84(') == 1
    return before.replace('void func_15167D84(', 'u8 *func_15167D84(')


def retired_guards(before):
    lines = before.splitlines(keepends=True)
    selected, kept = [], [lines[0]]
    for line in lines[1:]:
        row = next(csv.reader([line.decode()]))
        (selected if row[:2] == ['game_1944C0', NAME] else kept).append(line)
    assert len(selected) == 13
    rows = list(csv.DictReader(io.StringIO((lines[0] + b''.join(selected)).decode())))
    assert [int(r['offset'], 0) for r in rows] == list(range(0x48, 0x7C, 4))
    assert sum(bool(r['insert_after']) for r in rows) == 2
    return b''.join(kept), lines[0] + b''.join(selected)


def checked_payload(raw, refs):
    assert len(raw) == 136 and sha(raw) == RAW_SHA, 'packet return compiler body changed'
    wanted = {at: [('R_MIPS_26', name)] for at, name in ((0x40, 'func_15167A68'), (0x64, 'bcopy'))}
    assert refs == wanted, ('packet return bindings changed', refs)
    return raw, refs


def diagnostics(before, after, old, new, label):
    line_map = {}
    for tag, a, z, b, y in difflib.SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=False).get_opcodes():
        if tag == 'equal':
            line_map.update({b + i + 1: a + i + 1 for i in range(z - a)})
    def normalize(text, changed):
        text = text.replace(label + ('-after.c' if changed else '-before.c'), 'owner.c')
        return re.sub(r', line (\d+):', lambda m: ', line %d:' % (line_map[int(m[1])] if changed else int(m[1])), text)
    assert normalize(old, False) == normalize(new, True), 'owner diagnostics changed'


def assemble(text, label):
    source = OUT / (label + '.s')
    obj = source.with_suffix('.o')
    source.write_text(text)
    p = subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(obj), str(source)], cwd=ROOT / 'conker', capture_output=True, text=True)
    assert p.returncode == 0 and not p.stderr, p.stderr
    return obj


def qualify():
    installed = check_inputs()
    OUT.mkdir(exist_ok=True)
    guards, retired = retired_guards((FROZEN / 'conker/retail_word_patches.us.csv').read_bytes())
    (OUT / 'proposed-guards.csv').write_bytes(guards)
    (OUT / 'retired-guards.csv').write_bytes(retired)
    rows = []
    for index, (name, owner) in enumerate(zip(SOURCES, OWNERS)):
        before = (FROZEN / name).read_text()
        after = recovered_owner(before, index)
        label = 'owner%d' % index
        (OUT / (label + '-proposed.c')).write_text(after)
        a, ad = compile_owner(ROOT, OUT, before, label + '-before')
        b, bd = compile_owner(ROOT, OUT, after, label + '-after')
        diagnostics(before, after, ad, bd, label)
        count = same_functions(a, b, (NAME,) if index == 0 else ())
        assert count == (41, 41, 39)[index]
        assert normalized_pools(a) == normalized_pools(b)
        padded = assemble(pc.emit_padded_assembly(b, ROOT / 'conker/retail_layout.us.txt', owner.split('/')[-1], word_patches_path=OUT / 'proposed-guards.csv'), label + '-layout')
        installed_obj = FROZEN / ('conker/build/src/' + owner + '.c.o')
        assert same_functions(installed_obj, padded, (NAME,) if index == 0 else ()) == count
        assert normalized_pools(installed_obj) == normalized_pools(padded)
        rows.append(dict(source=name, unchanged_raw_functions=count, unchanged_padded_functions=count, pools_unchanged=True, existing_warnings=ad.count('cfe: Warning')))
    raw, refs = checked_payload(*payload(OUT / 'owner0-after.o', NAME))
    retail = struct.unpack_from('>34I', (ROOT / 'conker/conker.us.bin').read_bytes(), ROM)
    assert tuple(bound_blob(raw, refs, symbols())) == retail
    assert payload(OUT / 'owner0-layout.o', NAME) == (raw, refs)
    # Independent strict retail-span padder. The old handwritten source for
    # this helper is absent, so retain an explicitly reconstructed *target-only*
    # original annotation from the immutable retail image, not a whole-owner claim.
    original = OUT / 'original-target.s'
    original.write_text('glabel ' + NAME + '\n' + ''.join('/* %X %08X %08X */ .word 0x%08X\n' % (ROM + 4*i, ENTRY + 4*i, w, w) for i, w in enumerate(retail)))
    compact = assemble('.section .text,"ax"\n.set noat\n.set noreorder\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'+''.join('.word 0x%08X\n'%w for w in struct.unpack('>34I', raw))+'.size '+NAME+',.-'+NAME+'\n'+''.join('.reloc '+NAME+'+0x%X,%s,%s\n'%(at,kind,n)for at,rs in refs.items()for kind,n in rs), 'target-compact')
    strict = assemble(pg.emit_padded_assembly(compact, original, filename='game_1944C0'), 'target-strict')
    assert payload(strict, NAME) == (raw, refs)
    # Both relocation-bearing JALs remain symbolic under independent rebases.
    for delta in (0, 0x10000, 0x20000):
        moved = {n:v+delta for n,v in symbols().items()}
        assert bound_blob(*payload(strict, NAME), moved) == bound_blob(raw, refs, moved)
    check_inputs()
    report = dict(installed=installed, raw_words=34, frame=40, direct_retail_words=34, new_guards=0, retired_guards=13, retired_insertions=2, whole_owner_layout_padders=3, strict_target_padder=True, owners=rows, c_match_credit=0)
    (OUT / 'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    print(json.dumps(qualify()), flush=True)
