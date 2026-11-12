"""Direct owner, bounded guest, native, relocations and connected callers."""
import struct,subprocess,unittest
from tools.experiments import game_script_15079fbc_match as match
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_script_15079fbc_oracle as oracle
from tools.tests import game_script_15079fbc_native as native
from tools.tests import game_script_15079fbc_caller as caller

class ScriptHandlerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_01_owner_and_padding(self):
  self.assertEqual(len(self.state['raw_words']),81);self.assertEqual(match.MANIFEST['guard_rows'],[]);self.assertEqual(self.state['raw_words'],self.state['retail_words']);a,b=match.pad_both(self.state);self.assertEqual(oracle.words(a),oracle.words(b))
 def test_02_guest_reference(self):
  r=oracle.run(self.state);self.assertEqual((r['cases'],r['bodies'],r['retail_words_visited']),(2304,3,80))
 def test_03_native_and_controls(self):
  for r in native.run(self.state).values():self.assertEqual((r['cases'],r['negative_controls'],r['UBSan']),(3072,12,True))
 def test_04_relocations_and_rebases(self):
  one,_=match.pad_both(self.state);data,refs=match.payload(one);self.assertEqual((len(data),len(refs)),(324,22));names=sorted({n for row in refs.values() for _,n in row})
  for low in (0,0x7ffc,0x8000,0xfffc):
   symbols={n:(0x15100000+i*0x10000+low if n.startswith('func_') else 0x80010000+i*0x10000+low) for i,n in enumerate(names)};expected=bound_blob(data,refs,symbols);script=match.OUT/('rebase-%04x.ld'%low);script.write_text('SECTIONS { .text 0x15079FBC : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
   cmd=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(one)];z=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr)
   subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>81I',binary.read_bytes())),expected)
 def test_05_dispatcher_window(self):self.assertEqual(caller.run(self.state)['cases'],256)
 def test_06_original_lookup(self):
  r=caller.lookup(self.state);self.assertEqual((r['cases'],r['helper_words_visited'],r['helper_words']),(96,52,59))
 def test_07_guest_fault_prefixes(self):
  r=oracle.fault_prefixes(self.state);self.assertEqual((r['prefixes'],r['cases'],r['bodies']),(93,6,3))
