"""Owner, guest, native, relocation, original caller and provider checks."""
import struct,subprocess,unittest
from tools.experiments import game_random_point_15146e84_match as match
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_random_point_15146e84_oracle as oracle
from tools.tests import game_random_point_15146e84_native as native
from tools.tests import game_random_point_15146e84_caller as caller

class RandomPointEffectTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_01_direct_owner_and_padding(self):
  self.assertEqual(len(self.state['raw_words']),111);self.assertEqual(match.MANIFEST['guard_rows'],[]);self.assertEqual(self.state['raw_words'],self.state['retail_words'])
  one,two=match.pad_both(self.state);self.assertEqual(same_functions(one,two),13);self.assertEqual(oracle.words(one),self.state['retail_words'])
 def test_02_guest_reference(self):
  r=oracle.run(self.state);self.assertEqual((r['cases'],r['bodies'],r['retail_words_visited']),(8192,3,111))
 def test_03_native_and_controls(self):
  for r in native.run(self.state).values():self.assertEqual((r['cases'],r['negative_controls'],r['UBSan']),(4096,11,True))
 def test_04_relocations_and_rebases(self):
  one,_=match.pad_both(self.state);data,refs=match.payload(one);self.assertEqual((len(data),len(refs)),(444,11))
  source='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+match.NAME+'\n.type '+match.NAME+',@function\n'+match.NAME+':\n'
  for i,(word,) in enumerate(struct.iter_unpack('>I',data)):
   for typ,name in refs.get(4*i,[]):source+='.reloc ., '+typ+', '+name+'\n'
   source+='.word 0x%08X\n'%word
  isolated=match.assemble(source+'.size '+match.NAME+',.-'+match.NAME+'\n','isolated');self.assertEqual(match.payload(isolated),(data,refs))
  names=sorted({n for row in refs.values() for _,n in row})
  for low in (0,0x7ffc,0x8000,0xfffc):
   symbols={n:0x15100000+i*0x10000+low for i,n in enumerate(names)};expected=bound_blob(data,refs,symbols);script=match.OUT/('rebase-%04x.ld'%low);script.write_text('SECTIONS { .text 0x15146E84 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
   cmd=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(isolated)];z=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr)
   subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>111I',binary.read_bytes())),expected)
 def test_05_dispatcher_windows(self):self.assertEqual(caller.run(self.state)['cases'],320)
 def test_06_retail_slot_provider(self):
  r=caller.provider(self.state);self.assertEqual((r['cases'],r['provider_words_visited'],r['provider_words']),(96,19,19))
