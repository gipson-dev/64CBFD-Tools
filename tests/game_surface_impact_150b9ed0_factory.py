"""Connect the real emitter wrapper; allocation/setup/release stay opaque."""
import itertools,json,struct
from tools.experiments import game_surface_impact_150b9ed0_match as s
from tools.tests import game_surface_impact_150b9ed0_oracle as o
from tools.match_progress import load_elf_functions
BASE,SETUP,RELEASE=0x1513c350,0x1513e2ac,0x1516972c
OUTPUT=0x50000

def run(state):
 live,_,_=load_elf_functions(str(s.FROZEN/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 retail=struct.unpack_from('>59I',state['rom'],0x169b00)
 variants={'retail-wrapper':retail,'production-wrapper':tuple(live['func_1513C650'])}
 seen={k:set()for k in variants};count=0
 normalized=s.normalizer.derive(state['raw_words']);assert normalized==state['retail_words']
 programs=(('retail',state['retail_words'],'retail'),('source',state['raw_words'],'raw'),('normalized',normalized,'retail'))
 class Connected(o.Oracle):
  def __init__(self,words,c,kind,allocation,setup,wrapper):
   super().__init__(words,c,kind);self.allocation=allocation;self.setup=setup;self.parent_args=None;self.wrapper_words=len(wrapper)
   self.code.update(zip(range(o.FACTORY,o.FACTORY+4*len(wrapper),4),wrapper))
  def record_call(self,t):
   if t in(BASE,SETUP,RELEASE):
    a=tuple(map(o.u32,self.arguments({BASE:11,SETUP:9,RELEASE:1}[t])));self.deep_args=a
    if t==BASE:
     assert self.parent_args is not None
     point=b''.join(struct.pack('>I',v)for v in self.parent_args[4:7]);assert o.data(self.memory,a[7],12)==point
     assert self.r[29]+44<=a[7]and a[7]+12<=self.home-(328 if self.kind=='raw'else 344)
     a=(*a[:7],('WRAPPER_POSITION',),*a[8:])
    self.calls.append((t,a))
   else:
    super().record_call(t)
    if t==o.FACTORY:self.parent_args=self.calls[-1][1]
  def hook(self,t):
   if t not in(BASE,SETUP,RELEASE):return super().hook(t)
   if t==BASE:o.escaped_effect(self.memory,self.cc,self.roles,12);value=OUTPUT if self.allocation else 0;n=11
   elif t==SETUP:value=self.setup;n=9
   else:value=1;n=1
   for i in range(max(4,n)):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=value
 for i,(mode,allocation,setup,mutation,phase)in enumerate(itertools.product((0,1,128,255),(0,1),(0,1),(0,1,2,4,8,15),(0,8))):
  c=o.Case(mode=0xabcd0000|mode,tag=o.u32(0x87654321+i*0x1020304),mutation=mutation,phase=phase,coords=i%8,corrupt=i%2,seed=i)
  for label,wrapper in variants.items():
   for name,words,kind in programs:
    want,calls,obs=o.reference(o.fixture(c,kind),c,kind);at=next(j for j,(t,_)in enumerate(calls)if t==o.FACTORY);a=calls[at][1]
    extra=[(BASE,(a[0],0,a[1],a[2],a[10],a[11],a[12],('WRAPPER_POSITION',),a[13],a[14],a[15]))]
    if allocation:
     extra.append((SETUP,(OUTPUT,0,a[3],*a[4:10])))
     if not setup:extra.append((RELEASE,(OUTPUT,)))
    calls=calls[:at+1]+extra+calls[at+1:]
    m=Connected(words,c,kind,allocation,setup,wrapper);gpr,fpr=m.r[:],m.f[:];m.run()
    assert(o.public(m.memory),m.calls,m.obs)==(want,calls,obs),(label,name,c,m.calls,calls)
    assert m.r[16:24]==gpr[16:24]and m.r[28:]==gpr[28:]and m.f[20:]==fpr[20:],(label,name,c,'saved ABI')
    seen[label].update(pc for pc in m.visits if o.FACTORY<=pc<o.FACTORY+4*len(wrapper))
  count+=1
 report=dict(passes=True,cases=count,parent_programs=3,wrapper_variants={k:dict(words=len(v),visited=len(seen[k]))for k,v in variants.items()},production_wrapper_is_retail=variants['production-wrapper']==retail,wrapper_point_bytes=12,allocation_setup_release_modeled=True,parent_allocation_and_setup_failure_paths=True,saved_ABI=True,source_installed=False,c_match_credit=0)
 (s.OUT/'factory-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
