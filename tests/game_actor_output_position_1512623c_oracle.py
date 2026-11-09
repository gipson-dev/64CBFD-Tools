"""Actor position outputs: seven-argument ABI, live aliases and original matrix helper."""
from dataclasses import dataclass,replace
import struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read,PointOracle,CONVERT,TRANSFORM,TRANSLATE,STATUS,DIAGNOSTIC,FLAG
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments import game_actor_output_position_1512623c_match as source
ACTOR,META,MATRIX,OUTPUT,ALT,CAMERA,DESCRIPTOR=0x200000,0x210000,0x220000,0x230000,0x240000,0x250000,0x260000
POINT=0x15143134;u32=lambda n:n&0xFFFFFFFF
signed16=lambda n:((n&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
 actor:int=ACTOR
 metadata:int=META
 category:int=0
 alternate:int=0
 matrix:int=MATRIX
 outputs:tuple=(OUTPUT,OUTPUT+4,OUTPUT+8)
 position:tuple=(0x3FA00000,0xC0200000,0x3E000000)
 height:int=20
 transformed:tuple=(0x41540000,0xC19C0000,0x3E800000)
 mode:int=0
 flag:int=1
 phase:int=0
 seed:int=0
 fixed_matrix:int=0

def arguments(c):return(c.actor,c.metadata,u32(c.category),*c.outputs,u32(c.alternate))
def symbols():return dict(func_15143134=POINT)
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def matrix_values(index):
 values=[0.0]*16
 for i in(0,5,10,15):values[i]=0.5
 values[12:15]=[3.25+index,-4.5-index,5.75+index]
 return values

def fixture(c=Case()):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for base,size in((c.actor-64,0x440),(c.metadata-64,0x180),(OUTPUT-32,96),(ALT-32,96),(CAMERA-32,0x680),(DESCRIPTOR,16),(STATUS-16,64),(FLAG,1)):
  for i in range(size):m.setdefault(base+i,(i*29+c.seed*11+0x5A)&255)
 for i,v in enumerate(c.position):put(m,c.actor+0x14+4*i,v)
 put(m,c.actor+0x1D4,c.matrix);put(m,c.metadata+0x114,c.height&65535,2)
 for i,v in enumerate((c.outputs[1],c.outputs[2],u32(c.alternate))):put(m,STACK+c.phase+16+4*i,v)
 put(m,STATUS,0x11223344);put(m,DIAGNOSTIC,0x55667788);m[FLAG]=c.fixed_matrix&255
 for i in range(3):put(m,STATUS+8+4*i,0x87654321+i)
 if c.matrix:
  for index in range(5):
   values=matrix_values(index)
   if c.fixed_matrix:
    ints=[int(v*65536)&0xFFFFFFFF for v in values];payload=struct.pack('>32H',*[v>>16 for v in ints],*[v&65535 for v in ints])
   else:payload=struct.pack('>16I',*[bits(v)for v in values])
   m.update({c.matrix+64*index+i:b for i,b in enumerate(payload)})
 return m

def observation(m,args,c):
 optional=lambda p,n:read(m,p,n)if all(p+i in m for i in range(n))else None
 return(args,data(m,args[0],12),tuple(optional(c.actor+0x14+4*i,4)for i in range(3)),optional(c.metadata+0x114,2))

def effect(m,c,home):
 if c.mode&1:
  for i,v in enumerate((5.5,-7.25,0.5)):put(m,c.actor+0x14+4*i,bits(v))
 if c.mode&2:put(m,c.metadata+0x114,(-19)&65535,2)
 if c.mode&4:
  for i in range(3):put(m,home+12+4*i,ALT+4*i)
 if c.mode&8:put(m,home-4,u32(c.flag))
 if c.mode&16:put(m,c.actor+0x1D4,0)

def point_reference(m,args):
 point,out,matrix=args;values=[floating(read(m,point+4*i))for i in range(3)];put(m,STATUS,0)
 for i in range(3):put(m,STATUS+8+4*i,read(m,point+4*i))
 put(m,DIAGNOSTIC,matrix)
 if m[FLAG]:
  mat=[]
  for i in range(16):
   word=read(m,matrix+2*i,2)<<16|read(m,matrix+32+2*i,2);signed=(word^0x80000000)-0x80000000
   mat.append(floating(bits(floating(bits(float(signed)))/65536.0)))
 else:mat=[floating(read(m,matrix+4*i))for i in range(16)]
 x,y,z=values
 result=[bits(floating(bits(floating(bits(mat[i]*x))+floating(bits(mat[i+4]*y))))+floating(bits(floating(bits(mat[i+8]*z))+mat[i+12])))for i in range(3)]
 for i,v in enumerate(result):put(m,out+4*i,v)

def reference(initial,c=Case(),helper=POINT,actual_point=False):
 m=dict(initial);home=STACK+c.phase;put(m,home+4,c.metadata);calls=[];obs=[];fallback=1;x=c.outputs[0]
 if read(m,c.actor+0x1D4):
  fallback=0
  if read(m,home+24):index=3;point=(0,0x41A00000,0)
  elif u32(c.category)==27:index=4;point=(0,0x42E80000,0x43020000)
  else:fallback=1
  if not fallback:
   put(m,home-32,index)
   for i,v in enumerate(point):put(m,home-16+4*i,v)
   args=(home-16,home-28,u32(read(m,c.actor+0x1D4)+64*index));put(m,home+12,x);put(m,home-4,0)
   calls.append((helper,args));obs.append(observation(m,args,c))
   if actual_point:point_reference(m,args)
   else:
    for i,v in enumerate(c.transformed):put(m,args[1]+4*i,v)
    effect(m,c,home)
   x=read(m,home+12);fallback=read(m,home-4)
   for i in range(3):
    dst=x if i==0 else read(m,home+12+4*i);put(m,dst,read(m,home-28+4*i))
 if fallback:
  put(m,x,read(m,c.actor+0x14));metadata=read(m,home+4);y=read(m,c.actor+0x18);dst=read(m,home+16)
  scaled=bits(float(signed16(read(m,metadata+0x114,2)))*0.75);value=bits(floating(y)+floating(scaled));put(m,dst,value)
  put(m,read(m,home+20),read(m,c.actor+0x1C))
 return m,calls,obs,fallback

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,syms=None,connected=None):
  super().__init__(words,memory,c,entry=entry,s=syms or symbols(),connected=connected,arguments=arguments(c));self.point_observations=[];self.target_entries=[];self.mutate=False;self.input_args=()
 def record_call(self,t):
  if t==source.ENTRY:self.target_home=self.r[29];args=tuple(map(u32,self.arguments(7)));self.target_entries.append(args)
  elif t==self.syms['func_15143134']:
   args=tuple(map(u32,self.arguments(3)));self.input_args=args;self.point_observations.append(observation(self.memory,args,self.case))
  else:return PointOracle.record_call(self,t)
  self.calls.append((t,args));self.events.append(('CALL',t,args))
 def clobber(self):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True
 def hook(self,t):
  if t!=self.syms['func_15143134']:return PointOracle.hook(self,t)
  args=self.calls[-1][1]
  for i,v in enumerate(self.case.transformed):put(self.memory,args[1]+4*i,v)
  effect(self.memory,self.case,self.target_home);self.clobber()

def complete(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.point_observations,m.target_entries)
def connected_machine(words,initial,c,rom,**kw):
 code=dict(zip(range(POINT,POINT+392,4),struct.unpack_from('>98I',rom,0x1705E4)));code.update(kw.pop('connected',{}))
 return Oracle(words,initial,c,connected=code,**kw)

WINDOWS=((0x15126668,0x153B18,13,0x1512669C),(0x15126BB0,0x154060,17,0x15126BF4))
def caller_machine(words,c,rom,index=0,actual_point=False):
 child=replace(c,outputs=(CAMERA+0x2F8,CAMERA+0x2FC,CAMERA+0x300),alternate=c.alternate&16);initial=fixture(child);home=STACK+c.phase
 put(initial,CAMERA+0x3D4,c.metadata);put(initial,CAMERA+0x5F0,u32(c.alternate));put(initial,CAMERA+0x36C,DESCRIPTOR);put(initial,DESCRIPTOR,0xA7,2);put(initial,home+0xC8,c.actor);put(initial,home+0xB4,u32(c.category))
 start,pos,n,end=WINDOWS[index];code=dict(zip(range(source.ENTRY,source.ENTRY+316,4),words));code[end]=0
 ctor=connected_machine if actual_point else Oracle
 m=ctor(struct.unpack_from('>%dI'%n,rom,pos),initial,child,**({'rom':rom}if actual_point else{}),entry=start,connected=code)
 m.r[16]=CAMERA;m.r[6]=u32(c.category);m.r[8]=0x34567890;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
 return m,initial,child

def return_use_audit(rom,start):
 """Over-approximate both branch edges until V0 is overwritten or a new call.

 Floating register 2 is distinct from GPR V0. No parent return or V0 read
 is accepted while the query's incidental value remains live.
 """
 pending=[start];seen=set();kills=[]
 def word(pc):return struct.unpack_from('>I',rom,pc-0x15000000+0x2D4B0)[0]
 def effect(w):
  op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63
  if op==0:
   if fn in(0,2,3):return rt==2,rd==2
   if fn in(0x21,0x23,0x25,0x24,0x26,0x2A,0x2B):return 2 in(rs,rt),rd==2
   if fn==8:raise ValueError('Query result reaches a parent return/jump')
  if op in(4,5,20,21):return 2 in(rs,rt),False
  if op in(1,6,7,22,23):return rs==2,False
  if op in(8,9,10,11,12,13,14):return rs==2,rt==2
  if op==15:return False,rt==2
  if op in(32,33,35,36,37):return rs==2,rt==2
  if op in(40,41,43):return 2 in(rs,rt),False
  if op in(49,53,57,61):return rs==2,False
  if op==17:return rt==2 if rs==4 else False,rt==2 if rs==0 else False
  if op in(2,3):return False,False
  raise ValueError(('Unsupported return-use opcode',hex(w)))
 def check(pc):
  w=word(pc);reads,writes=effect(w)
  if reads:raise ValueError(('Query V0 is consumed',hex(pc),hex(w)))
  seen.add(pc)
  if writes:kills.append(dict(pc=hex(pc),kind='overwrite'));return True
  return False
 while pending:
  pc=pending.pop()
  if pc in seen:continue
  if not 0x15126378<=pc<0x15127520:raise ValueError('Unclosed query return-use graph')
  w=word(pc);op=w>>26
  if check(pc):continue
  branch=op in(1,4,5,6,7,20,21,22,23)or(op==17 and w>>21&31==8)
  if branch:
   target=pc+4+(((w&65535)^32768)-32768)*4
   # Taken edges execute the delay. Non-likely false edges do too.
   if not check(pc+4):pending.append(target)
   likely=op in(20,21,22,23)or(op==17 and w>>16&2)
   if likely or not check(pc+4):pending.append(pc+8)
  elif op in(2,3):
   if check(pc+4):continue
   if op==3:kills.append(dict(pc=hex(pc),kind='next-call-before-use'))
   else:pending.append(((pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2))
  else:pending.append(pc+4)
 return dict(start=hex(start),visited_instructions=len(seen),kills=sorted({(r['pc'],r['kind'])for r in kills}),read_before_kill=False)
