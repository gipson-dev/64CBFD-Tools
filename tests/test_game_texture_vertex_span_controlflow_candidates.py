"""Consumer-independent scanner screen and compiler-phase parser checks."""
import copy
import unittest

from tools.experiments import game_texture_vertex_span_controlflow as flow
from tools.experiments import game_texture_vertex_span_ucode as trace


class TextureVertexSpanControlflowCandidateTests(unittest.TestCase):
    def test_screen_groups_are_bounded_distinct_and_complete(self):
        groups=(flow.variants,flow.exit_type_variants,flow.gpr_variants,flow.loop_variants,flow.unrolled_variants)
        self.assertEqual([len(list(group())) for group in groups],[16,9,13,16,3])
        for group in groups:
            rows=list(group())
            self.assertEqual(len(rows),len({label for label,_ in rows}))
            for _,body in rows:
                self.assertEqual(body.count('s32 func_1510BF60('),1)
                self.assertEqual(body.count('func_1510D0EC(resource, &extent, 3, 0)'),1)
                self.assertEqual(body.count('indices[12]'),1)
                self.assertNotIn('volatile',body)

    def test_phase_parser_accepts_changed_allocations_and_rejects_missing_evidence(self):
        names=('stage','maximum','nested','trimFirst','count')
        lines=['%s = %d;'%(name,3 if name=='count' else 0) for name in names]
        lines+=['maximum = 0;']
        def rows(storage,offsets):
            result=[]
            for i,offset in enumerate(offsets):
                result.extend([dict(name='loc',words=[0,i+1]),
                    dict(name='str',storage=storage,offset=offset)])
            return result
        # Later resets are not the first lexical initialization.
        front=rows('M',[-24,-28,-32,-92,-4,-28])
        optimized=rows('R',[31,7,10,18,8,7])
        optimized.extend([dict(name='ldc',constants=[0xFFFFFFDF],words=[0,0])]*2)
        record=dict(records=front,optimizer_records=optimized,code_unchanged=True,
            optimizer_record_count=len(optimized),record_count=len(front),
            complete=dict(events=[dict(type_storage=3<<5,raw44=r*4) for r in (31,7,10,18,8)],event_count=5))
        text='\n'.join(lines)
        summary=trace.phase_summary(record,text)
        self.assertEqual(summary['optimizer_registers'],dict(zip(names,(31,7,10,18,8))))
        self.assertEqual(summary['end_tag_unallocated_literals'],2)
        changed=copy.deepcopy(record)
        changed['optimizer_records'][3]['offset']=8
        changed['optimizer_records'][9]['offset']=7
        changed['optimizer_records'][-2:]=[dict(name='rldc',constants=[0xFFFFFFDF],words=[0,4])]
        summary=trace.phase_summary(changed,text)
        self.assertEqual(summary['count_materialization_register'],7)
        self.assertEqual(summary['end_tag_allocated_registers'],[4])
        self.assertEqual(summary['end_tag_unallocated_literals'],0)
        for mutation in ('binding','duplicate','constant','event','unqualified'):
            bad=copy.deepcopy(record)
            if mutation=='binding':
                bad['records'].pop(1)
            elif mutation=='duplicate':
                bad['optimizer_records'].insert(2,dict(name='str',storage='R',offset=31))
            elif mutation=='constant':
                bad['optimizer_records']=bad['optimizer_records'][:-2]
            elif mutation=='event':
                bad['complete']['events']=bad['complete']['events'][:-1]
            else:
                bad['code_unchanged']=False
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                trace.phase_summary(bad,text)
        with self.assertRaisesRegex(ValueError,'initialization source line'):
            trace.phase_summary(record,text.replace('count = 3;','count = 6;'))


if __name__=='__main__':
    unittest.main()
