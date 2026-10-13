"""Verify canonicalized tag arithmetic and unchanged production inputs."""
import hashlib
from pathlib import Path
import struct
import unittest

from tools.experiments import game_actor_command_finalizer_tag_dependencies as screen


class GameActorCommandFinalizerTagDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-tag-dependency-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=('conker/src/game/generated_61D10.c','conker/build/conker.us.elf',
            'conker/retail_word_patches.us.csv','conker/Makefile','conker/progress.csv')
        cls.before={p:hashlib.sha256((cls.root/p).read_bytes()).hexdigest() for p in cls.paths}
        assert cls.before[cls.paths[0]]=='76c0c333b9c1de6e9c9cbd3865dc84ea2742692f1b4add3ef6f3a52ef43da27f'
        assert cls.before[cls.paths[1]]=='9c75bf09dcf23dcfb2266396a565a8ca6196a4d41be59eff9ca1c6d3ae58a52b'
        compiler=screen.previous.previous.previous.previous.flow.roles.fitting.compile_candidate
        cls.forms={}
        for name,body in (*screen.candidates(),*screen.advised_placements()):
            meta,words=compiler(cls.root,cls.out,name,body)
            cls.forms[name]=(body,meta,words)
        cls.retail=list(struct.unpack_from('>405I',(cls.root/'conker/conker.us.bin').read_bytes(),
            screen.previous.previous.recovery.screen.ROM))

    def test_01_all_complete_tag_forms_emit_the_literal_baseline(self):
        self.assertEqual(len(self.forms),20)
        for name,(body,meta,words) in self.forms.items():
            early=name.endswith('-e1') or name=='baseline-1' or name.startswith('advised-')
            baseline=self.forms['baseline-'+str(int(early))][2]
            self.assertEqual(words,baseline,name)
            self.assertEqual((meta['body_words'],meta['frame'],meta['differences'],
                meta['pool_bytes'],meta['diagnostics']),(405,72,261 if early else 267,0,''),name)
            self.assertIn('s32 first, s32 second)',body)
            self.assertNotIn('volatile',body)

    def test_02_second_row_keeps_its_own_selector_snapshot(self):
        for name,(body,_meta,_words) in self.forms.items():
            primary,secondary=body.split('        D_800C3EF0 = value;',1)
            self.assertIn('primaryIndex = ',primary,name)
            self.assertIn('primaryIndex = ',secondary,name)
            self.assertEqual(body.count('primaryIndex = '),2,name)
            self.assertIn('actor[0x1FE] * *(s8 *)(actor + 0x202) / limit',secondary)

    def test_03_early_lower_is_still_an_effective_fault_counterexample(self):
        probes=screen.previous.fault_probes(self.forms['baseline-1'][2],self.retail)
        self.assertEqual((probes[1]['equal'],probes[1]['GPRs'],probes[1]['FPRs']),
            (False,[7],[16]))
        current=screen.previous.fault_probes(self.forms['baseline-0'][2],self.retail)
        self.assertTrue(current[1]['equal'])
        self.assertEqual((current[2]['equal'],current[2]['GPRs']),(False,[7]))

    def test_04_production_source_image_guards_profile_and_progress_are_fixed(self):
        self.assertEqual(self.before,{p:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for p in self.paths})

    def test_05_advised_orderings_have_no_new_emitted_instructions(self):
        for name,_body in screen.advised_placements():
            self.assertEqual(self.forms[name][2],self.forms['baseline-1'][2])
            observed=screen.previous.fault_probes(self.forms[name][2],self.retail)
            self.assertEqual((observed[1]['equal'],observed[1]['GPRs'],observed[1]['FPRs']),
                (False,[7],[16]))


if __name__=='__main__':
    unittest.main()
