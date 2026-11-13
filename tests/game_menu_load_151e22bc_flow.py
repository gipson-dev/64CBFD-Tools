"""Check byte-load temporaries are used only by their byte stores."""
from pathlib import Path
import json,os,runpy
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
d=runpy.run_module('tools.tests.game_menu_load_151e22bc_derive',run_name='__menu_flow_derivation__')
w=d['w'];truth=d['truth'];origins=d['origins'];pairs=d['load_store_pairs']
def access(word):
    op=word>>26;rs=word>>21&31;rt=word>>16&31;rd=word>>11&31;fn=word&63
    if word==0:return set(),set()
    if op==3:return set(),{31}
    if op==0:
        if fn==0:return {rt},{rd}
        return {rs,rt},{rd}
    if op in (4,5):return {rs,rt},set()
    if op in (9,10,11,12,13,15):return ({rs} if op!=15 else set()),{rt}
    if op in (32,36):return {rs},{rt}
    if op==40:return {rs,rt},set()
    raise ValueError(('Unexpected intervening instruction',hex(word)))
checks=0
for load,store in pairs:
    for label,words,start,end in [('retail',truth,load,store),('selected',w,origins[load],origins[store])]:
        assert start<end,(label,load,store,start,end)
        reg=words[start]>>16&31
        for i in range(start+1,end):
            reads,writes=access(words[i]);assert reg not in reads|writes,(label,load,store,i,reg)
        checks+=1
report={'low_byte_load_store_pairs':len(pairs),'stream_checks':checks,
        'no_intervening_register_use_or_write':True}
out=root/'conker/build/game-menu-load-151e22bc-durable'
(out/'static-flow-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
