"""Two original caller windows through retail, raw and normalized bodies."""
import itertools,json,struct
from dataclasses import replace
from tools.experiments import game_effect_record_151580b0_match as p
from tools.experiments import game_effect_record_151580b0_match as norm
from tools.tests import game_effect_record_151580b0_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WRAPPER=0x151581D8;WINDOW=0x1518A57C;SUCCESS=0x1518A5B8;FAILURE=0x1518A5E4
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.target_arguments=tuple(self.arguments(7))
  else:super().record_call(t)
def main():
 rom=(p.root/"conker/conker.us.bin").read_bytes();wrapper=struct.unpack_from(">19I",rom,0x185688);window=struct.unpack_from(">15I",rom,WINDOW-0x15000000+0x2d4b0);raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};symbols={name:lookup[name]for es in refs.values()for _,name in es};rawwords=p.bound_blob(raw,refs,symbols);normal,nrefs=norm.normalize(raw,refs);normalwords=p.bound_blob(normal,nrefs,symbols);retail=struct.unpack_from(">74I",rom,p.ROM);counts=[0,0]
 for kind,alloc,alternate,mode,count,mutation in itertools.product((0,1),(0,1),(0,1,0x100,0x101),(0,255),(-1,0,2,3),(0,1,2,4,8,16,27)):
  if kind==0:c=g.Case(alloc,0,alternate,mode,count,mutation,0,counts[kind]%3,extra=0)
  else:c=g.Case(alloc,1,1,mode,count,mutation,0,counts[kind]%3,extra=255,data=g.STACK+0x68,owner_addr=3)
  models=[]
  for ws in (retail,rawwords,normalwords):
   m=Caller(wrapper if kind==0 else window,c);m.code=dict(zip(range(WRAPPER,WRAPPER+4*len(wrapper),4),wrapper)) if kind==0 else dict(zip(range(WINDOW,SUCCESS,4),window));m.code.update(zip(range(p.ENTRY,p.ENTRY+4*len(ws),4),ws));m.entry=WRAPPER if kind==0 else WINDOW
   if kind==0:
    m.r[4:8]=[g.SOURCE,alternate,c.bytes,mode];g.put(m.memory,g.STACK+16,c.parameter)
   else:
    m.r[4:7]=[c.data,3,255];m.r[8]=12;m.r[11]=21;g.put(m.memory,g.STACK+0xd8,g.u32(c.bytes-0x38));g.put(m.memory,g.STACK+0xe0,c.parameter);m.memory[g.STACK+0xdf]=mode;m.code[SUCCESS]=m.code[FAILURE]=0;m.code=WindowCode(m.code,m);m.code.ends=(SUCCESS,FAILURE)
   m.initial=dict(m.memory)
   try:m.run()
   except WindowBoundary:
    assert kind==1
   else:assert kind==0
   want,calls,value=g.reference(c,m.initial);assert g.public(m.memory)==g.public(want),(kind,c,"memory");assert m.calls==calls,(kind,c,m.calls,calls);expected=list(g.args(c));expected[3]&=255;expected[5]&=255;assert m.target_arguments==tuple(expected),(kind,c,m.target_arguments,expected)
   if kind==0:assert m.r[2]==value and m.r[29]==g.STACK
   else:assert (SUCCESS in m.visits,FAILURE in m.visits)==(bool(value),not value) and m.r[3]==value and m.r[31]==0x1518A5A8
   models.append(m)
  a,b,d=models;assert(a.memory,a.r,a.f,a.calls,a.trace)==(d.memory,d.r,d.f,d.calls,d.trace),(kind,c,"normalized");counts[kind]+=1
 result=dict(wrapper_cases=counts[0],second_window_cases=counts[1],executions=3*sum(counts),original_callers=["func_151581D8","func_1518A3C0"],wrapper_returns_v0=True,second_uses_allocation_result=True,full_second_parent_not_qualified=True,helpers_modeled=True,source_installed=False);(p.out/"callers.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True);return result
