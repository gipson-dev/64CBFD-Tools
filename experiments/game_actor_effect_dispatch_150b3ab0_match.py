"""Fingerprint and prepare the actor-effect dispatch and its typed caller."""
import hashlib, json, os, shutil, struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT / 'conker/build/game-actor-effect-dispatch-150b3ab0-durable'
MANIFEST = json.loads(Path(__file__).with_name('game_actor_effect_dispatch_150b3ab0_manifest.json').read_text())

def digest(data):
    return hashlib.sha256(data).hexdigest()

def input_digest(path, data):
    if path not in ('conker/conker.us.bin', 'ido/ido5.3_recomp/cc'):
        data = data.replace(b'\r\n', b'\n')
    return digest(data)

def apply(text, changes, reverse=False):
    lines = text.splitlines(keepends=True)
    for item in reversed(changes):
        old, new = ('new', 'old') if reverse else ('old', 'new')
        at = item['new_at' if reverse else 'old_at']
        expected = item[old].splitlines(keepends=True)
        if lines[at:at + len(expected)] != expected:
            raise ValueError('Actor-effect source context changed')
        lines[at:at + len(expected)] = item[new].splitlines(keepends=True)
    return ''.join(lines)

def sources():
    texts, states = {}, []
    for name in ('source', 'caller'):
        item = MANIFEST[name]
        current = (ROOT / item['path']).read_text()
        if digest(current.encode()) == item['before_sha256']:
            before, installed = current, False
        elif digest(current.encode()) == item['after_sha256']:
            before, installed = apply(current, item['changes'], True), True
        else:
            raise ValueError('Unknown actor-effect ' + name + ' state')
        after = apply(before, item['changes'])
        if digest(before.encode()) != item['before_sha256'] or digest(after.encode()) != item['after_sha256']:
            raise ValueError('Actor-effect source fingerprint changed')
        texts[name] = (before, after)
        states.append(installed)
    if len(set(states)) != 1:
        raise ValueError('Actor-effect source and caller states differ')
    return texts, states[0]

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    for path, expected in MANIFEST['inputs'].items():
        if input_digest(path, (ROOT / path).read_bytes()) != expected:
            raise ValueError('Actor-effect input changed: ' + path)
    texts, installed = sources()
    for path, expected in MANIFEST['baseline'].items():
        dest = OUT / 'frozen' / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            if installed or digest((ROOT / path).read_bytes()) != expected:
                raise ValueError('Pre-install baseline missing: ' + path)
            shutil.copyfile(ROOT / path, dest)
        if digest(dest.read_bytes()) != expected:
            raise ValueError('Frozen baseline changed: ' + path)
    before, bd = compile_owner(ROOT, OUT, texts['source'][0], 'before')
    after, ad = compile_owner(ROOT, OUT, texts['source'][1], 'candidate-12')
    if same_functions(before, after, ('func_150B3AB0',)) != 1 or normalized_pools(before) != normalized_pools(after) or diagnostic_rows(bd) != diagnostic_rows(ad):
        raise ValueError('Actor-effect owner neighbors, pools or diagnostics changed')
    (OUT / 'caller-proposed.c').write_text(texts['caller'][1])
    symbols = {r[1]: r[2][1] for r in symbol_rows((OUT / 'frozen/conker/build/conker.us.elf').read_bytes())}
    truth = (ROOT / 'conker/conker.us.bin').read_bytes()[0xe0f60:0xe10bc]
    if struct.pack('>87I', *bound_blob(*payload(after, 'func_150B3AB0'), symbols)) != truth:
        raise ValueError('Actor-effect C body is not retail-exact')
    print('Actor-effect dispatch: 87 retail words, zero guards, one unchanged owner neighbor; installed=' + str(installed), flush=True)
    return texts, installed

if __name__ == '__main__':
    prepare()
