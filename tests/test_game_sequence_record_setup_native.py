"""Complete actual C candidate, typed native32 arena/caller/providers and effective controls."""
import json
from pathlib import Path
import subprocess
import unittest

from tools.experiments import game_sequence_record_setup as source
from tools.experiments import game_sequence_state_reset as reset
from tools.tests import game_sequence_record_setup_native as native
from tools.tests.test_game_projected_packet_draw import native_command


class SequenceRecordSetupNativeTests(unittest.TestCase):
    def test_native32_actual_body_O2_O0_UBSan_and_eight_controls(self):
        root=Path(__file__).resolve().parents[2];out=root/source.BUILD;source.freeze(root,out)
        caller=out/'native-caller.c';caller.write_text(native.program())
        reset_unit=out/'native-reset.c';reset_unit.write_text(native.BODY_HEADER+reset.SELECTED.replace('func_1501D044','actual_reset')+'\n')
        exits={}
        for label,opt,body in [('o2','-O2',source.SELECTED),('o0','-O0',source.SELECTED)]+[
                (label,'-O2',body) for label,body in native.controls(source.SELECTED).items()]:
            if label not in ('o2','o0'):self.assertNotEqual(body,source.SELECTED)
            unit=out/('native-'+label+'.c');unit.write_text(native.BODY_HEADER+body+'\n');exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',str(unit.relative_to(root)),
                str(reset_unit.relative_to(root)),str(caller.relative_to(root)),'-o',str(exe.relative_to(root))],cwd=root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120);exits[label]=ran.returncode
            if label in ('o2','o0'):self.assertEqual(ran.returncode,0,(label,ran.stdout,ran.stderr))
            else:self.assertIn(ran.returncode,(21,22),(label,ran.stdout,ran.stderr))
        (out/'native-qualification.json').write_text(json.dumps(dict(cases_each=sum(1 for _ in native.cases()),exits=exits,
            full_actual_C_body_and_separate_caller_providers=True,actual_restored_reset_C_executed=True,
            all_bank_pointer_numeric_padding_and_canary_bytes=True,all_allocated_arena_bytes_and_gaps=True,
            exact_packets_and_31_lane_boundary_snapshots=True,positive_mutation_counters=True,
            SDK_header8_descriptor8_runtime64_offsets4_38=True,UBSan=True,no_fwrapv=True,
            fixed_allocator_and_other_opaque_provider_contracts_not_gameplay=True),indent=2)+'\n')


if __name__=='__main__':unittest.main()
