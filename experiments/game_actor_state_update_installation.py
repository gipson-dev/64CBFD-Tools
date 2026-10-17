"""Freeze the complete two-function image before actor-state installation."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_actor_state_update as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-actor-state-update-install'
SERIALIZATION=()

def recovered_checkpoint(before):
    anchor='def previous_input(current,path,root):\n';freeze='        data=(root/path).read_bytes()\n'
    if before.count(anchor)!=1 or before.count(freeze)!=1:raise ValueError('Unknown halfword-point checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import actor_state_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1).replace(freeze,freeze+
        '        from tools.tests import actor_state_checkpoint as latest\n'
        '        data=latest.previous_input(data,path,root)\n',1)

def recovered_tests(before):
    anchor='            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)'
    if before.count(anchor)!=1:raise ValueError('Unknown halfword-point live input audit')
    return before.replace(anchor,'            from tools.tests import actor_state_checkpoint as latest\n'
        '            self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),data)',1)

def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:raise ValueError('Changed actor-state predecessor image')
    rows=symbol_rows(before);data=bytearray(before)
    for name,(entry,rom,size) in source.TARGETS.items():
        row=next(r for r in rows if r[1]==name)
        if row[2][1:3]!=(entry,12):raise ValueError('Unknown actor-state placeholder extent: '+name)
        at=elf_slot_offset(before,entry,size)
        data[at:at+size]=(out/'before-retail_rom').read_bytes()[rom:rom+size]
        struct.pack_into('>I',data,row[0]+8,size)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization,'SERIALIZATION',SERIALIZATION):serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data),fixed_owner=source.recovered_owner((out/'before-fixed_owner').read_text()).encode(),
        halfword_checkpoint=recovered_checkpoint((out/'before-halfword_checkpoint').read_text()).encode(),
        halfword_tests=recovered_tests((out/'before-halfword_tests').read_text()).encode())

def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'expected_inputs',expected_inputs),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        row=shared.predict(root,out)
    before=(out/'before-elf').read_bytes();after=expected_inputs(root,out)['elf'];code=extent=0
    for name,(entry,_,size) in source.TARGETS.items():
        at=elf_slot_offset(before,entry,size);symbol=next(r for r in symbol_rows(before) if r[1]==name)
        code+=sum(a!=b for a,b in zip(before[at:at+size],after[at:at+size]))
        extent+=sum(a!=b for a,b in zip(before[symbol[0]+8:symbol[0]+12],after[symbol[0]+8:symbol[0]+12]))
    row.update(code_bytes=code,extent_bytes=extent,metadata_bytes=row['changed_ELF_bytes']-code-extent,restored_functions=2)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row

def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first actor-state prediction')
    parts=['*** Begin Patch']
    for key,data in expected.items():
        if key=='elf':continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=source.BASELINE[key]:raise ValueError('Changed actor-state edit predecessor: '+key)
        rows=list(difflib.unified_diff(before.decode().splitlines(),data.decode().splitlines(),n=3,lineterm=''))
        parts.extend(['*** Update File: '+str(path),*('@@' if r.startswith('@@') else r for r in rows[2:])])
    return '\n'.join([*parts,'*** End Patch',''])

if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
