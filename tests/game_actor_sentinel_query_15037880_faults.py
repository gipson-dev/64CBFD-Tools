def run():
 from pathlib import Path
 from tools.tests import game_actor_sentinel_query_15037880_oracle as oracle
 ns=vars(oracle)
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 Machine=ns['Machine'];Case=ns['Case'];program=ns['program'];root=ns['root'];out=ns['out'];struct=ns['struct']
 retail=struct.unpack_from('>87I',(root/'conker/conker.us.bin').read_bytes(),0x64d30);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')];cuts=0
 for c in (Case(0,0,0,0,0,0,0),Case(8,-1,1,0,0,0,2),Case(0,1,1,0,0,0,3),Case(8,0,2,0,2,1,1),Case(0,0,2,4,0,1,0),Case(8,0,2,4,3,0,4),Case(0,0,3,0,0,0,0),Case(8,1,7,4,1,3,5)):
  full=Machine(retail,c).run()
  for cut in range(full.all_accesses):
   ms=[]
   for w in programs:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',cut))
    except AccessBoundary:pass
    ms.append(m)
   a=ms[0];assert all((m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace)==(a.memory,a.r,a.f,a.hi,a.lo,a.condition,a.trace) for m in ms[1:]),(c,cut)
   cuts+=1
 for mode in range(8):
  c=Case(0,0,mode,0,0,0,0);results=[]
  for w in programs:
   m=Machine(w,c);m.r[5]=0
   try:m.run();results.append(('return',m.r[2]))
   except AssertionError as e:results.append(('fault',str(e)))
  assert results.count(results[0])==4,(mode,results)
  assert results[0][0]==('fault' if mode in (1,2) else 'return'),(mode,results)
 # The distance gate can succeed without touching an invalid output.
 c=Case(0,0,2,4,3,0,0)
 for w in programs:
  m=Machine(w,c);m.r[5]=0;m.run();assert m.r[2]==1
 print('access cuts',cuts,'full state identical; nine null-output paths agree')
