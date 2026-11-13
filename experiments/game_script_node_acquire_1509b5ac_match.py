"""Rebuild the script-node acquisition candidate and check its retail slot."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object', pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT / 'conker/build/game-script-acquire-1509b5ac-durable'
MANIFEST = json.loads(Path(__file__).with_name('game_script_node_acquire_1509b5ac_manifest.json').read_text())
NAME, OWNER = 'func_1509B5AC', 'game_C8950'
ASM = 'conker/asm/nonmatchings/game_C8950/func_1509B5AC.s'
sha = lambda text: hashlib.sha256(text.encode()).hexdigest()


def apply(text, changes, reverse=False):
    lines = text.splitlines(keepends=True)
    for item in reversed(changes):
        old, new = ('new', 'old') if reverse else ('old', 'new')
        at = item['new_at' if reverse else 'old_at']
        expected = item[old].splitlines(keepends=True)
        if lines[at:at + len(expected)] != expected:
            raise ValueError('Script node candidate context changed')
        lines[at:at + len(expected)] = item[new].splitlines(keepends=True)
    return ''.join(lines)


def sources():
    result, states = {}, set()
    for name, spec in MANIFEST['paths'].items():
        current = (ROOT / spec['path']).read_text()
        if sha(current) == spec['before_sha256']:
            before, installed = current, False
        elif sha(current) == spec['after_sha256']:
            before, installed = apply(current, spec['changes'], True), True
        else:
            raise ValueError('Unknown script node input: ' + spec['path'])
        after = apply(before, spec['changes'])
        if sha(before) != spec['before_sha256'] or sha(after) != spec['after_sha256']:
            raise ValueError('Script node source reconstruction failed')
        result[name] = before, after
        states.add(installed)
    if len(states) != 1:
        raise ValueError('Partially installed script node candidate')
    return result, states.pop()


def assemble(text, label):
    asm = OUT / (label + '.s')
    obj = asm.with_suffix('.o')
    asm.write_text(text)
    result = subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300',
                             '-mabi=32', '-I', 'include', '-o', str(obj), str(asm)],
                            cwd=ROOT / 'conker', capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr)
    return obj


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, path in (('rom', 'conker/conker.us.bin'), ('layout', 'conker/retail_layout.us.txt'),
                      ('assembly', ASM)):
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != MANIFEST[key + '_sha256']:
            raise ValueError('Script node input changed: ' + path)
    texts, installed = sources()
    before, bd = compile_owner(ROOT, OUT, texts['source'][0], 'durable-before')
    after, ad = compile_owner(ROOT, OUT, texts['source'][1], 'durable-after')
    if same_functions(before, after, (NAME,)) != 16:
        raise ValueError('Script node owner neighbor changed')
    if normalized_pools(before) != normalized_pools(after) or diagnostic_rows(bd) != diagnostic_rows(ad):
        raise ValueError('Script node owner pool or diagnostics changed')
    if payload(before, 'func_1509B8FC') != payload(after, 'func_1509B8FC'):
        raise ValueError('Creator return correction changed generated instructions')
    retail = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'
                      + (ROOT / ASM).read_text() + '\n.size ' + NAME + ',.-' + NAME + '\n', 'durable-retail')
    raw, refs = payload(after, NAME)
    truth, truth_refs = payload(retail, NAME)
    if len(raw) != 344 or len(truth) != 344 or refs != truth_refs:
        raise ValueError('Script node extent or relocation bindings changed')
    guards = OUT / 'proposed-guards.csv'
    guards.write_text(texts['guards'][1])
    rows = [r for r in csv.DictReader(io.StringIO(texts['guards'][1])) if r['function'] == NAME]
    if rows != MANIFEST['guard_rows'] or len(rows) != 6:
        raise ValueError('Script node guard rows changed')
    padded = assemble(pc.emit_padded_assembly(after, ROOT / 'conker/retail_layout.us.txt', OWNER,
                                              word_patches_path=guards), 'durable-padded')
    if payload(padded, NAME) != (truth, truth_refs):
        raise ValueError('Padded script node body or relocations differ from retail')
    if same_functions(ROOT / 'conker/build/src/game_C8950.c.o', padded, (NAME,)) != 16:
        raise ValueError('Padded script node owner neighbor changed')
    addresses = {row[1]: row[2][1] for row in symbol_rows((ROOT / 'conker/build/conker.us.elf').read_bytes())}
    words = bound_blob(truth, truth_refs, {symbol: addresses[symbol]
                       for group in truth_refs.values() for _, symbol in group})
    if struct.pack('>86I', *words) != (ROOT / 'conker/conker.us.bin').read_bytes()[0xC8A5C:0xC8BB4]:
        raise ValueError('Assembled script node body differs from retail ROM')
    link_owner(ROOT, OUT, after, OWNER)
    print('Script node: 86 retail words, six guards, 16 unchanged neighbors; creator C ABI corrected', flush=True)
    return texts, installed


if __name__ == '__main__':
    prepare()
