"""Status actor selection: signed indices, float gate, live callbacks and mode stores."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import floating
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-status-actor-mode-update-match';F='func_151E7DC0';ENTRY=0x151E7DC0;BODY=220;RECORD=0x20000;ALT=0x21000;ACTORS=(0x30000,0x31000)
SYMS=dict(D_8008FDD4=0x8008FDD4,D_8008FFB0=0x8008FFB0,D_800ABA8C=0x800ABA8C,func_151149AC=0x151149AC)
short=lambda n:((n&255)^128)-128
@dataclass(frozen=True)
class Case:
 level:int=0x3F800000
 threshold:int=0x3F000000
 flag:int=0
 selector:int=3
 outcome:int=3
 mutation:int=0
 phase:int=0
 key0:int=37
 key1:int=222
 seed:int=0
 connected:int=0
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for j,base in enumerate((RECORD,ALT)):
  m.update({base+i:(i*13+j*17+c.seed+0x59)&255 for i in range(-256,256)});put(m,base+8,c.level if not j else 0x40000000);m[base+0x3E]=c.flag if not j else 0;m[base+0x2C]=c.selector if not j else 1
 for j,base in enumerate(ACTORS):m.update({base+i:(i*29+j*31+0x63)&255 for i in range(256)})
 m.update({s['D_8008FFB0']+i:(i*17+c.seed*13+0x57)&255 for i in range(-128,134)})
 for i in range(6):m[s['D_8008FFB0']+i]=(c.key0+i*29)&255;m[s['D_8008FFB0']+6+i]=(c.key1+i*29)&255
 put(m,s['D_8008FDD4'],RECORD);put(m,s['D_800ABA8C'],c.threshold)
 if c.connected:
  put(m,0x800DBEF0,6);put(m,0x800DBEF4,0x60000)
  for i,key in enumerate((1,2,3,1,255,128)):
   m.update({0x60000+i*160+j:(i*19+j*13+0x71)&255 for j in range(160)});m[0x60000+i*160+0x72]=key
 return m
def returned(c,n,s=SYMS,key=0):
 if c.connected:
  keys=(1,2,3,1,255,128)
  return 0x60000+keys.index(key)*160 if key in keys and key else 0
 if c.outcome<4:return ACTORS[n-1]if c.outcome>>(n-1)&1 else 0
 if c.outcome==4:return ACTORS[0]
 if n==2:return ACTORS[1]
 return {5:RECORD+0x2C-0x80,6:RECORD+0x3C-0x80,7:RECORD+8-0x80,8:s['D_8008FFB0']+4-0x80}[c.outcome]
def observation(m,s=SYMS):
 p=read(m,s['D_8008FDD4']);return(read(m,s['D_8008FDD4']),m[p+0x3E],m[p+0x2C],read(m,p+8),read(m,s['D_800ABA8C']),*(m[s['D_8008FFB0']+6+i]for i in range(6)))
def effect(m,c,n,s=SYMS):
 if n!=1:return
 mu=c.mutation
 if mu&1:put(m,s['D_8008FDD4'],ALT)
 p=read(m,s['D_8008FDD4'])
 if mu&2:m[p+0x3E]^=1
 if mu&4:m[p+0x2C]=2
 if mu&8:
  for i in range(6):m[s['D_8008FFB0']+6+i]^=0xA5
 if mu&16:put(m,p+8,0xBF800000);put(m,s['D_800ABA8C'],0x7F800000)
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];obs=[];indices=[];p=read(m,s['D_8008FDD4'])
 if floating(read(m,p+8))<floating(read(m,s['D_800ABA8C']))and m[p+0x3E]==0:return m,calls,obs,indices
 for i in range(2):
  p=read(m,s['D_8008FDD4']);selector=0 if m[p+0x3E]else short(m[p+0x2C]);at=6*i+selector;key=m[s['D_8008FFB0']+at];indices.append(at);calls.append((s['func_151149AC'],(key,)));obs.append(observation(m,s));effect(m,c,i+1,s);out=returned(c,i+1,s,key)
  if out:put(m,out+0x80,2)
 return m,calls,obs,indices
def native_safe(c):return not c.connected and c.selector<6 and c.outcome not in(5,6,8)
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.observations=[];self.n=0;super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=());self.before=self.r[:]
 def record_call(self,t):
  assert t in(self.syms['func_151149AC'],ENTRY);args=tuple(self.arguments(1 if t!=ENTRY else 0));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t!=ENTRY:self.observations.append(observation(self.memory,self.syms))
 def hook(self,t):
  assert t==self.syms['func_151149AC'];self.n+=1;assert self.r[29]==STACK+self.case.phase-48
  for reg,slot in((16,24),(17,28),(18,32),(19,36),(20,40),(31,44)):assert read(self.memory,self.r[29]+slot)==(getattr(self,'expected_target_ra',self.before[31])if reg==31 else self.before[reg])
  key=self.calls[-1][1][0];effect(self.memory,self.case,self.n,self.syms);value=returned(self.case,self.n,self.syms,key)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def cases():
 for level,flag,selector,outcome,mu,phase in itertools.product((0,0x3F800000,0x7FC12345),(0,1,128),(0,5,255),range(4),(0,1,2,4,8,16,31),(0,8)):yield Case(level=level,flag=flag,selector=selector,outcome=outcome,mutation=mu,phase=phase)
 floats=(0,0x80000000,0x3E800000,0x3F000000,0x3F800000,0x7F800000,0xFF800000,0x7FC12345)
 for level,threshold,flag,phase in itertools.product(floats,floats,(0,1),(0,8)):yield Case(level,threshold,flag,phase=phase)
 for byte,phase in itertools.product(range(256),(0,8)):yield Case(flag=byte,phase=phase);yield Case(selector=byte,phase=phase);yield Case(key0=byte,phase=phase);yield Case(key1=byte,phase=phase)
 for mu,outcome,phase in itertools.product(range(32),(0,1,2,3),(0,8)):yield Case(mutation=mu,outcome=outcome,phase=phase)
 for outcome,flag,mu,phase in itertools.product((4,5,6,7,8),(0,1),(0,1,2,31),(0,8)):yield Case(outcome=outcome,flag=flag,mutation=mu,phase=phase)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.observations)
def verify(m,initial,c,s=SYMS):
 want,calls,obs,_=reference(initial,c,s);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];visited=set();count=0;aliascases=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1;aliascases+=c.outcome>=5
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(level=0),Case(),Case(mutation=31),Case(flag=128,selector=255),Case(outcome=6,flag=1)):
  initial=fixture(c);full=Oracle(programs[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 c=Case(level=0);keep=set(range(SYMS['D_8008FDD4'],SYMS['D_8008FDD4']+4))|set(range(SYMS['D_800ABA8C'],SYMS['D_800ABA8C']+4))|set(range(RECORD+8,RECORD+12))|{RECORD+0x3E};initial={a:b for a,b in fixture(c).items()if STACK-256<=a<STACK+256 or a in keep};sparse=0
 for words in programs:m=Oracle(words,initial,c);m.run();assert m.calls==[]and public(m.memory)==public(initial);sparse+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(D_8008FDD4=0x80007FF0+k*0x100000,D_8008FFB0=0x80018000+k*0x100000,D_800ABA8C=0x8002FFF0+k*0x100000,func_151149AC=0x10008000+k*0x10000);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)]
  for level,flag,mu,phase in itertools.product((0,0x3F800000),(0,1),(0,1,2,31),(0,8)):
   c=Case(level=level,flag=flag,mutation=mu,phase=phase);initial=fixture(c,s)
   for words in ps:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();helper=dict(zip(range(0x151149AC,0x15114A1C,4),struct.unpack_from('>28I',rom,0x141E5C)));connected_count=0
 for key0,key1,flag,phase in itertools.product((0,1,7,255),(0,2,128),(0,1),(0,8)):
  c=Case(key0=key0,key1=key1,flag=flag,selector=0,phase=phase,connected=1);initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c,connected=helper);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);connected_count+=1
 caller_count=0;window=list(struct.unpack_from('>2I',rom,0x20BDD4));assert window==[0x0D479F70,0]
 for level,flag,mu,outcome,phase in itertools.product((0,0x3F800000),(0,1),(0,1,31),(0,3),(0,8)):
  c=Case(level=level,flag=flag,mutation=mu,outcome=outcome,phase=phase);initial=fixture(c);want,calls,obs,_=reference(initial,c)
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),words));code[0x151DE92C]=0;m=Oracle(window,initial,c,entry=0x151DE924,connected=code);m.expected_target_ra=0x151DE92C;m.code=WindowCode(m.code,m);m.code.ends=(0x151DE92C,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(public(m.memory),m.calls,m.observations)==(public(want),[(ENTRY,())]+calls,obs)
  caller_count+=1
 report=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,compiler_words=55,covered_words=55,slot_words=55,alignment_words=0,frame=48,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,live_record_and_table_after_helper=True,signed_selector=True,guest_mode_store_alias_cases=aliascases,access_prefix_pairs=prefixes,sparse_executions=sparse,rebase_layouts=3,rebase_cases=rebased,original_lookup_helper_words=28,connected_lookup_cases=connected_count,original_caller_windows=[dict(entry='0x151DE924',ROM='0x20BDD4',words=2,cases=caller_count,result_ignored=True,complete_parent_claimed=False)],native_domain='selector0..5 and no cross-endian byte/word mode-store aliases',hardware_FCSR_or_complete_parent_claimed=False)
 return report


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_151E7DC0';body=selected[selected.index('/* Mark'):]
 gate='*(f32 *)(D_8008FDD4 + 8) < D_800ABA8C && D_8008FDD4[0x3E] == 0'
 mutants=dict(inclusive_float_gate=body.replace('< D_800ABA8C','<= D_800ABA8C'),inverted_flag_gate=body.replace('&& D_8008FDD4[0x3E] == 0','&& D_8008FDD4[0x3E] != 0'),wrong_row=body.replace('D_8008FFB0[index]','D_8008FFB0[0]'),wrong_mode=body.replace('*(s32 *)(actor + 0x80) = 2','*(s32 *)(actor + 0x80) = 1'),wrong_mode_offset=body.replace('actor + 0x80','actor + 0x84'),cached_record=body.replace('D_8008FDD4','cachedRecord').replace('    s32 index;','    s8 *cachedRecord = D_8008FDD4;\n    s32 index;'),cached_selector=body.replace('D_8008FDD4[0x2C]','cachedSelector').replace('    s32 index;','    s8 cachedSelector = D_8008FDD4[0x2C];\n    s32 index;'),repeated_gate=body.replace('for (index = 0; index < 2; index++) {','for (index = 0; index < 2; index++) {\n        if (index && ('+gate+')) return;'));assert all(v!=body for v in mutants.values())
 text=r'''#include <ultra64.h>
static u8 records[2][512] __attribute__((aligned(8))),actors[2][256] __attribute__((aligned(8))),tableStorage[262] __attribute__((aligned(8)));
static u8 beforeRecords[2][512] __attribute__((aligned(8))),beforeActors[2][256] __attribute__((aligned(8))),beforeTable[262];
s8 *D_8008FDD4;f32 D_800ABA8C;
#define D_8008FFB0 ((u8 (*)[6])(tableStorage+128))
static u8* rec(u32 n){return records[n]+256;}
static u32 floatBits(f32 f){union{f32 f;u32 u;}x;x.f=f;return x.u;}static f32 asFloat(u32 u){union{f32 f;u32 u;}x;x.u=u;return x.f;}
static void p32(u8*p,u32 v){*(u32*)p=v;}static u32 r32(u8*p){return *(u32*)p;}
typedef struct{u32 key,obs[11];}Call;
typedef struct{u32 level,threshold,flag,selector,outcome,mutation,key0,key1,seed,count,root,finalThreshold,levels[2],flags[2],selectors[2],actorTouched[2];u8 table[12];Call calls[2];}Fixture;
static const Fixture*current;static u32 count,bad;
static u32 canonical(void*p){return p==rec(0)?0x20000u:p==rec(1)?0x21000u:0xDEADBEEFu;}
static u8* answer(u32 n){u32 o=current->outcome;if(o<4)return o>>(n-1)&1?actors[n-1]:0;if(o==4)return actors[0];return n==1?rec(0)+8-128:actors[1];}
u8 *func_151149AC(u8 key){const Call*c;u8*p=(u8*)D_8008FDD4;u32 i,obs[11];if(count>=current->count){bad=1;return 0;}c=current->calls+count++;obs[0]=canonical(p);obs[1]=p[0x3E];obs[2]=p[0x2C];obs[3]=r32(p+8);obs[4]=floatBits(D_800ABA8C);for(i=0;i<6;i++)obs[5+i]=D_8008FFB0[1][i];if(key!=c->key)bad=2;for(i=0;i<11;i++)if(obs[i]!=c->obs[i])bad=3;
 if(count==1){u32 mu=current->mutation;if(mu&1)D_8008FDD4=(s8*)rec(1);p=(u8*)D_8008FDD4;if(mu&2)p[0x3E]^=1;if(mu&4)p[0x2C]=2;if(mu&8)for(i=0;i<6;i++)D_8008FFB0[1][i]^=0xA5;if(mu&16){p32(p+8,0xBF800000);D_800ABA8C=asFloat(0x7F800000);}}
 return answer(count);}
'''
 text+='\n'.join(src.replace(F,'test_'+name)for name,src in dict(selected=body,**mutants).items());rows=[]
 def arr(v):return '{'+','.join('0x%Xu'%(x&0xFFFFFFFF)for x in v)+'}'
 for c in q.cases():
  if c.phase or not q.native_safe(c):continue
  initial=q.fixture(c);want,calls,obs,_=q.reference(initial,c);touched=[0,0]
  for n,(_,args)in enumerate(calls,1):
   out=q.returned(c,n,key=args[0])
   if out in q.ACTORS:touched[q.ACTORS.index(out)]=1
  scalar=[c.level,c.threshold,c.flag,c.selector,c.outcome,c.mutation,c.key0,c.key1,c.seed,len(calls),q.read(want,q.SYMS['D_8008FDD4']),q.read(want,q.SYMS['D_800ABA8C'])];levels=[q.read(want,p+8)for p in(q.RECORD,q.ALT)];flags=[want[p+0x3E]for p in(q.RECORD,q.ALT)];selectors=[want[p+0x2C]for p in(q.RECORD,q.ALT)];table=[want[q.SYMS['D_8008FFB0']+i]for i in range(12)];cr=['{0x%Xu,%s}'%(args[0],arr(ob))for(_,args),ob in zip(calls,obs)]
  rows.append('{'+','.join('0x%Xu'%(x&0xFFFFFFFF)for x in scalar)+','+arr(levels)+','+arr(flags)+','+arr(selectors)+','+arr(touched)+','+arr(table)+',{'+','.join(cr)+'}}')
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef void(*Fn)(void);
static s32 check(Fn fn){u32 n,i,j;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;current=c;count=bad=0;for(j=0;j<2;j++){for(i=0;i<512;i++)records[j][i]=(u8)(((s32)i-256)*13+j*17+c->seed+0x59);p32(rec(j)+8,j?0x40000000:c->level);rec(j)[0x3E]=(u8)(j?0:c->flag);rec(j)[0x2C]=(u8)(j?1:c->selector);for(i=0;i<256;i++)actors[j][i]=(u8)(i*29+j*31+0x63);}for(i=0;i<262;i++)tableStorage[i]=(u8)(((s32)i-128)*17+c->seed*13+0x57);for(i=0;i<6;i++){D_8008FFB0[0][i]=(u8)(c->key0+i*29);D_8008FFB0[1][i]=(u8)(c->key1+i*29);}D_8008FDD4=(s8*)rec(0);D_800ABA8C=asFloat(c->threshold);
 for(j=0;j<2;j++){for(i=0;i<512;i++)beforeRecords[j][i]=records[j][i];for(i=0;i<256;i++)beforeActors[j][i]=actors[j][i];}for(i=0;i<262;i++)beforeTable[i]=tableStorage[i];fn();if(bad||count!=c->count||canonical(D_8008FDD4)!=c->root||floatBits(D_800ABA8C)!=c->finalThreshold)return 1;
 for(j=0;j<2;j++){p32(beforeRecords[j]+256+8,c->levels[j]);beforeRecords[j][256+0x3E]=(u8)c->flags[j];beforeRecords[j][256+0x2C]=(u8)c->selectors[j];if(c->actorTouched[j])p32(beforeActors[j]+128,2);for(i=0;i<512;i++)if(records[j][i]!=beforeRecords[j][i])return 2;for(i=0;i<256;i++)if(actors[j][i]!=beforeActors[j][i])return 3;}for(i=0;i<12;i++)beforeTable[128+i]=c->table[i];for(i=0;i<262;i++)if(tableStorage[i]!=beforeTable[i])return 4;
 }return 0;}
static int run(void){if(sizeof(void*)!=4)return 90;{s32 result=check(test_selected);if(result)return 10+result;}
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');return text,dict(cases=len(rows),negative_controls=len(mutants),selector_domain='0..5',cross_endian_word_byte_aliases_claimed=False)
