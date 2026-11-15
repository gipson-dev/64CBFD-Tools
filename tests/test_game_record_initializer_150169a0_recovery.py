"""Private initializer recovery; keeps every frozen production input fixed."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_record_initializer_150169a0_candidates as source

class RecordInitializer150169A0RecoveryTests(unittest.TestCase):
    def test_private_recovery(self):
        record=json.loads((source.OUT/'production-baseline/fingerprints.json').read_text())
        def verify():
            self.assertEqual(record['inputs'],{p:hashlib.sha256((source.ROOT/p).read_bytes()).hexdigest()for p in record['inputs']})
        verify()
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT))
        for module in('tools.experiments.game_record_initializer_150169a0_candidates','tools.tests.game_record_initializer_150169a0_oracle','tools.tests.game_record_initializer_150169a0_callers'):
            p=subprocess.run([sys.executable,'-m',module],cwd=source.ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr)
            print(module+': '+p.stdout.strip(),flush=True)
        verify()
        report=lambda name:json.loads((source.OUT/name).read_text())
        r=report('raw-report.json');self.assertEqual((r['words'],r['frame'],r['retail_saved_registers'],r['candidate_saved_registers'],r['neighbors'],r['real_word_differences'],r['pool_bytes'],r['jump_entries'],r['inputs_unchanged']),(476,88,1,2,2,457,336,79,812))
        self.assertEqual(r['raw_sha256'],'43c4aa83a2394495d3d716ca65675451b2f89e8c2159fc08b9aa4f1d577d3539')
        r=report('behavior.json');self.assertEqual((r['cases'],r['streams'],r['retail_words_visited'],len(r['effective_controls']),len(r['unreachable_retail_words_proved'])),(686,2,473,3,4))
        self.assertTrue(r['saved_gprs_fprs_and_sp'] and r['public_bytes_and_entry_snapshots']);self.assertFalse(r['raw_fault_or_native_claimed'])
        r=report('caller-report.json');self.assertEqual((r['direct_sites'],r['literal_pointers'],r['caller_cases'],r['streams']),(1,0,48,2));self.assertTrue(r['result_use_and_complete_caller_unqualified'])

if __name__=='__main__':unittest.main()
