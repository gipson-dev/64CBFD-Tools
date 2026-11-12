import json, struct
from tools.tests import game_release_chain_motion_1518fc84_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob

TABLE=0x8008FC48
START,END=0x151D3190,0x151D31B0
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(2))
  else:super().record_call(t)

def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes()
 words=struct.unpack_from('>8I',rom,START-0x15000000+0x2D4B0)
 assert 0x0320F809 in words
 text,fs,rs=parse_object(g.out/'independent-selected.o')
 a,n=fs['func_1518FC84']['value'],fs['func_1518FC84']['size']
 refs={i-a:v for i,v in rs.items() if a<=i<a+n}
 look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())}
 candidate=bound_blob(text[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es})
 retail=struct.unpack_from('>80I',rom,0x1BD134)
 count=0
 for c in g.cases():
  if not c.alias:continue
  expected,calls=g.reference(c);g.put(expected,TABLE,g.ENTRY);expected[g.OWNER+0x2a]=0
  models=[]
  for ws in (retail,candidate):
   m=Caller(ws,c);m.entered=False;g.put(m.memory,TABLE,g.ENTRY);m.memory[g.OWNER+0x2a]=0
   m.r[16]=g.OWNER;m.r[18]=0xffffffff;m.r[2]=0;m.r[19]=TABLE
   code=dict(zip(range(START,END,4),words));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0
   m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.entered and m.target_args==(g.OWNER,g.OWNER+0x34) and END in m.visits,(c,'caller outcome')
   assert m.calls==calls,(c,'calls',m.calls,calls)
   assert g.public(m.memory)==expected,(c,'memory')
   models.append(m)
  assert g.public(models[0].memory)==g.public(models[1].memory)
  count+=1
 report=dict(cases=count,caller='func_151D3130',table='D_8008FC48[0]',helpers='modeled',full_parent_qualified=False,source_installed=False)
 (g.out/'caller_1518FC84_screen.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True);return report
