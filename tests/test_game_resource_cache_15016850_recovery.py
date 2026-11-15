"""Private cache qualification with all frozen production inputs preserved."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_resource_cache_15016850_candidates as source

class ResourceCache15016850RecoveryTests(unittest.TestCase):
    def test_recovery(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD
        hashes=json.loads((out/'production-baseline/fingerprints.json').read_text())['inputs']
        verify=lambda:self.assertEqual(hashes,{p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in hashes})
        verify();env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in('tools.experiments.game_resource_cache_15016850_candidates','tools.tests.game_resource_cache_15016850_oracle','tools.tests.game_resource_cache_15016850_native','tools.tests.game_resource_cache_15016850_callers'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        verify();report=lambda n:json.loads((out/n).read_text())
        r=report('raw-report.json');self.assertEqual((r['words'],r['frame'],r['handle_home'],r['saved_registers'],r['retail_saved_registers'],r['real_word_differences'],r['neighbors'],r['inputs_unchanged']),(84,96,80,8,7,76,2,812));self.assertTrue(r['uncredited'])
        r=report('behavior.json');self.assertEqual((r['cases'],r['visited_retail_words'],r['all_count_bytes'],r['alias_cases'],len(r['effective_controls'])),(1440,84,256,32,3));self.assertTrue(r['public_and_helper_snapshots']);self.assertFalse(r['raw_fault_order_claimed'])
        self.assertEqual([(r['cases'],r['effective_controls'],r['undefined_sanitizer'])for r in report('native-report.json')],[(576,6,True)]*3)
        r=report('caller-report.json');self.assertEqual((r['direct_sites'],r['caller_cases'],r['streams']),(1,64,2));self.assertFalse(r['complete_parent_or_return_contract_claimed'])

if __name__=='__main__':unittest.main()
