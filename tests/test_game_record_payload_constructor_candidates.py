"""Recovery scope, one language transition and unrecapturable input pins."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_record_payload_constructor_candidates as source


class RecordPayloadCandidateTests(unittest.TestCase):
    def test_only_the_selected_assembly_and_draft_are_replaced(self):
        before = '''s32 untouched(void) { return 7; }/* Non-matching C placeholders for asm/nonmatchings/game_169510/func_1513C350.s. */
#pragma GLOBAL_ASM("asm/nonmatchings/game_169510/func_1513C350.s")
// discarded draft
struct210 *func_1513C4EC(void) { return 0; }
'''
        after = source.recover(before)
        self.assertIn('s32 untouched(void) { return 7; }', after)
        self.assertIn('struct210 *func_1513C4EC(void) { return 0; }', after)
        self.assertIn(source.BODY, after)
        self.assertNotIn('discarded draft', after)
        self.assertNotIn('GLOBAL_ASM', after)
        with self.assertRaisesRegex(ValueError, 'one original'):
            source.recover(after)

    def test_only_one_progress_language_field_changes(self):
        before = b'header\nowner,func_1513C350,0,412,asm\nother,func_12345678,0,4,c\n'
        after = source.expected_progress(before)
        self.assertEqual(after, before.replace(b'412,asm\n', b'412,c\n'))
        for bad in (before.replace(b',asm\n', b',c\n'), before + before, b'header\n'):
            with self.assertRaisesRegex(ValueError, 'one original'):
                source.expected_progress(bad)

    def test_capture_pins_and_manifest_cannot_recapture_changed_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pins = {}
            for key, filename in source.PATHS.items():
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(key.encode())
                pins[key] = hashlib.sha256(key.encode()).hexdigest()
            out = root / 'out'
            out.mkdir()
            with patch.object(source, 'BASELINE', pins):
                source.freeze(root, out)
                (root / source.PATHS['owner']).write_bytes(b'changed live owner')
                source.freeze(root, out)
                self.assertEqual((out / 'before-owner').read_bytes(), b'owner')
                fresh = root / 'fresh'
                fresh.mkdir()
                with self.assertRaisesRegex(ValueError, 'capture changed'):
                    source.freeze(root, fresh)
                self.assertFalse(list(fresh.iterdir()))
                wrong = dict(pins, owner=hashlib.sha256(b'changed frozen owner').hexdigest())
                (out / 'before-owner').write_bytes(b'changed frozen owner')
                (out / 'baseline.json').write_text(json.dumps(wrong))
                with self.assertRaisesRegex(ValueError, 'baseline manifest'):
                    source.freeze(root, out)


if __name__ == '__main__':
    unittest.main()
