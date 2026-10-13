"""Qualify scalar predicate recovery and the complete finalizer contract."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_scalar as scalar
from tools.tests import test_game_actor_command_finalizer_opening as previous
from tools.tests import test_game_actor_command_finalizer_recovery as recovery


class GameActorCommandFinalizerScalarTests(previous.GameActorCommandFinalizerOpeningTests):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-scalar-test'
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
        assert cls.baseline['source']=='d321a244fd33ccda7232f4bff3721e736b46cccb713117afc2ea26a0268d6896'
        assert cls.baseline['elf']=='5d2bb92c40d9b4d2d75f8270d7f9bd803fe198e139b4c0632107b10447820e39'
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.owner_before=(cls.out/'before-source').read_text()
        cls.owner_after=scalar.recovered_owner(cls.owner_before)
        compiler=scalar.previous.flow.roles.fitting.compile_candidate
        cls.meta,cls.words=compiler(cls.root,cls.out,'selected',scalar.SELECTED)
        _,cls.banked_words=compiler(cls.root,cls.out,'banked',scalar.BASE)
        _,cls.old_words=compiler(cls.root,cls.out,'old-slot-control',scalar.previous.flow.roles.BASE)
        cls.retail=list(struct.unpack_from('>405I',(cls.root/'conker/conker.us.bin').read_bytes(),recovery.screen.ROM))

    def test_01_original_extent_frame_selector_schedule_and_no_guards(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(405,72,298,0,''))
        self.assertEqual(self.words[:14],self.retail[:14])
        self.assertEqual(self.words[-4:],self.retail[-4:])
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse([r for r in csv.DictReader(stream) if r['function']==recovery.screen.FUNCTION])
        observed=scalar.previous.opening(self.words,self.retail)
        self.assertEqual(observed['equal_cuts'],[True]*6)
        self.assertEqual(observed['cut5_GPRs'],[])
        self.assertEqual(observed['retail_selector_load_indices'],[9])
        self.receipt('shape',words=405,frame=72,differences=298,matching_credit=0,
            first14_words_exact=True,first6_fault_states_exact=True,opening=observed)

    def test_05_native32_actual_source_and_fresh_effective_negatives(self):
        with patch.object(previous.opening,'SELECTED',scalar.SELECTED):
            super().test_05_native32_actual_source_and_fresh_effective_negatives()

    def test_06_owned_frame_and_temporary_records(self):
        results=[]
        for name,body in (('banked',scalar.BASE),('selected',scalar.SELECTED)):
            record=scalar.previous.flow.roles.fitting.trace(self.root,self.out,name,body)
            self.assertTrue(record['code_unchanged'])
            events=[e for e in record['events'] if e['event']=='frame-write']
            self.assertEqual([e['frame'] for e in events],[8,24,72])
            self.assertEqual((events[-1]['locals'],events[-1]['saved'],events[-1]['outgoing']),(48,8,16))
            definitions=[r['length'] for r in record['records']['optimizer'] if r['name']=='def' and r['storage']=='M']
            offsets=sorted({r['offset']-0x100000000 if r['offset']>=0x80000000 else r['offset']
                for r in record['records']['optimizer'] if r['storage']=='M' and r.get('offset') is not None})
            self.assertEqual(definitions,[48])
            self.assertEqual(offsets,[-48,-40,-36,-28,-24,-20])
            constants=[dict(at=r['byte_offset'],words=r['words'],dtype=r['dtype']) for r in
                record['records']['optimizer'] if r['name']=='rldc' and r['constants']==[124,0]]
            self.assertEqual(len(constants),1)
            self.assertEqual(constants[0]['words'][1],3 if name=='banked' else 7)
            results.append(dict(name=name,M_definition=48,M_offsets=offsets,inputs=record['inputs'],
                category_constant=constants))
        self.receipt('allocation',frames_equal=True,objects_unchanged=True,records=results,
            all_six_role_offsets_preserved=True,constant_register_change_observed=True)

    def test_09_independent_original_links_and_carry_rebases(self):
        with patch.object(previous.opening,'SELECTED',scalar.SELECTED):
            super().test_09_independent_original_links_and_carry_rebases()

    def test_12_all_sampled_fired_access_cuts_keep_the_open_boundary(self):
        domains=[(kind,pattern,1,2,phase) for kind,pattern,phase in
            previous.itertools.product((0,0x42,0x69,0x70,0x7C,0x87),(0,1,3),(0,8))]
        domains += [(kind,0,first,second,phase) for kind,first,second,phase in
            previous.itertools.product((0,0x70),(1,255),(2,255),(0,8))]
        cases=[]
        pairs=equal=0
        for kind,pattern,first,second,phase in domains:
            memory,args=recovery.fixture(kind,pattern,first,second)
            complete=[scalar.previous.faults.InstructionOracle(w,memory,args,phase,0xFFFFFFFF).run()
                for w in (self.retail,self.words)]
            self.assertEqual(complete[0].accesses,complete[1].accesses)
            first_difference=None
            for cut in range(complete[0].accesses):
                models=[]
                for words in (self.retail,self.words):
                    model=scalar.previous.faults.InstructionOracle(words,memory,args,phase,0xFFFFFFFF)
                    model.fault=cut
                    with self.assertRaises(recovery.stream.AccessFault):model.run()
                    self.assertEqual(model.accesses,cut)
                    self.assertIn(model.dispatched_word>>26,(32,33,35,36,37,40,41,43,49,57))
                    models.append(model)
                same=scalar.previous.faults.state(models[0])==scalar.previous.faults.state(models[1])
                if cut<=5:self.assertTrue(same)
                pairs+=1
                equal+=same
                if not same and first_difference is None:
                    first_difference=dict(cut=cut,words=['%08X'%m.dispatched_word for m in models],
                        GPRs=[i for i in range(32) if models[0].r[i]!=models[1].r[i]],
                        memory_equal=models[0].memory==models[1].memory,
                        events_equal=models[0].events==models[1].events,
                        FPRs_equal=models[0].f==models[1].f)
            self.assertIsNotNone(first_difference)
            self.assertGreater(first_difference['cut'],5)
            cases.append(dict(kind=kind,pattern=pattern,selectors=[first,second],phase=phase,
                accesses=complete[0].accesses,first_difference=first_difference))
        self.assertEqual((len(cases),pairs),(52,2938))
        self.assertGreater(equal,260)
        self.receipt('fault-boundary',cases=cases,fired_pairs=pairs,equal_states=equal,
            cut5_closed_for_sampled_paths=True,whole_private_fault_match=False,
            hardware_PC_BD_FCSR_not_claimed=True)

    def test_13_non_selector_fault_is_not_mislabeled_as_a_selector_load(self):
        super().test_13_non_selector_fault_is_not_mislabeled_as_a_selector_load()


if __name__=='__main__':
    unittest.main()
