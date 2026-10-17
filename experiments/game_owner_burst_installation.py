"""Predict the complete burst successor and exact historical checkpoint views."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_owner_burst_match as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-owner-burst-install'
SERIALIZATION=(
    (('D_800A196C','.L1509FC94_game_data'),(1,0),
        ((0x800A196C,0,16,0,65521),(0x1509FC94,0,16,0,5))),
    (('D_800A195C','D_800A158C'),(1,0),
        ((0x800A195C,0,16,0,65521),(0x800A158C,0,16,0,65521))),
    (('D_800DDE38','D_800A1248'),(1,0),
        ((0x800DDE38,0,16,0,65521),(0x800A1248,0,16,0,6))),
)


def replace_once(text,before,after):
    if text.count(before)!=1:raise ValueError('Changed burst installation anchor: '+before[:70])
    return text.replace(before,after,1)


def makefile_text(before):
    anchor='$(BUILD_DIR)/$(SRC_DIR)/game/generated_11F780.c.o: RETAIL_RODATA_SYMBOL := jtbl_800A192C\n'
    return replace_once(before,anchor,anchor+'$(BUILD_DIR)/$(SRC_DIR)/game/generated_11FF10.c.o: RETAIL_RODATA_SYMBOL := D_800A196C\n')


def recovery_text(before):
    anchor='        data=(root/path).read_bytes()\n'
    return replace_once(before,anchor,anchor+
        '        from tools.tests import owner_burst_checkpoint as latest\n'
        '        data=latest.previous_input(data,path,root)\n')


def checkpoint_text(before):
    anchor='def previous_input(current,path,root):\n'
    return replace_once(before,anchor,anchor+
        '    from tools.tests import owner_burst_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n')


def test_history(before,anchor):
    helper='    def historical(self,path):\n        from tools.tests import owner_burst_checkpoint as latest\n        return latest.previous_input((self.root/path).read_bytes(),path,self.root)\n\n'
    if before.count('(self.root/source.PATHS[key]).read_bytes()')==2:
        before=before.replace('(self.root/source.PATHS[key]).read_bytes()','self.historical(source.PATHS[key])')
        before=replace_once(before,'(self.root/path).read_bytes()','self.historical(path)')
    else:
        before=replace_once(before,"(self.root/'conker/build/conker.us.elf').read_bytes()","self.historical('conker/build/conker.us.elf')")
        before=replace_once(before,'(self.root/path).read_bytes()','self.historical(path)')
    return replace_once(before,anchor,helper+anchor)


def baseline_test_text(before,anchor):
    before=replace_once(before,anchor,anchor+'        from tools.tests import owner_burst_checkpoint as latest\n')
    return replace_once(before,'(self.root/path).read_bytes()',
        'latest.previous_input((self.root/path).read_bytes(),path,self.root)')


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:raise ValueError('Changed burst predecessor ELF')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown burst placeholder extent')
    image=bytearray(before);offset=elf_slot_offset(before,source.ENTRY,source.SIZE)
    image[offset:offset+source.SIZE]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I',image,row[0]+8,source.SIZE)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization,'SERIALIZATION',SERIALIZATION):serialization.apply_burst_symbol_serialization(image)
    _,body,types=source.form()
    with patch.object(source.source,'TYPE',types):owner=source.source.recovered_owner((out/'before-record_gate_owner').read_text(),body)
    read=lambda key:(out/('before-'+key)).read_text()
    return dict(elf=bytes(image),record_gate_owner=owner.encode(),
        guards=source.guard_text((out/'before-guards').read_bytes().decode()).encode(),
        makefile=makefile_text(read('makefile')).encode(),owner_burst_2d14_recovery=recovery_text(read('owner_burst_2d14_recovery')).encode(),
        scale_timer_checkpoint=checkpoint_text(read('scale_timer_checkpoint')).encode(),
        scale_timer_tests=test_history(read('scale_timer_tests'),'    def test_07_complete_first_image_and_historical_adapters(self):\n').encode(),
        owner_burst_2d14_tests=test_history(read('owner_burst_2d14_tests'),'    def test_05_production_image_inputs_and_callback_unchanged(self):\n').encode(),
        owner_burst_2d14_frame_tests=baseline_test_text(read('owner_burst_2d14_frame_tests'),'    def test_06_production_baseline_unchanged(self):\n').encode(),
        owner_burst_2d14_local_tests=baseline_test_text(read('owner_burst_2d14_local_tests'),'    def test_04_complete_production_baseline_unchanged(self):\n').encode())


def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'expected_inputs',expected_inputs),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        result=shared.predict(root,out)
    result['new_guards']=20
    (out/'prelink-prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first burst installation prediction')
    result=['*** Begin Patch']
    for key,data in expected.items():
        if key in ('elf','guards'):continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=source.BASELINE[key]:raise ValueError('Changed burst edit predecessor: '+key)
        rows=list(difflib.unified_diff(before.decode().splitlines(),data.decode().splitlines(),n=3,lineterm=''))
        result.extend(['*** Update File: '+str(path),*('@@' if r.startswith('@@') else r for r in rows[2:])])
    return '\n'.join([*result,'*** End Patch',''])


def append_guards(root,out):
    expected=expected_inputs(root,out)['guards'];path=root/source.PATHS['guards'];before=path.read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['guards'] or not expected.startswith(before):
        raise ValueError('Changed burst guard prefix')
    path.write_bytes(expected)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
