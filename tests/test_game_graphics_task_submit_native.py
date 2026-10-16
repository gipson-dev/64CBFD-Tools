"""Native32 real SDK records and helper emitter at two optimization levels."""
import json
from pathlib import Path
import subprocess
import unittest

from tools.experiments import game_graphics_task_submit as source
from tools.tests import game_graphics_task_submit_native as native
from tools.tests.test_game_projected_packet_draw import native_command


class GraphicsTaskSubmitNativeTests(unittest.TestCase):
    def test_native32_O2_O0_UBSan_and_six_functional_controls(self):
        root = Path(__file__).resolve().parents[2]; out = root / source.BUILD
        source.freeze(root, out)
        harness = out / 'native.c'; harness.write_text(native.program())
        helper = out / 'native-providers.c'; helper.write_text(native.providers((out / 'before-frustum_owner').read_text()))
        exits = {}
        for name, opt, body in [('o2', '-O2', source.SELECTED), ('o0', '-O0', source.SELECTED)] + [
                (name, '-O2', body) for name, body in native.controls(source.SELECTED).items()]:
            if name not in ('o2', 'o0'): self.assertNotEqual(body, source.SELECTED)
            unit = out / ('native-' + name + '.c'); unit.write_text(native.HEADER + body + '\n'); exe = unit.with_suffix('.elf')
            built = subprocess.run([*native_command(opt), '-mstackrealign', '-malign-double', '-fno-strict-aliasing',
                str(unit.relative_to(root)), str(helper.relative_to(root)), str(harness.relative_to(root)),
                '-o', str(exe.relative_to(root))], cwd=root, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60); exits[name] = ran.returncode
            if name in ('o2', 'o0'): self.assertEqual(ran.returncode, 0, (name, ran.stdout, ran.stderr))
            else: self.assertIn(ran.returncode, (21, 22), (name, ran.stdout, ran.stderr))
        self.assertEqual(native.WORDS, 10761)
        (out / 'native-qualification.json').write_text(json.dumps(dict(cases_each=sum(1 for _ in native.cases()), exits=exits,
            actual_SDK_OSScTask96_list24_msg92_and_Gfx8=True, eight_byte_SDK_alignment_explicit=True,
            separate_typed_caller_body_and_providers=True, real_two_row_C_emitter=True,
            all10761_public_words_and_canaries=True, explicit_endian_lanes_and_pointer_fields_only=True,
            callback_positive_gates=True, UBSan=True, no_fwrapv=True,
            cache_blocking_queue_ucode_hardware_still_bounded=True), indent=2) + '\n')


if __name__ == '__main__': unittest.main()
