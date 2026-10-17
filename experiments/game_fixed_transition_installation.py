"""First complete constructor image prediction using the qualified predictor."""
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_fixed_transition_constructor as source
from tools.experiments import game_scrolling_tile_installation as shared

BUILD = 'conker/build/game-fixed-transition-install'
SERIALIZATION = ()


def expected_inputs(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        return shared.expected_inputs(root,out)


def predict(root,out):
    with patch.object(shared,'source',source),patch.object(shared,'SERIALIZATION',SERIALIZATION):
        return shared.predict(root,out)


if __name__=='__main__':
    import json
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
