from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-subtype-appearance-match';F='func_1518A214';ENTRY=0x1518A214;OBJECT,DESC,OUTPUT=0x30000,0x50000,0x70000
SYMS=dict(D_800A73C0=0x800A73C0,D_800A73C4=0x800A73C4,D_800A73C8=0x800A73C8)
@dataclass(frozen=True)
class Case:
 subtype:int=0
 alias:int=-1
 flags:int=0xFFFFFFFF
 pattern:int=0
 constant_alias:int=-1
 phase:int=0
 output:int=OUTPUT
def symbols(c,base=0x800A73C0):
 if c.constant_alias>=0:base=OBJECT+c.constant_alias
 return dict(zip(SYMS,(base,base+4,base+8)))
def fixture(c,s=None):
 s=symbols(c)if s is None else s;m={STACK+i:(i*17+0xA5)&255 for i in range(-256,512)}
 for base,n in((OBJECT-16,0x260),(DESC-16,0x100),(OUTPUT,4)):m.update({base+i:(i*29+0xA5)&255 for i in range(n)})
 put(m,OBJECT+0x188,DESC);m[DESC+0x68]=c.subtype;put(m,OBJECT+0x58,c.flags)
 patterns=((0x3F19999A,0x3E99999A,0x3F19999A),(0,0x80000000,0x7FC12345),(0x7F800001,0xFF800000,0xFFFFFFFF),(0x3F800000,0xBF800000,0x00000001))
 for address,value in zip(s.values(),patterns[c.pattern]):put(m,address,value)
 return m
def output(c):return c.output if c.alias<0 else OBJECT+c.alias
def reference(initial,c,s=None):
 s=symbols(c)if s is None else s;m=dict(initial);desc=read(m,OBJECT+0x188);subtype=m[desc+0x68];p=output(c)
 if subtype==15:put(m,OBJECT+0x58,read(m,OBJECT+0x58)&0xFFFFFFFD);m[p]=0
 else:
  name='D_800A73C4'if subtype==16 else'D_800A73C8'if subtype==17 else'D_800A73C0';value=read(m,s[name]);put(m,OBJECT+0x128,value);put(m,OBJECT+0x12C,value)
  if subtype in(16,17):m[OBJECT+0x28]=128 if subtype==16 else 255;m[OBJECT+0x29]=0;m[OBJECT+0x2A]=0
  else:m[OBJECT+0x2A]=0;m[OBJECT+0x29]=0;m[OBJECT+0x28]=255
  m[p]=1
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,s=None,connected=None):super().__init__(words,memory,c,entry=entry,s=symbols(c)if s is None else s,connected=connected,arguments=(OBJECT,output(c)))
 def record_call(self,t):
  assert t==ENTRY;args=tuple(self.arguments(2));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):raise AssertionError('No opaque providers allowed')
def linked(obj,label,entry=ENTRY,s=None):
 s=SYMS if s is None else s;text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

def run_suite(stage_output):
 global o
 o=stage_output
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected.o');triple=[linked(obj,'guest-'+str(i))for i,obj in enumerate(objects)];assert triple[0]==triple[1];count=0;visited=set()
 for subtype,alias,flags,pattern,phase in itertools.product(range(256),(-1,0x28,0x29,0x2A,0x58,0x5B,0x128,0x12B,0x12C,0x188),(0,2,0xFFFFFFFF),range(4),(0,8)):
  c=Case(subtype,alias,flags,pattern,-1,phase);initial=fixture(c);want=reference(initial,c);pair=[]
  for words in triple:
   m=Oracle(words,initial,c).run();assert(m.memory,m.r[2],m.calls)==(want,1,[]),(c,m.r[2]);pair.append(m)
  assert(pair[0].r,pair[0].f,pair[0].trace,pair[0].events)==(pair[1].r,pair[1].f,pair[1].trace,pair[1].events);visited.update(pair[0].visits);count+=1
 print('guest cases',count,flush=True)
 alias_cases=0
 for subtype,alias,pattern,constant_alias in itertools.product((0,15,16,17,255),(-1,0x28,0x128,0x188),range(4),(0x28,0x58,0x128)):
  c=Case(subtype,alias,0xFFFFFFFF,pattern,constant_alias,8);s=symbols(c);triple_alias=[linked(obj,'alias-%d-%d'%(constant_alias,j),s=s)for j,obj in enumerate(objects)]
  initial=fixture(c,s);want=reference(initial,c,s)
  for words in triple_alias:m=Oracle(words,initial,c,s=s).run();assert(m.memory,m.r[2],m.calls)==(want,1,[]),c
  alias_cases+=1
 prefixes=0
 for c in(Case(),Case(15,0x58),Case(16,0x128,phase=8),Case(17,0x188)):
  initial=fixture(c);full=Oracle(triple[0],initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in triple[:2]:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('No dispatched access cut')
    pair.append(m)
   assert(pair[0].r,pair[0].f,pair[0].memory,pair[0].trace,pair[0].events,pair[0].current_pc,pair[0].delay_of)==(pair[1].r,pair[1].f,pair[1].memory,pair[1].trace,pair[1].events,pair[1].current_pc,pair[1].delay_of);prefixes+=1
 c=Case(15);sparse=fixture(c)
 for v in SYMS.values():
  for i in range(4):del sparse[v+i]
 for words in triple:m=Oracle(words,sparse,c).run();assert m.memory==reference(sparse,c)and m.r[2]==1
 rebase_cases=0
 for k,(entry,base)in enumerate(((0x15001000,0x80007FF0),(0x1F008000,0x80008000),(0x1000FFF0,0x8000FFF0))):
  s=dict(zip(SYMS,(base,base+4,base+8)));rebased=[linked(obj,'rebase-%d-%d'%(k,j),entry,s)for j,obj in enumerate(objects)];assert rebased[0]==rebased[1]
  for subtype,alias,pattern in itertools.product((0,14,15,16,17,18,255),(-1,0x28,0x128,0x188),range(4)):
   c=Case(subtype,alias,0xFFFFFFFF,pattern,-1,8);initial=fixture(c,s);want=reference(initial,c,s)
   for words in rebased:m=Oracle(words,initial,c,entry,s).run();assert(m.memory,m.r[2],m.calls)==(want,1,[])
   rebase_cases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x232060)[0]==ENTRY;window=list(struct.unpack_from('>18I',rom,0x1B75A8));caller_cases=0
 for subtype,index,phase in itertools.product(range(256),(-1,0),(0,8)):
  c=Case(subtype,phase=phase,output=STACK+phase+0x4B);initial=fixture(c);initial[OBJECT+0x18E]=index&255;put(initial,0x8008D5A0,ENTRY);want=reference(initial,c)if index==0 else dict(initial)
  if index==0:put(want,STACK+phase+0x3C,OBJECT+0x170)
  for words in triple:
   code=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));code.update({0x1518A14C:0,0x1518A200:0});m=Oracle(window,initial,c,entry=0x1518A0F8,connected=code);m.r[16]=OBJECT;m.r[3]=OBJECT+0x170;m.r[2]=DESC;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(0x1518A14C,0x1518A200)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing actual caller boundary')
   calls=[(ENTRY,(OBJECT,output(c)))]if index==0 else[];assert(m.memory,m.calls)==(want,calls),(c,index,m.calls,calls)
   assert m.r[2]==(1 if index==0 and subtype==15 else DESC)
  caller_cases+=1
 receipt=dict(private_only=True,installed=False,matching_credit=0,guest_cases=count,guest_executions=count*3,covered_words=len(visited),unvisited=[hex(pc)for pc in range(ENTRY,ENTRY+212,4)if pc not in visited],constant_alias_cases=alias_cases,access_prefix_pairs=prefixes,sparse_inactive_constant_skip=True,rebase_layouts=3,rebase_cases=rebase_cases,caller_words=18,caller_cases=caller_cases,earlier_parent_gates_precondition=True,complete_parent_claimed=False,raw_public_state_equal=True,normalized_full_tested_state_equal=True,FCSR_hardware_claimed=False)

 return receipt

from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 body=selected[selected.index('/* Apply'):];F='func_1518A214'
 mutants=dict(wrong_subtype=body.replace('+ 0x68','+ 0x6A'),wrong_disable=body.replace('case 0:','case -1:'),wrong_mask=body.replace('&= ~2','&= ~4'),wrong_scale=body.replace('D_800A73C4','D_800A73C0'),wrong_color=body.replace('= 128;','= 127;'),wrong_field=body.replace('attributes[6]','attributes[5]'),omit_second=body.replace('        attributes[7] = scale;',''),wrong_return=body.replace('return 1;','return 0;'));assert all(v!=body for v in mutants.values())
 text='''#include <ultra64.h>
static f32 *nativeConstants[3];
#define D_800A73C0 (*nativeConstants[0])
#define D_800A73C4 (*nativeConstants[1])
#define D_800A73C8 (*nativeConstants[2])
'''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items())
 text+='''
static union {u32 align;u8 b[0x260];} owner,descriptor;
static union {f32 f[3];u32 u[3];} constants;
static u8 separate[4],expected[0x260],expectedSeparate[4];
static const u32 patterns[4][3]={{0x3F19999A,0x3E99999A,0x3F19999A},{0,0x80000000,0x7FC12345},{0x7F800001,0xFF800000,0xFFFFFFFF},{0x3F800000,0xBF800000,1}};
static const s32 aliases[10]={-1,0x28,0x29,0x2A,0x58,0x5B,0x128,0x12B,0x12C,0x188};
static const u32 flags[3]={0,2,0xFFFFFFFF};
static void setup(s32 subtype,s32 flag,s32 pattern,s32 alias){u32 i;u8 *base;
 for(i=0;i<sizeof(owner);i++){owner.b[i]=(u8)(i*29+0xA5);descriptor.b[i]=(u8)(i*13+0x5A);}
 for(i=0;i<4;i++)separate[i]=(u8)(i*17+0x37);
 *(u8**)(owner.b+0x188)=descriptor.b;descriptor.b[0x68]=subtype;*(u32*)(owner.b+0x58)=flags[flag];
 base=alias==0?(u8*)constants.u:owner.b+(alias==1?0x28:0x128);
 for(i=0;i<3;i++){nativeConstants[i]=(f32*)(base+4*i);*(u32*)(base+4*i)=patterns[pattern][i];}
}
static s32 reference(u8*object,u8*enabled){u32 subtype=(*(u8**)(object+0x188))[0x68];u32 word;
 if(subtype==15){*(u32*)(object+0x58)&=0xFFFFFFFDu;*enabled=0;}
 else {word=*(u32*)nativeConstants[subtype==16?1:subtype==17?2:0];*(u32*)(object+0x128)=word;*(u32*)(object+0x12C)=word;
 if(subtype==16||subtype==17){object[0x28]=subtype==16?128:255;object[0x29]=0;object[0x2A]=0;}else{object[0x2A]=0;object[0x29]=0;object[0x28]=255;}*enabled=1;}
 return 1;
}
typedef s32(*Fn)(u8*,u8*);
static s32 check(Fn fn){s32 t,a,f,p,c,n=0;u32 i;u8*out;
 for(t=0;t<256;t++)for(a=0;a<10;a++)for(f=0;f<3;f++)for(p=0;p<4;p++)for(c=0;c<3;c++){
 setup(t,f,p,c);out=aliases[a]<0?separate:owner.b+aliases[a];if(reference(owner.b,out)!=1)return 9;
 for(i=0;i<sizeof(owner);i++)expected[i]=owner.b[i];for(i=0;i<4;i++)expectedSeparate[i]=separate[i];
 setup(t,f,p,c);out=aliases[a]<0?separate:owner.b+aliases[a];if(fn(owner.b,out)!=1)return 1;
 for(i=0;i<sizeof(owner);i++)if(expected[i]!=owner.b[i])return 2;for(i=0;i<4;i++)if(expectedSeparate[i]!=separate[i])return 3;n++;
 }return n==92160?0:4;
}
static s32 run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
'''
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return text+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
