"""Qualify scanner lifetime tradeoffs without replacing the production stub."""
import json
from pathlib import Path
import re
import struct
import unittest

from tools.experiments import game_texture_vertex_span as source
from tools.experiments import game_texture_vertex_span_fit as fit
from tools.experiments import game_texture_vertex_span_lifetimes as life
from tools.experiments import game_texture_vertex_span_ucode as trace
from tools.tests import game_texture_vertex_span_oracle as model
from tools.tests import game_texture_vertex_span_native as native
from tools.tests import test_game_texture_vertex_span as scanner
from tools.tests import test_game_texture_vertex_span_ucode as previous
from tools.pad_generated_object import parse_object


class TextureVertexSpanLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/life.BUILD/'qualification'
        cls.out.mkdir(exist_ok=True)
        cls.forms=dict([*life.role_variants(),*life.endpoint_variants(),
            *life.induction_variants(),*life.copy_variants()])
        cls.selected=('count-as-opcode','index-init-before-decode')
        cls.measured={label:fit.measure(cls.root,cls.out,label,cls.forms[label]) for label in cls.selected}
        cls.captures={label:trace.trace_target(cls.root,cls.out,label+'-capture',cls.forms[label],
            life.COUNT_OPCODE_ROLES if label=='count-as-opcode' else None) for label in cls.selected}
        cls.allocation=trace.trace_allocation(cls.root,cls.out,'count-opcode-allocation',cls.forms['count-as-opcode'])
        cls.rows=list(model.cases())
        cls.words=cls.measured['count-as-opcode'][1]
        cls.retail=list(struct.unpack_from('>339I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM))

    receipt=scanner.TextureVertexSpanTests.receipt

    def native_body(self,body):
        if re.search(r'\bcount\b',body.split(life.CALL,1)[1]):
            return body
        # IDO retains this unused debug home; GCC needs only a local diagnostic annotation.
        declaration='    s32 count;'
        self.assertEqual(body.count(declaration),1)
        adapted=body.replace(declaration,'    s32 count __attribute__((unused));')
        self.assertEqual(adapted.split(life.CALL,1)[1],body.split(life.CALL,1)[1])
        return adapted

    def test_01_partial_retail_roles_are_not_an_overall_improvement(self):
        for label,expected in (('count-as-opcode',(1356,168,274,160)),
                ('index-init-before-decode',(1240,160,288,152))):
            meta,words,_=self.measured[label]
            self.assertEqual(tuple(meta[k] for k in ('bytes','frame','differences','extent_home')),expected)
            self.assertEqual(meta['diagnostics'],'')
            self.assertNotEqual(words,self.retail)
        self.assertEqual(self.words[17],0x00004025)
        self.assertIn(0x24070003,self.words)
        self.assertIn(0x82070000,self.words)
        self.assertIn(0x82020000,self.retail)
        self.receipt('shape',count_opcode_words=339,count_opcode_differences=274,
            maximum_T0_count_A3_recovered_but_opcode_A3_wrong=True,
            induction_words=310,induction_frame=160,induction_differences=288,
            best_seed_unchanged_at_258=True,installed=False,new_C_match=False)

    def test_02_fresh_phase_and_integer_allocation_evidence(self):
        summaries={}
        for label,counts in (('count-as-opcode',(1212,1299,194)),('index-init-before-decode',(1213,1217,167))):
            record=self.captures[label]
            self.assertEqual((record['record_count'],record['optimizer_record_count'],record['complete']['event_count']),counts)
            self.assertTrue(record['code_unchanged'])
            self.assertTrue(record['standalone_matches_complete_owner_target'])
            self.assertFalse(record['installable'])
            summary=json.loads((self.out/(label+'-capture')/'phase-summary.json').read_text())
            self.assertEqual(summary['end_tag_unallocated_literals'],2)
            self.assertEqual(summary['end_tag_allocated_registers'],[])
            summaries[label]=summary
        shared=summaries['count-as-opcode']
        self.assertEqual(shared['frontend_offsets']['opcode'],shared['frontend_offsets']['count'])
        self.assertEqual(shared['frontend_offsets']['opcode'],-16)
        self.assertEqual(shared['optimizer_registers'],dict(stage=31,maximum=8,nested=10,trimFirst=18,opcode=7,count=7))
        self.assertEqual(summaries['index-init-before-decode']['optimizer_registers'],
            dict(stage=31,maximum=10,nested=9,trimFirst=18,count=7))
        allocation=self.allocation
        self.assertEqual((len(allocation['variables']),len(allocation['constraints'])),(31,50))
        values={v['offset']:v for v in allocation['variables'] if v['storage']=='M'}
        constraints={c['expression']:c for c in allocation['constraints']}
        self.assertEqual((values[-28]['expression'],values[-16]['expression']),(8,17))
        self.assertEqual((constraints[8]['color'],constraints[17]['color']),(7,6))
        self.assertIn(17,constraints[8]['interference'])
        self.assertIn(8,constraints[17]['interference'])
        self.assertTrue(allocation['code_unchanged'])
        self.assertIn('numeric timings are not valid',allocation['caveat'])
        self.receipt('phase-roles',summaries=summaries,mode5_variables=31,mode5_constraints=50,
            integer_allocation_tradeoff_proven=True,no_numeric_timing_claim=True)

    def test_03_screen_identity_is_checked_not_inferred_from_difference_count(self):
        out=self.root/life.BUILD
        def signature(label):
            data,functions,relocations=parse_object(out/(label+'.o'))
            f=functions[source.FUNCTION]
            return data[f['value']:f['value']+f['size']],{at-f['value']:value for at,value in relocations.items()
                if f['value']<=at<f['value']+f['size']}
        baseline=signature('homes')
        counts,identical=[],[]
        for group,variants in (('roles',life.role_variants),('endpoints',life.endpoint_variants),
                ('induction',life.induction_variants),('copies',life.copy_variants)):
            path=out/(group+'-screens.json')
            before=path.read_bytes()
            rows=json.loads(before)
            self.assertEqual([r['label'] for r in rows],[label for label,_ in variants()])
            self.assertTrue(all(not r['diagnostics'] and r['differences']>=258 for r in rows))
            counts.append(len(rows))
            identical.append(sum(signature(r['label'])==baseline for r in rows))
            self.assertEqual(path.read_bytes(),before)
        self.assertEqual((counts,identical),([8,6,10,3],[1,2,0,3]))
        expected=[(0x1CC,0x27A20058,0x27A30064),(0x1E0,0x27A30064,0x27A20058),
            (0x22C,0x27A20058,0x27A30070),(0x240,0x27A30070,0x27A20058)]
        for label in ('end-first','end-before-loop','cursor-from-end'):
            current,relocations=signature(label)
            changes=[(i*4,a[0],b[0]) for i,(a,b) in enumerate(zip(struct.iter_unpack('>I',baseline[0]),
                struct.iter_unpack('>I',current))) if a!=b]
            self.assertEqual(changes,expected)
            self.assertEqual(relocations,baseline[1])
        self.receipt('screen-summary',groups=counts,total=27,identical_target_and_relative_relocations=identical,
            three_endpoint_forms_change_four_setup_words=True,no_exact_form=True)

    def test_04_two_full_public_candidates_and_effective_reuse_control(self):
        for label in self.selected:
            words=self.measured[label][1]
            for row in self.rows:
                memory,result,_=model.reference(row['memory'],row['args'],row['mode'])
                for phase in (0,8):
                    instance=model.SpanOracle(words,row['memory'],row['args'],row['mode'],phase).run()
                    self.assertEqual((model.external_memory(instance.memory),instance.r[2]),
                        (model.external_memory(memory),result),(label,row['args']))
            self.assertEqual(native.run(self.out,label,self.rows,self.native_body(self.forms[label])),[0,0])
        body=self.forms['count-as-opcode']
        bad=body.replace('                for (i = 0; i < opcode; i++) {',
            '                opcode = 0;\n                for (i = 0; i < opcode; i++) {')
        self.assertNotEqual(body,bad)
        _,words,_=fit.measure(self.root,self.out,'clobbered-reused-count',bad)
        witness=None
        for row in self.rows:
            memory,result,_=model.reference(row['memory'],row['args'],row['mode'])
            instance=model.SpanOracle(words,row['memory'],row['args'],row['mode']).run()
            if (model.external_memory(instance.memory),instance.r[2])!=(model.external_memory(memory),result):
                witness=row
                break
        self.assertIsNotNone(witness)
        self.assertEqual(native.run(self.out,'clobbered-reused-count',[witness],self.native_body(bad)),[2,2])
        self.receipt('public-semantics',variants=2,guest_cases_per_variant=len(self.rows)*2,
            native_cases_per_variant_per_profile=len(self.rows),returned_negative_statuses=[2,2],
            explicit_endian_warning_and_defined_base_boundary_retained=True,
            native_unused_debug_local_annotated_without_executable_statement_changes=True,
            not_all_27_forms_semantically_qualified=True)

    test_05_private_state_and_fired_prefixes_remain_unmatched=scanner.TextureVertexSpanTests.test_06_private_state_and_fired_prefixes_remain_unmatched
    test_06_production_and_all_archive_fingerprints_stay_fixed=previous.TextureVertexSpanUcodeTests.test_06_all_frozen_production_and_archive_inputs_stay_fixed


if __name__=='__main__':
    unittest.main()
