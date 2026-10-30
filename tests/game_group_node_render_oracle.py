"""Actor-group renderer: saved-next traversal, live group, cursor and five-argument calls."""
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
r=Path.cwd();o=r/'conker/build/game-group-node-render-match';F='func_15030F94';ENTRY=0x15030F94;BODY=220;ACTOR=0x20000;NODES=0x30000;MARK=0x70000
SYMS=dict(D_800C3EE0=0x800C3EE0,func_150311C4=0x150311C4)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 present:int=1
 resource:int=1
 group:int=3
 length:int=6
 pattern:int=63
 enabled:int=1
 mutation:int=0
 phase:int=0
 cursor:int=0x50000
 view:int=0x80000001
 mode:int=0xFFFFFFFF
 alias:int=0
def actor(c):return 0 if not c.present else ACTOR if not c.alias else NODES+(c.alias-1)*256
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,512)};m.update({ACTOR+i:(i*29+0x59)&255 for i in range(512)})
 for j in range(6):
  base=NODES+j*256;m.update({base+i:(i*13+j*31+0x21)&255 for i in range(512)});m[base]=c.group if c.pattern>>j&1 else c.group^0x80;m[base+3]=c.enabled;put(m,base+0x54,base+256 if j+1<c.length else 0)
 if actor(c):m[actor(c)+0x3B]=c.group;put(m,actor(c)+0x1D4,0x12345678 if c.resource else 0)
 put(m,s['D_800C3EE0'],NODES if c.length else 0);put(m,MARK,0);return m
def observation(m,c,node,s=SYMS):return(read(m,s['D_800C3EE0']),m[actor(c)+0x3B],read(m,actor(c)+0x1D4),m[node],m[node+3],read(m,node+0x54))
def effect(m,c,args,n,s=SYMS):
 _,node,a,view,mode=args;nextnode=read(m,node+0x54);mu=c.mutation
 if mu&1:put(m,s['D_800C3EE0'],0)
 if mu&2:put(m,node+0x54,0)
 if mu&4:m[a+0x3B]^=0x80
 if mu&8 and nextnode:m[nextnode+3]^=0xFF
 if mu&16 and nextnode:m[nextnode]^=0x80
 if mu&32:put(m,a+0x1D4,0)
 if mu&64 and nextnode:put(m,nextnode+0x54,0)
 put(m,MARK,u32(n*0x10000|(node-NODES)//256));return u32(args[0]+8*n+(view&3)+(mode&1))
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];obs=[];cursor=c.cursor;a=actor(c)
 if not a or not read(m,a+0x1D4)or not m[a+0x3B]:return m,calls,cursor,obs
 node=read(m,s['D_800C3EE0']);visits=0
 while node:
  visits+=1;assert visits<=6;nextnode=read(m,node+0x54)
  if m[a+0x3B]==m[node]and m[node+3]:
   args=(cursor,node,a,c.view,c.mode);calls.append((s['func_150311C4'],args));obs.append(observation(m,c,node,s));cursor=effect(m,c,args,len(calls),s)
  node=nextnode
 return m,calls,cursor,obs
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+512}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.observations=[];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(c.cursor,actor(c),c.view,c.mode));self.before=self.r[:]
 def record_call(self,t):
  assert t in(self.syms['func_150311C4'],ENTRY);args=tuple(self.arguments(5 if t!=ENTRY else 4));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t!=ENTRY:self.observations.append(observation(self.memory,self.case,args[1],self.syms))
 def hook(self,t):
  assert t==self.syms['func_150311C4'];assert self.r[29]==STACK+self.case.phase-56
  for reg,slot in((16,28),(17,32),(18,36),(19,40),(20,44),(21,48),(31,52)):assert read(self.memory,self.r[29]+slot)==(getattr(self,'expected_target_ra',self.before[31])if reg==31 else self.before[reg])
  args=self.calls[-1][1];n=sum(t==self.syms['func_150311C4']for t,_ in self.calls);value=effect(self.memory,self.case,args,n,self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def cases():
 for group,length,pattern,mu,phase in itertools.product((0,1,3,128,255),range(7),(0,63,21,42),(0,1,2,4,8,16,32,64),(0,8)):yield Case(group=group,length=length,pattern=pattern,mutation=mu,phase=phase)
 for present,resource,group,phase in itertools.product((0,1),(0,1),(0,3,255),(0,8)):yield Case(present=present,resource=resource,group=group,phase=phase)
 for byte,phase in itertools.product(range(256),(0,8)):yield Case(group=byte,phase=phase);yield Case(enabled=byte,phase=phase)
 for mu,pattern,phase in itertools.product(range(128),(63,21),(0,8)):yield Case(mutation=mu,pattern=pattern,phase=phase)
 for cursor,view,mode,phase in itertools.product((0,0x50000,0xFFFFFFFC),(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,0xFFFFFFFF),(0,8)):yield Case(cursor=cursor,view=view,mode=mode,phase=phase)
 for alias,group,mu,phase in itertools.product((1,3,6),(0,3,255),(0,2,4,8,32),(0,8)):yield Case(alias=alias,group=group,mutation=mu,phase=phase)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.observations)
def verify(m,initial,c,s=SYMS):
 want,calls,answer,obs=reference(initial,c,s);assert(public(m.memory),m.calls,m.r[2],m.observations)==(public(want),calls,answer,obs),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];visited=set();count=0;aliascases=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1;aliascases+=bool(c.alias)
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(present=0),Case(resource=0),Case(group=0),Case(length=0),Case(pattern=0),Case(mutation=127)):
  initial=fixture(c);full=Oracle(programs[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing boundary',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 sparse=0
 for c,keep in((Case(present=0),set()),(Case(resource=0),set(range(ACTOR+0x1D4,ACTOR+0x1D8))),(Case(group=0),set(range(ACTOR+0x1D4,ACTOR+0x1D8))|{ACTOR+0x3B})):
  initial={a:b for a,b in fixture(c).items()if STACK-256<=a<STACK+512 or a in keep}
  for words in programs:m=Oracle(words,initial,c);m.run();assert m.calls==[]and m.r[2]==c.cursor;sparse+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(D_800C3EE0=0x80007FF0+k*0x100000,func_150311C4=0x10008000+k*0x10000);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)]
  for length,mu,phase in itertools.product((0,1,6),(0,2,4,127),(0,8)):
   c=Case(length=length,mutation=mu,phase=phase);initial=fixture(c,s)
   for words in ps:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>8I',rom,0x5A96C));caller_count=0;skipped=0
 assert 'commands = func_15030F94(commands, actor, view, 1);'in(r/'conker/src/game/generated_58F80.c').read_text()
 for length,mu,view,phase in itertools.product((0,1,6),(0,2,4,127),(0,0x80000000),(0,8)):
  c=Case(length=length,mutation=mu,view=view,mode=1,phase=phase);initial=fixture(c);put(initial,STACK+phase+0x158,view);put(initial,STACK+phase+0x168,0);want,calls,answer,obs=reference(initial,c)
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),words));code[0x1502D4DC]=0;m=Oracle(window,initial,c,entry=0x1502D4BC,connected=code);m.r[16]=c.cursor;m.r[21]=actor(c);m.before=m.r[:];m.expected_target_ra=0x1502D4D8;m.code=WindowCode(m.code,m);m.code.ends=(0x1502D4DC,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(public(m.memory),m.calls,m.r[16],m.observations)==(public(want),[(ENTRY,(c.cursor,actor(c),view,1))]+calls,answer,obs)
  caller_count+=1
 for mode,phase in itertools.product((1,0xFFFFFFFF),(0,8)):
  c=Case(phase=phase);initial=fixture(c);put(initial,STACK+phase+0x158,c.view);put(initial,STACK+phase+0x168,mode)
  for words in programs:
   m=Oracle(window,initial,c,entry=0x1502D4BC,connected={0x1502D4DC:0});m.r[16]=c.cursor;m.r[21]=actor(c);m.code=WindowCode(m.code,m);m.code.ends=(0x1502D4DC,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing mode skip boundary')
   assert m.calls==[]and m.r[16]==c.cursor and public(m.memory)==public(initial);skipped+=1
 report=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,compiler_words=55,covered_words=55,slot_words=55,alignment_words=0,frame=56,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,saved_next_link=True,live_group_after_helper=True,helper_mutations=True,guest_alias_cases=aliascases,access_prefix_pairs=prefixes,sparse_executions=sparse,rebase_layouts=3,rebase_cases=rebased,original_caller_windows=[dict(entry='0x1502D4BC',ROM='0x5A96C',words=8,cases=caller_count,result_captured=True,call_delay_sets_mode_one=True,complete_parent_claimed=False)],skipped_caller_executions=skipped,complete_renderer_or_parent_or_gameplay_claimed=False)
 return report


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_15030F94';prefix=selected[:selected.index('/* Render')];body=selected[selected.index('/* Render'):]
 mutants=dict(missing_resource_gate=body.replace('*(u32 *)(actor + 0x1D4) == 0 || ',''),inverted_group_gate=body.replace('actor[0x3B] == 0','actor[0x3B] != 0'),inverted_group_match=body.replace('actor[0x3B] != node[0]','actor[0x3B] == node[0]'),inverted_enable=body.replace('node[3] == 0','node[3] != 0'),late_next=body.replace('node = next;','node = *(u8 **)(node + 0x54);').replace('u8 *next;','').replace('            next = *(u8 **)(node + 0x54);',''),stale_group=body.replace('u8 *next;','u8 *next;\n    u8 group;').replace('    node = D_800C3EE0;','    group = actor[0x3B];\n    node = D_800C3EE0;').replace('actor[0x3B] != node[0]','group != node[0]'),ignored_cursor=body.replace('cursor = (Gfx *)func_150311C4','(void)func_150311C4'),wrong_view=body.replace('node, actor, view, mode','node, actor, mode, mode'));assert all(v!=body for v in mutants.values())
 text=prefix+r'''
typedef struct {u32 args[5],obs[6];} Call;
typedef struct {u32 present,resource,group,length,pattern,enabled,mutation,cursor,view,mode,answer,finalGroup,finalResource,head,marker,count;u32 nodeGroup[6],nodeEnable[6],next[6];Call calls[6];} Fixture;
u8 *D_800C3EE0;
static u8 actor[512] __attribute__((aligned(8))),nodes[1792] __attribute__((aligned(8))),beforeActor[512],beforeNodes[1792];static const Fixture*current;static u32 count,marker,bad;
static u32 canonical(u8*p){if(!p)return 0;if(p>=nodes&&p<nodes+1792)return 0x30000u+(u32)(p-nodes);return 0xDEADBEEFu;}
static u8* host(u32 p){return p?nodes+(p-0x30000u):0;}
static u32 load(u8*p){return *(u32*)p;}static void store(u8*p,u32 v){*(u32*)p=v;}
static u32 effect(u32 cursor,u8*node,u8*a,s32 view,s32 mode){u8*next=*(u8**)(node+0x54);u32 mu=current->mutation;if(mu&1)D_800C3EE0=0;if(mu&2)*(u8**)(node+0x54)=0;if(mu&4)a[0x3B]^=0x80;if((mu&8)&&next)next[3]^=0xFF;if((mu&16)&&next)next[0]^=0x80;if(mu&32)store(a+0x1D4,0);if((mu&64)&&next)*(u8**)(next+0x54)=0;marker=count*0x10000u|(u32)(node-nodes)/256;return cursor+8*count+((u32)view&3)+((u32)mode&1);}
s32 func_150311C4(Gfx*cursor,u8*node,u8*a,s32 view,s32 mode){u32 i,args[5],obs[6];const Call*c;if(count>=current->count){bad=1;return(s32)cursor;}c=current->calls+count++;args[0]=(u32)cursor;args[1]=canonical(node);args[2]=a==actor?0x20000u:0xDEADu;args[3]=(u32)view;args[4]=(u32)mode;obs[0]=canonical(D_800C3EE0);obs[1]=a[0x3B];obs[2]=load(a+0x1D4);obs[3]=node[0];obs[4]=node[3];obs[5]=canonical(*(u8**)(node+0x54));for(i=0;i<5;i++)if(args[i]!=c->args[i])bad=2;for(i=0;i<6;i++)if(obs[i]!=c->obs[i])bad=3;return(s32)effect((u32)cursor,node,a,view,mode);}
'''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());rows=[]
 def arr(v):return '{'+','.join('0x%Xu'%(x&0xFFFFFFFF)for x in v)+'}'
 for c in q.cases():
  if c.phase or c.alias:continue
  want,calls,answer,obs=q.reference(q.fixture(c),c);scalars=[c.present,c.resource,c.group,c.length,c.pattern,c.enabled,c.mutation,c.cursor,c.view,c.mode,answer,want[q.ACTOR+0x3B]if c.present else c.group,q.read(want,q.ACTOR+0x1D4)if c.present else q.read(q.fixture(c),q.ACTOR+0x1D4),q.read(want,q.SYMS['D_800C3EE0']),q.read(want,q.MARK),len(calls)]
  # With no actor, its untouched initialization has no typed resource cell.
  if not c.present:scalars[11]=q.fixture(c)[q.ACTOR+0x3B]
  ng=[want[q.NODES+j*256]for j in range(6)];ne=[want[q.NODES+j*256+3]for j in range(6)];nx=[q.read(want,q.NODES+j*256+0x54)for j in range(6)];cr=['{'+arr(args)+','+arr(ob)+'}'for(_,args),ob in zip(calls,obs)]
  rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in scalars)+','+arr(ng)+','+arr(ne)+','+arr(nx)+',{'+','.join(cr)+'}}')
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef Gfx*(*Fn)(Gfx*,u8*,s32,s32);
static s32 check(Fn fn){u32 n,i,j,answer;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;current=c;count=marker=bad=0;for(i=0;i<512;i++)actor[i]=(u8)(i*29+0x59);for(j=0;j<6;j++){u8*p=nodes+j*256;for(i=0;i<512;i++)p[i]=(u8)(i*13+j*31+0x21);p[0]=(u8)((c->pattern>>j&1)?c->group:c->group^0x80);p[3]=(u8)c->enabled;*(u8**)(p+0x54)=j+1<c->length?p+256:0;}if(c->present){actor[0x3B]=(u8)c->group;store(actor+0x1D4,c->resource?0x12345678:0);}D_800C3EE0=c->length?nodes:0;for(i=0;i<512;i++)beforeActor[i]=actor[i];for(i=0;i<1792;i++)beforeNodes[i]=nodes[i];answer=(u32)fn((Gfx*)c->cursor,c->present?actor:0,(s32)c->view,(s32)c->mode);if(bad||count!=c->count||marker!=c->marker||answer!=c->answer||canonical(D_800C3EE0)!=c->head)return 1;
 beforeActor[0x3B]=(u8)c->finalGroup;if(c->present)store(beforeActor+0x1D4,c->finalResource);for(j=0;j<6;j++){u8*p=beforeNodes+j*256;p[0]=(u8)c->nodeGroup[j];p[3]=(u8)c->nodeEnable[j];*(u8**)(p+0x54)=host(c->next[j]);}for(i=0;i<512;i++)if(actor[i]!=beforeActor[i])return 2;for(i=0;i<1792;i++)if(nodes[i]!=beforeNodes[i])return 3;}return 0;}
static int run(void){if(sizeof(void*)!=4)return 90;{s32 result=check(test_selected);if(result)return 10+result;}
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');return text,dict(cases=len(rows),negative_controls=len(mutants),guest_alias_cases_excluded=True)
