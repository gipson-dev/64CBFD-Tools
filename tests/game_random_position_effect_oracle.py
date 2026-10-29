"""Bounded literal effect-packet qualification; no production installation."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-random-position-effect-match';F='func_151C56A4';ENTRY=0x151C56A4;POSITION=0x30000;MARK=0x40000
SYMS=dict(func_150ADA20=0x150ADA20,func_151602C0=0x151602C0)
@dataclass(frozen=True)
class Case:
 random0:int=0
 random1:int=0xFFFFFFFF
 kind:int=255
 mode:int=0x80000001
 pattern:int=0
 mutation:int=0
 phase:int=0
 position:int=POSITION
VALUES=((0x80000000,0,0x3F800000),(bits(-1.99),bits(1.99),bits(-270.5)),(bits(2147483520.),bits(-2147483648.),bits(65535.5)),(1,0x80000001,bits(360.99)),(0x7FC12345,0x7F800000,0xFF800000))
def trunc(word):
 v=floating(word);return math.trunc(v)&0xFFFFFFFF if math.isfinite(v)and -(2**31)<=v<2**31 else 0x80000000
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,1024)}
 m.update({POSITION+i:(i*29+0x59)&255 for i in range(32)})
 for i,v in enumerate(VALUES[c.pattern]):put(m,c.position+4*i,v)
 put(m,MARK,0);return m
def mutate(m,c,index):
 if c.mutation:
  values=(bits(-12.75),bits(200.5),bits(3.75))if index==0 else(bits(900.5),bits(-33.75),bits(0.5))
  for i,v in enumerate(values):put(m,c.position+4*i,v)
def reference(m,c,s=SYMS):
 m=dict(m);mutate(m,c,0);coordinates=tuple(trunc(read(m,c.position+4*i))for i in range(3));mutate(m,c,1)
 header=(3,255,(c.random0%3+3)>>8,(c.random0%3+3)&255,0)
 args=((STACK+c.phase-8)&0xFFFFFFFF,(STACK+c.phase-20)&0xFFFFFFFF,(c.random1&1)+6,255,232,171,255,0,0,c.kind&255,c.mode&0xFFFFFFFF)
 put(m,MARK,0xB16B00B5);return m,[(s['func_150ADA20'],()),(s['func_150ADA20'],()),(s['func_151602C0'],args)],(header,coordinates)
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+1024}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.random_calls=0;self.packet_observations=[];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(c.position,c.kind,c.mode))
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:
   prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=w
   try:self.f[w>>6&31]=trunc(self.f[w>>11&31])
   finally:self.own_instruction=prior
  else:super().execute(w)
 def record_call(self,t):
  assert t in(*self.syms.values(),ENTRY),hex(t);n=0 if t==self.syms['func_150ADA20']else 11 if t==self.syms['func_151602C0']else 3;args=tuple(self.arguments(n));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if n==11:self.packet_observations.append((tuple(self.memory[args[0]+i]for i in range(5)),tuple(read(self.memory,args[1]+4*i)for i in range(3))))
 def hook(self,t):
  c=self.case;assert self.r[29]==STACK+c.phase-80
  assert read(self.memory,self.r[29]+52)==getattr(self,'expected_target_ra',self.before[31])
  if t==self.syms['func_150ADA20']:
   index=self.random_calls;assert index<2;mutate(self.memory,c,index);value=(c.random0,c.random1)[index];self.random_calls+=1
  else:assert t==self.syms['func_151602C0'];put(self.memory,MARK,0xB16B00B5);value=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
RANDOMS=(0,1,2,3,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
def cases():
 for a in itertools.product(RANDOMS,RANDOMS,(0,127,128,255),(0,0x80000001),range(5),range(2),(0,8)):yield Case(*a)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.packet_observations)
def verify(m,initial,c,s=SYMS):
 want,calls,packet=reference(initial,c,s);assert(public(m.memory),m.calls,m.packet_observations)==(public(want),calls,[packet]),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+216,4));print(dict(cases=count,covered_words=len(visited)),flush=True)
 prefixes=0
 for c in(Case(),Case(pattern=4,mutation=1,phase=8)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 rebased=0
 for k,(entry,random,submit)in enumerate(((0x15001000,0x10007FF0,0x10008000),(0x1F008000,0x1F108000,0x1000FFF0),(0x1000FFF0,0x10008000,0x10007FF0))):
  s=dict(func_150ADA20=random,func_151602C0=submit);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2]
  for a in itertools.product((0,0x80000000,0xFFFFFFFF),(0,1),(0,255),range(2),(0,8)):
   c=Case(random0=a[0],random1=a[1],kind=a[2],mutation=a[3],phase=a[4]);initial=fixture(c)
   for words in ps:verify(Oracle(words,initial,c,s,entry).run(),initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();caller_rows=[]
 for entry,offset,n,end in((0x151C5358,0x1F2808,4,0x151C5368),(0x150288CC,0x55D7C,6,0x15029BA4)):
  window=list(struct.unpack_from('>%dI'%n,rom,offset));total=0
  for a in itertools.product((0,0x80000000,0xFFFFFFFF),(0,1),(0,255),range(2),(0,8)):
   c=Case(random0=a[0],random1=a[1],kind=a[2],mutation=a[3],phase=a[4]);c=replace(c,position=STACK+c.phase+0xD4)if n==4 else replace(c,mode=1);initial=fixture(c);home=STACK+c.phase
   if n==4:initial[home+0xE7]=c.kind;put(initial,home+0xE8,c.mode)
   else:initial[home+0xE3]=c.kind
   want,calls,packet=reference(initial,c)
   for words in programs:
    connected=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));connected[end]=0;m=Oracle(window,initial,c,entry=entry,connected=connected);m.r[16]=c.position;m.before=m.r[:];m.expected_target_ra=0x151C5368 if n==4 else 0x150288DC;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller boundary')
    assert(public(m.memory),m.calls,m.packet_observations)==(public(want),[(ENTRY,(c.position,c.kind,c.mode))]+calls,[packet])
    if n==6:assert m.r[2]==1
   total+=1
  caller_rows.append(dict(entry=hex(entry),ROM=hex(offset),words=n,cases=total,result_register_ignored=True,complete_parent_claimed=False))
 q=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,covered_words=54,frame=80,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,packet_fields=5,uninitialized_header_padding_claimed=False,float_invalid_guest_model_only=True,native_invalid_float_conversion_claimed=False,providers_bounded=True,helper_mutations=True,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,original_caller_windows=caller_rows,hardware_or_complete_parent_claimed=False)
 return q


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_151C56A4';body=selected[selected.index('/* Submit'):]
 mutants=dict(signed_remainder=body.replace('(u32)func_150ADA20() % 3U','func_150ADA20() % 3'),wrong_count=body.replace('% 3U + 3','% 3U + 4'),wrong_header=body.replace('header.unk1 = -1','header.unk1 = -2'),wrong_axis=body.replace('coordinates.unk0 = position[0]','coordinates.unk0 = position[1]'),wrong_selector=body.replace('& 1) + 6','& 2) + 6'),wrong_colour=body.replace('0xE8, 0xAB','0xAB, 0xE8'),missing_draw=body.replace('((u32)func_150ADA20() & 1)','(0U & 1)'),early_coordinates=body.replace('    header.unk0 = 3;','    f32 captured[3];\n    captured[0] = position[0]; captured[1] = position[1]; captured[2] = position[2];\n    header.unk0 = 3;').replace('coordinates.unk0 = position[0]','coordinates.unk0 = captured[0]').replace('coordinates.unk4 = position[1]','coordinates.unk4 = captured[1]').replace('coordinates.unk8 = position[2]','coordinates.unk8 = captured[2]'))
 assert all(v!=body for v in mutants.values())
 text=r'''#include <ultra64.h>
 #include "structs.h"
 typedef struct {u32 r0,r1,kind,mode,mutation,x,y,z,outx,outy,outz,finalx,finaly,finalz,count;} Fixture;
 static const Fixture*current;static f32 positionData[3];static s32 draws,submits,badArgs;
 static f32 asFloat(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
 static u32 asBits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
 s32 func_150ADA20(void){s32 n=draws++;if(n>1){badArgs=1;return 0;}if(current->mutation){positionData[0]=n?900.5f:-12.75f;positionData[1]=n?-33.75f:200.5f;positionData[2]=n?0.5f:3.75f;}return (s32)(n?current->r1:current->r0);}
 struct225 *func_151602C0(Header*h,Header2*p,s32 a,s32 b,s32 c,s32 d,u8 e,u8 f,s32 g,u8 kind,s32 mode){submits++;
  if(h->unk0!=3||h->unk1!=-1||h->unk2!=(s16)current->count||h->unk4!=0)badArgs=1;
  if((u32)p->unk0!=current->outx||(u32)p->unk4!=current->outy||(u32)p->unk8!=current->outz)badArgs=1;
  if(a!=(s32)((current->r1&1)+6)||b!=255||c!=232||d!=171||e!=255||f!=0||g!=0||kind!=current->kind||(u32)mode!=current->mode)badArgs=1;
  return (struct225*)0xDEADBEEF;
 }
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());cases=[c for c in q.cases()if c.phase==0 and c.pattern<4];rows=[]
 for c in cases:
  initial=q.fixture(c);want,calls,packet=q.reference(initial,c);rows.append((c.random0,c.random1,c.kind,c.mode,c.mutation,*[q.read(initial,c.position+4*i)for i in range(3)],*packet[1],*[q.read(want,c.position+4*i)for i in range(3)],c.random0%3+3))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+','.join('0x%08Xu'%x for x in row)+'}'for row in rows)+'\n};\n'
 text+=r'''
 typedef void(*Fn)(f32*,u8,s32);
 static s32 check(Fn fn){s32 n;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;current=c;positionData[0]=asFloat(c->x);positionData[1]=asFloat(c->y);positionData[2]=asFloat(c->z);draws=submits=badArgs=0;fn(positionData,(u8)c->kind,(s32)c->mode);
  if(badArgs||draws!=2||submits!=1)return 1;
  if(asBits(positionData[0])!=c->finalx||asBits(positionData[1])!=c->finaly||asBits(positionData[2])!=c->finalz)return 2;
  }return 0;}
 static int run(void){if(sizeof(void*)!=4||sizeof(Header)!=6||sizeof(Header2)!=12)return 90;if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(cases)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
