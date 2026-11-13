def run():
 from pathlib import Path
 from tools.tests import game_trajectory_actor_150e1570_oracle as oracle
 ns=vars(oracle)
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];external=ns['external']
 retail=struct.unpack_from('>161I',(root/'conker/conker.us.bin').read_bytes(),0x10ea20);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')];cuts=private=0
 for c in (Case(0,0,-1,0,0),Case(8,1,9,7,3),Case(0,25,24,2,4),Case(8,255,0,1,2)):
  full=Machine(retail,c).run()
  for cut in range(full.all_accesses):
   ms=[]
   for w in programs:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',cut))
    except AccessBoundary:pass
    ms.append(m)
   r=ms[0];assert all((m.memory,m.calls,m.trace)==(r.memory,r.calls,r.trace) for m in ms[2:]),(c,cut,'padded')
   assert (external(ms[1].memory),ms[1].calls)==(external(r.memory),r.calls),(c,cut,'raw')
   private+=ms[1].memory!=r.memory;cuts+=1
 print('fault/access cuts',cuts,'raw private-state differences',private,'padded streams exactly agree')
