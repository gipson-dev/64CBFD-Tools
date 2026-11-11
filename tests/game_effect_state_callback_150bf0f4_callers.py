import json,struct
from tools.tests import game_effect_state_callback_150bf0f4_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
START=0x1516D6A8;END_RETURN=0x1516D6D4;END_CONTINUE=0x1516D6F4;TABLE=0x8008CBA0
class Caller(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY,hex(t);self.called=True;self.args=tuple(self.arguments(1))
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>11I',rom,START-0x15000000+0x2D4B0);assert window[0]==0xAFA40018 and window[6]==0x0320F809
 retail=struct.unpack_from('>74I',rom,0xEC5A4);candidate=g.words('independent-selected');count=0
 for c in g.cases():
  machines=[]
  for ws in(retail,candidate):
   m=Caller(ws,c);m.called=False;m.memory[g.RECORD+0x23]=8;put(m.memory,TABLE+32,g.ENTRY);m.initial=dict(m.memory)
   code=dict(zip(range(START,START+4*len(window),4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END_RETURN]=0;code[END_CONTINUE]=0;m.code=WindowCode(code,m);m.code.ends=(END_RETURN,END_CONTINUE);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   expected,value=g.reference(c,m.initial);assert m.called and m.args==(g.RECORD,) and g.public(m.memory)==g.public(expected)
   assert (END_RETURN in m.visits)==(value==1) and (END_CONTINUE in m.visits)==(value!=1);machines.append(m)
  assert g.public(machines[0].memory)==g.public(machines[1].memory);count+=1
 report=dict(cases=count,caller='func_1516D678',dispatcher_window='0x1516D6A8..0x1516D6D4',table='D_8008CBA0[8]',branch_on_return_qualified=True,full_parent_not_qualified=True,source_installed=False)
 (g.out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
