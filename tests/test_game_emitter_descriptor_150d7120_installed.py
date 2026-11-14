"""Installed emitter descriptor: guest, caller, padding and native checks."""
from pathlib import Path
import os,subprocess,sys,unittest
from tools.experiments.game_remaining_donor_candidates import compile_owner

class EmitterDescriptor150D7120Tests(unittest.TestCase):
    def test_installed_owner(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        out=root/'conker/build/game-emitter-descriptor-150d7120-screen'
        out.mkdir(parents=True,exist_ok=True)
        owner=(root/'conker/src/game/generated_1045D0.c').read_text()
        self.assertIn('void func_150D7120(Position150D7120 *position, u8 slot, s32 context)',owner)
        compile_owner(root,out,owner,'baseline')
        compile_owner(root,out,owner,'selected')
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('guard','padder','behavior','native'):
            name='tools.tests.game_emitter_descriptor_150d7120_'+module
            p=subprocess.run([sys.executable,'-m',name],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,name+'\n'+p.stdout+'\n'+p.stderr)
            print(name+': '+p.stdout.strip(),flush=True)

if __name__=='__main__':
    unittest.main()
