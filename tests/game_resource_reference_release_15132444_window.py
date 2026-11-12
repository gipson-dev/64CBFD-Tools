import json,struct
from tools.tests import game_resource_reference_release_15132444_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_15132444']['value'],fs['func_15132444']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>75I',rom,0x15F8F4);reports={}
 for label,start,end in (('first',0x15132570,0x15132584),('second',0x1513259C,0x151325B0)):
  words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0);count=0
  for c in g.cases():
   expected,calls=g.reference(c);pair=[]
   for ws in(retail,candidate):
    m=Caller(ws,c);m.entered=False;code=dict(zip(range(start,end,4),words));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[end]=0;m.code=WindowCode(code,m);m.code.ends=(end,);m.entry=start
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary not reached')
    assert m.entered and m.target_args==(g.OWNER,)and end in m.visits and m.r[29]==g.STACK-0x18,(label,c,'caller outcome');assert m.calls==calls,(label,c,'calls');assert g.public(m.memory)==expected,(label,c,'memory');pair.append(m)
   assert g.public(pair[0].memory)==g.public(pair[1].memory);count+=1
  reports[label]=count
 report=dict(cases=reports,callers={'first':'func_15132570','second':'func_1513259C'},helpers='modeled',full_parents_qualified=False,source_installed=False);(g.out/'caller_15132444_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
