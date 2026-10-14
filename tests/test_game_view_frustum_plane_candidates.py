"""Recovery scope and immutable view-plane candidate inputs."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_view_frustum_plane_candidates as source


class ViewPlaneCandidateTests(unittest.TestCase):
    def test_only_one_stub_and_its_terminal_disabled_draft_are_replaced(self):
        before = '''#include "variables.h"
/* Generated placeholder declarations. */
s32 func_1501B22C();
s32 untouched();
/* End generated placeholder declarations. */
s32 untouched(void) { return 7; }
/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501B22C.s. */
s32 func_1501B22C() { return 0; }
// JUSTREG: I think?
// void func_1501B22C(s32 unused) {}
'''
        after = source.recover(before)
        self.assertIn('void func_1501B22C(s32 index);', after)
        self.assertIn(source.BODY, after)
        self.assertIn('s32 untouched(void) { return 7; }', after)
        self.assertNotIn('JUSTREG', after)
        group = after.split('/* Generated placeholder declarations. */')[1].split('/* End generated')[0]
        self.assertNotIn(source.FUNCTION, group)
        with self.assertRaisesRegex(ValueError, 'terminal draft'):
            source.recover(after)
        with self.assertRaisesRegex(ValueError, 'terminal draft'):
            source.recover(before + 's32 later(void) { return 9; }\n')

    def test_baseline_capture_and_manifest_cannot_recapture_changed_inputs(self):
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
                (root / source.PATHS['owner']).write_bytes(b'changed live source')
                source.freeze(root, out)
                self.assertEqual((out / 'before-owner').read_bytes(), b'owner')
                fresh = root / 'fresh'
                fresh.mkdir()
                with self.assertRaisesRegex(ValueError, 'capture changed'):
                    source.freeze(root, fresh)
                self.assertFalse(list(fresh.iterdir()))
                (out / 'before-owner').write_bytes(b'changed frozen source')
                (out / 'baseline.json').write_text(json.dumps(dict(pins, owner=hashlib.sha256(b'changed frozen source').hexdigest())))
                with self.assertRaisesRegex(ValueError, 'baseline manifest'):
                    source.freeze(root, out)


if __name__ == '__main__':
    unittest.main()
