from tools.tests.game_trajectory_actor_150e1570_oracle import *

def run():
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>161I',rom,0x10ea20);raw=program(out/'after.o');padded=[program(out/'generated.o'),program(out/'generic.o')];count=0
 for phase,slot,excluded,flags,pattern in itertools.product((0,8),(0,1,4,25,255),(-1,0,9,24,30),(0,1,2,3,4,7),range(5)):
  c=Case(phase,slot,excluded,flags,pattern);a=Machine(retail,c).run();b=Machine(raw,c).run();assert (external(a.memory),a.calls,a.r[2])==(external(b.memory),b.calls,b.r[2]),c
  for ws in padded:
   v=Machine(ws,c).run();assert (external(a.memory),a.calls,a.r[2])==(external(v.memory),v.calls,v.r[2]),c
  eligible=[i for i in range(25) if (not(flags&1 and i%4==0)) and i!=excluded and not(flags&2 and i%3==0) and not(flags&4 and i%7==0) and i!=slot-1]
  assert a.scores==eligible,(c,a.scores,eligible)
  choices=[i for i in eligible if score(i,pattern)!=0];best=min(choices,key=lambda i:score(i,pattern)) if choices else None
  assert a.r[2]==(0xdeadbeef if best is not None else 0),(c,best,hex(a.r[2]))
  if best is not None:assert read(a.memory,TABLE+best*0x32c+0x76,2)==0x6789
  count+=1
 print('private retail and raw candidate agree across',count,'modeled finite cases; independent eligibility and signed score checks pass')
 # Source-null witnesses: inactive records return zero; an eligible hit faults at
 # the subsequent source-halfword load in the bounded unmapped-memory model.
 for w in (retail,raw,*padded):
  c=Case(0,0,-1,0,0);m=Machine(w,c);m.r[4]=0
  for i in range(25):put(m.memory,TABLE+i*0x32c,0)
  m.run();assert m.r[2]==0 and [x[0] for x in m.calls]==[LOOK]
  c=Case(0,0,-1,0,0);m=Machine(w,c);m.r[4]=0
  try:m.run()
  except AssertionError as e:
   assert 'unmapped read' in str(e) and '118' in str(e),str(e)
  else:raise AssertionError('Expected modeled null halfword read to fault')
 print('two null-source outcomes agree in both streams')
