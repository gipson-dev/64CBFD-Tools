import itertools,json,struct
from tools.tests import game_startup_initializer_1500e470_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
START=0x15007F80;END=0x15007FAC;SPECIAL=0x151E81EC;GLOBAL=0x800BE9F0
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.target_called=True
  elif t==SPECIAL:self.special_called=True
  else:super().record_call(t)
 def hook(self,t):
  if t==SPECIAL:
   for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  else:super().hook(t)
def main():
 g.load_words()
 rom=(g.root/'conker/conker.us.bin').read_bytes();offset=START-0x15000000+0x2D4B0;window=struct.unpack_from('>11I',rom,offset);assert window[-2:]==(0x0D40391C,0)
 count=0
 for arg,sel,flags in itertools.product((0x5341200,0x1D),(0,1,2),(0,0x80)):
  g.ARG=arg;pair=[];c=g.Case(sel,flags,1)
  for words in (g.retail,g.candidate,g.fixed):
   m=Caller(words,c);m.target_called=False;m.special_called=False;put(m.memory,GLOBAL,arg);m.initial=dict(m.memory)
   code=dict(zip(range(START,END,4),window));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller did not reach boundary')
   assert m.target_called and m.special_called==(arg==0x1d) and END in m.visits and m.r[31]==END
   for t,args in m.calls:
    if t in (0x151732E0,0x15004FE0,0x1500ABA0,0x151872B0):assert args==(arg,),(hex(t),args,arg)
    if t==0x151645C4:assert args==(int(flags==0),)
   pair.append(m)
  assert all(g.public(pair[0].memory)==g.public(x.memory) and pair[0].calls==x.calls for x in pair[1:]);assert (pair[0].memory,pair[0].r,pair[0].f,pair[0].trace)==(pair[2].memory,pair[2].r,pair[2].f,pair[2].trace);count+=1
 report=dict(cases=count,caller='func_15007B3C',start=hex(START),call_site='0x15007FA4',END=hex(END),special_path_modeled=True,full_parent_not_qualified=True,helpers_modeled=True,source_installed=False)
 (g.out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
