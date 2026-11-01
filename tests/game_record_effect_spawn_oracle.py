"""Record effect callback: ordered guest payload, original helpers and dispatcher."""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=o=None;F='func_15014094';ENTRY=0x15014094;OWNER,OUTPUT,MARK=0x30000,0x50000,0x70000
names=('func_15144598','func_1510F800','func_1510FD20','func_15149130','memcpy');counts=(1,1,2,9,3)
@dataclass(frozen=True)
class Case:
 seed:int=0
 outcome:int=1
 mode:int=0
 phase:int=0
 first:int=0x8000
 second:int=0xFFFF
 height:int=0x80000000
 key:int=0x87654321
def u(n):return n&0xFFFFFFFF
def sh(n):return u(((n&65535)^32768)-32768)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,1024)}
 for base,size in ((OWNER-16,112),(OUTPUT-16,160),(MARK,16)):m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(size)})
 put(m,OWNER,c.first,2);put(m,OWNER+4,c.second,2);return m
def public(m,c):return {a:b for a,b in m.items() if not STACK+c.phase-1024<=a<STACK+c.phase}
def mutation(m,c,n,h):
 if c.mode&1 and n==1:put(m,OWNER,0xFFFF,2);put(m,OWNER+4,0x8000,2);m[OWNER+0x16]^=0x80
 if c.mode&2 and n==3:m[h-104+0x34+0x19]^=0x5A
def reference(initial,c,s,whole=False):
 m=dict(initial);h=STACK+c.phase;p=h-104+0x34;calls=[]
 m[OWNER+0x16]|=4;put(m,h,OWNER);put(m,p,OWNER);calls.append((s[names[0]],(OWNER,)));put(m,p+4,c.height);put(m,p+8,0)
 calls.append((s[names[1]],(0,)));mutation(m,c,1,h)
 calls.append((s[names[2]],(sh(read(m,OWNER,2)),sh(read(m,OWNER+4,2)))));put(m,p+12,c.key);m[p+0x2C]=0
 calls.append((s[names[3]],(300,0xFFFFFFFF,33,0xFFFFFFFF,0,0,52,255,1)));mutation(m,c,3,h)
 packet=None
 if c.outcome:
  calls.append((s[names[4]],(OUTPUT+40,p,52)));packet=bytes(m[p+i]for i in range(52))
  for i,v in enumerate(packet):m[OUTPUT+40+i]=v
 return (m if whole else public(m,c)),calls,packet
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;self.packets=[]
  super().__init__(words,memory,c,entry=entry,s={},arguments=(OWNER,),connected=connected)
  self.before_f=self.f[:]
 def record_call(self,t):
  if t==ENTRY:self.boundaries.append(tuple(self.arguments(1)));return
  assert t in self.s.values(),hex(t);n=next(i for i,k in enumerate(names)if self.s[k]==t);a=tuple(map(u,self.arguments(counts[n])))
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  n=next(i for i,k in enumerate(names)if self.s[k]==t);a=self.calls[-1][1]
  mutation(self.memory,self.c,n,STACK+self.c.phase)
  value=0xA5000002
  if n==2:value=self.c.key
  if n==3:value=OUTPUT if self.c.outcome else 0
  if n==4:
   assert a[2]==52;packet=bytes(self.memory[a[1]+i]for i in range(52));self.packets.append(packet)
   for i,v in enumerate(packet):self.memory[a[0]+i]=v
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u(value)
  if n==0:self.f[0]=self.c.height
def programs(layout):
 entry=ENTRY+layout*0x01000000;s={n:0x16100000+layout*0x100000+i*0x8000 for i,n in enumerate(names)};roots=[]
 for label,obj in (('original',o/('original-'+F+'.o')),('private',o/'selected-final.o')):
  script=o/('guest-%d-%s.ld'%(layout,label));script.write_text('SECTIONS{.text 0x%X : SUBALIGN(4) {*(.text)}}\n'%entry)
  elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',F,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  raw=sections(elf)['.text'][1][:176];roots.append(struct.unpack('>44I',raw))
 assert roots[0]==roots[1];return entry,s,roots

def qualify(root,output):
 global r,o
 r,o=root,output
 all_cases=[Case(seed,outcome,mode,phase,a,b,h,u(seed*0x1020304)) for seed,outcome,mode,phase,(a,b),h in itertools.product(range(4),(0,1),(0,1,2,3),(0,8),((0,0),(0x7FFF,0x8000),(0x8000,0xFFFF)),(0,0x80000000,bits(12.5)))]
 seen=set();done=0
 for layout in range(3):
  entry,s,roots=programs(layout)
  for c in all_cases:
   initial=fixture(c);expected,calls,packet=reference(initial,c,s);models=[]
   for root in roots:
    m=Oracle(root,initial,c,s,entry);m.run();assert public(m.memory,c)==expected,(layout,c,'memory',[(hex(a),m.memory.get(a),v)for a,v in expected.items()if m.memory.get(a)!=v][:12]);assert m.calls==calls,(layout,c,m.calls,calls);assert m.packets==([]if packet is None else[packet]);assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30)),c;assert m.f[20:]==m.before_f[20:];models.append(m);seen.update(m.visits);done+=1
   assert models[0].trace==models[1].trace and models[0].memory==models[1].memory and models[0].r==models[1].r
  assert set(range(entry,entry+176,4))<=seen
 # Access-prefix comparison: exact emitted schedule, not portable-C fault claims.
 c=Case(mode=3);entry,s,roots=programs(0);m=Oracle(roots[0],fixture(c),c,s,entry);m.run();cuts=m.all_accesses
 for cut in range(cuts):
  models=[]
  for root in roots:
   q=Oracle(root,fixture(c),c,s,entry);q.cut=cut
   try:q.run()
   except AccessBoundary:pass
   else:raise AssertionError('fault cut did not fire')
   models.append(q)
  assert models[0].trace==models[1].trace and models[0].memory==models[1].memory
 # Full retail callback dispatcher: A0 stays live and V0 is overwritten by return 1.
 rom=(r/'conker/conker.us.bin').read_bytes();start=0x1501396C;caller=struct.unpack_from('>16I',rom,start-0x15000000+0x2D4B0)
 (o/'original-dispatcher.bin').write_bytes(struct.pack('>16I',*caller))
 table=0x80082ECC;assert struct.unpack_from('>I',rom,0x2279D0)[0]==ENTRY
 caller_count=0
 for c,poison in itertools.product(all_cases[::8],(0,1,0x80000000,0xFFFFFFFF)):
  for root in roots:
   initial=fixture(c);initial[OWNER+0x17]=17;put(initial,table+17*4,ENTRY);expected,calls,packet=reference(initial,replace(c,phase=c.phase-24),s,whole=True);expected=public(expected,c)
   connected=dict(zip(range(ENTRY,ENTRY+176,4),root));m=Oracle(caller,initial,c,s,start,connected);m.boundaries=[];m.before_f=m.f[:];m.c=replace(c,phase=c.phase-24)
   class Code(WindowCode):
    def __getitem__(self,pc):
     if pc==0x15013998:self.owner.r[2]=poison
     return super().__getitem__(pc)
   m.code=Code(m.code,m);m.code.ends=()
   m.run();assert m.calls==calls and m.boundaries==[(OWNER,)] and m.r[2]==1,(c,m.calls,m.boundaries,hex(m.r[2]));assert public(m.memory,c)==expected,(c,[(hex(a),m.memory.get(a),v)for a,v in expected.items()if m.memory.get(a)!=v][:12]);caller_count+=1
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,root_cases=len(all_cases)*3,root_executions=done,independent_GNU_link_layouts=3,retail_words_covered=44,complete_public_memory_and_call_payloads=True,original_private_complete_memory_registers_and_trace_equal=True,seeded_untouched_payload_bytes_preserved=True,access_prefix_cuts=cuts,access_prefix_executions=cuts*2,full_fault_register_equivalence_claim=False,callback_dispatcher_words=16,callback_executions=caller_count,callback_return_poison_values=4,dispatcher_ignores_callback_return=True)
 (o/'private-guest-runtime.json').write_text(json.dumps(q,indent=2)+'\n');print(q,flush=True)
 return q

def helpers(root,output):
 global r,o
 r,o=root,output
 import sys
 g=sys.modules[__name__]
 rom=(r/'conker/conker.us.bin').read_bytes();entry,s,roots=g.programs(0);ALLOC,ZERO=0x15167A68,0x100226F0
 factory=struct.unpack_from('>49I',rom,0x1765E0);copy=struct.unpack_from('>11I',rom,0x22EC0);connected=dict(zip(range(s['func_15149130'],s['func_15149130']+196,4),factory));connected.update(zip(range(s['memcpy'],s['memcpy']+44,4),copy))
 class Oracle(g.Oracle):
  def record_call(self,t):
   if t in(ALLOC,ZERO):
    n=6 if t==ALLOC else 2;self.calls.append((t,tuple(map(g.u,self.arguments(n)))));return
   return super().record_call(t)
  def hook(self,t):
   if t not in(ALLOC,ZERO):return super().hook(t)
   a=self.calls[-1][1]
   if t==ALLOC:
    assert a==(35,1,92,1,255,1),a;value=g.OUTPUT if self.c.outcome else 0;g.mutation(self.memory,self.c,3,g.STACK+self.c.phase)
   else:
    assert a==(g.OUTPUT+20,16),a
    for i in range(16):self.memory[a[0]+i]=0
    value=0xDEADBEEF
   for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value
 count=0;seen=set()
 for seed,outcome,mode,phase in itertools.product(range(8),(0,1),(0,1,2,3),(0,8)):
  c=g.Case(seed,outcome,mode,phase,0x8000,0xFFFF,g.bits(-12.5),seed*0x1020304);initial=g.fixture(c);expected,calls,packet=g.reference(initial,c,s)
  expected=dict(expected);expected_calls=[]
  for t,a in calls:
   expected_calls.append((t,a))
   if t==s['func_15149130']:
    expected_calls.append((ALLOC,(35,1,92,1,255,1)))
    if outcome:expected_calls.append((ZERO,(g.OUTPUT+20,16)))
  if outcome:
   g.put(expected,g.OUTPUT+14,300,2)
   for at,value in((13,0),(16,255),(17,33),(18,255),(19,0)):expected[g.OUTPUT+at]=value
   for i in range(16):expected[g.OUTPUT+20+i]=0
  models=[]
  for root in roots:
   m=Oracle(root,initial,c,s,entry,connected);m.run();assert g.public(m.memory,c)==expected,(c,[(hex(a),m.memory.get(a),v)for a,v in expected.items()if m.memory.get(a)!=v][:8]);assert m.calls==expected_calls,(m.calls,expected_calls);models.append(m);seen.update(m.visits);count+=1
  assert models[0].trace==models[1].trace and models[0].memory==models[1].memory
 factory_expected=set(range(s['func_15149130'],s['func_15149130']+196,4))-{s['func_15149130']+52,s['func_15149130']+56};assert factory_expected<=seen
 assert set(range(s['memcpy'],s['memcpy']+44,4))<=seen
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=count//2,executions=count,original_factory_words=49,original_memcpy_words=11,reachable_factory_words=47,original_memcpy_words_executed=11,unreachable_factory_alternate_allocator_words=2,all_target_reachable_helper_words_executed=True,allocator_arguments_verified=True,original_null_and_success_routes=True,seeded_stack_payload_and_public_memory_equal=True)
 (o/'private-helper-runtime.json').write_text(json.dumps(q,indent=2)+'\n');print(q,flush=True)
 # Aligned retail census is an inventory, not a claim about arbitrary data execution.
 word=0x0C000000|((entry>>2)&0x3FFFFFF);jump=0x08000000|((entry>>2)&0x3FFFFFF);values=struct.unpack('>%dI'%(len(rom)//4),rom)
 census=dict(target='func_15014094',aligned_ROM_JALs=[i*4 for i,v in enumerate(values)if v==word],aligned_ROM_Js=[i*4 for i,v in enumerate(values)if v==jump],aligned_ROM_pointer_literals=[i*4 for i,v in enumerate(values)if v==entry],callback_table='D_80082ECC',callback_index=17,callback_pointer_ROM=0x2279D0,original_dispatcher='func_1501396C',original_dispatcher_passes_live_A0=True,callback_return_overwritten_with_one_at='0x15013998',all_known_static_routes_qualified=True)
 assert census['aligned_ROM_JALs']==[]and census['aligned_ROM_Js']==[]and census['aligned_ROM_pointer_literals']==[0x2279D0],census
 (o/'caller-census.json').write_text(json.dumps(census,indent=2)+'\n');print(census,flush=True)
 return q,census
