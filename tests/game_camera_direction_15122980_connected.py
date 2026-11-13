from tools.tests.game_camera_direction_15122980_oracle import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes()
 programs=[struct.unpack_from('>87I',rom,0x14fe30)]+[program(out/(n+'.o')) for n in ('after','generated','generic')]
 windows=((0x15122158,0x14f608,0x15122160,7),(0x15122198,0x14f648,0x151221a0,16))
 class Connected(Machine):
  def __init__(self,words,c,window):
   entry,romoff,end,reg=window
   caller=struct.unpack_from('>2I',rom,romoff);code=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));code[end]=0
   FactoryOracle.__init__(self,caller,fixture(c),c,entry=entry,s=S,arguments=(CAMERA,),connected=code)
   self.r[reg]=CAMERA;self.log=[];self.heading_count=0
   self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==ENTRY:self.calls.append((t,tuple(self.r[4:5])))
   else:super().record_call(t)
 count=0
 for phase,mode,gate,flags,angle,mutation in itertools.product((0,8),(0,4),(0,1),(0,0x100000),(bits(180.),bits(225.),0x7fc00000),range(2)):
  c=Case(phase,mode,gate,flags,angle,mutation);want,events=reference(c)
  for window in windows:
   for words in programs:
    m=Connected(words,c,window)
    try:m.run();raise AssertionError('missing caller boundary')
    except WindowBoundary:pass
    assert m.calls[0]==(ENTRY,(CAMERA,)) and (public(m.memory),m.log)==(want,events),(c,window,m.log,events)
   count+=1
 print('two original camera caller windows',count,'cases across four streams',flush=True)
 cuts=0
 for c in (Case(0,4,0,0,bits(0),0),Case(8,0,0,0,bits(0),0),Case(0,0,1,0,bits(225),1),Case(8,0,1,0x100000,0x7fc00000,3)):
  full=Machine(programs[0],c).run()
  for cut in range(full.all_accesses):
   results=[]
   for words in (programs[0],programs[2],programs[3]):
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',cut))
    except AccessBoundary:pass
    results.append(m)
   a=results[0];assert all((m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.log)==(a.memory,a.r,a.f,a.hi,a.lo,a.condition,a.trace,a.log) for m in results[1:]),(c,cut)
   cuts+=1
 print('retail and padded access prefixes',cuts,'cuts; raw source separately checked by semantic model',flush=True)
