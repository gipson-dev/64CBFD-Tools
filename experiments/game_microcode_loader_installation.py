"""Predict and install only the qualified microcode-loader source/guard successor."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_microcode_loader as source
from tools.experiments import game_microcode_loader_lifetimes as fit
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD = 'conker/build/game-microcode-loader-installation'
PATHS = dict(source.PATHS, startup_caller='conker/asm/nonmatchings/game_34F20/func_15007B3C.s')
BASELINE = dict(source.BASELINE, startup_caller='fbe6f895bfe7849d87ef1a8b9a32bdffaaa0b6c64032c99c2e919cce9345e422')
SERIALIZATION = ((('func_1518FC04', 'D_80089324'), (1, 0),
    ((0x1518FC04, 64, 18, 0, 5), (0x80089324, 0, 16, 0, 65521))),)


def freeze(root, out):
    source.freeze(root, out)
    key = 'startup_caller'; data = (root / PATHS[key]).read_bytes()
    if hashlib.sha256(data).hexdigest() != BASELINE[key]: raise ValueError('Unknown startup caller input')
    target = out / ('before-' + key)
    if not target.exists(): target.write_bytes(data)
    if target.read_bytes() != data: raise ValueError('Changed startup caller fixture')


def recovered_owner(before):
    _, body, declarations = next(fit.flat_forms())
    return source.recovered_owner(before, body).replace(source.DECLARATIONS, declarations)


def expected_inputs(root, out):
    before = (out / 'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']: raise ValueError('Changed microcode predecessor image')
    row = next(r for r in symbol_rows(before) if r[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12): raise ValueError('Unknown microcode predecessor extent')
    data = bytearray(before); at = elf_slot_offset(before, source.ENTRY, 388)
    data[at:at + 388] = (out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 388]
    struct.pack_into('>I', data, row[0] + 8, 388)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization, 'SERIALIZATION', SERIALIZATION):
        serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data), view_list_caller_owner=recovered_owner((out / 'before-view_list_caller_owner').read_text()).encode(),
        guards=fit.recovered_guards((out / 'before-guards').read_bytes(), out / 'qualified.o', out / 'original-loader.o'))


def prelink_prediction(root, out):
    freeze(root, out); _, padded, _, _ = fit.qualify(root, out)
    live = lambda:{k:hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()}
    capture = out / 'link-inputs.json'
    if not capture.exists():
        if live() != BASELINE: raise ValueError('Microcode link capture must precede installation')
        for name, path in (('before-linkscript', 'conker/build/conker.ld'),
                ('before-owner.o', 'conker/build/src/game/generated_49D30.c.o')):
            (out / name).write_bytes((root / path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out / n).read_bytes()).hexdigest()
            for n in ('before-linkscript', 'before-owner.o')}, indent=2) + '\n')
    for name, digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest: raise ValueError('Changed microcode link capture')
    for label, obj in (('baseline', out / 'before-owner.o'), ('prediction', padded)):
        link = (out / 'before-linkscript').read_text(); needle = 'build/src/game/generated_49D30.c.o(.text);'
        if link.count(needle) != 1: raise ValueError('Unknown microcode owner link selector')
        link = link.replace(needle, str(obj.relative_to(root / 'conker')) + '(.text);', 1)
        script = out / (label + '.ld'); script.write_text(link)
        subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-' + label + '.elf')).relative_to(root / 'conker'))],
            cwd=root / 'conker', capture_output=True, check=True)
    if (out / 'prelink-baseline.elf').read_bytes() != (out / 'before-elf').read_bytes():
        raise ValueError('Microcode predecessor image not reproduced')
    expected = expected_inputs(root, out); actual = (out / 'prelink-prediction.elf').read_bytes()
    if actual != expected['elf']: raise ValueError('Microcode link differs outside the first slot/extent/serialization prediction')
    hashes = {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}; initial = out / 'initial-prediction.json'
    if not initial.exists():
        if live() != BASELINE: raise ValueError('First microcode prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2) + '\n')
    if json.loads(initial.read_text()) != hashes: raise ValueError('Changed first microcode prediction')
    row = dict(after=hashes, changed_ELF_bytes=sum(a != b for a, b in zip((out / 'before-elf').read_bytes(), actual)),
        body_bytes=388, new_guards=23, exact_symbol_groups=len(SERIALIZATION), metadata_exclusions=0)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2) + '\n'); return row


def installation_patch(root, out):
    expected = expected_inputs(root, out)
    if json.loads((out / 'initial-prediction.json').read_text()) != {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}:
        raise ValueError('Changed microcode installation prediction')
    patches = []
    for key, after in expected.items():
        if key == 'elf': continue
        path = root / PATHS[key]; before = path.read_bytes()
        if hashlib.sha256(before).hexdigest() != BASELINE[key]: raise ValueError('Changed microcode source/guards before installation')
        diff = list(difflib.unified_diff(before.decode().splitlines(), after.decode().splitlines(), n=3, lineterm=''))
        patches.append('*** Update File: ' + str(path) + '\n' + '\n'.join(
            '@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n' + '\n'.join(patches) + '\n*** End Patch\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.prepare: print(installation_patch(root, root / BUILD), end='')
    else: print(json.dumps(prelink_prediction(root, root / BUILD), indent=2), flush=True)
