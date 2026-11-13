"""Differential stack overlap screen with several independent field patterns."""
from pathlib import Path
import importlib.util, itertools, json, struct, sys
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-line-record-1512dd50-durable'
from tools.tests import game_line_record_1512dd50_guest as g
programs=[bound_blob(*payload(out/p,'func_1512DD50'),{'func_150AD930':g.HELPER})
          for p in ('retail.o','pointer-reuse-00.o','explicit-padded.o')]
patterns=[((11,-7,19),3,(.5,1.,2.,-.25),0x12345678,0x80000001,0xe1,0),
          ((-32768,32767,-1),-2,(-1.25,.75,-.5,2.),0x80000081,0xffffffff,0x14,0),
          ((32767,-1,-32768),32767,(.5,1.,2.,-.25),0xffffffff,0,0xfa,8)]
counts={'cases':0,'all_terminated':0,'unresolved':0,'raw_mismatches':0,'padded_mismatches':0}
for delta,pattern in itertools.product(range(0x680,0x901,4),patterns):
    g.OWNER=STACK-delta;c=g.Case(*pattern);initial=g.fixture(c);results=[]
    for p in programs:
        try:
            m=g.Machine(p,initial.copy(),c).run()
            results.append((bytes(m.memory[g.OWNER+i] for i in range(0x870,0x8a0)),m.calls))
        except (AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError):results.append(None)
    counts['cases']+=1
    if any(x is None for x in results):counts['unresolved']+=1;continue
    counts['all_terminated']+=1
    counts['raw_mismatches']+=results[0]!=results[1]
    counts['padded_mismatches']+=results[0]!=results[2]
assert counts['raw_mismatches']==counts['padded_mismatches']==0,counts
(out/'overlap-extended.json').write_text(json.dumps(counts,indent=2)+'\n')
print(counts,flush=True)
