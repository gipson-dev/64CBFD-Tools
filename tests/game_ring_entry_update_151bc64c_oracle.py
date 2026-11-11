import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_ring_entry_update_151bc64c_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x151BC64C;OWNER=0x30000;RECORDS=0x50000;TICK=0x800BE9E4
s8=lambda x:((x&255)^128)-128
s16=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 cap:int;current:int;end:int;count:int;flags:int;timer:int;tick:int;phase:int=0;seed:int=0
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-256,512)};m.update({OWNER+i:(i*19+37)&255 for i in range(0xA0)});m.update({RECORDS+i:(i*13+11)&255 for i in range(160)})
 m[OWNER+0x25]=c.cap;m[OWNER+0x2c]=c.count&255;m[OWNER+0x2d]=c.current;m[OWNER+0x2e]=c.end;put(m,OWNER+0x1e,c.flags,2);put(m,OWNER+0x94,RECORDS);put(m,TICK,c.tick)
 for i in range(c.cap):put(m,RECORDS+20*i+12,c.timer,2);m[RECORDS+20*i+14]=(i*42+33)&255
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-256<=a<STACK+512}
def reference(c):
 m=fixture(c);count=c.count;current=c.current;index=c.end
 if count<2 and c.flags&8:return public(m),0
 while index!=current:
  index-=1
  if index<0:index=c.cap-1
  p=RECORDS+index*20;timer=s16(read(m,p+12,2)-c.tick);put(m,p+12,timer,2)
  if timer<0:
   while index!=current:
    current=s8(current+1)
    if current==c.cap:current=0
    count=s8(count-1);m[OWNER+0x2d]=current&255;m[OWNER+0x2c]=count&255
  elif timer<10:
   value=timer*25
   if value<m[p+14]:m[p+14]=value&255
 if count>0:
  for i in range(12):m[OWNER+0x54+i]=m[RECORDS+20*current+i]
 else:
  for i in range(12):m[OWNER+0x54+i]=0
 return public(m),1
class Oracle(FactoryOracle):
 def __init__(self,ws,c):super().__init__(ws,fixture(c),c,entry=ENTRY,arguments=(OWNER,));self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected helper',hex(t)))
def cases():
 result=[]
 for cap in (1,2,4,7):
  for current,end,count0,flags,timer,tick in itertools.product((0,cap-1),(0,cap-1),(0,1,2,cap),(0,8),(-10,0,9,32767),(-1,0,1,32767)):
   result.append(Case(cap,current,end,count0,flags,timer,tick))
 for cap,timer,tick in itertools.product((2,7),(-32768,-1,0,1,32767),(-2147483648,2147483647)):
  result.append(Case(cap,0,cap-1,cap,0,timer,tick))
 return result
def main():
 tag='independent-selected';data,fs,rs=parse_object(out/(tag+'.o'));a,n=fs['func_151BC64C']['value'],fs['func_151BC64C']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>82I',(root/'conker/conker.us.bin').read_bytes(),0x1E9AFC);seen=set();count=0
 for c in cases():
   expected,answer=reference(c);models=[Oracle(ws,c)for ws in (retail,candidate)]
   for label,m in zip(('retail','candidate'),models):
    m.run();actual=public(m.memory);assert actual==expected,(c,label,'memory',[(hex(k),expected.get(k),actual.get(k))for k in expected if expected.get(k)!=actual.get(k)][:16]);assert m.r[2]==answer,(c,'return');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
   seen.update(models[0].visits);count+=1
 report=dict(variant=tag,cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(82)),valid_disjoint_ring_storage=True,source_installed=False);(out/('guest_'+tag+'_screen.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
