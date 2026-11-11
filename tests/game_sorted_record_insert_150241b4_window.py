import itertools,json,struct
from tools.tests import game_sorted_record_insert_150241b4_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START,END,FRAME,RECORD=0x150244A0,0x150244C8,0x80000,0x90000
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(7))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>10I',rom,START-0x15000000+0x2D4B0);text,fs,rs=parse_object(g.out/'independent-nounroll.o');a,n=fs['func_150241B4']['value'],fs['func_150241B4']['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:(look[nm]if nm in look else int(nm[2:],16))for es in refs.values()for _,nm in es});retail=struct.unpack_from('>81I',rom,0x51664);count=0
 for c in g.cases():
  size,capacity,priority=c.size,c.capacity,c.priority;expected,calls=g.reference(c);expected_count=g.read(expected,g.COUNT);expected.pop(g.COUNT);expected.pop(g.COUNT+1);expected.pop(g.COUNT+2);expected.pop(g.COUNT+3);g.put(expected,FRAME,g.TABLE);expected[RECORD]=0x12;expected[RECORD+1]=0x34
  if size<capacity:
   index=next((i for i in range(size)if g.keys(c)[i]>=priority),size);g.put(expected,g.TABLE+12*index,RECORD)
  pair=[]
  for ws in(retail,candidate):
   m=Caller(ws,c);m.entered=False;m.count_address=g.STACK+0x88
   for i in range(4):m.memory.pop(g.COUNT+i)
   g.put(m.memory,FRAME,g.TABLE);m.memory[RECORD]=0x12;m.memory[RECORD+1]=0x34;g.put(m.memory,g.STACK+0x88,size);m.r[30]=FRAME;m.r[16]=RECORD;m.r[23]=c.tag;m.r[17]=priority&0xffffffff;m.r[13]=c.context;m.r[2]=c.parameter
   code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary not reached')
   assert m.entered and m.target_args==(g.TABLE,g.STACK+0x88,RECORD,c.tag,c.parameter,priority&0xffffffff,c.context),(c,m.target_args);assert g.read(m.memory,g.STACK+0x88)==expected_count and m.r[8]==1;assert g.public(m.memory)==expected,(c,'memory');assert m.calls==calls,(c,'calls',m.calls,calls);pair.append(m)
  assert g.public(pair[0].memory)==g.public(pair[1].memory);count+=1
 report=dict(cases=count,caller='func_150242F8',window='0x150244A0..0x150244C8',full_parent_qualified=False,helper='modeled',source_installed=False);(g.out/'caller_150241B4_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
