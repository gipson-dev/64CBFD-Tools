import json,struct
from tools.tests import game_channel_preset_initializer_1500ad84_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
START=0x1500BF40;END=0x1500BF54;PARAMS=0x34000
class Caller(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY,hex(t);self.called=True;self.args=tuple(self.arguments(3))
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>5I',rom,START-0x15000000+0x2D4B0);assert window==(0x02002025,0x96250000,0x0D402B61,0x96260002,0x26100001)
 retail=struct.unpack_from('>97I',rom,0x38234);candidate=g.words('independent-selected');count=0
 for c in g.cases():
  machines=[]
  for ws in(retail,candidate):
   m=Caller(ws,c);m.called=False;m.r[16]=c.slot;m.r[17]=PARAMS;put(m.memory,PARAMS,c.preset,2);put(m.memory,PARAMS+2,c.options,2);m.initial=dict(m.memory)
   code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.called and m.args==(c.slot,c.preset,c.options) and END in m.visits and m.r[31]==0x1500BF50 and m.r[16]==c.slot+1
   assert g.public(m.memory)==g.public(g.reference(c,m.initial));machines.append(m)
  assert g.public(machines[0].memory)==g.public(machines[1].memory);count+=1
 report=dict(cases=count,caller='func_1500BEC0',call_site='0x1500BF48',window_start=hex(START),window_end=hex(END),caller_does_not_read_return_before_next_instruction=True,full_parent_not_qualified=True,source_installed=False)
 (g.out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
