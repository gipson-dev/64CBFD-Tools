"""Qualify the C exponential approximation and its checked retail schedule."""
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
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT/'conker/build/game-exponential-1504a2b0-match'
MANIFEST = json.loads(Path(__file__).with_name('game_exponential_1504a2b0_manifest.json').read_text())
NAME = MANIFEST['name']


def payload(path):
    text, funcs, refs = parse_object(path)
    f = funcs[NAME]; a = f['value']; n = f['size']
    return text[a:a+n], {i-a: rows for i, rows in refs.items() if a <= i < a+n}


def proposal(source):
    old, selected = MANIFEST['old_body'], MANIFEST['selected']
    if source.count(old) == 1 and selected not in source:
        return source.replace(old, selected, 1), False
    if source.count(selected) == 1 and old not in source:
        return source, True
    raise ValueError('Unknown or partially installed source')


def proposed_guards(installed):
    live = (ROOT/'conker/retail_word_patches.us.csv').read_bytes()
    rows = [r for r in csv.DictReader(io.StringIO(live.decode())) if r['function'] == NAME]
    if rows != (MANIFEST['guard_rows'] if installed else []):
        raise ValueError('Unexpected exponential guard rows')
    stream = io.StringIO(newline='')
    fields = next(csv.reader(io.StringIO(live.decode())))
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writerows(MANIFEST['guard_rows'])
    suffix = stream.getvalue().encode()
    if installed:
        if not live.endswith(suffix):
            raise ValueError('Installed guard rows are not the expected suffix')
        return live
    if not live.endswith(b'\n'):
        raise ValueError('Guard manifest has no terminating newline')
    return live + suffix


def assemble(text, label):
    src = OUT/(label+'.s'); obj = src.with_suffix('.o'); src.write_text(text)
    result = subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300',
                             '-mabi=32', '-I', 'include', '-o', str(obj), str(src)],
                            cwd=ROOT/'conker', capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr)
    return obj


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    live = (ROOT/MANIFEST['source']).read_text()
    selected, installed = proposal(live)
    original = live.replace(MANIFEST['selected'], MANIFEST['old_body'], 1) if installed else live
    before, bd = compile_owner(ROOT, OUT, original, 'baseline')
    after, ad = compile_owner(ROOT, OUT, selected, 'selected')
    if same_functions(before, after, (NAME,)) != 0 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Unexpected owner or pool changes')
    if diagnostic_rows(bd) != diagnostic_rows(ad):
        raise ValueError('Compiler diagnostics changed')
    raw, _ = payload(after)
    if len(raw) != 4*MANIFEST['raw_words'] or hashlib.sha256(raw).hexdigest() != MANIFEST['raw_sha256']:
        raise ValueError('Raw candidate fingerprint changed')
    assembly = (ROOT/MANIFEST['assembly']).read_text()
    marker = 'glabel '+NAME+'\n'; end = 'endlabel '+NAME
    fragment = marker+assembly.split(marker, 1)[1].split(end, 1)[0]+end
    retail = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+NAME+',.-'+NAME+'\n', 'retail')
    truth, refs = payload(retail)
    if len(truth) != 4*MANIFEST['retail_words'] or hashlib.sha256(truth).hexdigest() != MANIFEST['retail_sha256']:
        raise ValueError('Retail instruction fingerprint changed')
    guards = OUT/'guards.csv'; guards.write_bytes(proposed_guards(installed))
    one = assemble(pad_generated_object.emit_padded_assembly(after, ROOT/MANIFEST['assembly'],
                   filename=MANIFEST['owner'], word_patches_path=guards), 'generated')
    two = assemble(pad_c_object.emit_padded_assembly(after, ROOT/'conker/retail_layout.us.txt',
                   MANIFEST['owner'], word_patches_path=guards), 'generic')
    if payload(one) != (truth, refs) or payload(two) != (truth, refs):
        raise ValueError('Independent padded outputs differ from retail')
    if installed and one.read_bytes() != (ROOT/'conker/build/src/game/generated_77760.c.o').read_bytes():
        raise ValueError('Installed padded owner differs')
    return dict(source=selected, before=before, after=after, retail=retail,
                generated=one, generic=two, installed=installed, guards=guards)
