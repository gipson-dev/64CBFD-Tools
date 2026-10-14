"""Refill source/profile edits and baseline capture fail closed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_codec_input_refill_candidates as source


class CodecRefillCandidateTests(unittest.TestCase):
    def test_recovery_keeps_neighbors_and_places_the_typed_forward_declaration(self):
        before = '''s32 func_151F8088(void *arg0, s32 arg1);
/* Generated placeholder declarations. */
s32 func_151F7F60();
s32 untouched();
/* End generated placeholder declarations. */
/* Non-matching C placeholders for asm/nonmatchings/game_221290/func_151F7F60.s. */
s32 func_151F7F60() { return 0; }
s32 untouched(void) { return 7; }
'''
        after = source.recover(before)
        self.assertIn('s32 func_151F8088(void *arg0, s32 arg1);\ns32 func_151F7F60(void *decoder);', after)
        self.assertIn(source.BODY, after)
        self.assertIn('s32 untouched(void) { return 7; }', after)
        group = after.split('/* Generated placeholder declarations. */', 1)[1].split('/* End generated', 1)[0]
        self.assertNotIn(source.FUNCTION, group)
        self.assertIn('s32 untouched();', group)

    def test_only_one_new_codec_profile_is_selected(self):
        before = '''# neighbors in this splat owner. Select only these seven functions from -g.
CODEC_RETAIL_G_FUNCTIONS := func_151F3DE0 func_151F42E8 func_151F578C \\
    func_151F6970 func_151F6B28 func_151F8088 func_151F85C4
unrelated: keep
'''
        after = source.recover_makefile(before)
        self.assertIn('these eight functions', after)
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
                with self.assertRaisesRegex(ValueError, 'changed image baseline'):
                    source.freeze(root, other)
                self.assertFalse(list(other.iterdir()))
                changed = dict(pins, owner=hashlib.sha256(b'changed baseline').hexdigest())
                (out / 'before-owner').write_bytes(b'changed baseline')
                (out / 'baseline.json').write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, 'baseline manifest'):
                    source.freeze(root, out)


if __name__ == '__main__':
    unittest.main()
