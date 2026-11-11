import itertools,json,struct
from tools.experiments import game_startup_initializer_1500e470_match as p
from tools.tests import game_startup_initializer_1500e470_oracle as g
def main():
 g.load_words()
 rom=(p.root/'conker/conker.us.bin').read_bytes();original=struct.unpack_from('>39I',rom,0x226f0);code=dict(zip(range(g.ZERO,g.ZERO+4*len(original),4),original));visits=set();count=0
 for sel,flags,seed in itertools.product((0,1,2),(0,0x80),(0,1)):
  c=g.Case(sel,flags,seed);machines=[]
  for words in (g.retail,g.candidate,g.fixed):
   m=g.Oracle(words,c,connected=code);m.run();assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];assert all(m.memory[0x800DD198+i]==0 for i in range(24));machines.append(m)
  assert all(g.public(m.memory)==g.public(machines[0].memory) and m.calls==machines[0].calls for m in machines[1:]);assert (machines[0].memory,machines[0].r,machines[0].f,machines[0].trace)==(machines[2].memory,machines[2].r,machines[2].f,machines[2].trace);visits.update(machines[0].visits);count+=1
 report=dict(cases=count,original_bzero_words=39,original_bzero_words_visited=sum(g.ZERO+4*i in visits for i in range(39)),other_helpers_modeled=True,source_installed=False);(p.out/'connected-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
