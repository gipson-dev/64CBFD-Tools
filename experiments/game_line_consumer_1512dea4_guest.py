"""Compare private C shapes with the original immediate camera-update branch."""
from pathlib import Path
import importlib.util,itertools,json,sys
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

out=Path('conker/build/game-line-consumer-1512dea4-screen')
from tools.experiments import game_line_consumer_1512dea4_retail as g
programs=[g.words]
for variant in range(6):
    raw,refs=payload(out/('shape-%02d.o'%variant),'func_1512DEA4')
    programs.append(bound_blob(raw,refs,{'func_150495B0':0x150495b0,'D_800A3710':0x800a3710,'D_800A3714':0x800a3714}))
results=[]
for kind,sx,sz,phase in itertools.product((0,1,2,3,4,255),(-7.,2.),(-3.,5.),(0,8)):
    c=g.Case(kind,sx,sz,phase);initial=g.fixture(c);values=[]
    for program in programs:
        try:
            m=g.Machine(initial.copy(),c);m.code.update({g.ENTRY+4*i:w for i,w in enumerate(program)});m=m.run()
            values.append(bytes(m.memory[g.OWNER+i] for i in range(0x9a0)).hex())
        except (AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError) as e:values.append('ERROR:'+str(e)[:100])
    results.append({'kind':kind,'case':repr(c),'matches':[values[0]==v and not v.startswith('ERROR:') for v in values[1:]],'errors':[v[:100] if v.startswith('ERROR:') else '' for v in values]})
report={'cases':len(results),'valid_kinds':sum(r['kind']<4 for r in results),
        'valid_mismatches':[sum(not r['matches'][i] for r in results if r['kind']<4) for i in range(6)],
        'invalid_mismatches':[sum(not r['matches'][i] for r in results if r['kind']>=4) for i in range(6)],
        'errors':sum(any(r['errors']) for r in results),'immediate_branch_only':True,'uncredited':True,'details':results}
(out/'guest-shape-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k!='details'},flush=True)
