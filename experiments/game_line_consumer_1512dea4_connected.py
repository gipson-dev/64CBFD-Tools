"""Execute both camera-update branches with the original retail smoothing body."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

out=Path('conker/build/game-line-consumer-1512dea4-screen')
from tools.experiments import game_line_consumer_1512dea4_retail as g
HELPER=0x150495b0
helper=list(struct.unpack_from('>54I',g.rom,0x76a60))
connected={HELPER+4*i:w for i,w in enumerate(helper)}
programs=[g.words]
for variant in range(6):
    raw,refs=payload(out/('shape-%02d.o'%variant),'func_1512DEA4')
    programs.append(bound_blob(raw,refs,{'func_150495B0':HELPER,'D_800A3710':0x800a3710,'D_800A3714':0x800a3714}))
class Machine(g.Machine):
    def __init__(self,program,m,c):
        FactoryOracle.__init__(self,program,m,c,entry=g.ENTRY,s={},arguments=(g.OWNER,),connected=connected)
    def record_call(self,target):
        assert target==HELPER,hex(target)
        self.calls.append((target,tuple(self.arguments(6))))
    def hook(self,target):raise AssertionError(('unexpected external call',hex(target)))

results=[]
for kind,phase in itertools.product((0,1,2,3,4,255),(0,8)):
    c=g.Case(kind,-7.,5.,phase);initial=g.fixture(c);initial[g.OWNER+0x23c]=0
    for off,value in ((0x898,4.),(0x89c,3.),(0x8a0,.25),(0x8a4,-.5),
                      (0x2f8,1.),(0x2fc,2.),(0x300,3.),
                      (0x3c0,.125),(0x3c4,-.25),(0x3c8,.5),(0x7b4,.25)):
        put(initial,g.OWNER+off,bits(value))
    for addr,value in ((0x800a3710,.125),(0x800a3714,.25)):put(initial,addr,bits(value))
    streams=[]
    for p in programs:
        try:
            m=Machine(p,initial.copy(),c).run()
            streams.append({'owner':bytes(m.memory[g.OWNER+i] for i in range(0x9a0)).hex(),'calls':m.calls})
        except (AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError) as e:streams.append({'error':str(e)[:200]})
    results.append({'kind':kind,'phase':phase,'streams':streams})
valid=[r for r in results if r['kind']<4];invalid=[r for r in results if r['kind']>=4]
report={'cases':len(results),'connected_retail_helper_words':len(helper),
        'valid_mismatches':[sum(r['streams'][0]!=r['streams'][i+1] for r in valid) for i in range(6)],
        'invalid_mismatches':[sum(r['streams'][0]!=r['streams'][i+1] for r in invalid) for i in range(6)],
        'retail_errors':[r for r in results if 'error' in r['streams'][0]],
        'retail_call_counts':[len(r['streams'][0].get('calls',[])) for r in results],
        'uncredited':True,'details':results}
(out/'connected-helper-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k!='details'},flush=True)
assert not report['retail_errors'] and report['retail_call_counts']==[5]*len(results)
