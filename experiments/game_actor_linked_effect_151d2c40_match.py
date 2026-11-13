"""Fail-closed qualification of the linked actor-effect updater."""
import csv, hashlib, io, json, os, shutil, struct, subprocess, sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object', pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT / 'conker/build/game-actor-linked-effect-151d2c40-durable'
NAME = 'func_151D2C40'
OWNER = 'game_1FFF60'
MANIFEST = json.loads(Path(__file__).with_name('game_actor_linked_effect_151d2c40_manifest.json').read_text())
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()

def apply(text, changes, reverse=False):
    lines = text.splitlines(keepends=True)
    for item in reversed(changes):
        old, new = ('new', 'old') if reverse else ('old', 'new')
        at = item['new_at' if reverse else 'old_at']
        expected = item[old].splitlines(keepends=True)
        if lines[at:at + len(expected)] != expected:
            raise ValueError('Linked-effect source context changed')
        lines[at:at + len(expected)] = item[new].splitlines(keepends=True)
    return ''.join(lines)

def sources():
    s, g = MANIFEST['source'], MANIFEST['guards']
    current = (ROOT / s['path']).read_text()
    if sha(current) == s['before_sha256']:
        before, installed = current, False
    elif sha(current) == s['after_sha256']:
        before, installed = apply(current, s['changes'], True), True
    else:
        raise ValueError('Unknown linked-effect source state')
    after = apply(before, s['changes'])
    if sha(before) != s['before_sha256'] or sha(after) != s['after_sha256']:
        raise ValueError('Linked-effect source hash changed')
    current, suffix = (ROOT / g['path']).read_text(), g['append']
    if installed:
        if not current.endswith(suffix): raise ValueError('Guard suffix missing')
        old, new = current[:-len(suffix)], current
    else:
        old, new = current, current + suffix
    if sha(old) != g['before_sha256'] or sha(new) != g['after_sha256']:
        raise ValueError('Linked-effect guard state changed')
    return {'source': (before, after), 'guards': (old, new)}, installed

def assemble(text, label):
    asm = OUT / (label + '.s'); obj = asm.with_suffix('.o'); asm.write_text(text)
    args = ['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(obj.relative_to(ROOT/'conker')), str(asm.relative_to(ROOT/'conker'))]
    p = subprocess.run(args, cwd=ROOT/'conker', capture_output=True, text=True)
    if p.returncode: raise ValueError(p.stderr)
    return obj

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    for path, digest in MANIFEST['inputs'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != digest: raise ValueError('Input changed: '+path)
    texts, installed = sources()
    for path, digest in MANIFEST['baseline'].items():
        dest = OUT/'frozen'/path; dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            if installed: raise ValueError('Retained pre-install baseline required: '+path)
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != digest: raise ValueError('Baseline changed: '+path)
            shutil.copyfile(ROOT/path, dest)
        if hashlib.sha256(dest.read_bytes()).hexdigest() != digest: raise ValueError('Frozen baseline changed: '+path)
    (OUT/'formatted.c').write_text(texts['source'][1])
    (OUT/'private-guards.csv').write_text(texts['guards'][1])
    (OUT/'proposed-guards.csv').write_text(texts['guards'][1])
    before, bd = compile_owner(ROOT, OUT, texts['source'][0], 'before')
    after, ad = compile_owner(ROOT, OUT, texts['source'][1], 'portable-03')
    if same_functions(before, after, (NAME,)) != 18 or normalized_pools(before) != normalized_pools(after) or diagnostic_rows(bd) != diagnostic_rows(ad):
        raise ValueError('Owner neighbors, pools or diagnostics changed')
    asm = (ROOT/'conker/asm/nonmatchings/game_1FFF60/func_151D2C40.s').read_text()
    retail = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm+'\n.size '+NAME+',.-'+NAME+'\n', 'retail')
    raw, refs = payload(after, NAME); truth, trefs = payload(retail, NAME)
    if len(raw) != 364 or len(truth) != 364: raise ValueError('Unexpected routine extent')
    w = list(struct.unpack('>91I', raw))
    if w[12:14] != [0x9058003b, 0x92190014] or 48 in refs or 52 in refs: raise ValueError('Unexpected load sequence')
    w[12:14] = [0x92180014, 0x9059003b]
    if (struct.pack('>91I', *w), refs) != (truth, trefs): raise ValueError('Raw derivation or bindings differ')
    old = list(csv.DictReader(io.StringIO(texts['guards'][0])))
    new = list(csv.DictReader(io.StringIO(texts['guards'][1])))
    if new[:len(old)] != old or new[len(old):] != MANIFEST['guard_rows'] or len(new)-len(old) != 2: raise ValueError('Guard history changed')
    emitted = pc.emit_padded_assembly(after, ROOT/'conker/retail_layout.us.txt', OWNER, word_patches_path=OUT/'proposed-guards.csv')
    padded = assemble(emitted, 'guarded')
    if payload(padded, NAME) != (truth, trefs) or same_functions(ROOT/'conker/build/src/game_1FFF60.c.o', padded, (NAME,)) != 18: raise ValueError('Padded owner differs')
    addresses = {r[1]:r[2][1] for r in symbol_rows((OUT/'frozen/conker/build/conker.us.elf').read_bytes())}
    linked = bound_blob(truth, trefs, addresses)
    if struct.pack('>91I', *linked) != (ROOT/'conker/conker.us.bin').read_bytes()[0x2000f0:0x20025c]: raise ValueError('Retail bytes differ')
    print('Linked effect: 91 retail words, two guarded loads, 18 unchanged neighbors; installed='+str(installed), flush=True)
    return texts, installed

if __name__ == '__main__': prepare()
