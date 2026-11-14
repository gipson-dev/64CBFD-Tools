"""Installed group-event selection: compiled guest, caller and native checks."""
from pathlib import Path
import inspect,os,subprocess,sys,unittest
from tools.experiments import game_remaining_donor_candidates as donor

class GroupEventChoice15023264Tests(unittest.TestCase):
    def test_installed_owner(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        out=root/'conker/build/game-group-event-choice-15023264-screen'
        out.mkdir(parents=True,exist_ok=True)
        owner=(root/'conker/src/game/generated_49D30.c').read_text()
        self.assertIn('s32 func_15023264(s32 group, s32 unused)',owner)
        code=inspect.getsource(donor.compile_owner)
        needle="*flags,\n        str(raw.relative_to(root / 'conker'))]"
        self.assertIn(needle,code)
        exec(code.replace(needle,"'-O2', '-g3',\n        str(raw.relative_to(root / 'conker'))]"),donor.__dict__)
        flags=('-O2','-g3','-Wo,-loopunroll,0')
        donor.compile_owner(root,out,owner,'baseline',flags=flags)
        donor.compile_owner(root,out,owner,'selected',flags=flags)
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('guard','padder','behavior','native'):
            name='tools.tests.game_group_event_choice_15023264_'+module
            p=subprocess.run([sys.executable,'-m',name],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,name+'\n'+p.stdout+'\n'+p.stderr)
            print(name+': '+p.stdout.strip(),flush=True)

if __name__=='__main__':
    unittest.main()
