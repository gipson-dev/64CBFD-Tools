"""Predict the complete actor-update image and exact archived-fixture adapters."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_actor_counter_motion as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-actor-counter-motion-install'
SERIALIZATION=((('D_8009FDDC','D_800CC264','D_800A0A0C'),(1,2,0),
    ((0x8009FDDC,0,16,0,65521),(0x800CC264,0,16,0,65521),(0x800A0A0C,0,16,0,65521))),
    (('D_8009FDD4','D_800A0A04'),(1,0),
    ((0x8009FDD4,0,16,0,65521),(0x800A0A04,0,16,0,65521))),
    (('D_8009FDD8','D_800A0A08'),(1,0),
    ((0x8009FDD8,0,16,0,65521),(0x800A0A08,0,16,0,65521))))


def recovered_checkpoint(before):
    anchor='def previous_input(current,path,root):\n';freeze='        data=(root/path).read_bytes()\n'
    if before.count(anchor)!=1 or before.count(freeze)!=1:raise ValueError('Unknown reveal checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import actor_counter_motion_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1).replace(freeze,freeze+
        '        from tools.tests import actor_counter_motion_checkpoint as latest\n'
        '        data=latest.previous_input(data,path,root)\n',1)


def recovered_white_source(before):
    anchor="        data=(root/path).read_bytes()\n        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed white-fade live input: '+key)"
    if before.count(anchor)!=1:raise ValueError('Unknown white-fade fixture predecessor')
    return before.replace(anchor,"        data=(root/path).read_bytes()\n"
        "        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:\n"
        "            from tools.tests import actor_counter_motion_checkpoint as latest\n"
        "            data=latest.previous_input(data,path,root)\n"
        "        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed white-fade live input: '+key)",1)


def recovered_white_tests(before):
    anchor="        for key,path in source.PATHS.items():self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+key)).read_bytes())"
    if before.count(anchor)!=1:raise ValueError('Unknown white-fade production audit')
    return before.replace(anchor,"        for key,path in source.PATHS.items():\n"
        "            from tools.tests import actor_counter_motion_checkpoint as latest\n"
        "            self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(self.out/('before-'+key)).read_bytes())",1)


def recovered_reveal_tests(before):
    live='            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)'
    functions="load_elf_functions(str(self.root/source.PATHS['elf']),'mips-linux-gnu-objdump')"
    if before.count(live)!=1 or before.count(functions)!=1:raise ValueError('Unknown reveal first-image audit')
    return before.replace(live,'            from tools.tests import actor_counter_motion_checkpoint as latest\n'
        '            self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),data)',1).replace(
        functions,"load_elf_functions(str(out/'after-elf'),'mips-linux-gnu-objdump')",1)


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:raise ValueError('Changed counter-motion predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown counter-motion placeholder extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,source.SIZE)
    data[at:at+source.SIZE]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I',data,row[0]+8,source.SIZE)
    if SERIALIZATION:
        from tools.tests import test_game_actor_burst_packet_match as serialization
        with patch.object(serialization,'SERIALIZATION',SERIALIZATION):serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data),motion_owner=source.recovered_owner((out/'before-motion_owner').read_text()).encode(),
        reveal_checkpoint=recovered_checkpoint((out/'before-reveal_checkpoint').read_text()).encode(),
        white_source=recovered_white_source((out/'before-white_source').read_text()).encode(),
        white_tests=recovered_white_tests((out/'before-white_tests').read_text()).encode(),
        reveal_tests=recovered_reveal_tests((out/'before-reveal_tests').read_text()).encode())


def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'expected_inputs',expected_inputs),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        return shared.predict(root,out)


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first counter-motion prediction')
    parts=['*** Begin Patch']
    for key,data in expected.items():
        if key=='elf':continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=source.BASELINE[key]:raise ValueError('Changed counter-motion edit predecessor: '+key)
        rows=list(difflib.unified_diff(before.decode().splitlines(),data.decode().splitlines(),n=3,lineterm=''))
        parts.extend(['*** Update File: '+str(path),*('@@' if r.startswith('@@') else r for r in rows[2:])])
    return '\n'.join([*parts,'*** End Patch',''])


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
