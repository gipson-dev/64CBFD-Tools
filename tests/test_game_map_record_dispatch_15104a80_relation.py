"""Private branch-layout relation; guarded installation remains a separate gate."""
import json,random,unittest
from tools.experiments import game_map_record_dispatch_15104a80_recovery as source
from tools.tests import game_map_record_dispatch_15104a80_relation as proof

class MapRecordRelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared=source.prepare()

    def test_01_complete_CFG_fixed_point_and_effective_controls(self):
        report=proof.qualify(self.prepared)
        self.assertTrue(report['loop_fixed_point_checked'])
        self.assertTrue(report['caller_owned_RA_cell_preserved'])
        self.assertTrue(report['ordered_memory_and_explicit_call_arguments_equal'])
        self.assertEqual(report['unvisited_words'],[[67,84,103],[66,100]])
        self.assertEqual(len(report['effective_instruction_controls']),131)
        self.assertFalse(report['literal_GPR_PC_and_callee_private_RA_stack_identity'])
        self.assertFalse(report['source_installed'])
        (self.prepared['out']/'CFG-relation.json').write_text(json.dumps(report,indent=2)+'\n')

    def test_02_affine_domain_materialization_and_branch_meets(self):
        # Check independently evaluated concrete witnesses are still admitted
        # after abstraction, materialization and intersection of incoming facts.
        rng=random.Random(0x15104A80)
        def evaluate(x,environment):
            if x[0]=='C':return x[1]
            if x[0]=='X':return environment[x]
            if x[0]=='V':return environment[x]
            self.assertEqual(x[0],'add')
            return sum(evaluate(t,environment)for t in x[1:])&0xffffffff
        previous=None
        for case in range(200):
            values=[proof.expr('add',('X',rng.randrange(8)),proof.C(rng.choice((0,1,-1,104,-104,84,-84,20,0x7fffffff,0x80000000)))) if rng.randrange(4) else proof.C(rng.getrandbits(32)) for _ in range(2*proof.N)]
            current=proof.abstract([values[:proof.N],values[proof.N:]])
            for invariant in (current, current if previous is None else (current[0]&previous[0],current[1]&previous[1])):
                reconstructed=proof.materialize(invariant)
                facts=proof.abstract(reconstructed)
                self.assertLessEqual(invariant[0],facts[0]);self.assertLessEqual(invariant[1],facts[1])
                environment={('X',i):rng.getrandbits(32)for i in range(8)}
                environment.update({('V',i):evaluate(x,environment)for i,x in enumerate(values)})
                self.assertEqual([evaluate(x,environment)for x in values],
                                 [evaluate(x,environment)for stream in reconstructed for x in stream])
            previous=current

if __name__=='__main__':unittest.main()
