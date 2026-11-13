"""Compare original and guarded access-fault prefixes in bounded cases."""
from pathlib import Path
import importlib.util,json,sys
from tools.tests.game_owner_float_payload_oracle import Case
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable'
from tools.tests import game_texture_tile_151ed29c_guest as g
programs=[g.programs[0],bound_blob(*payload(out/'guarded.o','func_151ED29C'),g.symbols)];assert programs[0]==programs[1]
cuts=0
for mode,w,h,fmt,size in (('normal',1,1,0,0),('normal',3,17,7,3),('size-image',16,255,3,1),('commands-image',1,1,7,2)):
    cmd,img,dest=g.commands,g.image,g.sizeout
    if mode=='size-image':dest=img+8
    if mode=='commands-image':cmd=img+4
    initial=g.fixture(w,h,fmt,size)
    for base,n in ((cmd,32),(img,16),(dest,4)):
        for a in range(base-16,base+n+16):initial.setdefault(a,0xa5)
    args=(cmd,img,dest);good=g.Machine(programs[0],initial.copy(),Case(),entry=g.entry,s={},arguments=args).run()
    for cut in range(good.all_accesses):
        pair=[]
        for p in programs:
            m=g.Machine(p,initial.copy(),Case(),entry=g.entry,s={},arguments=args);m.cut=cut
            try:m.run()
            except AccessBoundary:pass
            else:raise AssertionError(('ineffective access cut',cut))
            pair.append(m)
        assert complete(pair[0])==complete(pair[1]) and pair[0].trace==pair[1].trace,(mode,cut)
        cuts+=1
report={'cases':4,'fault_prefixes':cuts,'guarded_equals_retail':True,'uncredited':True}
(out/'fault-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
