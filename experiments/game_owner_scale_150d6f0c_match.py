"""Qualify the linked-owner scale callback without installing it.

The float-to-u32 cast has portable C semantics only on the finite, representable
path. Guest tests separately cover the retail conversion's non-finite behavior.
"""
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object', pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import body, compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT / 'conker/build/game-owner-scale-150d6f0c-match'
MANIFEST = json.loads(Path(__file__).with_name('game_owner_scale_150d6f0c_manifest.json').read_text())
NAME, OWNER = MANIFEST['function'], MANIFEST['owner']
STUB = 's32 func_150D6F0C() {\n    return 0;\n}'
SNIPPET = MANIFEST['declarations'] + '\n' + MANIFEST['comment'] + '\n' + MANIFEST['body']


def proposal(original):
    current = body(original, NAME)
    if current == MANIFEST['body']:
        if SNIPPET not in original:
            raise ValueError('Installed declarations or comment differ')
        return original, True
    if current != STUB:
        raise ValueError('Unexpected production predecessor')
    return original.replace(current, SNIPPET, 1), False


def payload(obj):
    text, functions, relocs = parse_object(obj)
    item = functions[NAME]
    start, size = item['value'], item['size']
    return text[start:start + size], {i - start: v for i, v in relocs.items() if start <= i < start + size}


def assemble(source, label):
    path = OUT / (label + '.s')
    obj = path.with_suffix('.o')
    path.write_text(source)
    argv = ['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300',
            '-mabi=32', '-I', 'include', '-o', str(obj), str(path)]
    result = subprocess.run(argv, cwd=ROOT / 'conker', capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr)
    return obj


def guard_file(installed):
    live = (ROOT / 'conker/retail_word_patches.us.csv').read_bytes()
    existing = [row for row in csv.DictReader(io.StringIO(live.decode())) if row['function'] == NAME]
    if installed:
        if existing != MANIFEST['guard_rows']:
            raise ValueError('Installed target guards changed')
        proposed = live
    else:
        if existing:
            raise ValueError('Unexpected predecessor guard')
        fields = next(csv.reader(io.StringIO(live.decode())))
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\r\n' if b'\r\n' in live else '\n')
        writer.writerows(MANIFEST['guard_rows'])
        proposed = live + stream.getvalue().encode()
    result = OUT / 'proposed-guards.csv'
    result.write_bytes(proposed)
    return result


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    live = (ROOT / MANIFEST['source']).read_text()
    selected, installed = proposal(live)
    original = live.replace(SNIPPET, STUB, 1) if installed else live
    before, before_diag = compile_owner(ROOT, OUT, original, 'baseline')
    after, after_diag = compile_owner(ROOT, OUT, selected, 'selected')
    if same_functions(before, after, (NAME,)) != 16:
        raise ValueError('Owner neighbors changed')
    if normalized_pools(before) != normalized_pools(after) or diagnostic_rows(before_diag) != diagnostic_rows(after_diag):
        raise ValueError('Owner pools or diagnostics changed')
    raw, refs = payload(after)
    if len(raw) != 348 or hashlib.sha256(raw).hexdigest() != MANIFEST['raw_sha256']:
        raise ValueError('Candidate body changed')
    if refs != {0x48: [('R_MIPS_26', 'func_150D6C98')], 0x110: [('R_MIPS_HI16', 'D_800BE9A4')], 0x118: [('R_MIPS_LO16', 'D_800BE9A4')]}:
        raise ValueError('Candidate relocation binding changed')
    text = (ROOT / MANIFEST['assembly']).read_text()
    start, end = 'glabel ' + NAME + '\n', 'endlabel ' + NAME
    fragment = start + text.split(start, 1)[1].split(end, 1)[0] + end
    retail = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n' +
                      fragment + '\n.size ' + NAME + ',.-' + NAME + '\n', 'retail')
    truth, truth_refs = payload(retail)
    if len(truth) != MANIFEST['size'] or truth_refs != refs:
        raise ValueError('Retail words or relocation binding changed')
    guard = guard_file(installed)
    generated = assemble(pad_generated_object.emit_padded_assembly(after, ROOT / MANIFEST['assembly'],
                         filename=OWNER, word_patches_path=guard), 'generated')
    generic = assemble(pad_c_object.emit_padded_assembly(after, ROOT / 'conker/retail_layout.us.txt',
                       OWNER, word_patches_path=guard), 'generic')
    if payload(generated) != (truth, truth_refs) or payload(generic) != (truth, truth_refs):
        raise ValueError('Guarded independent padders do not match retail')
    if sections(generated)['.reginfo'][1] != sections(ROOT / 'conker/build/src/game/generated_1028F0.c.o')['.reginfo'][1]:
        raise ValueError('Padded register metadata changed')
    return dict(source=selected, before=before, after=after, retail=retail, generated=generated,
                generic=generic, guards=guard, installed=installed)
