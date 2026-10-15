"""Qualify owned compiler captures without installing an unmatched scanner."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_texture_vertex_span as source
from tools.experiments import game_texture_vertex_span_fit as fit
from tools.experiments import game_texture_vertex_span_controlflow as flow
from tools.experiments import game_texture_vertex_span_ucode as trace
from tools.tests import game_texture_vertex_span_oracle as model
from tools.tests import game_texture_vertex_span_native as native
from tools.pad_generated_object import parse_object,ELF_HEADER,SECTION_HEADER,read_c_string


class TextureVertexSpanUcodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/trace.BUILD/'qualification'
        cls.out.mkdir(exist_ok=True)
        cls.forms=dict(flow.variants())
        cls.captures={label:trace.trace_target(cls.root,cls.out,label,cls.forms[label])
            for label in ('homes','for-increment')}
        cls.allocation=trace.trace_allocation(cls.root,cls.out,'homes-allocation',fit.HOMES)
        cls.retail=list(struct.unpack_from('>339I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM))

    def receipt(self,name,**record):
        (self.out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')

    def test_01_fresh_fired_phase_captures_preserve_complete_owner_code(self):
        counts=[]
        for label,expected in (('homes',(1212,1299,258)),('for-increment',(1213,1298,260))):
            record=self.captures[label]
            work=self.out/label
            summary=trace.phase_summary(record,(work/'baseline.c').read_text())
            self.assertEqual((record['record_count'],record['optimizer_record_count'],
                record['complete']['baseline']['differences']),expected)
            self.assertEqual(record['complete']['event_count'],194)
            self.assertTrue(record['code_unchanged'])
            self.assertTrue(record['standalone_matches_complete_owner_target'])
            self.assertFalse(record['installable'])
            self.assertEqual(summary['frontend_offsets'],dict(stage=-24,maximum=-28,nested=-32,trimFirst=-92,count=-4))
            self.assertEqual(summary['optimizer_registers'],dict(stage=31,maximum=7,nested=10,trimFirst=18,count=8))
            self.assertEqual(summary['end_tag_unallocated_literals'],2)
            self.assertEqual(summary['end_tag_allocated_registers'],[])
            counts.append(dict(label=label,frontend=expected[0],optimizer=expected[1],ugen=194))
        self.receipt('phases',captures=counts,optimizer_roles_already_differ=True,
            no_new_C_match_or_production_install=True,normal_and_traced_code_identical=True)

    def test_02_mode5_integer_allocation_constraints_not_numeric_timings(self):
        record=self.allocation
        self.assertTrue(record['code_unchanged'])
        self.assertEqual((record['mode'],len(record['variables']),len(record['constraints'])),(5,32,51))
        self.assertIn('numeric timings are not valid',record['caveat'])
        values={v['offset']:v for v in record['variables'] if v['storage']=='M'}
        constraints={v['expression']:v for v in record['constraints']}
        maximum,count=values[-28],values[-4]
        self.assertEqual((maximum['expression'],count['expression']),(8,127))
        self.assertEqual((constraints[8]['color'],constraints[127]['color']),(6,7))
        self.assertEqual(constraints[8]['forbidden'],[1,2,3,4,5])
        self.assertEqual(constraints[127]['forbidden'],[1,2,3,4,5,6,14])
        self.assertIn(127,constraints[8]['interference'])
        self.assertIn(8,constraints[127]['interference'])
        self.receipt('allocation',variables=32,constraints=51,mutual_interference=True,
            literal_GPR_mapping_from_optimized_STR_not_assumed_color_number=True,numeric_timings_valid=False)

    def test_03_sixty_completed_screen_inputs_and_relative_relocations(self):
        out=self.root/flow.BUILD
        groups=(('screens.json',flow.variants,False),('exit-type-screens.json',flow.exit_type_variants,False),
            ('gpr-screens.json',flow.gpr_variants,False),('loop-screens.json',flow.loop_variants,False),
            ('unrolled-screens.json',flow.unrolled_variants,False),
            ('private-no-unroll-unrolled-screens.json',flow.unrolled_variants,True))
        def signature(obj):
            data,functions,relocations=parse_object(obj)
            f=functions[source.FUNCTION]
            return data[f['value']:f['value']+f['size']],{at-f['value']:v for at,v in relocations.items()
                if f['value']<=at<f['value']+f['size']}
        baseline=signature(out/'homes.o')
        counts,identical=[],[]
        for filename,variants,private in groups:
            original=(out/filename).read_bytes()
            rows=json.loads(original)
            labels=[label+('-no-unroll' if private else '') for label,_ in variants()]
            self.assertEqual([r['label'] for r in rows],labels)
            self.assertTrue(all(not r['diagnostics'] and r['differences']>0 for r in rows))
            count=0
            for row in rows:
                literal,relocations=signature(out/(row['label']+'.o'))
                self.assertEqual(row['bytes'],len(literal))
                self.assertNotEqual(literal,struct.pack('>339I',*self.retail))
                count+=(literal,relocations)==baseline
                if private:
                    self.assertEqual(row['private_profile'],['-O2','-g3','-Wo,-loopunroll,0'])
            counts.append(len(rows))
            identical.append(count)
            self.assertEqual((out/filename).read_bytes(),original)
        self.assertEqual(counts,[16,9,13,16,3,3])
        self.assertEqual(identical,[7,2,10,16,0,0])
        self.receipt('screen-summary',groups=counts,identical_target_and_relative_relocations=identical,
            total=60,no_exact_form=True,private_profile_not_adopted=True)

    def test_04_for_increment_public_semantics_and_bad_occurrence_control(self):
        rows=list(model.cases())
        _,words=trace.compile_target(self.root,self.out,'semantic-for',self.forms['for-increment'])
        for row in rows:
            memory,result,_=model.reference(row['memory'],row['args'],row['mode'])
            for phase in (0,8):
                instance=model.SpanOracle(words,row['memory'],row['args'],row['mode'],phase).run()
                self.assertEqual((model.external_memory(instance.memory),instance.r[2]),
                    (model.external_memory(memory),result))
        self.assertEqual(native.run(self.out,'for-increment',rows,self.forms['for-increment']),[0,0])
        row=model.fixture([(0,0),(0x01000000,model.VERTICES),(0xFD000000,model.TEXTURE),
            model.triangle(5,[1,5,3]),(0xDF000000,0)],occurrence=1)
        memory,result,_=model.reference(row['memory'],row['args'])
        self.assertEqual(result,0)
        retail=model.SpanOracle(self.retail,row['memory'],row['args']).run()
        self.assertEqual((model.external_memory(retail.memory),retail.r[2]),(model.external_memory(memory),result))
        bad=fit.HOMES.replace('occurrence-- < 1','--occurrence < 1')
        self.assertNotEqual(bad,fit.HOMES)
        _,words=trace.compile_target(self.root,self.out,'bad-predecrement',bad)
        instance=model.SpanOracle(words,row['memory'],row['args']).run()
        self.assertNotEqual((model.external_memory(instance.memory),instance.r[2]),
            (model.external_memory(memory),result))
        self.assertEqual(native.run(self.out,'bad-predecrement',[row],bad),[2,2])
        self.receipt('semantics',guest_cases=len(rows)*2,native_cases_per_profile=len(rows),
            for_increment_public_agreement=True,predecrement_effective_returned_mismatch=True,
            not_whole_m2c_output_execution_or_private_schedule_equivalence=True)

    def test_05_effective_capture_object_probe_hash_and_compiler_controls(self):
        capture=trace.capture
        work=self.out/'homes'
        record=self.captures['homes']
        log=(work/'debugger.txt').read_text()
        filenames=('baseline.c','baseline.o','trace.o','frontend.ucode','optimizer.ucode',
            'ucode-table.json','ucode-types.json','frontend.json','trace.json')
        fixed={name:(work/name).read_bytes() for name in filenames}
        controls=[]
        # Validators write failure receipts: mutate only disposable copied inputs.
        with tempfile.TemporaryDirectory(dir=self.out,prefix='capture-controls-') as directory:
            copied=Path(directory)
            for name,payload in fixed.items():
                (copied/name).write_bytes(payload)
            complete=record['complete']
            capture.validate_capture(self.root,copied,log,complete)
            prefixes=(capture.PREFIX,capture.TABLE_PREFIX,capture.OPTIMIZER_PREFIX,capture.trace.PREFIX,
                capture.trace.INSTALLED,capture.trace.CHILD_EXIT,capture.trace.REMOVED,capture.trace.qualified.EXIT_MARKER)
            for prefix in prefixes:
                changed='\n'.join(line for line in log.splitlines() if not line.startswith(prefix))
                with self.subTest(prefix=prefix),self.assertRaises(ValueError):
                    capture.validate_capture(self.root,copied,changed,complete)
                controls.append(prefix)
            for name in ('frontend.ucode','optimizer.ucode','ucode-table.json','ucode-types.json'):
                (copied/name).write_bytes(fixed[name]+b'\n')
                with self.subTest(payload=name),self.assertRaises(ValueError):
                    capture.validate_capture(self.root,copied,log,complete)
                (copied/name).write_bytes(fixed[name])
                controls.append(name)
            for name in ('baseline.o','trace.o'):
                data=bytearray(fixed[name])
                h=ELF_HEADER.unpack_from(data)
                sections=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
                strings=sections[h[13]]
                names=data[strings[4]:strings[4]+strings[5]]
                text=next(s for s in sections if read_c_string(names,s[0])=='.text')
                data[text[4]+1]^=1
                (copied/name).write_bytes(data)
                with self.subTest(object=name),self.assertRaisesRegex(ValueError,'changed text'):
                    capture.validate_capture(self.root,copied,log,complete)
                (copied/name).write_bytes(fixed[name])
                controls.append(name)
            with patch.object(capture,'compiler_fingerprints',return_value={}):
                with self.assertRaisesRegex(ValueError,'fingerprint changed'):
                    capture.validate_capture(self.root,copied,log,complete)
            controls.append('compiler-fingerprint')
            capture.validate_capture(self.root,copied,log,complete)
        self.assertEqual({name:(work/name).read_bytes() for name in filenames},fixed)
        self.receipt('capture-controls',effective=len(controls),controls=controls,
            actual_positive_probe_fired=True,successful_inputs_untouched=True)

    def test_06_all_frozen_production_and_archive_inputs_stay_fixed(self):
        source.freeze(self.root,self.root/source.BUILD)
        for key,path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),source.BASELINE[key],key)
        manifest=self.root/'conker/build/alternative-source-byte-audit-20261014/source-before.json'
        self.assertEqual(hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'd8a07543bcd17a19096e744a66f67a2bf36ba153b51c81e569ae76b95e6581e1')
        rows=json.loads(manifest.read_text(encoding='utf-8-sig'))['files']
        self.assertEqual(len(rows),801)
        archive=self.root/'../Another Source/CBFD-Recompiled/conker'
        for path,digest in rows.items():
            self.assertEqual(hashlib.sha256((archive/path).read_bytes()).hexdigest().upper(),digest,path)
        self.receipt('preservation',production_inputs=len(source.PATHS),archive_inputs=len(rows),
            all_current_and_frozen_hashes_unchanged=True,README_and_match_credit_unchanged=True)


if __name__=='__main__':
    unittest.main()
