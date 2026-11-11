import itertools,json,struct
from tools.experiments import game_attachment_1518a094_match as p
from tools.tests import game_attachment_1518a094_oracle as g
from tools.tests.game_animation_timeline_oracle import bits,floating
def main():
 rom=(p.root/"conker/conker.us.bin").read_bytes();addr=g.TRANS;code=dict(zip(range(addr,addr+160,4),struct.unpack_from(">40I",rom,0xd4e10)))
 raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};candidate=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});retail=struct.unpack_from(">96I",rom,p.ROM);visited=set();n=0
 for pos,translation,scale,phase in itertools.product((0.0,1.0,-2.0,7.5),(-3.0,0.0,2.0,15.0),(0.5,1.0,2.0,4.0),(0,8)):
  c=g.Case(1,1,1,1,-1,1,1,1,0,phase,n%3);memory=g.fixture(c);ctx=g.OBJ+0x170;mat=g.MATRIX+128
  for i,val in enumerate((pos,pos+1,pos-1,pos*2,pos+2,pos-2)):g.put(memory,ctx+i*4,bits(val))
  for i in range(16):g.put(memory,mat+i*4,bits(scale if i in(0,5,10) else translation if i in(12,13,14) else 1.0 if i==15 else 0.0))
  expected=dict(memory);calls=[]
  for k in range(2):
   args=(mat,g.read(expected,ctx+k*12),g.read(expected,ctx+k*12+4),g.read(expected,ctx+k*12+8),g.OBJ+0x34+k*12,g.OBJ+0x38+k*12,g.OBJ+0x3c+k*12);calls.append((addr,args));x,y,z=map(floating,args[1:4])
   for axis,out in enumerate(args[4:]):
    a=floating(g.read(expected,mat+axis*4));b=floating(g.read(expected,mat+(axis+4)*4));d=floating(g.read(expected,mat+(axis+8)*4));e=floating(g.read(expected,mat+(axis+12)*4));value=bits(floating(bits(floating(bits(a*x))+floating(bits(b*y))))+floating(bits(floating(bits(d*z))+e)));g.put(expected,out,value)
  g.put(expected,g.OBJ+0x58,(g.read(expected,g.OBJ+0x58)|2)&~4)
  for ws in (retail,candidate):
   m=g.Oracle(ws,c,connected=code,memory=memory);m.run();assert g.public(m.memory)==g.public(expected),(c,pos,translation,scale,"memory");assert m.calls==calls,(c,m.calls,calls);assert m.r[2]==1;visited.update(m.visits)
  n+=1
 result=dict(cases=n,executions=2*n,original_matrix_helper_words_visited=sum(addr+4*i in visited for i in range(40)),lookup_and_subtype_skipped=True,finite_float_inputs_only=True,FCSR_hardware_not_qualified=True,source_installed=False,byte_exact=False)
 (p.out/"z000-matrix.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True);return result
