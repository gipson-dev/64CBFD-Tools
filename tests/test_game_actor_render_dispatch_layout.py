"""Qualify complete layout candidates without treating public parity as installation."""
import hashlib
import itertools
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_render_dispatch_layout as layout
from tools.tests import test_game_actor_render_dispatch_recovery as recovery


class PrivateFault(Exception):
    pass


class PrivateFaultOracle(recovery.DispatchOracle):
    def __init__(self,*args,**kwargs):
        self.private_fault,self.private_accesses,self.fault_address=None,0,None
        super().__init__(*args,**kwargs)

    def private_gate(self,address):
        if not self.recording or recovery.public(address):
            return
        if self.private_accesses==self.private_fault:
            self.fault_address=address
            raise PrivateFault(address)
        self.private_accesses+=1

    def get(self,address,size):
        self.private_gate(address)
        return super().get(address,size)

    def put(self,address,value,size):
        self.private_gate(address)
        super().put(address,value,size)


class PointerOracle(recovery.DispatchOracle):
    def __init__(self,*args,**kwargs):
        self.private_arguments=[]
        super().__init__(*args,**kwargs)

    def record_call(self,target):
        super().record_call(target)
        if target in (recovery.S[name] for name in recovery.NAMES):
            name,args,ordinal=self.pending
            if name in ('func_150849CC','func_1502D54C','func_1502D630'):
                self.private_arguments.append((name,ordinal,args[1]))
            elif name=='func_1502CCFC':
                self.private_arguments.append((name,ordinal,args[5]))


class GameActorRenderDispatchLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-render-dispatch-layout-test'
        cls.out.mkdir(exist_ok=True)
        cls.before={name:hashlib.sha256((cls.root/path).read_bytes()).hexdigest()
            for name,path in recovery.PATHS.items()}
        baseline=cls.out/'baseline.json'
        if not baseline.exists():
            baseline.write_text(json.dumps(cls.before,indent=2)+'\n')
        cls.retail=list(struct.unpack_from('>176I',
            (cls.root/'conker/conker.us.bin').read_bytes(),recovery.screen.ROM))
        cls.forms=dict((*layout.candidates(),*layout.lifetime_candidates()))
        cls.compiled={}
        for name,body in cls.forms.items():
            for profile in ('o2g3','o1g3'):
                meta,words=recovery.screen.compile_candidate(cls.root,cls.out,
                    name+'-'+profile,body,profile)
                cls.compiled[name+'-'+profile]=(meta,words)
        (cls.out/'measurements.json').write_text(json.dumps(
            [meta for meta,_ in cls.compiled.values()],indent=2)+'\n')
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_every_complete_form_public_semantics(self):
        cases=0
        plans=[]
        matches=dict.fromkeys(self.compiled,0)
        mismatches={}
        for slot,view,mode,alpha,owner in itertools.product((0,25),
                (-1,0,0x12340002),(0,3,4,5),(-1,0,254,255,256),(0,0x100)):
            memory=recovery.fixture(slot,view,enabled=cases%2,owner=owner,
                owner_view=0,factor=cases%256,limit=cases%3)
            plans.append((memory,slot,view,mode,recovery.Plan(second=alpha)))
            cases+=1
        for mask,view,first,matrix,visible in itertools.product((0,1,128),
                (0,7,32),(0,255),(False,True),(0,1)):
            memory=recovery.fixture(view=view,mask=mask,first_gate=1,matrix=matrix)
            plans.append((memory,0,view,0,recovery.Plan(first=first,visible=visible)))
        for index,(memory,slot,view,mode,plan) in enumerate(plans):
            returned,result,events=recovery.reference(memory,slot,view,mode,0x12345678,plan)
            expected=(returned,{a:v for a,v in result.items() if recovery.public(a)},events)
            original=recovery.DispatchOracle(self.retail,memory,slot,view,mode,
                0x12345678,plan=plan).run()
            self.assertEqual(recovery.projection(original),expected)
            for name,(_,words) in self.compiled.items():
                model=recovery.DispatchOracle(words,memory,slot,view,mode,
                    0x12345678,phase=8 if index%2 else 0,plan=plan).run()
                observed=recovery.projection(model)
                if observed==expected:
                    matches[name]+=1
                else:
                    mismatches.setdefault(name,dict(slot=slot,view=view,mode=mode,
                        return_equal=observed[0]==expected[0],
                        public_memory_equal=observed[1]==expected[1],
                        expected_events=expected[2],observed_events=observed[2]))
                if name.endswith('-o2g3'):
                    self.assertEqual(observed,expected,name)
        self.receipt('public-paths',cases=len(plans),compiled_forms=len(self.compiled),
            candidate_executions=len(plans)*len(self.compiled),
            original_and_independent_reference=True,private_addresses_normalized=True,
            matches=matches,first_public_mismatch=mismatches,
            opaque_callbacks_not_hardware_acceptance=True)

    def test_02_actual_private_arguments_and_fault_counterexamples(self):
        counters=[]
        memory=recovery.fixture(enabled=1)
        original=PointerOracle(self.retail,memory,mode=3).run()
        expected=original.private_arguments
        self.assertEqual([address-recovery.STACK for _,_,address in expected],
            [-4,-0x18,-0x18,-0x18])
        for name in ('overflow-flag-o2g3','ternary-flag-o2g3','scoped-flag-o2g3',
                'nested-render-volatile-actor-o2g3'):
            meta,words=self.compiled[name]
            model=PointerOracle(words,memory,mode=3).run()
            self.assertEqual(recovery.projection(model),recovery.projection(original))
            self.assertNotEqual(model.private_arguments,expected,name)
            faults=[]
            for ordinal in range(8):
                pair=[]
                for body in (self.retail,words):
                    probe=PrivateFaultOracle(body,memory,mode=3)
                    probe.private_fault=ordinal
                    with self.assertRaises(PrivateFault):
                        probe.run()
                    self.assertEqual(probe.private_accesses,ordinal)
                    self.assertIsNotNone(probe.fault_address)
                    pair.append(probe.fault_address)
                faults.append(pair)
            self.assertTrue(any(a!=b for a,b in faults),name)
            counters.append(dict(name=name,words=meta['body_words'],frame=meta['frame'],
                private_arguments=model.private_arguments,retail_private_arguments=expected,
                fault_addresses=faults))
        self.receipt('private-counterexamples',cases=counters,
            verified_fault_executions=64,all_fault_gates_fired=True,
            public_parity_not_private_alias_parity=True,not_installed=True)

    def test_03_native32_closer_nonvolatile_forms(self):
        receipts=[]
        for name in ('overflow-flag','ternary-flag','scoped-flag'):
            probe=recovery.GameActorRenderDispatchRecoveryTests(
                'test_07_actual_native32_complete_C')
            probe.root=self.root
            probe.out=self.out/name
            probe.out.mkdir(exist_ok=True)
            probe.path=Path(self.directory.name)
            with patch.object(recovery.screen,'SELECTED',self.forms[name]):
                probe.test_07_actual_native32_complete_C()
            receipts.append(dict(name=name,**json.loads((probe.out/'native.json').read_text())))
        self.receipt('native-forms',forms=receipts,actual_native32=True,
            opaque_callbacks_not_banked_machine_code=True)

    def test_04_physical_gates_and_production_unchanged(self):
        expected={'overflow-flag-o2g3':(175,0x60),'ternary-flag-o2g3':(177,0x60),
            'scoped-flag-o2g3':(176,0x60),'nested-render-volatile-actor-o2g3':(166,0x58)}
        for name,pair in expected.items():
            meta,words=self.compiled[name]
            self.assertEqual((meta['body_words'],meta['frame']),pair,name)
            self.assertEqual(meta['diagnostics'],'')
            self.assertEqual(meta['pool_bytes'],0)
        self.assertFalse(any(meta['body_words']==176 and meta['frame']==0x58
            for meta,_ in self.compiled.values()))
        after={name:hashlib.sha256((self.root/path).read_bytes()).hexdigest()
            for name,path in recovery.PATHS.items()}
        self.assertEqual(self.before,after)
        self.assertEqual(json.loads((self.out/'baseline.json').read_text()),after)
        self.receipt('production-gate',before=self.before,after=after,
            no_candidate_closes_extent_and_frame=True,no_match_credit=True,not_installed=True)


if __name__=='__main__':
    unittest.main()
