"""Predict the entire direct-reveal image before editing the production owner."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_text_reveal_renderer as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-text-reveal-install'
SERIALIZATION=((('D_800D9ED8','D_80088AD8'),(1,0),
    ((0x800D9ED8,0,16,0,65521),(0x80088AD8,0,16,0,65521))),
    (('D_800A0880','D_80098B80'),(1,0),
    ((0x800A0880,0,16,0,65521),(0x80098B80,0,16,0,65521))))


def recovered_checkpoint(before):
    anchor='def previous_input(current,path,root):\n'
    freeze='        data=(root/path).read_bytes()\n'
    if before.count(anchor)!=1 or before.count(freeze)!=1:raise ValueError('Unknown constructor checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import text_reveal_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1).replace(freeze,freeze+
        '        from tools.tests import text_reveal_checkpoint as latest\n'
        '        data=latest.previous_input(data,path,root)\n',1)


def recovered_tests(before):
    cache='source.freeze(self.root,self.out);real=hashlib.sha256;cache={}'
    read='def altered(path):return wrong if path==target else cache[path]'
    live='            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)'
    if before.count(cache)!=1 or before.count(read)!=1 or before.count(live)!=2:
        raise ValueError('Unknown constructor test predecessor')
    return before.replace(cache,cache+';original_read=Path.read_bytes',1).replace(read,
        'def altered(path):return wrong if path==target else cache[path] if path in cache else original_read(path)',1).replace(live,
        '            from tools.tests import text_reveal_checkpoint as latest\n'
        '            self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),data)')


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:raise ValueError('Changed reveal predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown reveal placeholder extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,source.SIZE)
    data[at:at+source.SIZE]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I',data,row[0]+8,source.SIZE)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization,'SERIALIZATION',SERIALIZATION):
        serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data),tile_owner=source.recovered_owner((out/'before-tile_owner').read_text()).encode(),
        constructor_checkpoint=recovered_checkpoint((out/'before-constructor_checkpoint').read_text()).encode(),
        constructor_tests=recovered_tests((out/'before-constructor_tests').read_text()).encode())


def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'expected_inputs',expected_inputs),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        return shared.predict(root,out)


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first reveal prediction')
    parts=['*** Begin Patch']
    for key,data in expected.items():
        if key=='elf':continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=source.BASELINE[key]:raise ValueError('Changed reveal edit predecessor: '+key)
        rows=list(difflib.unified_diff(before.decode().splitlines(),data.decode().splitlines(),n=3,lineterm=''))
        parts.extend(['*** Update File: '+str(path),*('@@' if r.startswith('@@') else r for r in rows[2:])])
    return '\n'.join([*parts,'*** End Patch',''])


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
