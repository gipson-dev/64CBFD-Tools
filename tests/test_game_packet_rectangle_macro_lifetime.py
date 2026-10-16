"""Qualify actual UOPT pool blockers while preserving the installed 18-word fit."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_macro_lifetime as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object


class RectangleMacroLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.work=cls.out/'compiler-selected-temp-pool'
        cls.result=source.validate_all(cls.root,cls.out)
        cls.log=(cls.work/'debugger.txt').read_text()
        cls.events=[json.loads(line[10:]) for line in cls.log.splitlines() if line.startswith('RECT_TEMP ')]
        with patch.object(source.compiler,'SIGNATURES',dict(source.compiler.SIGNATURES,**source.selected.TRACE_SIGNATURE)):
            cls.constraints=source.compiler.validate_allocation(cls.root,cls.out/'allocation-selected-qualified-5')['constraints']

    def test_01_all_live_inputs_and_production_body_unchanged(self):
        self.assertEqual({k:hashlib.sha256((self.root/p).read_bytes()).hexdigest()
            for k,p in source.PATHS.items()},source.BASELINE)
        self.assertEqual(len(source.PATHS),100)
        self.assertEqual(source.SELECTED,source.INITIAL)
        before=(self.out/'before-packet_owner').read_text()
        self.assertEqual(source.recovered_owner(before),before)
        self.assertEqual((self.out/'whole-selected-qualified.c').read_text(),before)
        source.selected.checked_object(self.out/'predecessor.o')

    def test_02_actual_streams_M_homes_and_intermediate_pool_are_distinct(self):
        self.assertEqual(self.result['record_counts'],dict(frontend=1362,optimizer=1208))
        self.assertEqual((self.result['events'],self.result['selected_expressions'],self.result['pool_count']),(24,20,6))
        self.assertEqual((self.result['intermediate_extent'],self.result['emitted_M_extent']),(144,136))
        self.assertFalse(self.result['installable'])
        parsed=source.validate_capture(self.root,self.work,True)
        records=parsed['records']
        for stage,extent in (('frontend',120),('optimizer',136)):
            self.assertEqual([r['length'] for r in records[stage] if r['name']=='def' and r['storage']=='M'],[extent])
        actual=[(i,r['name'],r['offset']) for i,r in enumerate(records['optimizer'])
            if r['storage']=='M' and r['name'] in ('lod','str')]
        self.assertEqual(actual,[(252,'str',-136),(255,'lod',-136),(261,'lod',-136),
            (399,'str',-132),(401,'lod',-132),(406,'lod',-132),(418,'str',-136),
            (420,'lod',-136),(462,'lod',-132),(474,'lod',-132),(496,'lod',-132),(524,'lod',-136)])
        old,new=map(source.decoded_pool,self.events[-2:])
        self.assertEqual([r['offset'] for r in old],[-124,-128,-132,-136,-140,-144])
        self.assertEqual([r['pointer'] for r in old],[r['pointer'] for r in new])
        self.assertEqual([r['available'] for r in old],[True]*4+[False]*2)
        self.assertEqual([r['available'] for r in new],[False]+[True]*3+[False]*2)

    def test_03_assignment_ownership_route_and_pool_corruption_controls(self):
        mutations=[]
        for key,value in (('pid',1),('inferior',9),('host_pc',0),('ichain',0),('temporary',0),('index',999)):
            rows=copy.deepcopy(self.events)
            rows[1][key]=value
            mutations.append(rows)
        for key,value in (('head',0),('tail',0),('extent',136),('count',5)):
            rows=copy.deepcopy(self.events)
            rows[-1][key]=value
            mutations.append(rows)
        for at in (0,4,8,12,16):
            rows=copy.deepcopy(self.events)
            raw=bytearray.fromhex(rows[-1]['pool'][0]['raw'])
            raw[at]^=1
            rows[-1]['pool'][0]['raw']=raw.hex()
            mutations.append(rows)
        rows=copy.deepcopy(self.events)
        rows[2],rows[3]=rows[3],rows[2]
        mutations.append(rows)
        for rows in mutations:
            with self.assertRaises(ValueError):
                source.checked_temp_events(rows,self.constraints)
        with self.assertRaises(ValueError):
            source.checked_temp_events(self.events[:-1],self.constraints)

    def test_04_interference_blocks_the_first_two_macro_homes(self):
        self.assertEqual(self.result['blockers'],{347:[[73,235],[107]],354:[[235],[107,349],[347]]})
        for index,blockers in ((347,[73,235]),(354,[107,349])):
            constraints=copy.deepcopy(self.constraints)
            row=next(r for r in constraints if r['expression']==index)
            row['interference']=[i for i in row['interference'] if i not in blockers]
            with self.assertRaisesRegex(ValueError,'blocker'):
                source.checked_temp_events(self.events,constraints)
        constraints=copy.deepcopy(self.constraints)
        next(r for r in constraints if r['expression']==347)['interference'].append(135)
        with self.assertRaisesRegex(ValueError,'reuse contradicts'):
            source.checked_temp_events(self.events,constraints)

    def test_05_missing_reordered_or_wrong_child_gates_are_not_absence(self):
        read=Path.read_text
        lines=self.log.splitlines()
        controls=['\n'.join(line for line in lines if not line.startswith(prefix))+'\n'
            for prefix in ('RECT_TEMP_INSTALLED','RECT_TEMP_REMOVED','RECT_TEMP ','TRACE_EXIT inferior=3')]
        removed=lines.index('RECT_TEMP_REMOVED')
        moved=[line for i,line in enumerate(lines) if i!=removed]
        moved.insert(lines.index('RECT_TEMP_INSTALLED')+1,'RECT_TEMP_REMOVED')
        controls.append('\n'.join(moved)+'\n')
        changed=[]
        for line in lines:
            if line.startswith('RECT_TEMP '):
                event=json.loads(line[10:])
                event['pid']=1
                line='RECT_TEMP '+json.dumps(event)
            changed.append(line)
        controls.append('\n'.join(changed)+'\n')
        for bad in controls:
            with patch.object(Path,'read_text',lambda p,*a,**k:bad if p==self.work/'debugger.txt' else read(p,*a,**k)):
                with self.assertRaises(ValueError):
                    source.validate_temps(self.root,self.work,self.constraints)

    def test_06_all_twenty_nine_complete_owner_screens_revalidated(self):
        before=(self.out/'before-packet_owner').read_text()
        truth=struct.unpack_from('>346I',(self.out/'before-retail_rom').read_bytes(),source.ROM)
        forms=list(source.forms())
        self.assertEqual((len(forms),len(dict(forms)),len({body for _,body in forms})),(29,29,29))
        best=10000
        for label,body in forms:
            with self.subTest(label=label):
                self.assertEqual((self.out/(label+'.c')).read_text(),source.recovered_owner(before,body))
                row=json.loads((self.out/(label+'.json')).read_text())
                text,functions,rel=parse_object(self.out/(label+'.o'))
                f=functions[source.FUNCTION]
                self.assertEqual(hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),row['raw_sha256'])
                bindings={str(a-f['value']):v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
                self.assertEqual(bindings,{a:[tuple(v) for v in values] for a,values in row['relocations'].items()})
                pools={n:d.hex() for n,(_,d) in sections(self.out/(label+'.o')).items()
                    if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
                self.assertEqual(pools,row['pools'])
                linked=sections(self.out/(label+'.elf'))['.text'][1]
                words=struct.unpack_from('>%dI'%(f['size']//4),linked,f['value'])
                difference=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-346)
                self.assertEqual((len(words),(-words[0])&65535,difference,row['diagnostics']),
                    (row['words'],row['frame'],row['differences'],''))
                self.assertEqual(row['different_words'],[[i*4,'0x%08X'%a,'0x%08X'%b]
                    for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
                best=min(best,difference)
        self.assertEqual(best,18)

    def test_07_equal_bodies_and_rejected_frame_or_count_changes(self):
        for label,_ in source.forms():
            row=json.loads((self.out/(label+'.json')).read_text())
            if label.startswith(('flip-mask','low-unsigned-product','declarations-','dimension-unsigned-')):
                source.selected.checked_object(self.out/(label+'.o'))
                self.assertEqual((row['words'],row['frame'],row['differences']),(346,136,18))
            elif label.startswith('low-wide'):
                self.assertEqual(row['frame'],176)
                self.assertGreater(row['words'],346)
            elif label.startswith('phase-corners'):
                self.assertGreater(row['words'],346)
                self.assertGreater(row['differences'],18)
        row=json.loads((self.out/'named-low-control.json').read_text())
        self.assertEqual((row['words'],row['frame'],row['differences']),(346,144,31))

    def test_08_immutable_inputs_scripts_and_existing_trace_no_repeat(self):
        read=Path.read_bytes
        for key in source.PATHS:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)
        read_text=Path.read_text
        path=self.work/'ugen-frame.gdb'
        with patch.object(Path,'read_text',lambda p,*a,**k:read_text(p,*a,**k)+'\n' if p==path else read_text(p,*a,**k)):
            with self.assertRaisesRegex(ValueError,'script'):
                source.validate_capture(self.root,self.work,True)
        with self.assertRaisesRegex(ValueError,'Preserve'):
            source.trace(self.root,self.out,'selected-temp-pool',True)
        with self.assertRaisesRegex(ValueError,'Preserve'):
            source.allocation_trace(self.root,self.out,'selected-qualified')
        manifest=(self.out/'baseline.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Reserved'):
            source.measure(self.root,self.out,'baseline')
        self.assertEqual((self.out/'baseline.json').read_bytes(),manifest)


    def test_09_equal_bad_objects_streams_and_compiler_controls(self):
        compiler=source.compiler
        text,functions,rel=compiler.parse_object(self.work/'baseline.o')
        f=functions[source.FUNCTION]
        for offset in (0,592,1016,1380):
            bad=bytearray(text)
            bad[f['value']+offset]^=1
            with patch.object(compiler,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaisesRegex(ValueError,'diagnostic object'):
                    source.validate_capture(self.root,self.work,True)
        at=next(iter(rel))
        bad=dict(rel)
        bad[at]=[(rel[at][0][0],'wrong')]
        with patch.object(compiler,'parse_object',return_value=(text,functions,bad)):
            with self.assertRaisesRegex(ValueError,'diagnostic object'):
                source.validate_capture(self.root,self.work,True)
        with patch.object(compiler,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):
                source.validate_capture(self.root,self.work,True)
        read=Path.read_bytes
        for name in ('baseline.c','frontend.ucode','optimizer.ucode','ucode-table.json','ucode-types.json'):
            path=self.work/name
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaises(ValueError):
                    source.validate_capture(self.root,self.work,True)
        with patch.object(compiler.frame,'fingerprints',return_value={}):
            with self.assertRaisesRegex(ValueError,'fingerprints'):
                source.validate_capture(self.root,self.work,True)


    def test_10_direct_native_forbidden_vectors_not_just_graph_inference(self):
        work=self.out/'compiler-selected-pool-gates'
        events=[json.loads(line[10:]) for line in (work/'debugger.txt').read_text().splitlines()
            if line.startswith('RECT_TEMP ')]
        result=source.checked_gate_events(events,self.constraints)
        self.assertEqual(result['native_gates'],{347:dict(forbidden=[0,1],selected=2,offset=-132),
            354:dict(forbidden=[0,1,2],selected=3,offset=-136)})
        for key,value in (('pointer',0),('blocks',0),('raw','00'*64)):
            rows=copy.deepcopy(events)
            next(e for e in rows if e.get('index')==347)['forbidden'][key]=value
            with self.assertRaises(ValueError):
                source.checked_gate_events(rows,self.constraints)
        rows=copy.deepcopy(events)
        row=next(e for e in rows if e.get('index')==354)
        raw=bytearray.fromhex(row['forbidden']['raw'])
        raw[4]=1
        row['forbidden']['raw']=raw.hex()
        with self.assertRaisesRegex(ValueError,'snapshot'):
            source.checked_gate_events(rows,self.constraints)


if __name__=='__main__':
    unittest.main()
