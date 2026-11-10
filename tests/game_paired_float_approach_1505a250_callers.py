"""Nine original argument-setup windows, with real leaf code and delay slots."""
import itertools,json,struct
from dataclasses import replace
from tools.tests import game_paired_float_approach_1505a250_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
WINDOWS=((0x15051514,0x15051544,0x164),(0x15051BD0,0x15051BF4,0x164),(0x1505205C,0x150520E0,0x164),(0x1505823C,0x15058298,0x174),(0x150592F4,0x15059324,0x164),(0x15064728,0x15064758,0x16C),(0x150C35B0,0x150C35D0,0x164),(0x150D974C,0x150D97A8,0x164),(0x150D97EC,0x150D9848,0x164))
CONSTANTS=(0x80099300,0x8009932C,0x800994B4,0x800997D8,0x800A0B74,0x800A0B78,0x800A0B7C,0x800A0B80,0x800A0B84)
class CallerOracle(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY and not self.calls
  args=(self.f[12],self.f[14],self.r[6],self.r[7],self.arguments(5)[4]);self.calls.append((t,args));self.events.append(('CALL',t,args));self.captured=dict(self.memory)
  effective=replace(self.c,target_x=args[0],target_z=args[1],rate=args[2]);self.expected=g.reference(self.captured,effective,addresses=args[3:])[0];self.outputs=args[3:]
def machine(rom,elf,ws,c,index):
 start,end,offset=WINDOWS[index];actor=g.OUTPUT+8-offset;home=g.STACK+c.phase
 mem={actor+i:(i*19+c.seed*7+90)&255 for i in range(812)};mem.update(g.fixture(c));g.put(mem,actor+0xB8,g.bits(10. if c.seed&1 else 50.));g.put(mem,actor+0x54,g.bits(.25));g.put(mem,actor+0x78,0x8000 if c.seed&2 else 0,2)
 for a,v in((actor+0x14,c.target_x),(actor+0x1C,c.target_z),(actor+0x3C,c.x),(home+0x68,c.target_x),(home+0x64,c.rate),(home+0x6C,c.target_x),(home+0x40,c.target_z),(home+0x44,c.target_x),(home+0x2C,c.rate),(home+0xF0,0),(home+0xF8,0),(home+0x14C,g.bits(2. if c.seed&1 else .5)),(home+0x154,c.rate),(home+0x158,g.bits(g.floating(c.rate)*2.))):g.put(mem,a,v)
 g.put(mem,home+0x68,c.target_z if index==1 else c.target_x);g.put(mem,home+0x64,c.target_z if index==3 else c.rate);g.put(mem,home+0x78,0x4000,2)
 for a in CONSTANTS:
  at=elf_slot_offset(elf,a,4);mem.update({a+i:v for i,v in enumerate(elf[at:at+4])})
 code=dict(zip(range(g.ENTRY,g.ENTRY+344,4),ws));code[end]=0;window=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0)
 m=CallerOracle.__new__(CallerOracle);m.c=c;m.step_symbol=g.TIMESTEP
 FactoryOracle.__init__(m,window,mem,c,entry=start,arguments=(0x87654321,0x76543210,c.rate,g.OUTPUT+8,g.OUTPUT+12),connected=code)
 m.r[1]=0x800A0000;m.r[16]=actor;m.r[17]=actor;m.r[10]=0x80000 if c.seed&1 else 0
 for f,v in((0,c.target_z),(2,c.rate),(4,g.bits(.25)),(6,g.bits(.5)),(8,g.bits(2.5)),(10,c.rate),(12,c.target_x),(14,c.target_z),(16,c.target_x),(18,c.target_z),(20,g.bits(60.)),(22,g.bits(g.floating(c.rate)*40.))):m.f[f]=v
 m.before=m.r[:];m.before_f=m.f[:];m.saved_f=m.f[20:].copy();m.initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(end,);return m
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();elf=(g.out/'frozen/conker/build/conker.us.elf').read_bytes();programs=(g.words(g.out/'selected.o'),struct.unpack_from('>86I',rom,0x87700))
 cs=[g.Case(x=g.bits(x),z=g.bits(z),target_x=g.bits(tx),target_z=g.bits(tz),rate=g.bits(rate),seed=i%4,phase=(i&1)*8)for i,(x,z,tx,tz,rate)in enumerate(itertools.product((-20.,0.,20.),(-20.,0.,20.),(-2.,0.,2.),(-2.,0.,2.),(.5,4.)))]
 counts={};runs=pairs=0
 for index,(start,end,_)in enumerate(WINDOWS):
  seen=set()
  for c in cs:
   models=[]
   for ws in programs:
    m=machine(rom,elf,ws,c,index)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller did not reach its recorded continuation')
    assert len(m.calls)==1;changed=set()
    for a in m.outputs:
     assert g.canonical(g.read(m.memory,a))==g.canonical(g.read(m.expected,a)),(index,c,hex(a));changed.update(range(a,a+4))
    assert all(m.memory[a]==v for a,v in g.public(m.expected).items()if a not in changed),(index,c,'public')
    assert m.r[29]==g.STACK+c.phase and m.r[16:24]==m.before[16:24]and m.f[20:]==m.before_f[20:]
    seen.update(pc for pc in m.visits if start<=pc<end);runs+=1;models.append(m)
   a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls),(index,c);pairs+=1
  wanted=set(range(start,end,4));assert seen==wanted,(index,sorted(wanted-seen));counts[hex(start)]=len(seen)
 report=dict(cases_per_window=len(cs),executions=runs,full_state_and_trace_pairs=pairs,window_coverage=counts,total_window_words=sum(counts.values()),all_nine_direct_call_sites=True,mixed_FP_GPR_and_stack_arguments=True,staged_caller_inputs=True,full_parent_algorithms_qualified=False)
 (g.out/'callers.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
