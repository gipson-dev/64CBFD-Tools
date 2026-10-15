"""Standalone source and packed-command controls, independent of ROM fixtures."""
import unittest

from tools.experiments import game_texture_vertex_span as source
from tools.tests import game_texture_vertex_span_oracle as model


class TextureVertexSpanCandidateTests(unittest.TestCase):
    def test_source_scope_variants_and_semantic_controls(self):
        before='#include <ultra64.h>\ns32 func_1510BF60(){return 0;}\nvoid next(void){}\n'
        body=dict(source.variants())['explicit-shared-end']
        after=source.recover(before,body)
        self.assertIn(source.DECLARATIONS,after)
        self.assertIn(body.rstrip(),after)
        self.assertTrue(after.endswith('void next(void){}\n'))
        self.assertEqual(len(list(source.variants())),23)
        self.assertEqual(len(source.negatives(body)),7)
        self.assertTrue(all(text!=body for text in source.negatives(body).values()))
        self.assertIn('            commands--;\n            continue;',body)
        self.assertNotIn('volatile',body)
        self.assertNotIn('register ',body)

    def test_all_triangle_fields_and_backward_cursor_witness(self):
        for kind,count,limit in ((5,3,128),(6,6,128),(16,12,32)):
            for index in range(count):
                for value in range(limit):
                    wanted=[3]*count
                    wanted[index]=value
                    self.assertEqual(model.decode(*model.triangle(kind,wanted)),wanted)
        end=(0xDF000000,0)
        commands=[(0,0),(0x01000000,model.VERTICES),(0x01000000,model.VERTICES+64),
            (0xFD000000,model.TEXTURE),model.triangle(5,[1,5,3]),end]
        row=model.fixture(commands)
        expected,result,visits=model.reference(row['memory'],row['args'])
        self.assertIn(model.COMMANDS+8,visits)
        self.assertEqual(model.read(expected,model.OUTPUT),model.VERTICES+16)
        self.assertEqual(result,9)
        invalid=model.fixture([(0xFD000000,model.TEXTURE),(0x01000000,model.VERTICES),end])
        with self.assertRaisesRegex(ValueError,'No defined vertex base'):
            model.reference(invalid['memory'],invalid['args'])


if __name__=='__main__':
    unittest.main()
