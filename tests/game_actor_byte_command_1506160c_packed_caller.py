"""Connect both packed-caller layouts to the complete recovered command leaf."""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_actor_byte_command_1506160c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_actor_byte_command_1506160c_guest as g
PARENT=0x150721A4;POINTER=0x800D154C;PACKED=0x800D1580
def main():
 raw=json.loads((out/'wrapper-words.json').read_text());truth=list(struct.unpack_from('>17I',(root/'conker/conker.us.bin').read_bytes(),0x9F654));count=0
 for command,priority,gates,phase in itertools.product(range(256),(0,255),((0,0,0,0),(0,0,0,1)),(0,8)):
  first=(command*17+0xAB)&255;second=(command*31+0xCD)&255;packed=0x80000000|(command<<16)|(second<<8)|first
  c=g.Case(command=command,first=first,second=second,priority=priority,gates=gates,flags=(command*19)&255,forced=command&1,phase=phase)
  pair=[]
  for caller in(raw,truth):
   memory=g.fixture(c);g.put(memory,POINTER,g.ACTOR);g.put(memory,PACKED,packed)
   connected=dict(zip(range(g.ENTRY,g.ENTRY+432,4),g.streams()[0]))
   m=g.Oracle(caller,c,entry=PARENT,connected=connected,memory=memory,args=()).run()
   assert m.calls==[(g.ENTRY,(g.ACTOR,command,first,second,0))]
   assert g.public(m.memory)==g.public(g.reference(m.initial,c))
   assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f==m.before_f
   pair.append((g.public(m.memory),m.calls,m.r[16:24],m.r[28:],m.f))
  assert pair[0]==pair[1];count+=1
 r=dict(cases_per_layout=count,caller_layouts=2,connected_leaf_words=108,actual_packed_global_and_actor_pointer=True,
  raw_19_word_and_retail_17_word_callers_public_ABI_equal=True,frame=32,volatile_private_register_identity_not_claimed=True,source_installed=packet.installed(),matching_credit=0)
 (out/'packed-caller.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
