"""Execute the original classifier and both original compiler jump tables."""
from pathlib import Path
from unittest.mock import patch
import json,struct,sys
from tools.experiments import game_source_heading_trail_151945cc_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_source_heading_trail_151945cc_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
GROUPS={14:(0x87,0xB0),15:(0xB1,),16:(0xB4,),17:(0x70,0xB2),18:(0xAB,),13:(0x10,0x38,0x91),12:(0x98,),11:(0x34,),10:(0x47,),1:(0x11,0x14,0x3B),2:(0x5A,0x5F,0x74,0x75,0x7A),3:(0x58,0x5B,0x80),4:(0x16,0x88,0x90),5:(0x9C,),6:(0x9D,),7:(0x96,),8:(0xA0,),9:(0x9F,),19:(0x9A,),0:(0,1,2,3,4)}
def classify(identity):return next((kind for kind,ids in GROUPS.items()if identity in ids),99)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 code=struct.unpack_from('>63I',rom,0x161520)
 assert elf[elf_slot_offset(elf,g.CLASSIFY,252):elf_slot_offset(elf,g.CLASSIFY,252)+252]==struct.pack('>63I',*code)
 table=rom[0x248E10:0x249070];assert len(table)==608
 assert elf[elf_slot_offset(elf,0x800A4350,608):elf_slot_offset(elf,0x800A4350,608)+608]==table
 pointers=struct.unpack('>152I',table);assert all(g.CLASSIFY<=p<g.CLASSIFY+252 and p%4==0 for p in pointers)
 Original=g.Oracle
 class Connected(Original):
  def __init__(self,words,c):
   super().__init__(words,c,connected=dict(zip(range(g.CLASSIFY,g.CLASSIFY+252,4),code)))
   self.memory[g.ACTOR+4]=c.seed
   for i,b in enumerate(table):self.memory[0x800A4350+i]=b
   self.initial=dict(self.memory)
 streams=g.programs();visits=set();count=0
 with patch.object(g,'Oracle',Connected):
  for identity in range(256):
   for category in(0,1,2,255):
    for mode in(0,9):
     c=g.Case(seed=identity,kind=classify(identity),category=category,mode=mode,phase=(identity&1)*8,alias=mode&1)
     machines=[g.check(ws,c)for ws in streams];visits.update(machines[1].visits)
     assert g.state(machines[0])==g.state(machines[1])==g.state(machines[2]);count+=1
 covered={i for i in range(63)if g.CLASSIFY+4*i in visits};assert covered==set(range(63)),sorted(set(range(63))-covered)
 r=dict(cases_per_stream=count,streams=3,original_classifier_words=63,covered_classifier_words=len(covered),original_classifier_tables_bytes=608,
  all_actor_identity_bytes=256,remaining_providers_modeled=True,original_classifier_connected=True,source_installed=packet.installed(),matching_credit=0)
 (out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':main()
