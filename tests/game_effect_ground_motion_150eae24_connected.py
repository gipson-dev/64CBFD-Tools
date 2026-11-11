import itertools,json,struct
from tools.experiments import game_effect_ground_motion_150eae24_match as p
from tools.tests import game_effect_ground_motion_150eae24_oracle as g
from tools.tests.test_game_point_transform_match import put,read
PRE=0x15047004;FALLBACK=0x1504697C
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();original=struct.unpack_from('>32I',rom,0x74130);code=dict(zip(range(g.HELPER,g.HELPER+4*len(original),4),original));raw,refs=p.payload(p.out/'independent-selected.o');lookup={v[1]:v[2][1] for v in p.symbol_rows((p.out/'frozen/conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{n:lookup[n] for es in refs.values() for _,n in es})
 class Connected(g.Oracle):
  def __init__(self,words,c,mode):self.result_mode=mode;super().__init__(words,c,connected=code)
  def record_call(self,t):
   if t in (PRE,FALLBACK):self.calls.append((t,tuple(self.arguments(3 if t==PRE else 4))))
   else:super().record_call(t)
  def hook(self,t):
   if t not in (PRE,FALLBACK):return super().hook(t)
   args=self.calls[-1][1]
   if t==PRE:
    assert args[1:]==(self.c.query,g.ACTOR+0x34)
    if self.c.mutation:put(self.memory,g.ACTOR+0x14,g.OUT2);put(self.memory,g.ACTOR+0x28,g.b(-11.5));put(self.memory,g.DELTA,g.b(.25))
    put(self.memory,g.ACTOR+0x34,g.b(19.75));value=self.result_mode
   else:
    assert self.result_mode==0 and args[1:]==(0,self.c.query,g.ACTOR+0x34);value=self.c.answer
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value
 visits=set();count=0
 for mode,answer,mutation,phase in itertools.product((0,1,2),(0,1),(0,1),(0,8)):
  if (mode==1 and answer!=0) or (mode==2 and answer!=1):continue
  c=g.Case(*(g.b(v) for v in (1.25,-2.75,.5,-1.5,8.5,-2.25,2.,.5)),answer,mutation,phase,count%3);m=Connected(words,c,mode);m.run();want,result,point=g.ref(c,m.initial);assert g.public(m.memory)==g.public(want) and m.r[2]==result and m.points==[point];assert [t for t,a in m.calls]==[g.HELPER,PRE]+([FALLBACK] if mode==0 else []),(mode,answer,mutation,m.calls);assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:],('saved',mode,answer,mutation);visits.update(m.visits);count+=1
 report=dict(cases=count,original_ground_helper_words=32,original_ground_helper_words_visited=sum(g.HELPER+4*i in visits for i in range(32)),precheck_and_fallback_modeled=True,finite_float_only=True,source_installed=False);(p.out/'connected-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
