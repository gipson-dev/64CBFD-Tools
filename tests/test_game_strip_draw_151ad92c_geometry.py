"""Complete geometry schedule and symbolic loop relation, with unchanged native replay."""
from pathlib import Path
import hashlib,json,struct,subprocess,unittest
from tools.experiments import game_strip_draw_151ad92c_geometry as source
from tools.tests import game_strip_draw_151ad92c_geometry_normalization as normalize
from tools.tests import game_strip_draw_151ad92c_geometry_proof as proof

class StripDrawGeometryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.guest,cls.caller,cls.native=source.enter_engines()
 @classmethod
 def tearDownClass(cls):
  try:source.check_inputs()
  finally:source.leave_engines()
 @classmethod
 def programs(cls):
  data,refs=cls.guest.o.payload(source.OUT/'owner.o',source.NAME)
  raw=cls.guest.o.bound_blob(data,refs,cls.guest.SYMS);derived,record=normalize.derive(raw)
  assert record==source.PIN['derivation']
  return {'retail':list(struct.unpack('>464I',(source.OUT/'retail.bin').read_bytes())),'raw':raw,'derived':derived}
 def test_01_source_owner_and_fail_closed_schedule(self):
  result=source.compile_and_check();programs=self.programs();self.assertEqual((result['raw_words'],result['frame']),(469,304))
  for index in normalize.CHECKED_INDICES:
   bad=programs['raw'][:];bad[index]^=1
   with self.assertRaises(AssertionError):normalize.derive(bad)
  (source.OUT/'derivation.json').write_text(json.dumps(source.PIN['derivation'],indent=2)+'\n')
 def test_02_entry_and_complete_generic_geometry_relations(self):
  programs=self.programs();a=proof.prefix(programs['retail'],programs['derived']);b=proof.prove(programs['retail'],programs['derived']);controls=proof.controls(programs['retail'],programs['derived'])
  self.assertEqual((a['paths'],b['paths']),(4,8))
  (source.OUT/'symbolic-report.json').write_text(json.dumps(dict(prefix=a,generic=b,controls=controls,source_installed=False,c_match_credit=0),indent=2)+'\n')
 def test_03_complete_finite_execution_and_full_FP_order(self):
  g=self.guest;programs=self.programs();coverage={name:set()for name in programs};n=operations=private=provider=0
  for c in g.cases():
   runs={name:g.verify(words,c)for name,words in programs.items()}
   for name,m in runs.items():coverage[name].update(m.visits)
   a,b=runs['retail'],runs['derived'];self.assertEqual(a.fp,b.fp)
   operations+=len(a.fp);private+=a.memory==b.memory;provider+=a.boundaries==b.boundaries;n+=1
  self.assertEqual((n,operations),(544,306846));self.assertEqual((private,provider),(0,0))
  report=dict(cases_per_stream=n,streams=list(programs),words_visited={k:len(v)for k,v in coverage.items()},all_ordered_FP_observations=operations,all_ordered_FP_equal=True,complete_public_calls_return_and_saved_regs_equal=True,complete_RAM_equal_cases=private,provider_frame_equal_cases=provider,provider_private_state_and_adoption_open=True,source_installed=False,c_match_credit=0)
  (source.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n')
 def test_04_complete_original_caller_with_derived_stream(self):
  import itertools
  programs=self.programs();seen={name:set()for name in programs};n=0
  for seed,category,list_row,depth,budget in itertools.product(range(4),(47,78),(0,1),(0,3),(0,4096)):
   c=self.guest.Case(seed=seed,count=(0,1,3,20)[seed],bank=seed&1,texture=54+(seed>>1&1),pattern=seed,phase=(seed&1)*8,viewport=(0,0xABCD8000,0x12347FFF,0xFFFFFFFF)[seed],mutation=seed*5)
   runs={name:self.caller.one(code,c,category,list_row,depth,budget)for name,code in programs.items()}
   for name,m in runs.items():
    seen[name].update(m.visits);self.assertEqual(self.guest.o.public(m.memory),self.guest.o.public(runs['retail'].memory));self.assertEqual(m.r[2],runs['retail'].r[2])
   n+=1
  report=dict(cases_per_stream=n,streams=list(programs),complete_original_caller=True,caller_words=348,selector_words=47,caller_coverage={name:len({at for at in values if self.caller.CALLER<=at<self.caller.CALLER+1392})for name,values in seen.items()},registered_classes=[47,78],signed_viewport_and_budget_rollback=True,source_installed=False,c_match_credit=0)
  (source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n')
 def test_05_unchanged_native_binaries_and_fingerprinted_replay(self):
  old=source.common.QUALIFICATION/'qualification-primary-final/native';previous=json.loads((old/'native-report.json').read_text())
  self.assertEqual(hashlib.sha256((old/'fixtures.bin').read_bytes()).hexdigest(),previous['fixture_sha256'])
  runs=[]
  for record in previous['runs']:
   stem=record['name']+'-'+record['opt'][1:];src=old/(stem+'.c');exe=old/stem
   self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(),record['source_sha256']);self.assertEqual(hashlib.sha256(exe.read_bytes()).hexdigest(),record['exe_sha256'])
   if record['name']=='selected':self.assertIn(source.common.PIN['body'],src.read_text())
   execution=subprocess.run([str(exe)],capture_output=True,timeout=30);self.assertEqual(execution.returncode,record['exit_code'])
   runs.append(dict(name=record['name'],opt=record['opt'],exit_code=execution.returncode,exe_sha256=record['exe_sha256']))
  self.assertEqual(len(runs),7)
  report=dict(cases=previous['cases'],runs=runs,native_compilation_reused=True,native_execution_fresh=True,unchanged_C_body_and_SDK_inputs_fingerprinted=True,fixture_sha256=previous['fixture_sha256'],no_native_FP_status_claim=True,source_installed=False,c_match_credit=0)
  (source.OUT/'native-replay-report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':unittest.main()
