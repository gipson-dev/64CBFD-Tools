from tools.tests.game_hud_state_15178eb0_oracle import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes()
 progs={INIT:streams('func_15178EB0',0x1a6360,19),TRANS:streams('func_15178EFC',0x1a63ac,67)}
 windows=((INIT,0x1500e584,0x3ba34,0x1500e58c),(TRANS,0x1000c3f0,0xc3f0,0x1000c3f8),(TRANS,0x1000c42c,0xc42c,0x1000c434))
 class Connected(Machine):
  def __init__(self,w,c,win):
   target,entry,romoff,end=win;code=dict(zip(range(target,target+len(w)*4,4),w));code[end]=0
   FactoryOracle.__init__(self,struct.unpack_from('>2I',rom,romoff),fixture(c),c,entry=entry,s=S,arguments=(0x12345678,),connected=code)
   self.entrypoint=target;self.dispose_count=0;self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==self.entrypoint:self.calls.append((t,tuple(self.r[4:5])))
   else:super().record_call(t)
 count=0
 for phase,status,array,plan in itertools.product((0,8),(0,3,255),(0,1),range(3)):
  for win in windows:
   target=win[0];c=Case(phase,2,status,array,plan);want,calls=reference(c,target)
   for words in progs[target]:
    m=Connected(words,c,win)
    try:m.run();raise AssertionError('missing caller boundary')
    except WindowBoundary:pass
    expected_arg=0x12345678 if target==INIT else 2
    assert m.calls==[(target,(expected_arg,))]+calls and public(m.memory)==want,(c,win,m.calls,calls)
   count+=1
 print('original init and game caller windows',count,'cases across four streams',flush=True)
 cuts=0
 for c,entry in ((Case(0,0,0,0,0),INIT),(Case(8,2,0,0,0),TRANS),(Case(0,3,3,1,0),TRANS),(Case(8,2,0,1,1),TRANS)):
  full=Machine(progs[entry][0],c,entry).run()
  selected=set(range(min(full.all_accesses,20)))|set(range(max(0,full.all_accesses-20),full.all_accesses))|set(range(0,full.all_accesses,25))
  for cut in sorted(selected):
   results=[]
   streams_to_check=progs[entry] if entry==INIT else (progs[entry][0],progs[entry][2],progs[entry][3])
   for words in streams_to_check:
    m=Machine(words,c,entry);m.cut=cut
    try:m.run();raise AssertionError(('missing cut',cut))
    except AccessBoundary:pass
    results.append(m)
   a=results[0];assert all((m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace)==(a.memory,a.r,a.f,a.hi,a.lo,a.condition,a.trace) for m in results[1:]),(c,cut)
   cuts+=1
 print('retail/padded selected access prefixes',cuts,'cuts; raw transition checked semantically',flush=True)
