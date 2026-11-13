"""Exercise every guest byte index through the original mapped data tables."""
from pathlib import Path
import importlib.util,itertools,json,os,sys
from tools.tests.game_owner_float_payload_oracle import Case
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable'
from tools.tests import game_texture_tile_151ed29c_guest as g
g.programs[1]=bound_blob(*payload(out/os.environ.get('TILE_OBJECT','coords-02.o'),'func_151ED29C'),g.symbols)
cases=0
for w,h,fmt,size in itertools.product((0,1,3,16,65535),(0,1,3,65535),(0,7),range(256)):
    initial=g.fixture(w,h,fmt,size);expected=g.reference(initial)
    for n,p in enumerate(g.programs):
        m=g.Machine(p,initial.copy(),Case(),entry=g.entry,s={},arguments=(g.commands,g.image,g.sizeout)).run()
        if m.memory!=expected or m.r[2]!=g.commands+32:raise AssertionError((w,h,fmt,size,n))
    cases+=1
report={'cases':cases,'guest_size_values':256,'streams':2,'native_out_of_table_behavior_not_claimed':True,'uncredited':True}
(out/'size-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
