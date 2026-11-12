"""Check the two retail callback-dispatch windows with private candidate code."""
import json,struct
from tools.tests import game_timed_effect_callback_150e4cbc_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
TABLE=0x8008C9C8;INDEX=13
class Caller(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY,hex(t);self.called=True;self.args=tuple(self.arguments(1))
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>82I',rom,0x11216c);candidate=g.words('independent-selected');count=0
 windows=((0x15167E80,0x15167EC0,0x2f,0x12345678),(0x151689D4,0x15168A04,0xb2,0x76543210))
 assert struct.unpack_from('>I',rom,0x2314bc)[0]==g.ENTRY
 for start,end,indexoff,arg3 in windows:
  words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2d4b0);assert 0x0060f809 in words
  for c in g.cases():
   pair=[]
   for target in (retail,candidate):
    m=Caller(target,c);m.called=False;m.r[7]=arg3;m.memory[g.RECORD+indexoff]=INDEX;g.put(m.memory,TABLE+INDEX*4,g.ENTRY);m.initial=dict(m.memory)
    code=dict(zip(range(start,end,4),words));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(target),4),target));code[end]=0
    m.code=WindowCode(code,m);m.code.ends=(end,);m.entry=start
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary not reached')
    assert m.called and m.args==(g.RECORD,) and end in m.visits and m.r[4]==g.RECORD
    assert g.public(m.memory)==g.public(g.reference(c,m.initial)),(hex(start),c)
    pair.append(m)
   assert g.public(pair[0].memory)==g.public(pair[1].memory);count+=1
 report=dict(cases=count,callers=['func_15167E0C','func_15168870'],table='D_8008C9C8[13]',full_parents_not_qualified=True,source_installed=False)
 (g.out/'callers_150E4CBC_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
