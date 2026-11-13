"""Compare terminating owner/stack overlaps without counting faults as matches."""
from pathlib import Path
import importlib.util,json,struct,sys
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-line-record-1512dd50-durable'
from tools.tests import game_line_record_1512dd50_guest as g
programs=[list(struct.unpack_from('>85I',g.rom,0x15b200))]
for name in ('pointer-reuse-00.o','explicit-padded.o'):
 raw,refs=payload(out/name,'func_1512DD50');programs.append(bound_blob(raw,refs,{'func_150AD930':g.HELPER}))
results=[]
for delta in range(0x680,0x901,4):
 g.OWNER=STACK-delta;c=g.Case((11,-7,19),3,(0.5,1.0,2.0,-0.25),0x12345678,0x80000001,0xe1);initial=g.fixture(c);streams=[]
 for p in programs:
  try:
   m=g.Machine(p,initial.copy(),c).run();streams.append({'ok':True,'bytes':bytes(m.memory[g.OWNER+i] for i in range(0x870,0x8a0)).hex(),'calls':m.calls})
  except (AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError) as e:streams.append({'ok':False,'error':str(e)[:180]})
 matches=[x==streams[0] if x['ok'] and streams[0]['ok'] else None for x in streams[1:]]
 results.append({'owner_delta':hex(delta),'matches':matches,'streams':streams})
report={'cases':len(results),'retail_terminated':sum(r['streams'][0]['ok'] for r in results),'unresolved':sum(not all(s['ok'] for s in r['streams']) for r in results),'explicit_conversion_mismatches':sum(r['matches'][0] is False for r in results),'padded_mismatches':sum(r['matches'][1] is False for r in results),'details':results}
assert report['explicit_conversion_mismatches']==report['padded_mismatches']==0
(out/'overlap-sweep.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='details'}),flush=True)
