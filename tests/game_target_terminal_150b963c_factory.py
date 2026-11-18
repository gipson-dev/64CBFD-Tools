"""Execute the actual factory wrapper and memcpy; deep providers stay bounded."""
from dataclasses import replace
import itertools,json,struct
from tools.experiments import game_target_terminal_150b963c_match as s
from tools.tests import game_target_terminal_150b963c_oracle as o
from tools.match_progress import load_elf_functions
BASE,SETUP,RELEASE=0x1513D2F0,0x1513D6FC,0x1516972C

def run(state):
 live,_,_=load_elf_functions(str(s.FROZEN/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 retail=struct.unpack_from('>53I',state['rom'],0x16AA44);copy=struct.unpack_from('>11I',state['rom'],0x22EC0);assert tuple(live['memcpy'])==copy
 variants={'retail-wrapper':retail,'production-wrapper':tuple(live['func_1513D594'])};seen={k:set()for k in variants};copy_seen=set();count=0
 normalized=s.normalizer.derive(state['raw_words']);assert normalized==state['retail_words']
 programs=(('retail',state['retail_words'],'retail'),('source',state['raw_words'],'raw'),('normalized',normalized,'retail'))
 class Connected(o.Oracle):
  def __init__(self,words,c,kind,allocation,setup,wrapper):
   super().__init__(words,c,kind);self.allocation=allocation;self.setup=setup;self.code.update(zip(range(o.FACTORY,o.FACTORY+4*len(wrapper),4),wrapper));self.code.update(zip(range(o.COPY,o.COPY+44,4),copy))
  def record_call(self,t):
   if t in(BASE,SETUP,RELEASE):self.calls.append((t,tuple(map(o.g.u32,self.arguments({BASE:12,SETUP:7,RELEASE:1}[t])))))
   else:super().record_call(t)
  def hook(self,t):
   if t not in(BASE,SETUP,RELEASE):return super().hook(t)
   if t==BASE:o.factory_effect(self.memory,replace(self.cc,success=self.allocation),self.roles);value=o.OUTPUT if self.allocation else 0;n=12
   elif t==SETUP:value=self.setup;n=7
   else:value=1;n=1
   for i in range(max(4,n)):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=value
 for flags,allocation,setup,mutation,phase in itertools.product(range(4),(0,1),(0,1),(0,1,2,4,8,16,32,63),(0,8)):
  c=o.Case(distance=o.g.bits(10.),speed=o.g.bits(15.),random_bit=0,query=1,success=allocation and setup,mutation=mutation,phase=phase,flags=flags)
  for label,wrapper in variants.items():
   for name,words,kind in programs:
    want,calls,obs,result=o.reference(o.fixture(c,kind),c,kind);at=next(i for i,(t,_)in enumerate(calls)if t==o.FACTORY);args=calls[at][1]
    extra=[(BASE,(args[0],args[1],args[2],args[3],args[4],12,args[5],args[11],args[12],args[14]+24,args[15],args[16]))]
    if allocation:
     extra.append((SETUP,(o.OUTPUT+0x110,args[6],args[7],args[8],args[9],args[10],args[13])))
     if not setup:
      extra.append((RELEASE,(o.OUTPUT,)))
      burst=next(data for tag,data in obs if tag=='burst')
      for i,value in enumerate(burst):want[o.OUTPUT+0x10+i]=value
    calls=calls[:at+1]+extra+calls[at+1:]
    m=Connected(words,c,kind,allocation,setup,wrapper);before,fp=m.r[:],m.f[:];m.run()
    assert(o.public(m.memory),m.calls,m.obs,m.r[2])==(want,calls,obs,result),(label,name,c,m.calls,calls)
    assert m.r[16:24]==before[16:24]and m.r[28:]==before[28:]and m.f[20:]==fp[20:]
    seen[label].update(pc for pc in m.visits if o.FACTORY<=pc<o.FACTORY+4*len(wrapper));copy_seen.update(pc for pc in m.visits if o.COPY<=pc<o.COPY+44)
  count+=1
 report=dict(passes=True,cases=count,parent_programs=3,wrapper_variants={k:dict(words=len(v),visited=len(seen[k]))for k,v in variants.items()},production_wrapper_is_retail=variants['production-wrapper']==retail,memcpy_words_visited=len(copy_seen),allocation_setup_release_query_and_spray_modeled=True,parent_allocation_and_setup_failure_paths=True,nonnull_asset_path=True,saved_abi_checked=True,source_installed=False,c_match_credit=0)
 (s.OUT/'factory-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
