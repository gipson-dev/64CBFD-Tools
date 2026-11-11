import json,struct
from tools.tests import game_resource_table_loader_150163d0_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START,END,SCENE=0x15007F60,0x15007F6C,0x800BE9F0
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>3I',rom,START-0x15000000+0x2D4B0);retail=struct.unpack_from('>76I',rom,0x43880)
 text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_150163D0']['value'],fs['func_150163D0']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};lookup={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:lookup.get(nm,int(nm[2:],16)if nm.startswith('D_')else 0)for es in refs.values()for _,nm in es})
 count=0
 for n in range(13):
  for outcome in (0,1,0x7fffffff,0x80000000,0xffffffff):
   for resource in (0,1,0x12345678):
    c=g.Case(n,outcome,resource);pair=[]
    for ws in (retail,candidate):
     m=Caller(ws,c);m.entered=False;g.put(m.memory,SCENE,resource);code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
     try:m.run()
     except WindowBoundary:pass
     else:raise AssertionError('caller boundary not reached')
     assert m.entered and m.target_args==(resource,) and END in m.visits
     expected=g.reference(c);g.put(expected,SCENE,resource);assert g.public(m.memory)==expected,(c,'memory');pair.append(m)
    assert g.public(pair[0].memory)==g.public(pair[1].memory);count+=1
 report=dict(cases=count,caller='func_15007B3C',window='0x15007F60..0x15007F6C',full_parent_qualified=False,source_installed=False)
 (g.out/'caller_150163D0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
