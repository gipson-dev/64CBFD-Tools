"""Complete clock qualification without changing production inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_clock_update_1510aa44_match as source

class ClockUpdate1510AA44MatchTests(unittest.TestCase):
    def test_match(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/137ED0.s','conker/asm/data/22D710.rodata.s',
               'conker/include/functions.h','conker/build/conker.us.elf',
               'conker/build/conker.ld','conker/progress.csv','conker/Makefile',
               'conker/retail_word_patches.us.csv')
        digest=lambda:{p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths}
        before=digest();env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in('tools.experiments.game_clock_update_1510aa44_match',
                      'tools.tests.game_clock_update_1510aa44_proof',
                      'tools.tests.game_clock_update_1510aa44_oracle',
                      'tools.tests.game_clock_update_1510aa44_native',
                      'tools.tests.game_clock_update_1510aa44_callers',
                      'tools.tests.game_clock_update_1510aa44_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,digest());out=root/source.BUILD
        report=lambda name:json.loads((out/name).read_text())
        r=report('raw-report.json')
        self.assertEqual(tuple(r[k]for k in('raw_words','words','frame','guards','inserted_nops','neighbors','corruption_controls')),(229,229,64,10,0,3,234))
        r=report('proof-report.json')
        self.assertEqual((r['tail_paths'],r['caller_fprs'],r['register_edit_words'],r['commutative_branches'],r['proof_controls']),(3,6,9,1,2))
        self.assertTrue(r['all_other_bits_and_bindings_fixed']and r['no_renamed_incoming_values_read'])
        r=report('behavior.json')
        self.assertEqual((r['cases'],r['streams'],r['visited_words'],r['full_state_prefixes'],r['whole_record_bytes'],len(r['emitted_controls'])),(2563,3,193,119,272,4))
        self.assertFalse(r['hardware_claimed']or r['raw_fault_order_claimed'])
        self.assertEqual([(r['cases'],r['effective_controls'],r['undefined_sanitizer'])for r in report('native-report.json')],[(2435,7,True)]*3)
        r=report('caller-report.json')
        self.assertEqual((r['registry_index'],r['installer_words'],r['caller_sites'],r['caller_cases'],r['streams'],r['return_poison_values']),(46,22,2,144,3,4))
        self.assertTrue(r['return_ignored']and r['all_installer_words_visited']and r['gate_and_repeated_iteration']);self.assertFalse(r['full_parent_claimed'])
        r=report('padder-report.json')
        self.assertEqual(tuple(r[k]for k in('padders','layouts','gnu_links','owner_functions','guards','words')),(2,4,12,4,10,229))

if __name__=='__main__':unittest.main()
