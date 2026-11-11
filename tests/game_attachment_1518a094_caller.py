"""Original bounded record dispatcher through all three callback bodies."""
import itertools,json,struct
from tools.experiments import game_attachment_1518a094_match as p
from tools.experiments import game_attachment_1518a094_match as norm
from tools.tests import game_attachment_1518a094_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOW,END,TABLE=0x1513D038,0x1513D070,0x80089CB8
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.target_arguments=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(p.root/"conker/conker.us.bin").read_bytes();assert struct.unpack_from(">I",rom,0x22e780)[0]==p.ENTRY;window=struct.unpack_from(">14I",rom,WINDOW-0x15000000+0x2d4b0);raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};symbols={n:lookup[n]for es in refs.values()for _,n in es};original=struct.unpack_from(">96I",rom,p.ROM);candidate=p.bound_blob(raw,refs,symbols);normal,nrefs=norm.normalize(raw,refs);normalized=p.bound_blob(normal,nrefs,symbols);cases=0
 for initial,found,active,same,subtype,cbret,enabled,matrix,mutation,remove in itertools.product((0,1),(0,1),(0,1),(0,1),(-1,0),(0,1),(0,1),(0,1),(0,1),(0,1)):
  c=g.Case(initial,found,active,same,subtype,cbret,enabled,matrix,mutation,0,cases%3)
  for ws in (original,candidate,normalized):
   m=Caller(window,c);m.code=dict(zip(range(WINDOW,END,4),window));m.code.update(zip(range(p.ENTRY,p.ENTRY+4*len(ws),4),ws));m.code[END]=0;m.entry=WINDOW;m.r[2]=2;m.r[4]=g.OBJ;m.r[7]=remove;g.put(m.memory,TABLE+8,p.ENTRY);m.initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(END,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError("dispatcher did not stop")
   expected,calls,value=g.reference(c,m.initial);assert g.public(m.memory)==g.public(expected),(c,"memory");assert g.normalize(m.calls)==calls,(c,m.calls,calls);assert m.target_arguments==(g.OBJ,);assert m.r[7]==(1 if value==0 else remove),(c,m.r[7],value);assert m.r[4]==g.OBJ and m.r[29]==g.STACK and m.r[31]==0x1513D060
  cases+=1
 report=dict(cases=cases,executions=3*cases,dispatcher="func_1513CFE4",window="0x1513D038..0x1513D070",table="D_80089CB8",selector=2,return_controls_removal=True,full_parent_not_qualified=True,source_installed=False,byte_exact=False)
 (p.out/"z000-caller.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report),flush=True);return report
