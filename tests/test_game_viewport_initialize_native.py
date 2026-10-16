"""Native32 complete-body qualification under the explicitly bounded provider ABI."""
import json
from pathlib import Path
import subprocess
import unittest

from tools.experiments import game_viewport_initialize as source
from tools.experiments import game_viewport_initialize_lifetimes as lifetime
from tools.tests import game_viewport_initialize_native as native
from tools.tests.test_game_projected_packet_draw import native_command


class ViewportInitializeNativeTests(unittest.TestCase):
    def test_complete_body_native32_O2_O0_UBSan_and_seven_effective_controls(self):
        root = Path(__file__).resolve().parents[2]; out = root / lifetime.BUILD
        lifetime.freeze(root, out); before = (out / 'before-frustum_owner').read_text()
        harness = out / 'native.c'; harness.write_text(native.program(before))
        helper = out / 'native-providers.c'; helper.write_text(native.providers(before))
        exits = {}
        controls = dict(native.controls(lifetime.SELECTED), old_unsequenced_source=source.SELECTED)
        for name, opt, body in [('o2', '-O2', lifetime.SELECTED), ('o0', '-O0', lifetime.SELECTED)] + [
                (name, '-O2', body) for name, body in controls.items()]:
            if name not in ('o2', 'o0'): self.assertNotEqual(body, lifetime.SELECTED)
            unit = out / ('native-' + name + '.c'); unit.write_text(native.header(before) + body + '\n')
            exe = unit.with_suffix('.elf')
            build = subprocess.run([*native_command(opt), '-mstackrealign', '-fno-strict-aliasing',
                str(unit.relative_to(root)), str(helper.relative_to(root)), str(harness.relative_to(root)),
                '-o', str(exe.relative_to(root))], cwd=root, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
            exits[name] = ran.returncode
            if name in ('o2', 'o0'): self.assertEqual(ran.returncode, 0, (name, ran.stdout, ran.stderr))
            else: self.assertIn(ran.returncode, (21, 22), (name, ran.stdout, ran.stderr))
        self.assertEqual(native.WORDS, 6936)
        (out / 'native-qualification.json').write_text(json.dumps(dict(cases_each=sum(1 for _ in native.cases()),
            exits=exits, complete_native32_body=True, typed_caller_and_providers_separate_units=True,
            real_bounds_clamp_SDK_Vp=True, all6936_public_words_and_canaries=True,
            explicit_endian_lanes_and_pointer_fields_only=True, callback_positive_gates=True,
            UBSan=True, no_fwrapv=True, FOV_trig_projection_still_bounded=True,
            guest_only_high_pages_overlap_invalid_casts=True), indent=2) + '\n')


if __name__ == '__main__': unittest.main()
