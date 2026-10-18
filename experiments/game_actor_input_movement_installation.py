"""Predict and audit the complete production movement successor before editing."""
import difflib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_recovery as recovery
from tools.experiments import game_actor_input_movement_tail_match as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols

BUILD = 'conker/build/game-actor-input-movement-install'
PATHS, BASELINE = dict(source.PATHS), dict(source.BASELINE)
for key, path, sha in (
    ('movement_install_predecessor', 'tools/experiments/game_actor_input_movement_tail_match.py',
     'c9623733dc7a4dd34c143008640221ffadbc8e79ed994b9dcaf8cd32372577f2'),
    ('movement_install_predecessor_tests', 'tools/tests/test_game_actor_input_movement_tail_match.py',
     'eca26546d3b1a61c878754acdd69ac8a7f47754dd2d511c47a5168d035b64d25'),
):
    if key in PATHS:
        raise ValueError('Duplicate movement installation predecessor')
    PATHS[key], BASELINE[key] = path, sha

digest = shared.digest
SERIALIZATION = (
    (('D_800A19B4', 'D_80097BB4'), (1, 0),
     ((0x800A19B4, 0, 16, 0, 65521), (0x80097BB4, 0, 16, 0, 6))),
    (('D_800A19B8', 'D_80097BB8'), (1, 0),
     ((0x800A19B8, 0, 16, 0, 65521), (0x80097BB8, 0, 16, 0, 6))),
    (('D_800A19B0', 'D_80097BB0'), (1, 0),
     ((0x800A19B0, 0, 16, 0, 65521), (0x80097BB0, 0, 16, 0, 6))),
    (('func_150FDB0C', 'D_800889C0'), (1, 0),
     ((0x150FDB0C, 148, 18, 0, 5), (0x800889C0, 0, 16, 0, 65521))),
    (('D_800A198C', 'D_80097B8C'), (1, 0),
     ((0x800A198C, 0, 16, 0, 65521), (0x80097B8C, 0, 16, 0, 6))),
    (('D_800A1994', 'D_80097FB4'), (1, 0),
     ((0x800A1994, 0, 16, 0, 65521), (0x80097FB4, 0, 16, 0, 6))),
    (('D_800A19BC', 'D_80097BBC', 'D_800A1E1C'), (1, 2, 0),
     ((0x800A19BC, 0, 16, 0, 65521), (0x80097BBC, 0, 16, 0, 6), (0x800A1E1C, 0, 16, 0, 65521))),
    (('D_800D136C', 'D_8008896C'), (1, 0),
     ((0x800D136C, 0, 16, 0, 65521), (0x8008896C, 0, 16, 0, 65521))),
    (('D_800A1990', 'D_80097B90'), (1, 0),
     ((0x800A1990, 0, 16, 0, 65521), (0x80097B90, 0, 16, 0, 6))),
    (('func_15177A94', 'func_15044658', 'D_800A11E8'), (2, 0, 1),
     ((0x15177A94, 12, 18, 0, 5), (0x15044658, 8, 18, 0, 5), (0x800A11E8, 0, 16, 0, 6))),
    (('D_800A19C8', 'func_1507B8F4', 'D_80097BC8'), (1, 2, 0),
     ((0x800A19C8, 0, 16, 0, 65521), (0x1507B8F4, 100, 18, 0, 5), (0x80097BC8, 0, 16, 0, 6))),
    (('D_800A19C0', 'D_800A15F0', 'D_80097BC0'), (1, 2, 0),
     ((0x800A19C0, 0, 16, 0, 65521), (0x800A15F0, 0, 16, 0, 65521), (0x80097BC0, 0, 16, 0, 6))),
    (('func_151635A8', 'D_800889A0'), (1, 0),
     ((0x151635A8, 88, 18, 0, 5), (0x800889A0, 0, 16, 0, 65521))),
    (('D_80088558', 'D_80088988'), (1, 0),
     ((0x80088558, 0, 16, 0, 65521), (0x80088988, 0, 16, 0, 65521))),
    (('D_800A199C', '.L150643A4_game_data', 'func_150AE280', 'D_80097B9C'), (1, 2, 3, 0),
     ((0x800A199C, 0, 16, 0, 65521), (0x150643A4, 0, 16, 0, 5),
      (0x150AE280, 12, 18, 0, 5), (0x80097B9C, 0, 16, 0, 6))),
    (('D_800A19A4', 'D_80097BA4', 'D_800A1E04'), (1, 2, 0),
     ((0x800A19A4, 0, 16, 0, 65521), (0x80097BA4, 0, 16, 0, 6), (0x800A1E04, 0, 16, 0, 65521))),
    (('D_800A19A8', 'D_80097BA8'), (1, 0),
     ((0x800A19A8, 0, 16, 0, 65521), (0x80097BA8, 0, 16, 0, 6))),
    (('func_1511F990', 'func_15108BC0', 'D_80088990'), (2, 0, 1),
     ((0x1511F990, 12, 18, 0, 5), (0x15108BC0, 120, 18, 0, 5), (0x80088990, 0, 16, 0, 65521))),
    (('D_800A19AC', 'func_1501B640', 'D_80097BAC'), (1, 2, 0),
     ((0x800A19AC, 0, 16, 0, 65521), (0x1501B640, 32, 18, 0, 5), (0x80097BAC, 0, 16, 0, 6))),
    (('D_800A1988', 'D_80097FA8', 'D_80097B88'), (1, 2, 0),
     ((0x800A1988, 0, 16, 0, 65521), (0x80097FA8, 0, 16, 0, 6), (0x80097B88, 0, 16, 0, 6))),
    (('D_800A19D4', 'D_800A1E34'), (1, 0),
     ((0x800A19D4, 0, 16, 0, 65521), (0x800A1E34, 0, 16, 0, 65521))),
    (('D_800A19D0', 'D_80097BD0'), (1, 0),
     ((0x800A19D0, 0, 16, 0, 65521), (0x80097BD0, 0, 16, 0, 6))),
)


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if digest(data) != BASELINE[key]:
            raise ValueError('Changed movement installation predecessor: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement installation first image: ' + key)


def capture(root, out):
    freeze(root, out)
    for name, path in (('before-linkscript', 'conker/build/conker.ld'),
                       ('before-owner.o', 'conker/build/src/game/generated_11FF10.c.o')):
        data = (root / path).read_bytes()
        target = out / name
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed movement installation link input: ' + name)
    manifest = {n: digest((out / n).read_bytes()) for n in ('before-linkscript', 'before-owner.o')}
    path = out / 'link-inputs.json'
    if not path.exists():
        path.write_text(json.dumps(manifest, indent=2) + '\n')
    if json.loads(path.read_text()) != manifest:
        raise ValueError('Changed first movement link capture')


def expected_inputs(root, out):
    before = (out / 'before-elf').read_bytes()
    if digest(before) != BASELINE['elf']:
        raise ValueError('Changed movement predecessor ELF')
    row = next(r for r in symbol_rows(before) if r[1] == recovery.FUNCTION)
    if row[2][1:3] != (recovery.ENTRY, 12):
        raise ValueError('Unknown movement predecessor symbol')
    expected = bytearray(before)
    offset = elf_slot_offset(before, recovery.ENTRY, recovery.SIZE)
    expected[offset:offset + recovery.SIZE] = (out / 'before-retail_rom').read_bytes()[recovery.ROM:recovery.ROM + recovery.SIZE]
    struct.pack_into('>I', expected, row[0] + 8, recovery.SIZE)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization, 'SERIALIZATION', SERIALIZATION):
        serialization.apply_burst_symbol_serialization(expected)
    owner = recovery.recovered_owner((out / 'before-record_gate_owner').read_text(), source.previous.previous.selected_body()).encode()
    if owner != (out / 'dataflow-423.c').read_bytes():
        raise ValueError('Movement successor differs from qualified owner')
    guards = (out / 'expected-tail-guards.csv').read_bytes()
    if not guards.startswith((out / 'before-guards').read_bytes()):
        raise ValueError('Movement guard extension changes prior rows')
    return dict(elf=bytes(expected), record_gate_owner=owner, guards=guards)


def predict(root, out):
    capture(root, out)
    _, padded, _, _, result = source.qualify(root, out)
    if result['normalized_differences'] or result['research_guards'] != 134:
        raise ValueError('Movement production candidate is not fully qualified')
    selector = 'build/src/game/generated_11FF10.c.o(.text);'
    for label, obj in (('baseline', out / 'before-owner.o'), ('prediction', padded)):
        script = (out / 'before-linkscript').read_text()
        if script.count(selector) != 1:
            raise ValueError('Unknown movement owner link selector')
        script = script.replace(selector, str(obj.relative_to(root / 'conker')) + '(.text);', 1)
        path = out / (label + '.ld')
        path.write_text(script)
        subprocess.run(['mips-linux-gnu-ld', '-T', str(path.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-' + label + '.elf')).relative_to(root / 'conker'))],
            cwd=root / 'conker', capture_output=True, check=True)
    before = (out / 'before-elf').read_bytes()
    if (out / 'prelink-baseline.elf').read_bytes() != before:
        raise ValueError('Movement baseline full link does not reproduce')
    expected = expected_inputs(root, out)
    actual = (out / 'prelink-prediction.elf').read_bytes()
    if actual != expected['elf']:
        row = dict(actual=digest(actual), expected=digest(expected['elf']),
                   differing_bytes=sum(a != b for a, b in zip(actual, expected['elf'])),
                   same_size=len(actual) == len(expected['elf']),
                   canonical_symbols_equal=canonical_symbols(actual) == canonical_symbols(expected['elf']))
        (out / 'unclosed-image-diagnostic.json').write_text(json.dumps(row, indent=2) + '\n')
        raise ValueError('Unclosed complete movement image difference: ' + repr(row))
    hashes = {k: digest(v) for k, v in expected.items()}
    manifest = out / 'initial-prediction.json'
    if not manifest.exists():
        manifest.write_text(json.dumps(hashes, indent=2) + '\n')
    if json.loads(manifest.read_text()) != hashes:
        raise ValueError('Changed first movement successor prediction')
    for key, data in expected.items():
        path = out / ('after-' + key)
        if not path.exists():
            path.write_bytes(data)
        if path.read_bytes() != data:
            raise ValueError('Changed immutable movement successor: ' + key)
    at = elf_slot_offset(before, recovery.ENTRY, recovery.SIZE)
    symbol = next(r for r in symbol_rows(before) if r[1] == recovery.FUNCTION)
    code = sum(a != b for a, b in zip(before[at:at + recovery.SIZE], actual[at:at + recovery.SIZE]))
    extent = sum(a != b for a, b in zip(before[symbol[0] + 8:symbol[0] + 12], actual[symbol[0] + 8:symbol[0] + 12]))
    total = sum(a != b for a, b in zip(before, actual))
    result = dict(after=hashes, changed_ELF_bytes=total, code_bytes=code, extent_bytes=extent,
                  metadata_bytes=total - code - extent, exact_symbol_groups=len(SERIALIZATION),
                  metadata_exclusions=0, new_guards=134, protected_entries=len(PATHS), protected_paths=len(set(PATHS.values())))
    (out / 'prelink-prediction.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def installation_patch(root, out):
    expected = expected_inputs(root, out)
    if json.loads((out / 'initial-prediction.json').read_text()) != {k: digest(v) for k, v in expected.items()}:
        raise ValueError('Changed movement installation prediction')
    lines = ['*** Begin Patch']
    for key in ('record_gate_owner',):
        path = root / PATHS[key]
        before = path.read_bytes()
        if digest(before) != BASELINE[key]:
            raise ValueError('Changed movement production edit predecessor: ' + key)
        diff = list(difflib.unified_diff(before.decode().splitlines(), expected[key].decode().splitlines(), n=3, lineterm=''))
        lines.extend(['*** Update File: ' + str(path), *('@@' if r.startswith('@@') else r for r in diff[2:])])
    return '\n'.join([*lines, '*** End Patch', ''])


def append_guards(root, out):
    expected = expected_inputs(root, out)['guards']
    path = root / PATHS['guards']
    before = path.read_bytes()
    if digest(before) != BASELINE['guards'] or not expected.startswith(before):
        raise ValueError('Changed movement guard prefix')
    if json.loads((out / 'initial-prediction.json').read_text())['guards'] != digest(expected):
        raise ValueError('Changed movement guard prediction')
    path.write_bytes(expected)


def audit(root, out):
    from tools.tests import movement_install_checkpoint as checkpoint
    from tools.match_progress import load_elf_functions
    from tools.check_game_data_layout import audit_layout
    checkpoint.verify(root, installed=True)
    expected = expected_inputs(root, out)
    for key, data in expected.items():
        if checkpoint.raw_read(root / PATHS[key]) != data:
            raise ValueError('Movement installed member differs from complete prediction: ' + key)
    production_object = root / 'conker/build/src/game/generated_11FF10.c.o'
    qualified = recovery.parts(out / 'tail-normalized-padded.o')
    if recovery.parts(production_object) != qualified:
        raise ValueError('Movement actual object bytes or relocations differ from qualified target')
    before = (out / 'before-elf').read_bytes()
    actual = checkpoint.raw_read(root / PATHS['elf'])
    old_functions, _, old_addresses = load_elf_functions(str(out / 'before-elf'), 'mips-linux-gnu-objdump')
    functions, _, addresses = load_elf_functions(str(root / PATHS['elf']), 'mips-linux-gnu-objdump')
    if old_addresses != addresses or set(old_functions) != set(functions):
        raise ValueError('Movement installation changes function addresses or membership')
    if [n for n in old_functions if old_functions[n] != functions[n]] != [recovery.FUNCTION]:
        raise ValueError('Movement installation changes an unrelated function body')
    old_symbols = [(n, (f[1], recovery.SIZE if n == recovery.FUNCTION else f[2], *f[3:]))
                   for _, n, f, _ in symbol_rows(before)]
    if sorted(old_symbols) != sorted((n, f[1:]) for _, n, f, _ in symbol_rows(actual)):
        raise ValueError('Movement installation changes unrelated named definitions')
    changed = set(checkpoint.PATHS.values())
    for key, path in PATHS.items():
        if path not in changed and (root / path).read_bytes() != (out / ('before-' + key)).read_bytes():
            raise ValueError('Movement installation changes protected predecessor: ' + key)
    data = audit_layout(root / PATHS['elf'], root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Movement installation changes Game data')
    target = elf_slot_offset(actual, recovery.ENTRY, recovery.SIZE)
    truth = (out / 'before-retail_rom').read_bytes()[recovery.ROM:recovery.ROM + recovery.SIZE]
    if actual[target:target + recovery.SIZE] != truth:
        raise ValueError('Movement installed slot differs from retail')
    callback = elf_slot_offset(actual, 0x80086068, 4)
    if struct.unpack_from('>I', actual, callback)[0] != recovery.ENTRY:
        raise ValueError('Movement callback slot changed')
    row = dict(installed=True, whole_first_ELF_exact=True, metadata_exclusions=0,
        compared_bodies=len(functions), only_target_changed=True, all_addresses_preserved=True,
        target_words=959, actual_target_object_identical=True,
        target_relocation_sites=len(qualified[1]), callback_slot='0x80086068', checkpoint_members=3,
        protected_entries=len(PATHS), protected_paths=len(set(PATHS.values())), game_data=data,
        successor_SHA=digest(actual))
    (out / 'installed-audit.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root, root / BUILD), indent=2))
