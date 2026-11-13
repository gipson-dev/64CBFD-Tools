from tools.tests.game_fade_update_151e4ee8_oracle import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes()
 programs=[struct.unpack_from('>83I',rom,0x212398)]+[program(out/(n+'.o')) for n in ('after','generated','generic')]
 window=struct.unpack_from('>8I',rom,0x212744)
 assert struct.unpack_from('>I',rom,0x2348c8)[0]==ENTRY
 class Connected(Machine):
  def __init__(self,words,c):
   memory=fixture(c);memory[0x800e0b94]=7
   put(memory,0x8008fe08,struct.unpack_from('>I',rom,0x2348c8)[0])
   code=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words));code[0x151e52b4]=0
   FactoryOracle.__init__(self,window,memory,c,entry=0x151e5294,s=S,arguments=(0x12345678,),connected=code)
   self.observed=None;self.code=WindowCode(self.code,self);self.code.ends=(0x151e52b4,)
  def record_call(self,t):
   if t==ENTRY:self.calls.append((t,()))
   else:super().record_call(t)
 count=0
 for a,r,t,l in itertools.product((0,84,109,110,254,255),(0,8,255),(0,1,0xffffffff),(0x3f000000,0x3f800000,0x7fc00000)):
  c=Case(8 if count&1 else 0,a,r,t,l,0x3f000000,count&1)
  expected,obs=reference(c)
  for words in programs:
   m=Connected(words,c)
   try:m.run();raise AssertionError('missing caller boundary')
   except WindowBoundary:pass
   actual=public(m.memory);actual.pop(0x800e0b94,None)
   for i in range(4):actual.pop(0x8008fe08+i,None)
   assert (actual,m.observed)==(expected,obs),(c,m.observed,obs)
   assert m.calls[0]==(ENTRY,()) and len(m.calls)==1+(obs is not None)
  count+=1
 print('original state-table dispatch and return window',count,'cases, four streams')
 cuts=0
 for c in (Case(0,0,0,0,0,0),Case(8,0,8,1,0,0),Case(0,255,8,0,0,0,1),Case(8,84,255,1,0x3f800000,0,0),Case(0,109,255,1,0x3f800000,0,1),Case(8,254,255,1,0x7fc00000,0,1)):
  full=Machine(programs[0],c).run()
  for cut in range(full.all_accesses):
   results=[]
   for words in programs:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',cut))
    except AccessBoundary:pass
    results.append(m)
   a=results[0]
   assert all((m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace)==(a.memory,a.r,a.f,a.hi,a.lo,a.condition,a.trace) for m in results[1:]),(c,cut)
   cuts+=1
 print('retail fault-prefix instruction order',cuts,'access cuts across four streams')
