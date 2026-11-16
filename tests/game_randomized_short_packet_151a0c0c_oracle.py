"""Private finite guest check of all packet bytes and opaque-provider order."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,json,struct
from tools.tests import game_short_packet_factory_oracle as old
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_randomized_short_packet_151a0c0c_match as m
r,o,ENTRY,POOL=m.ROOT,m.OUT,m.ENTRY,0x80400000
S={name:int(name.split('_',1)[1],16)for name in('func_150ADA20','func_150ADA68','func_151423D8','func_15167D84','D_800918A0','D_8009187C','D_8008F8D0')}
bits,floating=old.old.bits,old.old.floating
u32=old.u32
@dataclass(frozen=True)
class Case:
 seed:int=0
 mode:int=0
 phase:int=0
 style:int=0
 heading:int=0
 x:float=1.25
 y:float=-2.5
 z:float=3.75
 owner:int=1
 mutation:int=0
def initial(c,raw_pool=None):
 m={old.STACK+c.phase+i:0xCD for i in range(-4096,1024)}
 m.update({old.MARK+i:(i*7+0x5A)&255 for i in range(1024)})
 m.update({S['D_8008F8D0']+i:128 if i<2 else 0 for i in range(16)})
 for addr,value in((0x800A8D14,503.0),(0x800A8D18,801.0)):old.put(m,addr,bits(value))
 if raw_pool is not None:m.update({POOL+i:v for i,v in enumerate(raw_pool)})
 return m
def args(c):return (1,0x87654321,bits(c.x),bits(c.y),bits(c.z),0x11111111,0x22222222,0x33333333,u32(c.heading),0x123400FF,0x3F000000,c.style,0x3F800000,0x81234567,0xF0000000|c.mode)
class Machine(old.Machine):
 def __init__(self,words,c,pool=None):
  self.case=c;self.home=old.STACK+c.phase;self.target=ENTRY;self.providers=S
  self.rng_i=self.rng_f=self.trig_i=self.submits=0;self.payloads=[]
  old.FactoryOracle.__init__(self,words,initial(c,pool),c,entry=ENTRY,s={},arguments=args(c))
  self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,target):
  counts={S['func_150ADA20']:0,S['func_150ADA68']:0,S['func_151423D8']:1,S['func_15167D84']:6}
  assert target in counts,hex(target)
  arguments=tuple(u32(v)for v in self.arguments(counts[target]));self.calls.append((target,arguments));self.events.append(('CALL',target,arguments))
  if target==S['func_15167D84']:
   assert arguments==(self.packet,0,0,0xFFFFFFFF,self.case.mode&255,1),arguments
   packet=old.data(self.memory,self.packet,56);assert old.private_bytes_untouched(packet);self.payloads.append((packet,arguments))
def reference(c,integer_offset=0,trig_offset=0,float_offset=0):
 m={i:0xCD for i in range(56)};calls=[];angle=old.rng_value(integer_offset,c)%15-63
 calls.append((S['func_150ADA20'],()))
 samples=[]
 for ordinal,value in enumerate((angle,angle-64,c.heading,c.heading-64)):
  a=value&255;calls.append((S['func_151423D8'],(a,)));samples.append(old.trig_value(ordinal+trig_offset,a,c))
 calls.append((S['func_150ADA68'],()))
 speed=bits(floating(bits(floating(old.float_value(float_offset,c))*503.0))+801.0)
 product=bits(floating(speed)*floating(samples[0]))
 def trunc(w):return int(floating(w))
 def store(offset,value,size):old.put(m,offset,value,size)
 store(0x16,trunc(bits(floating(product)*floating(samples[3]))),2)
 store(0x20,trunc(bits(floating(speed^0x80000000)*floating(samples[1]))),2)
 store(0x18,trunc(bits(floating(product)*floating(samples[2]))),2)
 calls.append((S['func_150ADA20'],()));store(0x22,old.rng_value(1+integer_offset,c)%41-130,2)
 calls.append((S['func_150ADA20'],()));store(0x2A,old.rng_value(2+integer_offset,c)%3+6,1)
 calls.append((S['func_150ADA20'],()));size=old.rng_value(3+integer_offset,c)%451+250;store(0x24,size,2);store(0x26,size,2)
 for offset in(0x30,0x31,0x32):store(offset,0,1)
 store(0x2F,255,1);store(0x1F,255,1);store(0x34,0,2);store(0x0C,0,2);store(0x0E,0,2)
 for offset,value in((0x10,c.x),(0x12,c.y),(0x14,c.z)):store(offset,int(floating(bits(value))),2)
 for offset in(0x2C,0x2D,0x2E):store(offset,128 if c.style<2 else 0,1)
 scaled=trunc(bits(floating(bits(c.x))*256.0))
 for offset in(0x1C,0x1D,0x1E):store(offset,scaled,1)
 if c.style in(0,1):store(0,S['D_800918A0' if c.style==0 else 'D_8009187C'],4)
 store(0x28,200,2);submit=(old.STACK+c.phase-56,0,0,0xFFFFFFFF,c.mode&255,1);calls.append((S['func_15167D84'],submit))
 return bytes(m[i]for i in range(56)),calls
def main():
 record=json.loads((m.FROZEN/'fingerprints.json').read_text())
 def immutable():
  m.check_inputs()
 immutable();programs=m.programs()
 cases=[Case(seed=i%8,mode=i,phase=(i%2)*8,style=(0,1,2,15)[i%4],heading=(0,63,64,255,0x12340080)[i%5],x=(-0.0,0.125,7.75,-19.375,127.5)[i%5],y=-2.25-i,z=0.75+i)for i in range(256)]
 cases += [Case(seed=seed,mode=255-seed,style=style,heading=angle,x=-3.75,y=100.5,z=-99.25)for seed in range(8)for style in(0,1,2,15)for angle in(0,0x876500FF)]
 visited={label:set()for label in programs}
 for index,c in enumerate(cases):
  expected,calls=reference(c)
  for label,(words,pool)in programs.items():
   q=Machine(words,c,pool).run();assert q.payloads[0][0]==expected,(index,label,'packet',q.payloads[0][0].hex(),expected.hex())
   assert q.calls==calls,(index,label,'provider calls',q.calls,calls);assert q.r[2]==1 and q.submits==1
   assert [q.r[i]for i in(*range(16,24),28,29,30,31)]==[q.before[i]for i in(*range(16,24),28,29,30,31)]
   assert q.f[20:]==q.before_f[20:] and old.get(q.memory,old.MARK)==1
   visited[label].update(q.visits)
 # A real output corruption must fail the independent complete-packet check.
 bad=programs['retail'][0][:];sites=[i for i,w in enumerate(bad)if w>>26==9 and w>>21&31==0 and w&65535==200];assert len(sites)==1;bad[sites[0]]^=1
 q=Machine(bad,cases[0]).run();assert q.payloads[0][0]!=reference(cases[0])[0]
 immutable();report=dict(cases_per_stream=len(cases),streams=len(programs),complete_packet_bytes=56,unwritten_packet_bytes_untouched=14,all256_mode_bytes=True,styles=[0,1,2,15],providers='four integer RNG, four trigonometric, one float RNG, one packet submission',opaque_provider_clobbers=True,saved_ABI_preserved=True,packet_corruption_control=True,visited_words={k:len(v)for k,v in visited.items()},production_state_matches_audited_inputs=len(record['inputs']),private_only=True,c_match_credit=0,scope='finite guest check; separate proof and image gates')
 (o/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
