"""Strip renderer complete source/object/relations/execution/caller gates."""
from pathlib import Path
import hashlib,itertools,json,struct,subprocess,unittest
from tools.experiments import game_strip_draw_151ad92c_recovery as source,game_strip_draw_151ad92c_match as matching
from tools.tests import game_strip_draw_151ad92c_normalization as normalize
from tools.tests import game_strip_draw_151ad92c_suffix_proof as proof
from tools.tests import game_strip_draw_151ad92c_geometry_proof as geometry

class StripDrawMatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  source.compile_and_check();matching.main();cls.guest,cls.caller,cls.native=source.bind_engines()
 @classmethod
 def tearDownClass(cls):
  try:source.check_inputs()
  finally:source.restore_engines()
 @classmethod
 def programs(cls):
  data,refs=cls.guest.o.payload(source.OUT/'owner.o',source.NAME)
  raw=cls.guest.o.bound_blob(data,refs,cls.guest.SYMS);derived,record=normalize.derive(raw)
  assert json.loads(json.dumps(record))==source.PIN['private_transformation']['derivation']
  assert hashlib.sha256(struct.pack('>464I',*derived)).hexdigest()==source.PIN['derived_sha256']
  return {'retail':list(struct.unpack('>464I',(source.OUT/'retail.bin').read_bytes())),'raw':raw,'derived':derived},record
 def test_01_both_padders_rebases_and_guard_controls(self):
  row=json.loads((source.OUT/'object-report.json').read_text())
  self.assertEqual((row['body_words'],row['retail_words'],row['frame'],row['insertions'],row['omissions']),(469,464,304,3,8))
  self.assertEqual(row['stale_CSV_controls'],4*len(source.PIN['guard_rows']));self.assertEqual(row['gnu_links'],12)
  self.assertEqual((row['neighbors_preserved'],row['padders']),(32,2))
  programs,_=self.programs()
  for i in range(469):
   bad=programs['raw'][:];bad[i]^=1
   with self.assertRaises(AssertionError):normalize.derive(bad)
 def test_02_geometry_provider_UV_and_unrestricted_return_relations(self):
  programs,record=self.programs();truth,candidate=programs['retail'],programs['derived']
  result=dict(geometry_entry=geometry.prefix(truth,candidate),geometry_generic=geometry.prove(truth,candidate))
  for phase in('provider','uv','return'):result[phase]=proof.prove(truth,candidate,record,phase)
  result['controls']=proof.controls(truth,candidate,record)
  for name,before,after in(('wrong-point-stride',0x24A50018,0x24A5001C),('wrong-cached-Z-home',0xC7A00100,0xC7A00104)):
   self.assertEqual(candidate.count(before),1);bad=candidate[:];bad[bad.index(before)]=after
   with self.assertRaises(AssertionError):geometry.prove(truth,bad)
  self.assertEqual([result[k]['paths']for k in('geometry_entry','geometry_generic','provider','uv','return')],[4,8,2,4,1])
  (source.OUT/'symbolic-report.json').write_text(json.dumps(result,indent=2)+'\n')
 def test_03_complete_finite_RAM_provider_frames_and_FP_order(self):
  g=self.guest;programs,_=self.programs();coverage={name:set()for name in programs};n=operations=0
  for case in g.cases():
   runs={name:g.verify(words,case)for name,words in programs.items()}
   for name,m in runs.items():coverage[name].update(m.visits)
   a,b=runs['retail'],runs['derived'];self.assertEqual(a.fp,b.fp);self.assertEqual(a.memory,b.memory);self.assertEqual(a.boundaries,b.boundaries)
   operations+=len(a.fp);n+=1
  self.assertEqual((n,operations),(544,306846))
  (source.OUT/'guest-report.json').write_text(json.dumps(dict(cases_per_stream=n,streams=list(programs),coverage={k:len(v)for k,v in coverage.items()},all_ordered_FP_observations=operations,complete_RAM_and_provider_frames_equal=True,padder_execution_reused_by_exact_bound_byte_identity=True),indent=2)+'\n')
 def test_04_unchanged_native_compilation_fingerprinted_fresh_replay(self):
  old=source.ADOPTION.parent/'lifetime-qualified/qualification-primary-final/native';previous=json.loads((old/'native-report.json').read_text())
  self.assertEqual(hashlib.sha256((old/'fixtures.bin').read_bytes()).hexdigest(),previous['fixture_sha256']);runs=[]
  for row in previous['runs']:
   stem=row['name']+'-'+row['opt'][1:];src=old/(stem+'.c');exe=old/stem
   self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(),row['source_sha256']);self.assertEqual(hashlib.sha256(exe.read_bytes()).hexdigest(),row['exe_sha256'])
   if row['name']=='selected':self.assertIn(source.PIN['body'],src.read_text())
   q=subprocess.run([str(exe)],capture_output=True,timeout=30);self.assertEqual(q.returncode,row['exit_code'])
   runs.append(dict(name=row['name'],opt=row['opt'],exit_code=q.returncode,exe_sha256=row['exe_sha256']))
  self.assertEqual(len(runs),7)
  (source.OUT/'native-report.json').write_text(json.dumps(dict(cases=previous['cases'],runs=runs,fixture_sha256=previous['fixture_sha256'],compilation_reused=True,execution_fresh=True),indent=2)+'\n')
 def test_05_complete_original_caller_and_private_stack(self):
  programs,_=self.programs();seen={name:set()for name in programs};n=0
  for seed,category,list_row,depth,budget in itertools.product(range(4),(47,78),(0,1),(0,3),(0,4096)):
   c=self.guest.Case(seed=seed,count=(0,1,3,20)[seed],bank=seed&1,texture=54+(seed>>1&1),pattern=seed,phase=(seed&1)*8,viewport=(0,0xABCD8000,0x12347FFF,0xFFFFFFFF)[seed],mutation=seed*5)
   runs={name:self.caller.one(code,c,category,list_row,depth,budget)for name,code in programs.items()}
   for name,m in runs.items():
    seen[name].update(m.visits);self.assertEqual(self.guest.o.public(m.memory),self.guest.o.public(runs['retail'].memory));self.assertEqual(m.r[2],runs['retail'].r[2])
   self.assertEqual(runs['derived'].memory,runs['retail'].memory);n+=1
  (source.OUT/'caller-report.json').write_text(json.dumps(dict(cases_per_stream=n,streams=list(programs),complete_original_caller=True,caller_words=348,selector_words=47,complete_derived_RAM_and_private_stack_equal=True,caller_coverage={name:len({at for at in values if self.caller.CALLER<=at<self.caller.CALLER+1392})for name,values in seen.items()},registered_classes=[47,78]),indent=2)+'\n')
if __name__=='__main__':unittest.main()
