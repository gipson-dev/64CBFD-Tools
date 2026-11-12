import json,struct
from tools.tests import game_motion_ring_integrator_151cd674_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START,END,TABLE=0x151477B0,0x151477DC,0x8008A200
class Caller(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY;self.entered=True;self.target_args=tuple(self.arguments(1))
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>11I',rom,START-0x15000000+0x2D4B0);assert 0x0320F809 in window
 text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_151CD674']['value'],fs['func_151CD674']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>82I',rom,0x1FAB24);count=0
 for c in g.cases():
  expected,answer=g.reference(c);g.put(expected,TABLE+36,g.ENTRY);pair=[]
  for ws in (retail,candidate):
   m=Caller(ws,c);m.entered=False;m.r[5]=0;m.r[10]=36;g.put(m.memory,TABLE+36,g.ENTRY);code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.entered and m.target_args==(g.OWNER,)and END in m.visits and m.r[4]==g.OWNER and m.r[5]==(0 if answer else 1),(c,'caller outcome');assert g.public(m.memory)==expected,(c,'memory');pair.append(m)
  assert g.public(pair[0].memory)==g.public(pair[1].memory);count+=1
 report=dict(cases=count,caller='func_15147740',table='D_8008A200[9]',window='0x151477B0..0x151477DC',full_parent_qualified=False,source_installed=False);(g.out/'caller_151CD674_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
