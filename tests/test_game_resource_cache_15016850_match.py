"""Complete guarded resource-cache qualification with production inputs fixed."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_resource_cache_15016850_match as source

class ResourceCache15016850MatchTests(unittest.TestCase):
    def test_match(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD
        paths=json.loads((out/'production-baseline/fingerprints.json').read_text())['inputs']
        digest=lambda:{p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths}
        before=digest();env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in('tools.experiments.game_resource_cache_15016850_match','tools.tests.game_resource_cache_15016850_proof','tools.tests.game_resource_cache_15016850_oracle','tools.tests.game_resource_cache_15016850_native','tools.tests.game_resource_cache_15016850_callers','tools.tests.game_resource_cache_15016850_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,digest());report=lambda n:json.loads((out/n).read_text())
        r=report('match-report.json');self.assertEqual((r['raw_words'],r['words'],r['frame'],r['guards'],r['inserted_derived_words'],r['neighbors'],r['corruption_controls']),(81,84,96,27,3,2,96))
        r=report('proof-report.json');self.assertEqual((r['transfer_paths'],r['proof_controls']),(5,3));self.assertTrue(r['ordered_access_and_call_traces']and r['live_loop_state']and r['original_saved_homes']and r['epilogue_exact']);self.assertFalse(r['full_fault_state_claimed'])
        r=report('behavior.json');self.assertEqual((r['cases'],r['streams'],r['visited_retail_words'],r['all_count_bytes'],r['alias_cases'],len(r['effective_controls'])),(1440,3,84,256,32,3))
        self.assertEqual([(r['cases'],r['effective_controls'],r['undefined_sanitizer'])for r in report('native-report.json')],[(576,6,True)]*3)
        r=report('caller-report.json');self.assertEqual((r['direct_sites'],r['caller_cases'],r['streams'],r['return_proof_controls']),(1,64,3,2));self.assertTrue(r['result_ignored_proven']);self.assertFalse(r['complete_parent_or_return_contract_claimed'])
        r=report('padder-report.json');self.assertEqual((r['padders'],r['layouts'],r['gnu_links'],r['owner_functions'],r['guards'],r['words']),(2,4,12,3,27,84))

if __name__=='__main__':unittest.main()
