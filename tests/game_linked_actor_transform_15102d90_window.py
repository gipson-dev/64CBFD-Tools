import json,struct
from tools.tests import game_linked_actor_transform_15102d90_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START,END,TABLE,INDEX=0x1513D038,0x1513D074,0x80089CB8,41
class CallerCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x1513D060:self.owner.returned_value=self.owner.r[2]
  return super().__getitem__(pc)
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>15I',rom,START-0x15000000+0x2D4B0);assert 0x0320F809 in window
 text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_15102D90']['value'],fs['func_15102D90']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>74I',rom,0x130240);count=0
 for c in g.cases():
  for remove in (0,1):
   expected,calls,answer=g.reference(c);g.put(expected,TABLE+4*INDEX,g.ENTRY);pair=[]
   for ws in (retail,candidate):
    m=Caller(ws,c);m.entered=False;m.r[2]=INDEX;m.r[7]=remove;m.r[29]=g.STACK-0x20;g.put(m.memory,TABLE+4*INDEX,g.ENTRY);code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=CallerCode(code,m);m.code.ends=(END,);m.entry=START
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary not reached')
    assert m.entered and m.target_args==(g.OWNER,)and END in m.visits and m.r[4]==g.OWNER and m.r[7]==(remove or not answer),(c,remove,'caller outcome',m.entered,getattr(m,'target_args',None),END in m.visits,m.r[4],m.r[7],getattr(m,'returned_value',None),answer,[hex(x) for x in m.visits if START<=x<=END]);assert m.calls==calls,(c,'calls');assert g.public(m.memory)==expected,(c,'memory');pair.append(m)
   assert g.public(pair[0].memory)==g.public(pair[1].memory);count+=1
 report=dict(cases=count,caller='func_1513CFE4',table='D_80089CB8[41]',window='0x1513D038..0x1513D074',helpers='modeled',full_parent_qualified=False,source_installed=False);(g.out/'caller_15102D90_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
