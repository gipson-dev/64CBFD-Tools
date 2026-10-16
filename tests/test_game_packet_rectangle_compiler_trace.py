"""Qualify compiler provenance without granting rectangle matching credit."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_middle as source
from tools.experiments import game_packet_rectangle_compiler_trace as trace
from tools.tests.test_game_record_constructor_match import elf_slot_offset


class RectangleCompilerTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)
        cls.frame={n:cls.out/('compiler-qualified-'+n) for n in ('selected','mixed')}
        cls.allocation={n:cls.out/('allocation-final-'+n+'-5') for n in ('selected','mixed')}

    def test_01_all_live_inputs_and_production_body_unchanged(self):
        live={k:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for k,p in source.PATHS.items()}
        self.assertEqual(live,source.BASELINE)
        self.assertEqual(len(live),100)
        data=(self.root/source.PATHS['elf']).read_bytes()
        at=elf_slot_offset(data,source.ENTRY,1384)
        words=struct.unpack_from('>346I',data,at)
        truth=struct.unpack_from('>346I',(self.out/'before-retail_rom').read_bytes(),source.ROM)
        self.assertEqual(sum(a!=b for a,b in zip(words,truth)),71)
        self.assertEqual(words[:104],truth[:104])
        self.assertEqual(words[-91:],truth[-91:])

    def test_02_frame_traces_producers_tables_and_full_objects(self):
        for name,work in self.frame.items():
            parsed=trace.validate(self.root,work)
            self.assertEqual({k:len(v) for k,v in parsed['records'].items()},{'frontend':1355,'optimizer':1205})
            self.assertEqual(trace.checked_signature(work/'baseline.o'),trace.checked_signature(work/'trace.o'))
            self.assertEqual(len(trace.parse_object(work/'trace.o')[1]),1)
            self.assertEqual(parsed['events'][-1]['frame'],136)
            self.assertEqual(parsed['events'][-1]['temporary'],0)
            self.assertEqual(parsed['events'][-1]['pool'],[])

    def test_03_constant_payloads_explain_distinct_loads(self):
        selected=[r for r in trace.constant_rows(self.frame['selected'],'optimizer') if r['dtype']=='R']
        mixed=[r for r in trace.constant_rows(self.frame['mixed'],'optimizer') if r['dtype']=='R']
        self.assertEqual([(r['name'],r['text']) for r in selected],[('rldc','2.0'),('rldc','32.0'),('rldc','1.0')])
        self.assertEqual([(r['name'],r['text']) for r in mixed],
            [('rldc','2.0'),('rldc','32.0'),('ldc','3.2000000000000000e+01'),('ldc','3.2000000000000000e+01'),('rldc','1.0')])
        front=trace.constant_rows(self.frame['mixed'],'frontend')
        self.assertEqual(sum(r['text']=='3.2000000000000000e+01' for r in front),2)

    def test_04_M_homes_already_exist_before_UGEN(self):
        records=trace.validate(self.root,self.frame['selected'])['records']
        lengths=lambda stage:[r['length'] for r in records[stage] if r['name']=='def' and r['storage']=='M']
        self.assertEqual(lengths('frontend'),[116])
        self.assertEqual(lengths('optimizer'),[132])
        self.assertEqual((132+7)&~7,136)
        opt=records['optimizer']
        self.assertEqual([(r['name'],r['storage'],r['offset']) for r in opt[241:246]],
            [('cvt',None,None),('vreg','M',-128),('str','M',-128),('vreg','M',-128),('lod','M',-128)])
        homes={r['offset'] for r in opt if r['storage']=='M' and r['name'] in ('lod','str')}
        self.assertEqual(homes,{-128,-132})

    def test_05_allocation_constraints_separate_the_two_issues(self):
        for name,work in self.allocation.items():
            result=trace.validate_allocation(self.root,work)
            self.assertEqual(len(result['variables']),35)
            self.assertEqual(len(result['constraints']),72 if name=='selected' else 73)
            picked={r['expression']:r for r in result['constraints']}
            self.assertEqual((picked[123]['color'],picked[123]['forbidden']),(12,list(range(1,12))))
            self.assertEqual((picked[137]['color'],picked[137]['forbidden']),(0,list(range(1,13))))
            text=(work/'uoptlist').read_text()
            self.assertRegex(text,r'(?m)^\{\s*\d+\|\d+\}\s+137\s+isop\s+ucvt\{')

    def test_06_frame_flow_and_gate_controls(self):
        work=self.frame['selected']
        path=work/'debugger.txt'
        read=Path.read_text
        original=read(path)
        lines=original.splitlines()
        for prefix in ('RECT_EXIT ','RECT_FLOW ','FRAME_INPUT ','RECT_TABLES ','FRAME_TRACE ','TRACE_EXIT inferior=1'):
            bad='\n'.join(line for line in lines if not line.startswith(prefix))+'\n'
            with patch.object(Path,'read_text',lambda p,*a,**k:bad if p==path else read(p,*a,**k)):
                with self.assertRaises(ValueError):
                    trace.validate(self.root,work)
        flows=[i for i,line in enumerate(lines) if line.startswith('RECT_FLOW ')]
        altered=[line for i,line in enumerate(lines) if i not in flows]
        altered.extend(lines[i] for i in flows)
        bad='\n'.join(altered)+'\n'
        with patch.object(Path,'read_text',lambda p,*a,**k:bad if p==path else read(p,*a,**k)):
            with self.assertRaisesRegex(ValueError,'Misordered'):
                trace.validate(self.root,work)

    def test_07_source_stream_table_and_compiler_controls(self):
        work=self.frame['selected']
        rb=Path.read_bytes
        for name in ('baseline.c','frontend.ucode','optimizer.ucode','ucode-table.json','ucode-types.json'):
            path=work/name
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaises(ValueError):
                    trace.validate(self.root,work)
        with patch.object(trace.frame,'fingerprints',return_value={}):
            with self.assertRaisesRegex(ValueError,'fingerprints'):
                trace.validate(self.root,work)

    def test_08_identical_bad_objects_do_not_pass_equivalence_alone(self):
        work=self.frame['selected']
        text,funcs,rel=trace.parse_object(work/'baseline.o')
        f=funcs[source.FUNCTION]
        for offset in (0,416,1020,1380):
            bad=bytearray(text)
            bad[f['value']+offset]^=1
            with patch.object(trace,'parse_object',return_value=(bytes(bad),funcs,rel)):
                with self.assertRaisesRegex(ValueError,'diagnostic object'):
                    trace.validate(self.root,work)
        at=next(iter(rel))
        bad=dict(rel)
        bad[at]=[(rel[at][0][0],'wrong')]
        with patch.object(trace,'parse_object',return_value=(text,funcs,bad)):
            with self.assertRaisesRegex(ValueError,'diagnostic object'):
                trace.validate(self.root,work)
        with patch.object(trace,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):
                trace.validate(self.root,work)

    def test_09_allocation_gates_independent_of_log_hash(self):
        work=self.allocation['selected']
        read=Path.read_text
        original=read(work/'debugger.txt')
        receipt=json.loads(read(work/'trace.json'))
        for prefix in ('RECT_ALLOC_INSTALLED ','RECT_ALLOC_REMOVED','Allocate diagnostic stream buffer',
                'Suppress diagnostic real-number printer','TRACE_EXIT inferior=1'):
            bad='\n'.join(line for line in original.splitlines() if not line.startswith(prefix))+'\n'
            forged=dict(receipt,log_sha256=hashlib.sha256(bad.encode()).hexdigest())
            def changed(p,*a,**k):
                if p==work/'debugger.txt':
                    return bad
                if p==work/'trace.json':
                    return json.dumps(forged)
                return read(p,*a,**k)
            with patch.object(Path,'read_text',changed):
                with self.assertRaises(ValueError):
                    trace.validate_allocation(self.root,work)

    def test_10_45_screens_revalidated_from_objects_and_linked_words(self):
        before=(self.out/'before-packet_owner').read_text()
        truth=struct.unpack_from('>346I',(self.out/'before-retail_rom').read_bytes(),source.ROM)
        best=10000
        forms=list(source.forms())
        self.assertEqual(len(forms),45)
        for label,body in forms:
            self.assertEqual((self.out/(label+'.c')).read_text(),source.recovered_owner(before,body))
            row=json.loads((self.out/(label+'.json')).read_text())
            text,funcs,_=trace.parse_object(self.out/(label+'.o'))
            f=funcs[source.FUNCTION]
            self.assertEqual(hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),row['raw_sha256'])
            linked=trace.sections(self.out/(label+'.elf'))['.text'][1]
            words=struct.unpack_from('>%dI'%(f['size']//4),linked,f['value'])
            difference=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-346)
            self.assertEqual((len(words),(-words[0])&65535,difference,row['diagnostics']),
                (row['words'],row['frame'],row['differences'],''))
            best=min(best,difference)
        self.assertEqual(best,71)
        self.assertEqual(source.SELECTED,source.INITIAL)

    def test_11_100_frozen_input_controls(self):
        rb=Path.read_bytes
        for key in source.PATHS:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)

    def test_12_owned_paths_and_no_automatic_repeat(self):
        for label in ('../escape','a/b','a b',''):
            with self.assertRaises(ValueError):
                trace.prepared(self.root,self.out,label,source.SELECTED)
        with self.assertRaises(ValueError):
            trace.prepared(self.root,self.root.parent,'outside',source.SELECTED)
        with self.assertRaisesRegex(ValueError,'Preserve'):
            trace.trace(self.root,self.out,'qualified-selected',source.SELECTED)
        for mode in (6,9):
            with self.assertRaises(ValueError):
                trace.trace_allocation(self.root,self.out,'invalid',source.SELECTED,mode)
        with self.assertRaisesRegex(ValueError,'Preserve'):
            trace.trace_allocation(self.root,self.out,'final-selected',source.SELECTED,5)


if __name__=='__main__':
    unittest.main()
