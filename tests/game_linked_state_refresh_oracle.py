"""Linked-state refresh guest execution, original cleanup and complete dispatcher."""
"""Private linked-state refresh qualification; no installation or matching credit."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
r=o=None
ENTRY,RECORD,STATE,NEWSTATE,ACTOR=0x151A084C,0x30000,0x50000,0x60000,0x70000
REFRESH,CLEANUP=0x1519F1C8,0x151A0928
PATCHES=((0x68,0xAFA80024,0xAFA80028),(0x8C,0x8FA80024,0x8FA80028))
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 active:int=1
 match:int=1
 gate:int=1
 mode:int=6
 result:int=0x87654321
 mutation:int=0
 alias:int=0
 phase:int=0
 seed:int=0

def state(c):return STATE if not c.alias else RECORD-0x2C
def cases():
 rows=[]
 for mode,active,match,gate,mutation,result,phase in itertools.product((0,1,6,7,255),(0,1,0xFFFFFFFF,0x80000000),(0,1),(0,1),range(8),(0,1,0x87654321,0xFFFFFFFF),(0,8)):
  rows.append(Case(active,match,gate,mode,result,mutation,0,phase,(mode+mutation)%2))
 for mode in range(256):rows.append(Case(1,1,1,mode,0x12345678,mode%8,mode%2,8*(mode%2),mode%2))
 return rows

def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for base,n in ((RECORD-64,256),(STATE,256),(NEWSTATE,256),(ACTOR,512)):
  m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 s=state(c);put(m,RECORD+40,s);m[RECORD+44]=c.mode;m[RECORD+13]=0xA4;put(m,RECORD+14,0x1234,2)
 put(m,s+24,ACTOR);m[s+28]=0x87;put(m,ACTOR,c.active);m[ACTOR+59]=0x87 if c.match else 0x86;put(m,ACTOR+468,c.gate)
 return m

def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+1024}
def refresh_effect(m,c):
 if c.mutation&1:m[RECORD+44]=(0,6,7,255)[c.mode%4]
 if c.mutation&2:put(m,RECORD+40,NEWSTATE)
 if c.mutation&4:m[RECORD+13]^=0x40;put(m,RECORD+14,0x2468,2)
def cleanup_effect(m):
 mode=m[RECORD+44];s=read(m,RECORD+40);put(m,s+88+(4 if mode==6 else 12),0)
def reference(initial,c):
 m=dict(initial);s=read(m,RECORD+40);actor=read(m,s+24);outputs=s+88;invalid=read(m,actor)==0;calls=[]
 if m[read(m,RECORD+40)+28]!=m[actor+59]:invalid=True
 if not invalid and read(m,actor+468)!=0:
  invalid=True;calls.append((REFRESH,(read(m,RECORD+40),m[RECORD+44])));refresh_effect(m,c)
  put(m,outputs+(0 if m[RECORD+44]==6 else 8),c.result)
 if invalid:
  calls.append((CLEANUP,(RECORD,)));cleanup_effect(m);put(m,RECORD+14,0xFFFF,2);m[RECORD+13]|=1
 return public(m,c),calls

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,connected=None):
  self.c=c
  super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(RECORD,))
 def record_call(self,t):
  assert t in (REFRESH,CLEANUP),hex(t);self.calls.append((t,tuple(self.arguments(2 if t==REFRESH else 1))))
 def hook(self,t):
  if t==REFRESH:refresh_effect(self.memory,self.c);value=self.c.result
  else:cleanup_effect(self.memory);value=0xDEADBEEF
  for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def normalize(raw):
 result=bytearray(raw)
 for at,old,new in PATCHES:
  assert struct.unpack_from('>I',result,at)[0]==old
  struct.pack_into('>I',result,at,new)
 return bytes(result)

def qualify(root,output):
 global r,o
 r,o=Path(root),Path(output)
 rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 obj=o/'selected-final.o'
 raw,bindings=payload(obj,'func_151A084C');assert len(raw)==220
 # Retain both original and current cleanup bodies; never infer original identity.
 helper=struct.unpack_from('>10I',rom,0x1CDDD8);at=elf_slot_offset(before,CLEANUP,40);retained=struct.unpack_from('>10I',before,at)
 helper_equal=helper==retained;helper_modes=[('original',helper)]if helper_equal else[('original',helper),('retained',retained)]
 truth=struct.unpack_from('>55I',rom,0x1CDCFC);layouts=[]
 for layout in range(3):
  entry=ENTRY+layout*0x1000000;p=o/('guest-root-%d'%layout);p.with_suffix('.ld').write_text('SECTIONS{.text 0x%X:SUBALIGN(4){*(.text)}}\n'%entry)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_151A084C','--defsym=func_1519F1C8=0x1519F1C8','--defsym=func_151A0928=0x151A0928','-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
  linked=sections(p.with_suffix('.elf'))['.text'][1][:220];normalized=normalize(linked);assert struct.unpack('>55I',normalized)==truth
  layouts.append((entry,struct.unpack('>55I',linked),truth))
 count=0;seen=set();helper_seen=set();root_cases=cases()
 for layout,(entry,unpatched,normalized)in enumerate(layouts):
  for c in root_cases:
   initial=fixture(c);expected,calls=reference(initial,c);models=[]
   for words in (truth,normalized,unpatched):
    m=Oracle(words,initial,c,entry);m.run();assert public(m.memory,c)==expected and m.calls==calls,(layout,c,m.calls,calls)
    assert m.r[16:24]==m.before[16:24]and m.r[29]==m.before[29];models.append(m);count+=1;seen.update(pc-layout*0x1000000 for pc in m.visits)
   a,b,raw_model=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls)
   assert(a.r,a.f,a.hi,a.lo,a.calls)==(raw_model.r,raw_model.f,raw_model.hi,raw_model.lo,raw_model.calls)
 missing=sorted(set(range(ENTRY,ENTRY+220,4))-seen);assert missing==[0x151A08EC],missing
 connected_count=0
 for label,ws in helper_modes:
  connected=dict(zip(range(CLEANUP,CLEANUP+40,4),ws))
  for c in root_cases[::17]:
   initial=fixture(c);expected,calls=reference(initial,c);models=[]
   for words in (truth,layouts[0][2]):
    m=Oracle(words,initial,c,ENTRY,connected);m.run();assert public(m.memory,c)==expected and m.calls==calls,(label,c);models.append(m);connected_count+=1;helper_seen.update(m.visits)
   a,b=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls)
 assert set(range(CLEANUP,CLEANUP+40,4))<=helper_seen
 pairs=0
 for c in (Case(),Case(active=0),Case(match=0),Case(gate=0),Case(mutation=7,alias=1)):
  m=Oracle(truth,fixture(c),c);m.run()
  for cut in range(m.all_accesses):
   models=[]
   for words in (truth,layouts[0][2]):
    q=Oracle(words,fixture(c),c);q.cut=cut
    try:q.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    models.append(q)
   a,b=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls);pairs+=1
 # Invalid paths skip the actor resource field; valid unavailable paths skip mode/output memory.
 sparse=0
 for c in (Case(active=0),Case(match=0),Case(gate=0)):
  initial=fixture(c)
  if not c.active or not c.match:
   for j in range(4):del initial[ACTOR+468+j]
  else:
   del initial[RECORD+44]
   for j in range(16):del initial[state(c)+88+j]
  for words in (truth,layouts[0][2]):m=Oracle(words,initial,c);m.run();sparse+=1
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=len(root_cases)*3,executions=count,independent_link_layouts=3,words=55,covered_words=54,unreachable_offsets=[0xA0],closed_private_spill_pair=list(PATCHES),raw_C_public_state_and_calls_equal=True,normalized_complete_model_state_equal=True,all_256_mode_bytes=True,live_mode_after_refresh=True,cached_output_base_and_live_cleanup_link=True,entry_mode_output_alias=True,access_prefix_pairs=pairs,sparse_executions=sparse,cleanup_retained_equal_original=helper_equal,cleanup_modes=[n for n,_ in helper_modes],cleanup_connected_executions=connected_count,cleanup_words_executed=10,refresh_helper_stubbed=True,portable_C_fault_claim=False)
 return q

def callers(root,output):
 global r,o
 r,o=Path(root),Path(output)
 import sys
 g=sys.modules[__name__]
 rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 PARENT,FREE,DESTRUCTOR=0x15149264,0x1516972C,0x17400000
 words=struct.unpack_from('>45I',rom,0x176714);at=elf_slot_offset(before,PARENT,180);retained=struct.unpack_from('>45I',before,at);assert words==retained
 truth=struct.unpack_from('>55I',rom,0x1CDCFC);normalized=struct.unpack('>55I',g.normalize(sections(o/'guest-root-0.elf')['.text'][1][:220]));assert truth==normalized
 helper=struct.unpack_from('>10I',rom,0x1CDDD8);assert struct.unpack_from('>I',rom,0x22EFD4)[0]==g.ENTRY
 signed16=lambda n:((n&65535)^32768)-32768
 class Oracle(g.Oracle):
  def __init__(self,*args,destructor_reset=False,**kwargs):self.destructor_reset=destructor_reset;super().__init__(*args,**kwargs)
  def record_call(self,t):
   if t in(g.ENTRY,FREE,DESTRUCTOR):self.calls.append((t,tuple(self.arguments(1))));return
   return super().record_call(t)
  def hook(self,t):
   if t in(g.REFRESH,g.CLEANUP):return super().hook(t)
   assert t in(FREE,DESTRUCTOR)
   if t==DESTRUCTOR and self.destructor_reset:g.put(self.memory,g.RECORD+14,0,2)
   if t==FREE:g.put(self.memory,g.RECORD,0xDEADF00D)
   for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

 count=0;seen=set();case_count=0
 for c,flags,lifetime,delta,destructor,reset in itertools.product(g.cases()[::97],(0xA4,0xA5),(-1,0,32767),(0,0xFFFFFFFF),(-1,0),(0,1)):
  initial=g.fixture(c);initial[g.RECORD+13]=flags;initial[g.RECORD+16]=destructor&255;initial[g.RECORD+17]=11;g.put(initial,g.RECORD+14,lifetime,2);g.put(initial,0x800BE9E4,delta);g.put(initial,0x8008A514,g.ENTRY);g.put(initial,0x8008A4C0,DESTRUCTOR)
  expected=dict(initial)
  if flags&1:g.put(expected,g.RECORD+14,(lifetime-delta)&65535,2)
  expected,calls=g.reference(expected,c);calls=[(g.ENTRY,(g.RECORD,)),*calls]
  if signed16(g.read(expected,g.RECORD+14,2))<0 and destructor!=-1:
   calls.append((DESTRUCTOR,(g.RECORD,)))
   if reset:g.put(expected,g.RECORD+14,0,2)
  if signed16(g.read(expected,g.RECORD+14,2))<0:calls.append((FREE,(g.RECORD,)));g.put(expected,g.RECORD,0xDEADF00D)
  models=[]
  for root in(truth,normalized):
   connected=dict(zip(range(g.ENTRY,g.ENTRY+220,4),root));connected.update(zip(range(g.CLEANUP,g.CLEANUP+40,4),helper))
   m=Oracle(words,initial,c,PARENT,connected,destructor_reset=bool(reset));m.run();assert m.calls==calls and g.public(m.memory,c)==expected,(c,flags,lifetime,delta,destructor,reset,m.calls,calls);assert m.r[29]==m.before[29];models.append(m);seen.update(m.visits);count+=1
  a,b=models;assert(a.r,a.f,a.memory,a.trace,a.hi,a.lo,a.calls)==(b.r,b.f,b.memory,b.trace,b.hi,b.lo,b.calls);case_count+=1
 assert set(range(PARENT,PARENT+180,4))<=seen
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=case_count,executions=count,original_parent_words=45,parent_words_executed=45,retained_parent_equal_original=True,registration_ROM=0x22EFD4,registration_VA=0x8008A514,table='D_8008A4E8',index=11,root_interface='void(struct260 *)',all_callback_arguments_checked=True,full_original_parent_connected=True,real_cleanup_connected=True,signed_timer_wrapping_and_live_reload=True,destructor_and_free_stubbed=True,callback_return_unused=True,complete_bounded_machine_state_equal=True)
 return q
