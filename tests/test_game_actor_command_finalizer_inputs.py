"""Qualify direct numeric-byte conversion and the restored primary fault prefix."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_inputs as inputs
from tools.tests import test_game_actor_command_finalizer_scalar as previous
from tools.tests import test_game_actor_command_finalizer_opening as opening
from tools.tests import test_game_actor_command_finalizer_recovery as recovery


class GameActorCommandFinalizerInputsTests(previous.GameActorCommandFinalizerScalarTests):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-inputs-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=recovery.screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt',makefile='conker/Makefile',
            caller='conker/src/game/generated_61490.c',rodata='conker/asm/data/23C630.rodata.s')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']=='e08fb210c38dac11035c5a022e4339ee3075aab3c064aec21f23052aeeda7275'
        assert cls.baseline['elf']=='9f09cfe880661b3727547ecffb17e072a30c5ba5b9b6c44d9b6110417fcff623'
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.owner_before=(cls.out/'before-source').read_text()
        cls.owner_after=inputs.recovered_owner(cls.owner_before)
        compiler=inputs.previous.previous.flow.roles.fitting.compile_candidate
        cls.meta,cls.words=compiler(cls.root,cls.out,'selected',inputs.SELECTED)
        _,cls.banked_words=compiler(cls.root,cls.out,'banked',inputs.BASE)
        _,cls.old_words=compiler(cls.root,cls.out,'old-slot-control',inputs.previous.previous.flow.roles.BASE)
        cls.retail=list(struct.unpack_from('>405I',(cls.root/'conker/conker.us.bin').read_bytes(),recovery.screen.ROM))

    def test_01_original_extent_frame_selector_schedule_and_no_guards(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(405,72,269,0,''))
        self.assertEqual(self.words[:14],self.retail[:14])
        self.assertEqual(self.words[-4:],self.retail[-4:])
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse([r for r in csv.DictReader(stream) if r['function']==recovery.screen.FUNCTION])
        observed=inputs.observations(self.words,self.retail)
        self.assertEqual([r['equal'] for r in observed],[True,True,False,False])
        self.assertEqual(observed[2]['GPRs'],[11,25])
        self.receipt('shape',words=405,frame=72,differences=269,matching_credit=0,
            first14_words_exact=True,primary_cut9_exact=True,observations=observed)

    def test_05_native32_actual_source_and_fresh_effective_negatives(self):
        with patch.object(previous.scalar,'SELECTED',inputs.SELECTED):
            super().test_05_native32_actual_source_and_fresh_effective_negatives()

    def test_06_owned_frame_and_temporary_records(self):
        with patch.multiple(opening.opening,BASE=inputs.BASE,SELECTED=inputs.SELECTED):
            opening.GameActorCommandFinalizerOpeningTests.test_06_owned_frame_and_temporary_records(self)

    def test_09_independent_original_links_and_carry_rebases(self):
        with patch.object(previous.scalar,'SELECTED',inputs.SELECTED):
            super().test_09_independent_original_links_and_carry_rebases()

    def test_12_all_sampled_fired_access_cuts_keep_the_open_boundary(self):
        results=[inputs.fault_sweep(words,self.retail) for words in (self.banked_words,self.words)]
        self.assertEqual((len(results[0]['cases']),results[0]['fired_pairs'],
            results[0]['equal_states']),(52,2938,452))
        selected=results[1]
        self.assertEqual((len(selected['cases']),selected['fired_pairs']),(52,2938))
        self.assertEqual(selected['equal_states'],720)
        self.assertEqual(selected['first_cuts'],{10:44,7:8})
        for old,new in zip(results[0]['cases'],selected['cases']):
            self.assertEqual(old['accesses'],new['accesses'])
            end=9 if new['selectors'][0]!=255 else 6
            self.assertTrue(set(range(end+1)).issubset(new['equal_cuts']))
            self.assertGreater(new['first_difference']['cut'],end)
        self.receipt('fault-boundary',**selected,banked_equal_states=452,
            primary_cut9_closed_paths=44,primary_disabled_cut7_still_open=True,
            whole_private_fault_match=False,hardware_PC_BD_FCSR_not_claimed=True)


if __name__=='__main__':
    unittest.main()
