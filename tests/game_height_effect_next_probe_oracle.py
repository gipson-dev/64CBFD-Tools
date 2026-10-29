"""Private height-effect ABI and IEEE-single behavioral qualification."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/"conker/build/game-height-effect-next-probe-match";F='func_151AA09C';ENTRY=0x151AA09C;OWNER,ACTOR,OTHER=0x30000,0x70000,0x90000;QUERY,EFFECT=0x15045800,0x151ABE40
syms=dict(D_800A8F90=0x800A8F90,func_15045800=QUERY,func_151ABE40=EFFECT)
bits=lambda f:struct.unpack('>I',struct.pack('>f',f))[0]
value=lambda b:struct.unpack('>f',struct.pack('>I',b))[0]
rom=(r/'conker/conker.us.bin').read_bytes();THRESHOLD=struct.unpack_from('>I',rom,0x2275E0+0x800A8F90-0x80082B20)[0]
@dataclass(frozen=True)
class Case:
 top:int=bits(1000.)
 y:int=bits(200.)
 x:int=bits(125.25)
 z:int=bits(-75.5)
 outcome:int=1
 mode:int=0
 identity:int=255
 category:int=128
 height:int=bits(17.5)
 phase:int=0
 @property
 def position(self):return STACK+self.phase-16
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for p,n in((OWNER-32,256),(ACTOR-32,384),(OTHER-32,384)):
  assert not(p<STACK+1024 and p+n>STACK-1024)
  m.update({p+i:(i*13+0x59)&255 for i in range(n)})
 put(m,OWNER+24,ACTOR);put(m,ACTOR+20,c.x);put(m,ACTOR+24,c.y);put(m,ACTOR+28,c.z);put(m,ACTOR+280,c.top);put(m,syms['D_800A8F90'],THRESHOLD);m[OWNER+1]=c.identity;m[OWNER+12]=c.category;return m
def effect(m,c,t):
 if t==QUERY:
  put(m,OWNER+52,c.height);m[OWNER+80]^=0x40
  if c.mode&1:m[OWNER+1]^=0xFF;m[OWNER+12]^=0x55
  if c.mode&2:put(m,c.position,bits(-77.25));put(m,c.position+8,bits(99.5));put(m,c.position+4,bits(-999.))
  if c.mode&4:put(m,OWNER+24,OTHER)
 elif t==EFFECT:m[OWNER+53]^=0xAA;m[OWNER+81]^=0x20
def reference(initial,c):
 m=dict(initial);p=c.position;top=value(read(m,ACTOR+280));y=bits(top+100.)if value(THRESHOLD)<top else bits(value(read(m,ACTOR+24))+150.)
 for i,v in enumerate((read(m,ACTOR+20),y,read(m,ACTOR+28))):put(m,p+4*i,v)
 calls=[(QUERY,(p,0,bits(value(y)-300.),OWNER+52),tuple(read(m,p+i*4)for i in range(3)))];effect(m,c,QUERY)
 if c.outcome:
  put(m,p+4,read(m,OWNER+52));calls.append((EFFECT,(p,OWNER+52,4,m[OWNER+12],m[OWNER+1]),tuple(read(m,p+i*4)for i in range(3))));effect(m,c,EFFECT)
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,connected=None):super().__init__(words,memory,c,entry=entry,s=syms,connected=connected,arguments=(OWNER,))
 def record_call(self,t):
  assert t in(QUERY,EFFECT),hex(t);a=tuple(self.arguments(4 if t==QUERY else 5));position=tuple(read(self.memory,a[0]+4*i)for i in range(3));self.calls.append((t,a,position));self.events.append(('CALL',t,a,position))
 def hook(self,t):
  effect(self.memory,self.case,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.condition=True;self.r[2]=self.case.outcome&0xFFFFFFFF if t==QUERY else 0xA5000002
def linked(obj,label,entry=ENTRY,s=None):
 s=syms if s is None else s;text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
public=lambda m:{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}

from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 a=selected.index('/* Probe');header,body=selected[:a],selected[a:]
 mutants=dict(threshold_equality=body.replace('D_800A8F90 <','D_800A8F90 <='),high_offset=body.replace('+ 100.0f','+ 150.0f'),low_offset=body.replace('+ 150.0f','+ 100.0f'),probe_depth=body.replace('- 300.0f','- 150.0f'),omit_result_height=body.replace('        position[1] = *(f32 *)(owner + 0x34);\n',''),cached_metadata=body.replace('    u8 *actor;','    u8 *actor;\n    u8 identity = owner[1];\n    u8 category = owner[12];').replace('4, owner[0xC], owner[1]','4, category, identity'))
 assert all(s!=body for s in mutants.values())
 text=header+'\n'.join(s.replace(F,'test_'+n)for n,s in dict(selected=body,**mutants).items())
 text+=r'''
static u32 ownerWords[64], actorWords[96], otherWords[96];static u8 before[256];
static s32 calls,bad,outcome,mode;static u8 wantedIdentity,wantedCategory;
static f32 wantedY,wantedDepth;f32 D_800A8F90;
static u32 asBits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 asFloat(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
s32 func_15045800(f32 *p,u16 selector,f32 threshold,void *result){
 u8 *owner=(u8*)ownerWords;
 if(calls++!=0||selector||result!=owner+52||asBits(p[0])!=asBits(125.25f)||asBits(p[1])!=asBits(wantedY)||asBits(p[2])!=asBits(-75.5f)||asBits(threshold)!=asBits(wantedDepth))bad=1;
 *(f32*)(owner+52)=17.5f;owner[80]^=0x40;
 if(mode&1){owner[1]^=255;owner[12]^=0x55;}
 if(mode&2){p[0]=-77.25f;p[1]=-999.0f;p[2]=99.5f;}
 if(mode&4)*(void**)(owner+24)=otherWords;
 return outcome;
}
void func_151ABE40(f32 *p,void *result,s32 kind,u8 category,s32 identity){
 u8 *owner=(u8*)ownerWords;
 if(calls++!=1||!outcome||result!=owner+52||kind!=4||category!=(u8)(wantedCategory^((mode&1)?0x55:0))||identity!=(u8)(wantedIdentity^((mode&1)?255:0))||asBits(p[0])!=asBits((mode&2)?-77.25f:125.25f)||asBits(p[1])!=asBits(17.5f)||asBits(p[2])!=asBits((mode&2)?99.5f:-75.5f))bad=1;
 owner[53]^=0xAA;owner[81]^=0x20;
}
typedef void(*Fn)(u8*);
static u32 tops[]={0xC6147400u,0xC6147000u,0xC6146C00u,0x7FC12345u,0x7F800000u,0xFF800000u};
static u32 ys[]={0xC3160000u,0x43480000u,0x7FC12345u};static s32 outcomes[]={0,1,-1},modes[]={0,1,2,7};
static int check(Fn fn){s32 t,y,a,m,id,i;u8 *owner=(u8*)ownerWords,*actor=(u8*)actorWords;
 for(t=0;t<6;t++)for(y=0;y<3;y++)for(a=0;a<3;a++)for(m=0;m<4;m++)for(id=0;id<2;id++){
  for(i=0;i<256;i++)owner[i]=(u8)(i*13+0x59);
  for(i=0;i<384;i++){actor[i]=(u8)(i*7+0xA5);((u8*)otherWords)[i]=(u8)(i*3+0x35);}
  *(void**)(owner+24)=actor;*(f32*)(actor+20)=125.25f;*(f32*)(actor+24)=asFloat(ys[y]);*(f32*)(actor+28)=-75.5f;*(f32*)(actor+280)=asFloat(tops[t]);
  mode=modes[m];outcome=outcomes[a];wantedIdentity=owner[1]=id?255:0;wantedCategory=owner[12]=128;D_800A8F90=-9500.0f;
  wantedY=(asFloat(tops[t])>-9500.0f)?asFloat(tops[t])+100.0f:asFloat(ys[y])+150.0f;wantedDepth=wantedY-300.0f;
  for(i=0;i<256;i++)before[i]=owner[i];calls=bad=0;fn(owner);
  if(bad||calls!=(outcome?2:1))return 1;
  for(i=0;i<256;i++)if(!(i==1||i==12||(i>=24&&i<28)||(i>=52&&i<56)||i==80||i==81)&&owner[i]!=before[i])return 2;
  if(owner[1]!=(u8)(wantedIdentity^((mode&1)?255:0))||owner[12]!=(u8)(wantedCategory^((mode&1)?0x55:0)))return 3;
 }return 0;
}
static int run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
'''
 for i,n in enumerate(mutants):text+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return text+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
