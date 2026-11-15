"""Wave qualification preserves all production inputs before and after adoption."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_model_vertex_wave_1517725c_match as source

class ModelVertexWave1517725CMatchTests(unittest.TestCase):
    def test_match(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/data/231B20.rodata.s','conker/asm/data/24BC30.rodata.s','conker/include/functions.h','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_model_vertex_wave_1517725c_match','tools.tests.game_model_vertex_wave_1517725c_oracle','tools.tests.game_model_vertex_wave_1517725c_native','tools.tests.game_model_vertex_wave_1517725c_callers','tools.tests.game_model_vertex_wave_1517725c_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths})
        out=root/source.BUILD;r=json.loads((out/'raw-report.json').read_text())
        self.assertEqual((r['raw_words'],r['words'],r['frame'],r['guards'],r['inserted_save_restore'],r['neighbors'],r['corruption_controls']),(104,106,48,33,2,8,122))
        self.assertEqual(r['direct_callers'],[0x1b13e8]);self.assertEqual(r['registry_slots'],[])
        r=json.loads((out/'behavior.json').read_text());self.assertEqual((r['cases'],r['streams'],r['private_sine_cases'],r['full_state_prefixes'],r['visited_words']),(267,3,32,171,106))
        r=json.loads((out/'native-report.json').read_text());self.assertEqual([(v['cases'],v['effective_controls'])for v in r],[(284,5)]*3)
        r=json.loads((out/'caller-report.json').read_text());self.assertEqual((r['caller_cases'],r['window_words'],r['slot'],len(r['emitted_controls'])),(128,6,7,3))
        r=json.loads((out/'padder-report.json').read_text());self.assertEqual((r['padders'],r['layouts'],r['gnu_links'],r['owner_functions'],r['guards']),(2,4,12,9,33))

if __name__=='__main__':unittest.main()
