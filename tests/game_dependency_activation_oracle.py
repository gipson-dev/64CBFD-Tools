"""Dependency activation: ordered guest accesses and finite connected traversals."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.experiments import game_dependency_activation_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD
CALLBACK,WALK,CALLER=0x1509CCB4,0x1509CE64,0x1509CDDC
SYMS=dict(D_80087440=0x80087440,D_800D2E4C=0x800D2E4C,D_800D2E70=0x800D2E70,func_1509CCB4=CALLBACK)
LIST,BITS,ALTERNATE,DEPENDENCIES=0x220000,0x240000,0x250000,0x260000

@dataclass(frozen=True)
class Case:
 ids:tuple=(0,1,1,7,8,203)
 state:int=0
 mode:int=0
 index:int=0
 phase:int=0
 alias:int=0

def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-4096,256)}
 put(m,s['D_80087440']+20*c.index,LIST)
 for i,v in enumerate((*c.ids,65535)):put(m,LIST+2*i,v,2)
 if not c.ids:return m
 for v in set((*c.ids,0,1,3,9,11,203,204,65534)):

  if c.alias!=2:m[s['D_800D2E70']+v]=c.state
  for base in (BITS,ALTERNATE):m[base+(v>>3)]=(v*13+0x52)&255
 put(m,s['D_800D2E4C'],BITS)
 if c.alias==1:put(m,s['D_800D2E4C'],LIST+1)
 elif c.alias==2:assert s['D_800D2E70']==LIST+1
 elif c.alias==3:
  put(m,s['D_800D2E4C'],s['D_800D2E4C']);m[0x810D2E4C]=0x52
 elif c.alias==4:
  put(m,s['D_800D2E4C'],s['D_800D2E70']);m[s['D_800D2E70']]=2
 return m

def mutate(m,c,s,key,number):
 if c.mode&1:put(m,s['D_800D2E4C'],ALTERNATE)
 if c.mode&2:put(m,LIST+2*(number-1),9,2)
 if c.mode&4 and number<len(c.ids):put(m,LIST+2*number,11,2)
 if c.mode&8 and number<len(c.ids):put(m,LIST+2*number,65535,2)
 if c.mode&16:m[s['D_800D2E70']+key]=0
 if c.mode&32 and number<len(c.ids):m[s['D_800D2E70']+read(m,LIST+2*number,2)]=3
 if c.mode&64:put(m,s['D_80087440']+20*c.index,LIST+2*len(c.ids))

def reference(initial,c,s=SYMS,connected=False,caller=False):
 m=dict(initial);calls=[];counts={};work=0
 def callback(key,depth=0):
  nonlocal work
  work+=1;assert work<4096 and depth<16,'finite fixture bound'
  calls.append((s['func_1509CCB4'],(key,)))
  counts[key]=counts.get(key,0)+1
  if not connected:mutate(m,c,s,key,sum(counts.values()));return
  p=read(m,s['D_80087440']-4+20*key)
  calls.append((WALK,(p,s['func_1509CCB4'])))
  while read(m,p,2)!=65535:
   callback(read(m,p,2),depth+1)
   m[s['D_800D2E70']+read(m,p,2)]=3
   v=read(m,p,2);at=read(m,s['D_800D2E4C'])+(v>>3);m[at]|=1<<(v&7);p+=2
 def activate(index):
  p=read(m,s['D_80087440']+20*index);count=0;v=read(m,p,2);steps=0
  while v!=65535:
   steps+=1;assert steps<=32,'finite activation fixture'
   at=read(m,s['D_800D2E4C'])+(v>>3);m[at]|=1<<(v&7)
   at=s['D_800D2E70']+read(m,p,2)
   if m[at]!=3:
    m[at]=3;callback(read(m,p,2));count+=1
   p+=2;v=read(m,p,2)
  return count
 if not caller:return m,calls,activate(c.index)
 calls.append((source.ENTRY,(c.index,)));activate(c.index)
 for iteration in range(16):
  changes=0
  for index in range(204):
   if m[s['D_800D2E70']+index]==3:
    calls.append((source.ENTRY,(index,)));changes+=activate(index)
  if not changes:return m,calls,None
 raise AssertionError('finite caller fixture bound')

def public(m):return{a:b for a,b in m.items()if not STACK-4096<=a<STACK+256}

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected=None,fault=None):
  self.c,self.s,self.trace=c,s,[];self.callback_count=0
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.index&0xFFFFFFFF,),connected=connected)
  self.root_fault=fault
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  assert t in(self.s['func_1509CCB4'],WALK,source.ENTRY),(hex(t),'unexpected callback')
  args=self.arguments(2 if t==WALK else 1);self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t==self.s['func_1509CCB4'];self.callback_count+=1;key=self.calls[-1][1][0]
  mutate(self.memory,self.c,self.s,key,self.callback_count)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def linked(obj,label,entry=source.ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>58I',sections(p.with_suffix('.elf'))['.text'][1][:232]))

def images(label,entry=source.ENTRY,s=SYMS):
 result=[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-func_1509CCF4.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_C9EC0.c.o'))]
 assert result[0]==result[2]==result[3]
 assert [i for i,(a,b)in enumerate(zip(result[0],result[1]))if a!=b]==[21,45]
 return result

def compare(words,c,s=SYMS,entry=source.ENTRY,initial=None,connected=None,caller=False):
 initial=fixture(c,s)if initial is None else initial
 want,calls,count=reference(initial,c,s,bool(connected),caller)
 models=[Oracle(w,initial,c,entry,s,connected).run()for w in words]
 for m in models:
  assert public(m.memory)==public(want),(c,'public memory',[(hex(a),v,want.get(a))for a,v in public(m.memory).items()if want.get(a)!=v][:8])
  assert m.calls==calls,(c,'calls',m.calls,calls)
  if not caller:assert m.r[2]==count,(c,'return',m.r[2],count)
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace,(c,'complete trace')
 return models[0]

def guest_suite():
 count=aliases=cuts=delaycuts=0;seen=set()
 patterns=((),(0,),(7,7),(8,0,8),(203,204),(32767,32768,65534),(1,1,1,1),(0,1,7,8,203,65534))
 for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if j==0 else dict(D_80087440=0x81007FFC+j*0x10000,D_800D2E4C=0x82008000+j*0x10000,D_800D2E70=0x8300FFFC+j*0x10000,func_1509CCB4=entry+0x10000)
  words=images('activation-rebase-'+str(j),entry,s)
  for ids,state,mode,phase,index in itertools.product(patterns,(0,3,255),(0,1,2,4,8,16,32,64,127),(0,8),(-1,0,203)):
   c=Case(ids,state,mode,index,phase);m=compare(words,c,s,entry);seen.update(p-entry for p in m.visits if entry<=p<entry+232);count+=1
  if j==0:
   for v in range(204):
    c=Case((v,v),v%4,16 if v%2 else 1,index=v);compare(words,c);count+=1
   for alias,ids,state in ((1,(0,),0),(2,(0,),0),(3,(0,0),0),(4,(0,0),0)):
    a=dict(s)
    if alias==2:a['D_800D2E70']=LIST+1
    aw=words if a==s else images('activation-alias-'+str(alias),entry,a)
    for phase in(0,8):compare(aw,Case(ids,state,phase=phase,alias=alias),a);aliases+=1
   for c in(Case(()),Case((0,),0),Case((0,),3),Case(mode=1),Case(mode=8),Case(phase=8)):
    initial=fixture(c);good=Oracle(words[0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in words:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective dependency access cut')
      models.append(m)
     for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and (m.current_pc,m.delay_of,m.root_accesses)==(models[0].current_pc,models[0].delay_of,models[0].root_accesses)
     cuts+=1;delaycuts+=models[0].delay_of is not None
 assert seen==set(range(0,232,4)),sorted(set(range(0,232,4))-seen)
 return dict(cases=count,executions=4*count,raw_and_guarded_full_trace_equal=True,independent_rebases=3,alias_cases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delaycuts,root_words_visited=len(seen),empty_without_bitset_or_state_reads=True,all_u16_domain_claim=False)

def connected_fixture(c,shape=0,caller=False):
 m=fixture(c);end=LIST+0x100;put(m,end,65535,2);put(m,SYMS['D_800D2E4C'],BITS)
 m.update({SYMS['D_800D2E70']+i:0 for i in range(204)})
 m.update({BITS+i:(i*13+0x52)&255 for i in range(26)})
 for i in range(204):
  a=DEPENDENCIES+i*16
  put(m,SYMS['D_80087440']-4+20*i,a)
  children=()if i>7 or i<1 else ((i-1,)if shape==1 else(i-1,max(0,i-2))if shape==2 else())
  for n,v in enumerate((*children,65535)):put(m,a+2*n,v,2)
  if caller:
   a=LIST+0x200+8*i;put(m,SYMS['D_80087440']+20*i,a)
   for n,v in enumerate(((i-1,65535)if 0<i<=7 else(65535,))):put(m,a+2*n,v,2)
 if caller:m[SYMS['D_800D2E70']+c.index]=3
 for v in c.ids:m[SYMS['D_800D2E70']+v]=c.state
 return m

def original_helpers():
 rom=(o/'before-conker_conker.us.bin').read_bytes();from tools.match_progress import load_elf_functions
 live=load_elf_functions(str(r/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')[0]
 result={}
 for name,va,at,n in(('func_1509CCB4',CALLBACK,0xCA164,16),('func_1509CE64',WALK,0xCA314,49),('func_1509CDDC',CALLER,0xCA28C,34)):
  words=list(struct.unpack_from('>%dI'%n,rom,at));assert live[name]==words,(name,'helper retail identity')
  result[va]=words
 return result

def connected_suite():
 helpers=original_helpers();code={va+i*4:w for va,ws in helpers.items()if va!=CALLER for i,w in enumerate(ws)};words=images('activation-connected');seen=set();count=0
 for ids,state,shape,phase in itertools.product(((),(0,),(1,1),(7,6,3,7)),(0,3,255),(0,1,2),(0,8)):
  c=Case(ids,state,phase=phase);m=compare(words,c,initial=connected_fixture(c,shape),connected=code);seen.update(m.visits);count+=1
 return dict(cases=count,executions=4*count,original_connected_words=65,wrapper_words_visited=sum(CALLBACK+i*4 in seen for i in range(16)),walker_words_visited=sum(WALK+i*4 in seen for i in range(49)),finite_acyclic_fixture_depth_bound=16,general_cycle_claim=False)

def caller_suite():
 helpers=original_helpers();rom=(o/'before-conker_conker.us.bin').read_bytes();target=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
 sites=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==target];pointers=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
 assert sites==[0xCA2A8,0xCA2D4] and pointers==[],(sites,pointers)
 roots=images('activation-caller');count=0;seen=set()
 for index,shape,phase in itertools.product((0,1,7),(0,1,2),(0,8)):
  c=Case((),0,index=index,phase=phase);initial=connected_fixture(c,shape,True);want,calls,_=reference(initial,c,connected=True,caller=True);models=[]
  for root in roots:
   code={source.ENTRY+i*4:w for i,w in enumerate(root)}
   code.update({va+i*4:w for va,ws in helpers.items()if va!=CALLER for i,w in enumerate(ws)})
   m=Oracle(helpers[CALLER],initial,c,CALLER,connected=code).run();assert public(m.memory)==public(want)and m.calls==calls,(index,shape,'caller result');models.append(m);seen.update(m.visits)
  for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
  count+=1
 return dict(cases=count,executions=4*count,aligned_ROM_JAL_sites=sites,aligned_ROM_pointer_sites=pointers,original_caller_words=34,caller_words_visited=sum(CALLER+i*4 in seen for i in range(34)),full204_record_fixed_point_scan=True,finite_acyclic_fixtures=True)

def native_harness(body):
 return source.HEADERS+r'''
typedef char row_stride_is_twenty[sizeof(DependencyActivationRow)==20?1:-1];
typedef char pointer_is_four[sizeof(void *)==4?1:-1];
DependencyActivationRow D_80087440[205];
u8 D_800D2E70[65538], *D_800D2E4C;
static u8 expectedState[65538],banks[2][8194],expectedBanks[2][8194];
static u16 list[10],expectedList[10],empty[1]={65535};
static u32 logActual[10],logExpected[10];
static int calls,expectedCalls,mode,length,selected,indexNow,previous;
static void effect(u32 key,int n,int expected) {
 u16 *items=expected?expectedList:list;
 u8 *states=expected?expectedState:D_800D2E70;
 if(mode&1) {if(expected)selected=1;else D_800D2E4C=banks[1]+1;}
 if(mode&2) items[n-1]=9;
 if((mode&4)&&n<length) items[n]=11;
 if((mode&8)&&n<length) items[n]=65535;
 if(mode&16)states[key]=0;
 if((mode&32)&&n<length)states[items[n]]=3;
 if((mode&64)&&!expected)D_80087440[indexNow].entries=list+length;
}
void func_1509CCB4(s32 key) {
 if(calls>=9)__builtin_trap();
 logActual[calls++]=(u32)key;effect((u32)key,calls,0);
}
''' + body+r'''
static int reference(void) {
 int pos=0,count=0;u32 resource;
 while((resource=expectedList[pos])!=65535) {
  expectedBanks[selected][1+(resource>>3)]|=(u8)(1u<<(resource&7));
  resource=expectedList[pos];
  if(expectedState[resource]!=3) {
   expectedState[resource]=3;resource=expectedList[pos];
   logExpected[expectedCalls++]=resource;effect(resource,expectedCalls,1);count++;
  }
  pos++;
 }
 return count;
}
static int one(u32 id,int state,int m,int isEmpty) {
 u32 keys[12]={id,0,1,7,8,9,11,203,204,32767,32768,65534};
 int i,j,a,b;
 mode=m;length=isEmpty?0:5;calls=expectedCalls=selected=0;
 D_800D2E4C=banks[0]+1;
 D_80087440[previous].entries=empty;indexNow=(int)(id%204);
 D_80087440[indexNow].entries=list;previous=indexNow;
 for(i=0;i<10;i++)list[i]=expectedList[i]=65535;
 if(!isEmpty) {
  list[0]=expectedList[0]=(u16)id;list[1]=expectedList[1]=(u16)id;
  list[2]=expectedList[2]=0;list[3]=expectedList[3]=203;list[4]=expectedList[4]=8;
 }
 for(i=0;i<12;i++) {
  u32 v=keys[i];D_800D2E70[v]=expectedState[v]=(u8)state;
  for(j=0;j<2;j++)banks[j][1+(v>>3)]=expectedBanks[j][1+(v>>3)]=(u8)(0x52+13*(v>>3));
 }
 a=func_1509CCF4(indexNow);b=reference();
 if(a!=b||calls!=expectedCalls||(D_800D2E4C==banks[1]+1)!=(selected==1))return 1;
 for(i=0;i<calls;i++)if(logActual[i]!=logExpected[i])return 1;
 for(i=0;i<10;i++)if(list[i]!=expectedList[i])return 1;
 for(i=0;i<12;i++) {
  u32 v=keys[i];if(D_800D2E70[v]!=expectedState[v])return 1;
  for(j=0;j<2;j++)if(banks[j][1+(v>>3)]!=expectedBanks[j][1+(v>>3)])return 1;
 }
 for(j=0;j<2;j++)if(banks[j][0]!=0xD3||banks[j][8193]!=0xD3)return 1;
 if(D_800D2E70[65536]!=0xD3||D_800D2E70[65537]!=0xD3)return 1;
 return 0;
}
static int run(void) {
 u32 id;int i,j,p;static const int states[4]={0,1,3,255};
 for(i=0;i<205;i++)D_80087440[i].entries=empty;
 for(i=0;i<65538;i++)D_800D2E70[i]=expectedState[i]=0xD3;
 for(j=0;j<2;j++)for(i=0;i<8194;i++)banks[j][i]=expectedBanks[j][i]=0xD3;
 for(id=0;id<65535;id++)for(p=0;p<4;p++)if(one(id,states[p],(int)((id*5+(u32)p*31)&127),0))return 1;
 for(p=0;p<128;p++)if(one((u32)p,states[p%4],p,1))return 1;
 for(i=0;i<65538;i++)if(D_800D2E70[i]!=expectedState[i])return 1;
 for(j=0;j<2;j++)for(i=0;i<8194;i++)if(banks[j][i]!=expectedBanks[j][i])return 1;
 return 0;
}
''' + START

def native_controls():
 s=source.SELECTED
 result={
  'wrong_bit_byte':s.replace('resource >> 3','resource >> 4'),
  'wrong_bit_mask':s.replace('resource & 7','resource & 6'),
  'toggle_instead_of_set':s.replace('|=','^='),
  'inverted_state_gate':s.replace('!= 3','== 3'),
  'wrong_active_state':s.replace('D_800D2E70[*entry] = 3','D_800D2E70[*entry] = 2'),
  'skipped_callback':s.replace('func_1509CCB4(*entry);',';'),
  'wrong_callback_argument':s.replace('func_1509CCB4(*entry);','func_1509CCB4(*entry + 1);'),
  'double_count':s.replace('count++;','count += 2;'),
  'zero_return':s.replace('return count;','return 0;'),
  'wrong_table_row':s.replace('D_80087440[index].entries','D_80087440[index+1].entries'),
  'zero_terminates':s.replace('if ((resource = *entry) != 0xFFFF)','if ((resource = *entry) != 0xFFFF && resource != 0)'),
  'skip_active_bit':s.replace('D_800D2E4C[resource >> 3] |= 1 << (resource & 7);','if (D_800D2E70[resource] != 3) D_800D2E4C[resource >> 3] |= 1 << (resource & 7);'),
  'stale_bitset_pointer':s.replace('s32 resource;','s32 resource; u8 *captured = D_800D2E4C;').replace('D_800D2E4C[resource >> 3]','captured[resource >> 3]'),
  'stale_next_entry':s.replace('s32 resource;','s32 resource; s32 next;').replace('do {','do { next = entry[1];').replace('resource = *++entry;','entry++; resource = next;'),
  'count_every_entry':s.replace('count++;',';').replace('resource = *++entry;','count++; resource = *++entry;'),
 }
 assert len(result)==15 and all(v!=s for v in result.values())
 return result

def native_suite():
 results=[]
 for label,body in [('positive',source.SELECTED),*native_controls().items()]:
  unit=o/('native-activation-'+label+'.c');unit.write_text(native_harness(body))
  for opt in('O0','O2','O3')if label=='positive'else('O2',):
   exe=o/('native-activation-'+label+'-'+opt)
   q=subprocess.run([*native_command('-'+opt,True),'-mstackrealign','-fno-builtin',str(unit),'-o',str(exe)],cwd=r,capture_output=True,text=True)
   assert q.returncode==0,(label,opt,q.stderr)
   q=subprocess.run([str(exe)],capture_output=True,timeout=60)
   assert q.returncode==(0 if label=='positive'else 1),(label,opt,q.returncode,q.stderr)
   results.append((label,opt,q.returncode))
 return dict(profiles=['O0','O2','O3'],positive_cases_each=65535*4+128,all65535_non_sentinel_IDs=True,all128_callback_mutation_modes=True,effective_controls=15,controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,table_stride=20,disjoint_typed_objects=True,portable_alias_claim=False)
