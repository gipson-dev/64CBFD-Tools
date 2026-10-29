"""Record relocation: bounded guest memory, aliases and original caller window."""
from dataclasses import dataclass,replace
import struct
from tools.experiments import game_record_address_relocator_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
TABLE,COUNTS,DATA,ALT,BASE=0x200000,0x210000,0x220000,0x230000,0x50000
WINDOW,END=0x15003314,0x15003370
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 index:int=0
 offset:int=64
 count:int=2
 null:int=0
 alias:int=0
 seed:int=0
 phase:int=0
def symbols():return dict(D_800B0E30=0x800B0E30,D_800B0E34=0x800B0E34)
def fixture(c=Case(),s=None):
 s=s or symbols();slot=u32(TABLE+4*c.index);count=u32(COUNTS+c.index)
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-64,128)}
 for a,n in((slot-16,36),(count-8,20),(DATA-16,12*(c.count+1)+32),(ALT-16,80),(BASE-16,80)):
  for i in range(n):m[u32(a+i)]=(i*13+c.seed+0xA5)&255
 put(m,s['D_800B0E30'],TABLE);put(m,s['D_800B0E34'],COUNTS)
 for i in range(c.count):
  put(m,DATA+12*i,u32(0xFFFFFFF0-i*17-c.seed)|1)
  put(m,DATA+12*i+4,u32(0x7FFFFFFF+i*23+c.seed))
 put(m,DATA+12*c.count,0)
 incoming=0 if c.null else u32(DATA-c.offset)
 if c.alias:
  assert not c.null and c.offset==64 and c.index==0
  if c.alias==1:
   # Clearing the count also clears the low byte of the newly stored pointer.
   put(m,s['D_800B0E34'],slot+3);incoming=u32(DATA+0x23-c.offset)
   put(m,u32((incoming&0xFFFFFF00)+c.offset),0)
  elif c.alias==2:
   # The first record word is the selected table slot itself.
   incoming=slot-c.offset;put(m,slot+12,0);put(m,slot+c.offset,ALT)
   put(m,slot+c.offset+4,0xFFFFFFF0);put(m,slot+c.offset+12,0)
  elif c.alias==3:
   # The first record word redirects the global table pointer.
   incoming=u32(s['D_800B0E30']-c.offset)
   put(m,TABLE+c.offset,ALT);put(m,ALT+4,0xFFFFFFFF);put(m,ALT+12,0)
  elif c.alias==4:
   put(m,s['D_800B0E34'],DATA);put(m,DATA,0x01000000)
  else:raise AssertionError(c)
 return m,(u32(c.index),u32(c.offset),incoming)
def reference(initial,args,s=None):
 s=s or symbols();m=dict(initial);index,offset,incoming=args
 def slot():return u32(read(m,s['D_800B0E30'])+4*index)
 def record(n):return u32(read(m,slot())+12*n)
 def count_address():return u32(read(m,s['D_800B0E34'])+index)
 put(m,slot(),incoming);put(m,count_address(),0,1)
 if incoming:
  p=slot();put(m,p,u32(read(m,p)+offset));n=0
  while read(m,record(n)):
   p=record(n);put(m,p,u32(read(m,p)+offset))
   p=u32(record(n)+4);put(m,p,u32(read(m,p)+offset));n+=1
   assert n<=300,'Unbounded fixture'
  put(m,count_address(),n&255,1)
 return m
class RelocatorOracle(FactoryOracle):
 def __init__(self,words,memory,args,c=Case(),entry=None,s=None,connected=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=args)
 def record_call(self,t):
  assert t==source.ENTRY;args=tuple(map(u32,self.arguments(3)));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):raise AssertionError(('Unexpected helper',hex(t)))
def full_state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace)
def caller_machine(rom,words,c=Case(),reject=False):
 assert not c.alias
 c=replace(c,offset=BASE);initial,args=fixture(c)
 put(initial,BASE+32,args[2])
 for at,v in((0,0 if c.seed&1 else 0x40),(8,0 if c.seed&1 else 0x80),(16,0xC0 if c.seed&1 else 0)):put(initial,BASE+at,v)
 expected=dict(initial)
 for at in(0,8,16):
  v=read(expected,BASE+at)
  if v:put(expected,BASE+at,u32(v+BASE))
 expected=dict(initial) if reject else reference(expected,args)
 connected=dict(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words))
 connected.update({END:0,0x15003404:0,0x15003414:0})
 m=RelocatorOracle(struct.unpack_from('>23I',rom,0x307C4),initial,args,c,entry=WINDOW,connected=connected)
 m.r[16]=BASE;m.r[18]=c.index;m.r[25]=0 if reject else 1;m.before=m.r[:]
 m.code=WindowCode(m.code,m);m.code.ends=(END,0x15003404,0x15003414)
 return m,expected,args
