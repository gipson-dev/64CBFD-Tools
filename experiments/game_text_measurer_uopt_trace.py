"""Opt-in, fingerprint-locked UOPT diagnostics in an owned compiler process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from tools.experiments import game_text_measurer_candidates as screen

COMPILERS = {
    'cc': 'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'uopt': '23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
}
MODES = (4, 5, 6, 7)
EXIT_MARKER = 'TRACE_EXIT inferior=1 code=0'
CAVEAT = 'Debug real-number printing is suppressed; numeric timings are not valid.'


def compiler_fingerprints(root):
    return {name: hashlib.sha256((root / 'ido/ido5.3_recomp' / name).read_bytes()).hexdigest()
            for name in COMPILERS}


def allocation_constraints(text):
    """Read mode5 integer constraints; deliberately ignore suppressed real values."""
    records = []
    for block in re.split(r'(?m)(?=^>>>active<<<)', text):
        if not block.startswith('>>>active<<<'):
            continue
        line = block.splitlines()[0]
        active = re.fullmatch(r'>>>active<<<\{(\d+\|\d+)\}\s+(\d+)\s+(-?\d+)', line)
        forbidden = re.search(r'^forbidden: \[([ 0-9]*)\]$', block, re.MULTILINE)
        interference = re.search(r'^:::interfere with:::[ ]*([ 0-9]*)$', block, re.MULTILINE)
        if active is None or forbidden is None or interference is None:
            raise ValueError('Malformed mode5 allocation block')
        records.append(dict(identity=active[1], expression=int(active[2]), color=int(active[3]),
                            forbidden=[int(value) for value in forbidden[1].split()],
                            interference=[int(value) for value in interference[1].split()]))
    return records


def variable_expressions(text):
    """Read the integer variable table and its front-end virtual-register marker."""
    records = []
    for line in text.splitlines():
        if not line.startswith('{') or ' isvar ' not in line:
            continue
        match = re.fullmatch(r'\{\s*(\d+)\|(\d+)\}\s+(\d+)\s+isvar\s+([A-Z])\s+'
                             r'(\d+)\s+(-?\d+)(vreg)?', line)
        if match is None:
            raise ValueError('Malformed UOPT variable expression')
        records.append(dict(identity=match[1] + '|' + match[2], expression=int(match[3]),
                            storage=match[4], procedure=int(match[5]), offset=int(match[6]),
                            virtual_register=match[7] is not None))
    return records


def debugger_script(root):
    program = json.dumps(str((root / 'ido/ido5.3_recomp/uopt').resolve()))
    return '''set pagination off
set confirm off
set startup-with-shell off
set auto-load off
set print thread-events off
set follow-fork-mode child
set detach-on-fork off
set schedule-multiple on
handle SIGCHLD nostop noprint pass
python
def trace_exit(event):
    gdb.write('TRACE_EXIT inferior=%d code=%s\\n' %
              (event.inferior.num, getattr(event, 'exit_code', 'unknown')))
gdb.events.exited.connect(trace_exit)
end
catch exec
commands
silent
python
if gdb.current_progspace().filename == ''' + program + ''':
    bp = gdb.Breakpoint('*0x422830')
    bp.condition = '$edx == 0x0fb52914 && *(unsigned int*)($rdi + $rdx + 4) == 0'
    gdb.execute('commands %d\\nsilent\\nset $trace_fp = $edx\\nprintf "Allocate diagnostic stream buffer\\\\n"\\ncall ((int (*)(unsigned char *, int, unsigned int))0x4074e0)((unsigned char*)$rdi, 32, $trace_fp)\\ncontinue\\nend' % bp.number)
    timing = gdb.Breakpoint('*0x484590')
    gdb.execute('commands %d\\nsilent\\nprintf "Suppress diagnostic real-number printer\\\\n"\\nreturn\\ncontinue\\nend' % timing.number)
    gdb.execute('set follow-fork-mode parent')
end
continue
end
run
inferior 1
continue
python
# Remove UOPT-only native addresses before the driver launches UGEN/AS1.
for breakpoint in gdb.breakpoints() or ():
    if breakpoint.location in ('*0x422830', '*0x484590'):
        breakpoint.delete()
for attempt in range(6):
    if not any(inferior.num == 1 and inferior.pid for inferior in gdb.inferiors()):
        break
    if gdb.selected_inferior().pid:
        raise gdb.GdbError('Unexpected live child: refusing to resume a failed compiler')
    gdb.execute('inferior 1')
    gdb.execute('continue')
else:
    raise gdb.GdbError('Compiler did not terminate within bounded child-exit handling')
end
info inferiors
'''


def validate_trace(root, work, exit_code, log):
    record = dict(exit_code=exit_code, code_unchanged=False, caveat=CAVEAT)
    receipt = work / 'trace.json'
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    trace, obj = work / 'uoptlist', work / 'trace.o'
    if (exit_code or EXIT_MARKER not in log.splitlines() or not trace.is_file()
            or not trace.stat().st_size or not obj.is_file()
            or 'WHOLE UCODE TO UCODE OPTIMIZATION' not in trace.read_text()):
        raise ValueError('UOPT trace failed, incomplete, empty or missing object')
    if compiler_fingerprints(root) != COMPILERS:
        raise ValueError('Prepared compiler fingerprint changed')
    before = screen.compiler.parse_object(work / 'baseline.o')
    after = screen.compiler.parse_object(obj)
    left, right = screen.compiler.sections(work / 'baseline.o'), screen.compiler.sections(obj)
    pools = sorted(name for name in left.keys() | right.keys()
                   if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')))
    if before != after or any(left.get(name) != right.get(name) for name in pools):
        raise ValueError('UOPT diagnostic changed text, functions, relocations or pools')
    record.update(code_unchanged=True, bytes=trace.stat().st_size,
                  trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
                  compiler_sha256=COMPILERS, pool_sections=pools)
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    return record


def trace_uopt(root, out, name, body, mode=6):
    root, out = Path(root).resolve(), Path(out).resolve()
    work = (out / name).resolve()
    if (mode not in MODES or Path(name).name != name or name in ('', '.', '..')
            or not work.is_relative_to(root / 'conker/build')):
        raise ValueError('Diagnostic mode/name/output must be a known mode inside conker/build')
    if compiler_fingerprints(root) != COMPILERS:
        raise ValueError('Prepared compiler fingerprint mismatch; do not use native addresses')
    debugger = shutil.which('gdb')
    if debugger is None:
        raise FileNotFoundError('Existing GDB required; this helper does not install it')
    work.mkdir(parents=True, exist_ok=True)
    meta, _ = screen.compile_candidate(root, work, 'baseline', body)
    for filename in ('trace.o', 'uoptlist'):
        (work / filename).unlink(missing_ok=True)
    script = work / 'compiler-child.gdb'
    script.write_text(debugger_script(root))
    relative = lambda path: os.path.relpath(root / path, work)
    command = [debugger, '--nx', '--batch', '--iex', 'set auto-load off', '-x', str(script),
               '--args', relative('ido/ido5.3_recomp/cc'), '-c', '-32', '-G', '0',
               '-Xfullwarn', '-Xcpluscomm', '-signed', '-nostdinc', '-non_shared',
               '-Wab,-r4300_mul', '-mips2', '-o32']
    for include in ('conker/include', 'conker/include/2.0L', 'conker/include/2.0L/PR',
                    'conker/include/libc'):
        command.extend(('-I', relative(include)))
    command.extend(('-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2', '-D_MIPS_SZLONG=32',
                    *screen.PROFILES['owner'], '-Wo,-zdbug:' + str(mode),
                    '-o', 'trace.o', 'baseline.c'))
    result = subprocess.run(command, cwd=work, capture_output=True, text=True)
    log = result.stdout + result.stderr
    (work / 'debugger.txt').write_text(log)
    record = validate_trace(root, work, result.returncode, log)
    record.update(mode=mode, baseline=meta, source_sha256=hashlib.sha256(
                  (work / 'baseline.c').read_bytes()).hexdigest())
    (work / 'trace.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', type=int, choices=MODES, default=6)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    body = dict(screen.candidates())['flag-branches-captured']
    record = trace_uopt(root, root / 'conker/build/game-text-measurer-uopt-trace',
                        'mode-' + str(args.mode), body, args.mode)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
