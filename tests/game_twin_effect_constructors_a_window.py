import json,struct
from tools.tests import game_twin_effect_constructors_a_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x151AF338;END=0x151AF378;ACTOR=0x50000
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:
   self.entered=True;self.target_args=tuple(self.arguments(5)); self.position=tuple(g.read(self.memory,self.target_args[0]+4*i) for i in range(3))
  else:
   super().record_call(t)
   if t==g.EMIT:
    velocity,args=self.observed;self.observed=(velocity,(g.POSITION,*args[1:]))
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();data,fs,rs=parse_object(g.out/'variant_151AF388.o');a,n=fs['func_151AF388']['value'],fs['func_151AF388']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
 look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>82I',rom,0x1DC838)
 window=struct.unpack_from('>16I',rom,START-0x15000000+0x2d4b0);assert window[-2]==(0x0c000000|((g.ENTRY>>2)&0x03ffffff))
 count=0
 for c in g.cases():
  expected,velocity,args,answer=g.reference(c);actor={ACTOR+i:0 for i in range(16)};actor[ACTOR+12]=c.selector&255;expected.update(actor)
  for words in (retail,candidate):
   m=Caller(words,c);m.entered=False;m.r[29]=g.STACK-0x180;m.r[6]=g.bits(3.);m.r[7]=c.vector[0];m.f[12]=g.bits(1.);m.f[14]=g.bits(2.);m.memory.update(actor)
   g.put(m.memory,m.r[29]+0x10,c.vector[1]);g.put(m.memory,m.r[29]+0x14,c.vector[2]);g.put(m.memory,m.r[29]+0x18,ACTOR)
   code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code.update(zip(range(START,END,4),window));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.entered and m.position==(g.bits(1.),g.bits(2.),g.bits(3.)) and m.target_args[1:4]==c.vector and (m.target_args[4]&255)==(c.selector&255)
   assert g.public(m.memory)==expected and m.observed==(velocity,args) and m.r[2]==answer,(c,m.observed,velocity,args,hex(m.r[2]))
  count+=1
 report=dict(cases=count,caller='func_151AF338 callback wrapper',helpers='modeled',caller_window_only=True,full_parent_qualified=False,source_installed=False)
 (g.out/'caller_151AF388_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
