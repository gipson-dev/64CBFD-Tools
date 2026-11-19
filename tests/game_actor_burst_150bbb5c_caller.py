"""Execute the complete original caller for its burst-selection input domain."""
from dataclasses import replace
from pathlib import Path
import hashlib,itertools,json,math,struct,sys
from tools.experiments import game_actor_burst_150bbb5c_ordered as s
from tools.tests import game_actor_burst_150bbb5c_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import floating,bits

P=s.OUT
ENTRY=0x1507D754;CALLER_ROM=0xAAC04;COUNT=252;ALTERNATE=0x150BC488
TABLE=0x8009B6DC;TABLE_SIZE=(27+79)*4;MARK=0x70000

def state():
 elf=(s.FROZEN/'conker/build/conker.us.elf').read_bytes();rom=(s.FROZEN/'conker/conker.us.bin').read_bytes()
 data=rom[CALLER_ROM:CALLER_ROM+COUNT*4]
 at=elf_slot_offset(elf,ENTRY,len(data));assert elf[at:at+len(data)]==data
 at=elf_slot_offset(elf,TABLE,TABLE_SIZE);table=elf[at:at+TABLE_SIZE]
 found=rom.find(table);assert found>=0 and rom.find(table,found+1)<0
 assert rom[found:found+TABLE_SIZE]==table
 lower=struct.unpack('>79I',table[27*4:]);upper=struct.unpack('>27I',table[:27*4])
 ids=[i+5 for i,target in enumerate(lower) if 0x1507DAA0<=target<=0x1507DAD8]
 ids += [i+0x77 for i,target in enumerate(upper) if 0x1507DAA0<=target<=0x1507DAD8]
 assert ids==[32],ids
 assert lower[32-5]==0x1507DAA0
 assert hashlib.sha256(data).hexdigest()==s.PIN['caller_sha256']
 assert hashlib.sha256(table).hexdigest()==s.PIN['table_sha256']
 code=s.state()
 return struct.unpack('>252I',data),table,code,dict(original_caller_words=COUNT,production_caller_literal=True,
    caller_sha256=hashlib.sha256(data).hexdigest(),table_bytes=TABLE_SIZE,table_rom=found,
    table_sha256=hashlib.sha256(table).hexdigest(),table_entry_identities=ids)

def alternate_effect(m,c):
 g.put(m,MARK,0x5C00BEEF)
 g.put(m,c.actor+0x1C,bits(19.25+c.seed))

class Caller(g.Oracle):
 def __init__(self,words,memory,c,connected):
  FactoryOracle.__init__(self,words,memory,c,entry=ENTRY,s={},arguments=(c.actor,),connected=connected)
  self.cc=c;self.calls=[];self.obs=[];self.indices={t:0 for t in g.COUNTS}
  self.saved={i:self.r[i]for i in(*range(16,24),28,29,30)};self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(60,62):
   left,right=floating(self.f[w>>11&31]),floating(self.f[w>>16&31])
   self.condition=left<right if w&63==60 else left<=right
   return
  return super().execute(w)
 def record_call(self,target):
  if target in(g.ENTRY,ALTERNATE):
   args=tuple(self.arguments(1));assert args==(self.cc.actor,),('caller actor forwarding',hex(target),args)
   self.calls.append((target,args));return
  return super().record_call(target)
 def hook(self,target):
  if target!=ALTERNATE:return super().hook(target)
  alternate_effect(self.memory,self.cc)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)]
  self.r[2]=0xFEDCBA98;self.hi=self.lo=0xDEADBEEF

VELOCITIES=(0xC1A00001,0xC1A00000,0xC19FFFFF,0x80000000,0x7FC00001,0x7F800000)
def rows():
 for seed,pattern,mutation,phase,gate,velocity in itertools.product(range(16),range(4),(0,1),(0,8),(1,2),VELOCITIES):
  yield g.Case(seed,pattern,mutation,phase,gate),velocity

def fixture(c,velocity,table):
 initial=g.fixture(c);g.put(initial,c.actor+0x20,velocity);g.put(initial,c.actor+0x24,bits(5.));g.put(initial,MARK,0)
 initial.update({TABLE+i:v for i,v in enumerate(table)})
 return initial

def reference(initial,c,velocity):
 alternate=floating(velocity)<-20.
 if alternate:
  final=dict(initial);alternate_effect(final,c)
  return (g.public(final),[(ALTERNATE,(c.actor,))],[]),True
 final,calls,obs=g.reference(initial,c)
 return (final,[(g.ENTRY,(c.actor,))]+calls,obs),False

def compare(words,body,initial,c,wanted,alternate):
 # The private unpadded raw body extends into the following retail slot.
 # Do not map an unused raw body on the mutually exclusive alternate path.
 connected={} if alternate and len(body)>587 else dict(zip(range(g.ENTRY,g.ENTRY+len(body)*4,4),body))
 machine=Caller(words,initial,c,connected).run()
 assert (g.public(machine.memory),machine.calls,machine.obs)==wanted,('caller observations',c,alternate,machine.calls[:3],wanted[1][:3])
 assert machine.r[2]==0,('caller discarded return',machine.r[2])
 assert all(machine.r[i]==v for i,v in machine.saved.items()) and tuple(machine.f[20:])==machine.saved_fp
 return machine

def run(limit=None):
 words,table,programs,metadata=state();seen=set();target_seen=set();count=0;alternates=0;active=0
 for c,velocity in itertools.islice(rows(),limit):
  initial=fixture(c,velocity,table);wanted,alternate=reference(initial,c,velocity)
  for label,body in programs.items():
   machine=compare(words,body,initial,c,wanted,alternate)
   seen|=machine.visits&set(range(ENTRY,ENTRY+COUNT*4,4))
   if label=='retail':target_seen|=machine.visits&set(range(g.ENTRY,g.ENTRY+587*4,4))
  count+=1;alternates+=alternate;active+=not alternate and c.gate==2
  if count%512==0:print(json.dumps(dict(completed=count)),flush=True)
 report=dict(passes=True,cases=count,programs=2,executions=count*2,alternate_cases=alternates,
    active_burst_cases=active,caller_words_visited=len(seen),target_words_visited=len(target_seen),
    caller_type_domain=[32],velocity_boundary_and_quiet_nan_checked=True,return_ignored_and_caller_zero=True,
    other_dispatch_arms_qualified=False,alternate_helper='opaque ABI service',raw_physical_overlay_coexistence_claimed=False,
    source_installed=False,c_match_credit=0,**metadata)
 (P/('caller-report.json'if limit is None else'caller-pilot.json')).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True)
 return report

def controls():
 words,table,programs,metadata=state();report=[]
 forms=[('wrong-velocity-offset',0x1507DAA8,0xC60A0024),
  ('inclusive-threshold',0x1507DAAC,0x4610503E),
  ('wrong-actor-forwarding',0x1507DAD0,0x02202025),
  ('wrong-burst-return-clear',0x1507DAD8,0x24020001),
  ('wrong-alternate-return-clear',0x1507DAC8,0x24020001)]
 cases=[(g.Case(seed=0,pattern=0,mutation=1,gate=2),v)for v in VELOCITIES[:3]]
 for label,address,replacement in forms:
  bad=list(words);bad[(address-ENTRY)//4]=replacement;witness=None
  for c,velocity in cases:
   initial=fixture(c,velocity,table);wanted,alternate=reference(initial,c,velocity)
   try:compare(bad,programs['retail'],initial,c,wanted,alternate)
   except AssertionError as error:witness=dict(velocity=hex(velocity),reason=str(error)[:240]);break
  assert witness is not None,('ineffective caller control',label)
  report.append(dict(label=label,effective=True,witness=witness))
 # Redirect the real selector entry to the alternate call arm.
 badtable=bytearray(table);struct.pack_into('>I',badtable,27*4+(32-5)*4,0x1507DABC)
 c,velocity=cases[1];initial=fixture(c,velocity,bytes(badtable));wanted,alternate=reference(initial,c,velocity)
 try:compare(words,programs['retail'],initial,c,wanted,alternate)
 except AssertionError as error:report.append(dict(label='redirected-table-entry',effective=True,reason=str(error)[:240]))
 else:raise AssertionError('ineffective selector table control')
 result=dict(passes=True,effective_controls=len(report),controls=report,source_installed=False,c_match_credit=0)
 (P/'caller-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
 return result
