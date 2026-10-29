"""Randomized owner packet guest model and native32 harness."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,struct,subprocess
from tools.experiments import game_owner_random_packet_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];o=ROOT/source.BUILD
F,ENTRY,ROM=source.FUNCTION,source.ENTRY,source.ROM
RANDOM,FACTORY,COPY,OWNER,OUTPUT=0x150ADA20,0x15149130,0x10022EC0,0x30000,0x50000
syms=dict(func_150ADA20=RANDOM,func_15149130=FACTORY,memcpy=COPY)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 variant:int=0x87654321
 priority:int=0x1234ABFF
 context:int=0x87654321
 random:int=0xFFFFFFFF
 outcome:int=1
 mutation:int=0
 phase:int=0
 seed:int=0
 first:int=0x3F800000
 second:int=0x40000000

def fixture(c):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-512,512)}
 for base,n in ((OWNER-16,0x180),(OUTPUT-16,128)):
  for i in range(n):m[base+i]=(i*13+c.seed+0x59)&255
 m[OWNER+0x3B]=0x87;put(m,OWNER+0x84,0xCDEF,2);put(m,OWNER+0x14C,c.first);put(m,OWNER+0x150,c.second);return m

def args(c):return (OWNER,u32(c.variant),u32(c.priority),u32(c.context))

def mutate(m,mask):
 if mask:
  m[OWNER+0x3B]=0x11;put(m,OWNER+0x84,0x1234,2);put(m,OWNER+0x14C,0x42C80000);put(m,OWNER+0x150,0x43480000)

def reference(initial,c):
 m=dict(initial);packet=STACK+c.phase-20;put(m,packet,OWNER);m[packet+4]=0x87
 first=struct.unpack('>f',struct.pack('>I',c.first))[0];second=struct.unpack('>f',struct.pack('>I',c.second))[0];total=struct.unpack('>f',struct.pack('>f',first+second))[0]
 put(m,packet+8,struct.unpack('>I',struct.pack('>f',total*0.5))[0]);m[packet+13]=c.variant&255;calls=[(RANDOM,())];mutate(m,c.mutation&1)
 m[packet+12]=c.random%56+200;put(m,packet+6,read(m,OWNER+0x84,2),2)
 calls.append((FACTORY,(300,0xFFFFFFFF,0x61,4,0,0x31,16,c.priority&255,u32(c.context))));mutate(m,c.mutation&2)
 payload=bytes(m[packet+i]for i in range(16))
 if c.outcome:
  calls.append((COPY,(OUTPUT+40,packet,16)))
  for i,b in enumerate(payload):m[OUTPUT+40+i]=b
 return m,calls,payload

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None):super().__init__(words,memory,c,entry=entry,s=s or syms,connected=connected,arguments=args(c));self.packets=[]
 def record_call(self,t):
  assert t in (RANDOM,FACTORY,COPY);a=tuple(self.arguments({RANDOM:0,FACTORY:9,COPY:3}[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==COPY:self.packets.append(bytes(self.memory[a[1]+i]for i in range(a[2])))
 def hook(self,t):
  if t==RANDOM:mutate(self.memory,self.case.mutation&1);value=self.case.random
  elif t==FACTORY:mutate(self.memory,self.case.mutation&2);value=OUTPUT if self.case.outcome else 0
  else:
   a=self.calls[-1][1]
   for i,b in enumerate(self.packets[-1]):self.memory[a[0]+i]=b
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def public(m):return {a:b for a,b in m.items()if not STACK-512<=a<STACK+512}

def linked(obj,entry,label,s=syms):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

def native_harness():
    header=source.HEADERS;body=source.SELECTED;F=source.FUNCTION
    controls=dict(modulus=body.replace('% 56U','% 55U'),signed_random=body.replace('(u32)func_150ADA20()','func_150ADA20()').replace('% 56U','% 56'),scale=body.replace('* 0.5f','* 0.25f'),copy=body.replace('sizeof(packet));','12);'),early_flags=body.replace('    packet.flags = *(u16 *)((u8 *)owner + 0x84);\n','').replace('    packet.randomByte =','    packet.flags = *(u16 *)((u8 *)owner + 0x84);\n    packet.randomByte ='))
    assert all(b!=body for b in controls.values());t=header+'\n'.join(b.replace(F,'test_'+n)for n,b in dict(selected=body,**controls).items())
    t+=r'''
    static u32 ownerWords[0x180/4],outputWords[96/4];static int mode,outcome,bad,calls,copies;static u32 randomValue;static u8 expected[16];
    static u8 *owner=(u8*)ownerWords,*output=(u8*)outputWords;static u8 wantedVariant,wantedPriority;static s32 wantedContext;
    static void mutation(void){owner[0x3B]=0x11;*(u16*)(owner+0x84)=0x1234;*(f32*)(owner+0x14C)=100.0f;*(f32*)(owner+0x150)=200.0f;}
    s32 func_150ADA20(void){if(calls++!=0)bad=1;if(mode&1)mutation();return (s32)randomValue;}
    void *func_15149130(s16 a,s8 b,s8 c,s8 d,u8 e,u8 f,s32 g,u8 h,s32 i){
     if(calls++!=1||a!=300||b!=-1||c!=0x61||d!=4||e||f!=0x31||g!=16||h!=wantedPriority||i!=wantedContext)bad=1;
     if(mode&2)mutation();return outcome?output:0;
    }
    void *memcpy(void *dest,const void *src,u32 n){u32 i;u8 *to=dest;const u8 *from=src;
     if(copies++||calls!=2||dest!=output+40||n!=16)bad=1;
     for(i=0;i<n;i++){if(i!=5&&i!=14&&i!=15&&from[i]!=expected[i])bad=1;to[i]=from[i];}return dest;
    }
    typedef void(*Fn)(void*,u8,u8,s32);
    static u32 randoms[]={0,55,56,255,0x80000000u,0xFFFFFFFFu};
    static f32 firsts[]={1.0f,-1.0f,-0.0f,0.5000000596046448f},seconds[]={2.0f,1.0f,0.0f,1.0000003576278687f};
    static int check(Fn fn){int j,k,i,v;OwnerRandomPacket packet;
     for(j=0;j<6;j++)for(k=0;k<4;k++)for(v=0;v<4;v++)for(outcome=0;outcome<2;outcome++)for(mode=0;mode<4;mode++){
      for(i=0;i<0x180;i++)owner[i]=(u8)(i*13+0x59);for(i=0;i<96;i++)output[i]=(u8)(i*17+0xA5);
      owner[0x3B]=0x87;*(u16*)(owner+0x84)=0xCDEF;*(f32*)(owner+0x14C)=firsts[k];*(f32*)(owner+0x150)=seconds[k];
      wantedVariant=(u8)(v*85);wantedPriority=(u8)(255-v*63);wantedContext=v?-123456789:0;randomValue=randoms[j];
      packet.owner=owner;packet.ownerId=0x87;packet.flags=(mode&1)?0x1234:0xCDEF;packet.midpoint=(firsts[k]+seconds[k])*0.5f;packet.randomByte=(u8)(randomValue%56+200);packet.variant=wantedVariant;
      for(i=0;i<16;i++)if(i!=5&&i!=14&&i!=15)expected[i]=((u8*)&packet)[i];
      bad=calls=copies=0;fn(owner,wantedVariant,wantedPriority,wantedContext);
      if(bad||calls!=2||copies!=outcome)return 1;
      for(i=0;i<96;i++)if(!(outcome&&i>=40&&i<56)&&output[i]!=(u8)(i*17+0xA5))return 2;
     }return 0;
    }
    static int run(void){if(sizeof(void*)!=4||sizeof(OwnerRandomPacket)!=16)return 90;if(check(test_selected))return 10;
    '''
    for i,n in enumerate(controls):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    t+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    return t
