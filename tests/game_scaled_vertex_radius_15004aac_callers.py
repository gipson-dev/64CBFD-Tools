import json,struct
from tools.tests import game_scaled_vertex_radius_15004aac_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
START,END=0x150041B0,0x150041BC
class Caller(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY,hex(t);self.called=True;self.args=tuple(self.arguments(2))
def main():
 g.load_words()
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>3I',rom,START-0x15000000+0x2D4B0);assert window==(0x02002025,0x0D4012AB,0x8FA5004C)
 count=0
 for c in g.cases():
  machines=[]
  for ws in (g.retail,g.candidate,g.fixed):
   m=Caller(ws,c);m.called=False;m.r[16]=g.RECORD;put(m.memory,g.STACK+0x4c,0xABCDEF12);m.initial=dict(m.memory)
   code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.called and m.args==(g.RECORD,0xABCDEF12) and END in m.visits and m.r[31]==END
   assert g.public(m.memory)==g.public(g.reference(c,m.initial));machines.append(m)
  a,b,z=machines;assert g.public(a.memory)==g.public(b.memory);assert (a.memory,a.r,a.f,a.trace)==(z.memory,z.r,z.f,z.trace);count+=1
 report=dict(cases=count,caller='func_150039E0',call_site='0x150041B4',window_start=hex(START),window_end=hex(END),full_parent_not_qualified=True,source_installed=False)
 (g.out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
