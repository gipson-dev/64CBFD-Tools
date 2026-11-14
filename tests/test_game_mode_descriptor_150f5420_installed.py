"""Installed mode-descriptor C, guest behavior, caller and native checks."""
from pathlib import Path
import os,subprocess,sys,unittest
from tools.experiments.game_remaining_donor_candidates import compile_owner

class ModeDescriptor150F5420Tests(unittest.TestCase):
    def test_installed_owner(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        out=root/'conker/build/game-mode-descriptor-150f5420-screen'
        out.mkdir(parents=True,exist_ok=True)
        source=(root/'conker/src/game/generated_1228D0.c').read_text()
        self.assertIn('void *func_150F5420(u32 first, u32 second, u32 third, s32 mode)',source)
        compile_owner(root,out,source,'baseline')
        compile_owner(root,out,source,'selected')
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('guard','padder','behavior','callers','native'):
            name='tools.tests.game_mode_descriptor_150f5420_'+module
            result=subprocess.run([sys.executable,'-m',name],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,name+'\n'+result.stdout+'\n'+result.stderr)
            print(name+': '+result.stdout.strip(),flush=True)

if __name__=='__main__':
    unittest.main()
