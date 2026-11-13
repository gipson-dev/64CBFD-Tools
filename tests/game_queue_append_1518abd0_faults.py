def run():
 from pathlib import Path
 from tools.tests import game_queue_append_1518abd0_oracle as oracle
 ns=vars(oracle)
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct'];public=ns['public']
 retail=struct.unpack_from('>82I',(root/'conker/conker.us.bin').read_bytes(),0x1b8080);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')];cuts=private=0
 for c in (Case(0,0,1,0),Case(8,0,1,255),Case(0,1,0,1),Case(8,1,0,0),Case(0,1,1,1,0,2,0,1),Case(8,1,1,1,1,0,1,1),Case(0,1,1,255,0xffffffff,-1,1,0),Case(8,1,1,2,1,1,1,1)):
  full=Machine(retail,c).run()
  for cut in range(full.all_accesses):
   ms=[]
   for w in programs:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',cut))
    except AccessBoundary:pass
    ms.append(m)
   a=ms[0];assert all((m.memory,m.calls,m.trace)==(a.memory,a.calls,a.trace) for m in ms[2:]),(c,cut,'padded')
   assert (public(ms[1].memory,c),ms[1].calls)==(public(a.memory,c),a.calls),(c,cut,'raw')
   private+=ms[1].memory!=a.memory;cuts+=1
 print('fault/access cuts',cuts,'raw private-state differences',private,'padded streams agree')
