"""Derive the first basis schedule from pinned source instructions only."""
from collections import Counter
import hashlib,json,struct
from pathlib import Path
from tools.tests import game_strip_draw_151ad92c_entry_proof as opening
from tools.experiments import game_strip_draw_151ad92c_basis as source
p=source.OUT
BASE=0x1ADC
PINS={0x1CC8:0x4602F181,0x1CCC:0xC7A80100,0x1CDC:0x4600320D,
0x1CF8:0x440E4000,0x1CFC:0x4616B202,0x1D14:0x461A4000,0x1D1C:0x46000004,
0x1D60:0x46140032,0x1D64:0x4600218D,0x1D6C:0,
0x1D7C:0x8E190048,0x1D80:0x03080019,0x1D84:0x46125101,0x1D88:0x4600218D,
0x1D8C:0x440F3000,0x1D90:0x00007012,0x1D94:0x01C3C021,0x1D98:0x03007025,
0x1D9C:0x000EC180,0x1DA0:0x03387021,0x1DA4:0x4501000A,0x1DA8:0xA5CF0024}
def index(address):return(address-BASE)//4
def derive(words):
 assert len(words)==469
 for address,word in PINS.items():assert words[index(address)]==word,(hex(address),hex(words[index(address)]))
 result,homes=opening.derive(words)
 at=lambda a:words[index(a)]
 result[index(0x1CC8)]=at(0x1CCC)
 result[index(0x1CCC)]=0
 result[index(0x1CDC)]=at(0x1CC8)
 result[index(0x1CF8)]=0
 result[index(0x1CFC)]=0
 result[index(0x1D14)]=at(0x1CDC)
 result[index(0x1D1C)]=at(0x1CF8)
 result[index(0x1D60)]=at(0x1D64)
 result[index(0x1D64)]=at(0x1CFC)
 add=at(0x1D14);ft,fs=add>>16&31,add>>11&31
 result[index(0x1D6C)]=add&~((31<<16)|(31<<11))|fs<<16|ft<<11
 tail=[at(a)for a in(0x1D1C,0x1D80,0x1D7C,0x1D90,0x1D94,0x1D98,0x1D9C,0x1DA0,0x1D84,0x1D60,0x1D88,0x1D8C,0x1DA4,0x1DA8)]
 result[index(0x1D7C):index(0x1DAC)]=tail
 for address in(0x1CF8,0x1CCC):
  assert result[index(address)]==0;del result[index(address)]
 assert len(result)==len(words)
 def branch(w):return w>>26 in(1,2,3,4,5,6,7,20,21,22,23)or w>>26==17 and w>>21&31==8
 assert all(not branch(w)or result[i]==w for i,w in enumerate(words))
 before=Counter(w for w in opening.derive(words)[0]if w)
 before[add]-=1;before[result[index(0x1D6C)-2]]+=1
 # Exactly the original arithmetic/transfers remain, apart from the declared
 # declared norm operand order; no retail instruction range is copied.
 after=Counter(w for w in result if w)
 assert +before==+after,(before-after,after-before)
 return result,dict(home_edits=homes,moved_source_instructions=True,
  removed_vacated_nops=[index(0x1CCC),index(0x1CF8)],
  norm_add_operand_order=[add,add&~((31<<16)|(31<<11))|fs<<16|ft<<11],
  arithmetic_and_transfer_inventory_preserved=True,all_branch_words_and_positions_unchanged=True)
