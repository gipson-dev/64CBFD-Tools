"""Three-provider packet lifecycle, literal byte specification and caller ABI."""
from dataclasses import dataclass
import json,struct
from tools.experiments import game_opening_spray_150c1f60_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
r,o=p.ROOT,p.OUT;ENTRY=0x150c1f60;SPRAY=0x15151a38;BAND=0x15150178
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
GLOBALS=['D_800A%04X'%v for v in range(0x230,0x258,4)]
# Literal specs are independent of source statements, guards and compiler output.
FIRST=[(4,4,0x42200000),(12,4,0x41100000),(24,4,0x3f000000),(36,2,12),(38,2,13),(40,2,-160),(42,2,69),(44,2,-60),(46,2,67),(48,2,3),(50,2,5),(52,2,50),(54,2,31),(56,1,11),(57,1,1),(58,1,40),(60,4,1),(64,4,4),(68,4,0),(72,4,0),(76,4,0),(80,4,0),(84,1,255),(85,1,255),(86,1,0),(88,4,3),(92,4,255),(96,4,0),(100,4,0x220005),(104,4,0x1d0600),(108,4,1),(112,4,59),(116,4,128),(120,4,32),(124,1,0),(125,1,7),(128,2,12),(130,2,21)]
FIRST_FLOATS=[(0,GLOBALS[0]),(8,GLOBALS[1]),(28,GLOBALS[2]),(32,GLOBALS[3]),(16,GLOBALS[4]),(20,GLOBALS[5])]
SECOND=[(36,2,2),(38,2,3),(40,2,-108),(42,2,21),(44,2,-22),(46,2,22),(48,2,7),(50,2,0),(52,2,48),(54,2,21),(28,4,0x42c80000),(32,4,0x42660000),(16,4,0x421c0000),(24,4,0x3f800000)]
SECOND_FLOATS=[(12,GLOBALS[6]),(20,GLOBALS[7])]
HEADER=[(0,2,-159),(2,2,68),(4,2,-52),(6,2,38)]
BAND_FIELDS=[(12,2,25),(14,2,18),(16,4,0x42200000),(20,4,0x420c0000),(24,2,25),(26,2,25),(36,1,155),(37,1,100),(40,4,0x44900000),(44,4,0x44540000),(48,1,1),(49,1,6),(52,4,0),(56,1,1),(60,4,0)]
BAND_FLOATS=[(28,GLOBALS[8]),(32,GLOBALS[9])]
@dataclass(frozen=True)
class Case:
 channel:int=0;seed:int=0;phase:int=0;pattern:int=0;mutation:int=0

def cases():
 for channel in range(256):
  for pattern in range(4):yield Case((0,0xabcd0000,0x80000000,0xffffff00)[pattern]|channel,channel^pattern,8*(pattern&1),pattern,pattern&1)

def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)}
 patterns=[(0,0x80000000,0x3f800000,0xbf800000),(1,0x007fffff,0x7f7fffff,0xff7fffff),(0x7f800000,0xff800000,0x7fc12345,0xffcabcde),(0x7f800001,0xff800001,0x12345678,0x87654321)]
 for i,n in enumerate(GLOBALS):put(m,s[n],patterns[c.pattern][i%4])
 put(m,0x70000,0x13579bdf);return m

def define(m,base,fields,floats=(),s=None):
 s=S if s is None else s
 for at,width,value in fields:put(m,base+at,value,width)
 for at,n in floats:put(m,base+at,read(m,s[n]))

def effect(m,base,stage,c,s):
 if c.mutation:
  # Providers can modify every byte of the packet passed to them. Changes to
  # globals test that subsequent reads occur after the corresponding call.
  for i in range(136):m[base+i]^=(0x55 if stage==1 else 0xa3)
  for i,n in enumerate(GLOBALS):put(m,s[n],0x3e000000+stage*0x10000+i*0x101)
 put(m,0x70000,0xcafebabe+stage)

def expected(initial,c,s=None):
 s=S if s is None else s;m=dict(initial);sp=STACK+c.phase-240;spray=sp+104;band=sp+40;header=sp+32;observations=[]
 define(m,spray,FIRST,FIRST_FLOATS,s);observations.append(('spray',bytes(m[spray+i]for i in range(136))));effect(m,spray,1,c,s)
 define(m,spray,SECOND,SECOND_FLOATS,s);observations.append(('spray',bytes(m[spray+i]for i in range(136))));effect(m,spray,2,c,s)
 for i in range(12):m[band+i]=m[spray+i]
 define(m,header,HEADER);define(m,band,BAND_FIELDS,BAND_FLOATS,s);observations.append(('band',bytes(m[header+i]for i in range(8)),bytes(m[band+i]for i in range(64))))
 return observations

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None,arguments=None):
  super().__init__(words,initial,c,entry=entry,s=S if s is None else s,arguments=(c.channel,)if arguments is None else arguments,connected=connected)
  self.s=S if s is None else s;self.before=self.r[:];self.fp_before=self.f[:];self.snapshots=[];self.stage=0
 def record_call(self,t):
  assert t in(ENTRY,self.s['func_15151A38'],self.s['func_15150178']);n=1 if t==ENTRY else 3 if t==self.s['func_15151A38']else 5;a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.s['func_15151A38']:self.snapshots.append(('spray',bytes(self.memory[a[0]+i]for i in range(136))))
  if t==self.s['func_15150178']:self.snapshots.append(('band',bytes(self.memory[a[0]+i]for i in range(8)),bytes(self.memory[a[1]+i]for i in range(64))))
 def hook(self,t):
  a=self.calls[-1][1];sp=self.r[29];self.stage+=1
  if t==self.s['func_15151A38']:
   assert self.stage<=2 and a==(sp+104,self.case.channel&255,1);effect(self.memory,a[0],self.stage,self.case,self.s)
  else:
   assert t==self.s['func_15150178']and self.stage==3 and a==(sp+32,sp+40,0,self.case.channel&255,1)
   put(self.memory,0x70000,0xcafebac1)
  for i in range(4):put(self.memory,sp+i*4,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=0xdeadbeef;self.lo=0x12345678

def streams(s=None):
 s=S if s is None else s
 return {label:bound_blob(*payload(path,p.FUNCTION),s)for label,path in [('retail',o/'original-target.o'),('raw',o/'selected-final/owner-candidate.o'),('generic',o/'qualified-owner/generic.o'),('generated',o/'qualified-owner/generated.o')]}

def canonical(trace,sp):
 # Only the independently proved five inversions are permitted. The affected
 # final-phase accesses form one contiguous group and have unique keys.
 keys=[('W',sp+92,4),('W',sp+96,1),('W',sp+100,4),('W',sp+16,4),('R',sp+243,1)]
 result=list(trace);hits=[i for i,x in enumerate(result)if tuple(x[:3])in keys]
 # Earlier calls also read incoming channel; only the last five-key group is
 # canonicalized, immediately before the final CALL.
 hits=hits[-5:];assert len(hits)==5 and hits==list(range(hits[0],hits[0]+5)),hits
 group=[result[i]for i in hits];assert {tuple(x[:3])for x in group}==set(keys)
 assert [tuple(x[:3])for x in group]in(keys,[keys[i]for i in(1,3,4,0,2)])
 result[hits[0]:hits[-1]+1]=sorted(group,key=lambda x:keys.index(tuple(x[:3])));return result

def state(m,normalize=True):
 sp=STACK+m.case.phase-240;trace=canonical(m.trace,sp)if normalize else m.trace
 events=canonical(m.events,sp)if normalize else m.events
 return m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.snapshots,trace,events

def check(m,initial,c,s=None):
 s=S if s is None else s;sp=STACK+c.phase-240
 assert m.snapshots==expected(initial,c,s)
 assert m.calls[-3:]==[(s['func_15151A38'],(sp+104,c.channel&255,1)),(s['func_15151A38'],(sp+104,c.channel&255,1)),(s['func_15150178'],(sp+32,sp+40,0,c.channel&255,1))]
 assert m.r[16:24]==m.before[16:24]and m.r[28:30]==m.before[28:30]and m.r[30]==m.before[30]and m.f[20:]==m.fp_before[20:]

def main():
 programs=streams();assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;assert struct.pack('>204I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0xef410:0xef740];count=0;visited=set()
 for c in cases():
  initial=fixture(c);models=[]
  for label,words in programs.items():
   m=Oracle(words,initial,c);m.run();check(m,initial,c);assert m.r[31]==m.before[31];models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);visited|=models[0].visits;count+=1
 q=dict(cases_per_stream=count,streams=4,visited_words=sum(ENTRY+4*i in visited for i in range(204)),all_136_seeded_spray_and_72_band_header_bytes=True,three_provider_lifecycle_and_live_position=True,raw_trace_only_five_proved_private_inversions=True,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q

def faults():
 count=0;programs={k:v for k,v in streams().items()if k!='raw'}
 for c in [Case(),Case(0xffffffff,7,8,3,1)]:
  initial=fixture(c);full=Oracle(programs['retail'],initial,c);full.run()
  for cut in range(full.all_accesses):
   result=[]
   for words in programs.values():
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('cut did not fire')
    result.append(state(m,False))
   assert all(s==result[0]for s in result);count+=1
 q=dict(normalized_retail_fault_prefix_triples=count,raw_fault_prefix_excluded=True,portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q

def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();begin,end=0x150295d4,0x150295e0;words=struct.unpack_from('>3I',rom,0x56a84);count=0
 assert words[0]==0x93a40773 and words[1]==0x0c000000|(ENTRY>>2)&0x3ffffff and words[2]==0xafa400e0
 for c in [Case(),Case(255,7,8,3,1),Case(0x87654321,91,0,1)]:
  initial=fixture(c);put(initial,STACK+c.phase+0x773,c.channel,1);base=STACK+c.phase;models=[]
  for label,target in streams().items():
   code=dict(zip(range(ENTRY,ENTRY+816,4),target));code[end]=0;m=Oracle(words,initial,c,entry=begin,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('window escaped')
   check(m,initial,c);assert m.r[31]==end and m.r[29]==base and read(m.memory,base+0xe0)==c.channel&255;models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);count+=1
 helper=payload(o/'selected-final/helper-candidate.o','func_15150178');assert helper==(bytes.fromhex(p.MANIFEST['helper_hex']),{});stub=bound_blob(*helper,S)
 for c in [Case(),Case(255,9,8,3)]:
  initial=fixture(c);a=(0x50000,0x60000,0xffffffff,c.channel,0x12345678);put(initial,STACK+c.phase+16,a[4]);m=Oracle(stub,initial,c,entry=BAND,arguments=a);m.run();want=dict(initial)
  for i,v in enumerate(a[:4]):put(want,STACK+c.phase+i*4,v)
  assert m.memory==want and m.r==m.before and m.f==m.fp_before and read(m.memory,STACK+c.phase+16)==a[4]
 q=dict(original_caller_window_words=3,cases_per_stream=count,helper_ABI_only_words=6,helper_matching_credit=0,helper_stub_cases=2,fifth_stack_argument_preserved=True,void_result_uncompared=True,enclosing_caller_and_original_helper_implementation_claim=False);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q

if __name__=='__main__':main();faults();callers()
