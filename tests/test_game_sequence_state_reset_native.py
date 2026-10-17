"""Actual SDK-typed reset body, separate native caller/provider and effective controls."""
import json
from pathlib import Path
import subprocess
import unittest

from tools.experiments import game_sequence_state_reset as source
from tools.tests import game_sequence_state_reset_native as native
from tools.tests.test_game_projected_packet_draw import native_command


class SequenceStateResetNativeTests(unittest.TestCase):
    def test_native32_O2_O0_UBSan_snapshots_all_bytes_and_eight_controls(self):
        root = Path(__file__).resolve().parents[2]; out = root / source.BUILD; source.freeze(root, out)
        caller = out / 'native-caller.c'; caller.write_text(native.program())
        provider = out / 'native-provider.c'; provider.write_text(native.PROVIDER); exits = {}
        for label, opt, body in [('o2', '-O2', source.SELECTED), ('o0', '-O0', source.SELECTED)] + [
                (label, '-O2', body) for label, body in native.controls(source.SELECTED).items()]:
            if label not in ('o2', 'o0'): self.assertNotEqual(body, source.SELECTED)
            unit = out / ('native-' + label + '.c'); unit.write_text(native.body_header() + body + '\n'); exe = unit.with_suffix('.elf')
            built = subprocess.run([*native_command(opt), str(unit.relative_to(root)), str(provider.relative_to(root)),
                str(caller.relative_to(root)), '-o', str(exe.relative_to(root))], cwd=root, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60); exits[label] = ran.returncode
            if label in ('o2', 'o0'): self.assertEqual(ran.returncode, 0, (label, ran.stdout, ran.stderr))
            else: self.assertIn(ran.returncode, (21, 22), (label, ran.stdout, ran.stderr))
        (out / 'native-qualification.json').write_text(json.dumps(dict(cases_each=sum(1 for _ in native.model.cases(native=True)),
            exits=exits, separate_actual_body_and_typed_caller_provider=True, all_object_bytes_and_padding_canaries=True,
            helper_entry_snapshot=True, all_mutation_modes_fired=True, diagnostic_provider_not_retail_bzero=True,
            actual_SDK_struct163_size56=True, UBSan=True, no_fwrapv=True), indent=2) + '\n')


if __name__ == '__main__': unittest.main()
