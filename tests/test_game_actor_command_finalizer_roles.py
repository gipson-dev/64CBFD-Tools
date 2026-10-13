"""Qualify real temporary slots, integer promotion and full finalizer behavior."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_roles as roles
from tools.tests import test_game_actor_command_finalizer_fitting as previous
from tools.tests import test_game_actor_command_finalizer_recovery as recovery
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class RoleOracle(recovery.FinalizerOracle):
    def __init__(self,words,memory,args,phase=0,seed=0,changes=None):
        super().__init__(words,memory,args,phase,seed)
        self.changes=changes or {}
        self.snapshots=[]
    def hook(self,target):
        assert target==recovery.RANDOM
        sp=self.r[29]
        self.snapshots.append({name:recovery.stream.read(self.memory,sp+slot) for name,slot in roles.SLOTS.items()})
        for name,value in self.changes.get(len(self.calls),()):
            recovery.stream.put(self.memory,sp+roles.SLOTS[name],value)
        super().hook(target)


class GameActorCommandFinalizerRolesTests(unittest.TestCase):
    run_native=previous.GameActorCommandFinalizerFittingTests.run_native
    native_source=previous.GameActorCommandFinalizerFittingTests.native_source
    compare=previous.GameActorCommandFinalizerFittingTests.compare
    test_02_all_types_channels_field_boundaries_and_call_mutations=(
        previous.GameActorCommandFinalizerFittingTests.test_02_all_types_channels_field_boundaries_and_call_mutations)
    test_03_full_word_selectors_and_output_aliases=(
        previous.GameActorCommandFinalizerFittingTests.test_03_full_word_selectors_and_output_aliases)
    test_10_actual_parent_calls_complete_finalizer=(
        previous.GameActorCommandFinalizerFittingTests.test_10_actual_parent_calls_complete_finalizer)

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-roles-test'
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
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.owner_before=(cls.out/'before-source').read_text()
        cls.owner_after=roles.recovered_owner(cls.owner_before)
        cls.meta,cls.words=roles.fitting.compile_candidate(cls.root,cls.out,'roles',roles.SELECTED)
        _,cls.old_words=roles.fitting.compile_candidate(cls.root,cls.out,'old',roles.BASE)
        cls.retail=list(struct.unpack_from('>405I',(cls.root/'conker/conker.us.bin').read_bytes(),recovery.screen.ROM))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_full_extent_no_guards_and_exact_declared_slots(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(405,72,307,0,''))
        self.assertEqual(self.words[:5],self.retail[:5])
        self.assertEqual(self.words[-4:],self.retail[-4:])
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse([r for r in csv.DictReader(stream) if r['function']==recovery.screen.FUNCTION])
        offsets={name:72-(index+1)*4 for index,name in enumerate(roles.ROLE_ORDER[:13])}
        self.assertEqual({name:offsets[name] for name in roles.SLOTS},roles.SLOTS)
        self.assertNotEqual(self.words,self.retail)
        self.receipt('shape',words=405,frame=72,differences=307,matching_credit=0,slots=roles.SLOTS)

    def test_04_live_saves_and_private_provider_mutation_controls(self):
        cases=0
        failures=0
        for kind,phase,seed in itertools.product((0,0x42,0x69,0x70,0x7C,0x87),(0,8),
                (0,1,0x80000000,0xFFFFFFFF)):
            memory,args=recovery.fixture(kind,1)
            pair=[RoleOracle(w,memory,args,phase,seed).run() for w in (self.retail,self.words)]
            self.assertEqual(pair[0].snapshots[0],
                pair[1].snapshots[0])
            self.assertEqual(recovery.public(pair[0].memory),recovery.public(pair[1].memory))
            for index in range(len(pair[0].snapshots)):
                active=('upper','lower','noise','primaryBias') if index==0 else ('reverse','sign')
                self.assertEqual({k:pair[0].snapshots[index][k] for k in active},
                    {k:pair[1].snapshots[index][k] for k in active})
            cases+=1
        scenarios=(
            (1,255,1,((0x1FE,0,1),(0x1FF,1,1),(0x203,0,1)),
                {1:(('upper',100),('lower',90),('noise',2),('primaryBias',13))}),
            (1,2,1,(),{1:(('primaryBias',13),)}),
            (255,2,3,((0x204,255,2),(0x208,1,1),(0x209,60,1)),
                {1:(('sign',-1),('reverse',0))}),
            (255,2,1,((0x204,-255,2),(0x208,-1,1),(0x209,-60,1)),
                {1:(('sign',1),('reverse',0))}))
        for phase,seed,scenario in itertools.product((0,8),(0,1,0x80000000,0xFFFFFFFF),scenarios):
            first,second,pattern,fields,changes=scenario
            memory,args=recovery.fixture(0,pattern,first,second)
            for offset,value,size in fields:
                recovery.stream.put(memory,recovery.ACTOR+offset,value,size)
            pair=[RoleOracle(w,memory,args,phase,seed,changes).run() for w in (self.retail,self.words,self.old_words)]
            self.assertEqual((recovery.public(pair[0].memory),pair[0].r[2],pair[0].calls),
                (recovery.public(pair[1].memory),pair[1].r[2],pair[1].calls))
            if recovery.public(pair[2].memory)!=recovery.public(pair[0].memory):
                failures+=1
            cases+=1
        self.assertGreater(failures,0)
        self.receipt('slots',cases=cases,old_body_control_failures=failures,
            exact_live_role_slots=roles.SLOTS,provider_is_not_retail_PRNG=True,
            whole_private_RAM_and_fault_match=False)

    def test_05_native32_actual_source_and_fresh_effective_negatives(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(roles.SELECTED),profile)[0],0)
        negatives={
            'narrow-first':roles.SELECTED.replace('if (first != limit)','if ((u8)first != limit)'),
            'unsigned-jitter':roles.SELECTED.replace('*(s8 *)(actor + 0x202) * actor[0x1FE]',
                'actor[0x202] * actor[0x1FE]'),
            'wrong-suppression':roles.SELECTED.replace('value == 0x70','value == 0x71'),
            'wrong-sign':roles.SELECTED.replace('sign = -1;','sign = 1;'),
            'signed-modulo':roles.SELECTED.replace('(u32)func_150ADA20() %','func_150ADA20() %')}
        for name,body in negatives.items():
            self.assertNotEqual(body,roles.SELECTED)
            self.assertNotEqual(self.run_native(name,self.native_source(body))[0],0,name)
        self.receipt('native',cases=8192,profiles=['O2','O0'],effective_negatives=len(negatives))

    def test_06_owned_layout_observation_and_allocation_evidence(self):
        results=[]
        for name,body in (('old',roles.BASE),('roles',roles.SELECTED)):
            record=roles.fitting.trace(self.root,self.out,name,body)
            self.assertTrue(record['code_unchanged'])
            events=[e for e in record['events'] if e['event']=='frame-write']
            self.assertEqual([e['frame'] for e in events],[8,24,72])
            self.assertEqual((events[-1]['locals'],events[-1]['saved'],events[-1]['outgoing']),(48,8,16))
            definitions=[r['length'] for r in record['records']['optimizer']
                if r['name']=='def' and r['storage']=='M']
            self.assertEqual(definitions,[44 if name=='old' else 48])
            results.append(dict(name=name,M_definition=definitions[0],
                M_offsets=sorted({r['offset']-0x100000000 if r['offset']>=0x80000000 else r['offset']
                    for r in record['records']['optimizer'] if r['storage']=='M' and r.get('offset') is not None}),
                inputs=record['inputs']))
        self.receipt('allocation',frames_equal=True,objects_unchanged=True,records=results,
            all_six_role_offsets_derived=True)

    def test_07_copied_owner_all_neighbors_pools_and_both_padders(self):
        previous.GameActorCommandFinalizerFittingTests.test_07_owner_neighbors_pools_and_both_padders(self)

    def test_08_literal_image_and_protected_inputs(self):
        current=(self.root/self.paths['elf']).read_bytes()
        source=(self.root/self.paths['source']).read_text()
        expected=bytearray(self.before)
        installed=source==self.owner_after
        if installed:
            offset=elf_slot_offset(self.before,recovery.screen.ENTRY,1620)
            self.assertEqual(offset,elf_slot_offset(current,recovery.screen.ENTRY,1620))
            expected[offset:offset+1620]=struct.pack('>405I',*self.words)
        else:
            self.assertEqual(source,self.owner_before)
        self.assertEqual(current,bytes(expected))
        for name in set(self.paths)-{'source','elf'}:
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes(),name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('linked-audit',installed=installed,matching_credit=0,guard_rows_added=0,
            changed_bytes=sum(a!=b for a,b in zip(self.before,current)),data=data)

    def test_09_actual_role_source_independent_original_rebases(self):
        original_compile=recovery.screen.compile_candidate
        def compile_roles(root,out,name,body=None):
            return original_compile(root,out,name,roles.SELECTED if body is None else body)
        with patch.object(recovery.screen,'compile_candidate',compile_roles):
            recovery.GameActorCommandFinalizerRecoveryTests.test_08_independent_original_links_and_carry_sensitive_rebases(self)

    def test_11_incoming_home_contract_retained(self):
        cases=0
        for phase,offset,kind,pair in itertools.product((0,8),(0,8,10,12,14),
                (0,0x42,0x70,0x7C),((1,2),(255,2),(1,255),(0x80000000,0xFFFFFFFF))):
            first,second=pair
            memory,_=recovery.fixture(kind,1,first,second)
            output=recovery.STACK+phase+offset
            args=(output,recovery.ACTOR,first,second)
            models=[recovery.FinalizerOracle(w,memory,args,phase,0xFFFFFFFF).run() for w in (self.retail,self.words)]
            self.assertEqual((recovery.public(models[0].memory),models[0].r[2],models[0].calls),
                (recovery.public(models[1].memory),models[1].r[2],models[1].calls))
            self.assertEqual(bytes(models[0].memory[output+i] for i in range(16)),
                bytes(models[1].memory[output+i] for i in range(16)))
            cases+=1
        self.receipt('incoming',cases=cases,prior_home_contract_retained=True)


if __name__=='__main__':
    unittest.main()
