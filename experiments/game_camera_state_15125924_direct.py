"""Qualify the direct camera-state callback against the original object."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object', pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT/'conker/build/game-camera-state-15125924-qualified'
MANIFEST = json.loads(Path(__file__).with_name('game_camera_state_15125924_direct_manifest.json').read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
norm = lambda data: data.replace(b'\r\n', b'\n')


def assemble(text, label):
    source = OUT/(label+'.s')
    obj = OUT/(label+'.o')
    source.write_text(text)
    result = subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                             '-I', 'include', '-o', str(obj), str(source)],
                            cwd=ROOT/'conker', capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr)
    return obj


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = MANIFEST
    name = spec['name']
    if sha((ROOT/'conker/conker.us.bin').read_bytes()) != spec['rom_sha256']:
        raise ValueError('Retail input changed')
    guards = ROOT/'conker/retail_word_patches.us.csv'
    guardbytes = guards.read_bytes()
    if sha(norm(guardbytes)) != spec['guard_sha256_normalized']:
        raise ValueError('Guard baseline changed')
    if any(row['function'] == name for row in csv.DictReader(io.StringIO(guardbytes.decode()))):
        raise ValueError('Unexpected target guards')
    source = norm((ROOT/spec['source']).read_bytes())
    old = spec['old_source'].encode()
    selected = spec['selected_source'].encode()
    if source not in (old, selected) or sha(old) != spec['baseline_sha256']:
        raise ValueError('Owner source changed')
    before, bd = compile_owner(ROOT, OUT, spec['old_source'], 'before')
    after, ad = compile_owner(ROOT, OUT, spec['selected_source'], 'after')
    if same_functions(before, after, (name,)) != 44 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Owner neighbor or pool changed')
    if diagnostic_rows(bd) != diagnostic_rows(ad):
        raise ValueError('Compiler diagnostics changed')
    raw, rawrefs = payload(after, name)
    if len(raw) != 328 or sha(raw) != spec['raw_sha256']:
        raise ValueError('Candidate instruction body changed')
    assembly = (ROOT/spec['assembly']).read_text()
    retail = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly+
                      '\n.size '+name+',.-'+name+'\n', 'retail')
    truth, refs = payload(retail, name)
    if (raw, rawrefs) != (truth, refs):
        raise ValueError('Direct C differs from retail')
    padded = assemble(pc.emit_padded_assembly(after, ROOT/'conker/retail_layout.us.txt', spec['owner'],
                                               word_patches_path=guards), 'padded')
    baseline = assemble(pc.emit_padded_assembly(before, ROOT/'conker/retail_layout.us.txt', spec['owner'],
                                                 word_patches_path=guards), 'padded-before')
    if payload(padded, name) != (truth, refs) or same_functions(baseline, padded, (name,)) != 44:
        raise ValueError('Padded target or owner neighbors differ')
    return dict(before=before, after=after, retail=retail, padded=padded, installed=source == selected)
