"""Reconstruct and qualify the slot-notification callback from pinned inputs."""
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
OUT = ROOT / 'conker/build/game-slot-notification-15156028-durable'
MANIFEST = json.loads(Path(__file__).with_name('game_slot_notification_15156028_manifest.json').read_text())
NAME, OWNER = 'func_15156028', 'generated_182C30'
sha = lambda text: hashlib.sha256(text.encode()).hexdigest()


def apply(text, changes, reverse=False):
    lines = text.splitlines(keepends=True)
    for item in reversed(changes):
        old, new = ('new', 'old') if reverse else ('old', 'new')
        at = item['new_at' if reverse else 'old_at']
        expected = item[old].splitlines(keepends=True)
        if lines[at:at + len(expected)] != expected:
            raise ValueError('Slot-notification patch context changed')
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
            raise ValueError('Unknown input fingerprint: ' + spec['path'])
        after = apply(before, spec['changes'])
        if sha(before) != spec['before_sha256'] or sha(after) != spec['after_sha256']:
            raise ValueError('Slot-notification reconstruction failed: ' + name)
        result[name] = before, after
        states.add(installed)
    if len(states) != 1:
        raise ValueError('Partial slot-notification installation')
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
                        ('assembly', 'conker/asm/182C30.s')):
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != MANIFEST[label + '_sha256']:
            raise ValueError('Qualification input changed: ' + path)
    texts, installed = sources()
    before, bd = compile_owner(ROOT, OUT, texts['source'][0], 'durable-before')
    after, ad = compile_owner(ROOT, OUT, texts['source'][1], 'durable-after')
    if same_functions(before, after, (NAME,)) != 8:
        raise ValueError('Changed slot owner neighbors')
    if normalized_pools(before) != normalized_pools(after) or diagnostic_rows(bd) != diagnostic_rows(ad):
        raise ValueError('Changed slot owner pools or diagnostics')
    asm = (ROOT / 'conker/asm/182C30.s').read_text()
    start = asm.index('glabel ' + NAME)
    end = asm.index('endlabel ' + NAME, start) + len('endlabel ' + NAME)
    retail = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'
                      + asm[start:end] + '\n.size ' + NAME + ',.-' + NAME + '\n', 'durable-retail')
    raw, raw_refs = payload(after, NAME)
    truth, truth_refs = payload(retail, NAME)
    if len(raw) != 352 or len(truth) != 352:
        raise ValueError('Slot body extent changed')
    rows = list(csv.DictReader(io.StringIO(texts['guards'][1])))
    if len([r for r in rows if r['function'] == NAME]) != 51:
        raise ValueError('Unexpected slot guard count')
    guards = OUT / 'durable-guards.csv'
    guards.write_text(texts['guards'][1])
    objects = []
    for label, emitted in (
        ('durable-generated', pg.emit_padded_assembly(after, ROOT / 'conker/asm/182C30.s',
            filename=OWNER, word_patches_path=guards)),
        ('durable-generic', pc.emit_padded_assembly(after, ROOT / 'conker/retail_layout.us.txt',
            OWNER, word_patches_path=guards)),
    ):
        obj = assemble(emitted, label)
        if payload(obj, NAME) != (truth, truth_refs):
            raise ValueError('Padded slot body or relocations changed')
        if same_functions(ROOT / 'conker/build/src/game/generated_182C30.c.o', obj, (NAME,)) != 8:
            raise ValueError('Padded slot owner neighbor changed')
        objects.append(obj)
    lookup = {r[1]: r[2][1] for r in symbol_rows((ROOT / 'conker/build/conker.us.elf').read_bytes())}
    words = bound_blob(truth, truth_refs, {n: lookup[n] for refs in truth_refs.values() for _, n in refs})
    if struct.pack('>88I', *words) != (ROOT / 'conker/conker.us.bin').read_bytes()[0x1834d8:0x183638]:
        raise ValueError('Assembled slot body differs from retail image')
    print('Slot callback: raw and both padded owner objects prepared; 88 retail words, 8 neighbors', flush=True)
    return texts, installed


if __name__ == '__main__':
    prepare()
