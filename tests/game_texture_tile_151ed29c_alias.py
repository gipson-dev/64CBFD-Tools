"""Detect retail/C differences when image and output storage overlap."""
from pathlib import Path
import importlib.util,itertools,json,os,sys
from tools.tests.game_owner_float_payload_oracle import Case
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable'
from tools.tests import game_texture_tile_151ed29c_guest as g
g.programs[1]=bound_blob(*payload(out/os.environ.get('TILE_OBJECT','coords-02.o'),'func_151ED29C'),g.symbols)
rows=[];checked=0
for mode,offset,w,h,fmt,size in itertools.product(('size-image','size-commands','commands-image'),range(-8,17,4),(1,3,16,255),(1,4,15),(0,3,7),(0,1,2,3)):
    cmd,img,dest=g.commands,g.image,g.sizeout
    if mode=='size-image':dest=img+offset
    elif mode=='size-commands':dest=cmd+offset
    else:cmd=img+offset
    initial=g.fixture(w,h,fmt,size)
    for base,n in ((cmd,32),(img,16),(dest,4)):
        for a in range(base-16,base+n+16):
            if a not in initial:initial[a]=0xa5
    result=[]
    try:
        for p in g.programs:
            m=g.Machine(p,initial.copy(),Case(),entry=g.entry,s={},arguments=(cmd,img,dest)).run()
            result.append((m.memory,m.r[2]))
    except (AssertionError,KeyError) as e:
        rows.append({'mode':mode,'offset':offset,'case':[w,h,fmt,size],'fault':str(e)[:120]});continue
    if result[0]!=result[1]:
        diff=[(hex(a),result[0][0].get(a),result[1][0].get(a)) for a in sorted(set(result[0][0])|set(result[1][0])) if result[0][0].get(a)!=result[1][0].get(a)]
        rows.append({'mode':mode,'offset':offset,'case':[w,h,fmt,size],'different':diff[:10]})
    checked+=1
    if len(rows)>=8:break
(out/'alias-screen.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'checked':checked,'first_counterexamples':rows,'uncredited':True}),flush=True)
assert checked==3024 and not rows
