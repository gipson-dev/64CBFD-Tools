"""Polygon loop, all original plane callbacks and bounded caller observations."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_classifier_candidates import sections
ENTRY,F=0x15185DD4,'func_15185DD4'
TABLE,CLASSES,FAR,NEAR=0x8008D498,0x8008D4C0,0x800D3688,0x800D368C
INPUT,OUTPUT=0x20000,0x30000
INTERPS=(0x15185454,0x1518557C,0x151856A8,0x151857DC,0x151858FC,0x15185A28,0x15185B54,0x15185B54,0x15185C6C,0x15185C6C)
PREDICATES=(0x15185554,0x1518567C,0x151857B0,0x151858D4,0x151859FC,0x15185B28,0x15185C44,0x15185D84,0x15185DAC,0x15185D5C)
@dataclass(frozen=True)
class Case:
 phase:int=0
f32=lambda v:floating(bits(v))
half=lambda m,p:(read(m,p,2)^32768)-32768
def vertex(index,positive,i):
 x,y,z=0.25+i*.125,-.5+i*.25,2.0
 if index==0:y=4.0 if positive else 0.0
 elif index==1:x=-4.0 if positive else 0.0
 elif index==2:y=-4.0 if positive else 0.0
 elif index==3:x=4.0 if positive else 0.0
 elif index==4:z=4.0 if positive else 0.0
 elif index==5:z=-4.0 if positive else 0.0
 elif index==6:x=-2.0 if positive else 2.0
 elif index==7:x=2.0 if positive else -2.0
 elif index==8:y=2.0 if positive else -2.0
 else:y=-2.0 if positive else 2.0
 return struct.pack('>IIIhhhBB',bits(x),bits(y),bits(z),-30000+i*1777,-31+i*7,30000-i*1733,0x80+i,0xC0+i)
def fixture(index,flags,phase=0,table=TABLE,classes=CLASSES):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,4096)}
 for base in (INPUT,OUTPUT):m.update({base+i:(i*29+0x59)&255 for i in range(-16,2048)})
 for i,flag in enumerate(flags):
  for k,b in enumerate(vertex(index,flag,i)):m[INPUT+20*i+k]=b
 for i,(interpolate,classify)in enumerate(zip(INTERPS,PREDICATES)):put(m,table+4*i,interpolate);put(m,classes+4*i,classify)
 put(m,FAR,bits(2));put(m,NEAR,bits(-2));return m
def classify(m,p,index):
 x,y,z=(floating(read(m,p+4*i))for i in range(3))
 return (y>z,x<-z,y<-z,x>z,z>floating(read(m,FAR)),z<floating(read(m,NEAR)),x<=0,x>0,y>0,y<=0)[index]
def interpolate(m,a,b,out,index):
 ax,ay,az=(floating(read(m,a+4*i))for i in range(3));bx,by,bz=(floating(read(m,b+4*i))for i in range(3))
 if index==0:num=f32(az-ay);den=f32(f32(by-ay)-f32(bz-az))
 elif index==1:num=f32(az+ax);den=f32(f32(ax-bx)+f32(az-bz))
 elif index==2:num=f32(az+ay);den=f32(f32(ay-by)+f32(az-bz))
 elif index==3:num=f32(az-ax);den=f32(f32(bx-ax)-f32(bz-az))
 elif index in (4,5):num=f32(floating(read(m,FAR if index==4 else NEAR))-az);den=f32(bz-az)
 elif index in (6,7):num=ax;den=f32(ax-bx)
 else:num=ay;den=f32(ay-by)
 assert math.isfinite(den)and den!=0,(index,a,b,num,den)
 ratio=f32(num/den)
 lerp=lambda start,end:f32(start+f32(f32(end-start)*ratio))
 if index==0:
  put(m,out,bits(lerp(ax,bx)));value=bits(lerp(ay,by));put(m,out+8,value);put(m,out+4,value)
 elif index in (1,3):
  value=bits(lerp(ax,bx));put(m,out,value);put(m,out+8,value^(0x80000000 if index==1 else 0));put(m,out+4,bits(lerp(ay,by)))
 elif index==2:
  put(m,out,bits(lerp(ax,bx)));value=bits(lerp(ay,by));put(m,out+4,value);put(m,out+8,value^0x80000000)
 elif index in (4,5):
  put(m,out,bits(lerp(ax,bx)));put(m,out+4,bits(lerp(ay,by)));put(m,out+8,read(m,FAR if index==4 else NEAR))
 elif index in (6,7):
  put(m,out,0);put(m,out+4,bits(lerp(ay,by)));put(m,out+8,bits(lerp(az,bz)))
 else:
  put(m,out+4,0);put(m,out,bits(lerp(ax,bx)));put(m,out+8,bits(lerp(az,bz)))
 for at in (12,14,16):
  start,end=half(m,a+at),half(m,b+at);v=f32(f32(float(start))+f32(f32(float(end-start))*ratio));assert -32768<=math.trunc(v)<=32767
  put(m,out+at,math.trunc(v),2)
 return out+20
def reference(initial,count,index,base=INPUT,out=OUTPUT):
 m=dict(initial);cursor=out;calls=[]
 for i in range(max(0,count)):
  cur=base+20*i;prev=base+20*((i-1)%count);keep=classify(m,cur,index);prior=classify(m,prev,index)
  calls.extend(((PREDICATES[index],(cur,)),(PREDICATES[index],(prev,))))
  if keep!=prior:calls.append((INTERPS[index],(prev,cur,cursor)));cursor=interpolate(m,prev,cur,cursor,index)
  if keep:
   # Retail copies five words in order, including the retained tail bytes.
   for at in range(0,20,4):put(m,cursor+at,read(m,cur+at))
   cursor+=20
 return m,cursor,calls
class Oracle(FactoryOracle):
 def __init__(self,program,initial,args,phase=0,entry=ENTRY,connected=None):
  super().__init__(program,initial,Case(phase),entry=entry,s={},connected=connected,arguments=args);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in (7,13):
   if w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
   else:
    v=floating(self.f[w>>11&31]);assert math.isfinite(v)and -2147483648<=math.trunc(v)<=2147483647;self.f[w>>6&31]=math.trunc(v)&0xFFFFFFFF
  else:super().execute(w)
 def record_call(self,t):
  n=4 if t==ENTRY else 3 if t in INTERPS else 1 if t in PREDICATES else None;assert n is not None,hex(t);self.calls.append((t,tuple(self.arguments(n))))
 def hook(self,t):raise AssertionError(('Unowned callback',hex(t)))
def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+4096}
def state(m):return m.memory,m.r,m.f,m.trace,m.calls
def check_saved(m):assert all(m.r[i]==m.before[i]for i in (*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
def linked(obj,label,entry=ENTRY,table=TABLE,classes=CLASSES):
 p=o/label;p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\nD_8008D498 = 0x%X;\nD_8008D4C0 = 0x%X;\n'%(entry,table,classes))
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
 return list(struct.unpack('>84I',sections(p.with_suffix('.elf'))['.text'][1][:336]))
def configure(root,output,obj):
 global r,o,rom,objects,programs,helpers
 r,o=root,output;rom=(r/'conker/conker.us.bin').read_bytes();stage=r/'conker/build/game-polygon-plane-clip-15185DD4-match';objects=(stage/('original-'+F+'.o'),obj);programs=[linked(p,'root-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]
 text=(r/'conker/asm/1B1600.s').read_text();helpers={}
 for address in set(INTERPS+PREDICATES):
  f='func_%08X'%address;a=text.index('glabel '+f);b=text.index('endlabel '+f,a)
  for pc,w in re.findall(r'/\*\s*\w+\s+(\w{8})\s+(\w{8})\s*\*/',text[a:b]):helpers[int(pc,16)]=int(w,16)
def matrix():
 for index,flags,phase in itertools.product(range(10),((),(0,),(1,),(0,1),(1,0),(1,1,1),(0,0,0),(1,0,1,0),(1,0,0,1,0,1,1,0)),(0,8)):yield index,flags,phase
def run_suite():
 seen=set();helper_seen=set();count=0
 for index,flags,phase in matrix():
  initial=fixture(index,flags,phase);expected,cursor,calls=reference(initial,len(flags),index);pair=[]
  for program in programs:
   m=Oracle(program,initial,(INPUT,len(flags),index,OUTPUT),phase,connected=helpers);m.run();check_saved(m)
   assert (public(m.memory),m.r[2],m.calls)==(public(expected),cursor,calls),(index,flags,m.r[2],cursor)
   seen.update(m.visits);helper_seen.update(m.visits&helpers.keys());pair.append(state(m))
  assert pair[0]==pair[1];count+=1
 for index,count_value in itertools.product(range(10),(-1,-2147483648)):
  initial=fixture(index,());initial={a:v for a,v in initial.items()if not INPUT-16<=a<INPUT+2048}
  for program in programs:
   m=Oracle(program,initial,(INPUT,count_value&0xFFFFFFFF,index,OUTPUT),connected=helpers);m.run();assert m.r[2]==OUTPUT and not m.calls
  count+=1
 assert set(range(ENTRY,ENTRY+336,4))<=seen
 assert helper_seen==set(helpers)
 return dict(cases=count,executions=count*2,reachable_words=84,frame=56,table_entries=10,original_callback_routines=len(set(INTERPS+PREDICATES)),callback_words_executed=len(helper_seen),all_callback_words_reached=True,no_external_service_models=True,negative_count_sparse_cases=20,complete_output_and_cursor_checked=True,finite_representable_conversion_domain=True,hardware_FCSR_claimed=False)
def run_prefixes_rebases_aliases():
 prefixes=rebases=aliases=0
 for index,flags in ((0,(1,0,1)),(6,(0,1)),(9,())):
  initial=fixture(index,flags);full=Oracle(programs[0],initial,(INPUT,len(flags),index,OUTPUT),connected=helpers);full.run()
  for cut in range(full.all_accesses):
   pair=[]
   for program in programs:
    m=Oracle(program,initial,(INPUT,len(flags),index,OUTPUT),connected=helpers);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access prefix failed to fire')
    pair.append(state(m))
   assert pair[0]==pair[1];prefixes+=1
 for k,(entry,table,classes)in enumerate(((0x1ABC0000,0x31008000,0x41007FFC),(0x15007FFC,0x3200FFFC,0x42008000))):
  ps=[linked(p,'rebase-%d-%d'%(k,i),entry,table,classes)for i,p in enumerate(objects)];assert ps[0]==ps[1]
  for index in range(10):
   flags=(0,1,1,0);initial=fixture(index,flags,table=table,classes=classes);expected,cursor,calls=reference(initial,len(flags),index)
   for program in ps:
    m=Oracle(program,initial,(INPUT,len(flags),index,OUTPUT),entry=entry,connected=helpers);m.run();assert(public(m.memory),m.r[2],m.calls)==(public(expected),cursor,calls);rebases+=1
 for index in (0,6,9):
  flags=(1,1,1);initial=fixture(index,flags);expected,cursor,calls=reference(initial,len(flags),index,out=INPUT)
  for program in programs:
   m=Oracle(program,initial,(INPUT,len(flags),index,INPUT),connected=helpers);m.run();assert(public(m.memory),m.r[2],m.calls)==(public(expected),cursor,calls)
  aliases+=1
 return dict(fired_prefix_cases=prefixes,independent_rebase_profiles=2,rebase_executions=rebases,code_and_tables_relocated=True,signed_low16_carries=True,in_place_whole_copy_cases=aliases,portable_C_fault_claimed=False)

def run_callers():
 windows=((0x1518616C,0x15186198,range(6)),(0x15186218,0x15186234,(6,7)),(0x151862CC,0x151862E4,(8,9)),(0x1518632C,0x15186348,(8,9)))
 count=0
 for start,end,indices in windows:
  words=list(struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0))
  assert words[:2]==[0x0D461775,0]
  for index,flags,phase in itertools.product(indices,((),(1,0),(0,1,1)),(0,8)):
   initial=fixture(index,flags,phase);out=STACK+phase+0x88+520 if start==0x1518616C else OUTPUT
   for i in range(-4,16):initial[0x50000+i]=0xA5
   expected,cursor,calls=reference(initial,len(flags),index,out=out);result=(cursor-out)//20
   if start in (0x151862CC,0x1518632C):put(expected,0x50000,result)
   pair=[]
   for program in programs:
    code=dict(helpers);code.update(zip(range(ENTRY,ENTRY+336,4),program));code[end]=0
    m=Oracle(words,initial,(INPUT,len(flags),index,out),phase,start,code)
    m.r[16]=1 if start==0x1518616C else index-6 if start==0x15186218 else 0;m.r[17]=0x50000;m.r[19]=index;m.r[20]=len(flags);m.r[22]=out;m.r[30]=20
    m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller stop boundary not reached')
    assert m.calls==[(ENTRY,(INPUT,len(flags),index,out))]+calls
    assert public(m.memory)==public(expected)
    assert bytes(m.memory[out+i]for i in range(400))==bytes(expected[out+i]for i in range(400))
    if start==0x1518616C:assert m.r[20]==result and m.r[19]==index+1
    elif start==0x15186218:assert m.r[11]==result and m.r[16]==index-5
    else:assert read(m.memory,0x50000)==result
    pair.append(state(m))
   assert pair[0]==pair[1];count+=1
 return dict(cases=count,executions=count*2,windows=[dict(start=hex(a),end=hex(b),words=(b-a)//4)for a,b,_ in windows],all_four_original_calls=True,returned_cursor_divided_by_stride_20=True,complete_outer_caller_claimed=False,precall_state_explicitly_supplied=True)
