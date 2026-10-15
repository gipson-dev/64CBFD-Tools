"""Consumer-independent scanner lifetime fits and explicit phase-role tests."""
import unittest

from tools.experiments import game_texture_vertex_span_lifetimes as life
from tools.experiments import game_texture_vertex_span_fit as fit
from tools.experiments import game_texture_vertex_span_ucode as trace


class TextureVertexSpanLifetimeCandidateTests(unittest.TestCase):
    def test_bounded_sources_keep_public_ABI_and_existing_local_declarations(self):
        groups=(life.role_variants,life.endpoint_variants,life.induction_variants,life.copy_variants)
        self.assertEqual([len(list(group())) for group in groups],[8,6,10,3])
        names=[]
        header=fit.HOMES.split(life.CALL)[0]
        for group in groups:
            for label,body in group():
                names.append(label)
                self.assertEqual(body.split(life.CALL)[0],header)
                self.assertEqual(body.count(life.CALL),1)
                self.assertEqual(body.count('*(s8 *)commands'),3)
                self.assertNotIn('volatile',body)
        self.assertEqual(len(names),len(set(names)))
        swapped=life.reuse(fit.HOMES,{'indexCursor':'indexEnd','indexEnd':'indexCursor'})
        self.assertIn('indexEnd = indices, indexCursor = indexEnd + 3',swapped)
        with self.assertRaises(AssertionError):
            life.endpoint('not the complete scanner','end-first')

    def test_phase_roles_can_alias_one_frontend_local_and_one_physical_register(self):
        text='maximum = 0;\nopcode = *(s8 *)commands;\nopcode = 3;\n'
        initializers={'maximum = 0;':'maximum','opcode = *(s8 *)commands;':'opcode','opcode = 3;':'count'}
        def rows(storage,offsets):
            result=[]
            for i,offset in enumerate(offsets):
                result.extend([dict(name='loc',words=[0,i+1]),dict(name='str',storage=storage,offset=offset)])
            return result
        record=dict(code_unchanged=True,records=rows('M',[-28,-16,-16]),
            optimizer_records=rows('R',[8,7,7])+[dict(name='ldc',constants=[0xFFFFFFDF])]*2,
            record_count=6,optimizer_record_count=8,
            complete=dict(events=[dict(type_storage=96,raw44=reg*4) for reg in (8,7)],event_count=2))
        result=trace.phase_summary(record,text,initializers)
        self.assertEqual(result['frontend_offsets'],dict(maximum=-28,opcode=-16,count=-16))
        self.assertEqual(result['optimizer_registers'],dict(maximum=8,opcode=7,count=7))
        self.assertEqual(result['count_materialization_register'],7)
        for invalid in ({},{'maximum = 0;':'maximum'},
                {'opcode = 3;':'count','opcode = *(s8 *)commands;':'count'}):
            with self.assertRaisesRegex(ValueError,'distinct and include count'):
                trace.phase_summary(record,text,invalid)


if __name__=='__main__':
    unittest.main()
