"""Complete attachment body, aliases, original caller windows and guarded copies."""
import unittest
from tools.experiments import game_attachment_status_1504af10_match as source
from tools.tests import game_attachment_status_1504af10_oracle as guest
from tools.tests import game_attachment_status_1504af10_native as native
from tools.tests import game_attachment_status_1504af10_controls as controls
from tools.tests import game_attachment_status_1504af10_caller as caller
ROOT=source.ROOT
class AttachmentStatusTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=source.prepare(ROOT)
 def test_01_owner_actual_Make_and_entire_image(self):
  self.assertEqual(tuple(self.report[n]for n in('words','raw_words','frame','guards','insertions','raw_neighbors','padded_neighbors','diagnostics','image_changed_bytes','strict_unexplained_bytes')),(123,121,48,30,2,57,57,0,392,0))
  self.assertTrue(self.report['provenance']['all_source_words_used_once'])
 def test_02_guest_aliases_raw_truth_and_original_resolver(self):guest.main()
 def test_03_native_full_flag_domain_and_controls(self):native.main()
 def test_04_insertions_stale_guards_and_IDO_controls(self):controls.main()
 def test_05_original_caller_windows_and_placeholder_boundary(self):caller.main()
 def test_06_scope_and_guard_prefix(self):
  raw,refs=source.payload(ROOT/source.BUILD/'qualified-owner.o')
  for owner,function in(('wrong_owner',source.FUNCTION),(source.OWNER,'wrong_function')):
   with self.assertRaises(ValueError):source.checked(raw,refs,owner,function)
  old=(ROOT/source.BUILD/'frozen'/source.GUARDS).read_bytes();new=source.guards(ROOT/source.BUILD)
  self.assertTrue(new.startswith(old));self.assertIn((ROOT/source.GUARDS).read_bytes(),(old,new))
if __name__=='__main__':unittest.main()
