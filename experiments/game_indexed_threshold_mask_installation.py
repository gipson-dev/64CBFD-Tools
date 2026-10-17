"""Predict the full threshold-mask image and narrowly reverse historical inputs."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch
from tools.experiments import game_indexed_threshold_mask as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-indexed-threshold-mask-install'
SERIALIZATION=((('D_800A1E50','D_80097BF0','D_800A1278'),(2,0,1),
    ((0x800A1E50,0,16,0,65521),(0x80097BF0,0,16,0,6),(0x800A1278,0,16,0,6))),)


def checkpoint_text(before):
    anchor='def previous_input(current,path,root):\n';freeze='        data=(root/path).read_bytes()\n'
    if before.count(anchor)!=1 or before.count(freeze)!=1:raise ValueError('Unknown actor-state checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import indexed_threshold_mask_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1).replace(freeze,freeze+
        '        from tools.tests import indexed_threshold_mask_checkpoint as latest\n'
        '        data=latest.previous_input(data,path,root)\n',1)


def actor_tests_text(before):
    anchor='            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)'
    if before.count(anchor)!=1:raise ValueError('Unknown actor-state live-input audit')
    return before.replace(anchor,'            from tools.tests import indexed_threshold_mask_checkpoint as latest\n'
        '            self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),data)',1)


def gate_recovery_text(before):
    anchor='        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError(\'Changed record-gate live input: \'+key)'
    if before.count(anchor)!=1:raise ValueError('Unknown record-gate freeze predecessor')
    return before.replace(anchor,'        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:\n'
        '            from tools.tests import indexed_threshold_mask_checkpoint as latest\n'
        '            data=latest.previous_input(data,path,root)\n'+anchor,1)


def gate_tests_text(before):
    anchor="        for key,path in source.PATHS.items():self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+key)).read_bytes())"
    if before.count(anchor)!=1:raise ValueError('Unknown record-gate historical input audit')
    return before.replace(anchor,'        from tools.tests import indexed_threshold_mask_checkpoint as latest\n'
        "        for key,path in source.PATHS.items():self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(self.out/('before-'+key)).read_bytes())",1)


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:raise ValueError('Changed threshold-mask predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown threshold-mask placeholder extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,source.SIZE)
    data[at:at+source.SIZE]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I',data,row[0]+8,source.SIZE)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization,'SERIALIZATION',SERIALIZATION):serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data),record_gate_owner=source.recovered_owner((out/'before-record_gate_owner').read_text()).encode(),
        actor_state_checkpoint=checkpoint_text((out/'before-actor_state_checkpoint').read_text()).encode(),
        actor_state_tests=actor_tests_text((out/'before-actor_state_tests').read_text()).encode(),
        record_gate_recovery=gate_recovery_text((out/'before-record_gate_recovery').read_text()).encode(),
        record_gate_tests=gate_tests_text((out/'before-record_gate_tests').read_text()).encode())


def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'expected_inputs',expected_inputs),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        return shared.predict(root,out)


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first threshold-mask prediction')
    result=['*** Begin Patch']
    for key,data in expected.items():
        if key=='elf':continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=source.BASELINE[key]:raise ValueError('Changed threshold-mask edit predecessor: '+key)
        rows=list(difflib.unified_diff(before.decode().splitlines(),data.decode().splitlines(),n=3,lineterm=''))
        result.extend(['*** Update File: '+str(path),*('@@' if r.startswith('@@') else r for r in rows[2:])])
    return '\n'.join([*result,'*** End Patch',''])


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
