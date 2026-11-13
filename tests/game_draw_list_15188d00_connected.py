from tools.tests.game_draw_list_15188d00_oracle import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes()
 programs=[struct.unpack_from('>82I',rom,0x1b61b0)]+[program(out/(n+'.o')) for n in ('after','generated','generic')]
 window=struct.unpack_from('>12I',rom,0x46d18)
 class Connected(Machine):
  def __init__(self,words,c,second):
   memory=fixture(c);put(memory,HEAD+4,NODES[3] if second else 0)
   memory[NODES[3]]=1;put(memory,NODES[3]+0xc,0)
   code=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words));code[0x15019898]=0
   FactoryOracle.__init__(self,window,memory,c,entry=0x15019868,s=S,arguments=(0,),connected=code)
   self.r[16]=output(c);self.r[17]=c.view
   self.code=WindowCode(self.code,self);self.code.ends=(0x15019898,)
  def record_call(self,t):
   if t==ENTRY:self.calls.append((t,tuple(self.r[4:7])))
   else:super().record_call(t)
  def hook(self,t):
   if t in HANDLERS:
    previous=max(i for i,x in enumerate(self.calls) if x[0]==ENTRY)
    actual=sum(x[0] in HANDLERS for x in self.calls[previous+1:])
    c=self.case;a=self.calls[-1][1];result=effect(self.memory,c,a[1],a[0],actual)
    for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
    self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=result
   else:raise AssertionError(hex(t))
 count=0
 for phase,view,length,second,pattern in itertools.product((0,8),(0,1,0x7fff,0x8000,0xffff),range(4),(0,1),(0,1)):
  c=Case(phase,0,view,length,pattern,0)
  want=fixture(c);put(want,HEAD+4,NODES[3] if second else 0);want[NODES[3]]=1;put(want,NODES[3]+0xc,0)
  a,mid=render(want,c,0,output(c));b,end=render(want,c,1,mid)
  for words in programs:
   m=Connected(words,c,second)
   try:m.run();raise AssertionError('missing caller boundary')
   except WindowBoundary:pass
   calls=[x for x in m.calls if x[0]==ENTRY]
   assert calls==[(ENTRY,(output(c),0,s16(view)&0xffffffff)),(ENTRY,(mid,1,s16(view)&0xffffffff))],(c,second,calls)
   assert [x for x in m.calls if x[0] in HANDLERS]==a+b
   assert public(m.memory)==public(want) and m.r[2]==end,(c,second)
  count+=1
 print('original paired draw caller window',count,'cases across four streams',flush=True)
 cuts=0
 for c in (Case(0,0,0,0,0,0),Case(8,1,0xffff,1,0,0),Case(0,0,0x8000,3,1,1),Case(8,1,0x7fff,2,1,2),Case(0,0,1,2,0,3,1)):
  full=Machine(programs[0],c).run()
  for cut in range(full.all_accesses):
   results=[]
   for words in programs:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',cut))
    except AccessBoundary:pass
    results.append(m)
   a=results[0];assert all((m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace)==(a.memory,a.r,a.f,a.hi,a.lo,a.condition,a.trace) for m in results[1:]),(c,cut)
   cuts+=1
 print('guest access prefixes',cuts,'cuts match across four streams',flush=True)
