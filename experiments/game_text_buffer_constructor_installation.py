"""Predict the full constructor image and reversible historical-fixture adapters."""
import hashlib
import difflib
import json
from pathlib import Path
import struct
from unittest.mock import patch
from tools.experiments import game_text_buffer_constructor as source
from tools.experiments import game_scrolling_tile_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-text-buffer-constructor-install'
SERIALIZATION=()


def recovered_link_checkpoint(before):
    anchor='def previous_input(current,path,root):\n'
    if before.count(anchor)!=1:raise ValueError('Unknown link checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import text_buffer_constructor_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1)


def recovered_fade_source(before):
    anchor="        data=(root/path).read_bytes()\n        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed dual-buffer live input: '+key)"
    if before.count(anchor)!=1:raise ValueError('Unknown fade fixture predecessor')
    return before.replace(anchor,"        data=(root/path).read_bytes()\n"
        "        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:\n"
        "            from tools.tests import text_buffer_constructor_checkpoint as latest\n"
        "            data=latest.previous_input(data,path,root)\n"
        "        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed dual-buffer live input: '+key)",1)


def recovered_fixture_test(before):
    anchor='source.freeze(self.root,self.out);real=hashlib.sha256;cache={}'
    read='def read_bytes(path):return wrong if path==target else cache[path]'
    if before.count(anchor)!=1 or before.count(read)!=1:raise ValueError('Unknown historical fixture cache')
    return before.replace(anchor,anchor+';original_read=Path.read_bytes',1).replace(read,
        'def read_bytes(path):return wrong if path==target else cache[path] if path in cache else original_read(path)',1)


def compatibility_inputs(root,out):
    return {key:recovered_fixture_test((out/('before-'+key)).read_text()).encode() for key in ('fade_tests','link_tests')}


def predict_compatibility(root,out):
    expected=compatibility_inputs(root,out);hashes={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial=out/'initial-compatibility-prediction.json'
    if not initial.exists():
        if any(hashlib.sha256((root/source.PATHS[k]).read_bytes()).hexdigest()!=source.BASELINE[k] for k in expected):
            raise ValueError('Fixture cache prediction must precede edits')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first fixture-cache prediction')
    return hashes


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:raise ValueError('Changed constructor predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,28):raise ValueError('Unknown typed constructor placeholder extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,source.SIZE)
    data[at:at+source.SIZE]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I',data,row[0]+8,source.SIZE)
    expected=dict(elf=bytes(data),tile_owner=source.recovered_owner((out/'before-tile_owner').read_text()).encode())
    expected['guards']=source.guard_bytes((out/'before-guards').read_bytes())
    expected['link_checkpoint']=recovered_link_checkpoint((out/'before-link_checkpoint').read_text()).encode()
    expected['fade_source']=recovered_fade_source((out/'before-fade_source').read_text()).encode()
    return expected


def predict(root,out):
    with patch.object(shared.shared,'source',source),patch.object(shared.shared,'expected_inputs',expected_inputs),\
            patch.object(shared.shared,'SERIALIZATION',SERIALIZATION):
        result=shared.shared.predict(root,out)
    result['new_guards']=12
    result['compatibility_after']=predict_compatibility(root,out)
    (out/'prelink-prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first constructor prediction')
    compatibility=compatibility_inputs(root,out)
    if predict_compatibility(root,out)!={k:hashlib.sha256(v).hexdigest() for k,v in compatibility.items()}:
        raise ValueError('Changed fixture-cache prediction')
    expected.update(compatibility);parts=['*** Begin Patch']
    for key,data in expected.items():
        if key=='elf':continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=source.BASELINE[key]:raise ValueError('Changed constructor edit predecessor: '+key)
        rows=list(difflib.unified_diff(before.decode().splitlines(),data.decode().splitlines(),n=3,lineterm=''))
        parts.extend(['*** Update File: '+str(path),*('@@' if r.startswith('@@') else r for r in rows[2:])])
    return '\n'.join([*parts,'*** End Patch',''])


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
