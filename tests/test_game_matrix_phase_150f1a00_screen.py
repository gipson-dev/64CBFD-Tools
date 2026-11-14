"""Bounded checks for the private actor matrix-phase C candidate."""
import itertools,os,struct,subprocess,sys,unittest
from tools.experiments import game_matrix_phase_150f1a00_screen as source
from tools.tests import game_matrix_phase_150f1a00_guest as guest
from tools.tests import game_matrix_phase_150f1a00_native as native
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

class MatrixPhaseScreen(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.owner,cls.obj=source.prepare()
 def check_module(self,name,marker):
  env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
  result=subprocess.run([sys.executable,'-m','tools.tests.game_matrix_phase_150f1a00_'+name],cwd=source.ROOT,env=env,capture_output=True,text=True,timeout=300)
  self.assertEqual(result.returncode,0,(name,result.stdout,result.stderr));self.assertIn(marker,result.stdout)
 def test_original_and_candidate(self):
  self.assertEqual(guest.verify(guest.retail),480)
  self.assertEqual(guest.verify(guest.candidate_words(self.obj)),480)
 def test_original_direct_call(self):
  rom=(source.ROOT/'conker/conker.us.bin').read_bytes();needle=struct.pack('>I',0x0d43c680)
  hits=[i for i in range(0x2d4b0,0x22d710,4) if rom[i:i+4]==needle]
  self.assertEqual(hits,[0x61bb0])
 def test_original_caller_window(self):
  entry,start,end=0x150f1a00,0x15034700,0x15034708
  window=list(struct.unpack_from('>2I',guest.rom,0x61bb0))
  class Caller(guest.Oracle):
   def __init__(self,code,memory,cosval,mutation):
    connected={entry+i*4:word for i,word in enumerate(code)};connected[end]=0
    TimingOracle.__init__(self,window,memory,entry=start,arguments=(0x76543210,),connected=connected)
    self.cosval=cosval;self.mutation=mutation;self.r[7]=guest.ACTOR
    self.code=WindowCode(self.code,self);self.code.ends=(end,)
   def record_call(self,target):
    if target==entry:self.calls.append((target,self.r[4]))
    else:super().record_call(target)
  cases=0
  for flags,phase,tick,cosval,mutation in itertools.product((0,3,12,15),(-32768,0,32767),(0,1,0xffffffff),(-1.,1.),(0,1)):
   initial=guest.fixture(flags,phase,tick);expected,arg=guest.expected(initial,flags,phase,tick,cosval,mutation)
   for code in (guest.retail,guest.candidate_words(self.obj)):
    m=Caller(code,initial.copy(),cosval,mutation)
    try:m.run()
    except WindowBoundary:pass
    else:self.fail('Expected caller continuation')
    self.assertEqual(m.calls,[(entry,guest.ACTOR),(guest.COS,arg)])
    self.assertEqual(guest.public(m.memory),guest.public(expected))
   cases+=1
  self.assertEqual(cases,144)
 def test_semantic_negative_controls(self):
  scale='    scale = ((cosf((f32)D_800CC298[10] * D_800A18E8) + 1.0f) * 0.5f * D_800A18EC) + D_800A18F0;'
  matrix='    matrix = (f32 *)(*(u32 *)(actor + 0x1d4) + 0xf80);'
  controls={
   'priority':('(flags & 12) == 12','(flags & 12) == 8'),
   'rate':('rates.values[kind] * (u32)D_800BE9E4','(rates.values[kind] + 1u) * (u32)D_800BE9E4'),
   'early-matrix':(scale+'\n'+matrix,matrix+'\n'+scale),
   'four-columns':('col < 3','col < 4'),
  }
  for name,(old,new) in controls.items():
   with self.subTest(name=name):
    obj=source.compile_control(self.owner,name,old,new)
    with self.assertRaises(ValueError):guest.verify(guest.candidate_words(obj))
 def test_native32(self):
  report=native.verify()
  self.assertEqual((report['cases_per_configuration'],report['optimizations'],report['alias_modes']),(480,3,2))
 def test_fault_prefixes(self):self.check_module('fault',"'fault_prefixes': 144")
 def test_relocations(self):self.check_module('rebase',"'gnu_links': 8")
 def test_stale_guards(self):self.check_module('stale',"'stale_preimage_rejections': 96")
 def test_actual_make_and_image(self):self.check_module('image','"strict_exclusions": 0')

if __name__=='__main__':unittest.main()
