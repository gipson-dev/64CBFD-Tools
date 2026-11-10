"""Independent paired entity-query model, callback mutation and literal guest alias cases."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_context2_height_pair_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
FUNCTIONS=('func_15045880','func_15045AE4');ENTRIES=(0x15045880,0x15045AE4)
CONTEXT,SCAN=0x150A44F0,0x150A43E0
POS,INPUT,ALT_INPUT,OUTPUT,TRIANGLES,ENTITIES,METADATA=0x90000,0x98000,0x98100,0xA0000,0xB0000,0xE0000,0x2000020
SYMS={n:int(n.split('_')[1],16)for n in('D_80098D50','D_80098D54','D_800D37E0','D_800D3300','D_800DBEF4','D_800DBE3C','func_150A44F0','func_150A43E0')}
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 kind:int=0
 position:tuple=(0xC14C0000,0x40000000,0x41BE0000)
 threshold:int=0x40000000
 heights:tuple=(256,512,512,1024)
 count:int=4
 flags:int=165
 entity_flags:int=128
 metadata:bool=True
 first_triangle:int=0
 base_index:int=0
 byte_offset:int=16
 input_word:int=0x12345678
 mutation:int=0
 alias:int=0
 home_selected:int=-2
 home_input:bool=False
 home_threshold:int=-1
 phase:int=0
def vertex(row,axis):return 0xC0000+row*0x1000+axis*0x400+320
def output(c,s=SYMS):
 return {0:OUTPUT,1:s['D_800D3300']-4,2:s['D_800D3300']-16,3:s['D_800DBEF4']-32,4:ENTITIES+160+0x24}.get(c.alias,OUTPUT)
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+165)&255 for i in range(-768,768)}
 for p,n in((POS-16,48),(INPUT-16,40),(ALT_INPUT-16,40),(OUTPUT-16,68),(TRIANGLES-16,128),(ENTITIES,8*160),(s['D_800D37E0'],128)):
  m.update({p+i:(i*29+91)&255 for i in range(n)})
 for row in range(8):
  for axis in range(3):
   p=vertex(row,axis)
   for index in(-16,-2,-1,0,1,2,16):
    m.update({p+index*16+j:(index*16*13+j*13+row*37+axis*19+5)&255 for j in range(16)})
    for k in range(3):put(m,p+index*16+k*2,(-32768+row*731+axis*113+index*17+k*32701)&65535,2)
   put(m,TRIANGLES+row*12+axis*4,p)
  p=s['D_800D3300']+row*16;put(m,p,c.heights[row%4]);put(m,p+4,TRIANGLES+row*12);put(m,p+8,c.byte_offset);put(m,p+12,(row+1)%4)
 for row in range(8):
  p=ENTITIES+row*160;put(m,p+0x40,0x91570000+row);put(m,p+0x44,METADATA+4*(c.first_triangle+row)if c.metadata else 0);put(m,p+0x58,c.first_triangle,2);m[p+0x6F]=(c.entity_flags^(row*17))&255
 for i in range(-8,32):put(m,METADATA+i*4,0x81230000+(i&65535));put(m,METADATA+(65536+i)*4,0)
 for k,v in enumerate(c.position):put(m,POS+k*4,v)
 put(m,INPUT,c.input_word);put(m,INPUT+4,0x76543210);put(m,ALT_INPUT,c.input_word^0xA55AFFFF);put(m,ALT_INPUT+4,0xFEDCBA98)
 put(m,s['D_80098D50'],0x47C34FF3);put(m,s['D_80098D54'],0xC61C4000);put(m,s['D_800DBEF4'],ENTITIES);put(m,s['D_800DBE3C'],TRIANGLES+c.base_index*12)
 dst=output(c,s)
 for i in range(-16,52):m.setdefault(dst+i,(i*29+91)&255)
 if c.alias in(1,2):
  # A copy can overwrite the cached triangle and the subsequently reloaded entity index.
  put(m,vertex(0,0)+c.byte_offset+4,0x001B,2)
  put(m,vertex(0,2)+c.byte_offset,0,2);put(m,vertex(0,2)+c.byte_offset+2,2,2);put(m,vertex(0,2)+c.byte_offset+4,0x001B,2)
  # Map the wrong reload's lookup too; a negative control must finish semantically.
  for bad in(0x1B0000,0x001B0000|(TRIANGLES&65535)):
   diff=signed(bad-(TRIANGLES+c.base_index*12));q=abs(diff)//12*(-1 if diff<0 else 1)
   for e in range(8):put(m,METADATA+4*(q+e),0xDEF00000+e)
  for e in [base+i for base in(0x06000000,0x06020000,0x07000000,0x07020000)for i in range(8)]:
   fake=u32(ENTITIES+(e*160));m.update({fake+i:0 for i in range(160)});put(m,fake+0x40,0xAABBCCDD);put(m,fake+0x44,0);put(m,fake+0x58,0,2);m[fake+0x6F]=128 if e&0x00020000 else 0
 if c.alias==3:m[ENTITIES+2*160+0x6F]^=128
 if c.alias==2:assert c.flags==0,'The aliased index high byte must start at zero'
 m[dst+28]=c.flags
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-768<=p<STACK+768}
def snapshot(m,c,s=SYMS):
 return(data(m,output(c,s),36),data(m,POS,12),read(m,INPUT),read(m,ALT_INPUT),read(m,s['D_800DBEF4']),read(m,s['D_800DBE3C']),data(m,s['D_800D37E0'],16))
def context_effect(m,c,s,home):
 value=read(m,INPUT)
 for i in range(16):m[s['D_800D37E0']+i]=(value+i*17)&255
 if c.mutation&1:
  for i,v in enumerate((0x3FE00000,0x40000000,0xC0300000)):put(m,POS+i*4,v)
 if c.mutation&2:put(m,INPUT,77)
 if c.home_input:put(m,home+8,ALT_INPUT)
 if c.home_threshold>=0:put(m,home+4,c.home_threshold)
def scan_effect(m,c,s,home):
 dst=output(c,s)
 if c.mutation&4:put(m,POS+4,0x40800000 if not c.kind else 0x3F800000)
 if c.mutation&8:put(m,dst,0x3F000000 if not c.kind else 0x40C00000)
 if c.mutation&16:
  for row in range(8):put(m,s['D_800D3300']+row*16,(7-row)*256)
 if c.mutation&32:put(m,s['D_800DBEF4'],ENTITIES+160)
 if c.mutation&64:put(m,ENTITIES+160+0x44,0);m[ENTITIES+160+0x6F]^=128
 if c.mutation&128:
  for row in range(8):put(m,s['D_800D3300']+row*16+12,3)
 if c.home_selected!=-2:put(m,home-8,c.home_selected)
def reference(initial,c=Case(),s=SYMS,home=None):
 m=dict(initial);calls=[];obs=[];home=STACK+c.phase if home is None else home;dst=output(c,s)
 put(m,home+4,c.threshold);put(m,home+8,INPUT);put(m,dst,read(m,s['D_80098D50'if not c.kind else'D_80098D54']));put(m,home-8,0xFFFFFFFF)
 def record(t,args):calls.append((t,tuple(u32(v)for v in args)));obs.append(snapshot(m,c,s))
 record(s['func_150A44F0'],(read(m,INPUT),s['D_800D37E0'],0));context_effect(m,c,s,home)
 p=read(m,home+8);record(s['func_150A43E0'],(math.trunc(floating(read(m,POS))),math.trunc(floating(read(m,POS+8))),read(m,p),s['D_800D37E0']));scan_effect(m,c,s,home)
 selected=signed(read(m,home-8))
 for i in range(max(c.count,0)):
  h=bits(floating(bits(float(signed(read(m,s['D_800D3300']+i*16)))))*(1.0/256.0));y=floating(read(m,POS+4));old=floating(read(m,dst));hf=floating(h)
  eligible=y<=hf and hf<old if not c.kind else hf<=y and old<hf
  if eligible:selected=i;put(m,dst,h)
 if selected==-1:m[dst+28]&=253;return m,calls,obs,0
 candidate=s['D_800D3300']+selected*16;triangle=read(m,candidate+4);offset=signed(read(m,candidate+8))
 for axis in range(3):
  p=u32(read(m,triangle+axis*4)+offset)
  for k in range(3):put(m,dst+4+axis*6+k*2,read(m,p+k*2,2),2)
 entity=u32(read(m,s['D_800DBEF4'])+signed(read(m,candidate+12))*160);put(m,dst+32,entity);table=read(m,entity+0x44)
 if table:
  delta=signed(triangle-read(m,s['D_800DBE3C']));q=abs(delta)//12*(-1 if delta<0 else 1);index=signed(q-read(m,entity+0x58,2));value=read(m,u32(table+index*4))
 else:value=read(m,entity+0x40)
 put(m,dst+24,value);m[dst+28]|=6
 flagEntity=u32(read(m,s['D_800DBEF4'])+signed(read(m,candidate+12))*160)
 if m[flagEntity+0x6F]&128:m[dst+28]|=1
 m[dst+29]=2;height=floating(read(m,dst));threshold=floating(read(m,home+4));accepted=height<=threshold if not c.kind else threshold<=height
 if accepted:m[dst+28]|=2;return m,calls,obs,1
 return m,calls,obs,0
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c=Case(),s=SYMS,entry=None,connected=None):
  self.s=s;self.observations=[];super().__init__(ws,memory,c,entry=ENTRIES[c.kind]if entry is None else entry,s=s,connected=connected,arguments=(POS,c.threshold,INPUT,output(c,s)));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==0 and w&63==26:
   a,b=signed(self.r[w>>21&31]),signed(self.r[w>>16&31]);assert b;self.lo=u32(abs(a)//abs(b)*(-1 if(a<0)!=(b<0)else 1));self.hi=u32(a-signed(self.lo)*b);return
  return super().execute(w)
 def record_call(self,t):
  n={self.s['func_150A44F0']:3,self.s['func_150A43E0']:4}.get(t);assert n is not None,hex(t);a=tuple(u32(v)for v in self.arguments(n));self.calls.append((t,a));self.observations.append(snapshot(self.memory,self.case,self.s));self.events.append(('CALL',t,a))
 def hook(self,t):
  if t==self.s['func_150A44F0']:context_effect(self.memory,self.case,self.s,self.target_home);value=0xDEADBEEF
  else:assert t==self.s['func_150A43E0'];scan_effect(self.memory,self.case,self.s,self.target_home);value=self.case.count
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def words(obj,kind=0,s=SYMS):
 raw,fs,rs=parse_object(obj);a,n=fs[FUNCTIONS[kind]]['value'],fs[FUNCTIONS[kind]]['size'];return bound_blob(raw[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s)
def check(m,c=Case(),s=SYMS):
 want,calls,obs,result=reference(m.initial,c,s)
 assert(public(m.memory),m.calls,m.observations,u32(m.r[2]))==(public(want),calls,obs,result),('entity-height public/call/result mismatch',c)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 home=STACK+c.phase;assert all(m.memory[p]==want[p]for p in range(home,home+64)),('parameter homes',c)
def cases(kind=0):
 result=[replace(Case(),kind=kind,flags=i,entity_flags=i^128,count=i%10-2,metadata=bool(i&1),phase=(i&1)*8)for i in range(256)]
 result +=[replace(Case(),kind=kind,position=(0x3FE00000,y,0xC0300000),threshold=t,count=n,metadata=meta)for y,t,n,meta in itertools.product((0xC0000000,0,0x40000000,0x41200000,0x7FC12345,0x7F800000),(0,0x40000000,0x40A00000,0x7FC23456),(-1,0,1,4,8),(False,True))]
 result +=[replace(Case(),kind=kind,first_triangle=first,base_index=base,byte_offset=offset,entity_flags=flags,metadata=meta)for first,base,offset,flags,meta in itertools.product((0,32768,65535),(0,2),(-16,0,2,16),(0,128),(False,True))]
 result +=[replace(Case(),kind=kind,mutation=i,input_word=(0x80000000 if i&1 else 0xFFFFFFFF))for i in range(256)]
 for hs in((0,0,0,0),(256,256,512,512),(-1024,-512,-512,-256),(0x7FFFFFFF,0x80000000,0x00FFFFFF,0x01000001),((25599974,)*4 if not kind else(-2560000,)*4)):
  for n in(1,4,8):result.append(replace(Case(),kind=kind,heights=hs,count=n))
 result.append(replace(Case(),kind=kind,position=(0x3FE00000,0xC1200000 if not kind else 0x41200000,0xC0300000),heights=(-1024,-512,-512,-256),threshold=0))
 result +=[replace(Case(),kind=kind,position=(0x3FE00000,0 if not kind else 0x41200000,0xC0300000),alias=a,count=1,flags=0,byte_offset=0,entity_flags=128,threshold=0x40000000 if not kind else 0)for a in(1,2,3,4)]
 result +=[replace(Case(),kind=kind,count=n,home_selected=index,home_input=change,home_threshold=threshold)for n,index,change,threshold in itertools.product((0,4),(-1,0,2),(False,True),(-1,0xC0000000,0x41A00000))]
 return result
def canonical_trace(m,c,s=SYMS):
    # Normalize only a flags-byte read whose exact value was just stored by
    # this invocation. Keep every other public read/write and its order.
    result=[];written={};skipped=0;flag=output(c,s)+28
    for event in m.trace:
        kind,p,n,value=event
        if STACK-768<=p<STACK+768:continue
        if kind=='R'and p==flag and n==1 and written.get(p)==value:
            skipped+=1;continue
        result.append(event)
        if kind=='W':
            for i in range(n):written[p+i]=(value>>(8*(n-1-i)))&255
    return result,skipped

def main():
 coverage={};counts={};total=0;traces={};forwarded={}
 for kind,function in enumerate(FUNCTIONS):
  traces[function]={}
  paths={'raw':out/'selected.o','normalized':out/'qualified-padded/generated_71820.c.o','retail':out/(function+'-retail.o')}
  for label,path in paths.items():
   ws=words(path,kind);seen=set();cs=cases(kind)
   for c in cs:
    m=Oracle(ws,fixture(c),c)
    try:m.run();check(m,c)
    except(AssertionError,KeyError)as e:raise AssertionError((function,label,c,str(e)))from e
    trace,skipped=canonical_trace(m,c);forwarded[function+'/'+label]=forwarded.get(function+'/'+label,0)+skipped
    if label=='raw':traces[function][c]=trace
    else:assert traces[function][c]==trace,('public access trace mismatch',function,label,c)
    seen.update(m.visits)
   key=function+'/'+label;coverage[key]=sorted((p-ENTRIES[kind])//4 for p in set(range(ENTRIES[kind],ENTRIES[kind]+612,4))-seen);counts[key]=len(cs);total+=len(cs)
 rebases=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={k:(v if k.startswith('func_')else 0x80300000+low+(v&0xFFFFF))for k,v in SYMS.items()};s.update(func_150A44F0=0x15300000,func_150A43E0=0x15310000)
  for kind,function in enumerate(FUNCTIONS):
   for path in(out/'selected.o',out/'qualified-padded/generated_71820.c.o',out/(function+'-retail.o')):
    for mutation in(0,255):
     c=replace(Case(),kind=kind,mutation=mutation);m=Oracle(words(path,kind,s),fixture(c,s),c,s);m.run();check(m,c,s);rebases+=1
 assert all(v==([109,130]if k.endswith('/raw')else[111])for k,v in coverage.items()),coverage
 report=dict(cases_per_body=counts,total=total,unreachable_words=coverage,independent_rebases=rebases,all_result_and_entity_flag_bytes=True,cached_triangle_and_late_index_and_base_reload_aliases=True,unsigned_first_triangle_and_byte_offsets=True,public_access_traces_equal_after_flags_store_forwarding=True,redundant_flags_reads_reconciled=forwarded,helpers_are_bounded_providers=True,scripted_mutations_are_extensions=True,guest_frame_and_physical_aliases=True,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
