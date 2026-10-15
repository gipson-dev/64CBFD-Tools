"""Revalidate actual compiler streams, assigned roles and bounded new controls."""
import copy
import json
from pathlib import Path
import unittest

from tools.experiments import game_capture_request_allocation as study
from tools.experiments import game_capture_request_slot as source
from tools.experiments import game_text_measurer_frontend_trace as capture
from tools.experiments import game_text_measurer_uopt_trace as allocation


class CaptureRequestAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/study.BUILD

    def test_01_captured_streams_real_roles_and_owned_child_completion(self):
        work=self.out/'selected-frontend'
        stored=json.loads((work/'frontend.json').read_text())
        record=capture.validate_capture(self.root,work,(work/'debugger.txt').read_text(),stored['complete'])
        study.verify_owner(self.root,work,source.SELECTED)
        record['standalone_matches_complete_owner_target']=True
        summary=study.phase_summary(record,(work/'baseline.c').read_text())
        self.assertEqual((summary['frontend_cursor_home'],summary['optimizer_cursor_register'],
            summary['optimizer_end_register']),(-4,2,3))
        self.assertEqual((summary['frontend_records'],summary['optimizer_records'],summary['ugen_events']),(489,486,19))
        (work/'frontend.json').write_text(json.dumps(record,indent=2)+'\n')
        (work/'phase-summary.json').write_text(json.dumps(summary,indent=2)+'\n')

    def test_02_mode5_constraints_are_not_intrinsic_cost_or_priority_proof(self):
        work=self.out/'selected-mode5'
        log=(work/'debugger.txt').read_text()
        record=allocation.validate_trace(self.root,work,0,log)
        self.assertTrue(record['code_unchanged'])
        text=(work/'uoptlist').read_text()
        variables=allocation.variable_expressions(text)
        constraints=allocation.allocation_constraints(text)
        self.assertEqual((len(variables),len(constraints)),(8,10))
        cursor=next(x for x in constraints if x['identity']=='88|0')
        end=next(x for x in constraints if x['identity']=='1589|0')
        self.assertEqual((cursor['expression'],cursor['color'],cursor['forbidden']),(0,1,[6]))
        self.assertEqual((end['expression'],end['color'],end['forbidden']),(39,2,[1,6]))
        self.assertIn(39,cursor['interference'])
        self.assertIn(0,end['interference'])
        self.assertEqual(sum(x['storage']=='M' and x['offset']==-4 for x in variables),1)
        study.verify_owner(self.root,work,source.SELECTED)

    def test_03_summary_rejects_missing_unqualified_or_changed_role_evidence(self):
        work=self.out/'selected-frontend'
        record=json.loads((work/'frontend.json').read_text())
        text=(work/'baseline.c').read_text()
        for key in ('code_unchanged','standalone_matches_complete_owner_target'):
            bad=copy.deepcopy(record)
            bad[key]=False
            with self.assertRaises(ValueError):
                study.phase_summary(bad,text)
        for key in ('records','optimizer_records'):
            bad=copy.deepcopy(record)
            bad[key]=[]
            with self.assertRaises(ValueError):
                study.phase_summary(bad,text)
        bad=copy.deepcopy(record)
        bad['complete']['events']=[]
        with self.assertRaises(ValueError):
            study.phase_summary(bad,text)
        with self.assertRaises(ValueError):
            study.phase_summary(record,text.replace('if (request == D_800DD3FC) {','if (0) {'))

    def test_04_new_screens_are_bounded_and_no_direct_improvement_is_claimed(self):
        for filename,count in (('array-end-screens.json',6),('role-screens.json',12)):
            rows=json.loads((self.out/filename).read_text())
            self.assertEqual(len(rows),count)
            self.assertTrue(all(row['diagnostics']=='' and row['differences']>=22 for row in rows))
        self.assertEqual(len(list(study.array_end_variants())),6)
        self.assertEqual(len(list(study.role_variants())),12)


if __name__=='__main__':
    unittest.main()
