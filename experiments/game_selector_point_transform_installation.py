"""Predict selector-point source, table binding and exact historical adapters."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_selector_point_transform as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-selector-point-transform-install'
SERIALIZATION=(
    (('D_80041F00','D_80088A90'),(1,0),
        ((0x80041F00,0,16,0,65521),(0x80088A90,0,16,0,65521))),
    (('jtbl_800A192C','D_800A1180','D_800AAEB0','D_800A5480'),(1,2,3,0),
        ((0x800A192C,0,16,0,6),(0x800A1180,0,16,0,65521),
         (0x800AAEB0,0,16,0,65521),(0x800A5480,0,16,0,65521))),
    (('D_800A1920','D_800A1550'),(1,0),
        ((0x800A1920,0,16,0,65521),(0x800A1550,0,16,0,65521))))


def recovered_checkpoint(before):
    anchor='def previous_input(current,path,root):\n';freeze='        data=(root/path).read_bytes()\n'
    if before.count(anchor)!=1 or before.count(freeze)!=1:raise ValueError('Unknown fixed-sine checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import selector_point_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1).replace(freeze,freeze+
        '        from tools.tests import selector_point_checkpoint as latest\n'
        '        data=latest.previous_input(data,path,root)\n',1)


def recovered_fixed_tests(before):
    live='            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)'
    other="            if path not in owned:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())"
    if before.count(live)!=1 or before.count(other)!=1:raise ValueError('Unknown fixed-sine input audit')
    return before.replace(live,'            from tools.tests import selector_point_checkpoint as latest\n'
        '            self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),data)',1).replace(
        other,'            if path not in owned:\n'
        '                from tools.tests import selector_point_checkpoint as latest\n'
        "                self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(out/('before-'+key)).read_bytes())",1)


def recovered_phase_tests(before):
    anchor="            if key not in expected:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())"
    if before.count(anchor)!=1:raise ValueError('Unknown sine-phase unchanged-input audit')
    return before.replace(anchor,'            if key not in expected:\n'
        '                from tools.tests import selector_point_checkpoint as latest\n'
        "                self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(out/('before-'+key)).read_bytes())",1)


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:raise ValueError('Changed selector-point predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown selector-point placeholder extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,source.SIZE)
    data[at:at+source.SIZE]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I',data,row[0]+8,source.SIZE)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization,'SERIALIZATION',SERIALIZATION):serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data),fixed_owner=source.recovered_owner((out/'before-fixed_owner').read_text()).encode(),
        makefile=source.recovered_makefile((out/'before-makefile').read_text()).encode(),
        fixed_checkpoint=recovered_checkpoint((out/'before-fixed_checkpoint').read_text()).encode(),
        fixed_tests=recovered_fixed_tests((out/'before-fixed_tests').read_text()).encode(),
        phase_tests=recovered_phase_tests((out/'before-phase_tests').read_text()).encode())


def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'expected_inputs',expected_inputs),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        return shared.predict(root,out)


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first selector-point prediction')
    parts=['*** Begin Patch']
    for key,data in expected.items():
        if key=='elf':continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=source.BASELINE[key]:raise ValueError('Changed selector-point edit predecessor: '+key)
        rows=list(difflib.unified_diff(before.decode().splitlines(),data.decode().splitlines(),n=3,lineterm=''))
        parts.extend(['*** Update File: '+str(path),*('@@' if r.startswith('@@') else r for r in rows[2:])])
    return '\n'.join([*parts,'*** End Patch',''])


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
