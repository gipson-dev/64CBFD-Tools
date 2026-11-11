"""Connect original fixed-point update and contact damping helpers."""
import itertools,json,math,struct
from tools.experiments import game_packed_motion_1516a648_match as p
from tools.experiments import game_packed_motion_1516a648_match as norm
from tools.tests import game_packed_motion_1516a648_oracle as g
def main():
 rom=(p.root/"conker/conker.us.bin").read_bytes();helpers=((g.UPDATE,0x19cd14,34),(g.CONTACT,0x19cdfc,14),(0x1516F8EC,0x19cd9c,12),(0x1516F91C,0x19cdcc,12));code={}
 for addr,off,size in helpers:code.update(zip(range(addr,addr+4*size,4),struct.unpack_from(">"+str(size)+"I",rom,off)))
 class Connected(g.Oracle):
  def record_call(self,t):
   if t in (0x1516F8EC,0x1516F91C):self.calls.append((t,tuple(self.arguments(2))))
   else:super().record_call(t)
 raw,refs=p.payload(p.out/"independent-selected.o");lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};symbols={name:lookup[name]for es in refs.values()for _,name in es};rawwords=p.bound_blob(raw,refs,symbols);normal,nrefs=norm.normalize(raw,refs);normalwords=p.bound_blob(normal,nrefs,symbols);retail=struct.unpack_from(">73I",rom,p.ROM);visited=set();n=0
 for ticks,xspeed,zspeed,answer,y,phase in itertools.product((0,1,7,0xffffffff,0x80000000),(0,1,0x7fff,0x8000,0xffff),(0,1,0x7fff,0x8000,0xffff),(0xfffffff5,0,1000),(-200,0,500),(0,8)):
  c=g.Case(1,255,ticks,y,-301,answer,0,phase,n%3);memory=g.fixture(c);g.put(memory,g.OBJ+0x26,xspeed,2);g.put(memory,g.OBJ+0x28,zspeed,2);memory[g.OBJ+0x2a]=0x5a;memory[g.OBJ+0x2b]=0xa5;want=dict(memory);calls=[(g.UPDATE,(g.OBJ,))];g.put(want,g.OBJ+0x18,(g.signedword(want,g.OBJ+0x18)-300)&65535,2)
  for coord,speed,fraction in ((0xe,0x26,0x2a),(0x12,0x28,0x2b)):
   vector=g.s16(g.read(want,g.OBJ+speed,2));v=g.s32(g.signedword(want,g.OBJ+coord)*256+want[g.OBJ+fraction]+g.u32(vector*ticks));g.put(want,g.OBJ+coord,(v>>8)&65535,2);want[g.OBJ+fraction]=v&255
  calls.append((g.HEIGHT,tuple(g.u32(g.signedword(want,g.OBJ+i))for i in (0xe,0x10,0x12))+(0,)));level=g.s32(answer+10);want[g.OBJ+0x2c]=(level>>8)&255;want[g.OBJ+0x2d]=level&255
  if g.signedword(want,g.OBJ+0x10)<level:
   g.put(want,g.OBJ+0x10,level&65535,2);speed=math.trunc(g.signedword(want,g.OBJ+0x18)*-0.5);g.put(want,g.OBJ+0x18,speed&65535,2);calls.extend(((g.CONTACT,(g.OBJ,230)),(0x1516F8EC,(g.OBJ,230)),(0x1516F91C,(g.OBJ,230))))
   for offset in (0x26,0x28):
    velocity=g.s16(g.read(want,g.OBJ+offset,2));out=g.s32(velocity*230)>>8;g.put(want,g.OBJ+offset,out&65535,2)
  for ws in (retail,rawwords,normalwords):
   m=Connected(ws,c,connected=code,memory=memory);m.run();assert g.public(m.memory)==g.public(want),(c,xspeed,zspeed,"memory");assert m.calls==calls,(c,m.calls,calls);assert m.r[2]==0;visited.update(m.visits)
  n+=1
 result=dict(cases=n,executions=3*n,original_helpers={hex(addr):sum(addr+4*i in visited for i in range(size))for addr,off,size in helpers},height_helper_modeled=True,finite_float_velocity_only=True,source_installed=False,byte_exact=False);(p.out/"connected.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True);return result
