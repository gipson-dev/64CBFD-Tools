"""Publisher memory/reference model, original ABI routes and native SDK harness."""
from pathlib import Path
from dataclasses import dataclass,replace
import struct,subprocess
from tools.experiments import game_state_byte_publisher_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_row_destination_fill import START
F,ENTRY,PROVIDER=source.FUNCTION,source.ENTRY,source.PROVIDER
STATE,FLAGS,ALT=0x22000,0x24000,0x26000
@dataclass(frozen=True)
class Case:
 status:int=255
 flags:int=1
 context:int=0x87654321
 mode:int=0
 phase:int=0
 seed:int=0

def symbols():return dict(D_800B0DF0=0x800B0DF0,D_800DBFF0=0x800DBFF0,D_800DD2E4=0x800DD2E4,D_800DBEA8=0x800DBEA8,func_151733E4=PROVIDER)

def fixture(c,s):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-512,512)}
 for p,n in ((STATE-32,192),(FLAGS-32,0x650),(ALT-32,192)):
  m.update({p+i:(i*13+c.seed+0x59)&255 for i in range(n)})
 for name in ('D_800DD2E4','D_800DBEA8'):
  for i in range(-8,16):m.setdefault(s[name]+i,(i*19+c.seed+0x6B)&255)
 put(m,s['D_800B0DF0'],STATE);put(m,s['D_800DBFF0'],FLAGS);put(m,FLAGS+0x5F0,c.flags);m[STATE+70]=c.status
 for i in range(3):m[STATE+5+i]=(c.seed+0x31+i*37)&255;m[ALT+5+i]=(c.seed+0x81+i*23)&255;m[s['D_800DD2E4']+i]=(c.seed+0xA1+i*17)&255
 return m

def effect(m,c,s):
 if c.mode&1:put(m,s['D_800B0DF0'],ALT)
 if c.mode&2:
  for i in range(3):m[s['D_800DD2E4']+i]=(c.seed+0xD1+i*11)&255
 if c.mode&4:m[s['D_800DBEA8']]=0xEE
 if c.mode&8:put(m,FLAGS+0x5F0,c.flags^1)

def reference(initial,c,s):
 m=dict(initial);calls=[]
 if m[read(m,s['D_800B0DF0'])+70]!=255:return m,calls
 selected=read(m,read(m,s['D_800DBFF0'])+0x5F0)&1;mode=6 if selected else 0;calls=[(s['func_151733E4'],(mode,mode,c.context&0xFFFFFFFF,0,0xFFFFFFFF))];effect(m,c,s)
 if selected:
  values=[m[s['D_800DD2E4']+i]for i in range(3)]
  for i,b in enumerate(values):m[s['D_800DBEA8']+i]=b
 else:
  current=read(m,s['D_800B0DF0'])
  for i in range(3):m[s['D_800DBEA8']+i]=m[current+5+i]
 return m,calls

class PublisherOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s or symbols(),connected=connected,arguments=(c.context,))
 def record_call(self,t):
  assert t==self.syms['func_151733E4'];a=tuple(self.arguments(5));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  effect(self.memory,self.case,self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}

def state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace)

def linked(obj,entry,s,label,output):
 text,functions,bindings=parse_object(obj);f=functions[F];assembly,unknown=emit_function(text,f,bindings,F,s);assert not unknown;p=output/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

class CallerOracle(PublisherOracle):
 def record_call(self,t):
  if t==ENTRY:
   a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a));self.case=replace(self.case,context=a[0]);return
  return super().record_call(t)

def controls():
    body=source.SELECTED
    return dict(gate=body.replace('value == -1','value != -1'),flag=body.replace('& 1','& 2'),mode=body.replace('(6, 6, context','(7, 6, context'),context=body.replace('6, 6, context','6, 6, 0').replace('0, 0, context','0, 0, 0'),sentinel=body.replace('context, 0, -1','context, 0, 0'),source=body.replace('state[5]','state[6]'),second=body.replace('D_800DD2E4[1]','D_800DD2E4[0]'),destination=body.replace('D_800DBEA8[2] = D_800DD2E4[2]','D_800DBEA8[1] = D_800DD2E4[2]'))
def native_harness():
    header=source.HEADERS;body=source.SELECTED;F=source.FUNCTION
    controls=globals()["controls"]()
    assert all(b!=body for b in controls.values())
    t=header+'\n'.join(b.replace(F,'test_'+n)for n,b in dict(selected=body,**controls).items())
    t+=r'''
    Generated1A0790State state0,state1,*D_800B0DF0;
    static union {u32 align;u8 bytes[0x650];} flagsData;
    u8 *D_800DBFF0;u8 D_800DD2E4[3],D_800DBEA8[3];
    typedef void(*Fn)(s32);
    static int calls,bad,mode,active,choice;static s32 context;
    s32 func_151733E4(s32 a,s32 b,s32 c,s32 d,s32 e){int i;
     if(calls++||!active||a!=(choice?6:0)||b!=a||c!=context||d||e!=-1)bad=1;
     if(mode&1)D_800B0DF0=&state1;
     if(mode&2)for(i=0;i<3;i++)D_800DD2E4[i]=(u8)(0xD1+i*11);
     if(mode&4)D_800DBEA8[0]=0xEE;
     if(mode&8)*(u32*)(flagsData.bytes+0x5F0)^=1;
     return -123;
    }
    static u32 flagWords[]={0,1,2,0xFFFFFFFF};
    static s32 contexts[]={0,1,(-2147483647-1),-1};
    static int check(Fn fn){int status,j,k,i;u32 flags;u8 expected[3];
     if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(state0)!=71)return 90;
     for(status=0;status<256;status++)for(j=0;j<4;j++)for(k=0;k<4;k++)for(mode=0;mode<16;mode++){
      for(i=0;i<71;i++){((u8*)&state0)[i]=0x31;((u8*)&state1)[i]=0x81;}
      state0.value=(s8)status;D_800B0DF0=&state0;D_800DBFF0=flagsData.bytes;
      for(i=0;i<3;i++){((u8*)&state0)[5+i]=(u8)(0x31+i*37);((u8*)&state1)[5+i]=(u8)(0x81+i*23);D_800DD2E4[i]=(u8)(0xA1+i*17);D_800DBEA8[i]=expected[i]=(u8)(0x71+i*13);}
      flags=flagWords[j];*(u32*)(flagsData.bytes+0x5F0)=flags;context=contexts[k];active=status==255;choice=(flags&1)!=0;calls=bad=0;
      if(active)for(i=0;i<3;i++)expected[i]=choice?(u8)((mode&2)?0xD1+i*11:0xA1+i*17):(u8)((mode&1)?0x81+i*23:0x31+i*37);
      fn(context);if(bad||calls!=active)return 1;
      for(i=0;i<3;i++)if(D_800DBEA8[i]!=expected[i])return 2;
      for(i=0;i<71;i++)if((i<5||i>7)&&i!=70&&(((u8*)&state0)[i]!=0x31||((u8*)&state1)[i]!=0x81))return 3;
     }return 0;
    }
    static int run(void){if(check(test_selected))return 10;
    '''
    for i,n in enumerate(controls):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    t+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    return t
