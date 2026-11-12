"""Connect the retail transition completion call site to the candidate."""
import itertools,struct
from tools.experiments import game_sequence_1501df04_match as match
from tools.tests import game_sequence_1501df04_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions

def run(s):
 entry,end=0x1501e2d4,0x1501e2e8;rom=s['rom'];caller=struct.unpack_from('>5I',rom,0x4b784)
 live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 assert tuple(live['func_1501E1B4'])==struct.unpack_from('>81I',rom,0x4b664)
 class Connected(o.Oracle):
  def __init__(self,initial,c,body):
   self.case=c;self.advances=0;connected=dict(zip(range(o.ENTRY,o.ENTRY+344,4),body))
   o.g.Oracle.__init__(self,caller,initial,c,entry=entry,connected=connected)
   self.r[4]=c.slot;self.r[5]=0x800c3c88;self.r[8]=0x800c3c89;self.r[13]=2;self.r[29]=o.STACK+c.phase-32;self.before=self.r[:]
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,tuple(map(o.g.u32,self.arguments(1)))))
   else:super().record_call(t)
 count=0
 for slot,provider,found,pattern,fa,phase in itertools.product(range(2),range(2),range(2),range(4),range(2),(0,8)):
  c=o.Case(slot,provider,found,pattern,fa,0,0,phase);initial=o.fixture(c);o.put(initial,0x800c3c88,1,1);o.put(initial,0x800c3c89,3,1)
  before=dict(initial);o.put(before,0x800c3c89,0,1);o.put(before,0x800c3c88,2,1);expected,calls=o.reference(before,c);o.put(expected,0x800c3c88,0,1)
  for code in (s['raw_words'],s['retail_words']):
   m=Connected(initial,c,code);m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('caller did not stop')
   except WindowBoundary:pass
   assert (o.public(m.memory),m.calls)==(expected,[(o.ENTRY,(slot,))]+calls),c
  count+=1
 return dict(cases=count,bodies=2,caller='byte-exact original transition completion call site',helpers='modeled')

def real_refresh(s):
 rom=s['rom'];live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 words=struct.unpack_from('>59I',rom,0x4b2c8);assert tuple(live['func_1501DE18'])==words
 connected=dict(zip(range(o.ADVANCE,o.ADVANCE+236,4),words));count=0;seen=set()
 toggles=0x150242f8;close=0x1501ec38;update=0x15020ec4;eligible=0x150229e4;finish=0x1501e81c
 class Connected(o.Oracle):
  def __init__(self,body,c,initial):super().__init__(body,c);self.memory=dict(initial);self.code.update(connected)
  def record_call(self,t):
   counts={toggles:2,close:1,update:1,eligible:1,finish:2}
   if t in counts:self.calls.append((t,tuple(map(o.g.u32,self.arguments(counts[t])))))
   else:super().record_call(t)
  def hook(self,t):
   if t not in (toggles,close,update,eligible,finish):return super().hook(t)
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=0
 for slot,provider,found,phase in itertools.product(range(2),range(2),range(2),(0,8)):
  c=o.Case(slot,provider,found,0,0,0,0,phase);initial=o.fixture(c)
  o.put(initial,0x800c3640+slot*4,100);o.put(initial,0x800bea08,5);o.put(initial,0x800c35b0+slot*4,0);o.put(initial,0x800c3e78,0xff,1)
  expected,calls=o.reference(initial,c);o.put(expected,0x800c35b0+slot*4,105);o.put(expected,0x800c3e78,23,1)
  prefix=[(toggles,(1,0)),(close,(0,)),(toggles,(0,0)),(update,(0,))]+[(eligible,(o.ACTORS+i*0x32c,)) for i in range(1,25,2)]+[(finish,(1,slot))]
  at=calls.index((o.ADVANCE,(slot,)))+1;calls[at:at]=prefix
  for body in (s['raw_words'],s['retail_words']):
   m=Connected(body,c,initial).run();assert (o.public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls)
   seen.update(pc for pc in m.visits if pc in connected)
  count+=1
 return dict(cases=count,helper_words_visited=len(seen),helper_words=len(words),scope='one original actor refresh; nested providers modeled')
