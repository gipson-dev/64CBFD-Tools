"""Live table/count dispatch with bounded mutating helpers and original caller."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-live-record-dispatch-match';F='func_150A278C';ENTRY=0x150A278C;ACTOR=0x20000;A=0x30000;B=0x50000;MARK=0x70000;CAPACITY=8
SYMS=dict(func_150A1DA0=0x150A1DA0,func_15172E7C=0x15172E7C,D_800D3094=0x800D3094,D_800D3098=0x800D3098)
@dataclass(frozen=True)
class Case:
 disabled:int=0
 count:int=4
 pattern:int=0
 result_pattern:int=0
 mutation:int=0
 phase:int=0
 flag:int=-1
def flag(c,i,pool):
 if c.flag>=0:return c.flag
 i=(i+pool)%8
 if c.pattern==0:return 0x20+(i&3)
 if c.pattern==1:return 0x20 if i%2==0 else 0x24
 if c.pattern==2:return(0,0x1F,0x24,255)[i%4]
 return(0x23,0x60,0x21,0xA0,0x20,0x22,0x1F,0x24)[i]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)};m.update({ACTOR+i:(i*29+0x59)&255 for i in range(512)});m[ACTOR+101]=c.disabled
 for pool,base in enumerate((A,B)):
  m.update({base+i:(i*13+pool*17+0x33)&255 for i in range(CAPACITY*52)})
  for i in range(CAPACITY):p=base+52*i;m[p+21]=flag(c,i,pool);m[p+23]=(i*73+pool*17+128)&255;put(m,p+24,(0x80000001^(i*0x1020304)^(pool*0x55667788))&0xFFFFFFFF)
 put(m,s['D_800D3094'],c.count);put(m,s['D_800D3098'],A);put(m,MARK,0);return m
def where(entry):
 found=[(pool,(entry-base)//52)for pool,base in enumerate((A,B))if base<=entry<base+52*CAPACITY and(entry-base)%52==0];assert len(found)==1,hex(entry);return found[0]
def query_value(c,index):return(0,1,index&1,0x80000001 if index==1 else 0)[c.result_pattern]
def effects(m,c,query,ordinal,index,q,d,s=SYMS,entry=None):
 if query:
  if c.mutation==1:put(m,s['D_800D3094'],0)
  elif c.mutation==2:put(m,s['D_800D3098'],B if read(m,s['D_800D3098'])==A else A)
  elif c.mutation==3 and ordinal==1:put(m,s['D_800D3094'],min(read(m,s['D_800D3094'])+2,6));m[ACTOR+101]=1
  elif c.mutation==5:
   m[entry+23]^=0x80;put(m,entry+24,read(m,entry+24)^0xA5A5A5A5)
   if index+1<CAPACITY:m[entry+52+21]=0x20
 else:
  if c.mutation==4:put(m,s['D_800D3094'],0)
  elif c.mutation==6 and ordinal==1:
   put(m,s['D_800D3094'],min(read(m,s['D_800D3094'])+1,6));p=B if read(m,s['D_800D3098'])==A else A;put(m,s['D_800D3098'],p);m[ACTOR+101]=1
   if index+1<CAPACITY:m[p+(index+1)*52+21]=0x21
 put(m,MARK,(q<<16)|d)
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];q=d=0
 if not m[ACTOR+101]:
  index=0
  while index<read(m,s['D_800D3094']):
   assert index<CAPACITY,('Unbounded fixture',c,index);entry=read(m,s['D_800D3098'])+index*52
   if m[entry+21]>>2==8:
    calls.append((s['func_150A1DA0'],(ACTOR,entry,0)));q+=1;effects(m,c,True,q,index,q,d,s,entry)
    if query_value(c,index)==0:
     entry=read(m,s['D_800D3098'])+index*52;calls.append((s['func_15172E7C'],(ACTOR,m[entry+23],read(m,entry+24))));d+=1;effects(m,c,False,d,index,q,d,s,entry)
   index+=1
 return m,calls
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.q=self.d=0;self.last_index=0;super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,))
 def record_call(self,t):
  assert t in(*[self.syms[n]for n in('func_150A1DA0','func_15172E7C')],ENTRY);n=1 if t==ENTRY else 3;a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1];assert self.r[29]==STACK+c.phase-48
  for reg,offset in((16,20),(17,24),(18,28),(19,32),(20,36),(21,40),(31,44)):assert read(self.memory,self.r[29]+offset)==(getattr(self,'expected_target_ra',self.before[31])if reg==31 else self.before[reg])
  if t==s['func_150A1DA0']:
   pool,index=where(a[1]);self.last_index=index;self.q+=1;effects(self.memory,c,True,self.q,index,self.q,self.d,s,a[1]);value=query_value(c,index)
  else:assert t==s['func_15172E7C'];self.d+=1;effects(self.memory,c,False,self.d,self.last_index,self.q,self.d,s);value=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.o').with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def cases():
 for a in itertools.product((0,1,255),(0,1,2,4,6),range(4),range(4),range(7),(0,8)):yield Case(*a)
 for byte,phase in itertools.product(range(256),(0,8)):yield Case(count=1,flag=byte,phase=phase)
 for count,disabled,phase in itertools.product((0x80000000,0xFFFFFFFF),(0,255),(0,8)):yield Case(count=count,disabled=disabled,mutation=1,phase=phase)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.q,m.d)
def verify(m,initial,c,s=SYMS):
 want,calls=reference(initial,c,s);assert(public(m.memory),m.calls)==(public(want),calls),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+216,4));print(dict(cases=count,covered_words=len(visited)),flush=True);total_cases=count
 prefixes=0
 for c in(Case(disabled=255),Case(count=0),Case(count=2,pattern=2),Case(count=2,mutation=2),Case(count=4,mutation=1,phase=8),Case(count=1,mutation=3)):
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
 for c in(Case(disabled=255),Case(count=0)):
  initial={STACK+i:(i*17+0xA5)&255 for i in range(-128,128)};initial[ACTOR+101]=c.disabled
  if not c.disabled:put(initial,SYMS['D_800D3094'],0)
  for words in programs:m=Oracle(words,initial,c).run();assert m.calls==[];sparse+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(func_150A1DA0=0x10007FF0+k*0x10000,func_15172E7C=0x10008000+k*0x10000,D_800D3094=0x80007FF0+k*0x100000,D_800D3098=0x80018000+k*0x100000);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)]
  for count,mu,result,phase in itertools.product((0,2,4),(0,2,3,4,5,6),(0,1),(0,8)):
   c=Case(count=count,mutation=mu,result_pattern=result,phase=phase);initial=fixture(c,s)
   for words in ps:verify(Oracle(words,initial,c,s,entry).run(),initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>3I',rom,0x77EC4));caller_count=0
 for disabled,count,mu,phase in itertools.product((0,1),(0,2,4),(0,2,3,4,5,6),(0,8)):
  c=Case(disabled=disabled,count=count,mutation=mu,phase=phase);initial=fixture(c);want,calls=reference(initial,c)
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));code[0x1504AA20]=0;m=Oracle(window,initial,c,entry=0x1504AA14,connected=code);m.r[16]=ACTOR;m.before=m.r[:];m.expected_target_ra=0x1504AA1C;m.code=WindowCode(m.code,m);m.code.ends=(0x1504AA20,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(public(m.memory),m.calls,m.r[24])==(public(want),[(ENTRY,(ACTOR,))]+calls,read(initial,ACTOR+0x184))
  caller_count+=1
 q=dict(private_only=True,installed=False,matching_credit=0,cases=total_cases,executions=total_cases*3,covered_words=54,frame=48,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,all_256_flag_values=True,live_count_and_base_mutations=True,actor_gate_not_rechecked=True,unsigned_high_count_terminates_via_helper=True,providers_bounded=True,access_prefix_pairs=prefixes,sparse_executions=sparse,rebase_layouts=3,rebase_cases=rebased,original_caller_windows=[dict(entry='0x1504AA14',ROM='0x77EC4',words=3,cases=caller_count,result_ignored=True,complete_parent_claimed=False)],complete_query_or_dispatch_or_parent_claimed=False)
 return q


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_150A278C';prefix=selected[:selected.index('/* Dispatch')];body=selected[selected.index('/* Dispatch'):]
 mutants=dict(inverted_gate=body.replace('[0x65] == 0','[0x65] != 0'),wrong_flags=body.replace('(D_800D3098[index].flags >> 2) == 8','(D_800D3098[index].flags & 0x20) != 0'),inverted_query=body.replace('(s32)&D_800D3098[index], 0) == 0','(s32)&D_800D3098[index], 0) != 0'),cached_count=body.replace('u32 index;','u32 index;\n    u32 cachedCount = (u32)D_800D3094;').replace('index < (u32)D_800D3094','index < cachedCount'),cached_base=body.replace('u32 index;','u32 index;\n    GeneratedCDE80Record *cachedBase = D_800D3098;').replace('D_800D3098[index]','cachedBase[index]'),rechecked_gate=body.replace('index < (u32)D_800D3094','index < (u32)D_800D3094 && ((u8 *)actor)[0x65] == 0'),wrong_record=body.replace('D_800D3098[index]','D_800D3098[index + 1]'),wrong_payload=body.replace('D_800D3098[index].field18','D_800D3098[index].field1C'))
 assert all(v!=body for v in mutants.values())
 def hashbytes(seq):
  h=2166136261
  for x in seq:h=((h^x)*16777619)&0xFFFFFFFF
  return h
 text=prefix+r'''
 typedef struct{u32 disabled,count,pattern,result,mutation,flag,wantCount,wantPool,wantGate,wantMarker,hashA,hashB,traceHash,queries,dispatches;} Fixture;
 static const Fixture*current;static u8 actorBytes[512] __attribute__((aligned(8)));static GeneratedCDE80Record pools[2][8];GeneratedCDE80Record*D_800D3098;s32 D_800D3094;
 static u32 queries,dispatches,lastIndex,badArgs,marker,traceHash;
 static void traceWord(u32 v){s32 j;for(j=24;j>=0;j-=8)traceHash=(traceHash^((v>>j)&255u))*16777619u;}
 static u32 byteHash(const u8*p,u32 n){u32 h=2166136261u,i;for(i=0;i<n;i++)h=(h^((i%52>=24&&i%52<28)?((*(const u32*)(p+i-i%52+24)>>(24-8*(i%52-24)))&255u):p[i]))*16777619u;return h;}
 static u32 flags(u32 i,u32 pool){static const u8 rejected[]={0,31,36,255},mixed[]={35,96,33,160,32,34,31,36};if(current->flag!=0xFFFFFFFFu)return current->flag;i=(i+pool)%8;if(current->pattern==0)return 32+(i&3);if(current->pattern==1)return i%2==0?32:36;if(current->pattern==2)return rejected[i%4];return mixed[i];}
 static void effect(s32 query,u32 ordinal,u32 index,GeneratedCDE80Record*entry){u32 mode=current->mutation;u8*actor=actorBytes;
  if(query){if(mode==1)D_800D3094=0;else if(mode==2)D_800D3098=D_800D3098==pools[0]?pools[1]:pools[0];else if(mode==3&&ordinal==1){D_800D3094=(u32)D_800D3094+2>6?6:D_800D3094+2;actor[101]=1;}else if(mode==5){entry->field17^=128;entry->field18=(s32)((u32)entry->field18^0xA5A5A5A5u);if(index+1<8)(entry+1)->flags=32;}}
  else{if(mode==4)D_800D3094=0;else if(mode==6&&ordinal==1){D_800D3094=(u32)D_800D3094+1>6?6:D_800D3094+1;D_800D3098=D_800D3098==pools[0]?pools[1]:pools[0];actor[101]=1;if(index+1<8)D_800D3098[index+1].flags=33;}}
  marker=(queries<<16)|dispatches;
 }
 s32 func_150A1DA0(struct127*actor,s32 handle,s32 zero){GeneratedCDE80Record*entry=(GeneratedCDE80Record*)handle;u32 pool,index;if((u8*)actor!=actorBytes||zero)badArgs=1;
  if((u32)entry>=(u32)pools[0]&&(u32)entry<(u32)(pools[0]+8))pool=0;else if((u32)entry>=(u32)pools[1]&&(u32)entry<(u32)(pools[1]+8))pool=1;else{badArgs=1;return 1;}
  index=((u32)entry-(u32)pools[pool])/52;lastIndex=index;traceWord(1);traceWord(pool);traceWord(index);queries++;effect(1,queries,index,entry);
  if(current->result==0)return 0;if(current->result==1)return 1;if(current->result==2)return index&1;return index==1?(s32)0x80000001u:0;
 }
 s32 func_15172E7C(struct127*actor,u8 selector,s32 payload){if((u8*)actor!=actorBytes)badArgs=1;traceWord(2);traceWord(selector);traceWord((u32)payload);dispatches++;effect(0,dispatches,lastIndex,0);return(s32)0xDEADBEEFu;}
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());cases=[c for c in q.cases()if c.phase==0];rows=[]
 for c in cases:
  initial=q.fixture(c);want,calls=q.reference(initial,c);trace=[];nq=nd=0
  for target,args in calls:
   if target==q.SYMS['func_150A1DA0']:pool,index=q.where(args[1]);words=(1,pool,index);nq+=1
   else:words=(2,args[1],args[2]);nd+=1
   for word in words:trace.extend(word.to_bytes(4,'big'))
  rows.append((c.disabled,c.count,c.pattern,c.result_pattern,c.mutation,c.flag&0xFFFFFFFF,q.read(want,q.SYMS['D_800D3094']),int(q.read(want,q.SYMS['D_800D3098'])==q.B),want[q.ACTOR+101],q.read(want,q.MARK),hashbytes(want[q.A+i]for i in range(416)),hashbytes(want[q.B+i]for i in range(416)),hashbytes(trace),nq,nd))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+','.join('0x%08Xu'%x for x in row)+'}'for row in rows)+'\n};\n'
 text+=r'''
 typedef void(*Fn)(struct127*);
 static s32 check(Fn fn,s32 control){u32 n,i,p;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;current=c;if(control&&c->count>8)continue;
  for(i=0;i<512;i++)actorBytes[i]=(u8)(i*29+0x59);actorBytes[101]=(u8)c->disabled;
  for(p=0;p<2;p++){u8*bytes=(u8*)pools[p];for(i=0;i<416;i++)bytes[i]=(u8)(i*13+p*17+0x33);for(i=0;i<8;i++){pools[p][i].flags=(u8)flags(i,p);pools[p][i].field17=(u8)(i*73+p*17+128);pools[p][i].field18=(s32)(0x80000001u^(i*0x1020304u)^(p*0x55667788u));}}
  D_800D3098=pools[0];D_800D3094=(s32)c->count;queries=dispatches=badArgs=marker=lastIndex=0;traceHash=2166136261u;fn((struct127*)actorBytes);
  if(badArgs||(u32)D_800D3094!=c->wantCount||D_800D3098!=pools[c->wantPool]||actorBytes[101]!=c->wantGate||marker!=c->wantMarker||queries!=c->queries||dispatches!=c->dispatches||traceHash!=c->traceHash)return 1;
  if(byteHash((u8*)pools[0],416)!=c->hashA||byteHash((u8*)pools[1],416)!=c->hashB)return 2;
  for(i=0;i<512;i++)if(i!=101&&actorBytes[i]!=(u8)(i*29+0x59))return 3;
  }return 0;}
 static int run(void){if(sizeof(void*)!=4||sizeof(GeneratedCDE80Record)!=52)return 90;{s32 result=check(test_selected,0);if(result)return 10+result;}
 '''.replace('CASE_COUNT',str(len(cases)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+',1))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
