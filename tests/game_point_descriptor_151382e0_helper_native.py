from pathlib import Path
import sys
from tools.experiments.game_point_descriptor_151382e0_match import ROOT as root, OUT as base
out=base/'helper-native';out.mkdir(exist_ok=True)
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.game_angular_trail_factory_native import qualify
old=(Path(__file__).with_name('game_point_descriptor_151382e0_helper_native_fixture.c')).read_text();previous=body(old,'func_15153F18');candidate=body((out.parent/'durable-helper-after.c').read_text(),'func_15153F18');assert old.count(previous)==1
old=old.replace(previous,candidate,1).replace('f32 position[3];','struct { f32 x, y, z; } position;').replace('position[0]','position.x').replace('position[1]','position.y').replace('position[2]','position.z')
(out/'native_harness_v1.c').write_text(old);report=qualify(out)
print('nested helper native independent model: 256 cases each at O0/O2/O3, UBSan:',report['success'])
