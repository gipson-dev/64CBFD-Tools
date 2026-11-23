"""Private two-stream semantic screen; no adoption or matching credit."""
from pathlib import Path
import hashlib
from dataclasses import dataclass,replace
import itertools,json,math,struct,sys
from tools.experiments import game_compact_sprite_renderer_15168118_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15168118;STATE=0x30000;META=0x70000;CAMERA=0x90000;OUTPUT=0x50000;FRAMES=0x11000000
u32=lambda n:n&0xffffffff;s16=lambda n:((n&65535)^32768)-32768;s32=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
bits=lambda f:int.from_bytes(struct.pack('>f',f),'big');floating=lambda n:struct.unpack('>f',u32(n).to_bytes(4,'big'))[0]
f32=lambda f:floating(bits(f))
elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();SYMS={n:f[1]for _,n,f,_ in symbol_rows(elf)if n}
NAMES=('func_15142E24','func_15142B7C','func_1513F4E4','func_15142FBC','func_15142CF0','func_15142C10','func_15095760')
COUNTS=dict(zip((SYMS[n]for n in NAMES),(11,3,3,4,8,6,2)));NAME={SYMS[n]:n for n in NAMES}
def get(m,p,n=4):return int.from_bytes(bytes(m[u32(p+i)]for i in range(n)),'big')
def put(m,p,v,n=4):m.update({u32(p+i):b for i,b in enumerate((v&((1<<(n*8))-1)).to_bytes(n,'big'))})
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def half(m,p):return s16(get(m,p,2))
@dataclass(frozen=True)
class Case:
 flags:int=0
 texture_type:int=5
 width:int=1024
 height:int=512
 yaw:float=0
 pitch:float=0
 orientation:int=0
 position:int=257
 view:int=0
 special:int=0
 frame_table:bool=False
 effect:int=0
 phase:int=0
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 for p,n in((STATE,0x4C),(META,64),(OUTPUT,192),(SYMS['D_800907FC'],16),(SYMS['D_8009053C'],16)):
  m.update({p+i:(i*13+7)&255 for i in range(-16,n+16)})
 texture=(META,SYMS['D_800907FC'],SYMS['D_8009053C'])[c.special]
 put(m,STATE+0x10,texture);put(m,texture,FRAMES if c.frame_table else 0x2345678);m[texture+0xA]=c.texture_type
 put(m,FRAMES+(c.position>>8)*4,0x456789A)
 for off,val in((0x1C,c.position),(0x20,-32768),(0x22,19),(0x24,32767),(0x34,c.width),(0x36,c.height),(0x44,c.flags)):put(m,STATE+off,val,2)
 put(m,STATE+0x14,0x000D0011);put(m,STATE+0x18,c.orientation)
 put(m,SYMS['D_800DBFF0'],CAMERA)
 for off,val in((0x380,c.yaw),(0x388,c.pitch)):put(m,CAMERA+s16(c.view)*0x9A0+off,bits(val))
 for n in('D_800A6CA0','D_800A6CA4'):
  at=elf_slot_offset(elf,SYMS[n],4);put(m,SYMS[n],int.from_bytes(elf[at:at+4],'big'))
 for i in range(80):put(m,SYMS['D_800A4AC8']+4*i,0x01020304*i^0xA55AA55A)
 return m
def effect(m,c,name,state=STATE):
 if name=='func_15142E24'and c.effect&1:
  put(m,state+0x34,-2000,2);put(m,state+0x36,-511,2);put(m,state+0x18,129)
 if name=='func_1513F4E4'and c.effect&2:
  put(m,state+0x44,get(m,state+0x44,2)^0x201,2)
  m[state+0x3C]^=0x5A;m[state+0x40]^=0xA5
 if name=='func_15142CF0'and c.effect&4:
  put(m,state+0x44,get(m,state+0x44,2)|1,2);m[state+0x41]^=0xAA
def observation(m,name,args,packet,sync):
 if name=='func_15142E24':return(name,args[:8]+('packet','sync',args[10]),get(m,sync,1),get(m,packet+13,1))
 if name=='func_15095760':return(name,(args[0],'packet'),data(m,packet,20))
 return(name,args[:-1]+('sync',)if name not in('func_15142B7C',)else args,get(m,sync,1))
def contract(m,c,name,args,packet,sync,state=STATE):
 output=args[0]
 if name=='func_15142E24':
  mask=get(m,packet+13,1)
  for i in range(20):put(m,packet+i,i*11+3,1)
  put(m,packet+13,mask,1)
 if name not in('func_15142B7C','func_15095760'):put(m,sync,0,1)
 # Each provider writes a bounded command and returns its next cursor. This
 # is a contract, not a claim that the providers' entire implementations ran.
 put(m,output,0xA0000000|NAMES.index(name));put(m,output+4,sum(v for v in args[1:]if isinstance(v,int)and not STACK-2048<=v<STACK+512))
 effect(m,c,name,state);return output+8
def reference(initial,c):
 m=dict(initial);packet=STACK+c.phase-20;sync=STACK+c.phase-29;log=[];output=OUTPUT
 def call(name,*args):
  log.append(observation(m,name,args,packet,sync));return contract(m,c,name,args,packet,sync)
 flags=get(m,STATE+0x44,2);put(m,packet+13,(1 if flags&4 else 0)|(2 if flags&8 else 0),1);put(m,sync,1,1)
 texture=get(m,STATE+0x10);image=get(m,texture)
 if image>=0x10000000:image=get(m,u32(image+(half(m,STATE+0x1C)>>8)*4))
 output=call('func_15142E24',output,texture,u32(half(m,STATE+0x1C)<<8),2,256,256,image,5,packet,sync,3)
 view=s16(c.view)
 for off in(0,2,4):put(m,packet+off,half(m,STATE+0x20+off),2)
 dimension=half(m,STATE+0x34)
 if dimension<0:
  angle=abs(f32(floating(get(m,CAMERA+view*0x9A0+0x380))+f32((get(m,STATE+0x18)&255)*1.40625)))
  while angle>=360:angle=f32(angle-360)
  if angle>=180:angle=f32(angle-180)
  if angle>=90:angle=f32(180-angle)
  dimension=math.trunc(f32(f32(dimension*angle)*floating(get(m,SYMS['D_800A6CA0']))));dimension=max(1024,dimension)
 put(m,packet+6,dimension,2);dimension=half(m,STATE+0x36)
 if dimension<0:
  base=max(0,half(m,STATE+0x34));scale=abs(floating(get(m,CAMERA+view*0x9A0+0x388)))
  dimension=math.trunc(f32(f32(f32(scale*(base+dimension))*floating(get(m,SYMS['D_800A6CA4'])))-f32(dimension)))
 put(m,packet+8,dimension,2);flags=get(m,STATE+0x44,2)
 if flags&0x100:
  settings=get(m,STATE+0x14);combiner=(settings>>16)&255;mode=settings&255
  output=call('func_15142B7C',output,5,0);output=call('func_1513F4E4',output,combiner,sync)
  mode_bits=0x100000 if get(m,STATE+0x44,2)&0x200 else 0
 else:
  kind=get(m,get(m,STATE+0x10)+0xA,1)
  if kind!=5:combiner=13;mode=3;mode_bits=0
  elif flags&0x10:combiner=13;mode=18;mode_bits=0
  else:combiner=15;mode=17;mode_bits=0x100000
  output=call('func_1513F4E4',output,combiner,sync)
 render=get(m,SYMS['D_800A4AC8']+mode*8)|get(m,SYMS['D_800A4AC8']+mode*8+4)|4
 output=call('func_15142FBC',output,mode_bits|get(m,SYMS['D_800D2C9C'])|0x2CA0,render,sync)
 output=call('func_15142CF0',output,1,0,*data(m,STATE+0x3C,4),sync)
 if get(m,STATE+0x44,2)&1:color=tuple(data(m,STATE+0x40,3))
 else:
  texture=get(m,STATE+0x10);color=(128,128,255)if texture==SYMS['D_800907FC']else(255,255,255)if texture==SYMS['D_8009053C']else(0,0,0)
 output=call('func_15142C10',output,*color,0,sync);output=call('func_15095760',output,packet)
 return m,log,output
class Oracle(FactoryOracle):
 run=TriangleOracle.run
 def execute(self,word):
  if word>>26==17 and word>>21&31==16 and word&63==5:
   self.f[word>>6&31]=self.f[word>>11&31]&0x7FFFFFFF
  else:super().execute(word)
 def __init__(self,words,memory,c,entry=ENTRY,connected=None,arguments=None):
  super().__init__(words,memory,c,entry=entry,s=SYMS,arguments=(OUTPUT,STATE,u32(c.view))if arguments is None else arguments,connected=connected)
  self.before=self.r[:];self.initial=dict(memory);self.observations=[];self.packet=None;self.sync=None;self.target_calls=[]
 def record_call(self,t):
  if t==ENTRY:
   a=tuple(map(u32,self.arguments(3)));self.target_calls.append(a)
   assert a==(OUTPUT,STATE,u32(s16(self.case.view))),('Wrong renderer arguments',a)
   return
  a=tuple(map(u32,self.arguments(COUNTS[t])));name=NAME[t]
  if name=='func_15142E24':self.packet,self.sync=a[8:10]
  self.calls.append((t,a));self.observations.append(observation(self.memory,name,a,self.packet,self.sync))
 def hook(self,t):
  value=contract(self.memory,self.case,NAME[t],self.calls[-1][1],self.packet,self.sync)
  for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+512}
def cases():
 rows=[Case(flags=f,texture_type=t,special=s,frame_table=b,effect=e)for f,t,s,b,e in itertools.product((0,1,4,8,12,16,0x100,0x101,0x300),(0,3,5),(0,1,2),(False,True),(0,1,2,4,7))]
 rows +=[Case(width=w,height=h,yaw=y,pitch=p,orientation=a,view=v,phase=phase)for w,h,y,p,a,v,phase in itertools.product((-32768,-2000,-1,0,32767),(-3000,-1,0,32767),(-720.5,90,359.999),(-90,0,30),(0,255),(0,1,0xFFFF),(0,8))]
 return rows
def main():
 label=sys.argv[1]if len(sys.argv)>1 else'typed'
 raw=bound_blob(*payload(o/label/'candidate.o','func_15168118'),SYMS)
 original=list(struct.unpack('>337I',(r/'conker/conker.us.bin').read_bytes()[0x1955C8:0x195B0C]))
 rows=cases()
 result={}
 for name,ws in(('raw',raw),('retail',original)):
  seen=set()
  for c in rows:
   memory=fixture(c);put(memory,SYMS['D_800D2C9C'],0x40000)
   want,log,value=reference(memory,c);m=Oracle(ws,memory,c);m.run()
   assert(m.observations,m.r[2],public(m.memory))==(log,value,public(want)),(name,c,m.observations,log,m.r[2],value)
   seen.update(m.visits)
  result[name]=dict(cases=len(rows),unexecuted=[i for i in range(len(ws))if ENTRY+4*i not in seen])
 report=dict(target_label=label,raw_sha256=hashlib.sha256(payload(o/label/'candidate.o','func_15168118')[0]).hexdigest(),streams=result,helper_contracts=True,independent_f32_model=True,source_installed=False,matching_credit=0)
 (o/(label+'-guest-screen.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
