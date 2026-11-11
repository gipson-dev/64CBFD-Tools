import itertools,json,struct
from tools.experiments import game_attachment_1518a094_match as p
from tools.tests import game_attachment_1518a094_oracle as g
def main():
 rom=(p.root/"conker/conker.us.bin").read_bytes();addr=g.LOOK;code=dict(zip(range(addr,addr+0x120,4),struct.unpack_from(">72I",rom,0xb1340)))
 raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};candidate=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});retail=struct.unpack_from(">96I",rom,p.ROM);base=0x800cc2d0;visited=set();n=0
 for index,selector,phase in itertools.product(range(-1,26),(0,0x42,0xff),(0,8)):
  c=g.Case(0,1,1,1,-1,1,1,0,0,phase,n%3);memory=g.fixture(c);memory[g.OBJ+0x18d]=selector
  for i in range(26):
   a=base+i*0x32c;g.put(memory,a,0);memory[a+0x3b]=0
  if index>=0:
   chosen=base+index*0x32c
   for i in range(0x220):memory[chosen+i]=memory[g.RES+i]
   g.put(memory,chosen,1);memory[chosen+0x3b]=0x42;g.put(memory,chosen+0x1d4,0)
  found=index>=0 and selector==0x42;expected=dict(memory);g.put(expected,g.OBJ+0x188,chosen if found else 0)
  if found:g.put(expected,g.OBJ+0x58,g.read(expected,g.OBJ+0x58)&~2)
  for ws in (retail,candidate):
   m=g.Oracle(ws,c,connected=code,memory=memory);m.run();assert g.public(m.memory)==g.public(expected),(index,selector,"memory");assert m.calls==[(addr,(selector,))],(index,selector,m.calls);assert m.r[2]==int(found),(index,selector,m.r[2]);visited.update(m.visits)
  n+=1
 result=dict(cases=n,executions=2*n,original_lookup_words_visited=sum(addr+4*i in visited for i in range(72)),actor_slots_tested=26,lookup_zero_and_miss_tested=True,subtype_skipped_matrix_null=True,source_installed=False,byte_exact=False)
 (p.out/"z000-lookup.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True);return result
