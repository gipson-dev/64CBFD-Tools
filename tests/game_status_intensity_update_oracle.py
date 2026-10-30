"""Status-byte decay and bounded signed float conversion; no hardware FCSR claim."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_actor_input_movement_oracle import trunc
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-status-intensity-update-match';F='func_151E530C';ENTRY=0x151E530C;ACTOR=0x30000
SYMS=dict(D_800E0B94=0x800E0B94,D_800E0B96=0x800E0B96,D_800BE9E4=0x800BE9E4,D_8008FD74=0x8008FD74,D_8008FDD4=0x8008FDD4)
@dataclass(frozen=True)
class Case:
 mode:int=0
 intensity:int=255
 ticks:int=1
 rate:int=8
 present:int=1
 flag:int=0
 active:int=0x3F800000
 level:int=0x3F800000
 phase:int=0
 alias:int=0
def symbols(c,s=SYMS):
 s=dict(s)
 if c.alias:s['D_800E0B96']=ACTOR+(0x2B if c.alias==1 else 0xB)
 return s
def fixture(c,s=SYMS):
 s=symbols(c,s);m={STACK+i:(i*17+0xA5)&255 for i in range(-128,128)};m.update({ACTOR+i:(i*29+0x59)&255 for i in range(64)});put(m,ACTOR+8,c.level);put(m,ACTOR+12,c.active);m[ACTOR+43]=c.flag
 for n,v in(('D_800E0B94',c.mode),('D_800E0B96',c.intensity),('D_8008FD74',c.rate)):m[s[n]]=v
 put(m,s['D_800BE9E4'],c.ticks);put(m,s['D_8008FDD4'],ACTOR if c.present else 0);return m
def reference(initial,c,s=SYMS):
 s=symbols(c,s);m=dict(initial);conversion=None
 if m[s['D_800E0B94']]!=2:
  if m[s['D_800E0B96']]:value=signed((m[s['D_800E0B96']]-read(m,s['D_800BE9E4'])*m[s['D_8008FD74']])&0xFFFFFFFF);m[s['D_800E0B96']]=max(value,0)&255
  actor=read(m,s['D_8008FDD4'])
  if actor and m[actor+43]==0 and floating(read(m,actor+12))>0 and floating(read(m,actor+8))>0.5:
   scaled=bits(floating(bits(floating(read(m,actor+8))-0.5))*524.0);conversion=scaled;value=signed(trunc(floating(scaled)));m[s['D_800E0B96']]=(255 if value>=256 else value)&255
 return m,conversion
def native_defined(c):
 if c.alias:return False
 _,word=reference(fixture(c),c)
 return word is None or math.isfinite(floating(word))and -(2**31)<=floating(word)<2**31
def public(m):return{a:b for a,b in m.items()if not STACK-128<=a<STACK+128}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.conversions=[];super().__init__(words,memory,c,entry=entry,s=symbols(c,s),connected=connected,arguments=(0x12345678,))
 def execute(self,word):
  if word>>26==17 and word>>21&31==16 and word&63==13:
   fs=word>>11&31;fd=word>>6&31;value=trunc(floating(self.f[fs]));self.f[fd]=value;self.conversions.append((self.current_pc,self.f[fs],value))
  else:super().execute(word)
 def record_call(self,t):
  assert t==ENTRY,hex(t);self.calls.append((t,()));self.events.append(('CALL',t,()))
 def hook(self,t):raise AssertionError(('Unexpected helper',t))
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:220]))
def cases():
 for args in itertools.product((0,2,255),(0,1,255),(0,1,0x7FFFFFFF,0xFFFFFFFF),(0,8,255),(0,1),(0,255),(0,0x3F800000,0x7FC12345),(0x3F000000,0x3F000001,0x3F800000,0x7F800000,0x7FC12345)):
  yield Case(*args)
 for field in('mode','intensity','rate','flag'):
  for byte,phase in itertools.product(range(256),(0,8)):yield replace(Case(),**{field:byte,'phase':phase})
 boundary=bits((2**31)/524.0+0.5);level_values=(0,0x80000000,1,0x80000001,0x3EFFFFFF,0x3F000000,0x3F000001,bits(0.986),bits(0.987),bits(1),boundary-1,boundary,boundary+1,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
 for level,active,phase in itertools.product(level_values,(0,0x80000000,1,0x80000001,0x3F800000,0xBF800000,0x7F800000,0xFF800000,0x7FC12345),(0,8)):yield Case(level=level,active=active,phase=phase)
 for ticks,intensity,rate,phase in itertools.product((0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,255),(0,1,8,127,255),(0,8)):yield Case(ticks=ticks,intensity=intensity,rate=rate,present=0,phase=phase)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.condition,m.conversions)
def verify(m,initial,c,s=SYMS):
 want,conversion=reference(initial,c,s);assert public(m.memory)==public(want),c;assert[entry[1]for entry in m.conversions]==([]if conversion is None else[conversion]),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];case_count=0;visited=set();invalid=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);assert m.calls==[];machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);case_count+=1;invalid+=not native_defined(c)
 assert visited==set(range(ENTRY,ENTRY+220,4));prefixes=0
 for c in(Case(mode=2),Case(present=0),Case(intensity=1,present=0),Case(),Case(active=0),Case(level=0x3F000000),Case(level=0x7F800000)):
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
 sparse=0
 for c in(Case(mode=2),Case(intensity=0,present=0),Case(intensity=0,active=0)):
  needed={SYMS['D_800E0B94']}
  if c.mode!=2:
   needed.add(SYMS['D_800E0B96']);needed.update(SYMS['D_8008FDD4']+i for i in range(4))
   if c.present:needed.add(ACTOR+43);needed.update(ACTOR+12+i for i in range(4))
  initial={a:b for a,b in fixture(c).items()if a in needed}
  for words in programs:m=Oracle(words,initial,c).run();assert m.calls==[];sparse+=1
 rebased=0;alias_cases=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s={n:0x80007FF0+k*0x100000+i*0x10010 for i,n in enumerate(SYMS)};ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)]
  for mode,intensity,level,active in itertools.product((0,2),(0,255),(0x3F000001,0x3F800000,0x7F800000),(0,0x3F800000)):
   c=Case(mode=mode,intensity=intensity,level=level,active=active);initial=fixture(c,s)
   for words in ps:verify(Oracle(words,initial,c,s,entry).run(),initial,c,s)
   rebased+=1
 for alias,intensity,rate,level in itertools.product((1,2),(0,1,255),(0,8),(0x3F000000,0x3F800000)):
  c=Case(alias=alias,intensity=intensity,rate=rate,level=level);s=symbols(c);ps=[linked(p,'alias%d-%d'%(alias,i),ENTRY,s)for i,p in enumerate(objects)];initial=fixture(c)
  for words in ps:verify(Oracle(words,initial,c).run(),initial,c)
  alias_cases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();callers=((0x151DE6DC,0x20BB8C),(0x151DEA68,0x20BF18),(0x151E2294,0x20F744),(0x151E4288,0x211738),(0x151E450C,0x2119BC),(0x151E4E6C,0x21231C),(0x151E82C0,0x215770),(0x151E8420,0x2158D0));caller_rows=[]
 for entry,offset in callers:
  window=list(struct.unpack_from('>2I',rom,offset));assert window[0]==0x0D4794C3;count=0
  for mode,intensity,present,active in itertools.product((0,2),(0,255),(0,1),(0,0x3F800000)):
   c=Case(mode=mode,intensity=intensity,present=present,active=active);initial=fixture(c);window_memory=dict(initial)
   if window[1]:window_memory[0x8008FD80]=9
   want,_=reference(window_memory,c)
   if window[1]:want[0x8008FD80]=3
   for words in programs:
    code=dict(zip(range(ENTRY,ENTRY+220,4),words));code[entry+8]=0;m=Oracle(window,window_memory,c,entry=entry,connected=code)
    if window[1]:m.r[1]=0x80090000;m.r[14]=3;m.before=m.r[:]
    m.code=WindowCode(m.code,m);m.code.ends=(entry+8,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller boundary')
    assert public(m.memory)==public(want)and m.calls==[(ENTRY,())]and m.r[29]==STACK
   count+=1
  caller_rows.append(dict(entry=hex(entry),ROM=hex(offset),words=2,cases=count,result_ignored=True,delay_slot_store=bool(window[1]),complete_parent_claimed=False))
 report=dict(private_only=True,installed=False,matching_credit=0,cases=case_count,executions=case_count*3,covered_words=55,frame=0,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,all_256_mode_intensity_rate_and_flag_bytes=True,integer_wrapping_and_signed_clamp=True,float_thresholds_and_quiet_NaNs=True,float_invalid_guest_model_only=True,native_invalid_float_conversion_claimed=False,invalid_guest_cases=invalid,access_prefix_pairs=prefixes,sparse_executions=sparse,rebase_layouts=3,rebase_cases=rebased,guest_alias_cases=alias_cases,original_caller_windows=caller_rows,hardware_FCSR_or_complete_parent_claimed=False)
 return report


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_151E530C';prefix=selected[:selected.index('/* Decay')];body=selected[selected.index('/* Decay'):]
 mutants=dict(inverted_phase=body.replace('D_800E0B94 != 2','D_800E0B94 == 2'),wrong_lower_clamp=body.replace('intensity < 0','intensity > 0'),wrong_decay=body.replace('* D_8008FD74','+ D_8008FD74'),wrong_record_gate=body.replace('record[0x2B] == 0','record[0x2B] != 0'),wrong_active_boundary=body.replace('(record + 0xC) > 0.0f','(record + 0xC) >= 0.0f'),wrong_level_boundary=body.replace('(record + 8) > 0.5f','(record + 8) >= 0.5f'),wrong_upper_clamp=body.replace('intensity = 255;','intensity = 254;'),wrong_scale=body.replace('524.0f','512.0f'));assert all(v!=body for v in mutants.values())
 text=prefix+r'''
 typedef struct{u32 mode,intensity,ticks,rate,present,flag,active,level,want,safeControl;} Fixture;
 u8 D_800E0B94,D_800E0B96,D_8008FD74;s32 D_800BE9E4;s8*D_8008FDD4;static u8 actor[64] __attribute__((aligned(8))),beforeActor[64];
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());cases=[c for c in q.cases()if c.phase==0 and q.native_defined(c)];rows=[]
 for c in cases:
  want,_=q.reference(q.fixture(c),c);scaled=q.bits(q.floating(q.bits(q.floating(c.level)-0.5))*524.0);f=q.floating(scaled);safe=int(math.isfinite(q.floating(c.level))and math.isfinite(f)and -(2**31)<=f<2**31)
  rows.append((c.mode,c.intensity,c.ticks,c.rate,c.present,c.flag,c.active,c.level,want[q.SYMS['D_800E0B96']],safe))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+','.join('0x%08Xu'%x for x in row)+'}'for row in rows)+'\n};\n'
 text+=r'''
 typedef void(*Fn)(void);
 static s32 check(Fn fn,s32 control){u32 n,i;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;if(control&&!c->safeControl)continue;D_800E0B94=(u8)c->mode;D_800E0B96=(u8)c->intensity;D_800BE9E4=(s32)c->ticks;D_8008FD74=(u8)c->rate;D_8008FDD4=c->present?(s8*)actor:NULL;for(i=0;i<64;i++)actor[i]=(u8)(i*29+0x59);*(u32*)(actor+8)=c->level;*(u32*)(actor+12)=c->active;actor[43]=(u8)c->flag;for(i=0;i<64;i++)beforeActor[i]=actor[i];fn();
  if(D_800E0B96!=c->want||D_800E0B94!=c->mode||(u32)D_800BE9E4!=c->ticks||D_8008FD74!=c->rate||D_8008FDD4!=(c->present?(s8*)actor:NULL))return 1;for(i=0;i<64;i++)if(actor[i]!=beforeActor[i])return 2;
  }return 0;}
 static int run(void){if(sizeof(void*)!=4)return 90;{s32 result=check(test_selected,0);if(result)return 10+result;}
 '''.replace('CASE_COUNT',str(len(cases)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+',1))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
