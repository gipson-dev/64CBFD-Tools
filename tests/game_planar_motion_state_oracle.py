"""Planar state callback IEEE-single model and original callback dispatcher."""
from pathlib import Path
from dataclasses import dataclass
import itertools,struct,subprocess
from tools.experiments import game_planar_motion_state_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_row_destination_fill import START
ROOT=Path(__file__).resolve().parents[2];o=ROOT/source.BUILD
F,ENTRY,ROM=source.FUNCTION,source.ENTRY,source.ROM
ACTOR,MOTION=0x30000,0x70000
VECTOR,ANGLE,DELTA=0x15144B34,0x150484A0,0x15144C8C
syms=dict(D_80082FA4=0x80082FA4,D_800A0310=0x800A0310,D_800A0314=0x800A0314,func_15144B34=VECTOR,func_150484A0=ANGLE,func_15144C8C=DELTA)
bits=lambda f:struct.unpack('>I',struct.pack('>f',f))[0]
value=lambda b:struct.unpack('>f',struct.pack('>I',b))[0]
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 state:int=6
 x:int=0
 z:int=0
 difference:int=0x3F000000
 angle:int=0x3FA00000
 heading:int=0x3F800000
 player:int=1
 mode:int=0
 phase:int=0

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for p,n in ((ACTOR-16,544),(MOTION-16,64)):
  assert not(p<STACK+512 and p+n>STACK-512)
  for i in range(n):m[p+i]=(i*13+0x59)&255
 put(m,ACTOR+0x1C,c.state,2);put(m,ACTOR+0x160,c.heading);put(m,MOTION,c.x);put(m,MOTION+8,c.z)
 put(m,syms['D_80082FA4'],u32(c.player));put(m,syms['D_800A0310'],bits(2500000.0));put(m,syms['D_800A0314'],bits(0.4));m[ACTOR+0x10]=0;m[ACTOR+0x11]=60;return m

def effect(m,c,t):
 if t==VECTOR:
  if c.mode&1:put(m,ACTOR+0x1C,9,2)
  if c.mode&2:put(m,syms['D_800A0310'],bits(0.0))
 elif t==ANGLE:
  if c.mode&4:put(m,ACTOR+0x160,bits(2.0))
 elif t==DELTA:
  if c.mode&8:put(m,syms['D_800A0314'],bits(1.0));put(m,ACTOR+0x1C,7,2)

def reference(initial,c):
 m=dict(initial);calls=[];state=((c.state&65535)^32768)-32768;stop=False
 if state>=6:
  calls.append((VECTOR,(u32(c.player),)));effect(m,c,VECTOR)
  x,z=value(c.x),value(c.z);squared=value(bits(value(bits(x*x))+value(bits(z*z))))
  if squared<value(read(m,syms['D_800A0310'])):stop=True
  else:
   calls.append((ANGLE,(c.x,c.z)));effect(m,c,ANGLE)
   calls.append((DELTA,(c.angle,read(m,ACTOR+0x160))));effect(m,c,DELTA)
   if value(read(m,syms['D_800A0314']))<value(c.difference):stop=True
 if stop:put(m,ACTOR+0x1C,5,2)
 return m,calls

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None):super().__init__(words,memory,c,entry=entry,s=syms,connected=connected,arguments=(ACTOR,))
 def record_call(self,t):
  assert t in (VECTOR,ANGLE,DELTA),hex(t);a=tuple(self.arguments(1))if t==VECTOR else(self.f[12],self.f[14]);self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  effect(self.memory,self.case,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.condition=True
  if t==VECTOR:self.r[2]=MOTION
  else:self.f[0]=self.case.angle if t==ANGLE else self.case.difference

def public(m):return {a:b for a,b in m.items()if not STACK-512<=a<STACK+512}

def linked(obj,label,entry=ENTRY,s=None):
 s=syms if s is None else s;text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

class Caller(Oracle):
 def record_call(self,t):
  if t==ENTRY:
   a=tuple(self.arguments(1));assert a==(ACTOR,);self.calls.append((t,a));self.events.append(('CALL',t,a));return
  return super().record_call(t)

def native_harness():
    header=source.HEADERS;body=source.SELECTED;F=source.FUNCTION
    controls=dict(signed_state=body.replace('if (*(s16 *)(actor + 0x1C) >= 6)','if (*(u16 *)(actor + 0x1C) >= 6)'),state_boundary=body.replace('>= 6','> 6'),magnitude_equality=body.replace('x < D_800A0310','x <= D_800A0310'),angle_equality=body.replace('D_800A0314 < x','D_800A0314 <= x'),early_heading=body.replace('            x = func_150484A0(motion[0], motion[2]);','            z = *(f32 *)(actor + 0x160);\n            x = func_150484A0(motion[0], motion[2]);').replace('func_15144C8C(x, *(f32 *)(actor + 0x160))','func_15144C8C(x, z)'),early_threshold=body.replace('            x = func_15144C8C(x, *(f32 *)(actor + 0x160));','            z = D_800A0314;\n            x = func_15144C8C(x, *(f32 *)(actor + 0x160));').replace('D_800A0314 < x','z < x'))
    assert all(t!=body for t in controls.values());t=header+'\n'.join(b.replace(F,'test_'+n)for n,b in dict(selected=body,**controls).items())
    t+=r'''
    static u32 actorWords[128],motionWords[3];static u8 before[512];static s32 mode,calls,bad,active,closeCase;
    static u32 wantedX,wantedZ,wantedDifference;static s32 wantedPlayer;
    s32 D_80082FA4;f32 D_800A0310,D_800A0314;
    static u32 asBits(f32 value){union{f32 f;u32 u;}v;v.f=value;return v.u;}
    static f32 asFloat(u32 value){union{f32 f;u32 u;}v;v.u=value;return v.f;}
    f32 *func_15144B34(s32 player){
     if(calls++||!active||player!=wantedPlayer)bad=1;
     if(mode&1)*(s16*)((u8*)actorWords+0x1C)=9;
     if(mode&2)D_800A0310=0.0f;
     return(f32*)motionWords;
    }
    f32 func_150484A0(f32 x,f32 z){
     if(calls++!=1||!active||closeCase||asBits(x)!=wantedX||asBits(z)!=wantedZ)bad=1;
     if(mode&4)*(f32*)((u8*)actorWords+0x160)=2.0f;
     return 1.25f;
    }
    f32 func_15144C8C(f32 angle,f32 heading){
     if(calls++!=2||!active||closeCase||asBits(angle)!=asBits(1.25f)||asBits(heading)!=asBits((mode&4)?2.0f:1.0f))bad=1;
     if(mode&8){D_800A0314=1.0f;*(s16*)((u8*)actorWords+0x1C)=7;}
     return asFloat(wantedDifference);
    }
    typedef s32(*Fn)(u8*);
    static s32 states[]={-32768,-1,5,6,7,32767},modes[]={0,1,6,15};
    static u32 vectors[][2]={{0,0},{0x44BB8000u,0x43FA0000u},{0x44FA0000u,0},{0x7FC12345u,0x3F800000u},{0x7F800000u,0x3F800000u}};
    static u32 differences[]={0,0x3ECCCCCDu,0x3F000000u,0x7FC12345u,0x3F800000u};
    static int check(Fn fn){s32 s,v,d,m,i,result,wanted;u8 *actor=(u8*)actorWords;
     for(s=0;s<6;s++)for(v=0;v<5;v++)for(d=0;d<5;d++)for(m=0;m<4;m++){
      for(i=0;i<512;i++)actor[i]=(u8)(i*13+0x59);
      *(s16*)(actor+0x1C)=(s16)states[s];*(f32*)(actor+0x160)=1.0f;for(i=0;i<512;i++)before[i]=actor[i];
      wantedX=motionWords[0]=vectors[v][0];motionWords[1]=0x87654321;wantedZ=motionWords[2]=vectors[v][1];wantedDifference=differences[d];mode=modes[m];active=states[s]>=6;closeCase=v==0&&!(mode&2);wantedPlayer=D_80082FA4=m;D_800A0310=2500000.0f;D_800A0314=0.4f;wanted=states[s];
      if(active){
       if(mode&1)wanted=9;
       if(closeCase)wanted=5;
       else{if(mode&8)wanted=7;if(!(mode&8)&&(d==2||d==4))wanted=5;}
      }
      calls=bad=0;result=fn(actor);if(bad||result!=1||calls!=(active?(closeCase?1:3):0)||*(s16*)(actor+0x1C)!=wanted)return 1;
      for(i=0;i<512;i++)if(!(i==0x1C||i==0x1D||(i>=0x160&&i<0x164))&&actor[i]!=before[i])return 2;
      if(asBits(*(f32*)(actor+0x160))!=asBits(active&&!closeCase&&(mode&4)?2.0f:1.0f))return 3;
     }return 0;
    }
    static int run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
    '''
    for i,n in enumerate(controls):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    t+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');
    return t
