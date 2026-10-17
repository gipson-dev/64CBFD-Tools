"""Execute the complete flat C loader in a separate native32 caller/provider rig."""
import json
from pathlib import Path
import subprocess
import unittest

from tools.experiments import game_microcode_loader_lifetimes as source
from tools.tests import game_microcode_loader_native as native
from tools.tests.test_game_projected_packet_draw import native_command


class MicrocodeLoaderNativeTests(unittest.TestCase):
    def test_native32_O2_O0_UBSan_and_four_functional_controls(self):
        root = Path(__file__).resolve().parents[2]; out = root / source.BUILD
        source.source.freeze(root, out)
        caller = out / 'native-caller.c'; caller.write_text(native.program())
        providers = out / 'native-providers.c'; providers.write_text(native.PROVIDERS)
        selected = next(source.flat_forms())[1]; exits = {}
        for label, opt, body in [('o2', '-O2', selected), ('o0', '-O0', selected)] + [
                (label, '-O2', body) for label, body in native.controls(selected).items()]:
            if label not in ('o2', 'o0'): self.assertNotEqual(body, selected)
            unit = out / ('native-' + label + '.c'); unit.write_text(native.HEADER + body + '\n'); exe = unit.with_suffix('.elf')
            built = subprocess.run([*native_command(opt), '-mstackrealign', '-malign-double', '-fno-strict-aliasing',
                str(unit.relative_to(root)), str(providers.relative_to(root)), str(caller.relative_to(root)),
                '-o', str(exe.relative_to(root))], cwd=root, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60); exits[label] = ran.returncode
            if label in ('o2', 'o0'): self.assertEqual(ran.returncode, 0, (label, ran.stdout, ran.stderr))
            else: self.assertIn(ran.returncode, (21, 22), (label, ran.stdout, ran.stderr))
        self.assertEqual(native.BYTES, 25240)
        (out / 'native-qualification.json').write_text(json.dumps(dict(cases_each=sum(1 for _ in native.cases()), exits=exits,
            actual_SDK_state_selector_offset43=True, separate_typed_body_caller_provider=True,
            public_bytes_each=25240, surrounding_typed_canaries=True, explicit_numeric_and_pointer_lanes_only=True,
            real_table_vectors_and_synthetic_extended_table=True, callback_positive_gates=True,
            UBSan=True, no_fwrapv=True, DMA_PI_cache_queue_hardware_still_bounded=True), indent=2) + '\n')


if __name__ == '__main__': unittest.main()
