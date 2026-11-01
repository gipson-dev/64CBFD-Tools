"""Actor-ID lookup: full-width argument, first active slot and read-only trace."""
"""Bounded actor-key lookup proof: exact link, guest loads and native32 ABI."""
from pathlib import Path
from dataclasses import dataclass
import json,struct,subprocess,itertools
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
r=o=None;F='func_1505F0AC';ENTRY=0x1505F0AC;BODY=220;BASE=0x800CC2D0;STRIDE=0x32C
@dataclass(frozen=True)
class Case:
 key:int=37
 slot:int=24
 second:int=-1
 state:int=1
 phase:int=0
 pattern:int=0

def cases():
 rows=[]
 for key,slot,phase in itertools.product(range(256),(-1,0,1,4,24,25),(0,8)):rows.append(Case(key,slot,phase=phase))
 for slot,state,phase in itertools.product(range(26),(0,1,0x100,0x80000000,0xFFFFFFFF),(0,8)):rows.append(Case(slot%256,slot,state=state,phase=phase))
 for slot,second,phase in itertools.product(range(25),(0,4,24,25),(0,8)):rows.append(Case(255,slot,second,state=0x80000000,phase=phase,pattern=1))
 for key,slot,phase in itertools.product((-2147483648,-1,256,511,2147483647),(-1,0,1,24,25),(0,8)):rows.append(Case(key,slot,phase=phase))
 return tuple(dict.fromkeys(rows))

def fixture(c,base=BASE):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for i in range(26):
  p=base+i*STRIDE;put(m,p,0 if c.pattern==0 else 1);m[p+4]=(c.key+1)&255
 for i in (c.slot,c.second):
  if i>=0:put(m,base+i*STRIDE,c.state);m[base+i*STRIDE+4]=c.key&255
 return m

def reference(m,c,base=BASE):
 for i in range(25):
  if read(m,base+i*STRIDE) and m[base+i*STRIDE+4]==c.key:return base+i*STRIDE
 return 0

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,base=BASE,connected=None):
  super().__init__(words,memory,c,entry=entry,s={},arguments=(c.key&0xFFFFFFFF,),connected=connected);self.before=self.r[:]
 def record_call(self,t):
  assert t==ENTRY;args=(self.r[4],);self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):raise AssertionError(('Unexpected provider',hex(t)))

def linked(obj,label,base=BASE,entry=ENTRY):
 p=o/label;s={'D_800CC2D0':base,'D_800CC5FC':base+STRIDE,'D_800CC2D4':base+4};p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
 return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))

def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)

def verify(m,initial,c,base=BASE):
 assert m.r[2]==reference(initial,c,base),(c,hex(m.r[2]));assert m.memory==initial
 assert m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24] and m.r[28]==m.before[28]
 assert not any(x[0]=='W'for x in m.trace)



def qualify(root,output):
 global r,o
 r,o=root,output
 visited=set();count=prefixes=rebased=0
 for k,base in enumerate((BASE,0x80007FF0,0x80018000,0x8002FFF0)):
  programs=[linked(p,'guest-id-%d-%d'%(k,i),base=base)for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o'))];assert programs[0]==programs[1]
  for c in cases():
   initial=fixture(c,base);machines=[]
   for words in programs:
    m=Oracle(words,initial,c,base=base);m.run();verify(m,initial,c,base);machines.append(m)
   assert state(machines[0])==state(machines[1]);visited.update(machines[0].visits);count+=1
   if k:rebased+=1
 expected=set(range(ENTRY,ENTRY+BODY,4))-{ENTRY+x for x in(0x58,0x7C,0xA0)};assert visited==expected
 for c in(Case(),Case(slot=-1),Case(slot=0),Case(slot=4,state=0),Case(key=-1,slot=24),Case(slot=1,second=24,pattern=1)):
  initial=fixture(c);full=Oracle(programs[0],initial,c);default=[linked(p,'fault-id-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o'))];full=Oracle(default[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in default:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access prefix',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1]);prefixes+=1
 report=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=count,executions=count*2,covered_words=len(visited),unreachable_offsets=[0x58,0x7C,0xA0],compiler_words=55,frame=0,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,literal_full_state_equal=True,read_only=True,reserved_slot_25_excluded=True,all_256_ID_bytes=True,full_s32_search_argument=True)
 (o/'private-guest-runtime.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
 return report

def callers(root,output):
 global r,o
 r,o=root,output
 import sys
 g=sys.modules[__name__]
 r=g.r;rom=(r/'conker/conker.us.bin').read_bytes();values=struct.unpack('>%dI'%(len(rom)//4),rom);refs=[i*4 for i,w in enumerate(values)if w==0x0C000000|((g.ENTRY>>2)&0x3FFFFFF)];assert refs==[0x919BC,0xA1170,0xA5070,0xB0BF0]
 census=dict(target=g.F,aligned_ROM_JALs=refs,aligned_ROM_Js=[i*4 for i,w in enumerate(values)if w==0x08000000|((g.ENTRY>>2)&0x3FFFFFF)],aligned_ROM_pointer_literals=[i*4 for i,w in enumerate(values)if w==g.ENTRY]);assert not census['aligned_ROM_Js']and not census['aligned_ROM_pointer_literals'];(o/'caller-census.json').write_text(json.dumps(census,indent=2)+'\n')
 roots=[g.linked(p,'caller-root-'+str(i))for i,p in enumerate((o/('original-'+g.F+'.o'),o/'selected-final.o'))]
 SCRIPT,OWNER=0x60000,0x61000;D0,D1=0x800D1890,0x800D1891
 windows=((0x15064504,0x1506452C,False),(0x15073CB8,0x15073CF4,True),(0x15077BB4,0x15077BE4,True),(0x15083740,0x15083770,False));rows=[];total=0
 for which,(start,end,full)in enumerate(windows):
  off=start-0x15000000+0x2D4B0;words=struct.unpack_from('>%dI'%((end-start)//4),rom,off);(o/('original-caller-%d.bin'%which)).write_bytes(struct.pack('>%dI'%len(words),*words));count=0;seen=set()
  for key,slot,phase,state,tag in itertools.product(((108,)if which==0 else(83,)if which==1 else(0,128,255)),((-1,0,1,4,24,25)if which in(1,3)else(0,1,4,24)),(0,8),(1,0x80000000),(0,31)):
   c=g.Case(key,slot,state=state,phase=phase);initial=g.fixture(c);answer=g.reference(initial,c);h=g.STACK+phase
   for p,n in((SCRIPT,16),(OWNER,0x400),(D0,4)):initial.update({p+i:0xA5 for i in range(n)})
   initial[SCRIPT]=key;initial[D0]=0x7E;initial[D1]=key
   for i in range(26):
    p=g.BASE+i*g.STRIDE;g.put(initial,p+0x218,0x87654321);g.put(initial,p+0x21C,0xABCD,2);g.put(initial,p+0x244,tag,2);g.put(initial,p+0x2E4,0x13579BDF);initial[p+0x232]=0x55;initial[p+0x65]=0xA7
   expected=dict(initial)
   if which==0:g.put(expected,h+108,0x12345678);g.put(expected,h+104,0x3F800000);expected[OWNER+0x81]=1
   if which==1 and answer and tag==31:g.put(expected,answer+0x21C,0,2)
   if which==2:g.put(expected,answer+0x218,0);expected[answer+0x232]=0x7E
   machines=[]
   for root in roots:
    code=dict(zip(range(g.ENTRY,g.ENTRY+220,4),root));code[0x15083798]=0;m=g.Oracle(words,initial,c,entry=start,connected=code);m.r[16]=OWNER if which==0 else SCRIPT;m.r[8]=0x12345678;m.f[16]=0x3F800000
    m.r[19]=g.BASE;m.r[20]=g.STRIDE;m.r[21]=g.BASE+max(0,slot)*g.STRIDE;m.before=m.r[:];m.saved_f=m.f[20:]
    if not full:m.code=WindowCode(m.code,m);m.code.ends=(end,0x15083798)
    try:m.run()
    except WindowBoundary:assert not full
    else:assert full
    assert m.calls==[(g.ENTRY,(key,))],(which,c,m.calls)
    def public(memory):return {a:b for a,b in memory.items()if not h-256<=a<h}
    assert public(m.memory)==public(expected),(which,c,'public')
    if which==0:assert m.r[2]==answer and m.r[6]==answer and m.r[3]==0x13579BDF and m.r[8]==0x12345678 and m.f[16]==0x3F800000
    elif which==1:assert m.r[2]==answer
    elif which==2:assert answer!=0 and m.r[2]==answer
    else:
     assert m.r[2]==answer and m.r[4]==answer
     if answer:assert m.r[9]==slot and m.r[10]==slot+1 and m.r[11]==0xA7
    machines.append(m);seen.update(m.visits);count+=1
   assert g.state(machines[0])==g.state(machines[1])
  rows.append(dict(start=hex(start),end=hex(end),words=len(words),executions=count,full_parent=full,covered_window_words=len(set(range(start,end,4))&seen),nonnull_consumer_cases_only=which in(0,2)))
  total+=count
 # A slot-zero hit requires only that slot's active word and ID byte.
 c=g.Case(slot=0);initial=g.fixture(c);sparse={a:b for a,b in initial.items()if g.STACK-256<=a<g.STACK+256 or g.BASE<=a<g.BASE+5}
 for root in roots:m=g.Oracle(root,sparse,c);m.run();assert m.r[2]==g.BASE and m.memory==sparse
 report=dict(success=True,private_only=True,installed=False,matching_credit=0,original_call_sites=4,executions=total,windows=rows,complete_small_parents=2,larger_parent_claims=False,actual_argument_setup_and_return_pointer_consumers=True,null_guarded_caller_paths=True,unguarded_callers_qualified_only_for_nonnull_results=True,sparse_first_slot_executions=2)
 (o/'private-caller-runtime.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
 return report
