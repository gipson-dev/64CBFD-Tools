"""Freeze the independent complete child-motion image before installing anything."""
from pathlib import Path
from unittest.mock import patch
import json
from tools.experiments import game_transition_child_motion as source
from tools.experiments import game_scrolling_tile_installation as shared

BUILD='conker/build/game-transition-child-motion-install'
SERIALIZATION=()


def expected_inputs(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        expected=shared.expected_inputs(root,out)
    expected['guards']=source.guard_bytes((out/'before-guards').read_bytes())
    expected['burst_predecessor_screen']=source.recovered_predecessor_screen(
        (out/'before-burst_predecessor_screen').read_text()).encode()
    return expected


def predict(root,out):
    with patch.object(shared.shared,'source',source),patch.object(shared.shared,'expected_inputs',expected_inputs),\
            patch.object(shared.shared,'SERIALIZATION',SERIALIZATION):
        result=shared.shared.predict(root,out)
    result['new_guards']=10
    (out/'prelink-prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
