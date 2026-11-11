import itertools,json,struct
from tools.experiments import game_attachment_1518a094_match as p
from tools.tests import game_attachment_1518a094_oracle as g
def main():
 rom=(p.root/"conker/conker.us.bin").read_bytes();callbacks={0:(0x1518a214,0x1b76c4,53),1:(0x1518a2e8,0x1b7798,15),2:(0x1518a324,0x1b77d4,15),3:(0x151c9b64,0x1f7014,15)}
 code={}
 for address,offset,n in callbacks.values():code.update(zip(range(address,address+4*n,4),struct.unpack_from(">"+str(n)+"I",rom,offset)))
 raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};candidate=p.bound_blob(raw,refs,{n:lookup[n]for es in refs.values()for _,n in es});retail=struct.unpack_from(">96I",rom,p.ROM);visits=set();n=0
 for subtype,byte,matrix,seed,phase in itertools.product((0,1,2,3),(0,1,15,16,17,255),(0,1),range(8),(0,8)):
  c=g.Case(1,1,1,1,subtype,1,1,matrix,0,phase,seed);memory=g.fixture(c);addr=callbacks[subtype][0];g.put(memory,g.TABLE+subtype*4,addr);memory[g.RES+0x68]=byte;memory[g.RES+0x6a]=byte;memory[g.RES+0x6f]=byte;g.put(memory,0x800a73c0,0x3f19999a);g.put(memory,0x800a73c4,0x3e99999a);g.put(memory,0x800a73c8,0x3f19999a)
  for ws in (retail,candidate):
   m=g.Oracle(ws,c,connected=code,memory=memory);m.run();expected=dict(memory);flag=(byte==15 if subtype==0 else byte!=0 if subtype in (1,3) else byte==0);calls=[(addr,(g.OBJ,"stack-byte",subtype))]
   if flag:g.put(expected,g.OBJ+0x58,g.read(expected,g.OBJ+0x58)&~2)
   else:
    if subtype==0:
     scale=0x3e99999a if byte==16 else 0x3f19999a;g.put(expected,g.OBJ+0x128,scale);g.put(expected,g.OBJ+0x12c,scale);expected[g.OBJ+0x28]=128 if byte==16 else 255;expected[g.OBJ+0x29]=0;expected[g.OBJ+0x2a]=0
   if not flag and matrix:
    ctx=g.OBJ+0x170;mat=g.MATRIX+expected[ctx+0x1c]*64
    for i in range(2):
     args=(mat,g.read(expected,ctx+i*12),g.read(expected,ctx+i*12+4),g.read(expected,ctx+i*12+8),g.OBJ+0x34+i*12,g.OBJ+0x38+i*12,g.OBJ+0x3c+i*12);calls.append((g.TRANS,args));g.transform(expected,args)
    g.put(expected,g.OBJ+0x58,(g.read(expected,g.OBJ+0x58)|2)&~4)
   elif not flag:g.put(expected,g.OBJ+0x58,g.read(expected,g.OBJ+0x58)&~2)
   norm=[(t,(a[0],"stack-byte",a[2])if t==addr else a)for t,a in m.calls];assert g.public(m.memory)==g.public(expected),(c,"memory");assert norm==calls,(c,norm,calls);assert m.r[2]==1,(c,m.r[2]);visits.update(m.visits)
  n+=1
 result=dict(cases=n,executions=2*n,original_handlers=["func_1518A214","func_1518A2E8","func_1518A324","func_151C9B64"],handler_words_visited={hex(a):sum(a+i*4 in visits for i in range(size))for a,_,size in callbacks.values()},lookup_and_transform_modeled=True,source_installed=False,byte_exact=False)
 (p.out/"z000-connected-all.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True);return result
