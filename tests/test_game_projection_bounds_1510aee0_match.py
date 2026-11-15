"""Complete projection qualification without modifying production inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_projection_bounds_1510aee0_match as source

class ProjectionBounds1510AEE0MatchTests(unittest.TestCase):
    def test_match(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/137ED0.s','conker/include/functions.h',
               'conker/build/conker.us.elf','conker/build/conker.ld',
               'conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        digest=lambda:{p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths}
        before=digest();env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        modules=('tools.experiments.game_projection_bounds_1510aee0_match',
                 'tools.tests.game_projection_bounds_1510aee0_proof',
                 'tools.tests.game_projection_bounds_1510aee0_oracle',
                 'tools.tests.game_projection_bounds_1510aee0_native',
                 'tools.tests.game_projection_bounds_1510aee0_callers',
                 'tools.tests.game_projection_bounds_1510aee0_padder')
        for module in modules:
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr)
            print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,digest())
        out=root/source.BUILD
        report=lambda name:json.loads((out/name).read_text())
        r=report('raw-report.json')
        self.assertEqual(tuple(r[k]for k in('raw_words','body_words','slot_words','frame','guards','inserted_nops','neighbors','corruption_controls')),(93,97,100,16,82,4,3,94))
        r=report('proof-report.json')
        self.assertEqual((r['alias_layouts'],r['symbolic_terminal_paths'],r['independent_controls']),(300,2235,3))
        self.assertTrue(r['ordered_fp_dags']and r['full_memory_and_saved_state']and r['late_pointer_alias_control_killed'])
        r=report('behavior.json')
        self.assertEqual((r['cases'],r['streams'],r['visited_body_words'],r['full_state_prefixes'],r['nan_payload_cases'],len(r['emitted_controls'])),(2598,3,96,205,96,3))
        self.assertFalse(r['hardware_nan_rule_verified']or r['raw_fault_order_claimed'])
        self.assertEqual([(r['cases'],r['effective_controls'],r['undefined_sanitizer'])for r in report('native-report.json')],[(2577,5,True)]*3)
        r=report('caller-report.json')
        self.assertEqual((r['direct_sites'],r['caller_cases'],r['streams'],r['literal_registry_pointers']),(4,256,3,0))
        self.assertTrue(r['full_ten_word_packets']);self.assertFalse(r['full_parent_claimed'])
        r=report('padder-report.json')
        self.assertEqual(tuple(r[k]for k in('padders','layouts','gnu_links','owner_functions','guards','words')),(2,4,12,4,82,100))
        self.assertTrue(r['full_owner'])

if __name__=='__main__':unittest.main()
