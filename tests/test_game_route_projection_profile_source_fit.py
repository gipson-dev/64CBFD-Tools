"""Measure the complete-memory boundary of normal-profile projection loops."""
import itertools
import json
from pathlib import Path
import re
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_projection_profile_source_fit as source
from tools.tests import test_game_route_projection_setup as prior
from tools.tests.test_game_route_projection_lifetime_fit import cases
from tools.tests.test_game_route_projection_unrolled_fit import FirstSelectorOracle,CallBoundary


class ProfileSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.body=source.SELECTED
        cls.obj,cls.words,cls.row=source.qualify(cls.root,cls.out)
        rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.truth=list(struct.unpack_from('>321I',rom,source.source.ROM));cls.helpers={}
        for entry,count in prior.HELPERS.items():
            cls.helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,rom,entry-0x14FD2B50)))

    def machine(self,words,memory,args,phase=0):
        return prior.ProjectionOracle(words,memory,args,self.helpers,phase)

    def test_01_complete_memory_and_public_trace_boundary(self):
        count=whole=frame=traces=selector_cases=0;differences={};visits=[set(),set()]
        for memory,args in cases():
            expected,calls,_=prior.reference(memory,args);phase=(count&1)*8
            a,b=[self.machine(w,memory,args,phase).run() for w in (self.words,self.truth)]
            for i,m in enumerate((a,b)):
                self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls),(count,i))
                self.assertEqual(m.f[20:],m.saved_f);visits[i].update(m.visits)
            delta={at for at in a.memory.keys()|b.memory.keys() if a.memory.get(at)!=b.memory.get(at)}
            for at in delta:
                relative=at-(prior.STACK+phase);differences[relative]=differences.get(relative,0)+1
            whole+=not delta
            frame+=not any(prior.STACK+phase-120<=at<prior.STACK+phase for at in delta)
            traces+=a.trace==b.trace
            child=prior.STACK+phase-124
            self.assertEqual([a.memory[x] for x in range(child,child+4)],[b.memory[x] for x in range(child,child+4)])
            if any(c[0]==0x1508907C for c in a.calls):
                self.assertEqual(prior.read(a.memory,child),prior.selector.GLOBAL);selector_cases+=1
            count+=1
        self.assertEqual((count,whole,frame,traces,selector_cases),(575,404,404,274,301))
        self.assertEqual(differences,{-48:171,-47:171,-46:171,-45:171})
        self.assertFalse(any(w>>26==43 and w>>21&31==29 and w&65535==0x48 for w in self.words))
        row=dict(paired_cases=count,whole_memory_equal=whole,parent_frame_equal=frame,
            ordered_public_trace_equal=traces,different_stack_bytes=differences,
            selector_child_S0_equal=575,selector_cases=selector_cases,
            root_visited=[sum(source.source.ENTRY<=pc<source.source.ENTRY+len(w)*4 for pc in v)
                for v,w in zip(visits,(self.words,self.truth))],installable=False,matching_credit=0)
        (self.out/'guest.json').write_text(json.dumps(row,indent=2)+'\n')

    def test_02_null_save_order_and_all_fault_prefixes(self):
        complete=count=equal=0
        for state,flag,phase in itertools.product((0,2,3,255),(0,64),(0,8)):
            memory,args=prior.fixture(state,flag=flag,null=1)
            a,b=[self.machine(w,memory,args,phase).run() for w in (self.words,self.truth)]
            self.assertEqual((a.memory,a.calls,a.f),(b.memory,b.calls,b.f));complete+=1
            self.assertEqual(a.all_accesses,b.all_accesses)
            for cut in range(a.all_accesses):
                stopped=[]
                for words in (self.words,self.truth):
                    m=self.machine(words,memory,args,phase);m.access_fault=cut
                    with self.assertRaises(prior.base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,cut);stopped.append(m)
                self.assertEqual(stopped[0].memory,stopped[1].memory);equal+=1;count+=1
        self.assertEqual((complete,count,equal),(16,240,240))
        (self.out/'null-private.json').write_text(json.dumps(dict(complete_null=complete,
            paired_fired_prefixes=count,all_memory_equal=True),indent=2)+'\n')

    def test_03_all_screens_preserve_normal_owner_and_sampled_public_behavior(self):
        rows=source.audit_screens(self.root,self.out);count=0
        for row in rows:
            obj=self.out/('normal-'+row['name']+'.o')
            data,functions=source.source.neighbor.baseline.model.link_owner(self.root,self.out,obj,source.source.OWNER)
            f=functions[source.source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            self.assertNotEqual(len(words),321)
            for state,position,flag in itertools.product((2,3,0),(0,2,3,7),(0,64)):
                memory,args=prior.fixture(state,position,flag=flag);expected,calls,_=prior.reference(memory,args)
                m=self.machine(words,memory,args,(count&1)*8).run()
                self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls));count+=1
        self.assertEqual(count,384)
        (self.out/'screen-public.json').write_text(json.dumps(dict(screens=16,sampled_public_cases=count,
            unchanged_neighbors_each=72,installable=False),indent=2)+'\n')

    def test_04_all_five_slot_patterns_at_first_real_call(self):
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
        (self.out/'five-slot-prefixes.json').write_text(json.dumps(dict(paired_first_call_prefixes=count,
            slot_patterns=243,full_memory_equal=True,not_full_parent_or_fault_equality=True),indent=2)+'\n')

    def test_05_high_bit_objects_and_private_preference_control(self):
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
        body=source.SELECTED.replace('    volatile u8 preferred;','    u8 preferred;')
        _,negative,row=source.measure(self.root,self.out,'negative-cached-preference',body);self.assertFalse(row['diagnostics'])
        aliases=0
        for flag,phase in itertools.product((0,64),(0,8)):
            memory,_=prior.fixture(3,2,flag=flag);home=prior.STACK+phase-120+0x44;record=home-0x4A
            prior.put(memory,record+0x30,3,1);prior.put(memory,record+0x4B,2,1);args=(record,prior.ACTOR)
            machines=[]
            for words in (self.words,self.truth,negative):
                m=FirstSelectorOracle(words,memory,args,self.helpers,phase)
                with self.assertRaises(CallBoundary):m.run()
                machines.append(m)
            self.assertEqual(machines[0].calls,machines[1].calls)
            self.assertEqual(machines[0].calls[-1][1][-1],2)
            self.assertNotEqual(machines[2].calls,machines[0].calls);aliases+=1
        (self.out/'high-and-preference.json').write_text(json.dumps(dict(high_objects=count,
            private_alias_cases=aliases,cached_control_effective=True,native64_claim=False),indent=2)+'\n')

    def test_06_complete_C_negative_controls(self):
        body=source.SELECTED
        controls={
            'unsigned-coordinates':body.replace('s16 x, y, z;','u16 x, y, z;'),
            'wrong-root-kind':body.replace('node->kind == 5','node->kind == 4'),
            'wrong-class':body.replace('routeClass == 3','routeClass == 2').replace('routeClass != 3','routeClass != 2'),
            'wrong-preferred-bit':body.replace('D_8008FDBC & 0x40','D_8008FDBC & 0x80'),
            'wrong-command':body.replace('), 7, payload);','), 6, payload);'),
        }
        fixtures=[prior.branching_fixture(),prior.fixture(2,0),prior.fixture(3,2),prior.fixture(3,3)]
        fixtures.extend(prior.fixture(3,3,alias=a) for a in range(1,8));witnesses={}
        memory,args=prior.fixture(3,1)
        for axis,value in enumerate((-100,-20,-100)):prior.put(memory,prior.TABLE+16+axis*2,value,2)
        for axis,value in enumerate((-99.,-19.,-99.)):prior.put(memory,prior.ACTOR+0x14+axis*4,prior.base.bits(value))
        expected,calls,_=prior.reference(memory,args)
        for words in (self.words,self.truth):
            m=self.machine(words,memory,args).run()
            self.assertEqual((prior.public(m.memory),m.calls),(prior.public(expected),calls))
        fixtures.append((memory,args))
        for name,b in controls.items():
            self.assertNotEqual(b,body);_,words,row=source.measure(self.root,self.out,'negative-'+name,b)
            self.assertFalse(row['diagnostics'])
            for index,(memory,args) in enumerate(fixtures):
                expected,calls,_=prior.reference(memory,args);m=self.machine(words,memory,args).run()
                if (prior.public(m.memory),m.calls)!=(prior.public(expected),calls):witnesses[name]=index;break
            else:self.fail('Ineffective normal-profile source control: '+name)
        (self.out/'controls.json').write_text(json.dumps(witnesses,indent=2)+'\n')

    def test_07_words_bindings_and_current_inputs_fail_closed(self):
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
                with patch.object(Path,'read_bytes',corrupt),self.assertRaises(ValueError):source.freeze(self.root,self.out)
                checks+=1
        self.assertEqual((len(raw)//4,len(bindings),checks),(334,18,32))
        (self.out/'input-controls.json').write_text(json.dumps(dict(raw_word_corruptions=334,
            missing_bindings=18,input_corruptions=checks,matching_credit=0),indent=2)+'\n')

    def test_08_owned_compiler_capture_and_effective_fact_controls(self):
        row=source.audit_observation(self.root,self.out)
        self.assertEqual(row['roles']['current_node']['color'],15)
        self.assertEqual(row['roles']['previous_node']['color'],2)
        self.assertEqual(row['lifecycle']['child_and_driver_exit_codes'],[0]*5)
        self.assertTrue(row['lifecycle']['final_inferior_null'])
        work=self.out/'normal-mode-5';text=(work/'uoptlist').read_text();controls=0
        for role in row['roles'].values():
            pattern=r'(>>>active<<<\{'+re.escape(role['identity'])+r'\}\s+'+str(role['expression'])+r'\s+)(-?\d+)'
            bad,n=re.subn(pattern,lambda m:m[1]+str(int(m[2])+1),text,count=1);self.assertEqual(n,1)
            with self.assertRaises(ValueError):source.allocation_facts(bad)
            controls+=1
        original_text,original_bytes=Path.read_text,Path.read_bytes
        for path,old,new in ((work/'baseline.c','void func_150891E8','void changed'),
                (work/'debugger.txt','Allocate diagnostic stream buffer','MISSING'),
                (work/'debugger.txt','Suppress diagnostic real-number printer','MISSING'),
                (work/'debugger.txt','TRACE_EXIT inferior=2 code=0','MISSING')):
            self.assertIn(old,original_text(path))
            def changed(actual,*args,**kwargs):
                data=original_text(actual,*args,**kwargs);return data.replace(old,new) if actual==path else data
            with patch.object(Path,'read_text',changed),self.assertRaises(ValueError,msg=old):source.audit_observation(self.root,self.out)
            controls+=1
        def corrupted(actual,*args,**kwargs):
            data=original_bytes(actual,*args,**kwargs);return data+b'\0' if actual==work/'uoptlist' else data
        with patch.object(Path,'read_bytes',corrupted),self.assertRaises(ValueError):source.audit_observation(self.root,self.out)
        controls+=1
        self.assertEqual(controls,14)
        (self.out/'observation-controls.json').write_text(json.dumps(dict(effective_controls=controls,
            fresh_debugger_invocations_in_tests=0),indent=2)+'\n')


if __name__=='__main__':unittest.main()
