"""Reject misleading image provenance while retaining the full normal compile."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from tools.experiments import game_actor_record_gate_expression_image as source


class RecordGateImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.result=source.capture(cls.root)
        cls.out=cls.root/source.BUILD/'normal';cls.log=(cls.out/'debugger.txt').read_text()
        cls.wire=json.loads((cls.out/'frontend.json').read_text())

    def test_01_fired_image_interning_and_complete_normal_compile(self):
        facts=self.result['facts']
        self.assertEqual(facts['distinct_read_nodes'],2)
        self.assertEqual(facts['raw_image_tag'],0x00940000)
        self.assertEqual(facts['initial_global_loads'],[2,1])
        self.assertEqual(facts['shared_before'],list(source.STAGES))
        self.assertTrue(self.result['full_normal_object_unchanged'])
        self.assertEqual(self.result['lifecycle']['child_and_driver_exit_codes'],[0]*5)
        self.assertTrue(self.result['lifecycle']['final_inferior_null'])
        self.assertFalse(self.result['installable'])
        raw,_=source.target.source.parts(self.out/'trace.o')
        self.assertEqual(hashlib.sha256(raw).hexdigest(),source.target.source.RAW_SHA)

    def replaced(self,rows):
        iterator=iter(rows)
        return '\n'.join(source.PREFIX+json.dumps(next(iterator)) if line.startswith(source.PREFIX) else line for line in self.log.splitlines())+'\n'

    def test_02_effective_scope_association_and_cleanup_controls(self):
        originals=source.events(self.log);controls=[]
        for index,key,value in ((0,'program','other/compiler'),(1,'procedure',761),
                (3,'node',originals[1]['node']),(2,'image',originals[2]['image']+4),
                (4,'node',originals[2]['node']),(5,'stage','copypropagate'),
                (9,'pending',1),(9,'exit_code',1),(9,'probes',5)):
            wrong=copy.deepcopy(originals);wrong[index][key]=value;controls.append(self.replaced(wrong))
        for index,field,offset,value in ((1,'input',0,0x52400000),(1,'input',1,748),
                (1,'input',2,8),(1,'words',5,4),(3,'words',9,4),
                (2,'before',5,4),(2,'after',5,4),(4,'image_words',1,0),(4,'image_words',2,4)):
            wrong=copy.deepcopy(originals);wrong[index][field][offset]=value;controls.append(self.replaced(wrong))
        wrong=copy.deepcopy(originals);wrong[7]['nodes'][1]['words'][5]+=4;controls.append(self.replaced(wrong))
        controls.append(self.log.replace('TRACE_EXIT inferior=3 code=0','TRACE_EXIT inferior=3 code=1'))
        installed=next(line for line in self.log.splitlines() if line.startswith(source.PREFIX))
        controls.append(installed+'\n'+self.log.replace(installed+'\n',''))
        reemit=next(line for line in self.log.splitlines() if line.startswith(source.PREFIX) and '"stage": "reemit"' in line)
        controls.append(self.log.replace(reemit+'\n','').replace('TRACE_EXIT inferior=3 code=0\n',
            'TRACE_EXIT inferior=3 code=0\n'+reemit+'\n'))
        for control in controls:
            with self.assertRaises(ValueError):source.facts(self.root,control,self.wire)
        for line in self.log.splitlines():
            if line.startswith(source.PREFIX):
                with self.assertRaises(ValueError):source.facts(self.root,self.log.replace(line+'\n',''),self.wire)
        with self.assertRaises(ValueError):source.facts(self.root,self.log+source.PREFIX+'[]\n',self.wire)
        (self.out/'negative-controls.json').write_text(json.dumps(dict(effective_controls=len(controls)+len(originals)+1,
            scope_identity_width_association_stage_cleanup=True),indent=2)+'\n')

    def test_03_production_frozen_and_lifecycle_counterexample(self):
        source.target.source.freeze(self.root,self.root/source.target.source.BUILD)
        for inferior in (2,3,4,5,1):
            with self.assertRaises(ValueError):source.target.lifecycle(self.root,
                self.log.replace('TRACE_EXIT inferior=%d code=0'%inferior,'TRACE_EXIT inferior=%d code=1'%inferior))
        self.assertTrue(self.result['no_matching_credit'])


if __name__=='__main__':unittest.main()
