"""Sole real JAL, its delay store, and continuation overwriting unused V0."""
import json,struct
from tools.tests import game_palette_state_15000940_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOW,END=0x1500076C,0x15000794
class Caller(g.Oracle):
 def record_call(self,t):
  assert t==g.ENTRY;self.calls.append((t,tuple(self.arguments(1))))
def execute(ws,c,bits):
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>10I',rom,0x2DC1C);memory=g.fixture(c);g.put(memory,0x800D3670,0xA5A5A5A5);code=dict(zip(range(g.ENTRY,g.ENTRY+380,4),ws));code[END]=0;m=Caller(window,memory,c,entry=WINDOW,connected=code);m.r[1]=0x800D0000;m.f[6]=bits;m.code=WindowCode(m.code,m);m.code.ends=(END,)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing continuation')
 expected=g.reference(m.initial,c);g.put(expected,0x800D3670,bits);assert g.public(m.memory)==g.public(expected);assert m.calls==[(g.ENTRY,(c.unused,))];assert m.r[2]==m.r[5]==0x800D9B68;assert m.r[4]==0x800D9B78 and m.r[6]==0x800D9B84 and m.r[16]==0;assert m.r[17:24]==m.before[17:24]and m.r[29]==g.STACK+c.phase and m.r[31]==WINDOW+8;return m
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();sites=[];literals=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
  if w==g.ENTRY:literals.append(4*i)
  if w>>26 in(2,3)and(w&0x3FFFFFF)<<2==g.ENTRY&0x0FFFFFFF:sites.append(4*i)
 assert sites==[0x2DC1C]and not literals
 raw=g.words(g.out/'selected.o');normal=g.words(g.out/'target-generic.o');truth=struct.unpack_from('>95I',rom,g.ROM);pairs=0
 for c in g.cases()[:48]:
  bits=(0,0x42C80000,0x7FC12345)[c.seed%3];a,b,d=[execute(ws,c,bits)for ws in(raw,normal,truth)];assert g.public(a.memory)==g.public(d.memory);assert(b.memory,b.r,b.f,b.calls)==(d.memory,d.r,d.f,d.calls);pairs+=1
 r=dict(caller_triples=pairs,caller_window_words=10,direct_J_JAL_ROM=sites,literal_pointers=literals,actual_parent='func_150006E0',return_V0_overwritten_before_any_read=True,unused_A0_word_home_retained=True,full_parent_or_gameplay_qualified=False)
 (g.out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
