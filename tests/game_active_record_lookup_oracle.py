"""Read-only active-record lookup model, GNU rebasing and native SDK harness."""
from pathlib import Path
from dataclasses import dataclass
import json,struct,subprocess
from tools.experiments import game_active_record_lookup_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_row_destination_fill import START
F,ENTRY,TABLE=source.FUNCTION,source.ENTRY,source.TABLE
GLOBAL=0x80084498
@dataclass(frozen=True)
class Case:
 phase:int=0

def linked(obj,entry,table,label,output):
 text,functions,bindings=parse_object(obj);f=functions[F];assembly,unknown=emit_function(text,f,bindings,F,{'D_80087430':table});assert not unknown;p=output/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\nD_80087430 = 0x%X;\n'%(entry,table))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

def fixture(table,hit,flags=0,key=0x20000000,active=1):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for i in range(204):
  for j in range(20):m[table+i*20+j]=(i*29+j*13)&255
  put(m,table+i*20,0 if i%17==0 else 0x80000001);put(m,table+i*20+4,(flags<<29)|((i+33)&0x1FFFFFFF))
 # Inactive matching records must be skipped. Duplicate later matches must lose.
 for i in range(0,204,17):put(m,table+i*20+4,(flags<<29)|((key-1)&0x1FFFFFFF))
 if hit<204:
  put(m,table+hit*20,active);put(m,table+hit*20+4,(flags<<29)|((key-1)&0x1FFFFFFF))
  if hit+1<204:put(m,table+(hit+1)*20,1);put(m,table+(hit+1)*20+4,(flags<<29)|((key-1)&0x1FFFFFFF))
 return m

def reference(m,table,key):
 for i in range(204):
  p=table+i*20;active=int.from_bytes(bytes(m[p+j]for j in range(4)),'big')
  if active:
   value=int.from_bytes(bytes(m[p+4+j]for j in range(4)),'big')
   if (value&0x1FFFFFFF)+1==key:return i
 return 204

def machine(words,m,key,entry=ENTRY,phase=0):return FactoryOracle(words,m,Case(phase),entry=entry,s={},arguments=(key,))

def state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace)

class WindowOracle(FactoryOracle):
 def record_call(self,t):
  assert t==ENTRY;args=tuple(self.arguments(1));self.calls.append((t,args));self.events.append(('CALL',t,args))

def controls():
    body=source.SELECTED
    return dict(active=body.replace('.field0 != 0','.field0 == 0'),mask=body.replace('0x1FFFFFFF','0xFFFFFFFF'),increment=body.replace(') + 1 == key',') == key'),first_index=body.replace('return index;','return index + 1;'),third_key=body.replace('entry[2].field4','entry[3].field4'),sentinel=body.replace('return 204;','return 203;'),bounds=body.replace('index != 204','index != 200'))

def native_harness():
    header=source.HEADERS;body=source.SELECTED;F=source.FUNCTION
    controls=globals()["controls"]()
    assert all(b!=body for b in controls.values())
    t=header+'\n'.join(b.replace(F,'test_'+n)for n,b in dict(selected=body,**controls).items())
    t+=r'''
    GeneratedC9EC0Entry D_80087430[204];
    typedef s32(*Fn)(u32);
    static u8 saved[4080];
    static int check(Fn fn){u32 key,flags;int hit,i,j,negative;u8 *bytes=(u8*)D_80087430;s32 answer;
     if(sizeof(GeneratedC9EC0Entry)!=20)return 90;
     for(hit=0;hit<=204;hit++)for(flags=0;flags<8;flags++)for(j=0;j<2;j++)for(negative=0;negative<2;negative++){
      key=j?0x20000000:1;
      for(i=0;i<4080;i++)bytes[i]=(u8)(i*13+hit);
      for(i=0;i<204;i++){
       D_80087430[i].field0=(i%17)?-1:0;
       D_80087430[i].field4=(s32)((flags<<29)|(i+33));
       if(i%17==0)D_80087430[i].field4=(s32)((flags<<29)|(key-1));
      }
      if(hit<204){
       D_80087430[hit].field0=negative?(-2147483647-1):1;
       D_80087430[hit].field4=(s32)((flags<<29)|(key-1));
       if(hit+1<204){D_80087430[hit+1].field0=1;D_80087430[hit+1].field4=(s32)((flags<<29)|(key-1));}
      }
      for(i=0;i<4080;i++)saved[i]=bytes[i];answer=fn(key);
      if(answer!=hit)return 1;
      for(i=0;i<4080;i++)if(saved[i]!=bytes[i])return 2;
     }
     for(i=0;i<204;i++){D_80087430[i].field0=1;D_80087430[i].field4=-1;}
     if(fn(0)!=204||fn(0x20000001)!=204||fn(0xFFFFFFFF)!=204)return 3;
     return 0;
    }
    static int run(void){if(check(test_selected))return 10;
    '''
    for i,n in enumerate(controls):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    t+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    return t
