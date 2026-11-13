"""Vary every nearby record/settings overlap for the menu-loader screens."""
from pathlib import Path
import importlib.util,itertools,json,sys
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable'
from tools.tests import game_menu_load_151e22bc_guest as g
cases=[]
for index,value,clamp,alias in itertools.product((0,1,2,5,7,8,9),(-128,1),(4,255),range(-16,22)):
    if alias==0:continue
    c=g.Case(index,value,clamp,alias);initial,rec=g.fixture(c);expected=g.reference(initial,c,rec)
    wanted={a:v for a,v in expected.items() if not g.TABLE<=a<g.TABLE+40}
    models=[]
    for p,mapped in g.programs:
        try:
            memory=initial.copy();memory.update({g.TABLE+i:v for i,v in enumerate(mapped)})
            m=g.Machine(p,memory,c).run()
            public={a:v for a,v in m.memory.items() if not g.STACK-512<=a<g.STACK+512 and not g.TABLE<=a<g.TABLE+40}
            models.append({'match':public==wanted,'error':''})
        except (AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError) as e:models.append({'match':False,'error':str(e)[:100]})
    cases.append({'case':repr(c),'models':models})
report={'cases':len(cases),'streams':len(g.programs),
        'mismatches':[sum(not r['models'][i]['match'] for r in cases) for i in range(len(g.programs))],
        'errors':[sum(bool(r['models'][i]['error']) for r in cases) for i in range(len(g.programs))],
        'samples':[[r['case'] for r in cases if not r['models'][i]['match']][:6] for i in range(len(g.programs))],
        'uncredited':True}
(out/'guest-alias-sweep.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
