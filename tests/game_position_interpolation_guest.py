from pathlib import Path
import sys,struct,random,math,json
from tools.experiments import game_position_interpolation_match as source
root=source.root
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.game_animation_timeline_oracle import floating
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_queued_segment_writer import STACK
p=source.out;entry=0x150BE2E8; text,fs,rs=parse_object(p/'base_no_const.o');a=fs['func_150BE2E8']['value'];n=fs['func_150BE2E8']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};symbols={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:symbols[nm] for es in refs.values() for _,nm in es});ret=list(struct.unpack('>84I',(root/'conker/conker.us.bin').read_bytes()[0xeb798:0xeb8e8]));diff=[i for i,(x,y) in enumerate(zip(candidate,ret)) if x!=y];assert diff==[43,44,69,70,71,73,74,75,76,77]
patched=list(candidate)
for i in diff:patched[i]=ret[i]
assert patched==ret
class Model(TriangleOracle):
 def execute(self,w):
  if w>>26==17 and (w>>21)&31==16 and w&63==13:
   src=(w>>11)&31;dst=(w>>6)&31;v=floating(self.f[src]);assert math.isfinite(v) and -2147483648<=v<2147483648,('float outside bounded model',v);self.f[dst]=math.trunc(v)&0xffffffff
  else:super().execute(w)
def fixture(actor,values,ticks,factor):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-0x700,0x180)}
 for base,length in ((actor-64,0x140),(0x800A0068-64,0x100),(0x800BE9E4-64,0x100)):
  m.update({base+i:(i*29+3)&255 for i in range(length)})
 for off,v in zip((0x7c,0x7e,0x80,0x82,0x84,0x86,0x3c,0x3e),values):put(m,actor+off,v&65535,2)
 put(m,0x800A0068,factor);put(m,0x800BE9E4,ticks&0xffffffff)
 return m
def run(words,m,actor):
 model=Model(words,m,entry=entry,arguments=(actor,)).run()
 external={a:b for a,b in model.memory.items() if not STACK-0x700<=a<STACK+0x180}
 events=[e for e in model.events if not STACK-0x700<=e[1]<STACK+0x180]
 return external,events

def main():
 rng=random.Random(0x150BE2E8);factors=[0x00000000,0x80000000,0x3f000000,0xbf000000,0x3f800000,0x3eaaaaab,0x3dcccccd];counts={'separate':0,'alias':0}; raw_mismatch=0
 for k in range(400):
  actor=(0x20000,0x800A0068-0x10,0x800BE9E4-0x10,0x800A0068-0x3c)[k%4]
  values=[rng.randrange(-32768,32768) for _ in range(8)];ticks=(0,1,2,-1,31)[k%5];factor=factors[k%len(factors)];m=fixture(actor,values,ticks,factor)
  try:
   oracle=run(ret,m,actor);normalized=run(patched,m,actor);raw=run(candidate,m,actor)
  except AssertionError as e:
   if e.args and isinstance(e.args[0],tuple) and e.args[0][0]=='float outside bounded model':continue
   raise
  assert oracle==normalized,(k,actor)
  if oracle!=raw:raw_mismatch+=1
  counts['separate' if k%4==0 else 'alias']+=1
 assert raw_mismatch==0
 print(json.dumps(dict(cases=counts,raw_mismatches=raw_mismatch,patched_equal=True,limits='bounded finite in-range model; no NaN, infinity, overflow or guest exception claims'),indent=2))


if __name__ == "__main__":main()
