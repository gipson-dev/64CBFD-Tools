"""Extent/home qualification with explicit remaining saved-role and fault limits."""
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_projection_unrolled_fit as source
from tools.tests import test_game_route_projection_setup as prior
from tools.tests.test_game_route_projection_lifetime_fit import cases


class CallBoundary(Exception):pass


class FirstSelectorOracle(prior.ProjectionOracle):
    def record_call(self,target):
        super().record_call(target)
        if target==0x1508907C:raise CallBoundary
        raise AssertionError('Unexpected earlier projection helper')


class UnrolledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.helpers={}
        cls.truth=list(struct.unpack_from('>321I',cls.rom,source.source.ROM))
        for entry,count in prior.HELPERS.items():
            cls.helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,cls.rom,entry-0x14FD2B50)))

    def machine(self,words,memory,args,phase=0,stop=False):
        return (FirstSelectorOracle if stop else prior.ProjectionOracle)(words,memory,args,self.helpers,phase)

    def test_01_public_complete_parent_frame_and_child_save_boundary(self):
        count=whole_equal=traces=child_different=0;visits=[set(),set()]
        for memory,args in cases():
            expected,calls,reference=prior.reference(memory,args);phase=(count&1)*8
            a,b=[self.machine(w,memory,args,phase).run() for w in (self.words,self.truth)]
            for i,m in enumerate((a,b)):
                self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls),(count,i))
                visits[i].update(m.visits)
            self.assertEqual([a.memory[at] for at in range(prior.STACK+phase-120,prior.STACK+phase)],
                [b.memory[at] for at in range(prior.STACK+phase-120,prior.STACK+phase)])
            different={at for at in set(a.memory)|set(b.memory) if a.memory.get(at)!=b.memory.get(at)}
            child=prior.STACK+phase-124
            self.assertLessEqual(different,set(range(child,child+4)))
            if different:
                calls=[c for c in a.calls if c[0]==0x1508907C];self.assertTrue(calls)
                self.assertEqual(prior.read(a.memory,child),calls[-1][1][0])
                self.assertEqual(prior.read(b.memory,child),prior.selector.GLOBAL)
                child_different+=1
            whole_equal+=not different;traces+=a.trace==b.trace;count+=1
        self.assertEqual((count,whole_equal,child_different,traces),(575,274,301,445))
        (self.out/'guest.json').write_text(json.dumps(dict(paired_cases=count,parent_frame_equal=575,
            whole_memory_equal=whole_equal,sole_child_word_differences=child_different,ordered_trace_equal=traces,
            raw_child_S0='last selector current ID',retail_child_S0='address D_800D2350',
            root_visited=[sum(source.source.ENTRY<=pc<source.source.ENTRY+1284 for pc in v) for v in visits],
            installable=False,matching_credit=0),indent=2)+'\n')

    def test_02_null_complete_memory_and_save_order_fault_rejection(self):
        cases_count=equal=different=0
        for state,flag,phase in itertools.product((0,2,3,255),(0,64),(0,8)):
            memory,args=prior.fixture(state,flag=flag,null=1)
            a,b=[self.machine(w,memory,args,phase).run() for w in (self.words,self.truth)]
            self.assertEqual((a.memory,a.calls,a.f),(b.memory,b.calls,b.f))
            self.assertEqual(a.all_accesses,b.all_accesses);self.assertEqual(a.all_accesses,15)
            for cut in range(15):
                stopped=[]
                for words in (self.words,self.truth):
                    m=self.machine(words,memory,args,phase);m.access_fault=cut
                    with self.assertRaises(prior.base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,cut);stopped.append(m)
                x,y=stopped
                if cut in (2,3,4):self.assertNotEqual(x.memory,y.memory);different+=1
                else:self.assertEqual(x.memory,y.memory);equal+=1
            cases_count+=1
        self.assertEqual((cases_count,equal,different),(16,192,48))
        (self.out/'null-private.json').write_text(json.dumps(dict(paired_cases=cases_count,
            fired_prefixes=240,equal_memory_prefixes=equal,save_order_mismatch_prefixes=different,
            null_final_memory_equal=True,full_fault_equality=False),indent=2)+'\n')

    def test_03_preference_home_alias_and_effective_cached_control(self):
        body=source.SELECTED.replace('    volatile u8 preferred;','    u8 preferred;')
        _,wrong,row=source.measure(self.root,self.out,'negative-cached-preference',body)
        self.assertFalse(row['diagnostics']);count=0
        for flag,phase in itertools.product((0,64),(0,8)):
            memory,_=prior.fixture(3,2,flag=flag);home=prior.STACK+phase-120+0x44
            record=home-0x4A;prior.put(memory,record+0x30,3,1);prior.put(memory,record+0x4B,2,1)
            args=(record,prior.ACTOR);models=[]
            for words in (self.words,self.truth,wrong):
                m=self.machine(words,memory,args,phase,True)
                with self.assertRaises(CallBoundary):m.run()
                models.append(m)
            a,b,c=models
            self.assertEqual(a.calls,b.calls);self.assertEqual(a.calls[-1][1][-1],2)
            self.assertEqual(prior.read(a.memory,home,1),2)
            self.assertNotEqual(c.calls,a.calls);self.assertEqual(c.calls[-1][1][-1],1 if flag else 0)
            count+=1
        (self.out/'preference-alias.json').write_text(json.dumps(dict(paired_call_boundaries=count,
            cached_control_wrong_forwarded_preference=True,stops_before_helper_execution=True,
            forged_private_alias_not_native_C_domain=True),indent=2)+'\n')

    def test_04_all_five_slot_outcomes_at_real_first_call_boundary(self):
        count=0
        for slots,mode,flag in itertools.product(itertools.product((255,1,2),repeat=5),(0,1,128),(0,64)):
            memory,args=prior.fixture(2,mode=mode,flag=flag);phase=(count&1)*8;selected=0
            prior.put(memory,prior.TABLE+2*16+0xF,0,1)
            for j,c in enumerate(slots):
                prior.put(memory,prior.TABLE+9+j,c,1)
                if c!=255 and ((mode==0)==(c==1)):selected=c
            models=[]
            for words in (self.words,self.truth):
                m=self.machine(words,memory,args,phase,True)
                with self.assertRaises(CallBoundary):m.run()
                self.assertEqual(prior.read(m.memory,args[0]+0x4B,1),selected)
                self.assertEqual(m.calls[-1][1],(selected,255,0,1 if flag else 0))
                models.append(m)
            self.assertEqual(models[0].memory,models[1].memory)
            count+=1
        self.assertEqual(count,1458)
        (self.out/'five-slot-prefixes.json').write_text(json.dumps(dict(paired_prefixes=count,
            slot_patterns=243,all_five_slots=True,full_memory_equal_at_first_call=True,
            no_cycle_termination_or_full_parent_claim=True),indent=2)+'\n')

    def test_05_high_bit_objects(self):
        count=0
        for address,state,phase in itertools.product((0x7FFF0000,0x80060000,0xFFFF0000),(0,2,3,255),(0,8)):
            memory,args=prior.fixture(state,3)
            for at in range(prior.OBJECT,prior.OBJECT+0x300):memory[address+at-prior.OBJECT]=memory.pop(at)
            prior.put(memory,prior.ACTOR+0x318,address);expected,calls,_=prior.reference(memory,args)
            for words in (self.words,self.truth):
                m=self.machine(words,memory,args,phase).run()
                self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls))
                self.assertEqual(prior.read(m.memory,prior.STACK+phase-120+0x3C),address)
            count+=1
        (self.out/'high-objects.json').write_text(json.dumps(dict(paired_cases=count,native64_claim=False),indent=2)+'\n')

    def test_06_effective_complete_C_controls(self):
        fixtures=[prior.branching_fixture(),prior.fixture(2,0),prior.fixture(3,2),prior.fixture(3,3)]
        fixtures.extend(prior.fixture(3,3,alias=a) for a in range(1,8))
        fixtures.append(prior.fixture(2,3,alias=9,cursor=19));witnesses={}
        with patch.object(prior.source,'MODEL',source.SELECTED):controls=prior.controls()
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED)
            _,words,row=source.measure(self.root,self.out,'negative-'+name,body);self.assertFalse(row['diagnostics'])
            for index,(memory,args) in enumerate(fixtures):
                expected,_,_=prior.reference(memory,args);m=self.machine(words,memory,args).run()
                if prior.public(m.memory)!=prior.public(expected):witnesses[name]=index;break
            else:self.fail('Ineffective unrolled control: '+name)
        (self.out/'controls.json').write_text(json.dumps(witnesses,indent=2)+'\n')

    def test_07_words_bindings_and_inputs_fail_closed(self):
        raw,bindings=source.checked(self.obj);neighbor=source.source.neighbor
        text,functions,rel=neighbor.parse_object(self.obj);f=functions[source.source.FUNCTION]
        for at in range(f['value'],f['value']+f['size'],4):
            bad=bytearray(text);bad[at]^=1
            with patch.object(neighbor,'parse_object',return_value=(bytes(bad),functions,rel)),self.assertRaises(ValueError):source.checked(self.obj)
        for at in (at for at in rel if f['value']<=at<f['value']+f['size']):
            bad=dict(rel);bad.pop(at)
            with patch.object(neighbor,'parse_object',return_value=(text,functions,bad)),self.assertRaises(ValueError):source.checked(self.obj)
        checks=0
        for index,name in enumerate(source.source.INPUTS):
            for target in (self.root/name,self.out/('before-%02d'%index)):
                def corrupt(path,*args,**kwargs):
                    data=source.source.raw_read(path,*args,**kwargs);return data+b'\0' if path==target else data
                with patch.object(Path,'read_bytes',corrupt),self.assertRaises(ValueError):source.source.freeze(self.root,self.out)
                checks+=1
        self.assertEqual((len(raw)//4,len(bindings),checks),(321,18,30))
        self.assertEqual(self.row['differences'],221);self.assertFalse(self.row['installable'])
        source.source.freeze(self.root,self.out)
        (self.out/'input-audit.json').write_text(json.dumps(dict(raw_word_corruptions=321,
            missing_bindings=18,input_corruptions=checks,matching_credit=0),indent=2)+'\n')


if __name__=='__main__':unittest.main()
