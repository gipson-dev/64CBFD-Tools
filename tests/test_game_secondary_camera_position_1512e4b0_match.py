"""Secondary camera: whole image, caller, trig, native and strict controls."""
import json,struct,unittest
from unittest.mock import patch
from tools.experiments import game_secondary_camera_position_1512e4b0_match as match
from tools.tests import game_secondary_camera_position_1512e4b0_oracle as guest
from tools.tests import game_secondary_camera_position_1512e4b0_caller as caller
from tools.tests import game_secondary_camera_position_1512e4b0_connections as connections
from tools.tests import game_secondary_camera_position_1512e4b0_native as native
from tools.tests import test_game_attachment_effect_150eee00_match as linking
ROOT=match.ROOT
class SecondaryCameraTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.prepared=match.prepare(ROOT);cls.out=ROOT/match.BUILD;cls.truth=(ROOT/'conker/conker.us.bin').read_bytes()[match.ROM:match.ROM+match.SLOT_SIZE]
 def receipt(self,name,v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
 def test_01_owners_actual_Make_and_strict_whole_image(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['caller_functions_fixed'],q['strict_changed_bytes'],q['exclusions']),(77,40,45,260,0));self.assertTrue(q['caller_object_fixed'])
  blob,refs=match.payload(self.out/'qualified-owner.o');match.checked(blob,refs)
  for i in range(len(blob)):
   bad=bytearray(blob);bad[i]^=1
   with self.assertRaises(ValueError):match.checked(bytes(bad),refs)
  for at in refs:
   bad=dict(refs);bad[at]=[(refs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.checked(blob,bad)
  before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes()
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,match.SLOT_SIZE)):
   bad=bytearray(after);bad[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
  bad=bytearray(self.truth);bad[-1]^=1
  with self.assertRaises(ValueError):match.strict_image(before,after,bytes(bad))
 def test_02_selector_heading_wrap_live_trig_effects_and_faults(self):
  v=guest.guest_checks();self.assertEqual((v['cases_per_body'],v['visited_body_words'],v['fault_prefix_pairs']),(1192,77,115));self.receipt('guest-contract',v)
 def test_03_complete_dispatcher_and_void_pointer_repair(self):
  v=caller.caller_checks();self.assertEqual((v['cases_per_body'],v['target_entered'],v['target_skipped']),(768,272,496));self.receipt('caller-contract',v)
 def test_04_original_sine_cosine_and_polynomial_reference(self):
  v=connections.connection_checks();self.assertEqual((v['cases_per_body'],v['target_words_visited'],v['sine_words_visited'],v['cosine_words_visited']),(96,77,93,67));self.receipt('trig-connections',v)
 def test_05_GNU_rebases_and_public_compiled_counterexamples(self):
  rows={};rebased=0
  with patch.object(linking,'match',match):
   for j in range(6):
    entry=match.ENTRY+j*0x10000;s={k:v+j*(0x20000 if k in('sinf','cosf')else 0x108000)for k,v in guest.SYMS.items()};ws,_=linking.linked(self.out/'qualified-owner.o',entry,s,'rebase-'+str(j),self.out)
    for c in(guest.Case(),guest.Case(view=3,heading=0x8000,speed=guest.bits(.125)),guest.Case(mutation=63),guest.Case(mutation=127),guest.Case(heading=0x7FFF,speed=guest.bits(1e8))):
     initial=guest.fixture(c,s);m=guest.Oracle(ws,initial,c,entry=entry,s=s).run();guest.check(m,initial,c,s=s);rebased+=1
   cases=list(guest.native_cases())
   for name,b in native.controls().items():
    obj,diag=match.compile_owner(ROOT,self.out,match.HEADER+b,'negative-'+name);self.assertFalse(diag);ws,pools=linking.linked(obj,match.ENTRY,guest.SYMS,'negative-link-'+name,self.out,True);witness=None
    for c in cases:
     initial=guest.fixture(c);initial.update(pools);m=guest.Oracle(ws,initial,c).run()
     try:guest.check(m,initial,c,semantic=True)
     except AssertionError:witness=c;break
    self.assertIsNotNone(witness,name);rows[name]=dict(compiled=True,counterexample=vars(witness),private_frame_or_home_not_a_witness=True,literal_words=len(ws))
  self.assertEqual((rebased,len(rows)),(30,14));self.receipt('rebases-controls',dict(GNU_links=6,rebased_cases=rebased,semantic_controls=rows))
 def test_06_native32_wide_conversion_aliasing_and_negative_controls(self):
  for label,source in(('no-alias',(match.HEADER+match.SELECTED).replace('__attribute__((__may_alias__))','')),('narrow',match.HEADER+native.narrow_control())):
   obj,diag=match.compile_owner(ROOT,self.out,source,label+'-IDO-control');self.assertFalse(diag);match.checked(*match.payload(obj))
  v=native.native_checks();self.assertEqual((v['cases_per_profile'],v['semantic_controls']),(433,14));self.receipt('native-summary',v)

if __name__=='__main__':unittest.main()
