"""Qualify retail primary-byte load order without weakening the open fault boundary."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_schedule as schedule
from tools.tests import test_game_actor_command_finalizer_inputs as previous
from tools.tests import test_game_actor_command_finalizer_recovery as recovery


class GameActorCommandFinalizerScheduleTests(previous.GameActorCommandFinalizerInputsTests):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-schedule-test'
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
        assert cls.baseline['source']=='b53f5e1b36f268f51ff6560664a07923449229a95845234c4f67179e381e9301'
        assert cls.baseline['elf']=='3c14e2b16246c2c33855e82c1cb8218311d0490af26f71f2b2f7d0891d4c81f8'
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.owner_before=(cls.out/'before-source').read_text()
        cls.owner_after=schedule.recovered_owner(cls.owner_before)
        compiler=schedule.previous.previous.previous.flow.roles.fitting.compile_candidate
        cls.meta,cls.words=compiler(cls.root,cls.out,'selected',schedule.SELECTED)
        _,cls.banked_words=compiler(cls.root,cls.out,'banked',schedule.BASE)
        _,cls.old_words=compiler(cls.root,cls.out,'old-slot-control',schedule.previous.previous.previous.flow.roles.BASE)
        cls.retail=list(struct.unpack_from('>405I',(cls.root/'conker/conker.us.bin').read_bytes(),recovery.screen.ROM))

    def test_01_original_extent_frame_selector_schedule_and_no_guards(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(405,72,267,0,''))
        self.assertEqual([i for i,(old,new) in enumerate(zip(self.banked_words,self.words)) if old!=new],[81,82])
        self.assertEqual(self.words[81:83],self.retail[81:83])
        self.assertEqual(self.words[:14],self.retail[:14])
        self.assertEqual(self.words[-4:],self.retail[-4:])
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse([r for r in csv.DictReader(stream) if r['function']==recovery.screen.FUNCTION])
        observed=schedule.fault_probes(self.words,self.retail)
        self.assertEqual([r['equal'] for r in observed[:5]],[True,True,False,True,True])
        self.assertEqual(observed[5]['GPRs'],[11,25])
        self.receipt('shape',words=405,frame=72,differences=267,changed_words=[81,82],
            matching_credit=0,first14_words_exact=True,original_load_order=True,observations=observed)

    def test_05_native32_actual_source_and_fresh_effective_negatives(self):
        body=schedule.SELECTED
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(body),profile)[0],0)
        negatives={
            'narrow-first':body.replace('if (first != limit)','if ((u8)first != limit)'),
            'unsigned-jitter':body.replace('actor[0x1FE] * *(s8 *)(actor + 0x202)',
                'actor[0x1FE] * actor[0x202]'),
            'wrong-suppression':body.replace('value == 0x70','value == 0x71'),
            'wrong-sign':body.replace('sign = -1;','sign = 1;'),
            'signed-modulo':body.replace('(u32)func_150ADA20() %','func_150ADA20() %')}
        for name,negative in negatives.items():
            self.assertNotEqual(negative,body,name)
            self.assertNotEqual(self.run_native(name,self.native_source(negative))[0],0,name)
        self.receipt('native',cases=8192,profiles=['O2','O0'],effective_negatives=5,
            actual_reversed_integer_expression=True,signed_jitter_control_effective=True)

    def test_06_owned_frame_and_temporary_records(self):
        with patch.multiple(previous.inputs,BASE=schedule.BASE,SELECTED=schedule.SELECTED):
            super().test_06_owned_frame_and_temporary_records()

    def test_09_independent_original_links_and_carry_rebases(self):
        with patch.object(previous.inputs,'SELECTED',schedule.SELECTED):
            super().test_09_independent_original_links_and_carry_rebases()

    def test_12_all_sampled_fired_access_cuts_keep_the_open_boundary(self):
        results=[schedule.previous.fault_sweep(words,self.retail) for words in (self.banked_words,self.words)]
        old,new=results
        self.assertEqual((len(old['cases']),old['fired_pairs'],old['equal_states']),(52,2938,720))
        self.assertEqual((len(new['cases']),new['fired_pairs'],new['equal_states']),(52,2938,1086))
        self.assertEqual(new['first_cuts'],{10:44,7:8})
        for before,after in zip(old['cases'],new['cases']):
            self.assertEqual(before['accesses'],after['accesses'])
            self.assertTrue(set(before['equal_cuts']).issubset(after['equal_cuts']))
        self.receipt('fault-boundary',**new,banked_equal_states=720,
            no_previously_exact_sampled_states_lost=True,whole_private_fault_match=False,
            primary_cut10_and_disabled_cut7_still_open=True,hardware_PC_BD_FCSR_not_claimed=True)


if __name__=='__main__':
    unittest.main()
