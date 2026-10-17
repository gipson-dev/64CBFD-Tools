"""Qualify common-image reuse and reject word-count-only restoration credit."""
import copy
import itertools
import json
from pathlib import Path
import struct
import unittest

from tools.experiments import game_actor_record_gate_expression_reuse as source
from tools.tests import test_game_actor_record_gate_recovery as model
from tools.tests import test_game_actor_burst_consumer_match as faults


class RecordGateReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.result=source.capture(cls.root);cls.obj,cls.control=source.reload_control(cls.root)
        cls.log=(cls.out/'normal/debugger.txt').read_text();cls.wire=json.loads((cls.out/'normal/frontend.json').read_text())
        cls.rom=(cls.root/model.source.BUILD/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>139I',cls.rom,model.source.ROM))

    def test_01_actual_lookup_and_register_emission(self):
        facts=self.result['facts']
        self.assertEqual((facts['distinct_nodes'],facts['lookup_hash']),(2,148))
        self.assertEqual((facts['observed_memory_loads'],facts['observed_register_stores'],facts['observed_register_reads']),(1,1,2))
        self.assertEqual((facts['availability_color'],facts['emitted_hardware_GPR']),(1,2))
        self.assertTrue(self.result['full_normal_object_unchanged'])
        self.assertEqual(self.result['lifecycle']['child_and_driver_exit_codes'],[0]*5)
        self.assertTrue(self.result['lifecycle']['final_inferior_null'])
        self.assertFalse(self.result['installable'])

    def rows(self):return [json.loads(line[len(source.PREFIX):]) for line in self.log.splitlines() if line.startswith(source.PREFIX)]
    def replaced(self,rows):
        iterator=iter(rows)
        return '\n'.join(source.PREFIX+json.dumps(next(iterator)) if line.startswith(source.PREFIX) else line for line in self.log.splitlines())+'\n'

    def test_02_effective_lookup_register_emission_and_lifecycle_controls(self):
        original=self.rows();controls=[]
        for at,key,value in ((0,'program','other/uopt'),(1,'procedure',761),(1,'result',4),
                (2,'node',original[1]['node']),(5,'result',0),(9,'color',2),
                (13,'caller',0x438f4c),(15,'node',original[7]['node']),
                (16,'active',[4]),(16,'pending',1),(16,'probes',3),(16,'exit_code',1)):
            rows=copy.deepcopy(original);rows[at][key]=value;controls.append(self.replaced(rows))
        for at,key,value in ((1,'edx',149),(2,'r8d',4),(5,'edx',4),(9,'r9d',0),(13,'ecx',4)):
            rows=copy.deepcopy(original);rows[at]['args'][key]=value;controls.append(self.replaced(rows))
        for at,word,value in ((4,1,748),(6,3,3),(10,0,0x52800000),(14,3,3)):
            rows=copy.deepcopy(original);rows[at]['record'][word]=value;controls.append(self.replaced(rows))
        for at in (3,8,12):
            rows=copy.deepcopy(original);rows[at]['words'][5]=4;controls.append(self.replaced(rows))
        for line in self.log.splitlines():
            if line.startswith(source.PREFIX):controls.append(self.log.replace(line+'\n',''))
        for wrong in controls:
            with self.assertRaises(ValueError):source.facts(self.root,wrong,self.wire)
        for inferior in (2,3,4,5,1):
            with self.assertRaises(ValueError):source.target.lifecycle(self.root,
                self.log.replace('TRACE_EXIT inferior=%d code=0'%inferior,'TRACE_EXIT inferior=%d code=1'%inferior))
        (self.out/'controls.json').write_text(json.dumps(dict(provenance_controls=len(controls),lifecycle_controls=5),indent=2)+'\n')

    def test_03_reload_control_has_retail_length_but_fails_private_state(self):
        self.assertEqual(len(self.control),139)
        self.assertEqual(self.control[0],0x27bdffc0)
        saves=[(w>>16)&31 for w in self.control[:24] if w>>26==43 and (w>>21)&31==29 and 16<=(w>>16)&31<=23]
        self.assertEqual(saves,[21,20,19,18,17,16])
        self.assertEqual(sum(a!=b for a,b in zip(self.truth,self.control)),134)
        machines=[model.Oracle(w,model.fixture()) for w in (self.truth,self.control)]
        for m in machines:
            m.access_fault=0
            with self.assertRaises(faults.AccessBoundary):m.run()
            self.assertEqual(m.all_accesses,0)
        self.assertNotEqual(model.private(machines[0]),model.private(machines[1]))
        normal=source.target.source.linked(self.root,self.out,self.out/'baseline.o','baseline-linked')
        address=model.source.SYMBOLS['D_800CC5EC']
        counts=[]
        for w in (self.truth,normal,self.control):
            m=model.Oracle(w,model.fixture()).run();counts.append(sum(e[0]=='R' and e[1]==address for e in m.events))
        self.assertEqual(counts,[2,1,2])
        (self.out/'rejected-control.json').write_text(json.dumps(dict(words=139,retail_words=139,frame=64,
            saved_GPRs=6,word_differences=134,opening_reads=counts,private_fault_cut0_rejects=True,
            historical_volatile_declaration_not_claimed=True,installable=False,no_matching_credit=True),indent=2)+'\n')

    def test_04_control_public_behavior_not_full_private_qualification(self):
        cases=0
        for gate,masks,selector,value,present,phase in itertools.product(range(3),range(4),(0,1,100,255),
                (0,1,0xffffffff,0x80000000,0x7fffffff),(False,True),(0,8)):
            memory=model.fixture(gate,masks,selector,value,present)
            want,calls=model.reference(memory,selector,value,present)
            m=model.Oracle(self.control,memory,phase=phase,present=present).run()
            self.assertEqual((model.public(m.memory),m.calls),(model.public(want),calls));cases+=1
        sparse=connected=0
        for delta,masks,mode,phase in itertools.product((-321,-160,-159,-1,0,159,160,321,0x7fffffff,0x80000000),range(4),range(5),(0,8)):
            memory=model.fixture(masks=masks,delta=delta);want,calls=model.reference(memory,delta=delta,mode=mode)
            m=model.Oracle(self.control,memory,phase,delta,True,mode).run()
            self.assertEqual((model.public(m.memory),m.calls),(model.public(want),calls));sparse+=1
        lookup={model.LOOKUP+i*4:w for i,w in enumerate(struct.unpack_from('>28I',self.rom,0x141E5C))}
        setter={model.OVERLAY+i*4:w for i,w in enumerate(struct.unpack_from('>6I',self.rom,0x1C37C8))}
        for value,phase in itertools.product((0,255,256,0xffffffff,0x80000000,0x7fffffff),(0,8)):
            memory=model.fixture(masks=2,value=value);want,calls=model.reference(memory,value=value,actual_offsets=True)
            m=model.Oracle(self.control,memory,phase=phase,connected={**lookup,**setter}).run()
            self.assertEqual((model.public(m.memory),m.calls),(model.public(want),calls));connected+=1
        model.source.freeze(self.root,self.root/model.source.BUILD)
        (self.out/'public-control.json').write_text(json.dumps(dict(core=cases,sparse_mutation=sparse,actual_helpers=connected,
            public_only=True,no_new_native32_or_private_claim=True,production_unchanged=True),indent=2)+'\n')


if __name__=='__main__':unittest.main()
