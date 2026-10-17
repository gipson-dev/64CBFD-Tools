"""Separate actual C body and SDK-typed native32 caller, with effective controls."""
import json
from pathlib import Path
import subprocess
import unittest

from tools.experiments import game_record_maximum_scan as source
from tools.tests import game_record_maximum_native as native
from tools.tests.test_game_projected_packet_draw import native_command


class RecordMaximumNativeTests(unittest.TestCase):
    def test_native32_O2_O0_UBSan_all_input_bytes_and_eight_controls(self):
        root = Path(__file__).resolve().parents[2]; out = root / source.BUILD; source.freeze(root, out)
        caller = out / 'native-caller.c'; caller.write_text(native.program()); exits = {}
        for label, opt, body in [('o2', '-O2', source.SELECTED), ('o0', '-O0', source.SELECTED)] + [
                (label, '-O2', body) for label, body in native.controls(source.SELECTED).items()]:
            if label not in ('o2', 'o0'): self.assertNotEqual(body, source.SELECTED)
            unit = out / ('native-' + label + '.c'); unit.write_text(native.HEADER + body + '\n'); exe = unit.with_suffix('.elf')
            built = subprocess.run([*native_command(opt), '-fno-strict-aliasing', str(unit.relative_to(root)),
                str(caller.relative_to(root)), '-o', str(exe.relative_to(root))], cwd=root, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=90); exits[label] = ran.returncode
            if label in ('o2', 'o0'): self.assertEqual(ran.returncode, 0, (label, ran.stdout, ran.stderr))
            else: self.assertEqual(ran.returncode, 21, (label, ran.stdout, ran.stderr))
        (out / 'native-qualification.json').write_text(json.dumps(dict(cases_each=sum(1 for _ in native.model.cases()), exits=exits,
            actual_SDK_widths_and_prefix_offsets=True, separate_typed_body_and_caller=True,
            all_input_bytes_and_surrounding_output_canaries=True, UBSan=True, no_fwrapv=True,
            high_u16_counts=True, mixed_endian_overlapping_objects_not_claimed=True), indent=2) + '\n')


if __name__ == '__main__': unittest.main()
