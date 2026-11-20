"""Guarded trail-emitter source, ABI, loop relation and strict-image gates."""
import csv,json,struct,subprocess,unittest
from tools.experiments import game_map_trail_emitter_151058b4_match as match
from tools.tests import game_map_trail_emitter_151058b4_match_oracle as guest
from tools.tests.game_map_trail_emitter_151058b4_match_native import native_checks
from tools.tests.game_map_trail_emitter_151058b4_match_proof import prove,negative_controls
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
SYMS={n:int(n.split('_')[1],16)for bindings in match.SPEC['refs'].values()for _,n in bindings}

class TrailMatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=match.prepare()
 def receipt(self,name,value):
  (self.p['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
 def test_01_owner_profile_pools_neighbors_and_actual_Make(self):
  q=self.p['report']
  self.assertEqual(tuple(q[n]for n in('body_words','raw_words','frame','raw_frame','guards','insertions','omissions','unchanged_raw_neighbors')),(197,197,240,248,47,0,0,10))
  self.assertTrue(q['ELF_identical']);self.assertEqual(q['matching_credit'],int(q['source_installed']))
  self.assertEqual(q['Make']['commands'],5);self.assertEqual(q['new_diagnostics'],0)
 def test_02_guest_full_packets_homes_and_guarded_access_order(self):
  p=self.p;result=guest.check(p['truth'],p['words'],p['truth'])
  self.assertEqual((result['cases'],result['visited_words']),(140,[196,196,196]))
  self.assertEqual(result['raw_public_read_order_difference_cases'],68);self.receipt('guest',result)
 def test_03_original_command_wrapper_and_literal_argument_homes(self):
  p=self.p;result=guest.caller_checks(p['truth'],p['words'],p['truth'],match.ROOT)
  self.assertEqual(result['cases'],40);self.receipt('caller',result)
 def test_04_native_SDK32_and_effective_source_controls(self):
  result=native_checks(self.p['out'])
  self.assertEqual((result['cases_each_positive_profile'],result['actual_C_wrapper_cases_each_profile'],result['controls']),(68,54,8))
 def test_05_loop_inductive_relation_and_effective_controls(self):
  p=self.p;result=prove(p['words'],p['truth'])
  self.assertEqual(result['visited_words'],[196,196]);self.assertEqual(result['source_gap_accesses'],0)
  controls=negative_controls(p['words'],p['truth']);self.assertEqual(controls['effective_negatives'],13)
  self.receipt('relation-controls',controls)
 def test_06_closed_normalizer_and_relocation_corruptions(self):
  p=self.p;raw=p['raw'];count=0
  for off in range(0,len(raw),4):
   wrong=bytearray(raw);wrong[off+3]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(wrong),p['refs'])
   count+=1
  for off,bindings in p['refs'].items():
   for i in range(len(bindings)):
    wrong={at:list(rs)for at,rs in p['refs'].items()};kind,name=wrong[off][i];wrong[off][i]=(kind,'wrong_symbol')
    with self.assertRaises(ValueError):match.normalize(raw,wrong)
    count+=1
  self.receipt('normalizer-controls',dict(effective_controls=count,word_controls=197,no_retail_replacement_word_array=True))
 def test_07_independent_GNU_rebases_and_both_pad_guard_controls(self):
  p=self.p;out=p['out'];raw,refs=match.normalize(p['raw'],p['refs'])
  self.assertEqual(match.payload(p['after'],match.FUNCTION),(raw,refs));self.assertTrue(p['report']['Make']['mixed_GLOBAL_ASM_recipe'])
  assembly,missing=emit_function(raw,dict(value=0,size=788),refs,match.FUNCTION,SYMS);self.assertFalse(missing)
  obj=match.assemble('normalized-isolated',assembly);self.assertEqual(match.payload(obj,match.FUNCTION),(raw,refs))
  for i,low in enumerate((0,0x7FFC,0x8000,0xFFFC)):
   entry=match.ENTRY+i*0x10000;syms={n:((v+(i+1)*0x20000)&0xFFFF0000)|low for n,v in SYMS.items()}
   script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
   for label,source in(('C',obj),('retail',p['retail'])):
    elf=out/('rebase-%d-%s.elf'%(i,label));command=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
    command+=['--defsym='+n+'=0x%X'%v for n,v in syms.items()]
    subprocess.run(command+[str(source)],check=True,capture_output=True);data=elf.read_bytes();at=elf_slot_offset(data,entry,788);bodies.append(data[at:at+788])
   self.assertEqual(*bodies)
  with(out/'proposed-guards.csv').open(newline='')as stream:
   reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
  target=[i for i,v in enumerate(rows)if v['function']==match.FUNCTION];self.assertEqual(len(target),47)
  controls=0
  for i in target:
   for kind in('expected','expected_relocations'):
    broken=[dict(v)for v in rows];row=broken[i]
    row[kind]='0x%08X'%(int(row[kind],0)^1)if kind=='expected'else'R_MIPS_HI16:wrong_symbol'
    path=out/'bad-guard.csv'
    with path.open('w',newline='')as stream:
     writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(broken)
    with self.assertRaises(ValueError):match.pc.emit_padded_assembly(out/'after.o',match.ROOT/'conker/retail_layout.us.txt',match.SPEC['owner'],word_patches_path=path)
    with self.assertRaises(ValueError):match.pg.emit_padded_assembly(out/'after.o',p['fullasm'],filename=match.SPEC['owner'],word_patches_path=path)
    controls+=2
  self.receipt('GNU-rebases',dict(rebases=4,independent_links=8,body_bytes=788,guard_controls=controls,low_halves=[0,0x7FFC,0x8000,0xFFFC]))
 def test_08_strict_complete_image_and_effective_corruptions(self):
  p=self.p;r=p['report'];image=p['elf'].read_bytes();self.assertEqual(match.strict_image(image),0)
  self.assertEqual((r['strict_changed_bytes'],r['exclusions'],r['conversion_rows']),(0,0,1));self.assertTrue(r['all_addresses_fixed'])
  at=elf_slot_offset(image,match.ENTRY,788)
  for pos in(0x80,len(image)-1,at,at+784):
   wrong=bytearray(image);wrong[pos]^=1
   with self.assertRaises(ValueError):match.strict_image(bytes(wrong))
  self.receipt('strict-image-controls',dict(changed_bytes=0,exclusions=0,effective_controls=4,all_functions=r['functions']))
 def test_09_actual_direction_definition_and_incompatible_pitch_control(self):
  from tools.experiments import game_map_trail_emitter_151058b4_frame as prior
  result=prior.direction_contract();self.assertTrue(result['correct_contract_compiles_identically']and result['wide_pitch_contract_rejected'])
  self.receipt('direction-contract',result)

if __name__=='__main__':unittest.main()
