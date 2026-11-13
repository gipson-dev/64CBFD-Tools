"""Verify target relocations against independently linked symbol bases."""
import subprocess

from tools.experiments import game_paired_ground_constructor_match as packet
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
from tools.tests import game_paired_ground_constructor_oracle as guest


def run(state):
    report = {}
    for name in state:
        count = 0
        for k, base in enumerate((0x15001000, 0x1f008000, 0x1000fff0)):
            symbols = {key: value + (0x11000 * k if key.startswith('D_') else 0x4000 * k)
                       for key, value in guest.symbols(name).items()}
            for key in ('after', 'retail', 'generated', 'generic'):
                ld = packet.OUT / (name + '-rebase-%d-%s.ld' % (k, key))
                elf = ld.with_suffix('.elf')
                ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % base)
                undefined = subprocess.run(['mips-linux-gnu-nm', '-u', str(state[name][key])],
                                           capture_output=True, text=True, check=True).stdout.splitlines()
                defined = dict(symbols)
                for line in undefined:
                    symbol = line.split()[-1]
                    if symbol not in defined:
                        defined[symbol] = 0x800a6000 if symbol.startswith('D_') else 0x15008000
                cmd = ['mips-linux-gnu-ld', '-m', 'elf32btsmip', '--unresolved-symbols=ignore-all',
                       '-T', str(ld), '-e', name,
                       *['--defsym=%s=0x%X' % (n, v) for n, v in defined.items()],
                       '-o', str(elf), str(state[name][key])]
                result = subprocess.run(cmd, cwd=packet.ROOT / 'conker', capture_output=True, text=True)
                assert result.returncode == 0, result.stderr
                functions, _, _ = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
                actual = functions[name]
                raw, refs = packet.payload(state[name][key], name)
                expected = bound_blob(raw, refs, symbols)
                assert len(actual) >= len(expected) and tuple(actual[:len(expected)]) == tuple(expected), (name, key, k)
                count += 1
        report[name] = {'symbol_bases': 3, 'actual_gnu_links': count}
    return report
