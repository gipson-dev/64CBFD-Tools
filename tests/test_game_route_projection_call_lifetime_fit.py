"""Qualify the selected-node spill together with saved roles and complete memory."""
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_projection_call_lifetime_fit as source
from tools.experiments import game_route_projection_prefix_proof as proof
from tools.tests import test_game_route_projection_setup as prior
from tools.tests.test_game_route_projection_lifetime_fit import cases
from tools.tests.test_game_route_projection_unrolled_fit import FirstSelectorOracle,CallBoundary


class CallLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.qualify(cls.root,cls.out)
        source.checked(cls.obj);rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.truth=list(struct.unpack_from('>321I',rom,source.source.ROM));cls.helpers={}
        for entry,count in prior.HELPERS.items():
            cls.helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,rom,entry-0x14FD2B50)))

    def machine(self,words,memory,args,phase=0):
        return prior.ProjectionOracle(words,memory,args,self.helpers,phase)

    def test_01_full_public_and_private_memory(self):
        count=whole=traces=0;different={};visits=[set(),set()]
        for memory,args in cases():
            expected,calls,_=prior.reference(memory,args);phase=(count&1)*8
            a,b=[self.machine(w,memory,args,phase).run() for w in (self.words,self.truth)]
            for i,m in enumerate((a,b)):
                self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls),(count,i))
                self.assertEqual(m.f[20:],m.saved_f);visits[i].update(m.visits)
            delta={at for at in a.memory.keys()|b.memory.keys() if a.memory.get(at)!=b.memory.get(at)}
            for at in delta:
                key=at-(prior.STACK+phase);different[key]=different.get(key,0)+1
            whole+=not delta;traces+=a.trace==b.trace;count+=1
        self.assertEqual((count,whole,traces),(575,575,445));self.assertEqual(different,{})
        (self.out/'guest.json').write_text(json.dumps(dict(paired_cases=count,whole_memory_equal=whole,
            different_stack_bytes=different,ordered_public_trace_equal=traces,
            root_visited=[sum(source.source.ENTRY<=pc<source.source.ENTRY+len(w)*4 for pc in v)
                for v,w in zip(visits,(self.words,self.truth))],installable=False),indent=2)+'\n')

    def test_02_null_and_all_memory_fault_prefixes(self):
        complete=count=0
        for state,flag,phase in itertools.product((0,2,3,255),(0,64),(0,8)):
            memory,args=prior.fixture(state,flag=flag,null=1)
            a,b=[self.machine(w,memory,args,phase).run() for w in (self.words,self.truth)]
            self.assertEqual((a.memory,a.calls,a.f),(b.memory,b.calls,b.f));complete+=1
            self.assertEqual(a.all_accesses,b.all_accesses)
            for cut in range(a.all_accesses):
                machines=[]
                for words in (self.words,self.truth):
                    m=self.machine(words,memory,args,phase);m.access_fault=cut
                    with self.assertRaises(prior.base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,cut);machines.append(m)
                self.assertEqual(machines[0].memory,machines[1].memory);count+=1
        self.assertEqual((complete,count),(16,240))
        (self.out/'null-private.json').write_text(json.dumps(dict(complete_null=complete,
            paired_fired_prefixes=count,all_memory_equal=True),indent=2)+'\n')

    def test_03_all_five_slot_patterns_at_first_call(self):
        count=0
        for slots,mode,flag in itertools.product(itertools.product((255,1,2),repeat=5),(0,1,128),(0,64)):
            memory,args=prior.fixture(2,mode=mode,flag=flag);phase=(count&1)*8;selected=0
            prior.put(memory,prior.TABLE+2*16+0xF,0,1)
            for j,c in enumerate(slots):
                prior.put(memory,prior.TABLE+9+j,c,1)
                if c!=255 and ((mode==0)==(c==1)):selected=c
            machines=[]
            for words in (self.words,self.truth):
                m=FirstSelectorOracle(words,memory,args,self.helpers,phase)
                with self.assertRaises(CallBoundary):m.run()
                self.assertEqual(m.calls[-1][1],(selected,255,0,1 if flag else 0));machines.append(m)
            self.assertEqual(machines[0].memory,machines[1].memory);count+=1
        self.assertEqual(count,1458)
        (self.out/'five-slot-prefixes.json').write_text(json.dumps(dict(paired_prefixes=count,
            full_memory_equal=True),indent=2)+'\n')

    def test_04_prefix_entry_and_inductive_iteration_proof(self):
        result=proof.prove(self.words,self.truth)
        self.assertEqual((result['entry_paths'],result['iteration_paths']),(7,2734))
        self.assertTrue(result['unrelated_scratch_inputs_per_side'])
        addresses=((0x80097FFC,0x80098000,0x800D8004,0x800D7FFC),
            (0x18000,0x17FFC,0x28004,0x27FFC))
        for row in addresses:
            anchors=dict(zip(('flags','count','table','mode'),row));bodies=[]
            for words in (self.words,self.truth):
                rebased=list(words)
                for hi,lo,name in ((11,14,'flags'),(15,19,'count'),(29,30,'table'),(33,34,'mode')):
                    value=anchors[name]
                    rebased[hi]=rebased[hi]&0xFFFF0000|((value+0x8000)>>16&65535)
                    rebased[lo]=rebased[lo]&0xFFFF0000|value&65535
                bodies.append(rebased)
            actual=proof.prove(*bodies,anchors)
            self.assertEqual((actual['entry_paths'],actual['iteration_paths']),(7,2734))
        (self.out/'prefix-proof.json').write_text(json.dumps(dict(**result,independent_data_rebases=2,
            source_prefix_words=164,retail_prefix_words=150,normalization_emitted=False),indent=2)+'\n')

    def test_05_prefix_proof_controls_are_effective(self):
        controls={
            'wrong-record-store':(48,self.words[48]^1),
            'wrong-node-stride':(39,self.words[39]^64),
            'wrong-object-offset':(10,self.words[10]^4),
            'wrong-preference-bit':(17,self.words[17]^64),
            'wrong-kind':(35,self.words[35]^1),
            'wrong-type':(25,self.words[25]^1),
            'wrong-empty-id':(36,self.words[36]^1),
        }
        for name,(index,word) in controls.items():
            bad=list(self.words);bad[index]=word
            with self.assertRaises(ValueError,msg=name):proof.prove(bad,self.truth)
        (self.out/'prefix-proof-controls.json').write_text(json.dumps(dict(effective_controls=list(controls),
            no_byte_matching_credit=True),indent=2)+'\n')

    def test_06_screen_sources_scopes_neighbors_and_public_cases(self):
        rows=source.audit_screens(self.root,self.out);count=0
        for row in rows:
            data,functions=source.source.neighbor.baseline.model.link_owner(self.root,self.out,self.out/(row['name']+'.o'),source.source.OWNER)
            f=functions[source.source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            self.assertNotEqual(len(words),321)
            for state,position,flag in itertools.product((2,3,0),(0,2,3,7),(0,64)):
                memory,args=prior.fixture(state,position,flag=flag);expected,calls,_=prior.reference(memory,args)
                m=self.machine(words,memory,args,(count&1)*8).run()
                self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls));count+=1
        self.assertEqual((len(rows),count),(10,240))
        (self.out/'screen-public.json').write_text(json.dumps(dict(screens=10,sampled_cases=count,
            full_owner_screens=8,isolated_typed_table_screens=2,normal_neighbors_each=72),indent=2)+'\n')

    def test_07_high_objects_preference_home_and_semantic_controls(self):
        count=0
        for address,state,phase in itertools.product((0x7FFF0000,0x80060000,0xFFFF0000),(0,2,3,255),(0,8)):
            memory,args=prior.fixture(state,3)
            for at in range(prior.OBJECT,prior.OBJECT+0x300):memory[address+at-prior.OBJECT]=memory.pop(at)
            prior.put(memory,prior.ACTOR+0x318,address);expected,calls,_=prior.reference(memory,args)
            a,b=[self.machine(w,memory,args,phase).run() for w in (self.words,self.truth)]
            self.assertEqual(a.memory,b.memory)
            self.assertEqual((prior.public(a.memory),a.calls),(prior.public(expected),calls));count+=1
        body=source.SELECTED.replace('    volatile u8 preferred;','    u8 preferred;')
        _,negative,row=source.measure(self.root,self.out,'negative-cached-preference',body);self.assertFalse(row['diagnostics'])
        aliases=0
        for flag,phase in itertools.product((0,64),(0,8)):
            memory,_=prior.fixture(3,2,flag=flag);home=prior.STACK+phase-120+0x44;record=home-0x4A
            prior.put(memory,record+0x30,3,1);prior.put(memory,record+0x4B,2,1);args=(record,prior.ACTOR);machines=[]
            for words in (self.words,self.truth,negative):
                m=FirstSelectorOracle(words,memory,args,self.helpers,phase)
                with self.assertRaises(CallBoundary):m.run()
                machines.append(m)
            self.assertEqual(machines[0].calls,machines[1].calls);self.assertEqual(machines[0].calls[-1][1][-1],2)
            self.assertNotEqual(machines[2].calls,machines[0].calls)
            self.assertEqual(machines[2].calls[-1][1][-1],1 if flag else 0);aliases+=1
        b=source.SELECTED
        controls={
            'unsigned-coordinates':b.replace('s16 x, y, z;','u16 x, y, z;'),
            'wrong-root-kind':b.replace('node->kind == 5','node->kind == 4'),
            'wrong-class':b.replace('routeClass == 3','routeClass == 2').replace('routeClass != 3','routeClass != 2'),
            'wrong-preferred-bit':b.replace('D_8008FDBC & 0x40','D_8008FDBC & 0x80'),
            'wrong-command':b.replace('), 7, payload);','), 6, payload);'),
        }
        memory,args=prior.fixture(3,1)
        for axis,value in enumerate((-100,-20,-100)):prior.put(memory,prior.TABLE+16+axis*2,value,2)
        for axis,value in enumerate((-99.,-19.,-99.)):prior.put(memory,prior.ACTOR+0x14+axis*4,prior.base.bits(value))
        expected,calls,_=prior.reference(memory,args)
        for words in (self.words,self.truth):
            m=self.machine(words,memory,args).run();self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls))
        fixtures=[prior.branching_fixture(),prior.fixture(2,0),prior.fixture(3,2),prior.fixture(3,3),(memory,args)];witnesses={}
        for name,body in controls.items():
            self.assertNotEqual(body,b);_,words,row=source.measure(self.root,self.out,'negative-'+name,body);self.assertFalse(row['diagnostics'])
            for index,(memory,args) in enumerate(fixtures):
                expected,calls,_=prior.reference(memory,args);m=self.machine(words,memory,args).run()
                if (prior.public(m.memory),m.calls)!=(prior.public(expected),calls):witnesses[name]=index;break
            else:self.fail('Ineffective joint-lifetime C control: '+name)
        (self.out/'controls.json').write_text(json.dumps(dict(high_objects=count,private_preference_aliases=aliases,
            cached_preference_wrong=True,compiled_semantic_witnesses=witnesses),indent=2)+'\n')

    def test_08_words_bindings_and_inputs_fail_closed(self):
        raw,bindings=source.checked(self.obj);neighbor=source.source.neighbor
        text,functions,rel=neighbor.parse_object(self.obj);f=functions[source.source.FUNCTION]
        for at in range(f['value'],f['value']+f['size'],4):
            bad=bytearray(text);bad[at]^=1
            with patch.object(neighbor,'parse_object',return_value=(bytes(bad),functions,rel)),self.assertRaises(ValueError):source.checked(self.obj)
        for at in (at for at in rel if f['value']<=at<f['value']+f['size']):
            bad=dict(rel);bad.pop(at)
            with patch.object(neighbor,'parse_object',return_value=(text,functions,bad)),self.assertRaises(ValueError):source.checked(self.obj)
        checks=0
        for index,name in enumerate(source.INPUTS):
            for target in (self.root/name,self.out/('before-%02d'%index)):
                def corrupt(path,*args,**kwargs):
                    data=source.source.raw_read(path,*args,**kwargs);return data+b'\0' if path==target else data
                with patch.object(Path,'read_bytes',corrupt),self.assertRaises(ValueError):source.prior.freeze(self.root,self.out)
                checks+=1
        self.assertEqual((len(raw)//4,len(bindings),checks),(335,18,32))
        (self.out/'input-controls.json').write_text(json.dumps(dict(raw_word_corruptions=335,
            removed_bindings=18,input_corruptions=checks),indent=2)+'\n')

    def test_09_prefix_proof_does_not_qualify_the_float_tail(self):
        at=next(i for i,w in enumerate(self.words) if w>>26==17 and w>>21&31==16 and w&63==3)
        bad=list(self.words);bad[at]=bad[at]&~63|2
        result=proof.prove(bad,self.truth)
        self.assertTrue(result['no_FPU_or_full_function_normalization_claim'])
        memory,args=prior.fixture(3,0);expected,calls,_=prior.reference(memory,args)
        m=self.machine(bad,memory,args).run()
        self.assertNotEqual(prior.public(m.memory),prior.public(expected))
        (self.out/'proof-scope-control.json').write_text(json.dumps(dict(changed_divide_word=at,
            prefix_proof_still_passes=True,full_parent_oracle_rejects=True,full_match_claim=False),indent=2)+'\n')

    def test_10_control_moves_cannot_hide_live_caller_scratch(self):
        for rs in (4,6):
            word=(17<<26)|(rs<<21)|(8<<16)|(31<<11)
            self.assertIn(8,proof.gp_liveins([word,0x03E00008,0])[0])
        for rs in (0,2):
            word=(17<<26)|(rs<<21)|(8<<16)|(31<<11)
            self.assertNotIn(8,proof.gp_liveins([word,0x01008021,0x03E00008,0])[0])
        unknown=(17<<26)|(5<<21)|(8<<16)
        with self.assertRaisesRegex(ValueError,'Unsupported GP liveness COP1'):
            proof.gp_liveins([unknown,0x03E00008,0])
        control=(17<<26)|(6<<21)|(8<<16)|(31<<11)
        bad=list(self.words);bad[165]=control
        self.assertIn(8,proof.gp_liveins(bad)[164])
        with self.assertRaisesRegex(ValueError,'Unproved caller-scratch live-in'):
            proof.prove(bad,self.truth)
        inventories=[sorted({w>>21&31 for w in body if w>>26==17}) for body in (self.words,self.truth)]
        self.assertEqual(inventories,[[4,8,16,20]]*2)
        (self.out/'proof-control-moves.json').write_text(json.dumps(dict(COP1_rs=inventories,
            frozen_bodies_have_no_control_moves=True,control_move_uses_and_defs_checked=4,
            unknown_control_rejected=True,inserted_CTC1_live_scratch_rejected=True),indent=2)+'\n')

    def test_11_exit_cut_is_the_frozen_epilogue(self):
        for side in (0,1):
            bodies=[list(self.words),list(self.truth)];bodies[side][12]^=1
            with self.assertRaisesRegex(ValueError,'Unknown route-prefix cutpoints'):
                proof.prove(*bodies)


if __name__=='__main__':unittest.main()
