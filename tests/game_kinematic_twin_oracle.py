from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/'conker/build/game-kinematic-twin-match';F='func_150CBE88';ENTRY=0x150CBE88;TIME=0x800BE9A4
@dataclass(frozen=True)
class Case:
 time:int=0x3F800000
 pattern:int=0
 alias:int=-1
 phase:int=0
 @property
 def record(self):return 0x30000 if self.alias==-1 else TIME-self.alias

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)};p=c.record;assert not(p<STACK+1024 and p+128>STACK-1024);m.update({p+i:(i*13+0x59)&255 for i in range(128)})
 patterns=[(0x3F800000,0xBF000000,0x40000000),(0x80000000,0,0x80000000),(1,0x007FFFFF,0x80000001),(0x7F7FFFFF,0xFF7FFFFF,0x3F800000),(0x7FC12345,0x3F800000,0xBF800000),(0x7FC12345,0x7FC54321,0x3F800000)]
 for i,off in enumerate((0x20,0x24,0x28,0x38,0x3C,0x40,0x44,0x48,0x4C,0x50,0x54,0x58,0x5C)):put(m,p+off,patterns[c.pattern][i%3])
 put(m,TIME,c.time);return m
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
def reference(initial,c):
 m=dict(initial);p=c.record;acc=read(m,p+0x5C);vy=read(m,p+0x48)
 put(m,p+0x38,add(read(m,p+0x38),mul(read(m,p+0x44),read(m,TIME))))
 dt=read(m,TIME);put(m,p+0x3C,add(read(m,p+0x3C),add(mul(vy,dt),mul(mul(mul(acc,dt),dt),0x3F000000))))
 put(m,p+0x40,add(read(m,p+0x40),mul(read(m,p+0x4C),read(m,TIME))))
 put(m,p+0x48,add(vy,mul(acc,read(m,TIME))))
 for off,velocity in ((0x20,0x50),(0x24,0x54),(0x28,0x58)):put(m,p+off,add(read(m,p+off),mul(read(m,p+velocity),read(m,TIME))))
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c):super().__init__(words,memory,c,entry=ENTRY,s=dict(D_800BE9A4=TIME),arguments=(c.record,))
 def record_call(self,t):raise AssertionError(('Unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('Unexpected hook',hex(t)))
def linked(obj,label):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,dict(D_800BE9A4=TIME));assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\nD_800BE9A4 = 0x%X;\n'%(ENTRY,TIME));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

from tools.experiments.game_four_head_lookup_match import payload
G=TIME
def view(obj):
 raw,bindings=payload(obj,F);words=list(struct.unpack('>%dI'%(len(raw)//4),raw));g={4:('P',0),0:0};f={};memory={};stores=[];global_value=('initial_global',)
 def read(addr):
  if isinstance(addr,tuple):return memory.get(addr[1],('initial_record',addr[1]))
  assert addr==G;return global_value
 def address(base,off):
  if isinstance(base,tuple):assert base[0]=='P';return ('P',(base[1]+off)&0xFFFFFFFF)
  return (base+off)&0xFFFFFFFF
 for at,w in enumerate(words):
  rel=bindings.get(at*4,[])
  if rel:
   assert len(rel)==1 and rel[0][1]=='D_800BE9A4'
   kind=rel[0][0];w=(w&0xFFFF0000)|(((G+0x8000)>>16)&65535 if kind=='R_MIPS_HI16'else G&65535)
  op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fd=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if w==0 or w==0x03E00008:continue
  if op==15:g[rt]=(w&65535)<<16
  elif op==9:g[rt]=address(g[rs],imm)
  elif op==49:f[rt]=read(address(g[rs],imm))
  elif op==57:
   addr=address(g[rs],imm);assert isinstance(addr,tuple);value=f[rt];memory[addr[1]]=value;stores.append((addr[1],value));global_value=('if_global_aliases_record_offset',addr[1],value,global_value)
  elif op==17 and rs==4:f[rd]=('bits',g[rt])
  elif op==17 and rs==16 and fn in (0,2):f[fd]=('add'if fn==0 else'mul',f[rd],f[rt])
  else:raise AssertionError((at,hex(w)))
 return dict(stores=stores,return_value=g[2],record_pointer=g[4],global_value=global_value)

from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 body=selected[selected.index('/* Integrate'):];F='func_150CBE88'
 mutants=dict(wrong_half=body.replace('0.5f','1.0f'),cached_time=body.replace('    f32 acceleration', '    f32 cachedTime = D_800BE9A4;\n    f32 acceleration',1).replace(' * D_800BE9A4',' * cachedTime'),omit_velocity=body.replace('    *(f32 *)(record + 0x48) = verticalVelocity + delta;','    (void)delta;'),wrong_rate=body.replace('record + 0x50','record + 0x54'),wrong_acceleration=body.replace('record + 0x5C','record + 0x58'),wrong_return=body.replace('return 1;','return 0;'));assert all(x!=body for x in mutants.values())
 text='#include <ultra64.h>\nstatic f32 *nativeTime;\n#define D_800BE9A4 (*nativeTime)\n'+'\n'.join(src.replace(F,'test_'+name)for name,src in dict(selected=body,**mutants).items())
 cases=[]
 for time,pattern,alias in itertools.product((0,0x80000000,0x3F800000,0xBF800000,0x3EAAAAAB,0x42C80000,1,0x007FFFFF,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345),range(6),(-1,0x20,0x24,0x28,0x38,0x3C,0x40,0x48,0x5C)):
  c=Case(time,pattern,alias,0);m=fixture(c);want=reference(m,c);cases.append((time,alias,[read(m,c.record+i*4)for i in range(32)],[read(want,c.record+i*4)for i in range(32)]))
 assert len(cases)==648
 text+='\ntypedef struct {u32 time;s32 alias;u32 before[32],after[32];} Fixture;\nstatic const Fixture fixtures[]={\n'+',\n'.join('{0x%08Xu,%d,{%s},{%s}}'%(time,alias,','.join('0x%08Xu'%x for x in before),','.join('0x%08Xu'%x for x in after))for time,alias,before,after in cases)+'\n};\n'
 text+=r'''
 static f32 record[32],separateTime;
 static u32 asBits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
 static f32 asFloat(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
 static s32 nanBits(u32 x){return (x&0x7F800000u)==0x7F800000u && (x&0x7FFFFFu)!=0;}
 static s32 output(s32 i){return i==8||i==9||i==10||i==14||i==15||i==16||i==18;}
 typedef s32(*Fn)(u8*);
 static s32 check(Fn fn){s32 n,i,count=0;for(n=0;n<648;n++){
  const Fixture *c=fixtures+n;for(i=0;i<32;i++)record[i]=asFloat(c->before[i]);
  separateTime=asFloat(c->time);nativeTime=c->alias<0?&separateTime:record+c->alias/4;
  if(fn((u8*)record)!=1)return 1;
  for(i=0;i<32;i++){u32 a=asBits(record[i]),e=c->after[i];if(a!=e && !(output(i)&&nanBits(a)&&nanBits(e)))return 2;}
  if(c->alias<0 && asBits(separateTime)!=c->time)return 3;count++;
  }return count==648?0:4;}
 static int run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
 '''
 for i,n in enumerate(mutants):text+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
