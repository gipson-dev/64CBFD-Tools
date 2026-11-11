import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_channel_preset_initializer_1500ad84_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
norm=p
from tools.experiments import game_channel_preset_initializer_1500ad84_match as p
ENTRY=0x1500AD84;PRESET=0x80095CE0;BASE=0x80095CC4;A=0x800DDBD0;B=0x800DDBE0;C=0x800DDBF0;KEY=0x800DDBC0;OPT=0x800DDC80;VALUES=0x800BE438;ZERO=0x800BE478;PAIRS=0x800DDC20;MASKS=(0x800DDC00,0x800DDC04,0x800DDC08)
@dataclass(frozen=True)
class Case:
 slot:int;preset:int;flags:int;options:int;value:int;seed:int=0;phase:int=0
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-256,512)}
 for at,n in ((PRESET,2560),(BASE,16),(A,16),(B,16),(C,16),(KEY,16),(OPT,16),(VALUES,64),(ZERO,32),(PAIRS,32),*((x,4)for x in MASKS)):
  m.update({at+i:(i*19+c.seed*11+37)&255 for i in range(n)})
 at=PRESET+10*c.preset;m[at]=c.flags;m[at+1]=c.value;put(m,at+4,-12345,2);put(m,at+6,23456,2)
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-256<=a<STACK+512}
def reference(c,initial):
 m=dict(initial);slot=c.slot
 if c.preset!=255:
  value=c.value;m[A+slot]=value
  if c.flags&0x10:value=(value-1)&255;m[A+slot]=value;m[B+slot]=value
  else:m[B+slot]=0
  m[C+slot]=2 if c.flags&0x80 else 1
  put(m,VALUES+4*slot,read(m,PRESET+10*c.preset+4,2),2);put(m,VALUES+4*slot+2,read(m,PRESET+10*c.preset+6,2),2)
  m[KEY+slot]=c.preset;m[OPT+slot]=c.options&0x7f
  for at,enabled in zip(MASKS,(c.options&0x80,c.flags&1,c.flags&8)):
   if enabled:put(m,at,read(m,at)|(1<<slot))
 else:m[A+slot]=0
 base=m[BASE+slot];put(m,ZERO+slot*2,0,2);m[PAIRS+slot*2]=base;m[PAIRS+slot*2+1]=base
 return m
class Oracle(FactoryOracle):
 def __init__(self,ws,c):
  super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(c.slot,c.preset,c.options));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected helper',hex(t)))
def words(tag):
 text,fs,rs=parse_object(out/(tag+'.o'));a,n=fs['func_1500AD84']['value'],fs['func_1500AD84']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};return bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es})
def cases():
 fs=[sum(bit for bit,on in zip((1,8,16,128),selection)if on)for selection in itertools.product((0,1),repeat=4)]+[0x66,0xff]
 return [Case(slot,preset,flags,options,value,i%3)for i,(slot,preset,flags,options,value)in enumerate(itertools.product((0,1,14),(0,2,254,255),fs,(0,0x80,0xff,0x100,0xffff),(0,1,255)))]
def main():
 candidate=words('independent-selected');retail=struct.unpack_from('>97I',(root/'conker/conker.us.bin').read_bytes(),0x38234);raw,refs=p.payload(out/'independent-selected.o');fixed,fre=norm.normalize(raw,refs);lookup={v[1]:v[2][1]for v in symbol_rows((out/'frozen/conker/build/conker.us.elf').read_bytes())};fixed=bound_blob(fixed,fre,{nm:lookup[nm]for es in fre.values()for _,nm in es});assert tuple(fixed)==retail;seen=set();cs=cases()
 for c in cs:
  machines=[]
  for ws in(retail,candidate,fixed):
   m=Oracle(ws,c);m.run();assert public(m.memory)==public(reference(c,m.initial)),(c,'memory');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];machines.append(m)
  assert public(machines[0].memory)==public(machines[1].memory);assert (machines[0].memory,machines[0].r,machines[0].f,machines[0].trace)==(machines[2].memory,machines[2].r,machines[2].f,machines[2].trace);seen.update(machines[0].visits)
 report=dict(cases=len(cs),retail_words_visited=sum(ENTRY+4*i in seen for i in range(97)),memory_and_saved_abi_match=True,normalized_complete_state=True,valid_channel_preset_only=True,source_installed=False)
 (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
