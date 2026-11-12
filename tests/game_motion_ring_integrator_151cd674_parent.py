import json,struct
from tools.tests import game_motion_ring_integrator_151cd674_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,END,TABLE,RELEASE,MARK=0x15147740,0x151478D0,0x8008A200,0x1516972C,0x70000
class Parent(g.Oracle):
 def record_call(self,t):
  assert t in (g.ENTRY,RELEASE),hex(t);args=tuple(self.arguments(1));assert args==(g.OWNER,);self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t==RELEASE;g.put(self.memory,MARK,0x13579BDF)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();parent=struct.unpack_from('>100I',rom,ENTRY-0x15000000+0x2D4B0);text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_151CD674']['value'],fs['func_151CD674']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>82I',rom,0x1FAB24);count=0
 for c in g.cases():
  expected,answer=g.reference(c);expected[g.OWNER+0x2f]=9;expected[g.OWNER+0x30]=0;g.put(expected,TABLE+36,g.ENTRY);g.put(expected,MARK,0x13579BDF if not answer else 0);pair=[]
  for ws in(retail,candidate):
   m=Parent(ws,c);m.memory[g.OWNER+0x2f]=9;m.memory[g.OWNER+0x30]=0;g.put(m.memory,TABLE+36,g.ENTRY);g.put(m.memory,MARK,0);m.r[31]=END;code=dict(zip(range(ENTRY,END,4),parent));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=ENTRY
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('parent return not reached')
   assert m.calls==[(g.ENTRY,(g.OWNER,))]+([]if answer else[(RELEASE,(g.OWNER,))]),(c,'calls',m.calls);assert g.public(m.memory)==expected,(c,'memory');pair.append(m)
  assert g.public(pair[0].memory)==g.public(pair[1].memory);count+=1
 report=dict(cases=count,caller='func_15147740',callback='D_8008A200[9]',bounded_parent_paths=True,release='modeled',source_installed=False);(g.out/'parent_151CD674_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
