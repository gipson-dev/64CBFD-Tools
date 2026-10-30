"""Group channel normalization: live bounds, callback effects and literal execution."""
from pathlib import Path
from dataclasses import dataclass,replace
import csv,hashlib,io,itertools,json,os,struct,subprocess
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.pad_generated_object import emit_padded_assembly
from tools.experiments.game_group_type2_actor_reset_match import compile_owner
from tools.experiments.game_four_head_lookup_match import payload
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-group-actor-channel-normalize-1501E73C-match';F='func_1501E73C';ENTRY=0x1501E73C
COUNT,TABLE,LOOKUP,REFRESH,INNER=0x800C363A,0x800C35F0,0x15083E90,0x1507EABC,0x1507E7E4
ROW,OTHER,ACTOR,POOL=0x30000,0x34000,0x50000,0x800CC2D0
SYMS=dict(D_800C363A=COUNT,D_800C35F0=TABLE,func_15083E90=LOOKUP,func_1507EABC=REFRESH)
@dataclass(frozen=True)
class Case:
 group:int=0
 length:int=2
 kind:int=2
 selector:int=255
 present:bool=True
 first:int=11
 second:int=12
 mode:int=0
 alias:int=0
 phase:int=0
 seed:int=0
 inner_mode:int=0

def actor(c,s=SYMS):return ACTOR if c.alias==0 else ROW if c.alias==1 else s['D_800C363A']+c.group-0x6C if c.alias==2 else STACK+c.phase-0x400
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-2048,512)}
 for base,size in((ROW,2048),(OTHER,2048),(ACTOR,1024),(s['D_800C35F0'],8),(s['D_800C363A']-4,12)):
  m.update({base+i:(i*13+c.seed)&255 for i in range(size)})
 a=actor(c,s)
 for i in range(0x300):m[a+i]=(i*19+c.seed)&255
 for base in(ROW,OTHER):
  for i in range(255):put(m,base+i*8,c.kind if base==ROW or i%2==0 else 0,2);m[base+i*8+2]=(c.selector+i*53+(7 if base==OTHER else 0))&255
 for g in range(2):put(m,s['D_800C35F0']+g*4,ROW);m[s['D_800C363A']+g]=0
 m[a+0x6C]=c.first;m[a+0x6D]=c.second;m[s['D_800C363A']+c.group]=c.length
 return m
def visible(m,c,s=SYMS):
 out={a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}
 a=actor(c,s);out.update({a+i:m[a+i]for i in range(0x300)});return out
def effect(m,c,s,which,n,a):
 if n==1:
  if c.mode&1:m[s['D_800C363A']+c.group]=1
  if c.mode&2:m[s['D_800C363A']+c.group]=4
  if c.mode&4:put(m,s['D_800C35F0']+4*c.group,OTHER)
  if c.mode&8:m[a+0x6C]=255;m[a+0x6D]=10;put(m,OTHER+8,2,2);m[OTHER+10]=17
 if which=='refresh':
  if c.mode&16:m[s['D_800C363A']+c.group]=0
  if c.mode&32:m[a+0x6C]=13;m[a+0x6A]=0xE1
def reference(initial,c,s=SYMS,a=None):
 m=dict(initial);calls=[];observations=[];offset=0;lookups=refreshes=0;a=actor(c,s)if a is None else a
 while offset<m[s['D_800C363A']+c.group]*8:
  record=read(m,s['D_800C35F0']+4*c.group)+offset
  if read(m,record,2)==2:
   selected=m[record+2];calls.append((s['func_15083E90'],(selected,)));lookups+=1;effect(m,c,s,'lookup',lookups,a)
   if c.present:
    if m[a+0x6C]>=10:m[a+0x6C]=0;m[a+0x6A]=0
    if m[a+0x6D]>=10:m[a+0x6D]=0;m[a+0x6B]=0
    calls.append((s['func_1507EABC'],(a,)));observations.append((a,bytes(m[a+i]for i in range(0x6A,0x6E))));refreshes+=1;effect(m,c,s,'refresh',refreshes,a)
  offset+=8
 return m,calls,observations

class Oracle(RayOracle):
 def __init__(self,words,memory,c=Case(),s=SYMS,entry=ENTRY,connected=None,args=None,actor_at=None):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.group,)if args is None else args,connected=connected)
  self.case=c;self.syms=s;self.trace=[];self.observations=[];self.actor_at=actor(c,s)if actor_at is None else actor_at;self.lookups=self.refreshes=0;self.inner=[]
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  s=self.syms;sizes={s['func_15083E90']:1,s['func_1507EABC']:1,INNER:5,ENTRY:1};assert target in sizes,('Unbounded helper',hex(target));args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==s['func_1507EABC']:
   a=self.r[4];self.observations.append((a,bytes(self.memory[a+i]for i in range(0x6A,0x6E))))
  if target==INNER:self.inner.append(args)
 def hook(self,target):
  c=self.case;s=self.syms;value=0
  if target==s['func_15083E90']:
   self.lookups+=1;effect(self.memory,c,s,'lookup',self.lookups,self.actor_at);value=self.actor_at if c.present else 0
  elif target==s['func_1507EABC']:
   self.refreshes+=1;effect(self.memory,c,s,'refresh',self.refreshes,self.actor_at);value=0xDEADBEEF
  elif target==INNER:
   # Deliberately alter channels before the original refresh's own checks.
   a=self.r[4];assert self.arguments(5)==(a,self.memory[a+0x70],3,65535,10)
   first,second=((0,0),(9,10),(10,9),(255,255))[c.inner_mode];self.memory[a+0x6C]=first;self.memory[a+0x6D]=second;self.memory[a+0x71]=0xA5;put(self.memory,a+0x72,0xFFFF,2);value=0xABCD1234
  else:raise AssertionError(hex(target))
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.observations,m.condition)
def verify(m,initial,c,s=SYMS):
 want,calls,obs=reference(initial,c,s);assert(visible(m.memory,c,s),m.calls,m.observations)==(visible(want,c,s),calls,obs),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.saved_f
def cases():
 for n in range(256):yield Case(length=n,kind=0,group=n&1)
 for n,g,found in itertools.product(range(256),(0,1),(False,True)):yield Case(length=1,group=g,selector=n,present=found,first=n,second=255-n)
 for n,g in itertools.product(range(256),(0,1)):yield Case(length=1,group=g,first=255-n,second=n,alias=1)
 for length,kind,found,mode,g,phase in itertools.product((0,1,2,4),(0,2,65535),(False,True),(0,1,2,4,8,16,32,7,63),(0,1),(0,8)):yield Case(length=length,kind=kind,present=found,mode=mode,group=g,phase=phase,first=9,second=10)
 for alias,g,mode in itertools.product((1,2,3),(0,1),(0,1,4,16,32,63)):yield Case(length=10 if alias==2 else 3,alias=alias,group=g,mode=mode)
def run_suite():
 original=linked(o/('original-'+F+'.o'),'semantic-original');normalized=linked(o/'qualified-padded.o','semantic-normalized');raw=linked(o/'selected-final.o','semantic-raw');assert original==normalized;count=0;visits=set();raw_empty_temp_difference=False
 for c in cases():
  initial=fixture(c);ms=[]
  for words in(original,normalized,raw):m=Oracle(words,initial,c).run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1]);assert ms[0].trace==ms[2].trace;visits.update(ms[0].visits);count+=1
  if c.length==0 and ms[0].r[24]!=ms[2].r[24]:raw_empty_temp_difference=True
 assert set(range(ENTRY,ENTRY+224,4))<=visits and raw_empty_temp_difference
 prefixes=delays=0
 for c in(Case(length=0),Case(length=1,kind=0),Case(length=1,present=False),Case(length=1),Case(length=2,mode=7,alias=1),Case(length=10,alias=2)):
  initial=fixture(c);full=Oracle(original,initial,c).run()
  for cut in range(full.root_accesses):
   pair=[]
   for words in(original,normalized):
    m=Oracle(words,initial,c);m.root_fault=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Unfired cut',cut))
    assert m.root_accesses==cut;pair.append(m)
   assert state(pair[0])==state(pair[1])and(pair[0].current_pc,pair[0].delay_of)==(pair[1].current_pc,pair[1].delay_of);prefixes+=1;delays+=pair[0].delay_of is not None
 lazy=0
 for c in(Case(length=0),Case(length=1,present=False)):
  initial=fixture(c)
  for i in range(0x300):initial.pop(ACTOR+i,None)
  if c.length==0:
   for i in range(8):initial.pop(TABLE+i,None)
   for i in range(2048):initial.pop(ROW+i,None)
  for words in(original,normalized,raw):Oracle(words,initial,c).run()
  lazy+=1
 rebased=0
 for j,(entry,table,countat)in enumerate(((0x17007FFC,0x80017FFC,0x80028002),(0x2500FFFC,0x80028000,0x8001FFFC),(0x15008000,0x8001FFFC,0x80017FFE))):
  s=dict(D_800C363A=countat,D_800C35F0=table,func_15083E90=entry+0x10004,func_1507EABC=entry+0x20008);ps=[linked(p,'rebase'+str(j)+'-'+str(i),entry,s)for i,p in enumerate((o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o'))];assert ps[0]==ps[1]
  for g,n,found,mode in itertools.product((0,1),(0,1,3),(False,True),(0,7,16,63)):
   c=Case(group=g,length=n,present=found,mode=mode);initial=fixture(c,s);ms=[]
   for words in ps:m=Oracle(words,initial,c,s,entry).run();verify(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])and ms[0].trace==ms[2].trace;rebased+=1
 return dict(cases=count,executions=count*3,body_words=56,covered_words=56,frame=40,guards=5,original_normalized_complete_state_equal=True,raw_public_and_memory_trace_equal=True,raw_empty_caller_saved_temp_difference_observed=raw_empty_temp_difference,all_unsigned_channel_and_selector_bytes=True,all_count_bytes=True,live_bound_and_table_callback_changes=True,alias_layouts=4,access_prefix_pairs=prefixes,delay_slot_cuts=delays,rebase_layouts=3,rebase_cases=rebased,lazy_unmapped_paths=lazy,portable_fault_private_home_FCSR_claimed=False)

def helper_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();lookup=list(struct.unpack_from('>72I',rom,0xB1340));refresh=list(struct.unpack_from('>28I',rom,0xABF6C));programs=[linked(p,'helper-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o'))];count=0;visits=set()
 for selector,hit,inactive_first,phase,channels,inner_mode in itertools.product((0,1,128,255),(-1,0,1,2,3,4,5,13,25),(False,True),(0,8),((9,10),(255,255)),range(4)):
  present=selector!=0 and hit>=0;c=Case(length=1,selector=selector,present=present,phase=phase,first=channels[0],second=channels[1],inner_mode=inner_mode);initial=fixture(c)
  for i in range(26*0x32C):initial[POOL+i]=(i*17+0xA5)&255
  for i in range(26):put(initial,POOL+i*0x32C,0 if inactive_first else 1);initial[POOL+i*0x32C+0x3B]=(selector+1)&255
  a=POOL+max(hit,0)*0x32C
  if present:
   put(initial,a,1);initial[a+0x3B]=selector;initial[a+0x6C]=channels[0];initial[a+0x6D]=channels[1]
   if hit<25:put(initial,a+0x32C,1);initial[a+0x32C+0x3B]=selector
   if inactive_first and hit>0:put(initial,POOL,0);initial[POOL+0x3B]=selector
  expected=dict(initial);calls=[(LOOKUP,(selector,))];observations=[]
  if present:
   if expected[a+0x6C]>=10:expected[a+0x6C]=0;expected[a+0x6A]=0
   if expected[a+0x6D]>=10:expected[a+0x6D]=0;expected[a+0x6B]=0
   observations.append((a,bytes(expected[a+i]for i in range(0x6A,0x6E))))
   calls.extend(((REFRESH,(a,)),(INNER,(a,expected[a+0x70],3,65535,10))))
   first,second=((0,0),(9,10),(10,9),(255,255))[inner_mode];expected[a+0x6C]=first;expected[a+0x6D]=second
   for i in(0x71,0x72,0x73):expected[a+i]=0
   if first>=10:expected[a+0x6C]=0;expected[a+0x6A]=0
   if second>=10:expected[a+0x6D]=0;expected[a+0x6B]=0
  ms=[]
  for words in programs:
   connected={base+i*4:w for base,body in((LOOKUP,lookup),(REFRESH,refresh))for i,w in enumerate(body)};m=Oracle(words,initial,c,connected=connected,actor_at=a).run();ms.append(m);visits.update(m.visits)
   assert(visible(m.memory,c),m.calls,m.observations)==(visible(expected,c),calls,observations),(c,hit,inactive_first)
   assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.f[20:]==m.saved_f
  assert state(ms[0])==state(ms[1])and ms[0].trace==ms[2].trace;count+=1
 lookup_missing=set(range(LOOKUP,LOOKUP+288,4))-visits
 assert lookup_missing=={LOOKUP+120,LOOKUP+156,LOOKUP+192,LOOKUP+228},sorted(hex(p-LOOKUP)for p in lookup_missing)
 assert set(range(REFRESH,REFRESH+112,4))<=visits
 return dict(cases=count,programs=3,original_lookup_words=72,lookup_covered_words=68,unreachable_lookup_word_offsets=sorted(p-LOOKUP for p in lookup_missing),original_refresh_words=28,refresh_covered_words=28,current_lookup_exact=True,current_refresh_exact=True,independent_pre_refresh_field_observations=True,inner_reset_mutations_then_refresh_checks=True,first_live_match_and_null_routes=True,bounded_providers=['func_1507E7E4'],no_helper_credit=True)

def caller_suite():
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 rom=(r/'conker/conker.us.bin').read_bytes();entry,end=0x1501E8C0,0x1501E8D8;window=list(struct.unpack_from('>6I',rom,0x4BD70));programs=[linked(p,'caller-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o'))];count=0;visits=set()
 for group,length,kind,present,mode,phase,alias in itertools.product((0,1),(0,1,3),(0,2),(False,True),(0,7,16,63),(0,8),(0,1)):
  c=Case(group=group,length=length,kind=kind,present=present,mode=mode,phase=phase,alias=alias);initial=fixture(c);gate=0x800C35EA+group;initial[gate]=255;initial[0x800C3638]=255;put(initial,STACK+phase+0x30,gate)
  entered=dict(initial);entered[gate]=0;entered[0x800C3638]=0;want,calls,obs=reference(entered,c);calls=[(ENTRY,(group,))]+calls;ms=[]
  for words in programs:
   connected={ENTRY+i*4:w for i,w in enumerate(words)};m=Oracle(window,initial,c,entry=entry,connected=connected);m.r[16]=group;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code[end]=0;m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller boundary not reached')
   assert(visible(m.memory,c),m.calls,m.observations)==(visible(want,c),calls,obs),c
   assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24];ms.append(m);visits.update(m.visits)
  assert state(ms[0])==state(ms[1])and ms[0].trace==ms[2].trace;count+=1
 assert set(range(entry,end,4))<=visits
 return dict(cases=count,programs=3,window_words=6,covered_window_words=6,entry=hex(entry),end=hex(end),original_group_from_S0=True,gate_clear_and_branch_delay_global_clear=True,current_caller_window_exact=False,complete_parent_claimed=False)

def controls(selected):
 cached_count=selected.replace('    s32 offset;','    s32 offset;\n    s32 cached_count = D_800C363A[group];').replace('offset < D_800C363A[group] * 8','offset < cached_count * 8')
 cached_table=selected.replace('    u8 *record;','    u8 *record;\n    u8 *cached_table;').replace('records = &D_800C35F0[group];','records = &D_800C35F0[group];\n        cached_table = *records;').replace('record = *records + offset;','record = cached_table + offset;')
 before=selected.replace('                    func_1507EABC(actor);','').replace('                    if (actor[0x6C] >= 10)','                    func_1507EABC(actor);\n                    if (actor[0x6C] >= 10)')
 return dict(wrong_type=selected.replace('*(u16 *)record == 2','*(u16 *)record == 3'),wrong_first_threshold=selected.replace('actor[0x6C] >= 10','actor[0x6C] >= 9'),signed_first=selected.replace('actor[0x6C] >= 10','(s8)actor[0x6C] >= 10'),wrong_second_threshold=selected.replace('actor[0x6D] >= 10','actor[0x6D] >= 11'),wrong_pair=selected.replace('actor[0x6A] = 0','actor[0x6B] = 0'),wrong_stride=selected.replace('offset += 8','offset += 4'),wrong_selector=selected.replace('record[2]','record[3]'),cached_count=cached_count,cached_table=cached_table,early_null_exit=selected.replace('goto advance','return'),wrong_refresh_actor=selected.replace('func_1507EABC(actor);','func_1507EABC(actor + 1);'),refresh_before_clear=before,skip_single=selected.replace('D_800C363A[group] > 0','D_800C363A[group] > 1'))

def native_harness(selected):
 marker='/* Normalize';head=selected[:selected.index(marker)];body=selected[selected.index(marker):];t=head+r'''
u8 D_800C363A[2];u8 *D_800C35F0[2];
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(u16)==2)?1:-1];
static union {u32 align;u8 b[2048];} ra,rb,sa,sb;
static union {u32 align;u8 b[0x300];} aa,ea;
static u32 group,mode,seed,found,alias,nL,nR,error,na,ne;
static u8 *actualActor;static u32 actualEvents[512][3],expectedEvents[512][3];
static void event(u32 tag,u32 value,u32 fields){if(na>=512){error=1;return;}actualEvents[na][0]=tag;actualEvents[na][1]=value;actualEvents[na++][2]=fields;}
static u32 fields(u8*a){return (u32)a[106]|(u32)a[107]<<8|(u32)a[108]<<16|(u32)a[109]<<24;}
static void set16(u8*p,u16 v){p[0]=(u8)v;p[1]=(u8)(v>>8);}
static void mutate(u32 refresh,u32 n,u8*counts,u8**table,u8*a,u8*b){
 if(n==1){if(mode&1)counts[group]=1;if(mode&2)counts[group]=4;if(mode&4)table[group]=b;if(mode&8){a[108]=255;a[109]=10;set16(b+8,2);b[10]=17;}}
 if(refresh){if(mode&16)counts[group]=0;if(mode&32){a[108]=13;a[106]=225;}}}
__attribute__((noinline)) u8 *func_15083E90(u8 id){event(1,id,0);mutate(0,++nL,D_800C363A,D_800C35F0,actualActor,rb.b);return found?actualActor:0;}
__attribute__((noinline)) void func_1507EABC(u8*a){if(a!=actualActor){error=1;return;}event(2,alias,fields(a));mutate(1,++nR,D_800C363A,D_800C35F0,a,rb.b);}
'''
 for name,text in dict(selected=body,**{n:x[x.index(marker):]for n,x in controls(selected).items()}).items():t+=text.replace('void '+F,'void test_'+name)+'\n'
 t+=r'''
typedef void(*Fn)(s32);
static int one(Fn fn,u32 length,u32 kind,u32 flags){u32 i,j,k,lane,lookups=0,refreshes=0;u8 counts[2],*tables[2],*a,*rec;
 found=flags&1;mode=(flags>>1)&63;alias=(flags>>7)&1;
 for(i=0;i<2048;i++)ra.b[i]=rb.b[i]=(u8)(i*13+seed);
 for(i=0;i<0x300;i++)aa.b[i]=ea.b[i]=(u8)(i*19+seed);
 for(i=0;i<255;i++){set16(ra.b+i*8,(u16)kind);set16(rb.b+i*8,(u16)(i%2?0:kind));ra.b[i*8+2]=(u8)(seed+i*53);rb.b[i*8+2]=(u8)(seed+i*53+7);}
 actualActor=alias?ra.b:aa.b;actualActor[108]=(u8)seed;actualActor[109]=(u8)(255-seed);
 for(i=0;i<2048;i++){sa.b[i]=ra.b[i];sb.b[i]=rb.b[i];}
 a=alias?sa.b:ea.b;a[108]=(u8)seed;a[109]=(u8)(255-seed);
 for(i=0;i<2;i++){D_800C363A[i]=counts[i]=0;D_800C35F0[i]=ra.b;tables[i]=sa.b;}D_800C363A[group]=counts[group]=(u8)length;
 ne=0;
 for(lane=0;lane<counts[group];lane++){
  rec=tables[group]+lane*8;
  if(((u32)rec[0]|(u32)rec[1]<<8)!=2)continue;
  expectedEvents[ne][0]=1;expectedEvents[ne][1]=rec[2];expectedEvents[ne++][2]=0;
  mutate(0,++lookups,counts,tables,a,sb.b);
  if(!found)continue;
  for(j=0;j<2;j++)if(a[108+j]>=10){a[108+j]=0;a[106+j]=0;}
  expectedEvents[ne][0]=2;expectedEvents[ne][1]=alias;expectedEvents[ne++][2]=fields(a);
  mutate(1,++refreshes,counts,tables,a,sb.b);
 }
 na=nL=nR=error=0;fn((s32)group);if(error||na!=ne)return 1;
 for(i=0;i<ne;i++)for(j=0;j<3;j++)if(actualEvents[i][j]!=expectedEvents[i][j])return 1;
 for(i=0;i<2;i++)if(D_800C363A[i]!=counts[i]||(D_800C35F0[i]==rb.b)!=(tables[i]==sb.b))return 1;
 for(k=0;k<2048;k++)if(ra.b[k]!=sa.b[k]||rb.b[k]!=sb.b[k])return 1;
 for(lane=0;lane<0x300;lane++)if(aa.b[lane]!=ea.b[lane])return 1;return 0;}
static int check(Fn fn){u32 g,n,k,f;static const u32 lengths[]={0,1,2,4,255};static const u32 kinds[]={0,1,2,65535};static const u32 modes[]={0,1,2,4,8,16,32,63};
 seed=0;for(g=0;g<2;g++)for(n=0;n<256;n++){group=g;if(one(fn,n,0,0))return 1;}
 for(seed=0;seed<256;seed++)for(g=0;g<2;g++)for(n=0;n<5;n++)for(k=0;k<4;k++)for(f=0;f<32;f++){
  group=g;if(one(fn,lengths[n],kinds[k],(f&1)|(modes[(f>>1)&7]<<1)|((f>>4)<<7)))return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(controls(selected)):t+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

def run_native(selected):
 p=o/'native-v1.c';p.write_text(native_harness(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native-v1'+opt);cmd=native_command(opt)+['-fno-strict-aliasing','-Wno-unused-label',str(p),'-o',str(exe)];build=subprocess.run(cmd,cwd=r,capture_output=True,text=True);assert build.returncode==0,(opt,build.stdout,build.stderr);run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stdout,run.stderr);profiles[opt]=dict(exit=run.returncode,cases=328192,UBSan=True);print('NATIVE_PROFILE',opt,profiles[opt],flush=True)
 return dict(cases=328192,negative_controls=len(controls(selected)),profiles=profiles,all_count_channel_and_selector_bytes=True,live_count_and_table_mutations=True,record_alias=True,exact_call_and_pre_refresh_fields=True,SDK_ABI=True,portable_private_home_fault_FCSR_claimed=False)

RAW_SHA='2c2bba3a77664d260aa9d4e5ed9885d4b8e7eecb71b7619a35bd37d7a2fa6358'
RAW_BINDINGS={24:[('R_MIPS_HI16','D_800C363A')],28:[('R_MIPS_LO16','D_800C363A')],52:[('R_MIPS_HI16','D_800C35F0')],56:[('R_MIPS_LO16','D_800C35F0')],88:[('R_MIPS_26','func_15083E90')],164:[('R_MIPS_26','func_1507EABC')]}
ORIGINAL_BINDINGS={24:[('R_MIPS_HI16','D_800C363A')],28:[('R_MIPS_LO16','D_800C363A')],40:[('R_MIPS_HI16','D_800C35F0')],44:[('R_MIPS_LO16','D_800C35F0')],88:[('R_MIPS_26','func_15083E90')],164:[('R_MIPS_26','func_1507EABC')]}
def normalize(raw,bindings,owner='generated_49D30',function=F):
 if owner!='generated_49D30'or function!=F or len(raw)!=224 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=RAW_BINDINGS:raise ValueError('Group normalization input fingerprint/scope changed')
 result=bytearray(raw);rs={a:list(v)for a,v in bindings.items()}
 for at,expected,replacement,newrs in((40,0x00008025,0x3C180000,[('R_MIPS_HI16','D_800C35F0')]),(44,0x00047880,0x27180000,[('R_MIPS_LO16','D_800C35F0')]),(52,0x3C180000,0x00047880,[]),(56,0x27180000,0x01F89021,[]),(60,0x01F89021,0x00008025,[])):
  if struct.unpack_from('>I',result,at)[0]!=expected:raise ValueError('Opening preimage changed')
  struct.pack_into('>I',result,at,replacement);rs.pop(at,None)
  if newrs:rs[at]=newrs
 result=bytes(result)
 if hashlib.sha256(result).hexdigest()!='8e317b30e24a06c5fbb7c57670bfbeb19e89af0e02dd133f3e49a4f5c9bcd419'or rs!=ORIGINAL_BINDINGS:raise ValueError('Normalized body/bindings differ from original')
 return result,rs

def guard_suite():
 work=o/('guard-run-'+str(os.getpid()));work.mkdir(exist_ok=False);raw,rs=payload(o/'selected-final.o',F);truth,trs=payload(o/('original-'+F+'.o'),F);assert normalize(raw,rs)==(truth,trs)
 gate_controls=0
 def reject(*args,**kwargs):
  nonlocal gate_controls
  try:normalize(*args,**kwargs)
  except ValueError:gate_controls+=1
  else:raise AssertionError('Ineffective raw normalization control')
 for i in range(224):
  bad=bytearray(raw);bad[i]^=1;reject(bytes(bad),rs)
 for at in rs:reject(raw,{**rs,at:[('R_MIPS_26','wrong_symbol')]})
 reject(raw[:-4],rs);reject(raw+b'\0\0\0\0',rs);reject(raw,rs,owner='other');reject(raw,rs,function='func_1501E81C');reject(raw,{**rs,60:[('R_MIPS_26','unexpected')]})
 asm=(r/'conker/asm/49D30.s').read_text();asm=asm[asm.index('glabel '+F):asm.index('endlabel '+F)+len('endlabel '+F)];target=work/'target.s';target.write_text(asm+'\n')
 def assemble(p):subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
 def emit(obj,label,guards=o/'proposed-guards.csv',owner='generated_49D30'):
  # This isolated retail slice contains one function. Keep its exact guard rows;
  # the separate full-owner proof consumes every inherited owner guard.
  source_rows=list(csv.DictReader(io.StringIO(guards.read_text())));selected=[x for x in source_rows if x['filename']=='generated_49D30'and x['function']in(F,'func_1501E81C')];stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=source_rows[0].keys(),lineterminator='\n');writer.writeheader();writer.writerows(selected);scoped=work/(label+'-guards.csv');scoped.write_text(stream.getvalue())
  p=work/(label+'.s');p.write_text(emit_padded_assembly(obj,target,word_patches_path=scoped,filename=owner));return payload(assemble(p),F)
 assert emit(o/'selected-final.o','positive')==(truth,trs)
 inherited=(o/'before-conker_retail_word_patches.us.csv').read_bytes();guard_bytes=(o/'proposed-guards.csv').read_bytes();assert guard_bytes.startswith(inherited)
 allrows=list(csv.DictReader(io.StringIO(guard_bytes.decode())));newrows=list(csv.DictReader(io.StringIO(guard_bytes[len(inherited):].decode()),fieldnames=allrows[0].keys()));assert len(newrows)==5 and[int(x['offset'],0)for x in newrows]==[40,44,52,56,60]
 # The five guards permute the same six opening operations, including the unchanged branch.
 before=[(raw[a:a+4],tuple(rs.get(a,[])))for a in range(40,64,4)];after=[(truth[a:a+4],tuple(trs.get(a,[])))for a in range(40,64,4)];assert sorted(before)==sorted(after)
 def object_file(label,data,bindings):
  p=work/(label+'.s');lines=['.text','.globl '+F,'.type '+F+',@function',F+':']
  for at in range(0,len(data),4):
   for kind,symbol in bindings.get(at,[]):lines.append('.reloc ., '+kind+', '+symbol)
   lines.append('.word 0x%08X'%struct.unpack_from('>I',data,at)[0])
  lines.append('.size '+F+',.-'+F);p.write_text('\n'.join(lines)+'\n');return assemble(p)
 actual_controls=0
 def emit_reject(obj,label,guards=o/'proposed-guards.csv'):
  nonlocal actual_controls
  try:emit(obj,label,guards)
  except ValueError:actual_controls+=1
  else:raise AssertionError(('Ineffective actual padder guard',label))
 for at in(40,44,52,56,60):
  bad=bytearray(raw);bad[at]^=1;emit_reject(object_file('word-'+str(at),bytes(bad),rs),'bad-word-'+str(at))
 for at,bindings in((40,{**rs,40:[('R_MIPS_HI16','wrong')]}),(52,{**rs,52:[('R_MIPS_HI16','wrong')]}),(56,{k:v for k,v in rs.items()if k!=56})):
  emit_reject(object_file('reloc-'+str(at),raw,bindings),'bad-reloc-'+str(at))
 assert emit(o/'selected-final.o','foreign-owner',owner='foreign-owner')==(raw,rs)
 foreign=[dict(x,function='func_1501E81C')for x in newrows];stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=allrows[0].keys(),lineterminator='\n');writer.writerows(foreign);p=work/'foreign.csv';p.write_bytes(inherited+stream.getvalue().encode());emit_reject(o/'selected-final.o','foreign-function',p)
 return dict(guards=5,raw_normalization_rejection_controls=gate_controls,actual_padder_preimage_relocation_rejections=actual_controls,foreign_owner_and_function_do_not_apply=True,opening_operation_multiset_identical=True,insertions=0,omissions=0,all_56_words_and_six_bindings_exact=True,inherited_guard_prefix_unchanged=True)

def compiled_controls(selected):
 effective=[]
 for name,text in controls(selected).items():
  if name=='early_null_exit':text=text.replace('advance:\n','')
  assert text!=selected;obj,diag=compile_owner(r,o,text,'negative-'+name);assert not diag,diag;words=linked(obj,'negative-link-'+name);failed=False
  for c in(Case(length=1),Case(length=1,first=9,second=10),Case(length=1,first=255,second=9),Case(length=2),Case(length=2,mode=2,present=False),Case(length=3,mode=4),Case(length=1,mode=32),Case(length=3,mode=7,alias=1)):
   initial=fixture(c);put(initial,ROW+4,2,2);initial[ROW+6]=17
   try:m=Oracle(words,initial,c).run();verify(m,initial,c)
   except(AssertionError,KeyError):failed=True;break
  assert failed,('Ineffective IDO control',name);effective.append(name)
 return dict(count=len(effective),effective_IDO_controls=effective,public_and_pre_refresh_reference_failures=True)
