"""Independent single-precision quad geometry, callback snapshots and real cosine."""
import json,math,struct,sys
from pathlib import Path
from dataclasses import dataclass,replace
from tools.experiments.game_vertex_quad_1513e13c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_actor_direction_point_oracle import DirectionOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x1513E13C;COS=0x151423D8;TABLE=0x8009A220;RECORD=0x20000;ALT=0x22000;BYTES=0x158
SYMS={'func_151423D8':COS,'D_8009A220':TABLE};OFFSETS=(0x40,0x42,0x44,0x50,0x52,0x54,0x60,0x62,0x64,0x70,0x72,0x74)
u32=lambda v:v&0xFFFFFFFF
add=lambda a,b:bits(floating(a)+floating(b))
sub=lambda a,b:bits(floating(a)-floating(b))
mul=lambda a,b:bits(floating(a)*floating(b))
@dataclass(frozen=True)
class Case:
 coordinates:tuple=(0x41480000,0xC1C80000,0x422E0000,0x42DC0000,0x42A00000)
 angle:int=0xA5
 scripted:tuple=()
 effects:int=0
 phase:int=0
 seed:int=0
 record:int=RECORD
def table():
 data=(root/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(data,TABLE,260);return tuple(struct.unpack_from('>65I',data,at))
def cos(word,values):
 n=word&255;index=64-(n&63)if n&64 else n&63;v=values[index];return v if n&192 in(0,192)else v^0x80000000
def arguments(c):return(c.record,*c.coordinates,c.angle)
def fixture(c,s=SYMS,values=None):
 values=table()if values is None else values;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,1024)}
 for p in(c.record,ALT):m.update({p+i:(i*29+c.seed*11+0x59)&255 for i in range(-8,BYTES+8)})
 for i,v in enumerate(values):put(m,s['D_8009A220']+4*i,v)
 return m
def snapshot(m,c):return tuple(bytes(m[p+i]for i in range(BYTES))for p in(c.record,ALT))
def effects(m,c,stage):
 home=STACK+c.phase
 if c.effects&1:m[c.record]^=0x55;put(m,c.record+0x40,0x1200+stage,2)
 if c.effects&2:
  vals=(bits(-14.25-stage),bits(-5.75),bits(88.5+stage),bits(13.0),bits(9.0))
  for i,v in enumerate(vals,1):put(m,home+4*i,v)
 if c.effects&4 and stage==2:put(m,home,ALT)
 if c.effects&8 and stage==1:m[home+27]=(c.angle^0x55)&255
def geometry(coords,sine,cosine):
 x,y,z,w,d=coords;a=mul(w,cosine);b=mul(d,sine);c=mul(d,cosine);e=mul(w,sine);xp=add(x,a);xm=sub(x,a);zp=add(z,c);zm=sub(z,c)
 words=(sub(xp,b),y,add(zp,e),sub(xm,b),y,sub(zp,e),add(xm,b),y,sub(zm,e),add(xp,b),y,add(zm,e));result=[]
 for word in words:
  n=math.trunc(floating(word));assert -0x80000000<=n<0x80000000,'Outside qualified signed conversion';result.append(n&65535)
 return tuple(result)
def reference(initial,c,s=SYMS,values=None,connected=False):
 values=table()if values is None else values;m=dict(initial);home=STACK+c.phase
 for i,v in enumerate(arguments(c)[:4]):put(m,home+4*i,v)
 calls=[];observations=[];returns=[]
 for stage in(1,2):
  angle=m[home+27];a=(angle-64)&255 if stage==1 else angle;calls.append((s['func_151423D8'],(a,)));observations.append(snapshot(m,c));returns.append(c.scripted[stage-1]if c.scripted else cos(a,values))
  if not connected:effects(m,c,stage)
 coords=tuple(read(m,home+4*i)for i in range(1,6));p=read(m,home)
 for at,value in zip(OFFSETS,geometry(coords,*returns)):put(m,p+at,value,2)
 return m,calls,observations
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c=Case(),entry=ENTRY,s=SYMS,values=None,connected=None):
  super().__init__(ws,memory,c,entry=entry,s=s,arguments=arguments(c),connected=connected);self.values=table()if values is None else values;self.before=self.r[:];self.before_f=self.f[:];self.initial=dict(self.memory);self.observations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:return DirectionOracle.execute(self,w)
  return super().execute(w)
 def record_call(self,t):
  assert t==self.syms['func_151423D8'];self.calls.append((t,tuple(self.arguments(1))));self.observations.append(snapshot(self.memory,self.case));self.events.append(('CALL',t,self.calls[-1][1]))
 def hook(self,t):
  stage=len(self.calls);assert stage in(1,2);c=self.case;value=c.scripted[stage-1]if c.scripted else cos(self.calls[-1][1][0],self.values);effects(self.memory,c,stage)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=value;self.hi,self.lo=0xA5000010,0xA5000011
def words(p,s=SYMS):
 raw,fs,rs=parse_object(p);f=fs['func_1513E13C'];a,n=f['value'],f['size'];return bound_blob(raw[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s)
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}
def check(m,c,s=SYMS,values=None,connected=False):
 want,calls,observations=reference(m.initial,c,s,values,connected);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),('Quad/callback contract',c)
 assert all(m.memory[p]==want[p]for p in m.initial if STACK+c.phase<=p<STACK+c.phase+512),'Caller storage/stack output changed'
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def cases():
 result=[replace(Case(),angle=0xABCD0000+i,phase=(i&1)*8,seed=i%3)for i in range(256)]
 coords=((0.,-0.,0.,0.,0.),(12.5,-25.,43.5,110.,80.),(-12.75,-5.75,23.75,-110.,80.),(32767.75,-32769.75,-32768.75,1024.,4096.),(16777216.,0.,16777216.,1.,1.),(1000000.,-2147483648.,-1000000.,1000000.,1000000.))
 for p in coords:
  for a in(0,1,31,32,63,64,65,127,128,191,192,255):
   for effect in(0,1,2,4,8,15):result.append(replace(Case(),coordinates=tuple(bits(v)for v in p),angle=a,effects=effect,phase=8,scripted=(bits(.75),bits(-.25))if effect&1 else()))
 for a in(0,32,64,128,192,255):result.append(replace(Case(),angle=a,record=STACK+128,seed=2))
 return result
def helper(s=SYMS):
 rom=(root/'conker/conker.us.bin').read_bytes();ws=list(struct.unpack_from('>27I',rom,COS-0x15000000+0x2D4B0));image=(root/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(image,COS,108);assert image[at:at+108]==struct.pack('>27I',*ws)
 raw=bytearray(struct.pack('>27I',*ws));refs={}
 for i,w in enumerate(ws):
  if w>>26==15 and w&65535==0x800A:refs[i*4]=[('R_MIPS_HI16','D_8009A220')];struct.pack_into('>I',raw,4*i,w&0xFFFF0000)
  elif w>>26 in(9,49)and w&65535==0xA220:refs[i*4]=[('R_MIPS_LO16','D_8009A220')];struct.pack_into('>I',raw,4*i,w&0xFFFF0000)
 assert refs=={68:[('R_MIPS_HI16','D_8009A220')],80:[('R_MIPS_LO16','D_8009A220')],84:[('R_MIPS_HI16','D_8009A220')],92:[('R_MIPS_LO16','D_8009A220')]},refs;ws=bound_blob(bytes(raw),refs,s);return dict(zip(range(s['func_151423D8'],s['func_151423D8']+108,4),ws))
def main():
 values=table();assert(values[0],values[64])==(0x3F800000,0);code=helper();paths={'raw':out/'qualified-owner.o','normalized':out/'qualified-padded.o','retail':out/'retail-reference.o'};counts={};coverage={};connected=0;rebases=0
 for label,p in paths.items():
  ws=words(p);seen=set()
  for c in cases():m=Oracle(ws,fixture(c,values=values),c,values=values);m.run();check(m,c,values=values);seen.update(m.visits)
  counts[label]=len(cases());coverage[label]=len([pc for pc in seen if ENTRY<=pc<ENTRY+4*len(ws)]);assert coverage[label]==len(ws)
  for angle in range(256):c=replace(Case(),angle=angle,phase=(angle&1)*8);m=Oracle(ws,fixture(c,values=values),c,values=values,connected=code);m.run();check(m,c,values=values,connected=True);connected+=1
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={'func_151423D8':0x15200000,'D_8009A220':0x80300000+low}
  for label,p in paths.items():
   for phase in(0,8):
    c=replace(Case(),angle=255,phase=phase);m=Oracle(words(p,s),fixture(c,s,values),c,entry=ENTRY+0x4000,s=s,values=values,connected=helper(s));m.run();check(m,c,s,values,True);rebases+=1
 report=dict(cases_per_body=counts,total=sum(counts.values()),root_visited_words=coverage,original_helper_cases=connected,independent_rebases=rebases,all_256_angles=True,scripted_nontrig_returns=True,guest_only_parameter_home_mutations=True,caller_stack_record=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');(out/'trig-table.json').write_text(json.dumps(values)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
