"""Original44-row update dispatcher, explicit bounded callbacks and full target."""
from tools.experiments import game_billboard_target_update_1514a19c_match as target_packet
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,re,struct,sys
sys.path.insert(0,str(target_packet.ROOT));o=target_packet.OUT;pass
from tools.tests import game_billboard_target_update_1514a19c_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;ACTOR=g.ACTOR;put,read,half,signed,bits=g.put,g.read,g.half,g.signed,g.bits
PARENT=0x1513CFE4;TABLE=0x80089D60;UPDATE,POST,FREE=0x1513E6E8,0x15149EC4,0x1516972C
@dataclass(frozen=True)
class Case(g.Case):
 active:bool=True
 flags:int=0
 life:int=5
 update:bool=False
 update_result:int=1
 post:bool=False
 post_result:int=0
 mutation:int=0
 invoke:bool=True
 alpha:int=200
 cutoff:int=10
 multiplier:int=3

def fixture(c):
 m=g.fixture(c)
 # Animation-rate branch is bounded to zero; this does not qualify animation services.
 for off in(0x24,0x148,0x14C,0x150):put(m,ACTOR+off,0)
 for off,v,n in((0x10,int(c.active),4),(0x58,c.flags,4),(0x1C,c.life,2),(0x70,int(c.update),1),(0x71,4 if c.invoke else 0,1),(0x72,int(c.post),1),(0x5C,c.alpha,1),(0x6C,c.cutoff,2),(0x6E,c.multiplier,2)):put(m,ACTOR+off,v,n)
 put(m,TABLE+16,g.ENTRY);put(m,0x80089CB8+4,UPDATE);put(m,0x80089E10+4,POST);return m
def update_effect(m,c):
    if c.mutation&1:put(m,ACTOR+0x2C,bits(1.0))
    if c.mutation&2:put(m,ACTOR+0x38,bits(300.0))
    if c.mutation&4:put(m,ACTOR+0x1C,0xFFFF,2)

def parent_reference(initial,c):
    m=dict(initial);calls=[]
    if not read(m,ACTOR+0x10)&1:return m,calls
    expired=False
    if read(m,ACTOR+0x58)&1:
        put(m,ACTOR+0x1C,(half(read(m,ACTOR+0x1C,2))-read(m,g.DELTA))&65535,2);expired=half(read(m,ACTOR+0x1C,2))<0
    if c.update:calls.append((UPDATE,(ACTOR,)));update_effect(m,c);expired|=not c.update_result
    if c.invoke:calls.append((g.ENTRY,(ACTOR,)));m,childcalls,_,_,result=g.reference(m,c);calls.extend(childcalls);expired|=not result
    flags=read(m,ACTOR+0x58);life=half(read(m,ACTOR+0x1C,2));cutoff=half(read(m,ACTOR+0x6C,2));product=signed((life*half(read(m,ACTOR+0x6E,2)))&0xFFFFFFFF)
    if not expired and life<cutoff:
        if flags&0x08000000 and product<m[ACTOR+0x5C]:m[ACTOR+0x5C]=product&255
        if flags&0x10000000 and product<m[ACTOR+0x5C]:m[ACTOR+0x2B]=product&255
    if expired and c.post:calls.append((POST,(ACTOR,)));expired=not c.post_result
    if expired:calls.append((FREE,(ACTOR,)));put(m,ACTOR+0x10,0)
    return m,calls

class Machine(g.Machine):
 def record_call(self,t):
  if t in(g.ENTRY,UPDATE,POST,FREE):
   a=tuple(map(g.u32,self.arguments(1)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  else:super().record_call(t)
 def hook(self,t):
  if t in(g.RNG,g.FRNG):return super().hook(t)
  c=self.c
  if t==UPDATE:update_effect(self.memory,c);value=c.update_result
  elif t==POST:value=c.post_result
  else:assert t==FREE;put(self.memory,ACTOR+0x10,0);value=0xDEAD0001
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def interface():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();reports=[]
 for fn,path,n,equal in [('func_1513CFE4','conker/asm/nonmatchings/game_169510/func_1513CFE4.s',195,True),('func_150ADA20','conker/asm/nonmatchings/game_DAE50/func_150ADA20.s',18,True),('func_150ADA68','conker/asm/nonmatchings/game_DAE50/func_150ADA68.s',25,True)]:
  data=(o/'baseline'/path).read_text();rows=re.findall(r'/\*\s*([0-9A-F]+)\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',data);blob=bytes.fromhex(''.join(w for _,_,w in rows));at,va=int(rows[0][0],16),int(rows[0][1],16);assert len(blob)==4*n and rom[at:at+4*n]==blob;pos=elf_slot_offset(elf,va,4*n);assert (elf[pos:pos+4*n]==blob)==equal
  reports.append(dict(function=fn,words=n,ASM_ROM_equal=True,frozen_ELF_equal=equal,sha256=hashlib.sha256(blob).hexdigest()))
 parent=struct.unpack_from('>195I',rom,0x16A494);pos=elf_slot_offset(elf,PARENT,780);assert elf[pos:pos+780]==rom[0x16A494:0x16A7A0];assert 'void func_1513CFE4(u8 *record)'in(o/'baseline/conker/src/game_169510.c').read_text()
 table=rom[0x22E820:0x22E8D0];assert len(table)==176 and struct.unpack_from('>I',table,16)[0]==g.ENTRY;at=elf_slot_offset(elf,TABLE,176);assert elf[at:at+176]==table
 literals=[];direct=[]
 for off in range(0,len(rom)-3,4):
  word=struct.unpack_from('>I',rom,off)[0]
  if word==g.ENTRY:literals.append(hex(off))
  if word>>26 in(2,3)and word&0x3FFFFFF==g.ENTRY>>2&0x3FFFFFF:direct.append(hex(off))
 assert literals==['0x22e830']and not direct,(literals,direct)
 q=dict(ABI='s32 (u8 *)',originals=reports,table='D_80089D60',table_entries=44,table_index=4,table_sha256=hashlib.sha256(table).hexdigest(),aligned_ROM_literals=literals,aligned_ROM_J_JAL_patterns=direct,production_parent_all195words_retail_exact=True,actual_parent_JALR='0x1513D090',actual_parent_boolean_consumer='0x1513D09C',source_installed=target_packet.installed(),matching_credit=0)
 (o/'interface-qualified.json').write_text(json.dumps(q,indent=2)+'\n');return parent,q

def main():
 parent,iface=interface();count=children=0;seen=set()
 for active,flags,life,pre,post,result,mutation,invoke,rm in itertools.product((False,True),(0,1,0x18000000,0x18000001),(-1,5),(False,True),(False,True),(0,1),(0,4),(False,True),(0,3)):
  c=Case(active=active,flags=flags,life=life,update=pre,post=post,update_result=result,post_result=result,mutation=mutation,invoke=invoke,rm=rm);initial=fixture(c);want,calls=parent_reference(initial,c);models=[]
  for target in(g.streams()[0],g.streams()[1]):
   m=Machine(parent,c,memory=initial,entry=PARENT,arguments=(ACTOR,),connected=dict(zip(range(g.ENTRY,g.ENTRY+484,4),target))).run()
   assert(g.public(m.memory,c),m.calls)==(g.public(want,c),calls),dict(case=str(c),memory_equal=g.public(m.memory,c)==g.public(want,c),actual_calls=m.calls,wanted_calls=calls)
   models.append(m);seen.update(p for p in m.visits if PARENT<=p<PARENT+780)
  assert g.state(models[0])==g.state(models[1]);count+=1;children+=int(active and invoke)
 q=dict(static_interface=iface,original_parent_words_pinned=195,original_parent_words_executed=len(seen),cases_per_stream=count,streams=2,connected_children_per_stream=children,table_index=4,table_entries=44,production_parent_all195words_retail_exact=True,actor_pointer_and_boolean_return_ABI=True,bounded_pre_post_release_providers=True,zero_animation_rate_scope=True,no_parent_matching_credit=True,source_installed=target_packet.installed(),matching_credit=0)
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
