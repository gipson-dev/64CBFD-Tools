"""Run the established preset native model against the revised nested source."""
import hashlib
from pathlib import Path
from tools.experiments import game_point_descriptor_151382e0_match as screen
from tools.tests import game_localized_trail_preset_151dbaa8_native as original

path = Path(original.__file__)
if hashlib.sha256(path.read_bytes()).hexdigest() != '8e0bee3957d735b467080443043befb1e6dc86d6df392e755e51512c52b40a78':
    raise ValueError('Historical preset native fixture fingerprint changed')
source = path.read_text()
changes = {
    'out=p.out;root=p.root': "from tools.experiments.game_point_descriptor_151382e0_match import ROOT as root, OUT as out",
    "out/'independent-selected.c'": "out/'durable-trail-after.c'",
    "'position[0] = point->unk0','position[0] = point->unk4'": "'position.x = point->unk0','position.x = point->unk4'",
    'f32 position[3],timeBase,timeRange,scaleBase,scaleRange,radiusBase,radiusRange;':
        'struct {f32 x,y,z;} position;f32 timeBase,timeRange,scaleBase,scaleRange,radiusBase,radiusRange;',
    'get_bits(&b->position[i])': 'get_bits(i==0?&b->position.x:i==1?&b->position.y:&b->position.z)',
}
for old, new in changes.items():
    if old not in source:
        raise ValueError('Historical preset fixture shape changed')
    source = source.replace(old, new)
namespace = {}
exec(compile(source, str(screen.OUT / 'trail-native-adapted.py'), 'exec'), namespace)
namespace['main']()
