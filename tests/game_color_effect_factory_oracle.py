"""Direct-exact color-effect packet factory guest oracle and access-prefix proof."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct
from tools.tests import game_point_effect_payload_oracle as old
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,INPUT,STACK,MARK,TABLE,CALLBACK,SUBMIT=0x15152874,0x22000,old.STACK,old.MARK,0x8008AC60,0x91000,0x150CCEB0
@dataclass(frozen=True)
class Case:
 seed:int=0;mode:int=0;extra:int=0;selector:int=-1;mutation:int=0;phase:int=0
def u32(v):return v&0xFFFFFFFF
def put(m,p,v,n=4):old.put(m,p,v,n)
def get(m,p,n=4):return old.read(m,p,n)
def packet(m,p):return old.data(m,p,52)
def fixture(c):
 home=STACK+c.phase;m={home+i:(i*19+c.seed*17+73)&255 for i in range(-2048,1024)}
 for i in range(0x4C):m[INPUT+i]=(i*29+c.seed*11+101)&255
 values=((0,1,4),(4,2,4),(8,old.bits(1.25+c.seed),4),(12,old.bits(-2.5),4),(16,old.bits(3.75),4),(0x14,-30,2),(0x16,60,2),(0x18,15,2),(0x1A,45,2),(0x1C,old.bits(2.),4),(0x20,old.bits(4.),4),(0x24,old.bits(.75),4),(0x28,old.bits(1.),4),(0x2C,old.bits(3.),4),(0x30,c.selector&255,1),(0x31,0xA5,1),(0x32,20,2),(0x34,8,2),(0x36,0xBEEF,2),(0x38,old.bits(.5),4),(0x3C,old.bits(1.5),4),(0x40,old.bits(2.5),4),(0x44,old.bits(3.5),4),(0x48,old.bits(4.5),4))
 for at,v,n in values:put(m,INPUT+at,v,n)
 put(m,TABLE,CALLBACK);return m
def mutate_input(m,c,late=False):
 if not(c.mutation&(2 if late else 1)):return
 values=((0,2,4),(4,1,4),(8,old.bits(-8.),4),(0x14,-12,2),(0x16,20,2),(0x18,6,2),(0x1A,18,2),(0x1C,old.bits(1.),4),(0x20,old.bits(2.),4),(0x24,old.bits(9.),4),(0x28,old.bits(3.),4),(0x2C,old.bits(5.),4),(0x32,7,2),(0x34,3,2),(0x38,old.bits(6.),4),(0x3C,old.bits(7.),4),(0x40,old.bits(8.),4),(0x44,old.bits(9.),4),(0x48,old.bits(10.),4))
 for at,v,n in values:put(m,INPUT+at,v,n)
def colors(c,index):return bytes(((c.seed*31+index*47+i*53+17)&255)for i in range(4))
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;p=home-144+0x58;calls=[];packets=[];ni=nf=0
 def integer():
  nonlocal ni
  calls.append((old.INTEGER,()));v=old.ri(ni,old.Case(seed=c.seed));ni+=1
  if ni==1:mutate_input(m,c)
  return v
 def real():
  nonlocal nf
  calls.append((old.FLOAT,()));v=old.rf(nf,old.Case(seed=c.seed));nf+=1;return v
 remaining=integer()%(get(m,INPUT+4)+1)+get(m,INPUT)
 for at in range(0,12,4):put(m,p+at,get(m,INPUT+8+at))
 put(m,p+0x18,get(m,INPUT+0x24));put(m,p+0x30,get(m,INPUT+0x48))
 number=0
 while remaining:
  first,second=integer(),integer();sample=real()
  a=old.HALF(first%(old.HALF(get(m,INPUT+0x16,2))+1)+old.HALF(get(m,INPUT+0x14,2)))
  b=old.HALF(second%(old.HALF(get(m,INPUT+0x1A,2))+1)+old.HALF(get(m,INPUT+0x18,2)))
  radius=old.fa(old.fm(sample,get(m,INPUT+0x20)),get(m,INPUT+0x1C));calls.append((old.VECTOR,(u32(a),u32(b),radius,p+0x0C)))
  for i,v in enumerate((old.bits(a*.125),old.bits(b*.25),old.fm(radius,old.bits(.5)))):put(m,p+0x0C+4*i,v)
  put(m,p+0x1C,old.fa(old.fm(real(),get(m,INPUT+0x2C)),get(m,INPUT+0x28)))
  put(m,p+0x24,integer()%(old.HALF(get(m,INPUT+0x34,2))+1)+old.HALF(get(m,INPUT+0x32,2)))
  put(m,p+0x28,old.fa(old.fm(real(),get(m,INPUT+0x40)),get(m,INPUT+0x38)))
  put(m,p+0x2C,old.fa(old.fm(real(),get(m,INPUT+0x44)),get(m,INPUT+0x3C)))
  selector=((get(m,INPUT+0x30,1)^128)-128)
  if selector!=-1:
   calls.append((CALLBACK,(p+0x20,)));m.update({p+0x20+i:b for i,b in enumerate(colors(c,number))})
  else:
   for i in range(4):m[p+0x20+i]=255
  calls.append((SUBMIT,(p,c.mode&255,c.extra&255)));packets.append((p,packet(m,p)));put(m,MARK+4*number,number+1);mutate_input(m,c,late=True)
  number+=1;remaining-=1
 return m,calls,packets,ni,nf
class Machine(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY):
  self.c=c;self.home=STACK+c.phase;self.rng_i=self.rng_f=self.submits=0;self.packets=[]
  super().__init__(words,memory,c,entry=entry,s={},connected=None,arguments=(INPUT,c.mode,c.extra))
 def record_call(self,t):
  counts={ENTRY:3,old.INTEGER:0,old.FLOAT:0,old.VECTOR:4,CALLBACK:1,SUBMIT:3};assert t in counts,hex(t)
  a=tuple(u32(v)for v in self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==SUBMIT:self.packets.append((a[0],packet(self.memory,a[0])))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];value=0;fvalue=None
  if t==old.INTEGER:
   value=old.ri(self.rng_i,old.Case(seed=c.seed));self.rng_i+=1
   if self.rng_i==1:mutate_input(self.memory,c)
  elif t==old.FLOAT:fvalue=old.rf(self.rng_f,old.Case(seed=c.seed));self.rng_f+=1
  elif t==old.VECTOR:
   for i,v in enumerate((old.bits(old.HALF(a[0])*.125),old.bits(old.HALF(a[1])*.25),old.fm(a[2],old.bits(.5)))):put(self.memory,a[3]+4*i,v)
  elif t==CALLBACK:
   for i,b in enumerate(colors(c,self.submits)):self.memory[a[0]+i]=b
  else:
   assert t==SUBMIT;self.submits+=1;mutate_input(self.memory,c,late=True);put(self.memory,MARK+4*(self.submits-1),self.submits)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
  if fvalue is not None:self.f[0]=fvalue
def programs(output,layout=0):
 q=json.loads((output/'private-layout-v4.json').read_text());entry=q['layouts'][layout]['entry'];result=[]
 for label in('original','C'):
  image=(output/('layout-%d-%s.elf'%(layout,label))).read_bytes();at=elf_slot_offset(image,entry,584);result.append(struct.unpack_from('>146I',image,at))
 assert result[0]==result[1];return entry,result
def state(m):return m.memory,m.r,m.f,m.trace,m.calls,m.packets,m.hi,m.lo,m.current_pc,m.delay_of,m.all_accesses,m.rng_i,m.rng_f,m.submits
def qualify(root,output):
 total=0;seen=set();modes=set();branches=set();prefixes=0
 cases=[Case(seed=i%4,mode=i,extra=(i*0x87654321)&0xFFFFFFFF,selector=(-1,0)[i%2],mutation=(0,1,2,3)[i%4],phase=(i%2)*8)for i in range(256)]
 layouts=json.loads((output/'private-layout-v4.json').read_text())['layouts'];assert len(layouts)==3
 entry,words=programs(output)
 for c in cases:
  initial=fixture(c);wanted,calls,packets,ni,nf=reference(initial,c);models=[Machine(code,initial,c,entry).run()for code in words]
  assert state(models[0])==state(models[1]);m=models[0]
  assert(old.public(m.memory,old.Case(phase=c.phase)),m.calls,m.packets,m.rng_i,m.rng_f)==(old.public(wanted,old.Case(phase=c.phase)),calls,packets,ni,nf)
  seen.update(v for model in models for v in model.visits);modes.add(c.mode&255);branches.add(c.selector)
  total+=1
 entry,words=programs(output)
 for c in(Case(selector=-1),Case(selector=0,mutation=3,phase=8)):
  initial=fixture(c);full=Machine(words[0],initial,c).run()
  for cut in range(full.all_accesses):
   models=[]
   for code in words:
    m=Machine(code,initial,c);m.cut=cut
    try:m.run()
    except old.faults.AccessBoundary:pass
    else:raise AssertionError('Access prefix did not fire')
    models.append(m)
   assert state(models[0])==state(models[1]);prefixes+=1
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>146I',rom,0x17FD24);traps={ENTRY+4*i for i,w in enumerate(retail)if w&0xFC00003F==13}
 assert len(traps)==4 and set(range(ENTRY,ENTRY+584,4))-traps<=seen and not(traps&seen) and modes==set(range(256)) and branches=={-1,0}
 report=dict(success=True,cases=total,executions=total*2,semantic_layouts=1,independent_GNU_links=len(layouts),root_words=146,covered_nontrap_words=142,unreachable_divisor_traps=4,all256_mode_bytes=True,color_default_and_callback_paths=True,live_input_after_first_RNG_and_after_submit=True,packet_visible_bytes=52,private_tail_bytes=4,private_tail_untouched=True,access_prefix_pairs=prefixes,original_and_C_full_state_calls_packets_and_traces_equal=True,independent_reference=True)
 (output/'private-guest-v5.json').write_text(json.dumps(report,indent=2)+'\n');return report
