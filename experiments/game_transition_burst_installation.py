"""Freeze the exact whole-image/source/guards/rodata/checkpoint successor first."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_transition_burst_match as source
from tools.experiments import game_scrolling_tile_installation as shared

BUILD='conker/build/game-transition-burst-install'
SERIALIZATION=((('D_800A0860','D_800A0490','D_800A4990'),(1,2,0),
    ((0x800A0860,0,16,0,65521),(0x800A0490,0,16,0,65521),(0x800A4990,0,16,0,65521))),)


def expected_inputs(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        expected=shared.expected_inputs(root,out)
    expected['guards']=source.guard_bytes((out/'before-guards').read_bytes())
    expected['makefile']=source.recovered_makefile((out/'before-makefile').read_text()).encode()
    expected['child_checkpoint']=source.recovered_child_checkpoint((out/'before-child_checkpoint').read_text()).encode()
    return expected


def predict(root,out):
    with patch.object(shared.shared,'source',source),patch.object(shared.shared,'expected_inputs',expected_inputs),\
            patch.object(shared.shared,'SERIALIZATION',SERIALIZATION):
        result=shared.shared.predict(root,out)
    result['new_guards']=11
    (out/'prelink-prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
