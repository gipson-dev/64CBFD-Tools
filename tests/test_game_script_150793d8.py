"""Qualified stack normalization and bounded randomized path writes."""
import csv,io,struct,subprocess,unittest
from tools.experiments import game_script_150793d8_match as match
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_script_150793d8_oracle as oracle
from tools.tests import game_script_150793d8_native as native
from tools.tests import game_script_150793d8_caller as caller
from tools.tests import test_game_actor_burst_consumer_match as faults

class RandomPathTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_guarded_owner(self):
  self.assertEqual((len(self.state['raw_words']),len(match.MANIFEST['guard_rows'])),(102,5))
  raw=self.state['raw_words'];retail=self.state['retail_words'];changed=[i*4 for i,(a,b) in enumerate(zip(raw,retail)) if a!=b]
  self.assertEqual(changed,[0x60,0x6c,0x74,0xa0,0xa4]);a,b=match.pad_both(self.state);self.assertEqual(match.payload(a),match.payload(b))
  for row in match.MANIFEST['guard_rows']:
   p=match.OUT/'bad-guard.csv';content=self.state['guards'].read_text();before=row['expected'];after='0xDEADBEEF';needle=','.join((row['filename'],row['function'],row['offset'],before))
   self.assertIn(needle,content);p.write_text(content.replace(needle,needle[:-len(before)]+after,1))
   with self.assertRaises(ValueError):match.pad_both(self.state,p)
 def test_guest(self):
  r=oracle.run(self.state);self.assertEqual((r['cases'],r['bodies']),(3600,3))
 def test_native(self):
  r=native.run();self.assertEqual((r['cases_per_optimization'],r['negative_controls'],r['optimizations']),(9800,12,3))
 def test_original_dispatcher(self):
  r=caller.run(self.state);self.assertEqual((r['cases'],r['bodies'],r['table_index']),(288,2,180))
 def test_access_cut_prefixes(self):
  bodies=(self.state['raw_words'],self.state['retail_words']);count=0
  for c in (oracle.Case(-1181,0,300,-300,0,0,0,0),oracle.Case(1180,-1180,300,-300,1,1,1,8),oracle.Case(0,0,0,0,0,1,1,0)):
   full=oracle.Oracle(bodies[0],c).run()
   for cut in range(full.all_accesses):
    results=[]
    for code in bodies:
     m=oracle.Oracle(code,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     trace=[e for e in m.trace if not oracle.STACK-1024<=e[1]<oracle.STACK+1024]
     results.append((trace,m.calls,oracle.public(m.memory),m.current_pc,m.delay_of))
    self.assertEqual(results[0],results[1]);count+=1
  self.assertGreater(count,30)
 def test_relocations(self):
  one,_=match.pad_both(self.state);data,refs=match.payload(one);self.assertEqual((len(data),len(refs)),(408,10))
  names=sorted({n for row in refs.values() for _,n in row})
  for low in (0,0x7ffc,0x8000,0xfffc):
   symbols={n:(0x15100000+i*0x10000+low if n.startswith('func_') else 0x80010000+i*0x10000+low) for i,n in enumerate(names)}
   expected=bound_blob(data,refs,symbols);script=match.OUT/('rebase-%04x.ld'%low);script.write_text('SECTIONS { .text 0x150793D8 : SUBALIGN(4) { *(.text) } }\n')
   elf=script.with_suffix('.elf');binary=script.with_suffix('.bin');cmd=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(one)]
   z=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr)
   subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True)
   self.assertEqual(list(struct.unpack_from('>102I',binary.read_bytes())),expected)
