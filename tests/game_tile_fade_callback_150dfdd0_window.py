import json,struct
from tools.tests import game_tile_fade_callback_150dfdd0_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
TABLE=0x800841C0;INDEX=12;START=0x15030578;END=0x150305A4
class Caller(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY,hex(t);self.entered=True;self.target_args=tuple(self.arguments(2))
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x228CB0)[0]==g.ENTRY
 text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_150DFDD0']['value'],fs['func_150DFDD0']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>75I',rom,0x10D280);words=struct.unpack_from('>11I',rom,START-0x15000000+0x2D4B0);assert 0x0320F809 in words
 count=0
 for c in g.cases():
  expected,answer=g.reference(c);expected[g.OWNER+7]=INDEX;g.put(expected,TABLE+4*INDEX,g.ENTRY)
  for ws in (retail,candidate):
   m=Caller(ws,c);m.entered=False;m.memory[g.OWNER+7]=INDEX;g.put(m.memory,TABLE+4*INDEX,g.ENTRY);m.r[17]=g.OWNER;m.r[19]=g.FADE;m.r[18]=0xabcdef12
   code=dict(zip(range(START,END,4),words));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.entered and m.target_args==(g.OWNER,g.FADE) and END in m.visits and m.r[18]==answer,(c,'caller outcome')
   assert g.public(m.memory)==expected,(c,'memory')
  count+=1
 report=dict(cases=count,caller='func_15030468 dispatch window',table='D_800841C0[12]',full_parent_qualified=False,source_installed=False);(g.out/'caller_150DFDD0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
