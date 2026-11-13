from tools.tests.game_fade_graphic_151ed09c_oracle import *
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();programs=[struct.unpack_from('>81I',rom,0x21a54c)]+[program(out/(x+'.o')) for x in ('generated','generic')];cuts=0
 for c in (Case(0,0,0,0,0),Case(8,64,255,1,0),Case(0,0xffffffff,127,1,1),Case(8,0x20000000,1,0,1)):
  full=Machine(programs[0],c).run()
  for cut in range(full.all_accesses):
   results=[]
   for words in programs:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',c,cut))
    except AccessBoundary:pass
    results.append(m)
   a=results[0];assert all((m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace)==(a.memory,a.r,a.f,a.hi,a.lo,a.condition,a.trace) for m in results[1:]),(c,cut);cuts+=1
 print('retail and padded execution:',cuts,'access-boundary prefixes across four cases',flush=True)
