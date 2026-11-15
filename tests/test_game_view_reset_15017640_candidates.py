"""Private recovery gates; none of these screens grants production C credit."""
from pathlib import Path
import hashlib,json,os,unittest
from tools.experiments import game_view_reset_15017640_candidates as source
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_view_reset_15017640_oracle as guest

class ViewReset15017640CandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();cls.out=cls.root/source.BUILD
  cls.record=json.loads((cls.out/'production-baseline/fingerprints.json').read_text())
  cls.hashes=cls.record['inputs'];cls.assert_frozen()
 @classmethod
 def assert_frozen(cls):
  for name,want in cls.hashes.items():
   if hashlib.sha256((cls.root/name).read_bytes()).hexdigest()!=want:raise AssertionError('Changed production input: '+name)
 @classmethod
 def tearDownClass(cls):cls.assert_frozen()
 def test_01_raw_forms_and_owner(self):
  source.main();report=json.loads((self.out/'screen.json').read_text())
  self.assertEqual([(r['words'],r['frame'],r['owner_neighbors']) for r in report['candidates']],[(82,40,1)]*2)
  self.assertEqual([r['real_word_differences'] for r in report['candidates']],[20,13]);self.assertEqual(report['c_match_credit'],0)
 def test_02_independent_guest_state_and_providers(self):
  guest.main();report=json.loads((self.out/'guest.json').read_text())
  self.assertEqual((report['cases'],report['streams'],report['observed_words']),(3456,3,[82,82,82]))
  self.assertEqual(report['jal_rom_sites'],[0x355e0]);self.assertEqual(report['literal_pointer_rom_sites'],[])
 def test_03_effective_compiled_source_controls(self):
  before=(self.out/'production-baseline'/source.SOURCE).read_text();body=source.pointer_body();symbols=source.symbols(self.root)
  controls={'old_four_record_draft':body.replace('index < 6','index < 4'),
            'unsigned_position_defaults':body.replace('= D_8009DCB4[','= (u16) D_8009DCB4['),
            'short_scratch_clear':body.replace('sizeof(D_800D24C8)','0x40'),
            'early_far_plane':body.replace('    s32 index;','    s32 index;\n    f32 farPlane = D_800968B0;').replace('53.0f, D_800968B0,','53.0f, farPlane,'),
            'wrong_projection_aspect':body.replace('60.6f','60.0f')}
  cases=(guest.Case(mode=0),guest.Case(mode=1),guest.Case(defaults=(32767,-1,-32768),mode=7))
  killed=[]
  for label,changed in controls.items():
   self.assertNotEqual(changed,body);obj,diagnostics=compile_owner(self.root,self.out,source.recover(before,changed),'control-'+label);self.assertEqual(diagnostics,'')
   words=bound_blob(*payload(obj,source.NAME),symbols);rejected=False
   for c in cases:
    initial=guest.fixture(c)
    m=guest.Oracle(words,initial,c,0x14000000);m.run()
    try:guest.compare(m,guest.reference(initial,c))
    except AssertionError:rejected=True;break
   self.assertTrue(rejected,'Ineffective source control: '+label);killed.append(label)
  report=dict(compiled_source_controls=killed,private=True,c_match_credit=0)
  (self.out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 def test_04_closed_prefix_and_dead_input(self):
  from tools.tests import game_view_reset_15017640_prefix_proof as proof
  proof.main();report=json.loads((self.out/'prefix-proof.json').read_text())
  self.assertEqual((report['prefix_words'],report['identical_suffix_words'],report['dead_input_register']),(34,48,'A2'))
  self.assertEqual(len(report['negative_controls']),3);self.assertFalse(report['normalization_installed'])
if __name__=='__main__':unittest.main()
