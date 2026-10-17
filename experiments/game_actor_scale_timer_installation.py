"""Predict the complete guarded scale-timer image and exact historical adapters."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch
from tools.experiments import game_actor_scale_timer as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-actor-scale-timer-install'
SERIALIZATION=(
    (('D_8008CC0C','D_800A1260'),(1,0),((0x8008CC0C,0,16,0,65521),(0x800A1260,0,16,0,6))),
    (('D_800A1950','D_800A1580'),(1,0),((0x800A1950,0,16,0,65521),(0x800A1580,0,16,0,65521))),
)


def checkpoint_text(before):
    anchor='def previous_input(current,path,root):\n';freeze='        data=(root/path).read_bytes()\n'
    if before.count(anchor)!=1 or before.count(freeze)!=1:raise ValueError('Unknown threshold-mask checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import actor_scale_timer_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1).replace(freeze,freeze+
        '        from tools.tests import actor_scale_timer_checkpoint as latest\n'
        '        data=latest.previous_input(data,path,root)\n',1)


def recovery_text(before):
    anchor='        data=(root/path).read_bytes()\n'
    if before.count(anchor)!=1:raise ValueError('Unknown threshold-mask recovery predecessor')
    return before.replace(anchor,anchor+
        '        from tools.tests import actor_scale_timer_checkpoint as latest\n'
        '        data=latest.previous_input(data,path,root)\n',1)


def tests_text(before):
    anchor='    def test_06_caller_and_frozen_boundaries(self):\n'
    if before.count(anchor)!=1:raise ValueError('Unknown threshold-mask test predecessor')
    before=before.replace(anchor,
        '    def historical(self,path):\n'
        '        from tools.tests import actor_scale_timer_checkpoint as latest\n'
        '        return latest.previous_input((self.root/path).read_bytes(),path,self.root)\n\n'+anchor,1)
    for a,b in (
        ("(self.root/'conker/retail_word_patches.us.csv').read_bytes()","self.historical('conker/retail_word_patches.us.csv')"),
        ('self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)','self.assertEqual(self.historical(source.PATHS[key]),data)'),
        ("if path not in owned:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())",
         "if path not in owned:self.assertEqual(self.historical(path),(out/('before-'+key)).read_bytes())")):
        if before.count(a)!=1:raise ValueError('Unknown threshold-mask historical test anchor')
        before=before.replace(a,b,1)
    return before


def followup_text(before):
    anchor="if path not in owned:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())"
    if before.count(anchor)!=1:raise ValueError('Unknown actor-state historical guard-view predecessor')
    return before.replace(anchor,"if path not in owned:self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(out/('before-'+key)).read_bytes())",1)


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:raise ValueError('Changed scale-timer predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown scale-timer placeholder extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,source.SIZE)
    data[at:at+source.SIZE]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I',data,row[0]+8,source.SIZE)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization,'SERIALIZATION',SERIALIZATION):serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data),record_gate_owner=source.recovered_owner((out/'before-record_gate_owner').read_text()).encode(),
        guards=source.guard_text((out/'before-guards').read_bytes().decode()).encode(),
        threshold_mask_recovery=recovery_text((out/'before-threshold_mask_recovery').read_text()).encode(),
        threshold_mask_checkpoint=checkpoint_text((out/'before-threshold_mask_checkpoint').read_text()).encode(),
        threshold_mask_tests=tests_text((out/'before-threshold_mask_tests').read_text()).encode())


def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'expected_inputs',expected_inputs),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        result=shared.predict(root,out)
    result['new_guards']=2
    (out/'prelink-prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first scale-timer prediction')
    result=['*** Begin Patch']
    for key,data in expected.items():
        if key in ('elf','guards'):continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=source.BASELINE[key]:raise ValueError('Changed scale-timer edit predecessor: '+key)
        rows=list(difflib.unified_diff(before.decode().splitlines(),data.decode().splitlines(),n=3,lineterm=''))
        result.extend(['*** Update File: '+str(path),*('@@' if r.startswith('@@') else r for r in rows[2:])])
    return '\n'.join([*result,'*** End Patch',''])


def append_guards(root,out):
    expected=expected_inputs(root,out)['guards'];path=root/source.PATHS['guards'];before=path.read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['guards']:raise ValueError('Changed guard predecessor')
    if not expected.startswith(before):raise ValueError('Changed existing guard bytes or line endings')
    path.write_bytes(expected)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
