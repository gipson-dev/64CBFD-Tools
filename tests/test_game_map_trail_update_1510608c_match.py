"""Fresh qualification of the direct map-trail update recovery."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools import pad_generated_object as pg
import sys
sys.modules.setdefault('pad_generated_object', pg)
from tools import pad_c_object as pc
from tools.experiments import game_map_trail_update_1510608c_recovery as source
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments import game_map_trail_constructor_15105ce0_match as make_driver
from tools.tests import game_map_trail_update_1510608c_oracle as guest
from tools.tests import game_map_trail_update_1510608c_native as native
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout


class TrailUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = source.screen()
        cls.out = source.OUT / 'qualification'
        cls.out.mkdir(exist_ok=True)
        cls.obj = source.OUT / 'screen/candidate.o'
        # compile_owner emits an .o beside its copied .c.
        if not cls.obj.exists():
            cls.obj = source.OUT / 'screen/candidate.c.o'
        cls.raw, cls.refs = source.payload(cls.obj, source.FUNCTION)
        cls.words = source.bind(cls.raw, cls.refs)

    def test_direct_source_and_owner(self):
        self.assertEqual((self.receipt['words'], self.receipt['frame'], self.receipt['positional_differences']), (85, 48, 0))
        self.assertEqual(self.receipt['unchanged_neighbors'], 36)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), '0fba75d9c18e104f8d13b77ba47ba5f8ca9d1b75e4e70934dfc94ffefb0e63df')
        original = source.OUT/'screen/before.o'
        if not original.exists():
            original = source.OUT/'screen/before.c.o'
        self.assertEqual((self.raw, self.refs), source.payload(original, source.FUNCTION),
                         'Raw words and relocation bindings must equal original assembly')
        before, after = source.source()
        live = (source.ROOT/source.SOURCE).read_text()
        self.assertIn(live, (before, after))
        (self.out/'caller-census.json').write_text(json.dumps(source.caller_census(), indent=2)+'\n')

    def test_guest_contract(self):
        report = guest.run(self.words)
        self.assertEqual(report['visited_words'], 84)  # Nonzero-divisor contract excludes BREAK.
        (self.out/'guest.json').write_text(json.dumps(report, indent=2)+'\n')

    def test_native_sdk32(self):
        report = native.run()
        self.assertEqual(len(report), 3)

    def test_effective_negative_controls(self):
        controls = {
            'changed-home': (16, (self.words[16]&0xFFFF0000)|0x2A),
            'enabled-mask': (23, (self.words[23]&0xFFFF0000)|2),
            'duration-sign': (30, self.words[30]^0x10000000),
            'timer-destination': (44, (self.words[44]&0xFFFF0000)|0x10),
            'second-endpoint': (74, (self.words[74]&0xFFFF0000)|0x20),
            'unsigned-random': (55, self.words[55]^1),
        }
        # Every mutation must change a word and fail the independent contract.
        rejected = []
        for label, (index, replacement) in controls.items():
            changed = list(self.words)
            self.assertNotEqual(changed[index], replacement, label)
            changed[index] = replacement
            with self.assertRaises((AssertionError, KeyError, ValueError), msg=label):
                guest.run(changed)
            rejected.append(label)
        (self.out/'negative-controls.json').write_text(json.dumps(rejected)+'\n')

    def test_actual_make_and_whole_image(self):
        root, out = source.ROOT, self.out
        guards = root/'conker/retail_word_patches.us.csv'
        base = source.OUT/'baseline'
        self.assertEqual(guards.read_bytes(), (base/'conker/retail_word_patches.us.csv').read_bytes())
        owner = 'generated_133190'
        assembly = pc.emit_padded_assembly(self.obj, root/'conker/retail_layout.us.txt', owner,
            rodata_symbol='D_800A2420', word_patches_path=guards)
        independent = pg.emit_padded_assembly(self.obj, root/'conker/asm/133190.s', filename=owner,
            rodata_symbol='D_800A2420', word_patches_path=guards)
        objects = []
        for label, text in (('layout', assembly), ('asm', independent)):
            path = out/(label+'.s')
            obj = path.with_suffix('.o')
            path.write_text(text)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                            '-I', str(root/'conker/include'), '-o', str(obj), str(path)], check=True, capture_output=True)
            self.assertEqual(obj.read_bytes(), (base/'conker/build/src/game/generated_133190.c.o').read_bytes())
            objects.append(obj)
        _, selected = source.source()
        (out/'after-diagnostics.txt').write_text(json.loads((source.OUT/'screen/receipt.json').read_text())['diagnostics'])
        spec = dict(selected=selected)
        with patch.multiple(make_driver, ROOT=root, OUT=out, SPEC=spec):
            make_report = make_driver.actual_Make(objects[0], self.obj, guards,
                selected=selected, functions=37)
        with patch.multiple(linker, FILENAME=owner, OBJECT='conker/build/src/game/generated_133190.c.o', LINKER='conker/build/conker.ld'):
            elf = linker.link_image(root, out, objects[0], 'image')
        self.assertEqual(elf.read_bytes(), (base/'conker/build/conker.us.elf').read_bytes())
        functions, _, addresses = load_elf_functions(elf, 'mips-linux-gnu-objdump')
        self.assertEqual(len(functions), 6051)
        audit = audit_layout(elf, root/'conker')
        report = dict(actual_Make=make_report, full_ELF_equal=True, whole_object_equal=True,
                      ELF_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(), function_slots=len(functions),
                      protected_data_audit=audit, guard_bytes_unchanged=True, source_installed=(root/source.SOURCE).read_text()==selected)
        (out/'integration.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
