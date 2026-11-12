from pathlib import Path
import sys,random,json,itertools,importlib.util
from tools.experiments import game_position_interpolation_match as source
root=source.root;p=source.out
from tools.tests import game_position_interpolation_guest as g

def main():
 rng=random.Random(0xbecad); factors=(0,0x80000000,0x3dcccccd,0x3eaaaaab,0x3f000000,0x3f800000,0xbf000000,0xbf800000,0x40000000,1,0x80000001);ticks=(0,1,2,3,-1,-2,31,-31,0x7fffffff,-0x80000000);actors=(0x20000,0x800A0068-0x10,0x800BE9E4-0x10,0x800A0068-0x3c)
 counts={'tested':0,'out_of_range_skipped':0,'alias_tested':0}; ext=set(); sign=set()
 for i,(factor,tick,actor) in enumerate(itertools.product(factors,ticks,actors)):
  for j in range(5):
   values=[rng.choice((-32768,-16384,-1,0,1,16384,32767,rng.randrange(-32768,32768))) for _ in range(8)];m=g.fixture(actor,values,tick,factor)
   try:ret=g.run(g.ret,m,actor);raw=g.run(g.candidate,m,actor)
   except AssertionError as e:
    if e.args and isinstance(e.args[0],tuple) and e.args[0][0]=='float outside bounded model':counts['out_of_range_skipped']+=1;continue
    raise
   assert ret==raw,(factor,tick,actor,values);counts['tested']+=1;counts['alias_tested']+=actor!=0x20000;ext.add(factor);sign.add(tick)
 assert len(ext)==len(factors) and len(sign)==len(ticks);print(json.dumps(dict(counts=counts,factors_covered=len(ext),tick_values_covered=len(sign),scope='finite, bounded conversion model; raw versus retail memory and access ordering'),indent=2))


if __name__ == "__main__":main()
