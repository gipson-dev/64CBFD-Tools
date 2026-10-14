"""Isolation retains interfaces and never fixes a failed body by erasing it."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments.alternative_source_c_inventory import definitions
from tools.experiments import alternative_source_function_isolation as source
from tools.experiments.alternative_source_function_isolation import isolate


class AlternativeSourceIsolationTests(unittest.TestCase):
    def test_c_only_profile_preserves_ido_flags_and_rejects_asm_wrappers(self):
        flags = ['-O1', '-g3']
        text = 'int selected(void) { return 1; }\n'
        self.assertEqual(source.preprocessor_flags(text, flags, True), ['-O1'])
        self.assertEqual(source.preprocessor_flags(text, flags), flags)
        self.assertEqual(flags, ['-O1', '-g3'])
        for wrapper in ('#pragma GLOBAL_ASM("file.s")', 'INCLUDE_ASM("dir", helper);',
                'INCLUDE_RODATA("dir", pool);', '#pragma asmproc recurse'):
            with self.assertRaisesRegex(ValueError, 'assembly wrappers'):
                source.preprocessor_flags(text + wrapper, flags, True)
        self.assertEqual(source.preprocessor_flags(text + '// GLOBAL_ASM("file.s")', flags, True), ['-O1'])

    def test_c_only_compile_uses_original_ido_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'selected.c'
            path.write_text('int selected(void) { return 1; }\n')
            out = root / 'output'
            out.mkdir()
            item = dict(path=path.name, function='selected',
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                compiler_flags=['-O1', '-g3'], c_only=True)
            calls = []
            def command(args, **kwargs):
                calls.append(args)
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            with patch.object(source.subprocess, 'run', side_effect=command):
                result = source.compile_one(root, root, out, item)
            self.assertIn('-O1', calls[0])
            self.assertNotIn('-g3', calls[0])
            self.assertIn('-O1', calls[1])
            self.assertIn('-g3', calls[1])
            self.assertEqual(result['compiler_flags'], ['-O1', '-g3'])
            self.assertEqual(result['preprocessor_flags'], ['-O1'])
            self.assertTrue(result['c_only'])

    def test_only_unrelated_bodies_become_unchanged_declarations(self):
        source = '''#include "private.h"
typedef struct { int x; } Record;
extern int callback(int);
static int bad(int x) { return nonexistent(x, 7); }
Record table[3];
int selected(Record *record) { return callback(record->x); }
void after(void) { const char *s = "{ }"; }
'''
        result = isolate(source, 'selected')
        self.assertEqual([row['function'] for row in definitions(result)], ['selected'])
        self.assertIn('static int bad(int x) ;', result)
        self.assertIn('Record table[3];', result)
        self.assertIn('int selected(Record *record) { return callback(record->x); }', result)
        self.assertIn('void after(void) ;', result)
        self.assertNotIn('nonexistent', result)
        self.assertIn('nonexistent', isolate(source, 'bad'))

    def test_comments_braces_and_conditionals_remain_in_context(self):
        source = '''/* fake(void) { } */
#if 0
int inactive(void) { return 7; }
#endif
int selected(int /* { } */ x) { if (x) { return 3; } return 4; }
'''
        result = isolate(source, 'selected')
        self.assertIn('#if 0\nint inactive(void) ;\n#endif', result)
        self.assertIn('int selected(int /* { } */ x) { if (x) { return 3; } return 4; }', result)
        self.assertIn('/* fake(void) { } */', result)

    def test_unknown_or_ambiguous_definition_is_rejected(self):
        with self.assertRaises(ValueError):
            isolate('int one(void) { return 1; }', 'missing')
        with self.assertRaises(ValueError):
            isolate('#if A\nint one(void) { return 1; }\n#else\nint one(void) { return 2; }\n#endif', 'one')

    def test_unused_local_conflicts_can_be_omitted_without_touching_used_types(self):
        text = '''#include "functions.h"
float unused_conflict(int);
float used(int);
int selected(int x) { return used(x); }
int unrelated(int x) { return unused_conflict(x); }
'''
        result = isolate(text, 'selected', True)
        self.assertIn('#include "functions.h"', result)
        self.assertIn('float used(int);', result)
        self.assertIn('int selected(int x) { return used(x); }', result)
        self.assertNotIn('unused_conflict', result)
        self.assertNotIn('unrelated', result)

    def test_global_initializer_and_macro_references_keep_interfaces(self):
        text = '''int callback(int);
int unused(int);
int (*handler)(int) = callback;
#define CALLBACK callback
int selected(int x) { return handler(x) + CALLBACK(x); }
int callback(int x) { return x + 1; }
int unused(int x) { return x + 2; }
'''
        result = isolate(text, 'selected', True)
        self.assertIn('int callback(int);', result)
        self.assertIn('int callback(int x) ;', result)
        self.assertIn('int (*handler)(int) = callback;', result)
        self.assertIn('#define CALLBACK callback', result)
        self.assertNotIn('int unused', result)

    def test_only_unused_extern_views_are_omitted_and_global_storage_is_kept(self):
        text = '''extern int unused_global;
extern const float used_global[2];
int storage[3] = {1, 2, 3};
int selected(void) { return (int)used_global[0] + storage[1]; }
'''
        result = isolate(text, 'selected', True)
        self.assertNotIn('unused_global', result)
        self.assertIn('extern const float used_global[2];', result)
        self.assertIn('int storage[3] = {1, 2, 3};', result)

    def test_changed_input_rejected_before_compiling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'selected.c'
            path.write_text('int selected(void) { return 1; }\n')
            item = dict(path=path.name, function='selected', source_sha256='0' * 64,
                compiler_flags=['-O2', '-g3'])
            with patch.object(source.subprocess, 'run') as command:
                with self.assertRaisesRegex(ValueError, 'Changed source input'):
                    source.compile_one(root, root, root, item)
                command.assert_not_called()

    def test_successful_exit_cannot_accept_a_stale_or_missing_object(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'selected.c'
            path.write_text('int selected(void) { return 1; }\n')
            out = root / 'output'
            out.mkdir()
            obj = out / 'selected-selected.o'
            obj.write_bytes(b'stale object')
            item = dict(path=path.name, function='selected',
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), compiler_flags=['-O2', '-g3'])
            completed = SimpleNamespace(returncode=0, stdout='', stderr='')
            with patch.object(source.subprocess, 'run', return_value=completed):
                result = source.compile_one(root, root, out, item)
            self.assertEqual(result['status'], 'missing_object')
            self.assertIsNone(result['object_sha256'])
            self.assertFalse(obj.exists())

    def test_wrong_definition_cannot_be_credited_to_the_selected_body(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'selected.c'
            path.write_text('int selected(void) { return 1; }\n')
            out = root / 'output'
            out.mkdir()
            item = dict(path=path.name, function='selected',
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), compiler_flags=['-O2', '-g3'])
            calls = []
            def command(args, **kwargs):
                calls.append(args)
                if len(calls) == 2:
                    (out / 'selected-selected.o').write_bytes(b'new object')
                return SimpleNamespace(returncode=0, stdout='', stderr='')
            with patch.object(source.subprocess, 'run', side_effect=command), patch.object(
                    source, 'parse_object', return_value=(b'', {'unrelated': {}}, {})):
                result = source.compile_one(root, root, out, item)
            self.assertEqual(result['status'], 'extra_definition_emitted')
            self.assertEqual(result['extra_definitions'], ['unrelated'])
            self.assertIsNone(result['object_sha256'])

    def test_spaced_double_pointer_return_does_not_leak_another_body(self):
        result = isolate('int selected(void) { return 1; }\nvoid * *other(void) { return 0; }\n', 'selected')
        self.assertEqual([row['function'] for row in definitions(result)], ['selected'])
        self.assertIn('void * *other(void) ;', result)

    def test_old_style_neighbor_keeps_nonprototype_call_interface(self):
        text = '''float old(x)
    float x;
{ return x; }
int selected(void) { return (int)old(3.0f); }
'''
        result = isolate(text, 'selected', True)
        self.assertIn('float old();', result)
        self.assertNotIn('float x;', result)
        self.assertEqual([row['function'] for row in definitions(result)], ['selected'])

    def test_collected_records_keep_body_and_profile_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'selected.c'
            path.write_text('int selected(void) { return 1; }\n')
            out = root / 'output'
            out.mkdir()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            item = dict(path=path.name, function='selected', source_sha256=digest, compiler_flags=['-O2', '-g3'])
            with patch.object(source.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')):
                source.compile_one(root, root, out, item)
            receipt = root / 'receipt.json'
            receipt.write_text(json.dumps(dict(draft_compile_gate=[dict(item, status='compile_error')])))
            result = source.collect_records(root, receipt, out)
            self.assertEqual(result['statuses'], {'missing_object': 1})
            self.assertFalse(result['complete_definition_sweep'])
            record = next(out.glob('*-diagnostics.json'))
            values = json.loads(record.read_text())
            values['compiler_flags'] = ['-O1']
            record.write_text(json.dumps(values))
            with self.assertRaisesRegex(ValueError, 'Changed collected profile'):
                source.collect_records(root, receipt, out)

    def test_retry_cannot_use_a_false_complete_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'selected.c'
            path.write_text('int selected(void) { return 1; }\n')
            item = dict(path=path.name, function='selected', source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                compiler_flags=['-O2', '-g3'], status='compile_error')
            receipt = root / 'receipt.json'
            receipt.write_text(json.dumps(dict(draft_compile_gate=[item],
                function_definitions=[dict(path=path.name, function='selected')])))
            previous = root / 'previous.json'
            previous.write_text(json.dumps(dict(complete_definition_sweep=True,
                receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(), draft_compile_gate=[])))
            with self.assertRaisesRegex(ValueError, 'does not cover all'):
                source.compile_failed(root, root, receipt, root / 'out', previous_isolation=previous)


if __name__ == '__main__':
    unittest.main()
