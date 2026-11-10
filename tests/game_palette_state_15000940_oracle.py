"""Independent palette initializer model; original code remains authoritative."""
import json,struct,sys,itertools
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-next-15000940-match'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.experiments import game_palette_state_15000940_match as p
from tools.experiments import game_palette_state_15000940_match as n
ENTRY=0x15000940;ROM=0x2DDF0;WORDS=95;CONTEXT=0x30000
NAMES=('D_800B0DF0','D_800A2CD0','D_800A2CE8','D_800A2CEC','D_800A2D04','D_800D9E70','D_800D9E88','D_800D9E98','D_800D9EA8','D_800D9EB4','D_800D9EB7','D_800D9EB8','D_800D9EC4')
@dataclass(frozen=True)
class Case:
 index:int=0
 unused:int=0
 phase:int=0
 seed:int=0
 generic:int=0
 alias:int=0
def symbols():return {n:int(n[2:],16)for n in NAMES}
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def fixture(c,s=None):
 s=s or symbols();m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for name,size in (('D_800B0DF0',4),('D_800A2CD0',0x1000),('D_800A2CE8',0x400),('D_800A2CEC',0x400),('D_800A2D04',0x400),('D_800D9E70',24),('D_800D9E88',12),('D_800D9E98',12),('D_800D9EA8',12),('D_800D9EB4',3),('D_800D9EB8',12)):
  base=s[name]-16;m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(size+32)})
 m.update({CONTEXT+i:(i*31+c.seed)&255 for i in range(0x50)});put(m,s['D_800B0DF0'],CONTEXT);put(m,CONTEXT+0x29,c.index,1)
 if not c.generic:
  elf=(out/'frozen/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,0x800A2CD0,0x54);preset=elf[at:at+0x54]
  for name,start,size in (('D_800A2CD0',0,24),('D_800A2CE8',24,4),('D_800A2CEC',28,24),('D_800A2D04',52,32)):
   for i,v in enumerate(preset[start:start+size]):m[s[name]+i]=v
 else:
  for i,v in enumerate((c.index,(c.index*73+129)&255,(c.index*197+255)&255)):put(m,s['D_800A2CD0']+3*c.index+i,v,1)
 return m
def public(m):return {a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def reference(initial,c,s=None):
 s=s or symbols();m=dict(initial);idx=read(m,read(m,s['D_800B0DF0'])+0x29,1);a=s['D_800A2CD0']+idx*3
 first=s['D_800A2CE8']+3*read(m,a,1);second=s['D_800A2CEC']+3*read(m,a+1,1);third=s['D_800A2D04']+3*read(m,a+2,1)
 for row in range(4):
  for channel in range(3):
   tv=read(m,third+channel,1);fv=read(m,first+channel,1);sv=read(m,second+channel,1);i=row*3+channel
   for p,v,n in ((s['D_800D9E70']+2*i,0,2),(s['D_800D9EB8']+i,0,1),(s['D_800D9EB4']+channel,tv,1),(s['D_800D9EA8']+i,tv,1),(s['D_800D9E88']+i,fv,1),(s['D_800D9E98']+i,sv,1)):put(m,p,v,n)
 return m
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c,s=None,entry=ENTRY,connected=None):
  super().__init__(ws,memory,c,entry=entry,s=s or symbols(),arguments=(c.unused,),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):raise AssertionError(('Unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('Unexpected hook',hex(t)))
def words(path,s=None):
 text,fs,rs=parse_object(path);a,n=fs['func_15000940']['value'],fs['func_15000940']['size'];return bound_blob(text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s or symbols())
def run(ws,c,s=None):
 m=Oracle(ws,fixture(c,s),c,s);m.run();assert public(m.memory)==public(reference(m.initial,c,s)),c
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],(c,'ABI');assert not m.calls
 return m
def cases():
 cs=[Case(index=i,unused=u,phase=p,seed=(i+p+u)%7)for i,u,p in itertools.product(range(8),(0,0x80000000,0xFFFFFFFF),(0,8))]
 cs +=[Case(index=i,generic=1,seed=i%7,phase=(i&1)*8,unused=(i*0x132FA583)&0xFFFFFFFF)for i in range(256)]
 return cs
def main():
 truth=struct.unpack_from('>95I',(root/'conker/conker.us.bin').read_bytes(),ROM);programs=[truth]
 if(out/'selected.o').is_file():
  raw,rs=p.payload(out/'selected.o');normal,nrefs=n.normalize(raw,rs);programs=[words(out/'selected.o'),bound_blob(normal,nrefs,symbols()),truth]
 cs=cases();seen=set();pairs=0
 for c in cs:
  models=[run(ws,c)for ws in programs]
  if len(models)==3:
   raw,a,b=models;assert(raw.memory,raw.trace)==(b.memory,b.trace),(c,'raw trace');assert(a.memory,a.r,a.f,a.trace,a.calls,a.current_pc,a.delay_of)==(b.memory,b.r,b.f,b.trace,b.calls,b.current_pc,b.delay_of),(c,'machine');pairs+=1
  seen.update((pc-ENTRY)//4 for pc in models[0].visits if ENTRY<=pc<ENTRY+380)
 r=dict(cases=len(cs),executions=len(cs)*len(programs),coverage=len(seen),missing=[i for i in range(95)if i not in seen],complete_machine_pairs=pairs,actual_presets=48,generic_byte_index_cases=256,generic_outside_actual_table_domain_guest_only=True,return_type_not_inferred_from_residual_V0=True)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
