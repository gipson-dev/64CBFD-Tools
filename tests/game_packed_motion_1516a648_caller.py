"""Connect the original packed-record dispatcher around callback index seven."""
import itertools,json,struct
from tools.experiments import game_packed_motion_1516a648_match as p
from tools.experiments import game_packed_motion_1516a648_match as norm
from tools.tests import game_packed_motion_1516a648_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOW,REMOVE,ADVANCE,TABLE=0x1516D6AC,0x1516D6D4,0x1516D6F4,0x8008CBA0
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.target_arguments=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(p.root/"conker/conker.us.bin").read_bytes();assert struct.unpack_from(">I",rom,0x23167c)[0]==p.ENTRY;window=struct.unpack_from(">10I",rom,WINDOW-0x15000000+0x2d4b0);raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};symbols={n:lookup[n]for es in refs.values()for _,n in es};original=struct.unpack_from(">73I",rom,p.ROM);candidate=p.bound_blob(raw,refs,symbols);normal,nrefs=norm.normalize(raw,refs);normalized=p.bound_blob(normal,nrefs,symbols);cases=0
 for state,alpha,ticks,answer,mutation in itertools.product((0,1),(0,1,128,255),(0,1,64,0xffffffff),(0xfffffff5,0,32767,0x7fffffff),(0,1,2,3)):
  c=g.Case(state,alpha,ticks,(-32768,-1,0,32767)[cases%4],(-301,-1,0,1,301)[cases%5],answer,mutation,0,cases%3);models=[]
  for ws in (original,candidate,normalized):
   m=Caller(window,c);m.code=dict(zip(range(WINDOW,REMOVE,4),window));m.code.update(zip(range(p.ENTRY,p.ENTRY+4*len(ws),4),ws));m.code[REMOVE]=m.code[ADVANCE]=0;m.entry=WINDOW;g.put(m.memory,g.STACK+0x18,g.OBJ);m.memory[g.OBJ+0x23]=7;g.put(m.memory,TABLE+7*4,p.ENTRY);m.initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(REMOVE,ADVANCE)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError("dispatcher did not stop")
   want,calls,value=g.reference(c,m.initial);assert g.public(m.memory)==g.public(want),(c,"memory");assert m.calls==calls,(c,m.calls,calls);assert m.target_arguments==(g.OBJ,);assert m.r[4]==g.OBJ and m.r[29]==g.STACK and m.r[31]==0x1516D6C8;assert (REMOVE in m.visits,ADVANCE in m.visits)==(value==1,value!=1);models.append(m)
  a,b,d=models;assert(a.memory,a.r,a.f,a.calls,a.trace)==(d.memory,d.r,d.f,d.calls,d.trace);cases+=1
 result=dict(cases=cases,executions=3*cases,dispatcher="func_1516D678",window="0x1516D6AC..0x1516D6D4/0x1516D6F4",table="D_8008CBA0",selector=7,return_one_selects_removal=True,full_parent_not_qualified=True,source_installed=False);(p.out/"caller.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True);return result
