"""Freeze and independently predict the complete reset/caller source and image successor."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_sequence_state_reset as source
from tools.experiments import game_sequence_state_reset_match as fit
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

SERIALIZATION = (
    (('D_8008630C', 'D_800890C0'), (1, 0),
        ((0x8008630C, 0, 16, 0, 65521), (0x800890C0, 0, 16, 0, 6))),
    (('D_800A48C8', 'D_800A03C8', 'D_80089234'), (2, 0, 1),
        ((0x800A48C8, 0, 16, 0, 65521), (0x800A03C8, 0, 16, 0, 65521), (0x80089234, 0, 16, 0, 65521))),
    (('D_800C35C2', 'game_data_VRAM'), (1, 0),
        ((0x800C35C2, 0, 16, 0, 65521), (0x80082B20, 0, 16, 0, 6))),
    (('func_150F2518', 'D_80089180'), (1, 0),
        ((0x150F2518, 136, 18, 0, 5), (0x80089180, 0, 16, 0, 6))),
    (('D_800C3C8E', 'D_800A0BF0'), (1, 0),
        ((0x800C3C8E, 0, 16, 0, 65521), (0x800A0BF0, 0, 16, 0, 65521))),
    (('D_800C367C', 'D_800AAC30', 'D_8009CE20', 'D_800AA7D0', 'D_800A1320'), (1, 2, 3, 4, 0),
        ((0x800C367C, 0, 16, 0, 65521), (0x800AAC30, 0, 16, 0, 65521), (0x8009CE20, 0, 16, 0, 6),
         (0x800AA7D0, 0, 16, 0, 65521), (0x800A1320, 0, 16, 0, 65521))),
    (('D_800C3C9E', 'D_8008FE86'), (1, 0),
        ((0x800C3C9E, 0, 16, 0, 65521), (0x8008FE86, 0, 16, 0, 65521))),
    (('func_150AED4C', 'D_800891FC'), (1, 0),
        ((0x150AED4C, 80, 18, 0, 5), (0x800891FC, 0, 16, 0, 65521))),
    (('D_800C3A58', 'D_8000031C'), (1, 0),
        ((0x800C3A58, 0, 16, 0, 65521), (0x8000031C, 0, 16, 0, 65521))),
    (('D_800C35F8', '.L15098DF0_game_data'), (1, 0),
        ((0x800C35F8, 0, 16, 0, 65521), (0x15098DF0, 0, 16, 0, 5))),
)


def expected_inputs(root, out):
    before = (out / 'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest() != source.BASELINE['elf']: raise ValueError('Changed sequence reset predecessor image')
    row = next(r for r in symbol_rows(before) if r[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12): raise ValueError('Unknown sequence reset predecessor extent')
    data = bytearray(before); at = elf_slot_offset(before, source.ENTRY, 400)
    data[at:at + 400] = (out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 400]
    struct.pack_into('>I', data, row[0] + 8, 400)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization, 'SERIALIZATION', SERIALIZATION): serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data), view_list_caller_owner=source.recovered_owner((out / 'before-view_list_caller_owner').read_text()).encode(),
        view_init_caller_owner=source.recovered_caller((out / 'before-view_init_caller_owner').read_text()).encode(),
        guards=fit.recovered_guards((out / 'before-guards').read_bytes(), out / 'qualified.o', out / 'original-reset.o'))


def prelink_prediction(root, out):
    source.freeze(root, out); _, padded, _, _ = fit.qualify(root, out)
    live = lambda:{k:hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}
    capture = out / 'link-inputs.json'
    captured = (('before-linkscript', 'conker/build/conker.ld'), ('before-owner.o', 'conker/build/src/game/generated_49D30.c.o'),
        ('before-caller.o', 'conker/build/src/game_34F20.c.o'))
    if not capture.exists():
        if live() != source.BASELINE: raise ValueError('Reset link capture must precede installation')
        for name, path in captured: (out / name).write_bytes((root / path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out / n).read_bytes()).hexdigest() for n, _ in captured}, indent=2) + '\n')
    for name, digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest: raise ValueError('Changed reset link capture')
    for label, objects in (('baseline', (out / 'before-owner.o', out / 'before-caller.o')),
            ('prediction', (padded, out / 'caller-after-padded.o'))):
        link = (out / 'before-linkscript').read_text()
        for selector, obj in zip(('build/src/game/generated_49D30.c.o(.text);', 'build/src/game_34F20.c.o(.text);'), objects):
            if link.count(selector) != 1: raise ValueError('Unknown reset/caller link selector')
            link = link.replace(selector, str(obj.relative_to(root / 'conker')) + '(.text);', 1)
        script = out / (label + '.ld'); script.write_text(link)
        subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-' + label + '.elf')).relative_to(root / 'conker'))],
            cwd=root / 'conker', capture_output=True, check=True)
    if (out / 'prelink-baseline.elf').read_bytes() != (out / 'before-elf').read_bytes(): raise ValueError('Reset predecessor not reproduced')
    expected = expected_inputs(root, out); actual = (out / 'prelink-prediction.elf').read_bytes()
    if actual != expected['elf']: raise ValueError('Unpredicted reset ELF bytes: %d' % sum(a != b for a, b in zip(actual, expected['elf'])))
    hashes = {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}; initial = out / 'initial-prediction.json'
    if not initial.exists():
        if live() != source.BASELINE: raise ValueError('First reset prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2) + '\n')
    if json.loads(initial.read_text()) != hashes: raise ValueError('Changed first reset prediction')
    row = dict(after=hashes, changed_ELF_bytes=sum(a != b for a, b in zip((out / 'before-elf').read_bytes(), actual)),
        body_bytes=400, new_guards=13, exact_symbol_groups=len(SERIALIZATION), metadata_exclusions=0)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2) + '\n'); return row


def installation_patch(root, out):
    expected = expected_inputs(root, out)
    if json.loads((out / 'initial-prediction.json').read_text()) != {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}:
        raise ValueError('Changed sequence reset installation prediction')
    patches = []
    for key, after in expected.items():
        if key == 'elf': continue
        path = root / source.PATHS[key]; before = path.read_bytes()
        if hashlib.sha256(before).hexdigest() != source.BASELINE[key]: raise ValueError('Changed sequence reset source/caller/guards')
        diff = list(difflib.unified_diff(before.decode().splitlines(), after.decode().splitlines(), n=3, lineterm=''))
        patches.append('*** Update File: ' + str(path) + '\n' + '\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n' + '\n'.join(patches) + '\n*** End Patch\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--prepare', action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.prepare: print(installation_patch(root, root / source.BUILD), end='')
    else: print(json.dumps(prelink_prediction(root, root / source.BUILD), indent=2), flush=True)
