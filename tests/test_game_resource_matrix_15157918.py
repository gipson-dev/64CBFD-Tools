"""Direct match and bounded semantics for the resource matrix callback."""
import csv
import itertools
import struct
import subprocess
import unittest

from tools.experiments import game_resource_matrix_15157918_match as match
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
from tools.tests import game_resource_matrix_15157918_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put

class ResourceMatrixTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_01_direct_words_and_relocations(self):
  data,refs=match.payload(self.state['after'])
  self.assertEqual((len(data),len(refs)),(400,5))
  self.assertEqual((data,refs),match.payload(self.state['retail']))
  with (match.ROOT/'conker/retail_word_patches.us.csv').open(newline='') as f:
   self.assertFalse(any(r['function']==match.NAME for r in csv.DictReader(f)))
 def test_02_guest_reference_and_mutating_helper(self):
  seen=set();count=0
  for args in itertools.product((0,1),(0,1),(g.bits(0.),g.bits(-1.),g.bits(.5),g.bits(2.)),range(4),(0,8)):
   c=g.Case(*args);expected,calls=g.reference(c);machine=g.Oracle(self.state['words'],c);machine.run()
   self.assertEqual((g.public(machine.memory),machine.calls,machine.r[2]),(expected,calls,1),c)
   seen.update(machine.visits);count+=1
  self.assertEqual(count,128);self.assertEqual(sum(g.ENTRY+4*i in seen for i in range(100)),100)
 def test_03_native_sdk_and_negative_controls(self):
  from tools.tests import game_resource_matrix_15157918_native as native
  self.assertEqual(set(native.profiles),{'-O0','-O2','-O3'})
  for v in native.profiles.values():self.assertEqual((v['cases'],v['negative_controls'],v['UBSan']),(64,4,True))
 def test_04_padders_and_rebases(self):
  a,b=match.pad_both(self.state);self.assertEqual(same_functions(a,b),26)
  data,refs=match.payload(a)
  source='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+match.NAME+'\n.type '+match.NAME+',@function\n'+match.NAME+':\n'
  for i,(word,) in enumerate(struct.iter_unpack('>I',data)):
   for typ,symbol in refs.get(4*i,[]):source+='.reloc ., '+typ+', '+symbol+'\n'
   source+='.word 0x%08X\n'%word
  isolated=match.assemble(source+'.size '+match.NAME+',.-'+match.NAME+'\n','isolated')
  self.assertEqual(match.payload(isolated),(data,refs))
  names=sorted({n for rows in refs.values() for _,n in rows})
  for low in (0,0x7ffc,0x8000,0xfffc):
   symbols={n:(0x15010000+i*0x10000+low if n.startswith('func_') else 0x80010000+i*0x10000+low) for i,n in enumerate(names)}
   expected=bound_blob(data,refs,symbols);script=match.OUT/('rebase-%04x.ld'%low);script.write_text('SECTIONS { .text 0x15157918 : SUBALIGN(4) { *(.text) } }\n')
   elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
   cmd=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(isolated)]
   z=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr)
   subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True)
   self.assertEqual(list(struct.unpack_from('>100I',binary.read_bytes())),expected)
 def test_05_connected_production_resource_dispatch(self):
  parent,second,update,link=0x151572D0,0x8008ADA0,0x1503F4B0,0x32000
  retail=struct.unpack_from('>84I',self.state['rom'],0x184780)
  live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
  self.assertEqual(tuple(live['func_151572D0']),retail)
  connected=dict(zip(range(g.ENTRY,g.ENTRY+400,4),self.state['words']))
  class Model(FactoryOracle):
   def __init__(self,c,m):super().__init__(retail,m,c,entry=parent,arguments=(g.OBJ,),connected=connected);self.recorded=[]
   def record_call(self,t):
    if t==g.HELPER:self.recorded.append((t,tuple(self.r[4:8])))
    else:
     assert t in (g.ENTRY,update),hex(t);self.recorded.append((t,(self.r[4],)))
   def hook(self,t):
    if t==g.HELPER:g.matrix_effect(self.memory,self.case,self.r[4])
    else:assert t==update
    for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
    for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
    self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
  count=0
  for idx,mut,scale,pattern,phase in itertools.product((0,1),(0,1),(g.bits(-1.),g.bits(.5)),range(4),(0,8)):
   c=g.Case(idx,mut,scale,pattern,phase);memory=g.fixture(c);memory[g.OBJ+0x10]=0;memory[g.OBJ+0x11]=255;memory[g.OBJ+0x12]=1
   put(memory,g.OBJ+0x68,link);memory.update({second+i:0 for i in range(8)});put(memory,second+4,g.ENTRY)
   expected,calls=g.reference(c)
   for address,value in g.public(memory).items():
    if address not in expected:expected[address]=value
   expected[g.OBJ+0x10]=0;expected[g.OBJ+0x11]=255;expected[g.OBJ+0x12]=1;put(expected,g.OBJ+0x68,link)
   model=Model(c,memory);model.run();self.assertEqual(g.public(model.memory),expected)
   self.assertEqual(model.recorded,[(g.ENTRY,(g.OBJ,))]+calls+[(update,(link,))]);count+=1
  self.assertEqual(count,64)
