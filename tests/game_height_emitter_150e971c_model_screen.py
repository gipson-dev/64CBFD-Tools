"""Independent bounded reference for the uncredited height callback."""
import itertools,json
from tools.tests import game_height_emitter_150e971c_guest_screen as g
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating

def reference(initial,mutation):
 m=initial.copy();state=g.actor+0x170
 calls=[(g.update,(g.actor,),None)]
 if mutation&1:put(m,g.actor+0x3c,bits(-3.0))
 if not floating(read(m,g.actor+0x3c)) < floating(read(m,state)):
  return 1,calls,bytes(m[g.actor+i] for i in range(0x1b0))
 if read(m,state+4)&31==10:
  calls.extend(((g.frng,(),None),(g.irng,(),None)))
  packet=g.STACK-44
  for offset,value,size in ((0,0x9701,4),(4,100,2),(6,11,1),(7,0,1),(8,0,4),(12,0,4),
          (16,255,1),(17,255,1),(18,255,1),(19,255,1),(20,255,1),(21,255,1),
          (22,0,1),(23,7,1),(24,0x3b0003,4),(34,20,2),(36,12,2)):
   put(m,packet+offset,value,size)
  if mutation&2:
   put(m,g.actor+0x38,bits(9.0));put(m,state,bits(15.0));m[g.actor+1]=0xa9
  args=(packet,0,0,state+8,read(m,g.actor+0x38),bits(floating(read(m,state))+5.0),
        read(m,g.actor+0x40),bits(25.0),bits(25.0),0xab,0,0,m[g.actor+0xc],m[g.actor+1])
  calls.append((g.emit,args,bytes(m[packet+i] for i in range(40))))
 return 0,calls,bytes(m[g.actor+i] for i in range(0x1b0))
def observe(m):return m.r[2],m.seen,bytes(m.memory[g.actor+i] for i in range(0x1b0))
corpus=[]
for height,flags,seed,mutation in itertools.product((-5.,10.,11.,float('nan')),(9,10,26,42,0xffffffff),(0,1),(0,1,2,3)):
 initial=g.fixture(height,flags,seed);corpus.append((initial,mutation))
for initial,mutation in corpus:
 want=reference(initial,mutation)
 for words in (g.truth,g.snapshot,g.guarded):
  assert observe(g.Oracle(words,initial.copy(),mutation).run())==want
controls=((0x4606203c,0x4606203e),(0x31cf001f,0x31cf000f),(0x304900ff,0x3049007f))
for old,new in controls:
 altered=list(g.snapshot);assert altered.count(old)==1;altered[altered.index(old)]=new
 assert any(observe(g.Oracle(altered,m.copy(),mode).run())!=reference(m,mode) for m,mode in corpus),(hex(old),hex(new))
report={'cases_per_stream':len(corpus),'streams':3,'nan_samples':True,'negative_controls':len(controls),'fcsr_not_modeled':True,'uncredited':True}
(g.out/'model-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
