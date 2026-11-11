"""Account for the typed placeholder stubs and bounded direct caller windows."""
import itertools,json,struct
from tools.tests import game_sequence_direction_1501fe68_oracle as g

def body(path,name):
 raw,refs=g.p.payload(path,name);assert not refs
 return struct.unpack('>%dI'%(len(raw)//4),raw)

def execute(ws,c,args,entry):
 mem=g.fixture(c);home=g.STACK+c.phase;g.put(mem,home+16,0xF1234567)
 m=g.Oracle(ws,mem,c,entry=entry);m.r[4:8]=args;m.before=m.r[:];m.before_f=m.f[:];m.run()
 assert m.r[2]==0 and m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
 assert not m.calls and g.read(m.memory,home+16)==0xF1234567
 return m

def main():
 tests=0
 for name,entry in (('func_1501F72C',g.F72),('func_1501FFE8',g.FFE)):
  old=body(g.out/'independent-before.o',name);new=body(g.out/'selected.o',name);assert len(old)==3 and len(new)==7
  for seed,phase in itertools.product(range(32),(0,8)):
   c=g.Case(seed=seed,phase=phase);args=tuple(((seed+1)*0x1020304+i*0x1726354)&0xFFFFFFFF for i in range(4));a,b=(execute(ws,c,args,entry) for ws in(old,new));home=g.STACK+phase
   assert a.r==b.r and a.f==b.f
   assert {k:v for k,v in a.memory.items()if not home<=k<home+16}=={k:v for k,v in b.memory.items()if not home<=k<home+16}
   assert all(g.read(b.memory,home+i*4)==v for i,v in enumerate(args));tests+=1
 rom=(g.root/'conker/conker.us.bin').read_bytes();sites={g.F72:[0x4D1FC,0x4D3D4],g.FFE:[0x4CD90,0x4D44C,0x4D950,0x4DDFC]};windows=0
 for target,addresses in sites.items():
  for at in addresses:
   call,=struct.unpack_from('>I',rom,at);assert call>>26==3 and ((call&0x3FFFFFF)<<2)==(target&0x0FFFFFFF)
   for (word,) in struct.iter_unpack('>I',rom[at+8:at+8+4*8]):
    op=word>>26;base=word>>21&31;off=((word&65535)^32768)-32768
    assert not (op in (0x20,0x21,0x23,0x24,0x25,0x31,0x35,0x37) and base==29 and 0<=off<16),(hex(at),hex(word))
   windows+=1
 r=dict(stub_pairs=tests,helpers=2,old_bytes=12,new_bytes=28,observable_difference='four incoming words written to argument-home area',direct_caller_linear_windows=windows,instructions_per_window=8,full_control_flow_or_indirect_call_proof=False,real_helpers_qualified=False)
 (g.out/'helpers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
