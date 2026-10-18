"""Qualify conditional object capture, without claiming full retail matching."""
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_projection_lifetime_fit as source
from tools.tests import test_game_route_projection_setup as prior


def cases():
    for state,position,mode,flag,cursor in itertools.product((2,3,0,128,255),range(8),(0,1,128),(0,64),(0,19)):
        yield prior.fixture(state,position,mode,flag,cursor)
    for alias,position in itertools.product(range(1,8),range(8)):
        yield prior.fixture(3,position,alias=alias)
    for position in range(8):yield prior.fixture(2,position,alias=8,cursor=0)
    for position in range(8):yield prior.fixture(2,position,alias=9,cursor=19)
    for count in (-32768,-1,0,1,2,3,255,256,32767):yield prior.fixture(2,count=count)
    for state in (0,2,3,255):yield prior.fixture(state,null=1)
    yield prior.branching_fixture()
    for mode in (0,1,128):
        memory,args=prior.fixture(2,mode=mode)
        prior.put(memory,prior.TABLE+14,4,1);yield dict(memory),args
        prior.put(memory,prior.TABLE+14,5,1);prior.put(memory,prior.TABLE+15,1,1)
        prior.put(memory,prior.TABLE+2*16+14,5,1);prior.put(memory,prior.TABLE+2*16+15,2,1)
        yield dict(memory),args
        memory,args=prior.fixture(2,mode=mode,count=300);prior.put(memory,prior.TABLE+14,4,1)
        for j,v in enumerate((1,2,255,255,255)):prior.put(memory,prior.TABLE+258*16+9+j,v,1)
        prior.put(memory,prior.TABLE+258*16+14,5,1);prior.put(memory,prior.TABLE+258*16+15,2,1)
        yield memory,args


class LifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.truth=list(struct.unpack_from('>321I',cls.rom,source.source.ROM));cls.helpers={}
        for entry,count in prior.HELPERS.items():
            cls.helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,cls.rom,entry-0x14FD2B50)))

    def machine(self,words,memory,args,phase=0):
        return prior.ProjectionOracle(words,memory,args,self.helpers,phase)

    def test_01_complete_public_cases_and_captured_object_home(self):
        count=0;traces=[0,0];visits=[set(),set()]
        for memory,args in cases():
            expected,calls,trace=prior.reference(memory,args);phase=(count&1)*8
            captured=prior.read(memory,args[1]+0x318)
            for i,words in enumerate((self.words,self.truth)):
                m=self.machine(words,memory,args,phase).run()
                self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls),(count,i))
                self.assertEqual(m.f[20:],m.saved_f)
                if captured:self.assertEqual(prior.read(m.memory,prior.STACK+phase-120+0x3C),captured,(count,i))
                if count<480:traces[i]+=m.trace==trace
                visits[i].update(m.visits)
            count+=1
        self.assertEqual(count,575);self.assertEqual(traces[1],480)
        (self.out/'guest.json').write_text(json.dumps(dict(paired_cases=count,base_trace_equal=traces,
            captured_object_home='SP+0x3C',root_visited=[sum(source.source.ENTRY<=pc<source.source.ENTRY+len(w)*4 for pc in v)
            for v,w in zip(visits,(self.words,self.truth))],installable=False,matching_credit=0),indent=2)+'\n')

    def test_02_high_bit_entry_object_round_trip(self):
        count=0
        for address,state,phase in itertools.product((0x7FFF0000,0x80060000,0xFFFF0000),(0,2,3,255),(0,8)):
            memory,args=prior.fixture(state,3)
            for at in range(prior.OBJECT,prior.OBJECT+0x300):memory[address+at-prior.OBJECT]=memory.pop(at)
            prior.put(memory,prior.ACTOR+0x318,address)
            expected,calls,_=prior.reference(memory,args)
            for words in (self.words,self.truth):
                m=self.machine(words,memory,args,phase).run()
                self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls))
                self.assertEqual(prior.read(m.memory,prior.STACK+phase-120+0x3C),address)
            count+=1
        self.assertEqual(count,24)
        (self.out/'high-object.json').write_text(json.dumps(dict(paired_cases=count,
            guest_32_bit_pointer_integer_round_trip=True,native_64_bit_claim=False),indent=2)+'\n')

    def test_03_null_complete_memory_and_real_fault_prefixes(self):
        count=prefixes=0
        for state,flag,phase in itertools.product((0,2,3,255),(0,64),(0,8)):
            memory,args=prior.fixture(state,flag=flag,null=1)
            a,b=[self.machine(w,memory,args,phase).run() for w in (self.words,self.truth)]
            self.assertEqual((a.memory,a.calls,a.trace,a.f),(b.memory,b.calls,b.trace,b.f))
            self.assertEqual(a.all_accesses,b.all_accesses);self.assertEqual(a.all_accesses,15)
            for cut in range(a.all_accesses):
                models=[]
                for words in (self.words,self.truth):
                    m=self.machine(words,memory,args,phase);m.access_fault=cut
                    with self.assertRaises(prior.base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,cut);models.append(m)
                x,y=models
                self.assertEqual((x.memory,x.calls,x.trace,x.f),(y.memory,y.calls,y.trace,y.f))
                self.assertEqual(x.r[16:24],y.r[16:24]);self.assertEqual(x.r[29:32],y.r[29:32])
                prefixes+=1
            count+=1
        (self.out/'null-private.json').write_text(json.dumps(dict(paired_cases=count,fired_prefixes=prefixes,
            full_memory_equal=True,dead_GPR_and_PC_equality_not_claimed=True),indent=2)+'\n')

    def test_04_old_early_store_and_wrong_home_controls(self):
        oldobj,old,row=source.measure(self.root,self.out,'old-model',source.source.MODEL)
        source.source.checked_model(oldobj);self.assertFalse(row['diagnostics'])
        for phase in (0,8):
            memory,args=prior.fixture(null=1)
            fixed,retail,previous=[self.machine(w,memory,args,phase).run() for w in (self.words,self.truth,old)]
            self.assertEqual(fixed.memory,retail.memory);self.assertNotEqual(previous.memory,retail.memory)
            self.assertEqual(prior.read(previous.memory,prior.STACK+phase-4),0)
        body=dict(source.carrier_forms())['carrier-byte']
        _,wrong,row=source.measure(self.root,self.out,'negative-home',body);self.assertFalse(row['diagnostics'])
        memory,args=prior.fixture(3,3)
        good,bad=[self.machine(w,memory,args).run() for w in (self.words,wrong)]
        self.assertEqual(prior.public(good.memory),prior.public(bad.memory))
        self.assertEqual(prior.read(good.memory,prior.STACK-120+0x3C),prior.OBJECT)
        self.assertNotEqual(prior.read(bad.memory,prior.STACK-120+0x3C),prior.OBJECT)
        (self.out/'private-controls.json').write_text(json.dumps(dict(old_early_store_failures=2,
            wrong_declared_home_effective=True,wrong_home_is_storage_not_public_semantic_control=True),indent=2)+'\n')

    def test_05_effective_complete_C_controls(self):
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
            else:self.fail('Ineffective lifetime semantic control: '+name)
        (self.out/'controls.json').write_text(json.dumps(witnesses,indent=2)+'\n')

    def test_06_strict_words_bindings_and_inputs(self):
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
        self.assertEqual((len(raw)//4,len(bindings),checks),(302,18,30))
        with self.assertRaisesRegex(ValueError,'not installable'):source.source.require_retail_contract(self.words)
        source.source.freeze(self.root,self.out)
        (self.out/'input-audit.json').write_text(json.dumps(dict(raw_word_corruptions=302,
            missing_bindings=18,input_corruptions=checks,matching_credit=0),indent=2)+'\n')


if __name__=='__main__':unittest.main()
