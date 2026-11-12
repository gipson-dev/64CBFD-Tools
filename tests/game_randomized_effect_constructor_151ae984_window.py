import itertools,json,struct
from tools.tests import game_randomized_effect_constructor_151ae984_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x151AE958;END=0x151AE974;ACTOR=0x50000
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(6))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();data,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_151AE984']['value'],fs['func_151AE984']['size']
 refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())}
 candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>76I',rom,0x1DBE34)
 window=struct.unpack_from('>7I',rom,START-0x15000000+0x2d4b0);assert window[-2]==0x0d46ba61
 count=0
 for c in g.cases():
  if c.mode not in (0,0x1234) or c.selector not in (0,0x1234):continue
  expected,velocity,args,answer=g.reference(c);actor={ACTOR+i:0 for i in range(16)};actor[ACTOR+12]=c.selector&255;expected.update(actor)
  for words in (retail,candidate):
   m=Caller(words,c);m.entered=False;m.r[29]=g.STACK-0x180;m.r[4]=g.POSITION;m.r[5]=c.vector[0];m.r[2]=c.mode;m.memory.update(actor)
   g.put(m.memory,m.r[29]+0x50,ACTOR);g.put(m.memory,m.r[29]+0x48,c.vector[1]);g.put(m.memory,m.r[29]+0x4c,c.vector[2])
   code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code.update(zip(range(START,END,4),window));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.entered and m.target_args[:4]==(g.POSITION,*c.vector) and (m.target_args[4]&255)==(c.mode&255) and m.target_args[5]==(c.selector&255)
   assert g.public(m.memory)==expected and m.observed==(velocity,args) and m.r[2]==answer,(c,m.observed,velocity,args,hex(m.r[2]),[(hex(k),v,g.public(m.memory).get(k)) for k,v in expected.items() if g.public(m.memory).get(k)!=v][:12])
   assert m.r[29]==g.STACK-0x180 and m.r[31]==END
  count+=1
 report=dict(cases=count,caller='func_151AE890 call window',helpers='modeled',caller_window_only=True,full_parent_qualified=False,source_installed=False)
 (g.out/'caller_151AE984_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
