"""Check relocations in multiple independently linked address layouts."""
import subprocess
from tools.experiments import game_effect_descriptor_150b9d8c_direct as packet
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
from tools.tests.game_effect_descriptor_150b9d8c_oracle import SYMS


def run():
    name = 'func_150B9D8C'
    for k, base in enumerate((0x15001000, 0x1f008000, 0x1000fff0)):
        symbols = {key: ((base & 0xf0000000) | (value & 0x0fffffff)) + 0x1000*k
                   for key, value in SYMS.items()}
        truth = bound_blob(*packet.payload(packet.OUT/'retail.o', name), symbols)
        for key in ('after', 'retail', 'generated', 'generic'):
            obj = packet.OUT/(key+'.o')
            ld = packet.OUT/('rebase-%s-%d.ld' % (key, k))
            elf = ld.with_suffix('.elf')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % base)
            undefined = subprocess.run(['mips-linux-gnu-nm', '-u', str(obj)], capture_output=True, text=True, check=True).stdout.splitlines()
            defined = dict(symbols)
            for line in undefined:
                sym = line.split()[-1]
                if sym not in defined:
                    defined[sym] = 0x800a6000 if sym.startswith('D_') else ((base & 0xf0000000) | 0x8000)
            command = ['mips-linux-gnu-ld', '-m', 'elf32btsmip', '--unresolved-symbols=ignore-all', '-T', str(ld), '-e', name,
                       *['--defsym=%s=0x%X' % item for item in defined.items()], '-o', str(elf), str(obj)]
            result = subprocess.run(command, cwd=packet.ROOT/'conker', capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            functions, _, _ = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
            expected = bound_blob(*packet.payload(obj, name), symbols)
            assert tuple(functions[name][:len(expected)]) == tuple(expected) == tuple(truth), (key, k)
