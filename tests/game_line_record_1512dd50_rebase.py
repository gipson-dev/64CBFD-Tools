"""Link the original and guarded owner at different MIPS jump regions."""
from pathlib import Path
import json, subprocess
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-line-record-1512dd50-durable'
name = 'func_1512DD50'
base = {r[1]: r[2][1] for r in symbol_rows((root / 'conker/build/conker.us.elf').read_bytes())}

def link(obj, target, defs, label):
    _, fs, _ = parse_object(obj)
    offset = fs[name]['value']
    script, elf, binary = (out / (label + ext) for ext in ('.ld', '.elf', '.bin'))
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (target-offset))
    u = subprocess.run(['mips-linux-gnu-nm', '-u', str(obj)], capture_output=True, text=True, check=True).stdout.splitlines()
    names = [line.split()[-1] for line in u if line.split()]
    assert set(names) <= set(defs), (obj, set(names)-set(defs))
    argv = ['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', name,
            *[x for n in names for x in ('--defsym', f'{n}={hex(defs[n])}')], '-o', str(elf), str(obj)]
    p = subprocess.run(argv, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    subprocess.run(['mips-linux-gnu-objcopy', '-O', 'binary', '-j', '.text', str(elf), str(binary)], capture_output=True, check=True)
    return binary.read_bytes()[offset:offset+340]

layouts = ((0x1512dd50, 0x150ad930), (0x17107ffc, 0x17017ffc),
           (0x1910fff0, 0x1902fffc), (0x1b10fff0, 0x1b038000))
results = []
for i, (target, helper) in enumerate(layouts):
    defs = dict(base)
    defs['func_150AD930'] = helper
    a = link(out/'retail.o', target, defs, f'rebase-{i}-retail')
    b = link(out/'explicit-padded.o', target, defs, f'rebase-{i}-padded')
    assert a == b, (i, target, helper)
    results.append(dict(entry=hex(target), helper=hex(helper)))
report = {'layouts': results, 'gnu_links': 8, 'normalized_equals_retail': True}
(out/'rebase-screen.json').write_text(json.dumps(report, indent=2)+'\n')
print(report, flush=True)
