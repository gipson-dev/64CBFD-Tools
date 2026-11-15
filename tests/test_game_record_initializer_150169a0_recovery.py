"""Private initializer recovery; keeps every frozen production input fixed."""
import csv,hashlib,io,json,os,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_initializer_150169a0_candidates as source
from tools.tests import game_record_initializer_150169a0_native as native

class RecordInitializer150169A0RecoveryTests(unittest.TestCase):
    def test_z_private_projection(self):
        source.main()
        p=subprocess.run([sys.executable,'-m','tools.experiments.game_record_initializer_150169a0_schedule'],cwd=source.ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        r=json.loads((source.OUT/'projection-report.json').read_text())
        self.assertEqual((r['raw_words'],r['projected_words'],r['table_entries'],r['corruption_controls']),(481,477,79,549))
        self.assertFalse(r['independent_equivalence_proof_pending']);self.assertTrue(r['uncredited']);self.assertFalse(r['production_installation'])
        guards=list(csv.DictReader(io.StringIO((source.ROOT/'conker/retail_word_patches.us.csv').read_text())))
        self.assertFalse([row for row in guards if row['function']==source.NAME])
        print('Scheduling projection remains uninstalled and uncredited',flush=True)

    def test_private_recovery(self):
        record=json.loads((source.OUT/'production-baseline/fingerprints.json').read_text())
        def verify():
            self.assertEqual(record['inputs'],{p:hashlib.sha256((source.ROOT/p).read_bytes()).hexdigest()for p in record['inputs']})
        verify()
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT))
        for module in('tools.experiments.game_record_initializer_150169a0_candidates','tools.tests.game_record_initializer_150169a0_oracle','tools.tests.game_record_initializer_150169a0_return','tools.tests.game_record_initializer_150169a0_callers'):
            p=subprocess.run([sys.executable,'-m',module],cwd=source.ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr)
            print(module+': '+p.stdout.strip(),flush=True)
        try:native.verify_receipt()
        except(FileNotFoundError,ValueError):
            p=subprocess.run([sys.executable,'-m','tools.tests.game_record_initializer_150169a0_native'],cwd=source.ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr);print('Fresh native32 validation: '+p.stdout.strip(),flush=True)
        native_rows=native.verify_receipt()
        rb=Path.read_bytes;exe=source.OUT/'native-O2'
        with patch.object(Path,'read_bytes',lambda p:rb(p)+b'changed'if p==exe else rb(p)):
            with self.assertRaisesRegex(ValueError,'artifact'):native.verify_receipt()
        with patch.object(native,'native_command',lambda opt:[]):
            with self.assertRaisesRegex(ValueError,'profile'):native.verify_receipt()
        print('Native receipts verified; two cache-corruption controls rejected',flush=True)
        verify()
        report=lambda name:json.loads((source.OUT/name).read_text())
        r=report('raw-report.json');self.assertEqual((r['words'],r['frame'],r['retail_saved_registers'],r['candidate_saved_registers'],r['neighbors'],r['real_word_differences'],r['pool_bytes'],r['jump_entries'],r['inputs_unchanged']),(481,88,1,1,2,405,336,79,812))
        self.assertEqual(r['raw_sha256'],'0028b0d4e468e23a1d1bd253c8286eca1bb2572ae5a2b659c83f467fdd8eb4ec')
        r=report('behavior.json');self.assertEqual((r['cases'],r['streams'],r['retail_words_visited'],len(r['effective_controls']),len(r['unreachable_retail_words_proved'])),(686,2,473,3,4))
        self.assertTrue(r['saved_gprs_fprs_and_sp'] and r['public_bytes_and_entry_snapshots']);self.assertFalse(r['raw_fault_or_native_claimed'])
        r=report('caller-report.json');self.assertEqual((r['direct_sites'],r['literal_pointers'],r['caller_cases'],r['streams']),(1,0,48,2));self.assertTrue(r['result_ignored_proven']and r['complete_caller_unqualified'])
        r=report('return-report.json');self.assertEqual((r['instructions'],r['effective_controls'],r['killer']),(68,2,'0x1502acac'))
        self.assertEqual([(r['cases'],r['effective_controls'],r['public_bytes'])for r in native_rows],[(639,7,29090)]*3)

if __name__=='__main__':unittest.main()
