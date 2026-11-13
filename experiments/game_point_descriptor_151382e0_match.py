"""Rebuild the point descriptor candidate from fingerprinted source changes.

This is a private qualification fixture: prepare() does not modify the consumer
sources, retail guard manifest, production objects, or match counts.
"""
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
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT / 'conker/build/game-point-descriptor-151382e0-durable'
MANIFEST = json.loads(Path(__file__).with_name('game_point_descriptor_151382e0_manifest.json').read_text())
NAME = 'func_151382E0'
HELPER = 'func_15153F18'
sha = lambda text: hashlib.sha256(text.encode()).hexdigest()


def apply(text, changes, reverse=False):
    lines = text.splitlines(keepends=True)
    for item in reversed(changes):
        old, new = ('new', 'old') if reverse else ('old', 'new')
        at = item['new_at' if reverse else 'old_at']
        expected = item[old].splitlines(keepends=True)
        if lines[at:at + len(expected)] != expected:
            raise ValueError('Candidate patch context changed')
        lines[at:at + len(expected)] = item[new].splitlines(keepends=True)
    return ''.join(lines)


def sources():
    result = {}
    states = set()
    for name, spec in MANIFEST['paths'].items():
        current = (ROOT / spec['path']).read_text()
        if sha(current) == spec['before_sha256']:
            before, installed = current, False
        elif sha(current) == spec['after_sha256']:
            before, installed = apply(current, spec['changes'], True), True
        else:
            raise ValueError('Unknown input fingerprint: ' + spec['path'])
        after = apply(before, spec['changes'])
        if sha(before) != spec['before_sha256'] or sha(after) != spec['after_sha256']:
            raise ValueError('Candidate reconstruction failed: ' + name)
        result[name] = before, after
        states.add(installed)
    if len(states) != 1:
        raise ValueError('Partial installation detected')
    return result, states.pop()


def assemble(source, label):
    asm = OUT / (label + '.s')
    obj = asm.with_suffix('.o')
    asm.write_text(source)
    result = subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300',
                             '-mabi=32', '-I', 'include', '-o', str(obj), str(asm)],
                            cwd=ROOT / 'conker', capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr)
    return obj


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    for label, path in (('rom', 'conker/conker.us.bin'), ('layout', 'conker/retail_layout.us.txt'),
                        ('assembly', 'conker/asm/nonmatchings/game_161520/func_151382E0.s')):
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != MANIFEST[label + '_sha256']:
            raise ValueError('Qualification input changed: ' + path)
    texts, installed = sources()
    diagnostics, outputs = {}, {}
    for name in ('point', 'helper', 'effect', 'trail', 'caller'):
        before, after = texts[name]
        first, bd = compile_owner(ROOT, OUT, before, 'durable-' + name + '-before')
        second, ad = compile_owner(ROOT, OUT, after, 'durable-' + name + '-after')
        excluded = (NAME,) if name == 'point' else (HELPER,) if name == 'helper' else ()
        expected = {'point': 63, 'helper': 40, 'effect': 89, 'trail': 62, 'caller': 1}[name]
        if same_functions(first, second, excluded) != expected:
            raise ValueError('Changed owner function count: ' + name)
        if normalized_pools(first) != normalized_pools(second) or diagnostic_rows(bd) != diagnostic_rows(ad):
            raise ValueError('Changed owner pools or diagnostics: ' + name)
        diagnostics[name] = len(diagnostic_rows(ad))
        outputs[name] = second
    raw, raw_refs = payload(outputs['point'], NAME)
    source = (ROOT / 'conker/asm/nonmatchings/game_161520/func_151382E0.s').read_text()
    retail = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'
                      + source + '\n.size ' + NAME + ',.-' + NAME + '\n', 'durable-retail')
    truth, truth_refs = payload(retail, NAME)
    if len(raw) != 324 or raw_refs != truth_refs:
        raise ValueError('Point size or relocation mismatch')
    differences = [i for i in range(0, 324, 4) if raw[i:i+4] != truth[i:i+4]]
    if differences != [0, 4, 0x124, 0x138]:
        raise ValueError(('Unexpected point differences', differences))
    before_rows = list(csv.DictReader(io.StringIO(texts['guards'][0])))
    after_rows = list(csv.DictReader(io.StringIO(texts['guards'][1])))
    old_helper = [row for row in before_rows if row['function'] == HELPER]
    new_helper = [row for row in after_rows if row['function'] == HELPER]
    point = [row for row in after_rows if row['function'] == NAME]
    if len(old_helper) != 16 or len(new_helper) != 16 or len(point) != 4:
        raise ValueError('Unexpected guard count')
    if sum(a != b for a, b in zip(old_helper, new_helper)) != 5:
        raise ValueError('Unexpected helper guard change')
    guard = OUT / 'durable-private-guards.csv'
    guard.write_text(texts['guards'][1])
    point_obj = assemble(pc.emit_padded_assembly(outputs['point'], ROOT / 'conker/retail_layout.us.txt',
        'game_161520', rodata_symbol='jtbl_800A4350_game', word_patches_path=guard,
        function_objects={'func_15138BC0': outputs['caller']}), 'durable-point-padded')
    if payload(point_obj, NAME) != payload(retail, NAME):
        raise ValueError('Padded point differs from retail')
    if same_functions(ROOT / 'conker/build/src/game_161520.c.o', point_obj, (NAME,)) != 64:
        raise ValueError('Padded point neighbor changed')
    for label, assembly in (
        ('durable-helper-generated', pg.emit_padded_assembly(outputs['helper'], ROOT / 'conker/asm/17CAF0.s',
            filename='generated_17CAF0', word_patches_path=guard)),
        ('durable-helper-padded', pc.emit_padded_assembly(outputs['helper'], ROOT / 'conker/retail_layout.us.txt',
            'generated_17CAF0', word_patches_path=guard)),
    ):
        obj = assemble(assembly, label)
        if same_functions(ROOT / 'conker/build/src/game/generated_17CAF0.c.o', obj) != 41:
            raise ValueError('Padded helper changed')
    addresses = {row[1]: row[2][1] for row in symbol_rows((ROOT / 'conker/build/conker.us.elf').read_bytes())}
    words = bound_blob(truth, truth_refs, {n: addresses[n] for refs in truth_refs.values() for _, n in refs})
    if struct.pack('>81I', *words) != (ROOT / 'conker/conker.us.bin').read_bytes()[0x165790:0x1658d4]:
        raise ValueError('Retail image does not match assembled point')
    print('Private point candidate prepared; raw 77/81, guarded 81/81, owner and helper neighbors preserved', flush=True)
    return texts, installed


if __name__ == '__main__':
    prepare()
