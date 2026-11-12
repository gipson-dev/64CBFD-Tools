import json,struct
from tools.tests import game_linked_scaled_matrix_151b76cc_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
TABLE=0x8008FB90;INDEX=1
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(2))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_151B76CC']['value'],fs['func_151B76CC']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>74I',rom,0x1E4B7C)
 reports={}
 for label,start,end in (('constructor',0x151B7414,0x151B7450),('update',0x151B784C,0x151B787C)):
  words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0);assert 0x0320F809 in words;count=0
  for c in g.cases():
   if not c.alias:continue
   expected,calls,answer=g.reference(c);g.put(expected,TABLE+4*INDEX,g.ENTRY)
   if label=='update':expected[g.DATA+8]=INDEX
   pair=[]
   for ws in (retail,candidate):
    m=Caller(ws,c);m.entered=False;g.put(m.memory,TABLE+4*INDEX,g.ENTRY)
    if label=='constructor':m.r[29]=g.STACK-0x120;m.memory[m.r[29]+0x107]=INDEX;m.r[16]=g.OWNER
    else:
     m.r[29]=g.STACK-0x48;m.r[3]=g.DATA;m.r[4]=g.OWNER;m.r[5]=g.OWNER+0x10;m.r[6]=g.OWNER;m.r[25]=0x80090000;m.memory[g.DATA+8]=INDEX
     for off,value in ((0x44,g.DATA),(0x1c,g.OWNER+0x10),(0x48,g.OWNER)):g.put(m.memory,m.r[29]+off,value)
    code=dict(zip(range(start,end,4),words));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[end]=0;m.code=WindowCode(code,m);m.code.ends=(end,);m.entry=start
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary not reached')
    assert m.entered and m.target_args==(g.OWNER,g.OWNER+0x10)and end in m.visits and m.r[2]==answer,(label,c,'caller outcome');assert m.calls==calls,(label,c,'calls');assert g.public(m.memory)==expected,(label,c,'memory')
    if label=='update':assert (m.r[3],m.r[5],m.r[6])==(g.DATA,g.OWNER+0x10,g.OWNER),(c,'restored registers')
    pair.append(m)
   assert g.public(pair[0].memory)==g.public(pair[1].memory);count+=1
  reports[label]=count
 report=dict(cases=reports,callers={'constructor':'func_151B7328','update':'func_151B77F4'},table='D_8008FB90[1]',helpers='modeled',full_parents_qualified=False,source_installed=False);(g.out/'caller_151B76CC_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
