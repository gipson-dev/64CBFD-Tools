"""Qualify path movement against the retail slot and bounded models."""
import struct,subprocess,unittest
from tools.experiments import game_script_1507602c_match as match
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_sequence_direction_1501fe68_match import elf_slot_offset
from tools.tests import game_script_1507602c_oracle as oracle
from tools.tests import game_script_1507602c_native as native
from tools.tests import game_script_1507602c_caller as caller
from tools.tests import test_game_actor_burst_consumer_match as faults

class PathMovementTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_owner_and_padders(self):
  self.assertEqual(len(self.state['raw_words']),103)
  self.assertEqual(self.state['raw_words'],self.state['retail_words'])
  a,b=match.pad_both(self.state);self.assertEqual(match.payload(a),match.payload(b))
 def test_guest(self):
  image=(match.ROOT/'conker/build/conker.us.elf').read_bytes()
  self.assertEqual(struct.unpack_from('>I',image,elf_slot_offset(image,0x8009a140,4))[0],0x3daaaa7e)
  r=oracle.run(self.state);self.assertEqual((r['cases'],r['bodies'],r['words_visited']),(96,3,85))
 def test_native(self):
  r=native.run();self.assertEqual((r['cases_per_optimization'],r['negative_controls'],r['optimizations']),(48,10,3))
 def test_original_dispatcher(self):
  r=caller.run(self.state);self.assertEqual((r['cases'],r['bodies'],r['table_index']),(64,2,16))
 def test_original_helper(self):
  r=caller.helper(self.state);self.assertEqual((r['cases'],r['bodies'],r['helper_words']),(64,2,110))
 def test_relocation_rebases(self):
  one,_=match.pad_both(self.state);data,refs=match.payload(one)
  self.assertEqual((len(data),len(refs)),(412,9))
  names=sorted({n for row in refs.values() for _,n in row})
  for low in (0,0x7ffc,0x8000,0xfffc):
   symbols={n:(0x15100000+i*0x10000+low if n.startswith('func_') else 0x80010000+i*0x10000+low) for i,n in enumerate(names)}
   expected=bound_blob(data,refs,symbols);script=match.OUT/('rebase-%04x.ld'%low)
   script.write_text('SECTIONS { .text 0x1507602C : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
   cmd=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(one)]
   z=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr)
   subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True)
   self.assertEqual(list(struct.unpack_from('>103I',binary.read_bytes())),expected)
 def test_access_cut_prefixes(self):
  bodies=(self.state['retail_words'],self.state['raw_words']);count=0
  for c in (oracle.Case(0,0,0,.5,0),oracle.Case(1,1,1,100.,8),oracle.Case(1,0,1,10.,0)):
   full=oracle.Oracle(bodies[0],c).run()
   for cut in range(full.all_accesses):
    results=[]
    for code in bodies:
     m=oracle.Oracle(code,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     results.append((m.trace,m.calls,oracle.public(m.memory),tuple(m.r),tuple(m.f),m.current_pc,m.delay_of))
    self.assertEqual(results[0],results[1]);count+=1
  self.assertGreater(count,30)
