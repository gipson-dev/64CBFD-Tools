"""Proof, original caller, guest/native receipts and actual complete-owner gates."""
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_record_initializer_150169a0_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_record_initializer_150169a0_oracle as guest
from tools.tests import game_record_initializer_150169a0_native as native

class RecordInitializer150169A0MatchTests(unittest.TestCase):
    def test_qualification(self):
        hashes=json.loads((source.OUT/'production-baseline/fingerprints.json').read_text())['inputs']
        digest=lambda:{p:hashlib.sha256((source.ROOT/p).read_bytes()).hexdigest()for p in hashes}
        before=digest();env=dict(os.environ,CBFD_CONSUMER_ROOT=str(source.ROOT),PYTHONDONTWRITEBYTECODE='1')
        for name in('tools.experiments.game_record_initializer_150169a0_match','tools.experiments.game_record_initializer_150169a0_schedule','tools.tests.game_record_initializer_150169a0_proof','tools.tests.game_record_initializer_150169a0_return','tools.tests.game_record_initializer_150169a0_callers','tools.tests.game_record_initializer_150169a0_padder'):
            q=subprocess.run([sys.executable,'-m',name],cwd=source.ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(q.returncode,0,name+'\n'+q.stdout+'\n'+q.stderr);print(name+': '+q.stdout.strip(),flush=True)
        native_rows=native.verify_receipt()
        self.assertEqual([(r['cases'],r['effective_controls'],r['public_bytes'])for r in native_rows],[(639,7,29090)]*3)
        print('Reused native O0/O2/O3 receipts with exact source/profile/artifact fingerprints',flush=True)
        programs=source.draft.programs();normal=payload(source.OUT/'guarded.o',source.NAME)
        from tools.experiments.game_path_heading_turn_roles import bound_blob
        normalized=(bound_blob(*normal,source.draft.symbols()),programs[0][1],source.ENTRY)
        self.assertEqual(normalized,programs[0]);programs=(*programs,normalized)
        count=0;seen=set()
        for c in guest.corpus():
            for i,program in enumerate(programs):
                machine=guest.run_case(program,c)
                if i==0:seen.update(machine.visits)
            count+=1
            if count%128==0:print('three-stream initializer cases',count,flush=True)
        self.assertEqual((count,len(seen)),(686,473))
        self.assertEqual(len(guest.unreachable_proof(*programs[0][:2])),4)
        controls=[]
        for pc,old,new,case in((0x1c,0x24ceffe6,0x24ceffe5,guest.Case(category=26)),(0x248,0xa1c00002,0xa1c70002,guest.Case()),(0x650,0xa72f0006,0xa72f0008,guest.Case(selected=1))):
            words,pool,entry=normalized;changed=words[:];self.assertEqual(changed[pc//4],old);changed[pc//4]=new
            with self.assertRaises(AssertionError):guest.run_case((changed,pool,entry),case)
            controls.append(hex(pc))
        get=lambda n:json.loads((source.OUT/n).read_text())
        r=get('match-report.json');self.assertEqual((r['guards'],r['omitted_words'],r['duplicated_source_words'],r['neighbors'],r['binding_sites'],r['table_entries']),(361,5,1,2,68,79))
        r=get('proof-report.json');self.assertEqual(r['symbolic_paths'],dict(prefix=39,header=2,player=302,cache=2,identity=4,finish=1))
        p=get('projection-report.json');self.assertEqual(p['corruption_controls'],549);self.assertFalse(p['independent_equivalence_proof_pending'])
        self.assertTrue(r['independent_allocation_positive_control']);self.assertEqual(len(r['effective_controls']),7)
        r=get('padder-report.json');self.assertEqual((r['padders'],r['layouts'],r['gnu_links'],r['owner_functions']),(2,4,12,3))
        r=get('return-report.json');self.assertEqual((r['instructions'],r['effective_controls'],r['killer']),(68,2,'0x1502acac'))
        r=get('caller-report.json');self.assertEqual((r['caller_cases'],r['streams']),(48,2));self.assertTrue(r['result_ignored_proven'])
        self.assertEqual(before,digest())
        report=dict(cases=count,streams=3,retail_words_visited=len(seen),guest_controls=controls,inputs_unchanged=len(before),native_mode='reused_exact_fingerprints',complete_caller_unqualified=True,production_state=get('match-report.json')['installed'])
        (source.OUT/'match-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
