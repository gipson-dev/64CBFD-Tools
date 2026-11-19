"""Private actor-burst semantic recovery; not an installed byte-exact match."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
PACKET = ROOT / 'conker/build/game-next-150bbb5c-private'
FROZEN = PACKET / 'baseline'
OUT = Path(os.environ.get('CBFD_ACTOR_BURST_150BBB5C_WORK', PACKET / 'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT / 'conker/build').resolve())
PIN = json.loads(Path(__file__).with_name('game_actor_burst_150bbb5c_manifest.json').read_text())
NAME = 'func_150BBB5C'
SOURCE = 'conker/src/game/generated_E8C10.c'
STUB = 's32 func_150BBB5C() {\n    return 0;\n}'
ENTRY, ROM, SIZE = 0x150BBB5C, 0xE900C, 2348
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def check_inputs():
    assert sha(FROZEN / 'fingerprints.json') == PIN['baseline_manifest_sha256']
    inputs = json.loads((FROZEN / 'fingerprints.json').read_text())['inputs']
    assert len(inputs) == PIN['frozen_inputs'] == 1859
    for name, digest in inputs.items():
        assert sha(ROOT / name) == digest, name
    assert (ROOT / SOURCE).read_bytes() == (FROZEN / SOURCE).read_bytes()
    return len(inputs)


def recover(before):
    assert before.count(STUB) == 1
    return before.replace(STUB, PIN['declarations'] + '\n' + PIN['body'])


def refs_from_json(rows):
    return {int(offset): [tuple(row) for row in entries] for offset, entries in rows.items()}


def qualify_source():
    check_inputs()
    OUT.mkdir(parents=True, exist_ok=False)
    before = (FROZEN / SOURCE).read_text()
    baseline, diagnostics = compile_owner(ROOT, OUT, before, 'baseline')
    assert not diagnostics, diagnostics
    candidate, diagnostics = compile_owner(ROOT, OUT, recover(before), 'owner')
    assert not diagnostics, diagnostics
    assert same_functions(baseline, candidate, (NAME,)) == 8
    assert normalized_pools(baseline) == normalized_pools(candidate)
    raw, refs = payload(candidate, NAME)
    assert hashlib.sha256(raw).hexdigest() == PIN['raw_sha256']
    assert refs == refs_from_json(PIN['refs'])
    assembly = (FROZEN / 'conker/asm/E8C10.s').read_text()
    fragment = 'glabel ' + NAME + '\n' + assembly.split('glabel ' + NAME + '\n')[1].split('endlabel ' + NAME)[0]
    path = OUT / 'original.s'
    path.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n' + fragment + '.size ' + NAME + ',.-' + NAME + '\n')
    run = subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300',
        '-mabi=32', '-I', 'include', '-o', str(path.with_suffix('.o')), str(path)],
        cwd=ROOT / 'conker', capture_output=True, text=True)
    assert run.returncode == 0 and not run.stderr, (run.stdout, run.stderr)
    truth, truth_refs = payload(path.with_suffix('.o'), NAME)
    assert hashlib.sha256(truth).hexdigest() == PIN['retail_unbound_sha256']
    assert truth_refs == refs_from_json(PIN['retail_refs'])
    words, retail = struct.unpack('>589I', raw), struct.unpack('>587I', truth)
    assert 65536 - (words[0] & 65535) == 624
    assert sum(left != right for left, right in zip(words, retail)) == 539
    assert any(word >> 16 == 0xAFB4 for word in words[:15])
    assert not any(word >> 16 == 0xAFB4 for word in retail[:15])
    report = dict(passes=True, raw_words=589, retail_words=587, raw_frame=624,
        retail_frame=624, overlapping_word_differences=539, unmatched_extra_words=2,
        raw_relocation_sites=len(refs), retail_relocation_sites=len(truth_refs),
        neighbors_unchanged=8, pools_unchanged=True, extra_saved_s4=True,
        guards=0, insertions=0, omissions=0, source_installed=False, c_match_credit=0)
    (OUT / 'source-report.json').write_text(json.dumps(report, indent=2) + '\n')
    state()
    check_inputs()
    return report


def lookup():
    return {name: fields[1] for _, name, fields, _ in symbol_rows((FROZEN / 'conker/build/conker.us.elf').read_bytes())}


def state():
    raw, refs = payload(OUT / 'owner.o', NAME)
    truth, truth_refs = payload(OUT / 'original.o', NAME)
    assert hashlib.sha256(raw).hexdigest() == PIN['raw_sha256']
    assert refs == refs_from_json(PIN['refs'])
    assert hashlib.sha256(truth).hexdigest() == PIN['retail_unbound_sha256']
    assert truth_refs == refs_from_json(PIN['retail_refs'])
    symbols = lookup()
    retail = bound_blob(truth, truth_refs, symbols)
    assert struct.pack('>587I', *retail) == (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
    return dict(raw=bound_blob(raw, refs, symbols), retail=retail)


def census():
    image = (FROZEN / 'conker/conker.us.bin').read_bytes()
    jal = 0x0C000000 | ((ENTRY >> 2) & 0x3FFFFFF)
    calls, pointers = [], []
    for offset in range(0, len(image)-3, 4):
        word = struct.unpack_from('>I', image, offset)[0]
        if word == jal: calls.append(offset)
        if word == ENTRY: pointers.append(offset)
    assert calls == [0xAAF7C] and not pointers
    caller = (FROZEN / 'conker/asm/nonmatchings/game_A9D90/func_1507D754.s').read_text()
    assert '/* AAF7C 1507DACC 0D42EED7 */' in caller
    assert '/* AAF88 1507DAD8 00001025 */' in caller
    report = dict(passes=True, aligned_jal_sites=calls, aligned_pointer_literals=pointers,
        original_caller_result_discarded=True, complete_caller_qualified=False)
    (OUT / 'census-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def controls():
    from tools.tests import game_actor_burst_150bbb5c_oracle as guest
    before = (FROZEN / SOURCE).read_text()
    cases = [guest.Case(seed, pattern, mutation, 0) for seed in (0,1,3,12,15)
        for pattern in range(4) for mutation in (0,1)]
    expected = [(case, guest.fixture(case)) for case in cases]
    expected = [(case, initial, guest.reference(initial, case)) for case, initial in expected]
    rows = []
    for label, old, new in PIN['negative_controls']:
        assert old in PIN['body'], label
        body = PIN['body'].replace(old, new)
        text = before.replace(STUB, PIN['declarations'] + '\n' + body)
        obj, diagnostics = compile_owner(ROOT, OUT, text, 'negative-' + label)
        assert not diagnostics, diagnostics
        assert same_functions(OUT / 'baseline.o', obj, (NAME,)) == 8
        assert normalized_pools(OUT / 'baseline.o') == normalized_pools(obj)
        raw, refs = payload(obj, NAME)
        words = bound_blob(raw, refs, lookup())
        witness = None
        for case, initial, wanted in expected:
            machine = guest.Oracle(words, initial, case).run()
            if (guest.public(machine.memory), machine.calls, machine.obs) != wanted:
                witness = case.__dict__
                break
        assert witness is not None, ('ineffective control', label)
        rows.append(dict(label=label, effective=True, witness=witness,
            raw_sha256=hashlib.sha256(raw).hexdigest()))
    report = dict(passes=True, effective_negatives=len(rows), controls=rows,
        source_installed=False, c_match_credit=0)
    (OUT / 'controls-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
