"""Eight-record update contract; connected retail helpers with bounded services."""
import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments.game_record_status_update_150de32c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_resource_status_bit_clear_oracle import Oracle as StatusOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY=0x150DE32C;POINT=0x150A32B4;LOOKUP=0x151149AC;STATUS=0x150A2864;COLLISION=0x150A1DA0;SHIFT=0x100268A4
BASE,OTHER,ACTORS=0x30000,0x40000,0x50000
SYMS={n:int(n.split('_')[1],16)for n in('D_80088950','D_80088958','D_800D3098','func_150A32B4','func_151149AC','func_150A2864','D_800D3094','D_800D30F0','D_800D3270','D_800DBEF0','D_800DBEF4')};SYMS['__ll_lshift']=SHIFT
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:(v^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 x:int=0
 y:int=-17
 z:int=2147483647
 mask:int=255
 mutation:int=0
 pattern:int=0
 phase:int=0
 result:int=1
def indices(c):return (24,25,26,27,13,48,49,50)if c.pattern==0 else tuple((c.pattern*31+i*37)&255 for i in range(8))
def tags(c):return (246,243,240,237,0,0,0,0)if c.pattern==0 else tuple(0 if i%3==0 else (c.pattern*43+i*29)&255 for i in range(8))
def public(m):return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2048)}
 for b,n in((BASE,52*256),(OTHER,52*256),(ACTORS,160*256),(s['D_800D30F0'],16*24+16)):
  m.update({b+i:(i*29+0x59)&255 for i in range(n)})
 for i in range(256):m[ACTORS+i*160+0x72]=i;m[ACTORS+i*160+0x73]=(i*13+c.pattern*11+0xA4)&255
 for n,values in(('D_80088950',indices(c)),('D_80088958',tags(c))):
  for i,v in enumerate(values):m[s[n]+i]=v
 for n,v in(('D_800D3098',BASE),('D_800D3094',256),('D_800DBEF0',256),('D_800DBEF4',ACTORS)):put(m,s[n],v)
 return m
def effect(m,c,s,i):
 if c.mutation&1:put(m,s['D_800D3098'],OTHER if i%2==0 else BASE)
 if c.mutation&2:
  for n in('D_80088950','D_80088958'):
   for j in range(8):m[s[n]+j]^=(17+i)
def apply_status(m,identity,s):
 identity&=4095
 if identity<read(m,s['D_800D3094']):m[read(m,s['D_800D3098'])+52*identity+20]=1
 for i in range(16):
  at=s['D_800D30F0']+24*i+8*(identity>>6);put(m,at,read(m,at,8)&~(1<<(identity&63)),8)
def reference(initial,c,s=SYMS,connected=False):
 m=dict(initial);ids=tuple(m[s['D_80088950']+i]for i in range(8));tt=tuple(m[s['D_80088958']+i]for i in range(8));calls=[]
 for i,(identity,tag)in enumerate(zip(ids,tt)):
  a=(read(m,s['D_800D3098'])+52*identity,u32(c.x),u32(c.y),u32(c.z));calls.append((s['func_150A32B4'],a));effect(m,c,s,i)
  if c.mask>>i&1:
   if tag:
    calls.append((s['func_151149AC'],(tag,)));p=ACTORS+160*tag;m[p+0x73]=(m[p+0x73]&252)|3
   else:calls.append((s['func_150A2864'],(identity,1)));apply_status(m,identity,s)
 return m,calls
class Oracle(StatusOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  FactoryOracle.__init__(self,words,memory,c,entry=entry,s=s,connected=connected,arguments=tuple(map(u32,(c.x,c.y,c.z))))
  self.before=self.r[:];self.before_f=self.f[:];self.query=0;self.external=[]
 def record_call(self,t):
  counts={self.syms['func_150A32B4']:4,self.syms['func_151149AC']:1,self.syms['func_150A2864']:2,COLLISION:3,SHIFT:4}
  assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t not in(COLLISION,SHIFT):self.external.append((t,a))
 def hook(self,t):
  c,s,a=self.case,self.syms,self.calls[-1][1]
  if t==SHIFT:return StatusOracle.hook(self,t)
  if t in(s['func_150A32B4'],COLLISION):
   if t==COLLISION:
    expected=tuple(bits(float(v))for v in(c.x,c.y,c.z))
    assert tuple(read(self.memory,a[0]+j)for j in(0x14,0x18,0x1C,0x2C,0x30,0x34,0x180))==(expected[0],expected[1],expected[2],expected[0],expected[1],expected[2],expected[1])
    assert a[2]==0
   hit=c.mask>>self.query&1;effect(self.memory,c,s,self.query);self.query+=1;value=(0 if hit else 7)if t==COLLISION else(c.result if hit else 0)
  elif t==s['func_151149AC']:value=ACTORS+160*a[0]
  else:assert t==s['func_150A2864']and a[1]==1;apply_status(self.memory,a[0],s);value=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for j in(1,2,3,*range(4,16),24,25):self.r[j]=0xA5000000+j
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(value);self.hi,self.lo=0xA5000010,0xA5000011
def words(path,s=SYMS):
 t,fs,rs=parse_object(path);f=fs['func_150DE32C'];return bound_blob(t[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']},s)
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.dispatched_word)
def check(m,initial,c,s=SYMS):
 expected,calls=reference(initial,c,s);assert(public(m.memory),m.external)==(public(expected),calls),(c,m.external,calls)
 assert m.query==8 and m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[30:]==m.before[30:]and m.f[20:]==m.before_f[20:]
def cases():
 for mask in range(256):yield Case(mask=mask,pattern=mask%7,mutation=mask%4,phase=(mask%2)*8,result=(-3 if mask%2 else 7))
 for x,mutation,pattern in itertools.product((-2147483648,-16777217,-1,0,1,16777217,2147483647),range(4),range(8)):
  yield Case(x=x,y=-x if x!=-2147483648 else 2147483647,z=x,mutation=mutation,pattern=pattern)
def main():
 ps=[words(out/n)for n in('retail-reference.o','qualified-padded.o','qualified-owner.o')];assert ps[0]==ps[1];visited=set();count=0
 for c in cases():
  initial=fixture(c);pair=[]
  for ws in ps:
   m=Oracle(ws,initial,c).run();check(m,initial,c);pair.append(m)
  assert state(pair[0])==state(pair[1]);visited.update(pair[0].visits);count+=1
 assert len(visited)==75,len(visited)
 prefixes=delay=0
 for c in(Case(),Case(mask=0),Case(pattern=3,mutation=3,phase=8)):
  initial=fixture(c);full=Oracle(ps[0],initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for ws in ps[:2]:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access boundary')
    except AccessBoundary:pass
    pair.append(m)
   assert state(pair[0])==state(pair[1]);prefixes+=1;delay+=pair[0].delay_of is not None
 rebases=0
 for j in range(6):
  s={k:v+j*(0x20000 if k.startswith('func_')else 0x108000)for k,v in SYMS.items()};entry=ENTRY+j*0x10000
  qs=[words(out/n,s)for n in('retail-reference.o','qualified-padded.o','qualified-owner.o')];assert qs[0]==qs[1]
  for c in(Case(),Case(mask=0),Case(pattern=7,mutation=3)):
   initial=fixture(c,s)
   for ws in qs:m=Oracle(ws,initial,c,entry,s).run();check(m,initial,c,s)
   rebases+=1
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'frozen/conker/build/conker.us.elf').read_bytes();code={};helpers=[]
 for addr,off,n in((POINT,0xD0764,31),(LOOKUP,0x141E5C,28),(STATUS,0xCFD14,55)):
  truth=rom[off:off+n*4];at=elf_slot_offset(elf,addr,n*4);assert elf[at:at+n*4]==truth
  code.update(zip(range(addr,addr+n*4,4),struct.unpack('>%dI'%n,truth)));helpers.append(dict(entry=hex(addr),words=n,baseline_exact=True))
 connections=0
 for c in(Case(x=x,mutation=mutation,pattern=pattern)for x,mutation,pattern in itertools.product((-2147483648,-16777217,0,16777217,2147483647),range(4),range(2))):
  initial=fixture(c);pair=[]
  for ws in ps:m=Oracle(ws,initial,c,connected=code).run();check(m,initial,c);pair.append(m)
  assert state(pair[0])==state(pair[1]);connections+=1
 report=dict(cases_per_body=count,executions=count*3,visited_body_words=75,fault_prefix_pairs=prefixes,delay_slot_faults=delay,rebase_layouts=6,rebase_cases=rebases,connected_original_helper_cases=connections,helpers=helpers,raw_C_public_contract_equal=True,normalized_literal_state_equal=True,no_direct_or_aligned_pointer_caller_found=True,computed_callers_not_ruled_out=True,bounded_services=['collision result and mutations','SDK split64 shift'],hardware_FCSR_claim=False)
 (out/'guest-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
