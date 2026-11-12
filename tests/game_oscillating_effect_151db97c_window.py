"""Qualify the original indexed dispatcher window and its return branch."""
import json,struct
from tools.tests import game_oscillating_effect_151db97c_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START=0x15130A0C;END=0x15130A50;TABLE=0x80089760;INDEX=5
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.called=True;self.target_args=tuple(self.arguments(2))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>75I',rom,0x208e2c);candidate=g.words('independent-selected');count=0
 window=struct.unpack_from('>%dI'%((END-START)//4),rom,START-0x15000000+0x2d4b0)
 assert 0x0320f809 in window and struct.unpack_from('>I',rom,0x22e234)[0]==g.ENTRY
 for c in g.cases():
  for ws in (retail,candidate):
   m=Caller(ws,c);m.called=False;m.r[7]=0;m.memory[g.RECORD+0x72]=INDEX;g.put(m.memory,TABLE+4*INDEX,g.ENTRY);m.initial=dict(m.memory)
   code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0
   m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   expected,calls,result=g.reference(c,m.initial)
   assert m.called and m.target_args==(g.RECORD,g.STACK+c.phase+0x48) and END in m.visits
   assert (g.public(m.memory),m.calls,m.r[2],m.r[7])==(g.public(expected),calls,result,0),(c,m.calls,calls)
  count+=1
 assert retail.count(0x24020001)==2
 zero_return=tuple(0x24020000 if word==0x24020001 else word for word in retail)
 controls=0
 for c in (next(c for c in g.cases() if c.flags==0),next(c for c in g.cases() if c.flags==1)):
  m=Caller(zero_return,c);m.called=False;m.r[7]=0;m.memory[g.RECORD+0x72]=INDEX;g.put(m.memory,TABLE+4*INDEX,g.ENTRY);m.initial=dict(m.memory)
  code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(zero_return),4),zero_return));code[END]=0
  m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('control boundary not reached')
  expected,calls,_=g.reference(c,m.initial)
  assert m.called and (g.public(m.memory),m.calls,m.r[2],m.r[7])==(g.public(expected),calls,0,1)
  controls+=1
 report=dict(cases=count,caller='func_151303EC callback window',table='D_80089760[5]',return_controls_branch=True,return_negative_controls=controls,full_parent_qualified=False,helpers='modeled with mutations',source_installed=False)
 (g.out/'caller_151DB97C_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
