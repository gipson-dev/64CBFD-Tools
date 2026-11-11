import itertools,json,struct
from tools.experiments import game_effect_ground_motion_150eae24_match as p
from tools.tests import game_effect_ground_motion_150eae24_oracle as g
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_sequence_direction_1501fe68_match import elf_slot_offset
PARENT=0x151603FC;PARENTROM=PARENT-0x15000000+0x2D4B0;TABLE=0x8008B0F0;CLEAN=0x1516972C;TICKS=0x800BE9E4;MARK=0x70000
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();elf=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();parent=struct.unpack_from('>41I',rom,PARENTROM);assert elf[elf_slot_offset(elf,PARENT,164):][:164]==rom[PARENTROM:PARENTROM+164]
 assert struct.unpack_from('>I',rom,0x22FBFC)[0]==p.ENTRY and elf[elf_slot_offset(elf,TABLE+19*4,4):][:4]==struct.pack('>I',p.ENTRY)
 raw,refs=p.payload(p.out/'independent-selected.o');look={v[1]:v[2][1] for v in p.symbol_rows(elf)};words=p.bound_blob(raw,refs,{name:look[name] for es in refs.values() for _,name in es});target=dict(zip(range(p.ENTRY,p.ENTRY+4*len(words),4),words))
 class Caller(g.Oracle):
  def record_call(self,t):
   if t==p.ENTRY:self.calls.append((t,tuple(self.arguments(1))))
   elif t==CLEAN:self.calls.append((t,tuple(self.arguments(1))))
   else:super().record_call(t)
  def hook(self,t):
   if t==CLEAN:
    assert self.calls[-1][1]==(g.ACTOR,);put(self.memory,MARK,1)
    for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
    self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
   else:super().hook(t)
 count=0;seen=set()
 for answer,mutation,expired,skip in itertools.product((0,1),(0,1),(0,1),(0,1)):
  vals=(1.25,-2.75,.5,-1.5,8.5,-2.25,-.5 if expired else 2.,.5);c=g.Case(*(g.b(v) for v in vals),answer,mutation,0,count%3);mem=g.fixture(c);mem[g.ACTOR+0xe]=1 if skip else 0;mem[g.ACTOR+0xf]=19;put(mem,g.ACTOR+0x10,0 if skip else 10,2);put(mem,TICKS,1);put(mem,TABLE+19*4,p.ENTRY);put(mem,MARK,0)
  m=Caller(parent,c,connected=target,memory=mem,entry=PARENT);initial=dict(m.memory);m.run();calls=[t for t,a in m.calls]
  if skip:
   assert calls==[CLEAN] and read(m.memory,MARK)==1 and g.HELPER not in calls
  else:
   want,result,point=g.ref(c,initial);expected=[p.ENTRY,g.HELPER]+([CLEAN] if not result else []);assert calls==expected,(calls,expected);assert m.calls[0][1]==(g.ACTOR,) and m.points==[point];put(want,MARK,0 if result else 1);assert g.public(m.memory)==g.public(want),(c,'memory');assert read(m.memory,MARK)==(0 if result else 1)
  assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:];seen.update(m.visits);count+=1
 report=dict(cases=count,original_dispatcher='func_151603FC',table='D_8008B0F0',index=19,entry_address=hex(TABLE+19*4),original_dispatcher_exact=True,original_table_entry_verified=True,full_parent_executed_bounded=True,ground_and_cleanup_helpers_modeled=True,source_installed=False);(p.out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
