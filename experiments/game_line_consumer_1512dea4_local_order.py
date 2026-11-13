"""Vary local declaration order to inspect retail stack-home discrepancies."""
from pathlib import Path
import itertools,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
root=Path.cwd();out=root/'conker/build/game-line-consumer-1512dea4-screen'
original=(out/'shape-00.c').read_text();needle='f32 offsetX,offsetZ,offsetY;';assert original.count(needle)==1
before=out/'before.o';rows=[]
for i,order in enumerate(itertools.permutations(('offsetX','offsetY','offsetZ'))):
    proposal=original.replace(needle,'f32 '+','.join(order)+';')
    obj,diag=compile_owner(root,out,proposal,'order-%02d'%i)
    assert same_functions(before,obj,('func_1512DEA4',))==1 and normalized_pools(before)==normalized_pools(obj)
    raw,_=payload(obj,'func_1512DEA4');words=struct.unpack('>%dI'%(len(raw)//4),raw)
    frame=65536-(words[0]&65535)
    loads=[(j,(w&65535)-frame) for j,w in enumerate(words) if w>>26==49 and (w>>21)&31==29]
    row={'order':order,'words':len(words),'frame':frame,'stack_loads_entry_relative':loads,'diagnostics':diag,'uncredited':True}
    rows.append(row);print(row,flush=True)
(out/'local-order-screen.json').write_text(json.dumps(rows,indent=2)+'\n')
