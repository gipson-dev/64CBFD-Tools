"""All five original pointer consumers and resource-free real cleanup/initializer paths."""
import csv,itertools,json,struct
from dataclasses import replace
from tools.tests import game_slot_allocation_1505ed34_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
WINDOWS=((0x1506C4E0,0x1506C510,(0x1506C510,0x1506C530)),(0x15073140,0x1507316C,(0x1507316C,)),(0x15082B3C,0x15082B78,(0x15082B7C,0x15083298)),(0x15083B08,0x15083B44,(0x15083B44,)),(0x151952A0,0x151952F0,(0x151952F0,)))
RNG,DEFAULT=0x150ADA20,0x150615DC
def census():
 rom=(g.root/'conker/conker.us.bin').read_bytes();rows=list(csv.DictReader((g.root/'conker/retail_layout.us.txt').open()));sites=[];pointers=[]
 for at in range(0,len(rom)-3,4):
  w=struct.unpack_from('>I',rom,at)[0]
  if w==g.ENTRY:pointers.append(hex(at))
  if w>>26 in(2,3)and(w&0x03FFFFFF)<<2==g.ENTRY&0x0FFFFFFF:
   pc=0x10000000+at if at<0x2D4B0 else 0x15000000+at-0x2D4B0 if at<0x255880 else 0x16000000+at-0x255880;owner=[v for v in rows if int(v['address'],16)<=pc<int(v['end'],16)];assert len(owner)==1;sites.append(dict(VA=hex(pc),ROM=hex(at),kind='JAL'if w>>26==3 else'J',parent=owner[0]['function'],owner=owner[0]['filename']))
 assert {int(v['VA'],16)for v in sites}=={v[0]for v in WINDOWS}and len(sites)==5 and all(v['kind']=='JAL'for v in sites)and not pointers
 return dict(sites=sites,aligned_literal_pointers=pointers,computed_indirect_calls_excluded=False)
def original(rom,start,end):return struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0)
def run_window(rom,ws,c,index):
 start,end,ends=WINDOWS[index];memory=g.fixture(c);home=g.STACK+c.phase;chosen,_=g.selection(c);actor=g.TABLE+chosen*812;parent=g.TABLE+((chosen+7)%26)*812
 for at,value in((0xBC,0xC0200000),(0xC0,0x3F000000),(0xC4,0x80000000),(0xC8,0xABCDEFE1),(0x48,0x12345678)):g.put(memory,home+at,value)
 code=dict(zip(range(g.ENTRY,g.ENTRY+380,4),ws));code.update({pc:0 for pc in ends});m=g.Oracle(original(rom,start,end),memory,c,entry=start,connected=code);m.r[3]=0x12345678;m.r[5]=0x76543210;m.r[16]=parent;m.r[17]=0xAB;m.f[10]=0x3F400000;m.code=WindowCode(m.code,m);m.code.ends=ends;m.initial=dict(m.memory);m.before=m.r[:];m.before_f=m.f[:]
 expected=dict(m.initial)
 if index==4:g.put(expected,parent+0x148,0x3F400000)
 expected,calls,value=g.reference(expected,c);calls=[(g.ENTRY,())]+calls
 if index==0:g.put(expected,home+0xEC,0x12345678)
 elif index==1:
  for at,offset in((0x24,0xC4),(0x20,0xC0),(0x3C,0xBC)):g.put(expected,actor+at,g.read(expected,home+offset))
  g.put(expected,actor+0x83,0xE1,1)
 elif index==2:g.put(expected,home+0x6C,0x76543210)
 elif index==3:g.put(expected,actor+0x3B,255-chosen,1);g.put(expected,actor+0xAB,0xAB,1)
 else:
  g.put(expected,actor,40);g.put(expected,actor+0x125,255,1);g.put(expected,actor+0x104,255,1);g.put(expected,actor+4,g.read(expected,parent+4,1),1)
  for at in(0x14,0x18,0x1C,0x40):g.put(expected,actor+at,g.read(expected,parent+at))
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing caller continuation')
 assert m.calls==calls,(c,index,'calls');assert g.public(m.memory)==g.public(expected),(c,index,'public')
 if index==0:assert m.r[16]==actor and m.r[3]==0x12345678 and m.r[1]==int(chosen<25)
 elif index==1:assert m.r[19]==actor and m.r[2]==actor
 elif index==2:assert m.r[16]==actor and m.r[2]==(0 if chosen==25 else chosen)
 elif index==3:assert m.r[18]==actor and m.r[4]==actor and m.r[2]==actor
 else:assert m.r[17]==actor and m.r[2]==actor
 return m
LEAVES={0x1514D310:1,0x151695F0:2,0x15084558:1,0x150626EC:2,0x10010AA8:1,0x150303E4:1,0x15060D54:1,0x15188AD0:1}
def clobber(m,value=0xA5000002):
 for i in range(4):m.put(m.r[29]+4*i,0xB5000000+i,4)
 for reg in(1,2,3,*range(4,16),24,25):m.r[reg]=0xA5000000+reg
 m.f[:20]=[0xA5000000+i for i in range(20)];m.r[2]=value;m.hi,m.lo=0xA5000010,0xA5000011
class ConnectedOracle(g.Oracle):
 def record_call(self,t):
  counts={**LEAVES,g.CLEAN:2,g.INIT:1,RNG:0,DEFAULT:1};assert t in counts,hex(t);args=tuple(map(g.u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t in LEAVES or t==RNG,hex(t)
  if t==RNG:g.put(self.memory,g.MARK+8,g.read(self.memory,g.MARK+8)+1);value=(0,49,50,0x80000000,0xFFFFFFFF)[self.c.seed%5]
  else:
   assert self.calls[-1][1][0]==g.TABLE+g.selection(self.c)[0]*812
   if t in(0x151695F0,0x150626EC):assert self.calls[-1][1][1]==0
   value=0xA5000002
  clobber(self,value)
def initialize(m,actor,c):
 for i in range(812):m[actor+i]=0
 for at,value in((0x14C,0x3F800000),(0x150,0x3F800000),(0x118,0x3E800000),(0x180,0x3E800000),(0x48,0x3F800000),(0x24,0xBF000000),(0x2C4,actor+4)):g.put(m,actor+at,value)
 for at,value in((0x2FD,2),(0x1DC,255),(0x127,255),(0x13F,255),(0x2C8,1),(0x2C9,1),(4,255),(0x2CB,50),(7,255),(8,255),(0xB,255),(0xC,255),(0xD,255),(0xE,255),(0x1DD,255),(0x1DE,255),(0x1DF,255)):g.put(m,actor+at,value,1)
 g.put(m,actor+0x38,(-10000)&65535,2);g.put(m,actor+0x84,65535,2)
 rng=(0,49,50,0x80000000,0xFFFFFFFF)[c.seed%5];g.put(m,g.MARK+8,g.read(m,g.MARK+8)+1);g.put(m,actor+0x6E,rng%50+50,1)
 for at in(0x196,0x198):g.put(m,actor+at,10,2)
def real_helpers(rom,ws,c):
 memory=g.fixture(c);chosen,cleanup=g.selection(c);actor=g.TABLE+chosen*812
 memory[actor+5]=c.poison%4;memory[actor+0x13F]=255
 for at in(0x260,0x264,0x268,0x26C,0x1D8,0x2D4,0x304,0x314,0x2D0,0x324,0x31C):g.put(memory,actor+at,0)
 g.put(memory,g.MARK+8,0);g.put(memory,0x8009962C,0x3E800000);g.put(memory,0x80099630,0xBF000000)
 code={}
 for start,end in((g.CLEAN,0x150611E8),(g.INIT,0x1505F298),(DEFAULT,0x1506160C)):code.update(zip(range(start,end,4),original(rom,start,end)))
 m=ConnectedOracle(ws,memory,c,connected=code);m.run();expected=dict(m.initial);calls=[]
 if cleanup:
  calls.extend(((g.CLEAN,(actor,0)),(0x1514D310,(actor,)),(0x151695F0,(actor,0))))
  if c.poison%4 not in(2,3):calls.extend(((0x15084558,(actor,)),(0x150626EC,(actor,0))))
  calls.extend((t,(actor,))for t in(0x10010AA8,0x150303E4,0x15060D54,0x15188AD0))
  calls.extend(((g.INIT,(actor,)),(RNG,()),(DEFAULT,(actor,))));initialize(expected,actor,c)
 calls.extend(((g.INIT,(actor,)),(RNG,()),(DEFAULT,(actor,))));initialize(expected,actor,c)
 assert m.calls==calls,(c,'real-helper-calls',m.calls,calls);assert g.public(m.memory)==g.public(expected),(c,'real-helper-public');assert m.r[2]==actor and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:],(c,'real-helper-return')
 elf=(g.out/'frozen/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,g.INIT,272);assert elf[at:at+272]==rom[0x8C638:0x8C748]
 return m
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();programs=(g.words(g.out/'selected.o'),original(rom,g.ENTRY,g.ENTRY+380));cs=[replace(c,seed=i%7,phase=(i&1)*8)for i,c in enumerate(g.Case(empty=0,mutation=mu)if mode==0 else g.Case(empty=24,mutation=mu)if mode==1 else g.Case(clear=24,mutation=mu)if mode==2 else g.Case(recycle=24,mutation=mu)if mode==3 else g.Case(reserved=reserved,mutation=mu)for mode,reserved,mu in itertools.product(range(5),(0,1,0xFFFFFFFF),(0,31)))];pairs=0;covered={}
 for index,(start,end,ends)in enumerate(WINDOWS):
  seen=set()
  for c in cs:
   a,b=[run_window(rom,ws,c,index)for ws in programs];assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls);pairs+=1;seen.update(pc for pc in a.visits if start<=pc<end)
  expected=set(range(start,end,4))
  if index==2:expected.remove(0x15082B78)if 0x15082B78 in expected else None
  assert seen==expected,(index,seen^expected);covered[hex(start)]=len(seen)
 helper_pairs=0;helper_seen=set()
 for mode,poison,seed in itertools.product(range(4),range(4),range(5)):
  c=g.Case(empty=24 if mode==0 else -1,clear=24 if mode==1 else -1,recycle=24 if mode==2 else -1,poison=poison,seed=seed)
  a,b=[real_helpers(rom,ws,c)for ws in programs];assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls);helper_pairs+=1;helper_seen.update(pc for pc in a.visits if g.CLEAN<=pc<0x150611E8 or g.INIT<=pc<0x1505F298 or DEFAULT<=pc<0x1506160C)
 result=dict(census=census(),caller_pairs=pairs,caller_executions=2*pairs,caller_window_words=covered,real_helper_pairs=helper_pairs,real_helper_executions=2*helper_pairs,real_helper_covered_words=len(helper_seen),resource_free_cleanup_path_only=True,cleanup_C_stub_unchanged=True,initializer_called_twice_after_real_cleanup=True,full_parent_or_callee_algorithms_qualified=False);(g.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
