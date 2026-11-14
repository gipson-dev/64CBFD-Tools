"""Bounded checks for the private actor matrix-phase C candidate."""
import struct,unittest
from tools.experiments import game_matrix_phase_150f1a00_screen as source
from tools.tests import game_matrix_phase_150f1a00_guest as guest

class MatrixPhaseScreen(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.owner,cls.obj=source.prepare()
 def test_original_and_candidate(self):
  self.assertEqual(guest.verify(guest.retail),480)
  self.assertEqual(guest.verify(guest.candidate_words(self.obj)),480)
 def test_original_direct_call(self):
  rom=(source.ROOT/'conker/conker.us.bin').read_bytes();needle=struct.pack('>I',0x0d43c680)
  hits=[i for i in range(0x2d4b0,0x22d710,4) if rom[i:i+4]==needle]
  self.assertEqual(hits,[0x61bb0])
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

if __name__=='__main__':unittest.main()
