"""Focused batch checks for the three alternate point-effect callbacks."""
import csv,io,itertools,struct,subprocess,unittest
from tools.experiments import game_alternate_point_effect_triple_match as match
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_alternate_point_effect_triple_oracle as oracle
from tools.tests import game_alternate_point_effect_triple_native as native
from tools.tests import game_alternate_point_effect_triple_caller as caller

class AlternatePointEffectTripleTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_01_owner_and_padding(self):
  self.assertEqual(len(match.MANIFEST['guard_rows']),57);one,two=match.pad_both(self.state);self.assertEqual(same_functions(one,two),13)
  for n in match.NAMES:self.assertEqual(oracle.words(one,n),self.state['retail_words'][n])
 def test_02_guest_reference(self):
  r=oracle.run(self.state);self.assertEqual((r['cases_per_target'],r['bodies'],r['retail_words_visited']),([4608]*3,3,[87]*3))
 def test_03_native_and_negatives(self):
  for r in native.run(self.state).values():self.assertEqual((r['cases'],r['per_target'],r['negative_controls'],r['UBSan']),(4320,1440,15,True))
 def test_04_guard_corruptions(self):
  with self.state['guards'].open(newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
  targets=[i for i,r in enumerate(rows) if r['function'] in match.NAMES];self.assertEqual(len(targets),57)
  for index in targets:
   bad=[dict(r) for r in rows];bad[index]['expected']='0x%08X'%(int(bad[index]['expected'],0)^1);out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields);w.writeheader();w.writerows(bad);path=match.OUT/'invalid-guard.csv';path.write_text(out.getvalue())
   for pad,layout in ((match.pad_generated_object,match.ROOT/match.MANIFEST['assembly']),(match.pad_c_object,match.ROOT/'conker/retail_layout.us.txt')):
    with self.assertRaises(ValueError):pad.emit_padded_assembly(self.state['after'],layout,filename=match.OWNER,rodata_symbol=match.RODATA,word_patches_path=path)
 def test_05_relocations_and_rebases(self):
  one,_=match.pad_both(self.state)
  for target,entry in zip(match.NAMES,match.MANIFEST['addresses']):
   data,refs=match.payload(one,target);self.assertEqual((len(data),len(refs)),(352,9));source='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+target+'\n.type '+target+',@function\n'+target+':\n'
   for i,(word,) in enumerate(struct.iter_unpack('>I',data)):
    for typ,name in refs.get(4*i,[]):source+='.reloc ., '+typ+', '+name+'\n'
    source+='.word 0x%08X\n'%word
   isolated=match.assemble(source+'.size '+target+',.-'+target+'\n','isolated-'+target);self.assertEqual(match.payload(isolated,target),(data,refs));names=sorted({n for row in refs.values() for _,n in row})
   for low in (0,0x7ffc,0x8000,0xfffc):
    symbols={n:(0x15100000+i*0x10000+low if n.startswith('func_') else 0x80010000+i*0x10000+low) for i,n in enumerate(names)};expected=bound_blob(data,refs,symbols);script=match.OUT/(target+'-rebase-%04x.ld'%low);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
    cmd=['mips-linux-gnu-ld','-T',str(script),'-e',target,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(isolated)];z=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr);subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>88I',binary.read_bytes())),expected)
 def test_06_connected_caller(self):self.assertEqual(caller.run(self.state)['cases_per_target'],[320]*3)
 def test_07_private_mode_slot_alias(self):
  class Stop(Exception):pass
  class Mutated(oracle.Oracle):
   def hook(self,target):
    if target==oracle.EMIT:raise Stop()
    super().hook(target)
    if target==oracle.SELECT:
     oracle.put(self.memory,self.home-0x38,0x45);oracle.put(self.memory,self.home-0x3c,0x46)
  one,_=match.pad_both(self.state)
  for kind,n in enumerate(match.NAMES):
   c=oracle.Case(kind=kind,amount=114);observed=[]
   for code in (self.state['retail_words'][n],self.state['raw_words'][n],oracle.words(one,n)):
    machine=Mutated(code,c)
    with self.assertRaises(Stop):machine.run()
    observed.append([a[5] for t,a in machine.calls if t==oracle.EMIT][0])
   self.assertEqual(observed,[0x45,0x46,0x45])
 def test_08_connected_retail_providers(self):
  result=caller.run_providers(self.state)
  self.assertEqual(result['cases_per_target'],[112]*3)
  self.assertEqual(result['provider_words'],[30,22,22])
 def test_09_actor_aliases_provider_and_constants(self):
  one,_=match.pad_both(self.state);counts=[0,0,0]
  for kind,which,mode,amount,mutation,phase in itertools.product(range(3),range(3),(1,2),(114,115),(0,1,4,8,16),(0,8)):
   actor=(oracle.SCALE[kind],oracle.TAG[kind],oracle.PTR[kind])[which]-0x40
   c=oracle.Case(kind=kind,actor=actor,mode=mode,amount=amount,mutation=mutation,phase=phase);want,calls,obs=oracle.reference(oracle.fixture(c),c);name=match.NAMES[kind]
   for code in (self.state['raw_words'][name],self.state['retail_words'][name],oracle.words(one,name)):
    m=oracle.Oracle(code,c).run();self.assertEqual((oracle.public(m.memory),m.calls,m.obs),(want,calls,obs),c)
   counts[kind]+=1
  self.assertEqual(counts,[120]*3)
