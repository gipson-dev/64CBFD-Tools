"""Complete chain-search C, both Make classes, header consumers and strict image."""
import csv,json,struct,subprocess,unittest
from tools.experiments import game_map_chain_search_15105c24_match as match
from tools.tests import game_map_chain_search_15105c24_oracle as guest
from tools.tests.game_map_chain_search_15105c24_native import run as native
from tools.tests.game_map_chain_search_15105c24_proof import prove,negative_controls
from tools.tests import game_map_chain_search_15105c24_debugger as debugger
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
SYMS={n:int(n.split('_')[1],16)for rs in match.SPEC['refs'].values()for _,n in rs}
class ChainSearchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=match.prepare()
 def receipt(self,name,value):(self.p['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
 def test_01_owner_profiles_both_Make_classes_and_header_dependencies(self):
  r=self.p['report'];self.assertEqual((r['body_words'],r['slot_words'],r['raw_words'],r['frame'],r['omissions']),(46,47,47,0,1))
  self.assertEqual((r['mixed_Make']['commands'],r['plain_Make']['commands']),(5,3));self.assertEqual(sum(v['functions']for v in r['dependencies'].values()),62)
  self.assertEqual(r['strict_changed_bytes'],1);self.assertEqual(r['matching_credit'],int(r['source_installed']))
 def test_02_guest_ordered_reads_fault_prefixes_and_original_parent(self):
  p=self.p;result=guest.run(p['words'],p['truth'],match.ROOT)
  self.assertEqual((result['cases'],result['visited_words'],result['public_read_prefixes'],result['caller_cases']),(288,[46,45],37,64));self.receipt('guest',result)
 def test_03_native_SDK32_and_effective_source_controls(self):
  p=self.p;result=native(match.ROOT,p['out'],match.SPEC['types'],match.SPEC['fragment'],guest)
  self.assertEqual((result['cases_each_profile'],result['profiles'],result['controls']),(288,3,7))
 def test_04_complete_node_loop_induction_and_semantic_controls(self):
  p=self.p;result=prove(p['words'],p['truth']);self.assertEqual(result['covered_words'],[46,45])
  self.assertEqual(sum(v['paths']for v in result['phases'].values()),37)
  controls=negative_controls(p['words'],p['truth']);self.assertEqual(controls['effective_negatives'],9);self.receipt('relation-controls',controls)
 def test_05_closed_normalizer_and_both_real_guard_rejections(self):
  p=self.p;count=0
  for at in range(0,len(p['raw']),4):
   wrong=bytearray(p['raw']);wrong[at+3]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(wrong),p['refs'])
   count+=1
  for at,rs in p['refs'].items():
   wrong=dict(p['refs']);wrong[at]=[(rs[0][0],'wrong_symbol')]
   with self.assertRaises(ValueError):match.normalize(p['raw'],wrong)
   count+=1
  out=p['out']
  with(out/'proposed-guards.csv').open(newline='')as stream:reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
  guards=0
  for i,row in enumerate(rows):
   if row['function']!=match.FUNCTION:continue
   for kind in('expected','expected_relocations'):
    broken=[dict(v)for v in rows];broken[i][kind]='0x%08X'%(int(row['expected'],0)^1)if kind=='expected'else'R_MIPS_HI16:wrong_symbol'
    path=out/'bad-guard.csv'
    with path.open('w',newline='')as stream:w=csv.DictWriter(stream,fieldnames=fields);w.writeheader();w.writerows(broken)
    with self.assertRaises(ValueError):match.pc.emit_padded_assembly(out/'owner-after.o',match.ROOT/'conker/retail_layout.us.txt',match.SPEC['owner'],word_patches_path=path)
    with self.assertRaises(ValueError):match.pg.emit_padded_assembly(out/'owner-after.o',p['fullasm'],filename=match.SPEC['owner'],word_patches_path=path)
    guards+=2
  self.receipt('normalizer-controls',dict(effective_controls=count,guard_controls=guards,source_omissions=1,no_retail_replacement_word_array=True))
 def test_06_independent_GNU_links_and_signed_low_half_carry(self):
  p=self.p;out=p['out'];assembly,missing=emit_function(p['normal'],dict(value=0,size=184),p['normal_refs'],match.FUNCTION,SYMS);self.assertFalse(missing)
  obj=match.assemble('normalized-isolated',assembly);self.assertEqual(match.payload(obj,match.FUNCTION),(p['normal'],p['normal_refs']))
  for i,low in enumerate((0,0x7FFC,0x8000,0xFFFC)):
   entry=match.ENTRY+i*0x10000;symbols={n:((v+(i+1)*0x20000)&0xFFFF0000)|low for n,v in SYMS.items()}
   script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
   for label,source in(('C',obj),('original',p['retail'])):
    elf=out/('rebase-%d-%s.elf'%(i,label));args=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf),*['--defsym='+n+'=0x%X'%v for n,v in symbols.items()],str(source)]
    subprocess.run(args,check=True,capture_output=True);data=elf.read_bytes();at=elf_slot_offset(data,entry,184);bodies.append(data[at:at+184])
   self.assertEqual(*bodies)
  self.receipt('GNU-rebases',dict(rebases=4,links=8,body_bytes=184,low_halves=[0,0x7FFC,0x8000,0xFFFC]))
 def test_07_complete_image_data_and_corruption_controls(self):
  p=self.p;image=p['elf'].read_bytes();self.assertEqual(match.strict_image(image),1);at=elf_slot_offset(image,match.ENTRY,188)
  for off in(0x80,len(image)-1,at,at+184):
   wrong=bytearray(image);wrong[off]^=1
   with self.assertRaises(ValueError):match.strict_image(bytes(wrong))
  self.assertEqual((p['report']['strict_changed_bytes'],p['report']['exclusions'],p['report']['functions']),(1,0,6051))
  self.receipt('image-controls',dict(effective_controls=4,changed_bytes=1,exclusions=0))
 def test_08_unpadded_debugger_array_metadata_and_independent_header_pair(self):
  p=self.p;result=debugger.verify(match.ROOT,match.BASE);self.assertEqual(result['functions_unchanged'],1)
  independent=debugger.reproduce(match.ROOT,p['out'],match.SPEC);self.assertEqual(independent['debug_growth'],20)
  root=p['out']/'debugger-guard-root';path=root/debugger.OBJECT;path.parent.mkdir(parents=True,exist_ok=True);data=(match.ROOT/debugger.OBJECT).read_bytes()
  for at in(0x80,len(data)//2,len(data)-1):
   wrong=bytearray(data);wrong[at]^=1;path.write_bytes(wrong)
   with self.assertRaises(ValueError):debugger.verify(root,match.BASE)
  self.receipt('debugger-metadata',dict(audit=result,independent=independent,effective_object_controls=3))
if __name__=='__main__':unittest.main()
