"""Private ordered-FP candidate; not an installed or byte-matching routine."""
from pathlib import Path
import hashlib
import json
import os
import struct
from tools.experiments import game_strip_update_151ad174_private_recovery as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools

ROOT = source.ROOT
PACKET = source.PACKET
NAME = source.NAME
QUALIFICATION = PACKET / 'ordered-final-v2'
FROZEN = PACKET / 'ordered-final-v2-baseline'
OUT = Path(os.environ.get('CBFD_STRIP_UPDATE_ORDERED_WORK', str(QUALIFICATION / 'qualification-primary')))
assert OUT.resolve().is_relative_to((ROOT / 'conker/build').resolve())
PIN = json.loads(Path(__file__).with_name('game_strip_update_151ad174_ordered_manifest.json').read_text())


def check_inputs():
    inputs = json.loads((FROZEN / 'fingerprints.json').read_text())['inputs']
    assert len(inputs) == PIN['frozen_input_count']
    for name, digest in inputs.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    assert source.STUB in (ROOT / source.SOURCE).read_text()
    return len(inputs)


def compile_and_check():
    check_inputs()
    OUT.mkdir(exist_ok=False)
    before = (source.FROZEN / source.SOURCE).read_text()
    baseline, diagnostics = source.compile_owner(ROOT, OUT, before, 'baseline')
    assert not diagnostics
    owner, diagnostics = source.compile_owner(ROOT, OUT, source.recover(before, PIN['body']), 'owner')
    assert not diagnostics
    raw, refs = payload(owner, NAME)
    assert len(raw) == 1964 and hashlib.sha256(raw).hexdigest() == PIN['raw_sha256']
    assert struct.unpack_from('>I', raw)[0] == 0x27BDFCF8
    assert refs == {int(k): [tuple(v) for v in rows] for k, rows in PIN['refs'].items()}
    assert same_functions(baseline, owner, (NAME,)) == 32
    assert normalized_pools(baseline) == normalized_pools(owner)
    truth = (source.FROZEN / 'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM + source.SIZE]
    assert hashlib.sha256(truth).hexdigest() == source.PIN['retail_sha256']
    for name, data in [('raw.bin', raw), ('retail.bin', truth)]:
        (OUT / name).write_bytes(data)
    (OUT / 'body.txt').write_text(PIN['body'])
    report = dict(raw_words=491, retail_words=494, frame=776, neighbors=32,
                  pools_unchanged=True, source_installed=False, c_match_credit=0)
    (OUT / 'source-report.json').write_text(json.dumps(report, indent=2) + '\n')
    check_inputs()
    return report
