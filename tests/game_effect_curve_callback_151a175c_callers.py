import json,struct
from tools.tests import game_effect_curve_callback_151a175c_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
TABLE=0x8008C9C8
class Caller(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY,hex(t);self.called=True;self.args=tuple(self.arguments(1))
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>96I',rom,0x1CEC0C);candidate=g.words('independent-selected');count=0
 windows=((0x15167E80,0x15167EC0,0x2F,0x12345678),(0x151689D4,0x15168A04,0xB2,0x76543210))
 for start,end,indexoff,arg3 in windows:
  words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0);assert 0x0060F809 in words
  for c in g.cases():
   pair=[]
   for ws in(retail,candidate):
    m=Caller(ws,c);m.called=False;m.r[7]=arg3;m.memory.update({g.RECORD+i:((i*19+c.seed*11+37)&255)for i in range(128,192)});m.memory[g.RECORD+indexoff]=16;put(m.memory,TABLE+64,g.ENTRY);m.initial=dict(m.memory)
    code=dict(zip(range(start,end,4),words));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[end]=0;m.code=WindowCode(code,m);m.code.ends=(end,);m.entry=start
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary not reached')
    assert m.called and m.args==(g.RECORD,) and end in m.visits and m.r[4]==g.RECORD
    assert g.public(m.memory)==g.public(g.reference(c,m.initial)),(hex(start),c);pair.append(m)
   assert g.public(pair[0].memory)==g.public(pair[1].memory);count+=1
 report=dict(cases=count,callers=['func_15167E0C','func_15168870'],table='D_8008C9C8[16]',full_parents_not_qualified=True,source_installed=False)
 (g.out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
