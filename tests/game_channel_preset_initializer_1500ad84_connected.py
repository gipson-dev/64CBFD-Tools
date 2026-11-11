import json,struct
from tools.tests import game_channel_preset_initializer_1500ad84_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
START=0x1500BF40;END=0x1500BF60;PARAMS=0x800BE4A0
class Caller(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY,hex(t);self.calls.append((t,tuple(self.arguments(3))))
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>8I',rom,START-0x15000000+0x2D4B0);assert window[2]==0x0D402B61 and window[-1]==0x26310004
 retail=struct.unpack_from('>97I',rom,0x38234);candidate=g.words('independent-selected');count=0
 for seed in range(16):
  for mode in (0,1):
   c0=g.Case(0,0,0,0,0,seed%3);base=g.fixture(c0);cases=[]
   for preset in (0,2,7):
    flags=((preset+seed)*9)&255;value=(preset*17+seed*23)&255;at=g.PRESET+10*preset;base[at]=flags;base[at+1]=value;put(base,at+4,-1000+preset,2);put(base,at+6,2000-preset,2)
   for slot in range(15):
    preset=(0,2,7,255)[(slot+seed+mode)%4];flags=base[g.PRESET+10*preset];value=base[g.PRESET+10*preset+1];options=(slot*31+seed*11)&255;put(base,PARAMS+4*slot,preset,2);put(base,PARAMS+4*slot+2,options,2);cases.append(g.Case(slot,preset,flags,options,value,seed%3))
   expected=dict(base)
   for c in cases:expected=g.reference(c,expected)
   machines=[]
   for ws in(retail,candidate):
    m=Caller(ws,c0);m.memory=dict(base);m.initial=dict(base);m.r[16]=0;m.r[17]=PARAMS
    code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('loop boundary not reached')
    assert m.r[16]==15 and m.r[17]==PARAMS+60 and m.calls==[(g.ENTRY,(c.slot,c.preset,c.options))for c in cases]
    assert g.public(m.memory)==g.public(expected),(seed,mode);machines.append(m)
   assert g.public(machines[0].memory)==g.public(machines[1].memory)and machines[0].calls==machines[1].calls;count+=1
 report=dict(cases=count,caller='func_1500BEC0',original_loop='0x1500BF40..0x1500BF60',channels_per_case=15,full_parent_not_qualified=True,source_installed=False)
 (g.out/'loop-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
