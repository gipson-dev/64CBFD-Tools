"""Validate actual ordinal cost gates, not a universal register-exhaustion claim."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_allocator_trace as source


class RectangleAllocatorTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.work=cls.root/source.BUILD/'allocation-ordinal-qualified-5'
        cls.result=source.validate(cls.root,cls.work)
        cls.lines=(cls.work/'debugger.txt').read_text().splitlines()

    def test_01_owned_ordinal_route_costs_and_constraints(self):
        events=self.result['events']
        self.assertEqual(len(events),75)
        self.assertFalse(self.result['installable'])
        self.assertEqual([e['active']['index'] for e in events if e['event']=='unconstrained'],[123,137])
        gates=[e for e in events if e['event']=='unconstrained-evaluate']
        values=lambda key:[struct.unpack('<f',bytes.fromhex(e[key]))[0] for e in gates]
        self.assertEqual(values('gain_bits'),[4.,3.])
        self.assertEqual(values('best_bits'),[0.,14.75])
        self.assertEqual([source.decode(e['active'])['regsleft'] for e in gates],[11,10])
        self.assertEqual([source.decode(r)['assigned'] for r in events[-1]['rows']],[12,0])
        alias=next(e['active'] for e in events if e['active'] and e['active']['index']==436)
        self.assertEqual(source.decode(alias)['expression'],78)

    def test_02_ownership_instruction_order_cost_and_raw_chain_controls(self):
        original=self.result['events']
        mutations=[]
        for key,value in (('pid',1),('inferior',9),('host_pc',0),('table',0)):
            rows=copy.deepcopy(original)
            rows[4][key]=value
            mutations.append(rows)
        rows=copy.deepcopy(original)
        rows[-9],rows[-5]=rows[-5],rows[-9]
        mutations.append(rows)
        for key,value in (('best_bits','00000000'),('gain_bits','00000000'),('chosen_reg',12),('eflags',514)):
            rows=copy.deepcopy(original)
            rows[-2][key]=value
            mutations.append(rows)
        rows=copy.deepcopy(original)
        rows[3]['rows'][0]['units'][0]['node']+=4
        mutations.append(rows)
        rows=copy.deepcopy(original)
        rows[3]['rows'][0]['units'].pop()
        mutations.append(rows)
        rows=copy.deepcopy(original)
        rows[-1]['rows'][0]['live']+=4
        mutations.append(rows)
        for rows in mutations:
            with self.assertRaises(ValueError):
                source.checked_events(self.lines,rows,self.result['constraints'])
        constraints=copy.deepcopy(self.result['constraints'])
        next(r for r in constraints if r['expression']==137)['color']=14
        with self.assertRaisesRegex(ValueError,'constraints'):
            source.checked_events(self.lines,original,constraints)

    def test_03_row_table_ichain_identity_and_unit_corruptions(self):
        original=self.result['events'][3]['rows'][0]
        for key in ('head','table_entry','ichain_prefix'):
            row=copy.deepcopy(original)
            data=bytearray.fromhex(row[key])
            data[0]^=1
            row[key]=data.hex()
            with self.assertRaises(ValueError):
                source.decode(row)
        row=copy.deepcopy(original)
        data=bytearray.fromhex(row['units'][0]['raw'])
        data[8]^=1
        row['units'][0]['raw']=data.hex()
        with self.assertRaisesRegex(ValueError,'ownership'):
            source.checked_units(row)

    def test_04_lifecycle_controls_survive_updated_log_digest(self):
        read=Path.read_text
        receipt=json.loads(read(self.work/'trace.json'))
        for prefix in ('RECT_COLOR_INSTALLED','RECT_COLOR_REMOVED','RECT_COLOR ',
                'RECT_ALLOC_INSTALLED ','TRACE_EXIT inferior=3'):
            bad='\n'.join(line for line in self.lines if not line.startswith(prefix))+'\n'
            forged=dict(receipt,log_sha256=hashlib.sha256(bad.encode()).hexdigest())
            def changed(p,*a,**k):
                if p==self.work/'debugger.txt':
                    return bad
                if p==self.work/'trace.json':
                    return json.dumps(forged)
                return read(p,*a,**k)
            with patch.object(Path,'read_text',changed):
                with self.assertRaises(ValueError):
                    source.validate(self.root,self.work)

    def test_05_known_object_pairs_and_owned_no_repeat_gate(self):
        previous=source.previous
        text,functions,rel=previous.parse_object(self.work/'baseline.o')
        f=functions[previous.source.FUNCTION]
        bad=bytearray(text)
        bad[f['value']+416]^=1
        with patch.object(previous,'parse_object',return_value=(bytes(bad),functions,rel)):
            with self.assertRaisesRegex(ValueError,'diagnostic object'):
                source.validate(self.root,self.work)
        with self.assertRaisesRegex(ValueError,'Preserve'):
            source.trace(self.root,self.root/source.BUILD,'ordinal-qualified')
        for label in ('../escape','a b',''):
            with self.assertRaises(ValueError):
                previous.prepared(self.root,self.root/source.BUILD,label,previous.source.SELECTED)


if __name__=='__main__':
    unittest.main()
