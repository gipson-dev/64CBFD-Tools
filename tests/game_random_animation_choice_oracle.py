"""Unsigned random choice, packed byte tables, helper mutations and bounded traps."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from functools import lru_cache
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.experiments import game_random_animation_choice_match as source
r=o=None
ENTRY,RANDOM,TRIGGER=0x1506B634,0x150ADA20,0x1506E8D8
ACTORS=(0x90000,0xA0000,0xD0000)
STATES=(0xB0000,0xB1000,0xB2000)
FLOATS=(0,0x80000000,0x3FA00000,0xC2000000,0x00800000,1)
@dataclass(frozen=True)
class Case:
 bound:int=8
 first:int=7
 second:int=2
 mode:int=1
 category:int=41
 pattern:int=0
 mutation:int=0
 fp:int=0
 home:int=-1
 alias:int=0
 phase:int=0

def symbols(index=0):
 if not index:return dict(D_800D154C=0x800D154C,D_800D1580=0x800D1580,D_800BE9F0=0x800BE9F0,D_80099AB4=0x80099AB4,D_80099ABC=0x80099ABC,D_80099C38=0x80099C38,func_150ADA20=RANDOM,func_1506E8D8=TRIGGER)
 b=(0x02337FFC,0x0343FFFC)[index-1]
 return dict(D_800D154C=b,D_800D1580=b+0x8004,D_800BE9F0=b+0x10004,D_80099AB4=b+0x18004,D_80099ABC=b+0x1800C,D_80099C38=b+0x20004,func_150ADA20=RANDOM,func_1506E8D8=TRIGGER)

@lru_cache(maxsize=1)
def retail():
 elf=(o/'before-conker_build_conker.us.elf').read_bytes()
 at=source.elf_slot_offset(elf,0x80099AB4,520);table=elf[at:at+520]
 at=source.elf_slot_offset(elf,0x80099C38,4);factor=int.from_bytes(elf[at:at+4],'big')
 return table,factor

def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,256)}
 for a in ACTORS:m.update({a+i:0xA5 for i in range(0x500)})
 states=list(STATES)
 if c.alias:states[0]=s['D_800D154C']-12
 for a in states:m.update({a+i:0xA5 for i in range(0x1C0)})
 for i,(a,t)in enumerate(zip(ACTORS,states)):
  put(m,a+0x31C,t);put(m,a+0x3C,FLOATS[(c.fp+i)%6]);m[t+0x16]=(c.mode+i)&255;put(m,t+0xE,0x5A5A,2)
 if c.alias:
  put(m,ACTORS[0]+0x40+0x31C,STATES[1]);put(m,ACTORS[0]+0x40+0x3C,0x3F400000);put(m,STATES[1]+0xE,0xA7,2)
 table,factor=retail()
 for i in range(520):
  value=table[i]if c.pattern==0 else 0xA7 if c.pattern==1 else (i*13+29)&255 if c.pattern==2 else (0xA7 if i in(0,8)else 0x44)if c.pattern==3 else 0x40
  m[s['D_80099AB4']+i]=value
 put(m,s['D_800D154C'],ACTORS[0]);put(m,s['D_800D1580'],0x12345678);put(m,s['D_800BE9F0'],c.category&0xFFFFFFFF);put(m,s['D_80099C38'],factor)
 return m

def observe(m,s):
 a=read(m,s['D_800D154C']);state=read(m,a+0x31C)
 return(read(m,s['D_800D1580']),ACTORS.index(a)if a in ACTORS else 3,read(m,state+0xE,2),m[state+0xC],read(m,s['D_800BE9F0']),read(m,s['D_80099C38']),read(m,a+0x3C))

def service(m,c,s,target,ordinal):
 if target==s['func_150ADA20']:
  if ordinal==1 and c.mutation&1:
   put(m,s['D_800D154C'],ACTORS[1]);put(m,s['D_800BE9F0'],41);m[STATES[1]+0x16]^=1
   for i in range(520):m[s['D_80099AB4']+i]=0xA7
  if ordinal==2 and c.mutation&2:put(m,s['D_800D154C'],ACTORS[2]);put(m,s['D_80099C38'],0x3F000000)
  return(c.first if ordinal==1 else c.second)&0xFFFFFFFF
 if c.mutation&4:put(m,s['D_800D154C'],ACTORS[0]);put(m,ACTORS[0]+0x3C,0xC0200000);put(m,s['D_80099C38'],0x40000000)
 return 0xDEADBEEF

def reference(initial,c,s):
 m=dict(initial);calls=[];observations=[];rng_count=0
 def call(t):
  nonlocal rng_count
  calls.append((t,()));observations.append((int(t==s['func_1506E8D8']),*observe(m,s)))
  if t==s['func_150ADA20']:rng_count+=1
  return service(m,c,s,t,rng_count)
 first=call(s['func_150ADA20']);bound=(c.bound if c.home<0 else c.home)&255
 if not bound:return m,calls,observations,True
 remainder=first%bound;choice=remainder&255;a=read(m,s['D_800D154C']);state=read(m,a+0x31C)
 if m[state+0x16]:
  if read(m,s['D_800BE9F0'])==41 and choice==7:choice=0
  value=m[s['D_80099ABC']+choice]
 else:value=m[s['D_80099AB4']+(remainder&255)]
 put(m,state+0xE,value,2);a=read(m,s['D_800D154C']);state=read(m,a+0x31C)
 if read(m,state+0xE,2)==0xA7:
  put(m,s['D_800D1580'],0xFF020144);second=call(s['func_150ADA20']);a=read(m,s['D_800D154C']);state=read(m,a+0x31C);m[state+0xC]=second%3+2
  call(s['func_1506E8D8']);a=read(m,s['D_800D154C']);put(m,a+0x3C,bits(floating(read(m,a+0x3C))*floating(read(m,s['D_80099C38']))))
 return m,calls,observations,False

class TrapBoundary(Exception):pass
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None,zero_pattern=0):
  self.c,self.s,self.rng_count,self.observations,self.zero_pattern=c,s,0,[],zero_pattern
  super().__init__(words,memory,c,entry=entry,s={},arguments=(c.bound&0xFFFFFFFF,),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  if w==0x0007000D:raise TrapBoundary
  if w>>26==0 and w&63==27 and self.r[w>>16&31]==0:
   # Trap-prefix comparison uses explicit opaque DIVU-zero result patterns.
   self.hi=(0,self.r[w>>21&31],0xFFFFFFFF)[self.zero_pattern];self.lo=0xFFFFFFFF;return
  return super().execute(w)
 def record_call(self,t):
  assert t in(ENTRY,self.s['func_150ADA20'],self.s['func_1506E8D8']),hex(t);self.calls.append((t,()))
  if t!=ENTRY:self.observations.append((int(t==self.s['func_1506E8D8']),*observe(self.memory,self.s)))
  if t==self.s['func_150ADA20']:self.rng_count+=1
 def hook(self,t):
  assert t in(self.s['func_150ADA20'],self.s['func_1506E8D8']);answer=service(self.memory,self.c,self.s,t,self.rng_count)
  if t==self.s['func_150ADA20']and self.rng_count==1 and self.c.home>=0:self.memory[STACK+self.c.phase+3]=self.c.home&255
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=answer;self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def corpus():
 for bound,first,mode,category,pattern in itertools.product((1,2,8,255),(0,1,7,8,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678),(0,1,128),(0,41,0x10029,0xFFFFFFFF),range(4)):
  yield Case(bound,first,(first*7+1)&0xFFFFFFFF,mode,category,pattern,(first^category^pattern)&7,(first+pattern)%6,phase=8 if mode==128 else 0)
 for bound in range(1,256):yield Case(bound,(bound*1664525+1013904223)&0xFFFFFFFF,bound*17,bound&1,41 if bound&2 else 0,bound%4,bound%8,bound%6)
 for second,fp in itertools.product((0,1,2,3,0x7FFFFFFF,0x80000000,0xFFFFFFFF),range(6)):yield Case(8,0,second,1,41,1,6,fp)
 for bound in(0x108,0x80000008,0xFFFFFFFF,0x12340002):yield Case(bound,0x80000007,2,1,41,3)
 for first,second in itertools.product((0,1,7,0xFFFFFFFF),(0,0xFFFFFFFF)):yield Case(8,first,second,0,0,4,0,0,-1,1)
 for first,home in itertools.product((0,7,0x80000000,0xFFFFFFFF),(1,2,8,255)):yield Case(8,first,2,1,41,1,0,0,home)

def public(m):return{a:v for a,v in m.items()if not STACK-128<=a<STACK+256}
def compare(programs,c,s,entry=ENTRY,trap=False,zero_pattern=0):
 initial=fixture(c,s);expected,calls,observations,fault=reference(initial,c,s);assert fault==trap;models=[]
 for program in programs:
  m=Oracle(program,initial,c,s,entry,zero_pattern=zero_pattern)
  try:m.run()
  except TrapBoundary:assert trap and m.current_pc-entry==0x3C
  else:assert not trap
  assert public(m.memory)==public(expected)and m.calls==calls and m.observations==observations,(c,'public state/calls/observations')
  if not trap:assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
  models.append(m)
 for m in models[1:]:assert(m.memory,m.r,m.f,m.trace,m.visits)==(models[0].memory,models[0].r,models[0].f,models[0].trace,models[0].visits)
 return models[0]

def guest():
 paths=('original-func_1506B634.o','selected-final.o','qualified-padded.o','make-shadow/src/game_981E0.c.o');count=traps=0;seen=set();retail_programs=None
 for index,entry in enumerate((ENTRY,0x17007FFC,0x1F00FFFC)):
  s=symbols(index);programs=[link(o/n,'choice-program-%d-%d'%(index,i),entry,s)for i,n in enumerate(paths)];assert all(p==programs[0]for p in programs)
  for c in corpus():m=compare(programs,c,s,entry);seen.update(pc-entry for pc in m.visits);count+=1
  for bound,home,zero_pattern in itertools.product((0,0x100,0xFFFFFF00,8),(-1,0),range(3)):
   if bound==8 and home<0:continue
   compare(programs,Case(bound,0x87654321,2,1,41,1,0,0,home),s,entry,True,zero_pattern);traps+=1
  if not index:retail_programs=programs
 assert set(range(0,268,4))-seen=={0x3C},set(range(0,268,4))-seen
 return dict(cases=count,executions=count*4,trap_cases=traps,trap_executions=traps*4,body_words=67,frame=24,rebases=3,all_66_nontrap_words_executed=True,break7_prefix_verified=True,DIVU_zero_hilo_hardware_claimed=False,all_nonzero_byte_bounds=True,table_alias_distance=8,helper_mutations_and_home_reload=True,all_machine_states_and_traces_equal=True),retail_programs

class ReturnPoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc in (0x1506B7E4,0x1506B81C):self.owner.r[2]=self.owner.poison;self.owner.return_poisons+=1
  return super().__getitem__(pc)

def callers(programs):
 rom=(r/'conker/conker.us.bin').read_bytes();s=symbols();count=0
 # Original argument construction and return epilogues, bounded before jr.
 windows=((0x1506B7DC,4,8),(0x1506B7F8,11,2))
 for start,n,bound in windows:
  body=struct.unpack_from('>%dI'%n,rom,start-0x15000000+0x2D4B0);end=start+n*4
  for first,mode,pattern,mutation in itertools.product((0,7,0x80000000,0xFFFFFFFF),(0,1),range(4),(0,7)):
   c=Case(bound,first,0xFFFFFFFF,mode,41,pattern,mutation);initial=fixture(c,s);expected,calls,observations,_=reference(initial,c,s)
   if bound==2:expected[ACTORS[0]+0x89]=0;expected[ACTORS[0]+0x83]=0
   for program,poison in itertools.product(programs,(0,1,0x80000000,0xFFFFFFFF)):
    memory=dict(initial);home=STACK;put(memory,home+0x14,0xDEAD0000)
    code=dict(zip(range(ENTRY,ENTRY+268,4),program));code[end]=0;m=Oracle(body,memory,c,s,start,code);m.r[2]=s['D_800D154C'];m.r[4]=0xABCD1234;m.poison=poison;m.return_poisons=0
    m.code=ReturnPoisonCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary not reached')
    assert public(m.memory)==public(expected)and m.calls==[(ENTRY,())]+calls and m.observations==observations,(hex(start),c,m.calls,calls)
    assert m.return_poisons==1 and m.r[29]==home+24 and m.r[31]==0xDEAD0000
   count+=1
 census=json.loads((o/'caller-census.json').read_text());assert len(census['aligned_ROM_JALs'])==2 and not census['aligned_ROM_pointer_literals']
 return dict(cases=count,executions=count*16,original_windows=2,actual_bounds=[8,2],return_poisons=4,return_ignored=True,full_parent_reachability_claimed=False)

def controls():
 return (
 ('signed-random','(u32)func_150ADA20()','func_150ADA20()'),
 ('wide-tables','((u8 *)D_80099','(D_80099'),
 ('wrong-category','D_800BE9F0 == 0x29','D_800BE9F0 != 0x29'),
 ('wrong-special','unkE == 0xA7','unkE == 0xA6'),
 ('wrong-variant','% 3U) + 2','% 3U) + 1'),
 ('cached-post-helper-actor','func_1506E8D8();\n        D_800D154C->xz_velocity *= D_80099C38;','{ struct127 *actor = D_800D154C; func_1506E8D8(); actor->xz_velocity *= D_80099C38; }'))

def digest(m,calls,observations,s):
 h=2166136261
 def mix(v):
  nonlocal h
  h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 for name in('D_800D1580','D_800BE9F0','D_80099C38'):mix(read(m,s[name]))
 mix(ACTORS.index(read(m,s['D_800D154C'])))
 for i in range(520):
  if not 388<=i<392:mix(m[s['D_80099AB4']+i])
 for a in ACTORS:
  mix(read(m,a+0x3C))
  for i in range(812):
   if not 0x3C<=i<0x40 and not 0x31C<=i<0x320:mix(m[a+i])
 for state in STATES:
  mix(read(m,state+0xE,2))
  for i in range(0x1AC):
   if i not in(14,15):mix(m[state+i])
 mix(len(calls))
 for observation in observations:
  for v in observation:mix(v)
 return h

def native():
 bodies=[source.SELECTED]
 for name,old,new in controls():assert old in source.SELECTED;bodies.append(source.SELECTED.replace(old,new))
 header=source.HEADERS.replace('extern s16 D_80099AB4[], D_80099ABC[];','union PackedChoices {s16 words[260];u8 bytes[520];struct {u8 pad[388];f32 factor;} scale;};\nstatic union PackedChoices packed;\n#define D_80099AB4 (packed.words)\n#define D_80099ABC (packed.words + 4)')
 header=header.replace('extern f32 D_80099C38;','#define D_80099C38 (packed.scale.factor)')
 code=header+'\n'.join(b.replace('func_1506B634','candidate_'+str(i))for i,b in enumerate(bodies))
 table,factor=retail()
 code+='''
struct127 *D_800D154C; s32 D_800D1580,D_800BE9F0;
static struct127 actors[3];static struct126 states[3];
static u32 randoms[2],rng_count,call_count,mutation,observations[3][8];
static const u32 floats[6]={0,0x80000000u,0x3FA00000u,0xC2000000u,0x00800000u,1};
static const u8 retail_bytes[520]={'''+','.join(str(v)for v in table)+'''};
typedef char ActorSize[sizeof(struct127)==812?1:-1];
typedef char StateSize[sizeof(struct126)==0x1AC?1:-1];
typedef char VelocityOffset[__builtin_offsetof(struct127,xz_velocity)==0x3C?1:-1];
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static f32 single(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static void log_call(u32 tag){u32 *v=observations[call_count++];struct127 *a=D_800D154C;v[0]=tag;v[1]=D_800D1580;v[2]=(u32)(a-actors);v[3]=a->unk31C->unkE;v[4]=a->unk31C->unkC;v[5]=D_800BE9F0;v[6]=word(D_80099C38);v[7]=word(a->xz_velocity);}
s32 func_150ADA20(void){u32 i,n=rng_count++,answer=randoms[n<2?n:1];log_call(0);
 if(n==0&&(mutation&1)){D_800D154C=&actors[1];D_800BE9F0=41;states[1].unk16^=1;for(i=0;i<520;i++)packed.bytes[i]=0xA7;}
 if(n==1&&(mutation&2)){D_800D154C=&actors[2];D_80099C38=single(0x3F000000u);}return(s32)answer;}
void func_1506E8D8(void){log_call(1);if(mutation&4){D_800D154C=&actors[0];actors[0].xz_velocity=single(0xC0200000u);D_80099C38=single(0x40000000u);}}
typedef struct{u32 bound,first,second,mode,category,pattern,mutation,fp,expected;}Test;
static const Test tests[]={
'''
 rows=[]
 for c in corpus():
  if c.alias or c.home>=0:continue
  s=symbols();initial=fixture(c,s);expected,calls,observations,trap=reference(initial,c,s);assert not trap
  rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in(c.bound,c.first,c.second,c.mode,c.category,c.pattern,c.mutation,c.fp,digest(expected,calls,observations,s)))+'}')
 code+=',\n'.join(rows)+'''};
static u32 mix(u32 h,u32 v){return(h^v)*16777619u;}
static u32 result(void){u32 h=2166136261u,i,j;u8*p;h=mix(h,D_800D1580);h=mix(h,D_800BE9F0);h=mix(h,word(D_80099C38));h=mix(h,(u32)(D_800D154C-actors));
 for(i=0;i<520;i++)if(i<388||i>=392)h=mix(h,packed.bytes[i]);
 for(j=0;j<3;j++){h=mix(h,word(actors[j].xz_velocity));p=(u8*)&actors[j];for(i=0;i<812;i++)if((i<0x3C||i>=0x40)&&(i<0x31C||i>=0x320))h=mix(h,p[i]);}
 for(j=0;j<3;j++){h=mix(h,states[j].unkE);p=(u8*)&states[j];for(i=0;i<0x1AC;i++)if(i!=14&&i!=15)h=mix(h,p[i]);}
 h=mix(h,call_count);for(j=0;j<call_count;j++)for(i=0;i<8;i++)h=mix(h,observations[j][i]);return h;}
static void reset(const Test*t){u32 i,j;u8*p;for(j=0;j<3;j++){p=(u8*)&actors[j];for(i=0;i<812;i++)p[i]=0xA5;p=(u8*)&states[j];for(i=0;i<0x1AC;i++)p[i]=0xA5;actors[j].unk31C=&states[j];actors[j].xz_velocity=single(floats[(t->fp+j)%6]);states[j].unk16=t->mode+j;states[j].unkE=0x5A5A;}
 for(i=0;i<520;i++)packed.bytes[i]=t->pattern==0?retail_bytes[i]:t->pattern==1?0xA7:t->pattern==2?(i*13+29)&255:(i==0||i==8)?0xA7:0x44;
 D_800D154C=&actors[0];D_800D1580=0x12345678;D_800BE9F0=t->category;D_80099C38=single(FACTOR);randoms[0]=t->first;randoms[1]=t->second;mutation=t->mutation;rng_count=call_count=0;}
static int run(void){u32 i,j,killed=0,h;for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<7;j++){reset(&tests[i]);switch(j){case 0:candidate_0(tests[i].bound);break;case 1:candidate_1(tests[i].bound);break;case 2:candidate_2(tests[i].bound);break;case 3:candidate_3(tests[i].bound);break;case 4:candidate_4(tests[i].bound);break;case 5:candidate_5(tests[i].bound);break;default:candidate_6(tests[i].bound);break;}h=result();if(h!=tests[i].expected){if(!j)return 10;killed|=1u<<(j-1);}}return killed==63?0:11;}
'''.replace('FACTOR','0x%Xu'%factor)+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=o/'native-random-choice.c';path.write_text(code);reports=[]
 for profile in('-O0','-O2','-O3'):
  exe=o/('native-random-choice'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=r,capture_output=True,text=True);(o/('native-random-choice'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  reports.append(dict(profile=profile,cases=len(rows),UBSan=True,zero_bound_excluded=True,packed_tables_share_8byte_offset=True,controls=[n for n,_,_ in controls()],all_controls_effective=True))
 return reports

def guest_control():
 body=source.SELECTED.replace('if (D_800D154C->unk31C->unkE == 0xA7)','if (state->unkE == 0xA7)');assert body!=source.SELECTED
 obj,diag=compile_owner(r,o,source.HEADERS+body,'public-cached-state-control');assert not diag
 raw,_=source.payload(obj)
 if (o/'cached-state-negative.o').exists():assert source.payload(obj)==source.payload(o/'cached-state-negative.o')
 program=link(obj,'cached-state-control-linked',ENTRY,symbols(),len(raw)//4)
 c=Case(8,7,2,0,0,4,0,0,-1,1);initial=fixture(c,symbols());expected,calls,observations,_=reference(initial,c,symbols());m=Oracle(program,initial,c,symbols()).run()
 assert public(m.memory)!=public(expected)or m.calls!=calls or m.observations!=observations
 return dict(compiled_cached_state_control_effective=True,alias_case_guest_only=True)

def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 g,programs=guest();print('guest qualified',g['cases'],flush=True)
 report=dict(guest=g,callers=callers(programs),guest_control=guest_control(),native=native(),helper_providers_explicit=True)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def link(obj,label,entry,s,words=67):
 text,functions,bindings=parse_object(obj);asm,unknown=emit_function(text,functions['func_1506B634'],bindings,'func_1506B634',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(name,value)for name,value in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_1506B634','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 data=sections(p.with_suffix('.elf'))['.text'][1][:words*4];return list(struct.unpack('>%dI'%words,data))
