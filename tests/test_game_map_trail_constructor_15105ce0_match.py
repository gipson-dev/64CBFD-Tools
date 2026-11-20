"""Complete constructor relation, providers/callers, real padders and image."""
import csv,json,struct,subprocess,unittest
from types import SimpleNamespace
from tools.experiments import game_map_trail_constructor_15105ce0_match as match
from tools.experiments import game_map_trail_constructor_15105ce0_recovery as source
from tools.tests import game_map_trail_constructor_15105ce0_oracle as guest
from tools.tests.game_map_trail_constructor_15105ce0_native import run as native
from tools.tests.game_map_trail_constructor_15105ce0_proof import prove,negative_controls
from tools.tests.game_map_trail_constructor_15105ce0_connected import run as connected,run_callers
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

class ConstructorMatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=match.prepare()
 def receipt(self,name,value):(self.p['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
 def test_01_owner_actual_Make_both_padders_and_all_slots(self):
  r=self.p['report'];self.assertEqual((r['raw_words'],r['body_words'],r['frame'],r['guards'],r['insertions'],r['omissions']),(233,235,216,126,2,0))
  self.assertEqual(r['unchanged_owner_neighbors'],36);self.assertEqual(r['Make']['commands'],5)
  dep=r['dependencies']['conker/src/game_131F30.c'];self.assertEqual(dep['functions'],11);self.assertEqual(dep['Make']['commands'],3)
 def test_02_full_guest_descriptors_and_provider_mutations(self):
  result=guest.run(self.p['words'],self.p['truth']);self.assertEqual(result['cases'],512);self.receipt('guest',result)
 def test_03_native_SDK32_and_effective_source_controls(self):
  view=SimpleNamespace(ROOT=match.ROOT,OUT=match.PACKET,PREAMBLE=match.SPEC['types'],BODY=match.SPEC['fragment'])
  result=native(view,guest);self.assertEqual((result['cases_each_profile'],result['profiles'],result['controls']),(512,3,8));self.receipt('native',result)
 def test_04_complete_CFG_arithmetic_private_FP_and_semantic_controls(self):
  p=self.p;result=prove(p['words'],p['truth']);self.assertEqual(result['symbolic_paths'],17)
  result=negative_controls(p['words'],p['truth']);self.assertEqual(result['effective_semantic_controls'],14);self.receipt('relation-controls',result)
 def test_05_original_provider_paths_and_independent_PRNG(self):
  result=connected(match.ROOT,self.p['words'],self.p['truth']);self.assertEqual(result['cases'],96);self.receipt('connected-providers',result)
 def test_06_all_four_original_call_setup_and_return_use_windows(self):
  result=run_callers(match.ROOT,self.p['words'],self.p['truth']);self.assertEqual(result['cases'],32);self.receipt('original-callers',result)
 def test_07_closed_words_bindings_and_real_guard_rejections(self):
  p=self.p;count=0
  for at in range(0,len(p['raw']),4):
   bad=bytearray(p['raw']);bad[at+3]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(bad),p['refs'])
   count+=1
  for at,rows in p['refs'].items():
   bad=dict(p['refs']);bad[at]=[(rows[0][0],'wrong_symbol')]
   with self.assertRaises(ValueError):match.normalize(p['raw'],bad)
   count+=1
  with(p['out']/'proposed-guards.csv').open(newline='')as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
  selected=[i for i,row in enumerate(rows)if row['function']==match.FUNCTION]
  indexes=(selected[0],selected[len(selected)//3],selected[2*len(selected)//3],selected[-1]);checks=0
  for index in indexes:
   for kind in('expected','expected_relocations'):
    broken=[dict(row)for row in rows];row=broken[index]
    row[kind]='0x%08X'%(int(row['expected'],0)^1)if kind=='expected'else'R_MIPS_HI16:wrong_symbol'
    path=p['out']/'bad-guard.csv'
    with path.open('w',newline='')as f:writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(broken)
    with self.assertRaises(ValueError):match.pc.emit_padded_assembly(p['out']/'after.o',match.ROOT/'conker/retail_layout.us.txt',match.SPEC['owner'],rodata_symbol='D_800A2420',word_patches_path=path)
    with self.assertRaises(ValueError):match.pg.emit_padded_assembly(p['out']/'after.o',p['fullasm'],filename=match.SPEC['owner'],rodata_symbol='D_800A2420',word_patches_path=path)
    checks+=2
  self.receipt('closed-guard-controls',dict(words_and_bindings=count,padder_controls=checks,representative_guard_groups=4))
 def test_08_independent_GNU_rebases_and_carry(self):
  p=self.p;out=p['out'];assembly,missing=emit_function(p['normal'],dict(value=0,size=940),p['nrefs'],match.FUNCTION,p['syms']);self.assertFalse(missing)
  obj=match.assemble('normalized-isolated',assembly);self.assertEqual(match.payload(obj,match.FUNCTION),(p['normal'],p['nrefs']))
  for i,low in enumerate((0,0x7FFC,0x8000,0xFFFC)):
   entry=match.ENTRY+i*0x10000;symbols={name:((value+(i+1)*0x20000)&0xFFFF0000)|low for name,value in p['syms'].items()}
   script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
   for label,sourceobj in(('C',obj),('original',p['original'])):
    elf=out/('rebase-%d-%s.elf'%(i,label));command=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf),*['--defsym='+name+'=0x%X'%value for name,value in symbols.items()],str(sourceobj)]
    subprocess.run(command,check=True,capture_output=True);data=elf.read_bytes();at=elf_slot_offset(data,entry,940);bodies.append(data[at:at+940])
   self.assertEqual(*bodies)
  self.receipt('GNU-rebases',dict(links=8,rebases=4,low_halves=[0,0x7FFC,0x8000,0xFFFC]))
 def test_09_complete_image_data_and_effective_corruptions(self):
  p=self.p;data=p['elf'].read_bytes();self.assertEqual(match.strict_image(data),0)
  at=elf_slot_offset(data,match.ENTRY,940)
  for off in(0x80,at,at+936,len(data)-1):
   bad=bytearray(data);bad[off]^=1
   with self.assertRaises(ValueError):match.strict_image(bytes(bad))
  self.assertEqual((p['report']['strict_changed_bytes'],p['report']['exclusions'],p['report']['functions']),(0,0,6051))
  self.receipt('strict-image-controls',dict(effective_controls=4,changed_bytes=0,exclusions=0))

if __name__=='__main__':unittest.main()
