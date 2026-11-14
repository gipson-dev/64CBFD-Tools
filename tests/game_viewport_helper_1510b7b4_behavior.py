from pathlib import Path
import itertools,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.test_game_viewport_command_helper import ViewportOracle,case,ENTRY,PAGE,TABLE,BASE
from tools.tests import test_game_queued_segment_writer as queue
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-viewport-helper-shape-screen';sym={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};retail=list(struct.unpack_from('>105I',(root/'conker/conker.us.bin').read_bytes(),0x138c64));raw=bound_blob(*payload(out/'owner-candidate.o','func_1510B7B4'),sym);guard=bound_blob(*payload(out/'guarded.o','func_1510B7B4'),sym);assert guard==retail
cases=[]
for slot,page,norm in itertools.product(range(4),range(2),(0,1,0x7fff,0x8000,0xffff,0x1234,0xabcd)):cases.append((case(slot,page,norm),queue.OUTPUT,slot))
for slot,page in itertools.product((0x20000000,0x40000000,0x80000000,0xe0000000),range(2)):cases.append((case(0,page,0x8001),queue.OUTPUT,slot))
for output,slot,page in itertools.product((PAGE-12,TABLE-84,PAGE-76,BASE-68),range(4),range(2)):cases.append((case(slot,page,0x8001,output),output,slot))
assert len(cases)==96
for memory,output,slot in cases:
 ref=ViewportOracle(retail,ENTRY,memory,(output,slot)).run()
 for code in(raw,guard):
  m=ViewportOracle(code,ENTRY,memory,(output,slot)).run();assert (m.memory,m.reads,m.stores,m.r[2])==(ref.memory,ref.reads,ref.stores,ref.r[2]),(output,slot)
controls=((0x240b0003,0x240b0004),(0x340cfffd,0x340cfffc),(0x35ce0007,0x35ce0005))
for before,after in controls:
 assert retail.count(before)==1,hex(before)
 mutant=retail.copy();mutant[mutant.index(before)]=after;initial,output,slot=cases[0];ref=ViewportOracle(retail,ENTRY,initial,(output,slot)).run();actual=ViewportOracle(mutant,ENTRY,initial,(output,slot)).run();assert (actual.memory,actual.reads,actual.stores,actual.r[2])!=(ref.memory,ref.reads,ref.stores,ref.r[2]),hex(before)
for slot,page in ((-1,0),(4,0),(0,2)):
 memory=case(0,page);states=[]
 for code in(retail,raw,guard):
  m=ViewportOracle(code,ENTRY,memory,(queue.OUTPUT,slot))
  try:m.run();raise RuntimeError('expected unmapped read')
  except AssertionError as e:assert 'unmapped' in str(e)
  states.append((m.memory,m.reads,m.stores))
 assert states[0]==states[1]==states[2]
report={'case_count_per_stream':len(cases),'streams':['retail','candidate','guarded'],'invalid_prefixes':3,'negative_controls':len(controls),'read_store_order_checked':True,'uncredited':True};(out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
