"""Complete attachment source, real padders, relation, execution and caller."""
import hashlib,json,struct,unittest
from tools.experiments import game_strip_attach_151ae0e4_recovery as source,game_strip_attach_151ae0e4_match as matching
from tools.tests import game_strip_attach_151ae0e4_oracle as g,game_strip_attach_151ae0e4_normalization as normalize,game_strip_attach_151ae0e4_proof as proof,game_strip_attach_151ae0e4_caller as caller,game_strip_attach_151ae0e4_native as native
class StripAttachMatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):source.compile_and_check();matching.main()
 @classmethod
 def tearDownClass(cls):source.check_inputs()
 @classmethod
 def programs(cls):
  raw=g.bound_blob(*g.o.payload(source.OUT/'owner.o',source.NAME),g.SYMS);derived=normalize.derive(raw)
  assert hashlib.sha256(struct.pack('>96I',*derived)).hexdigest()==source.PIN['derived_sha256']
  return dict(retail=list(struct.unpack('>96I',(source.OUT/'retail.bin').read_bytes())),raw=raw,derived=derived)
 def test_01_padders_links_and_checked_guards(self):
  row=json.loads((source.OUT/'object-report.json').read_text());self.assertEqual(row['gnu_links'],12);self.assertEqual(row['neighbors_preserved'],32)
  raw=self.programs()['raw']
  for i in range(95):
   bad=raw[:];bad[i]^=1
   with self.assertRaises(AssertionError):normalize.derive(bad)
 def test_02_complete_symbolic_relation_and_controls(self):
  p=self.programs();row=proof.prove(p['retail'],p['derived']);row['controls']=proof.controls(p['retail'],p['derived']);self.assertEqual(row['complete_paths'],6)
  (source.OUT/'symbolic-report.json').write_text(json.dumps(row,indent=2)+'\n')
 def test_03_guest_full_RAM_private_frames_and_FP_order(self):
  programs=self.programs();seen={k:set()for k in programs};n=ops=0
  for c in g.cases():
   runs={name:g.verify(words,c)for name,words in programs.items()};a,b=runs['retail'],runs['derived']
   self.assertEqual(a.memory,b.memory);self.assertEqual(a.boundaries,b.boundaries);self.assertEqual(a.fp,b.fp)
   for name,m in runs.items():seen[name].update(m.visits)
   n+=1;ops+=len(a.fp)
  self.assertEqual((n,ops),(624,8064))
  (source.OUT/'guest-report.json').write_text(json.dumps(dict(cases_per_stream=n,ordered_FP_observations=ops,coverage={k:len(v)for k,v in seen.items()},complete_RAM_and_provider_frames_equal=True,spin_preserved=True),indent=2)+'\n')
 def test_04_new_native32_O0_O2_O3_and_controls(self):
  native.main();(source.OUT/'native-report.json').write_bytes((source.OUT/'native/native-report.json').read_bytes())
 def test_05_complete_original_dispatcher(self):
  row=caller.run(self.programs());self.assertEqual(row['cases_per_stream'],128);self.assertEqual(set(row['caller_coverage'].values()),{30})
  (source.OUT/'caller-report.json').write_text(json.dumps(row,indent=2)+'\n')
if __name__=='__main__':unittest.main()
