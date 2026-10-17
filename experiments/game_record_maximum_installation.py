"""Predict the whole record-maximum image before changing production inputs."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_record_maximum_scan as source
from tools.experiments import game_record_maximum_match as fit
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

SERIALIZATION = ((('D_800C35D0', '.L15099274_game_data', 'D_800A8D98'), (1, 2, 0),
    ((0x800C35D0, 0, 16, 0, 65521), (0x15099274, 0, 16, 0, 5), (0x800A8D98, 0, 16, 0, 65521))),)


def expected_inputs(root, out):
    before = (out / 'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']: raise ValueError('Changed record maximum predecessor image')
    row = next(r for r in symbol_rows(before) if r[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12): raise ValueError('Unknown record maximum predecessor extent')
    data = bytearray(before); at = elf_slot_offset(before, source.ENTRY, 420)
    data[at:at + 420] = (out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 420]
    struct.pack_into('>I', data, row[0] + 8, 420)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization, 'SERIALIZATION', SERIALIZATION): serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data), view_list_caller_owner=source.recovered_owner((out / 'before-view_list_caller_owner').read_text()).encode(),
        guards=fit.recovered_guards((out / 'before-guards').read_bytes(), out / 'qualified.o', out / 'original-maximum.o'))


def prelink_prediction(root, out):
    source.freeze(root, out); _, padded, _, _ = fit.qualify(root, out)
    live = lambda:{k:hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}
    capture = out / 'link-inputs.json'
    if not capture.exists():
        if live() != source.BASELINE: raise ValueError('Link capture must precede installation')
        for name, path in (('before-linkscript', 'conker/build/conker.ld'), ('before-owner.o', 'conker/build/src/game/generated_49D30.c.o')):
            (out / name).write_bytes((root / path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out / n).read_bytes()).hexdigest()
            for n in ('before-linkscript', 'before-owner.o')}, indent=2) + '\n')
    for name, digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest: raise ValueError('Changed maximum link capture')
    for label, obj in (('baseline', out / 'before-owner.o'), ('prediction', padded)):
        link = (out / 'before-linkscript').read_text(); needle = 'build/src/game/generated_49D30.c.o(.text);'
        if link.count(needle) != 1: raise ValueError('Unknown record maximum owner selector')
        script = out / (label + '.ld'); script.write_text(link.replace(needle, str(obj.relative_to(root / 'conker')) + '(.text);', 1))
        subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-' + label + '.elf')).relative_to(root / 'conker'))],
            cwd=root / 'conker', capture_output=True, check=True)
    if (out / 'prelink-baseline.elf').read_bytes() != (out / 'before-elf').read_bytes(): raise ValueError('Maximum predecessor not reproduced')
    expected = expected_inputs(root, out); actual = (out / 'prelink-prediction.elf').read_bytes()
    if actual != expected['elf']:
        raise ValueError('Unpredicted maximum ELF bytes: %d' % sum(a != b for a, b in zip(actual, expected['elf'])))
    hashes = {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}; initial = out / 'initial-prediction.json'
    if not initial.exists():
        if live() != source.BASELINE: raise ValueError('First maximum prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2) + '\n')
    if json.loads(initial.read_text()) != hashes: raise ValueError('Changed first maximum prediction')
    row = dict(after=hashes, changed_ELF_bytes=sum(a != b for a, b in zip((out / 'before-elf').read_bytes(), actual)),
        body_bytes=420, new_guards=48, exact_symbol_groups=len(SERIALIZATION), metadata_exclusions=0)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2) + '\n'); return row


def installation_patch(root, out):
    expected = expected_inputs(root, out)
    if json.loads((out / 'initial-prediction.json').read_text()) != {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}:
        raise ValueError('Changed record maximum installation prediction')
    patches = []
    for key, after in expected.items():
        if key == 'elf': continue
        path = root / source.PATHS[key]; before = path.read_bytes()
        if hashlib.sha256(before).hexdigest() != source.BASELINE[key]: raise ValueError('Changed maximum source/guards before installation')
        diff = list(difflib.unified_diff(before.decode().splitlines(), after.decode().splitlines(), n=3, lineterm=''))
        patches.append('*** Update File: ' + str(path) + '\n' + '\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n' + '\n'.join(patches) + '\n*** End Patch\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--prepare', action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.prepare: print(installation_patch(root, root / source.BUILD), end='')
    else: print(json.dumps(prelink_prediction(root, root / source.BUILD), indent=2), flush=True)
