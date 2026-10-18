"""Qualify suffix equivalence without helper stubs or exception-order claims."""
import itertools
import json
from pathlib import Path
import struct
import unittest

from tools.experiments import game_route_projection_joint_extent_fit as screens
from tools.experiments import game_route_projection_suffix_proof as proof
from tools.tests import test_game_route_projection_setup as guest
from tools.tests.test_game_route_projection_lifetime_fit import cases


class SuffixProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/screens.BUILD
        proof.source.prior.freeze(cls.root,cls.out)
        old=cls.root/proof.source.BUILD;obj=old/'qualified.o';proof.source.checked(obj)
        data,functions=proof.source.source.neighbor.baseline.model.link_owner(cls.root,cls.out,obj,proof.source.source.OWNER)
        cls.words=list(struct.unpack_from('>335I',data,functions[proof.source.source.FUNCTION]['value']))
        rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.truth=list(struct.unpack_from('>321I',rom,proof.source.source.ROM))
        cls.helpers={entry:list(struct.unpack_from('>%dI'%count,rom,entry-0x14FD2B50)) for entry,count in proof.HELPERS.items()}

    def paired(self,words=None,helpers=None,strict=False):
        a=proof.prefix.Expressions();bodies=self.words if words is None else words,self.truth
        return [proof.Suffix(body,self.helpers if helpers is None else helpers,a,bool(i),strict).run('common') for i,body in enumerate(bodies)]

    def test_01_composed_prefix_and_inlined_suffix_paths(self):
        result=proof.prove(self.words,self.truth,self.helpers)
        self.assertEqual((result['prefix']['entry_paths'],result['prefix']['iteration_paths']),(7,2734))
        self.assertEqual(tuple(result[k+'_paths'] for k in ('cycle','loop','common')),(1,10242,6832))
        self.assertEqual(result['exit_paths'],1)
        self.assertTrue(result['helpers_inlined']);self.assertFalse(result['normalization_emitted'])
        (self.out/'whole-observational-proof.json').write_text(json.dumps(result,indent=2)+'\n')

    def test_02_float_spill_and_payload_controls_are_effective(self):
        divide=next(i for i,w in enumerate(self.words) if w>>26==17 and w>>21&31==16 and w&63==3)
        payload=next(i for i,w in enumerate(self.words) if w>>26==57 and w&65535==0x7C)
        controls={'wrong-divide':(divide,self.words[divide]&~63|2),
            'wrong-selected-node-home':(257,self.words[257]+4),'wrong-payload-field':(payload,self.words[payload]-4)}
        for name,(at,value) in controls.items():
            words=list(self.words);words[at]=value
            self.assertNotEqual(*self.paired(words),msg=name)
        (self.out/'suffix-controls.json').write_text(json.dumps(dict(effective_controls=list(controls)),indent=2)+'\n')

    def test_03_inlining_observes_the_actual_child_stack(self):
        helpers={entry:list(body) for entry,body in self.helpers.items()}
        self.assertEqual(helpers[0x1508907C][13],0xAFB00004)
        helpers[0x1508907C][13]=0xAFBF0004
        self.assertNotEqual(*self.paired(helpers=helpers))
        (self.out/'helper-return-address-control.json').write_text(json.dumps(dict(
            changed_child_S0_save_to_RA=True,observes_distinct_real_return_addresses=True,
            no_ABI_or_provider_stub=True),indent=2)+'\n')

    def test_04_FP_memory_interleaving_is_an_explicit_exclusion(self):
        self.assertNotEqual(*self.paired(strict=True))
        (self.out/'suffix-exception-scope-control.json').write_text(json.dumps(dict(
            strict_FP_memory_interleaving_differs=True,nontrapping_contract_only=True,
            no_fault_prefix_or_hardware_acceptance=True),indent=2)+'\n')

    def test_05_helper_fingerprints_fail_closed(self):
        changes=0
        for entry,body in self.helpers.items():
            for index in range(len(body)):
                bad={e:list(w) for e,w in self.helpers.items()};bad[entry][index]^=1
                with self.assertRaisesRegex(ValueError,'Unknown suffix helper words'):proof.prove(self.words,self.truth,bad)
                changes+=1
            bad=dict(self.helpers);bad.pop(entry)
            with self.assertRaisesRegex(ValueError,'Unknown suffix helper extents'):proof.prove(self.words,self.truth,bad)
        self.assertEqual(changes,132)
        (self.out/'helper-input-controls.json').write_text(json.dumps(dict(changed_words=132,removed_helpers=2),indent=2)+'\n')

    def test_06_joint_source_screens_keep_owner_scope_but_are_rejected(self):
        rows=screens.audit(self.root,self.out);count=0;helpers={}
        for entry,body in self.helpers.items():helpers.update(zip(range(entry,entry+len(body)*4,4),body))
        for row in rows:
            data,functions=proof.source.source.neighbor.baseline.model.link_owner(self.root,self.out,self.out/(row['name']+'.o'),proof.source.source.OWNER)
            f=functions[proof.source.source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            for state,position,flag in itertools.product((2,3,0),(0,2,3,7),(0,64)):
                memory,args=guest.fixture(state,position,flag=flag);expected,calls,_=guest.reference(memory,args)
                machine=guest.ProjectionOracle(words,memory,args,helpers,(count&1)*8).run()
                self.assertEqual((guest.public(machine.memory),machine.calls),(guest.public(expected),calls));count+=1
        self.assertEqual((len(rows),count),(8,192))
        (self.out/'screen-public.json').write_text(json.dumps(dict(screens=8,sampled_cases=count,
            normal_neighbors_each=72,installable=False),indent=2)+'\n')

    def test_07_original_extent_point_still_fails_private_memory(self):
        data,functions=proof.source.source.neighbor.baseline.model.link_owner(self.root,self.out,self.out/'old-split-common-node.o',proof.source.source.OWNER)
        f=functions[proof.source.source.FUNCTION];words=list(struct.unpack_from('>321I',data,f['value']));helpers={}
        self.assertNotEqual(words[:10],self.truth[:10])
        for entry,body in self.helpers.items():helpers.update(zip(range(entry,entry+len(body)*4,4),body))
        total=equal=traces=0;offsets={}
        for memory,args in cases():
            a,b=[guest.ProjectionOracle(w,memory,args,helpers,(total&1)*8).run() for w in (words,self.truth)]
            expected,calls,_=guest.reference(memory,args)
            self.assertEqual((guest.public(a.memory),a.calls),(guest.public(expected),calls))
            delta={at for at in a.memory.keys()|b.memory.keys() if a.memory.get(at)!=b.memory.get(at)}
            for at in delta:
                relative=at-(guest.STACK+(total&1)*8);offsets[relative]=offsets.get(relative,0)+1
            equal+=not delta;traces+=a.trace==b.trace;total+=1
        self.assertEqual((total,equal,traces),(575,274,445))
        self.assertEqual(offsets,{-124:301,-123:301,-122:301,-121:301})
        (self.out/'original-extent-private-rejection.json').write_text(json.dumps(dict(
            words=321,frame=120,differences=220,paired_cases=total,complete_memories_equal=equal,
            ordered_public_traces_equal=traces,different_stack_bytes=offsets,installable=False),indent=2)+'\n')


if __name__=='__main__':unittest.main()
