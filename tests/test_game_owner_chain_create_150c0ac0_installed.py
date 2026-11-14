"""Verify the installed direct C and owner-chain constructor behavior."""
from pathlib import Path
import csv
import os
import re
import struct
import subprocess
import sys
import unittest

from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT / 'conker/build/game-owner-chain-create-150c0ac0-screen'
NAME = 'func_150C0AC0'


class InstalledOwnerChainCreate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / 'conker/src/game/generated_EDE60.c'
        OUT.mkdir(parents=True, exist_ok=True)
        cls.raw, diagnostics = compile_owner(ROOT, OUT, source.read_text(), 'installed')
        if 'Error:' in diagnostics:
            raise AssertionError(diagnostics)
        cls.padded = ROOT / 'conker/build/src/game/generated_EDE60.c.o'
        cls.env = dict(os.environ, CBFD_CONSUMER_ROOT=str(ROOT),
                       OWNER_CHAIN_RAW=str(cls.raw), OWNER_CHAIN_PADDED=str(cls.padded),
                       OWNER_CHAIN_SOURCE=str(source), PYTHONDONTWRITEBYTECODE='1')

    def test_fresh_source_and_installed_slot(self):
        conker = ROOT / 'conker'
        symbols = {r[1]: r[2][1] for r in symbol_rows((conker / 'build/conker.us.elf').read_bytes())}
        retail = list(struct.unpack_from('>94I', (conker / 'conker.us.bin').read_bytes(), 0xedf70))
        self.assertEqual(bound_blob(*payload(self.raw, NAME), symbols), retail)
        self.assertEqual(bound_blob(*payload(self.padded, NAME), symbols), retail)
        with (conker / 'retail_word_patches.us.csv').open(newline='') as stream:
            self.assertFalse([row for row in csv.DictReader(stream) if row['function'] == NAME])
        asm = (conker / 'asm/EDE60.s').read_text()
        match = re.search(r'^glabel ' + NAME + r'\n.*?^endlabel ' + NAME + r'\s*$', asm, re.M | re.S)
        self.assertIsNotNone(match)
        source = OUT / 'installed-retail.s'
        obj = OUT / 'installed-retail.o'
        source.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'
                          + match.group() + '\n.size ' + NAME + ',.-' + NAME + '\n')
        command = ['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                   '-I', 'include', '-o', str(obj.relative_to(conker)), str(source.relative_to(conker))]
        subprocess.run(command, cwd=conker, check=True, capture_output=True)
        self.assertEqual(payload(self.raw, NAME), payload(obj, NAME))

    def test_installed_guest_and_native_behavior(self):
        for module in ('behavior', 'alias', 'stack_alias', 'memcpy_connected', 'fault',
                       'caller', 'native', 'controls'):
            with self.subTest(module=module):
                result = subprocess.run([sys.executable, '-m',
                    'tools.tests.game_owner_chain_create_150c0ac0_' + module],
                    cwd=ROOT, env=self.env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
