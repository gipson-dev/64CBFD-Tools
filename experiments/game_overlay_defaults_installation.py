"""Predict the complete overlay-reset successor before any production edit."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_overlay_defaults as source
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD = 'conker/build/game-overlay-defaults-install'
digest = lambda data: hashlib.sha256(data).hexdigest()
SERIALIZATION = ((('D_800A72B4','D_80099014','D_80090128','D_8009E974'), (1,2,3,0),
    ((0x800A72B4,0,16,0,65521),(0x80099014,0,16,0,65521),
     (0x80090128,0,16,0,65521),(0x8009E974,0,16,0,6))),)


def expected_inputs(root, out):
    before = (out/'before-elf').read_bytes()
    if digest(before) != source.BASELINE['elf']:
        raise ValueError('Changed overlay reset predecessor')
    row = next(row for row in symbol_rows(before) if row[1] == source.FUNCTION)
    if row[2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown overlay reset predecessor extent')
    data = bytearray(before)
    at = elf_slot_offset(before, source.ENTRY, source.SIZE)
    data[at:at+source.SIZE] = (out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I', data, row[0]+8, source.SIZE)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization, 'SERIALIZATION', SERIALIZATION):
        serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data), color_owner=source.recovered_owner((out/'before-color_owner').read_text()).encode())


def predict(root, out):
    source.freeze(root, out)
    _, padded, _, _ = source.qualify(root, out)
    live = lambda: {k:digest((root/p).read_bytes()) for k,p in source.PATHS.items()}
    capture = out/'link-inputs.json'
    if not capture.exists():
        if live() != source.BASELINE:
            raise ValueError('Overlay reset link capture must precede installation')
        for name,path in (('before-linkscript','conker/build/conker.ld'), ('before-owner.o','conker/build/src/game/'+source.OWNER+'.c.o')):
            (out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({n:digest((out/n).read_bytes()) for n in ('before-linkscript','before-owner.o')}, indent=2)+'\n')
    for name, value in json.loads(capture.read_text()).items():
        if digest((out/name).read_bytes()) != value:
            raise ValueError('Changed overlay reset link input')
    selector = 'build/src/game/'+source.OWNER+'.c.o(.text);'
    for label, obj in (('baseline',out/'before-owner.o'), ('prediction',padded)):
        script = (out/'before-linkscript').read_text()
        if script.count(selector) != 1:
            raise ValueError('Unknown overlay reset owner selector')
        script = script.replace(selector, str(obj.relative_to(root/'conker'))+'(.text);', 1)
        path = out/(label+'.ld')
        path.write_text(script)
        subprocess.run(['mips-linux-gnu-ld','-T',str(path.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
            '--no-check-sections','--no-warn-mismatch','-o',str((out/('prelink-'+label+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker', capture_output=True, check=True)
    if (out/'prelink-baseline.elf').read_bytes() != (out/'before-elf').read_bytes():
        raise ValueError('Overlay reset baseline image not reproduced')
    expected = expected_inputs(root, out)
    actual = (out/'prelink-prediction.elf').read_bytes()
    if actual != expected['elf']:
        raise ValueError('Unexpected complete overlay reset image difference')
    hashes = {k:digest(v) for k,v in expected.items()}
    initial = out/'initial-prediction.json'
    if not initial.exists():
        if live() != source.BASELINE:
            raise ValueError('First overlay reset prediction must precede source edit')
        initial.write_text(json.dumps(hashes, indent=2)+'\n')
    if json.loads(initial.read_text()) != hashes:
        raise ValueError('Changed first overlay reset prediction')
    before = (out/'before-elf').read_bytes()
    at = elf_slot_offset(actual, source.ENTRY, source.SIZE)
    total = sum(a != b for a,b in zip(before,actual))
    code = sum(a != b for a,b in zip(before[at:at+source.SIZE],actual[at:at+source.SIZE]))
    symbol = next(r for r in symbol_rows(before) if r[1] == source.FUNCTION)
    extent = sum(a != b for a,b in zip(before[symbol[0]+8:symbol[0]+12], actual[symbol[0]+8:symbol[0]+12]))
    row = dict(after=hashes, changed_ELF_bytes=total, code_bytes=code, extent_bytes=extent,
        metadata_bytes=total-code-extent, exact_symbol_groups=len(SERIALIZATION), metadata_exclusions=0, new_guards=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row, indent=2)+'\n')
    return row


def installation_patch(root, out):
    expected = expected_inputs(root, out)
    if json.loads((out/'initial-prediction.json').read_text()) != {k:digest(v) for k,v in expected.items()}:
        raise ValueError('Changed first overlay reset source prediction')
    path = root/source.PATHS['color_owner']
    before = path.read_bytes()
    if digest(before) != source.BASELINE['color_owner']:
        raise ValueError('Changed overlay reset source predecessor')
    diff = list(difflib.unified_diff(before.decode().splitlines(), expected['color_owner'].decode().splitlines(), n=3, lineterm=''))
    return '*** Begin Patch\n*** Update File: '+str(path)+'\n'+'\n'.join('@@' if s.startswith('@@') else s for s in diff[2:])+'\n*** End Patch\n'


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root, root/BUILD), indent=2), flush=True)
