"""Guarded sequence completion, bounded models and connected caller."""
import struct,subprocess,unittest
from tools.experiments import game_sequence_1501df04_match as match
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_sequence_1501df04_oracle as oracle
from tools.tests import game_sequence_1501df04_native as native
from tools.tests import game_sequence_1501df04_caller as caller
from tools.tests import test_game_actor_burst_consumer_match as faults

class SequenceCompletionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_owner_and_guards(self):
  self.assertEqual((len(self.state['raw_words']),len(match.MANIFEST['guard_rows'])),(86,2));a,b=match.pad_both(self.state);self.assertEqual(match.payload(a),match.payload(b))
  for row in match.MANIFEST['guard_rows']:
   p=match.OUT/'bad-guard.csv';content=self.state['guards'].read_text();old=row['expected'];needle=','.join((row['filename'],row['function'],row['offset'],old))
   self.assertIn(needle,content);p.write_text(content.replace(needle,needle[:-len(old)]+'0xDEADBEEF',1))
   with self.assertRaises(ValueError):match.pad_both(self.state,p)
 def test_guest(self):
  r=oracle.run(self.state);self.assertEqual((r['cases'],r['bodies'],r['words_visited']),(512,3,86))
 def test_native(self):
  r=native.run();self.assertEqual((r['cases_per_optimization'],r['negative_controls'],r['optimizations']),(256,12,3))
 def test_caller(self):self.assertEqual(caller.run(self.state)['cases'],128)
 def test_real_refresh(self):
  r=caller.real_refresh(self.state);self.assertEqual((r['cases'],r['helper_words']),(16,59))
 def test_rebases(self):
  one,_=match.pad_both(self.state);data,refs=match.payload(one);self.assertEqual((len(data),len(refs)),(344,30))
  names=sorted({n for row in refs.values() for _,n in row})
  text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+match.NAME+'\n.type '+match.NAME+',@function\n'+match.NAME+':\n'
  for i,(word,) in enumerate(struct.iter_unpack('>I',data)):
   for typ,name in refs.get(4*i,[]):text+='.reloc ., '+typ+', '+name+'\n'
   text+='.word 0x%08X\n'%word
  isolated=match.assemble(text+'.size '+match.NAME+',.-'+match.NAME+'\n','isolated-rebase')
  for low in (0,0x7ffc,0x8000,0xfffc):
   symbols={n:(0x15100000+i*0x10000+low if n.startswith('func_') else 0x80010000+i*0x10000+low) for i,n in enumerate(names)}
   expected=bound_blob(data,refs,symbols);script=match.OUT/('rebase-%04x.ld'%low);script.write_text('SECTIONS { .text 0x1501DF04 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
   cmd=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(isolated)];z=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr)
   subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>86I',binary.read_bytes())),expected)
 def test_access_cut_prefixes(self):
  codes=(self.state['raw_words'],self.state['retail_words']);count=0
  for c in (oracle.Case(0,0,0,0,0,0,0,0),oracle.Case(1,1,1,2,0,0,0,8),oracle.Case(1,1,0,3,1,0,0,0)):
   full=oracle.Oracle(codes[0],c).run()
   for cut in range(full.all_accesses):
    results=[]
    for code in codes:
     m=oracle.Oracle(code,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     results.append((m.trace,m.calls,oracle.public(m.memory),tuple(m.r),tuple(m.f),m.current_pc,m.delay_of))
    self.assertEqual(results[0],results[1]);count+=1
  self.assertGreater(count,100)
