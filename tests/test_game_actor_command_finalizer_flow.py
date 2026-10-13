"""Locate the finalizer's literal access-fault boundary without matching credit."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest

from tools.experiments import game_actor_command_finalizer_flow as flow
from tools.tests import test_game_actor_command_finalizer_recovery as recovery
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class InstructionOracle(recovery.FinalizerOracle):
    def execute(self,word):
        self.dispatched_word=word
        super().execute(word)


def state(model):
    return (model.memory,model.events,model.r,model.f,model.condition,model.lo,model.hi,model.calls)


class GameActorCommandFinalizerFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-flow-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=recovery.screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            makefile='conker/Makefile',caller='conker/src/game/generated_61490.c',
            layout='conker/retail_layout.us.txt',rodata='conker/asm/data/23C630.rodata.s')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']=='f4a7922c5317deaaec503865d0e0af59bfb29b6d31d1377c31b67b24e0d77024'
        assert cls.baseline['elf']=='6b3a795a43992b6ac9d8ffb736c8d80360a3416936d5ae7708db7c54aa3ecb86'
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.retail=list(struct.unpack_from('>405I',(cls.root/'conker/conker.us.bin').read_bytes(),recovery.screen.ROM))
        forms=dict(flow.candidates())
        cls.bodies={name:forms[name] for name in ('baseline','bounds','clamp','gate-primaryIndex-type-b0-c0')}
        cls.metadata={}
        cls.words={}
        for name,body in cls.bodies.items():
            cls.metadata[name],cls.words[name]=flow.roles.fitting.compile_candidate(cls.root,cls.out,name,body)
        cls.raw=cls.words['baseline']

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_shapes_are_diagnostics_not_an_accepted_fit(self):
        self.assertEqual(len(dict(flow.candidates())),46)
        wanted=dict(baseline=(405,307),bounds=(404,366),clamp=(404,333),
            **{'gate-primaryIndex-type-b0-c0':(403,387)})
        for name,record in self.metadata.items():
            self.assertEqual((record['body_words'],record['differences']),wanted[name])
            self.assertEqual((record['frame'],record['pool_bytes'],record['diagnostics']),(72,0,''))
        self.assertEqual(self.raw,list(struct.unpack_from('>405I',self.before,
            elf_slot_offset(self.before,recovery.screen.ENTRY,1620))))
        self.assertNotEqual(self.raw,self.retail)
        self.receipt('shapes',forms=46,controls=wanted,accepted_new_fit=False,matching_credit=0)

    def test_02_bounded_public_controls_do_not_establish_private_fit(self):
        cases=0
        for kind,pattern,first,second,phase in itertools.product(
                (0,0x42,0x70,0x7C),(0,1,3),(1,255),(2,255),(0,8)):
            memory,args=recovery.fixture(kind,pattern,first,second)
            original=recovery.FinalizerOracle(self.retail,memory,args,phase,0xFFFFFFFF).run()
            for name,words in self.words.items():
                model=recovery.FinalizerOracle(words,memory,args,phase,0xFFFFFFFF).run()
                self.assertEqual((recovery.public(model.memory),model.r[2],model.calls),
                    (recovery.public(original.memory),original.r[2],original.calls),name)
            cases+=1
        self.receipt('public-controls',cases_per_body=cases,bodies=len(self.words),
            private_alias_native_owner_rebase_qualification=False,installable_controls=False)

    def test_03_every_common_fired_access_cut_locates_first_divergence(self):
        cases=[]
        pairs=equal=0
        domains=[(kind,pattern,1,2,phase) for kind,pattern,phase in
            itertools.product((0,0x42,0x69,0x70,0x7C,0x87),(0,1,3),(0,8))]
        domains += [(kind,0,first,second,phase) for kind,first,second,phase in
            itertools.product((0,0x70),(1,255),(2,255),(0,8))]
        for kind,pattern,first,second,phase in domains:
            memory,args=recovery.fixture(kind,pattern,first,second)
            complete=[InstructionOracle(w,memory,args,phase,0xFFFFFFFF).run() for w in (self.retail,self.raw)]
            self.assertEqual((recovery.public(complete[0].memory),complete[0].r[2],complete[0].calls),
                (recovery.public(complete[1].memory),complete[1].r[2],complete[1].calls))
            counts=[m.accesses for m in complete]
            self.assertEqual(counts[0],counts[1])
            first_difference=None
            for cut in range(min(counts)):
                pair=[]
                for words in (self.retail,self.raw):
                    model=InstructionOracle(words,memory,args,phase,0xFFFFFFFF)
                    model.fault=cut
                    with self.assertRaises(recovery.stream.AccessFault):
                        model.run()
                    self.assertEqual(model.accesses,cut)
                    self.assertIn(model.dispatched_word>>26,(32,33,35,36,37,40,41,43,49,57))
                    pair.append(model)
                same=state(pair[0])==state(pair[1])
                equal+=same
                pairs+=1
                if not same and first_difference is None:
                    registers=[i for i in range(32) if pair[0].r[i]!=pair[1].r[i]]
                    first_difference=dict(cut=cut,words=['%08X'%m.dispatched_word for m in pair],
                        changed_GPRs=registers,memory_equal=pair[0].memory==pair[1].memory,
                        events_equal=pair[0].events==pair[1].events,
                        FPRs_equal=pair[0].f==pair[1].f,RA_equal=pair[0].r[31]==pair[1].r[31])
            self.assertIsNotNone(first_difference)
            self.assertEqual(first_difference['cut'],5)
            self.assertTrue(first_difference['memory_equal'])
            self.assertTrue(first_difference['events_equal'])
            self.assertTrue(first_difference['FPRs_equal'])
            self.assertTrue(first_difference['RA_equal'])
            cases.append(dict(kind=kind,pattern=pattern,selectors=[first,second],phase=phase,
                accesses=counts,first_difference=first_difference))
        self.assertEqual(len(cases),52)
        self.assertEqual((pairs,equal),(2938,260))
        self.receipt('fault-boundary',cases=cases,fired_pairs=pairs,equal_states=equal,
            whole_private_fault_match=False,hardware_PC_BD_FCSR_not_claimed=True,
            common_access_cuts_only=True,shared_oracle_changed=False)

    def test_04_first_gate_instruction_and_effective_corruption_control(self):
        memory,args=recovery.fixture(0,1)
        pair=[]
        for words in (self.retail,self.raw):
            model=InstructionOracle(words,memory,args)
            model.fault=5
            with self.assertRaises(recovery.stream.AccessFault):model.run()
            self.assertEqual(model.dispatched_word,0x8FAE0050)
            pair.append(model)
        indices=[[i for i,w in enumerate(words) if w==0x8FAE0050] for words in (self.retail,self.raw)]
        self.assertEqual(indices,[[9],[27]])
        corrupted=self.retail.copy()
        corrupted[2]^=4
        models=[]
        for words in (self.retail,corrupted):
            model=InstructionOracle(words,memory,args)
            model.fault=3
            with self.assertRaises(recovery.stream.AccessFault):model.run()
            self.assertEqual(model.accesses,3)
            models.append(model)
        self.assertNotEqual(models[0].memory,models[1].memory)
        self.receipt('opening',first_different_cut=5,first_selector_instruction_word=indices,
            selector_instruction_hex='8FAE0050',effective_wrong_home_control=True,
            no_hardware_PC_or_exception_claim=True)

    def test_05_exact_production_and_data_remain_unchanged(self):
        for name,path in self.paths.items():
            current=(self.root/path).read_bytes()
            self.assertEqual(current,(self.out/('before-'+name)).read_bytes(),name)
            self.assertEqual(hashlib.sha256(current).hexdigest(),self.baseline[name])
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('immutable',protected_inputs=len(self.paths),production_changed=False,
            data=data,source_SHA=self.baseline['source'],ELF_SHA=self.baseline['elf'])


    def test_06_passive_observation_does_not_fire_a_fake_instruction_fault(self):
        memory,args=recovery.fixture(0,1)
        model=InstructionOracle(self.retail,memory,args)
        model.fault=0
        before=(model.memory.copy(),list(model.events),list(model.r),list(model.f),model.accesses)
        observed=state(model)
        self.assertEqual((observed[0],observed[1],observed[2],observed[3],model.accesses),before)
        with self.assertRaises(recovery.stream.AccessFault):model.get(recovery.STACK,4)
        self.assertEqual(model.accesses,0)
        self.assertFalse(hasattr(model,'dispatched_word'))
        self.assertEqual((model.memory,model.events,model.r,model.f,model.accesses),before)
        with self.assertRaises(recovery.stream.AccessFault):model.run()
        self.assertEqual(model.dispatched_word,self.retail[1])
        self.assertEqual(model.dispatched_word>>26,43)
        self.assertEqual(model.accesses,0)
        self.receipt('observation',passive_state_non_gated=True,
            contaminated_get_negative_effective=True,actual_instruction_fault_confirmed=True)


if __name__=='__main__':
    unittest.main()
