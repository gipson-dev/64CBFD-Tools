"""Predict the exact callback image, manifest and checkpoint successor before edits."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_link_event_callback as source
from tools.experiments import game_scrolling_tile_installation as shared

BUILD='conker/build/game-link-event-install'
SERIALIZATION=()


def expected_inputs(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        expected=shared.expected_inputs(root,out)
    expected['guards']=source.guard_bytes((out/'before-guards').read_bytes())
    expected['burst_checkpoint']=source.recovered_burst_checkpoint((out/'before-burst_checkpoint').read_text()).encode()
    return expected


def predict(root,out):
    with patch.object(shared.shared,'source',source),patch.object(shared.shared,'expected_inputs',expected_inputs),\
            patch.object(shared.shared,'SERIALIZATION',SERIALIZATION):
        result=shared.shared.predict(root,out)
    result['new_guards']=1
    (out/'prelink-prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
