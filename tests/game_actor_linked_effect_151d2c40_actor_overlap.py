"""Compare original and selected updates with actor/effect storage overlap."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-linked-effect-151d2c40-durable'
from tools.tests import game_actor_linked_effect_151d2c40_guest as g
programs=[list(struct.unpack_from('>91I',g.rom,0x2000f0))]
for p in ('portable-03.o','guarded.o'):programs.append(bound_blob(*payload(out/p,'func_151D2C40'),g.symbols))
patterns=[(0,0,0,0,-1,-1,1,0),(0,1,0,1,0,1,1,0),(3,0,0,0,-1,-1,1,0)]
rows=[]
for delta,phase,pattern in itertools.product(range(-0x100,0x101,4),(0,8),patterns):
    g.ACTOR=g.EFFECT+delta;c=g.Case(*pattern,phase);initial=g.fixture(c);models=[]
    for p in programs:
        try:
            m=g.Machine(p,initial.copy(),c).run();models.append({'ok':True,'memory':m.memory,'calls':m.calls})
        except (AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError) as e:models.append({'ok':False,'error':str(e)[:180]})
    allok=all(x['ok'] for x in models);rows.append({'delta':delta,'phase':phase,'pattern':pattern,
        'retail_ok':models[0]['ok'],'all_ok':allok,
        'raw_match':models[0]==models[1] if allok else None,'guarded_match':models[0]==models[2] if allok else None})
report={'cases':len(rows),'retail_terminated':sum(r['retail_ok'] for r in rows),'all_terminated':sum(r['all_ok'] for r in rows),
        'unresolved':sum(not r['all_ok'] for r in rows),'raw_mismatches':sum(r['raw_match'] is False for r in rows),
        'guarded_mismatches':sum(r['guarded_match'] is False for r in rows),'helpers_modeled':True,'details':rows,'uncredited':True}
(out/'actor-overlap-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k!='details'},flush=True)
