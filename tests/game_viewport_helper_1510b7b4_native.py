from pathlib import Path
import re,unittest,json
from tools.tests.test_game_viewport_command_helper import GameViewportCommandHelperTests as Base
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-viewport-helper-shape-screen';text=(out/'owner-candidate.c').read_text();candidate=re.search(r'Gfx \*func_1510B7B4\([^;{}]+\) \{\n.*?\n\}',text,re.S).group(0)
__import__('sys').modules[Base.__module__].__file__=str(root/'tools/tests/test_game_viewport_command_helper.py')
class CandidateNative(Base):
 @classmethod
 def setUpClass(cls):
  super().setUpClass();assert cls.fixture.count(cls.body)==1;cls.fixture=cls.fixture.replace(cls.body,candidate);cls.body=candidate
 @classmethod
 def tearDownClass(cls):pass
names=('test_native_every_unsigned_normalization_value','test_native_slots_pages_packets_and_cursor','test_native_actual_helper_and_color_cursor_connection');suite=unittest.TestSuite(CandidateNative(n) for n in names);r=unittest.TextTestRunner(verbosity=2).run(suite);assert r.wasSuccessful() and r.testsRun==3 and not r.skipped
report={'tests':r.testsRun,'native_cases':CandidateNative.native,'bits':32,'optimization':'O2','strict_aliasing':False,'uncredited':True};assert report['native_cases']==65600;(out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
