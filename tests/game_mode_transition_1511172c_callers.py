"""Five original direct call sites execute the uninstalled candidate."""
import itertools,json,struct
from tools.experiments import game_mode_transition_1511172c_match as p
from tools.tests import game_mode_transition_1511172c_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
SITES=((0x15164624,4),(0x1516463c,4),(0x151646f4,6),(0x1516474c,6),(0x1516475c,1))
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.target_arguments=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();retail=struct.unpack('>75I',(p.out/'original-function.bin').read_bytes());raw,refs=p.payload(p.out/'independent-selected.o');lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};compiled=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});assert tuple(compiled)==retail
 n=0
 for (site,mode),current,flag,allocated,mutation in itertools.product(SITES,(1,4),(0,1),(0,1),(0,11)):
  c=g.Case(mode,current,4,flag,allocated,mutation,0,n%3);offset=site-0x15000000+0x2d4b0;window=struct.unpack_from('>2I',rom,offset);assert window[0]==0x0d4445cb and window[1]==0x24040000+mode
  m=Caller(window,c);m.code=dict(zip((site,site+4),window));m.code.update(zip(range(p.ENTRY,p.ENTRY+300,4),compiled));m.code[site+8]=0;m.code=WindowCode(m.code,m);m.code.ends=(site+8,);m.entry=site;m.initial=dict(m.memory)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('caller did not stop at return')
  want,calls=g.reference(c,m.initial);assert g.public(m.memory)==g.public(want),(site,c,'memory');assert m.calls==calls,(site,c,'calls');assert m.target_arguments==(mode,),(site,c,m.target_arguments);assert m.r[29]==g.STACK and m.r[31]==site+8,(site,c,'ABI');n+=1
 result=dict(original_caller='func_151645C4',caller_words_identical=111,sites=len(SITES),cases=n,helpers_modeled=True,bounded_windows_only=True,source_installed=False);(p.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
