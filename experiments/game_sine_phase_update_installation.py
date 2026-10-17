"""Predict the complete sine/phase image and strict prior-checkpoint adapters."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_sine_phase_update as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-sine-phase-update-install'
SERIALIZATION=()


def recovered_checkpoint(before):
    anchor='def previous_input(current,path,root):\n';freeze='        data=(root/path).read_bytes()\n'
    if before.count(anchor)!=1 or before.count(freeze)!=1:raise ValueError('Unknown motion checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import sine_phase_update_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1).replace(freeze,freeze+
        '        from tools.tests import sine_phase_update_checkpoint as latest\n'
        '        data=latest.previous_input(data,path,root)\n',1)


def recovered_tests(before):
    live='            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)'
    functions="load_elf_functions(str(self.root/source.PATHS['elf']),'mips-linux-gnu-objdump')"
    other="            if key not in expected:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())"
    if before.count(live)!=1 or before.count(functions)!=1 or before.count(other)!=1:
        raise ValueError('Unknown motion first-image audit')
    return before.replace(live,'            from tools.tests import sine_phase_update_checkpoint as latest\n'
        '            self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),data)',1).replace(
        functions,"load_elf_functions(str(out/'after-elf'),'mips-linux-gnu-objdump')",1).replace(other,
        '            if key not in expected:\n'
        '                from tools.tests import sine_phase_update_checkpoint as latest\n'
        "                self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(out/('before-'+key)).read_bytes())",1)


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:raise ValueError('Changed sine-phase predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown sine-phase placeholder extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,source.SIZE)
    data[at:at+source.SIZE]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I',data,row[0]+8,source.SIZE)
    if SERIALIZATION:
        from tools.tests import test_game_actor_burst_packet_match as serialization
        with patch.object(serialization,'SERIALIZATION',SERIALIZATION):serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data),phase_owner=source.recovered_owner((out/'before-phase_owner').read_text()).encode(),
        guards=source.recovered_guards((out/'before-guards').read_bytes()),
        motion_checkpoint=recovered_checkpoint((out/'before-motion_checkpoint').read_text()).encode(),
        motion_tests=recovered_tests((out/'before-motion_tests').read_text()).encode())


def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'expected_inputs',expected_inputs),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        row=shared.predict(root,out)
    row['new_guards']=1
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def compatibility_inputs(root,out):
    before=(out/'before-reveal_tests').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['reveal_tests']:
        raise ValueError('Changed sine-phase reveal compatibility predecessor')
    anchor="            if key not in expected:self.assertEqual((self.root/source.PATHS[key]).read_bytes(),(out/('before-'+key)).read_bytes())"
    text=before.decode()
    if text.count(anchor)!=1:raise ValueError('Unknown reveal unchanged-input gate')
    return dict(reveal_tests=text.replace(anchor,
        '            if key not in expected:\n'
        '                from tools.tests import sine_phase_update_checkpoint as latest\n'
        "                self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())",1).encode())


def predict_compatibility(root,out):
    expected=compatibility_inputs(root,out);hashes={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial=out/'initial-compatibility-prediction.json'
    if not initial.exists():
        if any(hashlib.sha256((root/source.PATHS[k]).read_bytes()).hexdigest()!=source.BASELINE[k] for k in expected):
            raise ValueError('First sine-phase compatibility prediction must precede edits')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first sine-phase compatibility prediction')
    return hashes


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first sine-phase prediction')
    predict_compatibility(root,out)
    expected.update(compatibility_inputs(root,out))
    parts=['*** Begin Patch']
    for key,data in expected.items():
        if key=='elf':continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=source.BASELINE[key]:raise ValueError('Changed sine-phase edit predecessor: '+key)
        rows=list(difflib.unified_diff(before.decode().splitlines(),data.decode().splitlines(),n=3,lineterm=''))
        parts.extend(['*** Update File: '+str(path),*('@@' if r.startswith('@@') else r for r in rows[2:])])
    return '\n'.join([*parts,'*** End Patch',''])


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
