"""Qualify both typed callers and predict the complete setup installation image."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_sequence_record_setup as source
from tools.experiments import game_sequence_record_setup_matching as fit
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import emit_padded_assembly
from tools import pad_c_object
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD = 'conker/build/game-sequence-record-setup-install'
EXTRA = dict(scene_caller_owner='conker/src/game/generated_20AE20.c',
    scene_caller_original='conker/asm/20AE20.s',
    event_caller_original='conker/asm/C98F0.s', other_caller_original='conker/asm/CDE80.s')
BASELINE = dict(source.BASELINE,
    scene_caller_owner='a26a822cd96123dd88fd7ea86eb7c53b9ed8d9716fb71e1d1e2dc2c5d599e5e9',
    scene_caller_original='b285f38871e2bc048fc6e576c20c731ce3dc743b8ccace0fac036b546daaa8c4',
    event_caller_original='f5f0a956ae9e416675f866fe42df021804dd29a324e287c5d0188472fbc96986',
    other_caller_original='95904fbecd5afa084a49b575c41494f0e275754359e2eefc3e1068d5efc15ec1')
PATHS = dict(source.PATHS, **EXTRA)
PROTOTYPE = 'void func_1501D348(s32 scene, s32 sequence, s32 slot, s32 hook, s32 parameter);\n'
CALLERS = (('view_init_caller_owner', 'game_34F20', None, 'void func_1501D044(s32 slot);\n'),
    ('scene_caller_owner', 'generated_20AE20', 'scene_caller_original', 'void func_151DE85C(void);\n'))
SERIALIZATION = (
    (('D_80097F54', 'D_800A1A24'), (1, 0), ((2148106068, 0, 16, 0, 6), (2148145700, 0, 16, 0, 6))),
    (('D_800C3C98', '.L1509DB94_game_data'), (1, 0), ((2148285592, 0, 16, 0, 65521), (352967572, 0, 16, 0, 5))),
    (('D_800C3C9A', 'D_800A13CC', 'D_800970DC'), (1, 2, 0),
        ((2148285594, 0, 16, 0, 65521), (2148144076, 0, 16, 0, 65521), (2148102364, 0, 16, 0, 65521))),
    (('D_800C3A50', 'D_800ABA24'), (1, 0), ((2148285008, 0, 16, 0, 65521), (2148186660, 0, 16, 0, 65521))),
    (('D_800D9B68', 'D_80088B38'), (1, 0), ((2148375400, 0, 16, 0, 65521), (2148043576, 0, 16, 0, 65521))),
    (('func_1519F3B8', 'D_80088B30'), (1, 0), ((354022328, 72, 18, 0, 5), (2148043568, 0, 16, 0, 65521))),
    (('D_87B', 'D_80088B34'), (1, 0), ((2171, 0, 16, 0, 65521), (2148043572, 0, 16, 0, 65521))),
)


def digest(data): return hashlib.sha256(data).hexdigest()


def freeze(root, out):
    source.freeze(root, out)
    for key, relative in EXTRA.items():
        data = (root / relative).read_bytes()
        if digest(data) != BASELINE[key]:
            from tools.tests import sequence_record_setup_checkpoint as checkpoint
            data = checkpoint.previous_input(data, relative, root)
        if digest(data) != BASELINE[key]: raise ValueError('Unknown setup installation input: ' + key)
        target = out / ('before-' + key)
        if not target.exists(): target.write_bytes(data)
        if target.read_bytes() != data: raise ValueError('Changed setup installation fixture: ' + key)


def recovered_caller(before, marker):
    if before.count(marker) != 1 or PROTOTYPE in before: raise ValueError('Unknown setup caller declarations')
    return before.replace(marker, marker + PROTOTYPE, 1)


def qualify_callers(root, out):
    freeze(root, out); rows = []
    for key, owner, original, marker in CALLERS:
        before = (out / ('before-' + key)).read_text(); objects = []; padded = []; warnings = []
        for stage, text in (('before', before), ('after', recovered_caller(before, marker))):
            obj, diagnostics = source.compile_owner(root, out, text, key + '-' + stage)
            warnings.append(re.sub(r'build/[^,]+\.c, line \d+', 'caller.c', diagnostics))
            objects.append(obj); script = out / (key + '-' + stage + '-padded.s')
            emitted = emit_padded_assembly(obj, out / ('before-' + original),
                word_patches_path=out / 'before-guards', filename=owner) if original else pad_c_object.emit_padded_assembly(
                    obj, out / 'before-layout', owner, word_patches_path=out / 'before-guards')
            script.write_text(emitted); path = script.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path), str(script)], capture_output=True, check=True)
            padded.append(path)
        raw_count = same_functions(*objects, ()); padded_count = same_functions(*padded, ())
        if raw_count != padded_count: raise ValueError('Setup caller function set changed')
        if warnings[0] != warnings[1]: raise ValueError('Setup caller diagnostics changed')
        rows.append(dict(owner=owner, unchanged_raw_functions=raw_count, unchanged_padded_functions=padded_count,
            unchanged_diagnostics=warnings[0]))
    (out / 'typed-callers.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def expected_inputs(root, out):
    before = (out / 'before-elf').read_bytes()
    if digest(before) != BASELINE['elf']: raise ValueError('Changed setup predecessor image')
    row = next(r for r in symbol_rows(before) if r[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12): raise ValueError('Unknown setup predecessor extent')
    data = bytearray(before); at = elf_slot_offset(before, source.ENTRY, 1892)
    data[at:at + 1892] = (out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 1892]
    struct.pack_into('>I', data, row[0] + 8, 1892)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization, 'SERIALIZATION', SERIALIZATION): serialization.apply_burst_symbol_serialization(data)
    raw, bindings, _ = fit.parts(out / 'raw.o'); wanted, _, _ = fit.parts(out / 'original-setup-match.o')
    result = dict(elf=bytes(data),
        view_list_caller_owner=source.recovered_owner((out / 'before-view_list_caller_owner').read_text(), fit.SELECTED).encode(),
        guards=fit.guard_bytes((out / 'before-guards').read_bytes(), raw, bindings, wanted))
    for key, _, _, marker in CALLERS:
        result[key] = recovered_caller((out / ('before-' + key)).read_text(), marker).encode()
    return result


def prelink_prediction(root, out):
    freeze(root, out); _, padded, _, _, _ = fit.guarded(root, out); callers = qualify_callers(root, out)
    live = lambda:{k:digest((root / p).read_bytes()) for k, p in PATHS.items()}
    capture = out / 'link-inputs.json'
    owners = ('game/generated_49D30', 'game_34F20', 'game/generated_20AE20')
    captured = [('before-linkscript', 'conker/build/conker.ld')] + [
        ('before-link-%d.o' % i, 'conker/build/src/' + owner + '.c.o') for i, owner in enumerate(owners)]
    if not capture.exists():
        if live() != BASELINE: raise ValueError('Setup link capture must precede installation')
        for name, path in captured: (out / name).write_bytes((root / path).read_bytes())
        capture.write_text(json.dumps({n:digest((out / n).read_bytes()) for n, _ in captured}, indent=2) + '\n')
    for name, value in json.loads(capture.read_text()).items():
        if digest((out / name).read_bytes()) != value: raise ValueError('Changed setup link capture')
    for label, objects in (('baseline', [out / ('before-link-%d.o' % i) for i in range(3)]),
            ('prediction', [padded] + [out / (key + '-after-padded.o') for key, _, _, _ in CALLERS])):
        link = (out / 'before-linkscript').read_text()
        for owner, obj in zip(owners, objects):
            selector = 'build/src/' + owner + '.c.o(.text);'
            if link.count(selector) != 1: raise ValueError('Unknown setup link selector')
            link = link.replace(selector, str(obj.relative_to(root / 'conker')) + '(.text);', 1)
        script = out / (label + '.ld'); script.write_text(link)
        subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-' + label + '.elf')).relative_to(root / 'conker'))],
            cwd=root / 'conker', capture_output=True, check=True)
    if (out / 'prelink-baseline.elf').read_bytes() != (out / 'before-elf').read_bytes(): raise ValueError('Setup predecessor not reproduced')
    expected = expected_inputs(root, out); actual = (out / 'prelink-prediction.elf').read_bytes()
    if actual != expected['elf']: raise ValueError('Unpredicted setup ELF bytes: %d' % sum(a != b for a, b in zip(actual, expected['elf'])))
    hashes = {k:digest(v) for k, v in expected.items()}; initial = out / 'initial-prediction.json'
    if not initial.exists():
        if live() != BASELINE: raise ValueError('First setup prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2) + '\n')
    if json.loads(initial.read_text()) != hashes: raise ValueError('Changed first setup prediction')
    row = dict(after=hashes, callers=callers, changed_ELF_bytes=sum(a != b for a, b in zip((out / 'before-elf').read_bytes(), actual)),
        body_bytes=1892, new_guards=165, exact_symbol_groups=len(SERIALIZATION), metadata_exclusions=0)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2) + '\n'); return row


def installation_patch(root, out):
    expected = expected_inputs(root, out)
    if json.loads((out / 'initial-prediction.json').read_text()) != {k:digest(v) for k, v in expected.items()}:
        raise ValueError('Changed setup installation prediction')
    patches = []
    for key, after in expected.items():
        if key == 'elf': continue
        path = root / PATHS[key]; before = path.read_bytes()
        if digest(before) != BASELINE[key]: raise ValueError('Changed setup source/callers/guards')
        diff = list(difflib.unified_diff(before.decode().splitlines(), after.decode().splitlines(), n=3, lineterm=''))
        patches.append('*** Update File: ' + str(path) + '\n' + '\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n' + '\n'.join(patches) + '\n*** End Patch\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--prepare', action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.prepare: print(installation_patch(root, root / BUILD), end='')
    else: print(json.dumps(prelink_prediction(root, root / BUILD), indent=2), flush=True)
