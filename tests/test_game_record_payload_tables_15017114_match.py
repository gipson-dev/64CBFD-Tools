"""Complete payload-table qualification, with frozen production inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from unittest.mock import patch
from tools.experiments import game_record_payload_tables_15017114_match as source
from tools.tests import game_record_payload_tables_15017114_oracle as guest
from tools.tests import game_record_payload_tables_15017114_native as native
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

class RecordPayloadTables15017114MatchTests(unittest.TestCase):
    def test_qualification(self):
        record=json.loads((source.OUT/'production-baseline/fingerprints.json').read_text());paths=record['inputs']
        digest=lambda:{p:hashlib.sha256((source.ROOT/p).read_bytes()).hexdigest()for p in paths}
        before=digest();installed=(source.ROOT/source.SOURCE).read_text()==source.draft.proposed((source.OUT/'production-baseline'/source.SOURCE).read_text())
        if not installed:self.assertEqual(before,paths)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CBFD_CONSUMER_ROOT=str(source.ROOT))
        for name in('tools.experiments.game_record_payload_tables_15017114_match','tools.tests.game_record_payload_tables_15017114_proof','tools.tests.game_record_payload_tables_15017114_oracle','tools.tests.game_record_payload_tables_15017114_callers','tools.tests.game_record_payload_tables_15017114_padder'):
            q=subprocess.run([sys.executable,'-m',name],cwd=source.ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(q.returncode,0,name+'\n'+q.stdout+'\n'+q.stderr);print(name+': '+q.stdout.strip(),flush=True)
        try:native.verify_receipt();native_mode='reused_exact_fingerprints'
        except(FileNotFoundError,ValueError):
            q=subprocess.run([sys.executable,'-m','tools.tests.game_record_payload_tables_15017114_native'],cwd=source.ROOT,env=env,capture_output=True,text=True)
            (source.OUT/'native-validation.log').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+'\n'+q.stderr);native_mode='fresh'
        rows=native.verify_receipt();self.assertEqual([(r['cases'],r['effective_controls'],r['public_bytes'])for r in rows],[(380,6,21025)]*3)
        print('Native O0/O2/O3: '+native_mode,flush=True)
        read_bytes=Path.read_bytes;exe=source.OUT/'native-O2'
        with patch.object(Path,'read_bytes',lambda p:read_bytes(p)+b'changed'if p==exe else read_bytes(p)):
            with self.assertRaisesRegex(ValueError,'artifact'):native.verify_receipt()
        with patch.object(native,'command',lambda opt:[]):
            with self.assertRaisesRegex(ValueError,'profile'):native.verify_receipt()
        normal=(bound_blob(*payload(source.OUT/'guarded.o',source.NAME),source.draft.symbols()),source.ENTRY)
        self.assertEqual(normal,source.draft.programs()[0]);count=0
        for c in guest.corpus():guest.run_case(normal,c);count+=1
        self.assertEqual(count,424)
        get=lambda name:json.loads((source.OUT/name).read_text())
        r=get('match-report.json');self.assertEqual((r['words'],r['guards'],r['insertions'],r['omissions'],r['corruption_controls']),(121,10,0,0,142))
        r=get('behavior.json');self.assertEqual((r['cases'],r['streams'],r['retail_words_visited'],len(r['effective_controls'])),(424,2,121,3));self.assertTrue(r['exposed_private_output_alias'])
        r=get('proof-report.json');self.assertEqual((r['symbolic_prefix_paths'],r['dead_input_paths'],r['exact_suffix_words'],len(r['effective_controls'])),(1,2,85,3));self.assertTrue(r['independent_saved_role_positive_control'])
        r=get('caller-report.json');self.assertEqual((r['caller_cases'],r['streams'],r['window_words'],r['effective_controls']),(48,2,4,4));self.assertEqual(r['result_use_proof']['instructions'],30)
        r=get('padder-report.json');self.assertEqual((r['padders'],r['layouts'],r['gnu_links'],r['slot_words'],r['alignment_words']),(2,4,12,123,2))
        self.assertEqual(before,digest())
        report=dict(cases=424,streams=3,retail_words_visited=121,native_mode=native_mode,native_cases_per_profile=380,cache_controls=2,inputs_unchanged=len(paths),production_state=installed)
        (source.OUT/'match-suite.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':unittest.main()
