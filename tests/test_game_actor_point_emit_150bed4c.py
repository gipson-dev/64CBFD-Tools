"""Focused owner, modeled semantics, guard and caller checks for actor point effect."""
import csv,io,struct,subprocess,unittest
from tools.experiments import game_actor_point_emit_150bed4c_match as match
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_actor_point_emit_150bed4c_oracle as oracle
from tools.tests import game_actor_point_emit_150bed4c_native as native
from tools.tests import game_actor_point_emit_150bed4c_caller as caller

class AlternateActorPointEmitTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_01_owner_and_padding(self):
  self.assertEqual(len(self.state['raw_words']),89);self.assertEqual(len(match.MANIFEST['guard_rows']),17)
  one,two=match.pad_both(self.state);self.assertEqual(same_functions(one,two),7)
  self.assertEqual(oracle.words(one),self.state['retail_words'])
 def test_02_guest_reference(self):
  result=oracle.run(self.state);self.assertEqual((result['cases'],result['bodies'],result['retail_words_visited']),(16384,3,89))
 def test_03_native_and_negatives(self):
  for result in native.run(self.state).values():self.assertEqual((result['cases'],result['negative_controls'],result['UBSan']),(4096,8,True))
 def test_04_guard_corruptions(self):
  with self.state['guards'].open(newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
  targets=[i for i,r in enumerate(rows) if r['function']==match.NAME];self.assertEqual(len(targets),17)
  for index in targets:
   bad=[dict(r) for r in rows];bad[index]['expected']='0x%08X'%(int(bad[index]['expected'],0)^1);out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields);w.writeheader();w.writerows(bad);path=match.OUT/'invalid-guard.csv';path.write_text(out.getvalue())
   for pad,layout in ((match.pad_generated_object,match.ROOT/match.MANIFEST['assembly']),(match.pad_c_object,match.ROOT/'conker/retail_layout.us.txt')):
    with self.assertRaises(ValueError):pad.emit_padded_assembly(self.state['after'],layout,filename=match.OWNER,word_patches_path=path)
 def test_05_relocations_and_rebases(self):
  one,_=match.pad_both(self.state);data,refs=match.payload(one);self.assertEqual((len(data),len(refs)),(356,9))
  source='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+match.NAME+'\n.type '+match.NAME+',@function\n'+match.NAME+':\n'
  for i,(word,) in enumerate(struct.iter_unpack('>I',data)):
   for typ,name in refs.get(4*i,[]):source+='.reloc ., '+typ+', '+name+'\n'
   source+='.word 0x%08X\n'%word
  isolated=match.assemble(source+'.size '+match.NAME+',.-'+match.NAME+'\n','isolated');self.assertEqual(match.payload(isolated),(data,refs))
  names=sorted({n for row in refs.values() for _,n in row})
  for low in (0,0x7ffc,0x8000,0xfffc):
   symbols={n:(0x15100000+i*0x10000+low if not n.startswith('D_') else 0x80010000+i*0x10000+low) for i,n in enumerate(names)};expected=bound_blob(data,refs,symbols);script=match.OUT/('rebase-%04x.ld'%low);script.write_text('SECTIONS { .text 0x150BED4C : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
   cmd=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(isolated)];z=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr)
   subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>89I',binary.read_bytes())),expected)
 def test_06_connected_caller(self):self.assertEqual(caller.run(self.state)['cases'],320)
 def test_07_private_mode_slot_alias(self):
  class Stop(Exception):pass
  class Mutated(oracle.Oracle):
   def hook(self,target):
    if target==oracle.EMIT:raise Stop()
    super().hook(target)
    if target==oracle.SELECT:
     oracle.put(self.memory,self.home-0x34,0x45);oracle.put(self.memory,self.home-0x3c,0x46)
  c=oracle.Case(amount=75);one,_=match.pad_both(self.state);observed=[]
  for code in (self.state['retail_words'],self.state['raw_words'],oracle.words(one)):
   machine=Mutated(code,c)
   with self.assertRaises(Stop):machine.run()
   observed.append([a[5] for t,a in machine.calls if t==oracle.EMIT][0])
  self.assertEqual(observed,[0x45,0x46,0x45])
