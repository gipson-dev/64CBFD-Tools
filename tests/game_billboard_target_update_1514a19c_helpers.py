"""Connect both43 original RNG words and qualify their actual seed-only footprint."""
from tools.experiments import game_billboard_target_update_1514a19c_match as target_packet
from pathlib import Path
from dataclasses import replace
import inspect,itertools,json,struct,sys
sys.path.insert(0,str(target_packet.ROOT));o=target_packet.OUT;pass
from tools.tests import game_billboard_target_update_1514a19c_guest as g
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
Case=g.Case;u32,half,read,put=g.u32,g.half,g.read,g.put;initial_fcsr=g.initial_fcsr;convert_integer=g.convert_integer;trunc=g.trunc;arithmetic=g.arithmetic;public=g.public;DELTA=g.DELTA;SCALARS=g.SCALARS;RNG=g.RNG;FRNG=g.FRNG
SEED,SCALE=0x800885B0,0x8009F740
class Connected(g.Machine):
 def execute(self,word):
         op,rs,rt,rd,shift,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63;mask=(1<<64)-1
         if op in(55,63)or op==0 and fn in(37,38,56,58,60,62,63,27):
             prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=word
             try:
                 if op in(55,63):
                     p=u32(self.r[rs]+half(word));assert p%8==0
                     if op==55:self.r[rt]=self.get(p,8)
                     else:self.put(p,self.r[rt],8)
                 elif fn==27:
                     a,b=u32(self.r[rs]),u32(self.r[rt]);assert b;self.lo,self.hi=a//b,a%b
                 else:
                     value=self.r[rt]&mask
                     if fn in(37,38):value=self.r[rs]|self.r[rt]if fn==37 else self.r[rs]^self.r[rt]
                     elif fn in(56,60):value<<=shift+(32 if fn==60 else 0)
                     elif fn in(58,62):value>>=shift+(32 if fn==62 else 0)
                     else:value=(value if value<1<<63 else value-(1<<64))>>(shift+32)
                     self.r[rd]=value&mask
                 self.r[0]=0
             finally:self.own_instruction=prior
         else:
             before=self.r[:];super().execute(word)
             destination=rt if op in(9,12,13,15,32,33,35,36,37)else rd if op==0 and fn in(0,2,3,33,35,36,42,43,16,18)else None
             for i,value in enumerate(before):
                 if i!=destination and value>0xFFFFFFFF:self.r[i]=value

def reference(initial,c,initial_csr=None):
 m=dict(initial);p=c.object;csr=initial_fcsr(c)if initial_csr is None else initial_csr;calls=[];ops=[];counts={RNG:0,FRNG:0}
 def operation(a,b,kind):
  nonlocal csr
  ops.append((kind,a,b,csr));v,flags=convert_integer(a,csr&3)if kind==32 else trunc(a)if kind==13 else arithmetic(a,b,kind,csr&3);csr=(csr&~0x3F000)|flags;return v
 def draw(t):
  calls.append((t,()));counts[t]+=1
  seed=next_seed(read(m,SEED,8));put(m,SEED,seed,8)
  if t==RNG:return u32(seed)
  return operation(operation(seed&65535,0,32),read(m,SCALE),2)
 def tick(off):
  put(m,p+off,u32(half(read(m,p+off,2))-read(m,DELTA)),2);return half(read(m,p+off,2))<0
 if tick(0x12E):
  put(m,p+0x12E,draw(RNG)%6,2);which=draw(RNG)&3;sample=draw(FRNG);a,b=(0x11C,0x120)if which else(0x124,0x11C);lower=read(m,p+b);put(m,p+0x128,operation(operation(sample,operation(read(m,p+a),lower,1),2),lower,0))
 current=read(m,p+0x30);put(m,p+0x30,operation(current,operation(operation(read(m,p+0x128),current,1),read(m,SCALARS[0]),2),0))
 if tick(0x12C):
  put(m,p+0x12C,draw(RNG)%17,2);sample=draw(FRNG);lower=read(m,p+0x114);put(m,p+0x118,operation(operation(sample,operation(read(m,p+0x110),lower,1),2),lower,0))
 current=read(m,p+0x2C);put(m,p+0x2C,operation(current,operation(operation(read(m,p+0x118),current,1),read(m,SCALARS[1]),2),0))
 if tick(0x154):
  put(m,p+0x154,draw(RNG)%15,2);sample=draw(FRNG);lower=read(m,p+0x14C);put(m,p+0x150,operation(operation(sample,operation(read(m,p+0x148),lower,1),2),lower,0))
 value=read(m,p+0x24);converted=operation(value,0,32);difference=operation(read(m,p+0x150),converted,1);adjustment=operation(operation(difference,read(m,SCALARS[2]),2),0,13);put(m,p+0x24,u32(value+adjustment));return m,calls,ops,csr,1

def main():
 r=target_packet.ROOT;rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();code={};pins=[]
 for entry,at,n in((g.RNG,0xDAED0,18),(g.FRNG,0xDAF18,25)):
  blob=rom[at:at+4*n];pos=elf_slot_offset(elf,entry,4*n);assert elf[pos:pos+4*n]==blob;code.update(zip(range(entry,entry+4*n,4),struct.unpack('>'+str(n)+'I',blob)));pins.append(dict(entry=hex(entry),words=n,frozen_ELF_and_ROM_exact=True))
 pos=elf_slot_offset(elf,SCALE,4);scale=struct.unpack_from('>I',elf,pos)[0];count=0;seen=set();writes=set()
 for seed,mask,rm in itertools.product(SEEDS,range(8),range(4)):
  c=g.Case(timers=tuple(-1 if mask>>i&1 else 3 for i in range(3)),rm=rm);memory=g.fixture(c);g.put(memory,SEED,seed,8);g.put(memory,SCALE,scale);models=[]
  for words in(g.streams()[0],g.streams()[1]):
   m=Connected(words,c,memory=memory,connected=code).run();want=reference(m.initial,c);assert g.observable(m)==(g.public(want[0],c),*want[1:]),dict(seed=hex(seed),mask=mask,rm=rm,parts=[a==b for a,b in zip(g.observable(m),(g.public(want[0],c),*want[1:]))],actual_FP=m.fp_operations,wanted_FP=want[2]);models.append(m);seen|=m.visits&set(code)
   # Instruction trace attributes helper stores to their actual executing PCs.
   writes|={t[1]for t in m.trace if t[0]=='W'and t[2]==8}
  assert g.state(models[0])==g.state(models[1]);count+=1
 assert seen==set(code)and writes=={SEED},(len(seen),writes)
 q=dict(cases_per_stream=count,streams=2,original_helpers=pins,all43_helper_words_executed=True,seed64_and_original_float_scale_preserved=True,mathematical_seed_and_ordered_FP_reference_equal=True,actual_helpers_only_write_seed=True,target_public_memory_calls_FP_FCSR_and_full_private_states_equal=True,all_four_rounding_modes=True,opaque_mutation_stress_is_separate=True,helper_matching_credit=0,source_installed=target_packet.installed(),matching_credit=0)
 (o/'helpers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
