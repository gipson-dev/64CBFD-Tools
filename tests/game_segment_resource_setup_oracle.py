"""Three live resource selections, segment stores, aliases and caller forwarding."""
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
r=Path.cwd();o=r/'conker/build/game-segment-resource-setup-match';F='func_150DFBD0';ENTRY=0x150DFBD0;OUTPUT=0x20000;MARK=0x70000;N=265
SYMS=dict(func_150DF8C0=0x150DF8C0,func_1510D0EC=0x1510D0EC,D_80090324=0x80090324,D_800DD405=0x800DD405)
@dataclass(frozen=True)
class Case:
 mask:int=7
 variant:int=0
 mutation:int=0
 alias:int=0
 result:int=1
 phase:int=0
def destination(c,s=SYMS):return(OUTPUT,s['D_80090324']+32,s['D_80090324']+40)[c.alias]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)};m.update({OUTPUT+i:(i*29+0x59)&255 for i in range(64)});m[s['D_800DD405']]=c.variant
 for i in range(N):put(m,s['D_80090324']+i*4,(0x80000001^(i*0x1020304))&0xFFFFFFFF)
 put(m,MARK,0);return m
def effects(m,c,query,index,q,d,s=SYMS):
 variant=s['D_800DD405'];table=s['D_80090324']
 if query:
  if c.mutation==1:m[variant]=(m[variant]+1)&255
  if c.mutation==3:put(m,table+32,0xF0000000|index);put(m,table+(m[variant]+9)*4,0xE0000000|index)
 else:
  if c.mutation==2:m[variant]=(m[variant]+3)&255
  if c.mutation==4:put(m,table+32,0xD0000000|index);put(m,table+(m[variant]+9)*4,0xC0000000|index)
 put(m,MARK,(q<<16)|d)
def query_value(c,i):return(0x80000001 if c.result==2 else 1)if c.mask&(1<<i)else 0
def loaded(c,index,resource):return(0,(0x12345678+index*0x1020304)&0xFFFFFFFF,resource^0x80000000)[c.result]
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];out=destination(c,s);local=STACK+c.phase-16
 for i in range(3):
  calls.append((s['func_150DF8C0'],(i,)));effects(m,c,True,i,i+1,i,s)
  offset=m[s['D_800DD405']]+9 if query_value(c,i)else 8;resource=read(m,s['D_80090324']+offset*4);calls.append((s['func_1510D0EC'],(resource,local,3,0)));effects(m,c,False,i,i+1,i+1,s);put(m,local,resource^0xA5A5A5A5);put(m,out+8*i,0xDB060000|(i+2)*4);put(m,out+8*i+4,loaded(c,i,resource))
 return m,calls,out+24
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.q=self.d=0;super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(destination(c,s),))
 def record_call(self,t):
  assert t in(self.syms['func_150DF8C0'],self.syms['func_1510D0EC'],ENTRY);n=4 if t==self.syms['func_1510D0EC']else 1;a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1];assert self.r[29]==STACK+c.phase-88
  for reg,slot in((*[(i,20+(i-16)*4)for i in range(16,24)],(31,52))):assert read(self.memory,self.r[29]+slot)==(getattr(self,'expected_target_ra',self.before[31])if reg==31 else self.before[reg])
  if t==s['func_150DF8C0']:index=self.q;assert a==(index,);self.q+=1;effects(self.memory,c,True,index,self.q,self.d,s);value=query_value(c,index)
  else:
   assert t==s['func_1510D0EC'];index=self.d;assert a[1:]==(STACK+c.phase-16,3,0);self.d+=1;effects(self.memory,c,False,index,self.q,self.d,s);self.put(a[1],a[0]^0xA5A5A5A5,4);value=loaded(c,index,a[0])
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>54I',sections(p.with_suffix('.elf'))['.text'][1][:216]))
def cases():
 for args in itertools.product(range(8),(0,1,7,127,255),range(5),range(3),range(3),(0,8)):yield Case(*args)
 for variant,phase in itertools.product(range(256),(0,8)):yield Case(variant=variant,phase=phase)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.q,m.d)
def verify(m,initial,c,s=SYMS):
 want,calls,result=reference(initial,c,s);assert(public(m.memory),m.calls,m.r[2])==(public(want),calls,result),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];case_count=0;visited=set()
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);case_count+=1
 assert visited==set(range(ENTRY,ENTRY+216,4));prefixes=0
 for c in(Case(mask=0),Case(mask=7,mutation=1),Case(mask=5,mutation=3,alias=1,phase=8),Case(mask=2,mutation=4,alias=2)):
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
 for c in(Case(mask=0),Case(mask=7)):
  initial=fixture(c)
  initial={a:b for a,b in initial.items()if not SYMS['D_80090324']<=a<SYMS['D_80090324']+N*4 or SYMS['D_80090324']+(8 if c.mask==0 else 9)*4<=a<SYMS['D_80090324']+(9 if c.mask==0 else 10)*4}
  if c.mask==0:initial.pop(SYMS['D_800DD405'])
  for words in programs:m=Oracle(words,initial,c).run();assert m.r[2]==OUTPUT+24;sparse+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(func_150DF8C0=0x10007FF0+k*0x10000,func_1510D0EC=0x10008000+k*0x10000,D_80090324=0x80007FF0+k*0x100000,D_800DD405=0x80018000+k*0x100000);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)]
  for mask,mu,alias,phase in itertools.product(range(8),(0,1,4),(0,1),(0,8)):
   c=Case(mask=mask,mutation=mu,alias=alias,phase=phase);initial=fixture(c,s)
   for words in ps:verify(Oracle(words,initial,c,s,entry).run(),initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>4I',rom,0x13901C));caller_count=0
 for mask,mu,alias,phase in itertools.product(range(8),(0,2,3),range(3),(0,8)):
  c=Case(mask=mask,mutation=mu,alias=alias,phase=phase);initial=fixture(c);want,calls,result=reference(initial,c)
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+216,4),words));code[0x1510BB98]=0;m=Oracle(window,initial,c,entry=0x1510BB6C,connected=code);m.r[16]=destination(c);m.before=m.r[:];m.expected_target_ra=0x1510BB74;m.code=WindowCode(m.code,m);m.code.ends=(0x1510BB98,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(public(m.memory),m.calls,m.r[16])==(public(want),[(ENTRY,(destination(c),))]+calls,result)
  caller_count+=1
 report=dict(private_only=True,installed=False,matching_credit=0,cases=case_count,executions=case_count*3,covered_words=54,frame=88,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,all_256_variant_values=True,live_variant_and_table_mutations=True,aliased_command_and_resource_table=True,providers_bounded=True,access_prefix_pairs=prefixes,sparse_executions=sparse,rebase_layouts=3,rebase_cases=rebased,original_caller_windows=[dict(entry='0x1510BB6C',ROM='0x13901C',words=4,cases=caller_count,result_forwarded=True,complete_parent_claimed=False)],complete_activity_or_loader_or_parent_claimed=False)
 return report


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_150DFBD0';prefix=selected[:selected.index('/* Load')];body=selected[selected.index('/* Load'):]
 mutants=dict(wrong_query=body.replace('func_150DF8C0(index)','func_150DF8C0(index + 1)'),inverted_activity=body.replace('if (address)','if (!address)'),cached_variant=body.replace('s32 index;','s32 index;\n    u32 cachedVariant = D_800DD405;').replace('address = D_800DD405;','address = cachedVariant;'),wrong_default=body.replace('D_80090324[8]','D_80090324[7]'),wrong_selected=body.replace('D_80090324[address + 9]','D_80090324[address + 8]'),wrong_segment=body.replace('index + 2, address','index + 1, address'),wrong_payload=body.replace('index + 2, address','index + 2, address + 1'),wrong_return=body.replace('return cursor;','return cursor - 1;'));assert all(v!=body for v in mutants.values())
 def hashbytes(seq):
  h=2166136261
  for x in seq:h=((h^x)*16777619)&0xFFFFFFFF
  return h
 text=prefix+r'''
 typedef struct{u32 mask,variant,mutation,alias,result,wantVariant,wantMarker,tableHash,outputHash,traceHash;} Fixture;
 static const Fixture*current;u8 D_800DD405;s32 D_80090324[265] __attribute__((aligned(8)));static u8 output[64] __attribute__((aligned(8)));static u32 queries,loads,badArgs,marker,traceHash;static s32*extentPointer;
 static void traceWord(u32 v){s32 j;for(j=24;j>=0;j-=8)traceHash=(traceHash^((v>>j)&255u))*16777619u;}
 static void effect(s32 query,u32 index){u32 mode=current->mutation;if(query){if(mode==1)D_800DD405++;if(mode==3){D_80090324[8]=(s32)(0xF0000000u|index);D_80090324[D_800DD405+9]=(s32)(0xE0000000u|index);}}else{if(mode==2)D_800DD405+=3;if(mode==4){D_80090324[8]=(s32)(0xD0000000u|index);D_80090324[D_800DD405+9]=(s32)(0xC0000000u|index);}}marker=(queries<<16)|loads;}
 s32 func_150DF8C0(s32 index){u32 n=queries++;if((u32)index!=n)badArgs=1;traceWord(1);traceWord((u32)index);effect(1,n);return current->mask&(1u<<n)?(current->result==2?(s32)0x80000001u:1):0;}
 u32 func_1510D0EC(s32 resource,s32*extent,s32 priority,s32 retain){u32 n=loads++;if(!extent||((u32)extent&3)||priority!=3||retain||(n&&extentPointer!=extent))badArgs=1;extentPointer=extent;traceWord(2);traceWord((u32)resource);traceWord((u32)priority);traceWord((u32)retain);effect(0,n);*extent=(s32)((u32)resource^0xA5A5A5A5u);return current->result==0?0:current->result==1?0x12345678u+n*0x1020304u:(u32)resource^0x80000000u;}
 static u32 hashTable(void){u32 h=2166136261u,i; s32 j;for(i=0;i<265;i++)for(j=24;j>=0;j-=8)h=(h^(((u32)D_80090324[i]>>j)&255u))*16777619u;return h;}
 static u32 hashOutput(void){u32 h=2166136261u,i;for(i=0;i<64;i++){u32 v=i<24?(*(u32*)(output+(i&~3u))>>(24-8*(i&3)))&255u:output[i];h=(h^v)*16777619u;}return h;}
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());cases=[c for c in q.cases()if c.phase==0];rows=[]
 for c in cases:
  initial=q.fixture(c);want,calls,result=q.reference(initial,c);trace=[]
  for target,args in calls:
   words=(1,args[0])if target==q.SYMS['func_150DF8C0']else(2,args[0],args[2],args[3])
   for word in words:trace.extend(word.to_bytes(4,'big'))
  rows.append((c.mask,c.variant,c.mutation,c.alias,c.result,want[q.SYMS['D_800DD405']],q.read(want,q.MARK),hashbytes(want[q.SYMS['D_80090324']+i]for i in range(q.N*4)),hashbytes(want[q.OUTPUT+i]for i in range(64)),hashbytes(trace)))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+','.join('0x%08Xu'%x for x in row)+'}'for row in rows)+'\n};\n'
 text+=r'''
 typedef Gfx*(*Fn)(Gfx*);
 static s32 check(Fn fn){u32 n,i;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;Gfx*cursor,*result;current=c;for(i=0;i<265;i++)D_80090324[i]=(s32)(0x80000001u^(i*0x1020304u));for(i=0;i<64;i++)output[i]=(u8)(i*29+0x59);D_800DD405=(u8)c->variant;queries=loads=badArgs=marker=0;extentPointer=0;traceHash=2166136261u;cursor=c->alias==0?(Gfx*)output:(Gfx*)(D_80090324+(c->alias==1?8:10));result=fn(cursor);
  if(badArgs||queries!=3||loads!=3||D_800DD405!=c->wantVariant||marker!=c->wantMarker||traceHash!=c->traceHash||result!=cursor+3)return 1;
  if(hashTable()!=c->tableHash)return 2;
  if(c->alias==0){if(hashOutput()!=c->outputHash)return 3;}else for(i=0;i<64;i++)if(output[i]!=(u8)(i*29+0x59))return 4;
  }return 0;}
 static int run(void){if(sizeof(void*)!=4||sizeof(Gfx)!=8)return 90;{s32 result=check(test_selected);if(result)return 10+result;}
 '''.replace('CASE_COUNT',str(len(cases)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
