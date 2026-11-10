"""Independent fixed-height/triangle model, literal context selection and bounded query providers."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from functools import lru_cache
from pathlib import Path
from tools.experiments.game_highest_height_150450cc_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import parse_object
ENTRY,CONTEXT,SELECT,SCAN=0x150450CC,0x1510F800,0x150A49F4,0x150A3A70
POS,OUTPUT,ALTERNATE,TRIANGLES,METADATA=0x90000,0xA0000,0xA1000,0xB0000,0xD0020
SYMS=dict(D_80098D44=0x80098D44,D_800DBE68=0x800DBE68,D_800DBE6C=0x800DBE6C,D_800DBE70=0x800DBE70,D_800DBE74=0x800DBE74,D_800D3300=0x800D3300,D_800DBE5C=0x800DBE5C,D_800DBE3C=0x800DBE3C,func_1510F800=CONTEXT,func_150A3A70=SCAN)
CONTEXT_ROWS=((0x800DBDD8,0x800DBE3C),(0x800DBDE8,0x800DBE40),(0x800DBDF8,0x800DBE44),(0x800DBE08,0x800DBE48),(0x800DBE18,0x800DBE4C))
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 position:tuple=(0xC14C0000,0x41200000,0x41BE0000)
 threshold:int=0
 heights:tuple=(256,512,768,1024)
 count:int=4
 flags:int=165
 metadata:bool=True
 mutation:int=0
 real_context:bool=False
 vertex_index:int=1
 base_index:int=0
 alias:int=0
 home_selected:int=-2
 home_output:bool=False
 home_threshold:int=-1
 phase:int=0
def pos(c):return OUTPUT if c.alias==1 else POS
def vertex(row,axis):return 0xC0000+row*0x400+axis*0x100+32
def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+165)&255 for i in range(-512,512)}
 for p,n in((POS-16,48),(OUTPUT-16,68),(ALTERNATE-16,68),(TRIANGLES-16,128),(METADATA-32,96)):
  m.update({p+i:(i*29+91)&255 for i in range(n)})
 for row in range(8):
  for axis in range(3):
   p=vertex(row,axis);m.update({p+i:(i*13+row*37+axis*19+5)&255 for i in range(-32,80)})
   for index in range(-2,3):
    for k in range(3):put(m,p+index*16+k*2,(-32768+row*731+axis*113+index*17+k*32701)&65535,2)
   put(m,TRIANGLES+row*12+axis*4,OUTPUT+4 if c.alias==2 and axis==0 else p)
  p=s['D_800D3300']+row*16;put(m,p,c.heights[row%len(c.heights)]);put(m,p+4,TRIANGLES+row*12);put(m,p+8,0 if c.alias==2 else c.vertex_index);put(m,p+12,0x76543210+row)
 for i in range(-8,16):put(m,METADATA+i*4,0x81230000+(i&65535))
 m[OUTPUT+28]=c.flags;m[ALTERNATE+28]=c.flags^128
 for k,v in enumerate(c.position):put(m,pos(c)+k*4,v)
 put(m,s['D_80098D44'],0xC61C4000);put(m,s['D_800DBE5C'],METADATA if c.metadata else 0)
 for i,key in enumerate(('D_800DBE68','D_800DBE6C','D_800DBE70','D_800DBE74')):put(m,s[key],0xBD800000+i)
 for i,(table,dest)in enumerate(CONTEXT_ROWS):
  for row in range(4):put(m,table+row*4,TRIANGLES+c.base_index*12 if not i else 0x110000+i*0x100+row*4)
  put(m,dest,0x210000+i*0x100)
 # The model supports independent movement of the labels actually bound by the root.
 put(m,s['D_800DBE3C'],TRIANGLES+c.base_index*12);put(m,0x800DBE50,0xDEADBEEF)
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+512}
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def snapshot(m,c,s=SYMS):return(data(m,OUTPUT,36),data(m,ALTERNATE,36),data(m,pos(c),12),tuple(read(m,s[k])for k in('D_800DBE68','D_800DBE6C','D_800DBE70','D_800DBE74','D_800DBE5C','D_800DBE3C')))
def context_effect(m,c,home):
 if c.mutation&1:
  for i,v in enumerate((0x3FE00000,0x41A00000,0xC0300000)):put(m,pos(c)+i*4,v)
 if c.home_threshold>=0:put(m,home+4,c.home_threshold)
def select_context(m,s=SYMS):
 for table,dest in CONTEXT_ROWS:put(m,s['D_800DBE3C']if dest==0x800DBE3C else dest,read(m,table))
 put(m,0x800DBE50,0)
def scan_effect(m,c,s=SYMS,home=STACK):
 if c.mutation&2:put(m,pos(c)+4,0x40000000)
 if c.mutation&4:put(m,OUTPUT,0x40C00000)
 if c.mutation&8:
  for i in range(8):put(m,s['D_800D3300']+i*16,(7-i)*256)
 if c.mutation&16:put(m,s['D_800DBE5C'],0)
 if c.home_selected!=-2:put(m,home-8,c.home_selected)
 if c.home_output:put(m,home+8,ALTERNATE)
def reference(initial,c=Case(),s=SYMS,home=None):
 m=dict(initial);calls=[];obs=[];home=STACK+c.phase if home is None else home;p=pos(c);dst=OUTPUT;put(m,home+4,c.threshold)
 if floating(read(m,p+4))<floating(read(m,home+4)):m[dst+28]&=253;return m,calls,obs,0
 put(m,dst,read(m,s['D_80098D44']));put(m,home-8,0xFFFFFFFF);put(m,home+8,dst)
 def record(t,a):calls.append((t,tuple(v&0xFFFFFFFF for v in a)));obs.append(snapshot(m,c,s))
 record(s['func_1510F800'],(0,));context_effect(m,c,home)
 if c.real_context:record(SELECT,(0,))
 select_context(m,s)
 for i,key in enumerate(('D_800DBE68','D_800DBE6C','D_800DBE70')):put(m,s[key],read(m,p+i*4))
 put(m,s['D_800DBE74'],read(m,home+4));a=(math.trunc(floating(read(m,p))),math.trunc(floating(read(m,p+8))));record(s['func_150A3A70'],a);scan_effect(m,c,s,home)
 selected=signed(read(m,home-8));dst=read(m,home+8)
 for i in range(max(0,c.count)):
  h=bits(floating(bits(float(signed(read(m,s['D_800D3300']+i*16)))))*(1.0/256.0))
  if floating(h)<=floating(read(m,p+4))and floating(read(m,dst))<floating(h):selected=i;put(m,dst,h)
 if selected==-1:m[dst+28]&=253;return m,calls,obs,0
 candidate=s['D_800D3300']+selected*16;index=signed(read(m,candidate+8));triangle=read(m,candidate+4)
 for axis in range(3):
  v=read(m,triangle+axis*4)+index*16
  for component in range(3):put(m,dst+4+axis*6+component*2,read(m,v+component*2,2),2)
 meta=read(m,s['D_800DBE5C'])
 if meta:
  difference=signed(read(m,candidate+4)-read(m,s['D_800DBE3C']));idx=abs(difference)//12*(-1 if difference<0 else 1);put(m,dst+24,read(m,meta+idx*4))
 else:put(m,dst+24,0)
 flags=m[dst+28];m[dst+29]=1;m[dst+28]=flags|7;put(m,dst+32,0)
 if floating(read(m,home+4))<=floating(read(m,dst)):m[dst+28]|=2;return m,calls,obs,1
 return m,calls,obs,0
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c=Case(),s=SYMS,entry=ENTRY,connected=None):
  self.s=s;self.observations=[];super().__init__(ws,memory,c,entry=entry,s=s,connected=connected,arguments=(pos(c),c.threshold,OUTPUT));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==0 and w&63==26:
   a,b=signed(self.r[w>>21&31]),signed(self.r[w>>16&31]);assert b;self.lo=(abs(a)//abs(b)*(-1 if(a<0)!=(b<0)else 1))&0xFFFFFFFF;self.hi=(a-signed(self.lo)*b)&0xFFFFFFFF;return
  return super().execute(w)
 def record_call(self,t):
  counts={ENTRY:3,self.s['func_1510F800']:1,SELECT:1,self.s['func_150A3A70']:2};assert t in counts,hex(t);a=tuple(v&0xFFFFFFFF for v in self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a));self.observations.append(snapshot(self.memory,self.case,self.s))
  if t==self.s['func_1510F800']:context_effect(self.memory,self.case,self.target_home)
  if t==self.s['func_150A3A70']:scan_effect(self.memory,self.case,self.s,self.target_home)
 def hook(self,t):
  if t==self.s['func_1510F800']:select_context(self.memory,self.s);answer=0xDEADBEEF
  elif t==self.s['func_150A3A70']:answer=self.case.count
  else:raise AssertionError(('Unbounded height provider',hex(t)))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=answer&0xFFFFFFFF
@lru_cache(maxsize=1)
def original_context():
 rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes();result={}
 for entry,offset,n in((CONTEXT,0x13CCB0,8),(SELECT,0xD1EA4,40)):
  raw=rom[offset:offset+n*4];at=elf_slot_offset(image,entry,n*4);assert image[at:at+n*4]==raw;result.update(zip(range(entry,entry+n*4,4),struct.unpack('>%dI'%n,raw)))
 return result
def words(p,s=SYMS):
 raw,fs,rs=parse_object(p);a,n=fs['func_150450CC']['value'],fs['func_150450CC']['size'];return bound_blob(raw[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s)
def check(m,c=Case(),s=SYMS):
 want,calls,obs,result=reference(m.initial,c,s)
 assert(public(m.memory),m.calls,m.observations,m.r[2]&0xFFFFFFFF)==(public(want),calls,obs,result),('height public/call/result mismatch',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 home=STACK+c.phase;assert all(m.memory[p]==want[p]for p in range(home,home+64)),('parameter homes',c)
def cases():
 result=[replace(Case(),flags=i,count=i%10-2,metadata=bool(i&1),real_context=bool(i&2),phase=(i&1)*8)for i in range(256)]
 result +=[replace(Case(),position=(0x3FE00000,y,0xC0300000),threshold=t,count=n,mutation=mutation,metadata=metadata,vertex_index=index,base_index=base,real_context=bool(mutation&1),phase=(n&1)*8)for y,t,n,mutation,metadata,index,base in itertools.product((0xC0000000,0x40000000,0x41200000,0x7FC12345,0x7F800000),(0,0x40A00000,0x7FC23456),(-1,0,1,4,8),(0,1,2,4,8,15),(False,True),(-1,1),(0,2))]
 result +=[replace(Case(),heights=hs,threshold=threshold)for hs,threshold in itertools.product(((0,0,0,0),(256,256,512,512),(-256,-512,-768,-1024),(-1,-256,-257,1),(0x7FFFFFFF,0x80000000,0x00FFFFFF,0x01000001)),(0,0x41200000))]
 result +=[replace(Case(),alias=a,mutation=m,vertex_index=0)for a,m in itertools.product((1,2),(0,1,2,4,8,15))]
 result +=[replace(Case(),count=n,home_selected=selected,home_output=output,home_threshold=threshold)for n,selected,output,threshold in itertools.product((0,4),(-1,0,2),(False,True),(-1,0xC0000000,0x41A00000))]
 return result
def main():
 paths={'raw':out/'selected.o','normalized':out/'qualified-padded/generated_71820.c.o','retail':out/'retail-reference.o'};coverage={};counts={};cs=cases()
 for label,path in paths.items():
  ws=words(path);seen=set()
  for c in cs:
   m=Oracle(ws,fixture(c),c,connected=original_context()if c.real_context else None)
   try:m.run();check(m,c)
   except(AssertionError,KeyError)as e:raise AssertionError((label,c,str(e)))from e
   seen.update(m.visits)
  coverage[label]=sorted((p-ENTRY)//4 for p in set(range(ENTRY,ENTRY+576,4))-seen);counts[label]=len(cs)
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={k:(v if k.startswith('func_')else 0x80300000+low+(v&0xFFFFF))for k,v in SYMS.items()};s.update(func_1510F800=0x15300000,func_150A3A70=0x15310000)
  for path in paths.values():
   for mutation in(0,15):
    c=replace(Case(),mutation=mutation);m=Oracle(words(path,s),fixture(c,s),c,s);m.run();check(m,c,s);rebases+=1
 assert all(v==[116]for v in coverage.values()),coverage
 report=dict(cases_per_body=counts,total=sum(counts.values()),unreachable_words=coverage,independent_rebases=rebases,original_context_wrapper_and_selector=True,spatial_scan_is_bounded_provider=True,scripted_mutations_are_extensions=True,all_flag_bytes=True,signed_fixed_heights_and_float_NaNs=True,guest_frame_and_coordinate_aliases=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
