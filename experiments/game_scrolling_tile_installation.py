"""Reuse the exact complete-image predictor for a separate direct SDK leaf."""
import hashlib
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_scrolling_tile_windows as source
from tools.experiments import game_overlay_defaults_installation as shared
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD = 'conker/build/game-scrolling-tile-install'
SERIALIZATION = ()


def expected_inputs(root,out):
    before = (out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['elf']:
        raise ValueError('Changed scrolling tile predecessor')
    row = next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):
        raise ValueError('Unknown scrolling tile predecessor extent')
    data = bytearray(before)
    at = elf_slot_offset(before,source.ENTRY,source.SIZE)
    data[at:at+source.SIZE] = (out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+source.SIZE]
    struct.pack_into('>I',data,row[0]+8,source.SIZE)
    if SERIALIZATION:
        from tools.tests import test_game_actor_burst_packet_match as serialization
        with patch.object(serialization,'SERIALIZATION',SERIALIZATION):
            serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data),tile_owner=source.recovered_owner((out/'before-tile_owner').read_text()).encode())


def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'expected_inputs',expected_inputs),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        return shared.predict(root,out)


if __name__=='__main__':
    import json
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
