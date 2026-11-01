"""Record flag callback: guest bit/ABI checks, original dispatcher and helper."""
from tools.tests.test_game_character_effect_pair import WindowCode
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_classifier_candidates import sections
r=o=None;F='func_15014144';ENTRY=0x15014144;RECORD,MARK=0x30000,0x70000
@dataclass(frozen=True)
class Case:
 bits:int=0
 selector:int=0
 height:int=0
 phase:int=0
 mode:int=0
def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for base,size in((RECORD-16,96),(MARK,16),(s['D_8009667C'],4)):m.update({base+i:(i*29+90)&255 for i in range(size)})
 put(m,RECORD+24,c.bits);m[RECORD+31]=c.selector;put(m,s['D_8009667C'],c.height);return m
def public(m,c):return {a:b for a,b in m.items() if not STACK+c.phase-512<=a<STACK+c.phase}
def args(c,s):return ((c.bits&31)^2,c.selector,RECORD,0,c.height,0x42C80000,0xFFFFFFFF,255,1)
def effect(m,c,s):
 put(m,MARK,0x13579BDF)
 if c.mode:put(m,RECORD+24,0xFEDCBA98);m[RECORD+31]=0xFF;put(m,s['D_8009667C'],0xDEADBEEF)
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;super().__init__(words,memory,c,entry=entry,s={},arguments=(RECORD,),connected=connected);self.before_f=self.f[:]
 def record_call(self,t):
  assert t==self.s['func_151A9390'],hex(t);a=tuple(self.arguments(9));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  effect(self.memory,self.c,self.s)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def programs(layout):
 entry=ENTRY+layout*0x01000000;s=dict(D_8009667C=(0x8009667C,0x80107FFC,0x80208004)[layout],func_151A9390=(0x151A9390,0x17200000,0x1827FFFC)[layout]);roots=[]
 for label,obj in(('original',o/('original-'+F+'.o')),('private',o/'selected-final.o')):
  script=o/('guest-%d-%s.ld'%(layout,label));script.write_text('SECTIONS{.text 0x%X : SUBALIGN(4) {*(.text)}}\n'%entry);elf=script.with_suffix('.elf')
  q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',F,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr;roots.append(struct.unpack('>55I',sections(elf)['.text'][1][:220]))
 assert roots[0]==roots[1];return entry,s,roots

def qualify(root,output):
 global r,o
 r,o=root,output
 cases=[Case(low|high,selector,height,phase,mode)for low,high,selector,height,phase,mode in itertools.product(range(32),(0,0x80000000),(0,8,9,255),(0,0x80000000,0x3F800000,0x7FC12345),(0,8),(0,1))]
 done=0
 for layout in range(3):
  entry,s,roots=programs(layout);seen=set()
  for c in cases:
   initial=fixture(c,s);expected=dict(initial);effect(expected,c,s);models=[]
   for root in roots:
    m=Oracle(root,initial,c,s,entry);m.run();assert public(m.memory,c)==public(expected,c);assert m.calls==[(s['func_151A9390'],args(c,s))];assert m.r[2]==1;models.append(m);seen.update(m.visits);done+=1
   assert models[0].memory==models[1].memory and models[0].trace==models[1].trace and models[0].r==models[1].r
  assert set(range(entry,entry+220,4))<=seen
 c=Case(31,8,0x7FC12345,8,1);entry,s,roots=programs(0);m=Oracle(roots[0],fixture(c,s),c,s,entry);m.run();cuts=m.all_accesses
 for cut in range(cuts):
  models=[]
  for root in roots:
   m=Oracle(root,fixture(c,s),c,s,entry);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError('Access cut ineffective')
   models.append(m)
  assert models[0].memory==models[1].memory and models[0].trace==models[1].trace
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=len(cases)*3,executions=done,rebases=3,retail_words_covered=55,complete_nine_argument_boundary=True,all_low_five_flag_combinations=True,high_bit_patterns=2,selector_boundaries=[0,8,9,255],global_float_bits_preserved=True,complete_public_memory_and_call_trace=True,original_private_complete_machine_memory_register_trace_equal=True,return_one_after_caller_saved_clobber=True,access_prefix_cuts=cuts,access_prefix_executions=cuts*2,full_fault_register_equivalence_claim=False)
 (o/'private-guest-runtime.json').write_text(json.dumps(q,indent=2)+'\n');print(q,flush=True)
 # Static retail inventory distinguishes direct calls from table references.
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom);census=dict(target=F,aligned_ROM_JALs=[i*4 for i,w in enumerate(words)if w==0x0C000000|((ENTRY>>2)&0x3FFFFFF)],aligned_ROM_Js=[i*4 for i,w in enumerate(words)if w==0x08000000|((ENTRY>>2)&0x3FFFFFF)],aligned_ROM_pointer_literals=[i*4 for i,w in enumerate(words)if w==ENTRY],table='D_80082E30',index=18,original_dispatcher='func_15013000')
 assert census['aligned_ROM_JALs']==[]and census['aligned_ROM_Js']==[]and census['aligned_ROM_pointer_literals']==[0x227938],census
 (o/'caller-census.json').write_text(json.dumps(census,indent=2)+'\n')
 return q,census

def dispatch(root,output):
 global r,o
 r,o=root,output
 import sys
 g=sys.modules[__name__]
 r=g.r;rom=(r/'conker/conker.us.bin').read_bytes();entry,s,roots=g.programs(0);start=0x15013000;words=struct.unpack_from('>45I',rom,0x404B0);TABLE,COUNT,BASE,ALT=0x80082E30,0x800D3094,0x800D3098,0x60000
 ACCUM,ACCUMF=0x800DCDC4,0x800DCD90;done=0;seen=set();reloads=0
 for bits,selector,phase,count,mode,poison in itertools.product((0,1,2,4,8,16,31,0xFFFFFFFF),(0,8,9,255),(0,8),(0,1,2),(0,1,2),(0,1,0x80000000,0xFFFFFFFF)):
  c=g.Case(bits,selector,0x7FC12345,phase,mode);initial=g.fixture(c,s)
  for base,size in((TABLE,26*4),(g.RECORD+80,80),(ALT,128),(COUNT,8),(ACCUM,4),(ACCUMF,4)):initial.update({base+i:0xA5 for i in range(size)})
  for i in range(26):g.put(initial,TABLE+4*i,0)
  g.put(initial,TABLE+18*4,entry);g.put(initial,COUNT,count);g.put(initial,BASE,g.RECORD);initial[g.RECORD+21]=72;initial[g.RECORD+52+21]=0;initial[ALT+52+21]=0
  expected=dict(initial);g.put(expected,ACCUM,0);g.put(expected,ACCUMF,0)
  if count:
   g.effect(expected,c,s)
   if mode==1:g.put(expected,COUNT,0)
   if mode==2:g.put(expected,BASE,ALT)
  for root in roots:
   class Caller(g.Oracle):
    def record_call(self,t):
     if t==entry:self.boundaries.append(tuple(self.arguments(1)));return
     return super().record_call(t)
    def hook(self,t):
     super().hook(t)
     if mode==1:g.put(self.memory,COUNT,0)
     if mode==2:g.put(self.memory,BASE,ALT)
   m=Caller(words,initial,c,s,start,dict(zip(range(entry,entry+220,4),root)));m.boundaries=[]
   class Code(WindowCode):
    def __getitem__(self,pc):
     if pc==0x15013080:self.owner.r[2]=poison;self.owner.poison_hits+=1
     return super().__getitem__(pc)
   m.code=Code(m.code,m);m.code.ends=();m.poison_hits=0;m.run();assert g.public(m.memory,c)==g.public(expected,c),(bits,selector,count,mode)
   assert m.boundaries==([(g.RECORD,)]if count else[]);assert m.calls==([(s['func_151A9390'],g.args(c,s))]if count else[]);assert m.poison_hits==int(bool(count));seen.update(m.visits);done+=1
   if count==2 and mode==2:assert ('R',ALT+52+21,1,0)in m.trace;reloads+=1
 assert set(range(start,start+180,4))<=seen
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=done//2,executions=done,original_dispatcher_words=45,all_original_dispatcher_words_covered=True,actual_table_index=18,return_poisons=4,callback_result_ignored=True,zero_one_two_records=True,null_callback_route=True,live_count_and_base_reloads=True,relocated_second_record_reads=reloads,complete_dispatcher_emulated=True)
 (o/'private-dispatch-runtime.json').write_text(json.dumps(q,indent=2)+'\n');print(q,flush=True)
 return q

def helper(root,output):
 global r,o
 r,o=root,output
 import sys
 g=sys.modules[__name__]
 r=g.r;rom=(r/'conker/conker.us.bin').read_bytes();entry,s,roots=g.programs(0);HELPER=s['func_151A9390'];TABLE,TEMPLATES,OUTPUT=0x8008F9AC,0x90000,0x50000;FACTORY,COPY,SECOND=0x151A8B20,0x10022EC0,0x1516284C
 words=struct.unpack_from('>169I',rom,0x1D6840);copy=struct.unpack_from('>11I',rom,0x22EC0);connected=dict(zip(range(HELPER,HELPER+676,4),words));connected.update(zip(range(COPY,COPY+44,4),copy))
 def fixture(c):
  m=g.fixture(c,s)
  for base,size in((TABLE,180),(TEMPLATES,9*64),(OUTPUT,512)):m.update({base+i:(i*29+90)&255 for i in range(size)})
  for i in range(9):
   at=TABLE+20*i;g.put(m,at,0x3F800000+i*0x10000);g.put(m,at+4,0x40000000+i*0x10000)
   for j in range(8,13):m[at+j]=i+j*3
   g.put(m,at+16,TEMPLATES+i*64)
  for at,v in((0,0x8000),(2,0x7FFF),(4,0xFFFF)):g.put(m,g.RECORD+at,v,2)
  return m
 def mutate(m,c):
  if c.mode:
   for at,v in((0,0xFFFF),(2,0x8000),(4,0x7FFF)):g.put(m,g.RECORD+at,v,2)
 class Oracle(g.Oracle):
  def record_call(self,t):
   if t==HELPER:return super().record_call(t)
   assert t in(FACTORY,COPY,SECOND),hex(t);a=tuple(self.arguments({FACTORY:5,COPY:3,SECOND:11}[t]));self.calls.append((t,a))
   if t==FACTORY:
    p=a[0];self.factory_packets.append((self.get(p,1),tuple(g.read(self.memory,p+at)for at in(4,8,12,16,20,24,28,32)),tuple(self.get(p+at,1)for at in(36,37,38))))
   if t==SECOND:
    self.second_packets.append((tuple(self.get(a[0]+at,n)for at,n in((0,1),(1,1),(2,2),(4,1))),tuple(g.read(self.memory,a[1]+i*4)for i in range(3))))
  def hook(self,t):
   assert t in(FACTORY,SECOND),hex(t)
   if t==FACTORY:mutate(self.memory,self.c);g.put(self.memory,g.MARK,0x13579BDF);value=OUTPUT if self.outcome else 0
   else:g.put(self.memory,g.MARK+4,0x2468ACE0);value=0xDEADBEEF
   for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value
 seen=set();done=0
 for bits,selector,phase,mode,outcome in itertools.product(range(32),(0,8,9,255),(0,8),(0,1),(0,1)):
  c=g.Case(bits,selector,0x7FC12345,phase,mode);initial=fixture(c);expected=dict(initial);flags=(bits&31)^2;h=g.STACK+phase-48-152;calls=[(HELPER,g.args(c,s))];factory_packets=[];second_packets=[]
  if selector<9:
   row=TABLE+20*selector;packet=h+0x70;calls.append((FACTORY,(packet,0xFFFFFFFF,44,255,1)));mutate(expected,c);g.put(expected,g.MARK,0x13579BDF)
   factory_packets=[(3|(4 if flags&1 else 0)|(8 if flags&2 else 0),(g.RECORD,g.read(initial,row),g.read(initial,row+4),0,0,0,c.height,0x42C80000),(2,255,1))]
   if outcome:
    src=g.read(initial,row+16);calls.append((COPY,(OUTPUT+128,src,44)))
    for i in range(44):expected[OUTPUT+128+i]=initial[src+i]
    expected[OUTPUT+168]|=(1 if flags&8 else 0)|(2 if flags&16 else 0)
   if flags&4:
    calls.append((SECOND,(h+0x60,h+0x54,initial[row+8],initial[row+9],initial[row+10],255,0,0,initial[row+12],255,1)))
    xyz=tuple(((g.read(expected,g.RECORD+2*i,2)^32768)-32768)&0xFFFFFFFF for i in range(3));second_packets=[((2,2,300,initial[row+11]),xyz)];g.put(expected,g.MARK+4,0x2468ACE0)
  for root in roots:
   m=Oracle(root,initial,c,s,entry,connected);m.outcome=outcome;m.factory_packets=[];m.second_packets=[];m.run()
   assert g.public(m.memory,c)==g.public(expected,c),(bits,selector,mode,outcome,'memory');assert m.calls==calls,(bits,selector,m.calls,calls);assert m.factory_packets==factory_packets,(m.factory_packets,factory_packets);assert m.second_packets==second_packets,(m.second_packets,second_packets);assert m.r[2]==1;seen.update(m.visits);done+=1
 required=set(range(HELPER,HELPER+676,4));missing=sorted(required-seen)
 assert set(range(COPY,COPY+44,4))<=seen
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=done//2,executions=done,original_helper_words=169,helper_words_executed=169-len(missing),unexecuted_helper_PCs=[hex(p)for p in missing],original_memcpy_words=11,all_copy_words_executed=True,full_original_helper_emulated=True,lower_factory_and_secondary_calls_stubbed=True,lower_factory_payload_checked=True,second_payload_and_signed_live_coordinates_checked=True,selector_zero_eight_nine_255=True,allocation_failure_success=True,template_copy_and_output_flags_checked=True,return_one_after_original_helper=True)
 (o/'private-helper-runtime.json').write_text(json.dumps(q,indent=2)+'\n');print(q,flush=True)
 return q
