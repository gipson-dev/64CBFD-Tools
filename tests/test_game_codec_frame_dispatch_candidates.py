"""Typed candidate interfaces, one profile selection and immutable baselines."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_codec_frame_dispatch_candidates as source


class FrameDispatchCandidateTests(unittest.TestCase):
    def test_typed_and_diagnostic_bodies_have_consistent_private_prototypes(self):
        before = '''s32 func_151F7F60(void *decoder);
/* Generated placeholder declarations. */
s32 func_151F86B0();
s32 untouched();
/* End generated placeholder declarations. */
s32 func_151F86B0() { return 0; }
s32 untouched(void) { return 7; }
'''
        after = source.recover(before)
        self.assertIn('s32 func_151F86B0(void *decoder, void **outputBuffer, s32 *bufferCount);', after)
        self.assertIn(source.BODY, after)
        self.assertIn('s32 untouched(void) { return 7; }', after)
        group = after.split('/* Generated placeholder declarations. */', 1)[1].split('/* End generated', 1)[0]
        self.assertNotIn(source.FUNCTION, group)
        raw = next(body for name, body in source.candidates() if name == 'raw-outputs')
        diagnostic = source.recover(before, raw)
        self.assertIn('s32 func_151F86B0(void *decoder, void *outputBuffer, void *bufferCount);', diagnostic)
        self.assertNotIn('void **outputBuffer', diagnostic)

    def test_only_one_new_g_function_is_selected(self):
        before = '''# neighbors in this splat owner. Select only these eight functions from -g.
CODEC_RETAIL_G_FUNCTIONS := func_151F3DE0 func_151F42E8 func_151F578C \\
    func_151F6970 func_151F6B28 func_151F7F60 func_151F8088 func_151F85C4
unrelated: keep
'''
        after = source.recover_makefile(before)
        self.assertIn('these nine functions', after)
        self.assertEqual(after.count(source.FUNCTION), 1)
        self.assertIn('unrelated: keep\n', after)
        with self.assertRaisesRegex(ValueError, 'one codec-g'):
            source.recover_makefile(after)

    def test_capture_and_manifest_cannot_recapture_changed_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {'elf': 'conker/build/conker.us.elf', 'owner': 'conker/src/game_221290.c',
                'makefile': 'conker/Makefile', 'guards': 'conker/retail_word_patches.us.csv', 'progress': 'conker/progress.csv'}
            pins = {}
            for key, path in paths.items():
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(key.encode())
                pins[key] = hashlib.sha256(file.read_bytes()).hexdigest()
            out = root / 'out'
            out.mkdir()
            with patch.object(source, 'BASELINE', pins):
                source.freeze(root, out)
                (root / paths['owner']).write_bytes(b'changed live owner')
                source.freeze(root, out)
                self.assertEqual((out / 'before-owner').read_bytes(), b'owner')
                other = root / 'other'
                other.mkdir()
                with self.assertRaisesRegex(ValueError, 'changed frame-dispatch inputs'):
                    source.freeze(root, other)
                self.assertFalse(list(other.iterdir()))
                changed = dict(pins, owner=hashlib.sha256(b'changed baseline').hexdigest())
                (out / 'before-owner').write_bytes(b'changed baseline')
                (out / 'baseline.json').write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, 'baseline manifest'):
                    source.freeze(root, out)


if __name__ == '__main__':
    unittest.main()
