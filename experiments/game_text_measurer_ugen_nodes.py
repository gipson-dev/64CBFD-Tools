"""Fingerprint-locked, read-only UGEN load-node diagnostics in owned children."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from tools.experiments import game_text_measurer_uopt_trace as qualified

screen = qualified.screen
UGEN_SHA256 = 'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d'
INSTALLED = 'UGEN_NODE_PROBE_INSTALLED'
CHILD_EXIT = 'UGEN_NODE_CHILD_EXIT code=0'
REMOVED = 'UGEN_NODE_PROBE_REMOVED'
PREFIX = 'UGEN_NODE '
FIELDS = {'node', 'opcode', 'type_storage', 'raw36', 'raw40', 'raw44', 'raw48'}


def compiler_fingerprints(root):
    hashes = qualified.compiler_fingerprints(root)
    hashes['ugen'] = hashlib.sha256((root / 'ido/ido5.3_recomp/ugen').read_bytes()).hexdigest()
    return hashes


def node_events(log):
    events = []
    for line in log.splitlines():
        if not line.startswith(PREFIX):
            continue
        try:
            node = json.loads(line.removeprefix(PREFIX))
            if (not isinstance(node, dict) or node.keys() != FIELDS
                    or any(type(value) is not int or not 0 <= value <= 0xFFFFFFFF
                           for value in node.values())
                    or node['node'] == 0 or node['node'] % 4
                    or node['opcode'] > 255 or node['type_storage'] > 255
                    or (node['type_storage'] >> 5 == 3
                        and (node['raw44'] % 4 or node['raw44'] // 4 >= 72))):
                raise ValueError
        except (ValueError, TypeError) as error:
            raise ValueError('Malformed UGEN load-node event') from error
        events.append(node)
    return events


def debugger_script(root):
    program = json.dumps(str((root / 'ido/ido5.3_recomp/ugen').resolve()))
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
import json
program = ''' + program + '''
def exited(event):
    gdb.write('TRACE_EXIT inferior=%d code=%s\\n' % (event.inferior.num, getattr(event, 'exit_code', 'unknown')))
    if event.inferior.progspace.filename == program:
        gdb.write('UGEN_NODE_CHILD_EXIT code=%s\\n' % getattr(event, 'exit_code', 'unknown'))
gdb.events.exited.connect(exited)
class LoadNode(gdb.Breakpoint):
    def stop(self):
        if gdb.current_progspace().filename != program:
            raise gdb.GdbError('UGEN probe fired in a different compiler child')
        base, node = int(gdb.parse_and_eval('$rdi')), int(gdb.parse_and_eval('$edx'))
        inferior = gdb.selected_inferior()
        word = lambda address: int.from_bytes(inferior.read_memory(base + address, 4).tobytes(), 'little')
        byte = lambda address: int.from_bytes(inferior.read_memory(base + (address ^ 3), 1).tobytes(), 'little')
        record = dict(node=node, opcode=byte(node + 32), type_storage=byte(node + 33),
                      raw36=word(node + 36), raw40=word(node + 40), raw44=word(node + 44),
                      raw48=word(node + 48))
        gdb.write('UGEN_NODE ' + json.dumps(record) + '\\n')
        return False
end
catch exec
commands
silent
python
if gdb.current_progspace().filename == program:
    LoadNode('*0x430480', internal=True)
    gdb.write('UGEN_NODE_PROBE_INSTALLED\\n')
    gdb.execute('set follow-fork-mode parent')
end
continue
end
run
inferior 1
continue
python
for attempt in range(6):
    if not any(inferior.num == 1 and inferior.pid for inferior in gdb.inferiors()):
        break
    if gdb.selected_inferior().pid:
        raise gdb.GdbError('Unexpected live child; refusing to resume a failed compiler')
    for breakpoint in gdb.breakpoints() or ():
        if breakpoint.location == '*0x430480':
            breakpoint.delete()
            gdb.write('UGEN_NODE_PROBE_REMOVED\\n')
    gdb.execute('inferior 1')
    gdb.execute('continue')
else:
    raise gdb.GdbError('Bounded compiler-child handling exhausted')
end
info inferiors
'''


def validate_trace(root, work, exit_code, log):
    record = dict(exit_code=exit_code, code_unchanged=False, installable=False)
    receipt = work / 'trace.json'
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    obj = work / 'trace.o'
    lines = log.splitlines()
    if (exit_code or qualified.EXIT_MARKER not in lines
            or any(lines.count(marker) != 1 for marker in (INSTALLED, CHILD_EXIT, REMOVED))
            or not obj.is_file()
            or not obj.stat().st_size or 'Python Exception' in log
            or 'Error in sourced' in log):
        raise ValueError('UGEN trace failed, incomplete or missing object/probe')
    events = node_events(log)
    if not events:
        raise ValueError('UGEN load-node probe did not fire')
    positions = [index for index, line in enumerate(lines) if line.startswith(PREFIX)]
    if not (lines.index(INSTALLED) < min(positions) <= max(positions)
            < lines.index(CHILD_EXIT) < lines.index(REMOVED) < lines.index(qualified.EXIT_MARKER)):
        raise ValueError('UGEN probe events or cleanup outside owned child lifetime')
    expected = dict(qualified.COMPILERS, ugen=UGEN_SHA256)
    if compiler_fingerprints(root) != expected:
        raise ValueError('Prepared compiler fingerprint changed')
    before = screen.compiler.parse_object(work / 'baseline.o')
    after = screen.compiler.parse_object(obj)
    left, right = screen.compiler.sections(work / 'baseline.o'), screen.compiler.sections(obj)
    pools = sorted(name for name in left.keys() | right.keys()
                   if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')))
    if before != after or any(left.get(name) != right.get(name) for name in pools):
        raise ValueError('UGEN diagnostic changed text, functions, relocations or pools')
    record.update(code_unchanged=True, events=events, event_count=len(events),
                  compiler_sha256=expected, pool_sections=pools,
                  log_sha256=hashlib.sha256(log.encode()).hexdigest())
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    return record


def trace_nodes(root, out, name, body):
    root, out = Path(root).resolve(), Path(out).resolve()
    work = (out / name).resolve()
    if (Path(name).name != name or name in ('', '.', '..')
            or not work.is_relative_to(root / 'conker/build')):
        raise ValueError('Diagnostic name/output must be inside conker/build')
    if compiler_fingerprints(root) != dict(qualified.COMPILERS, ugen=UGEN_SHA256):
        raise ValueError('Prepared compiler fingerprint mismatch; do not use native addresses')
    debugger = shutil.which('gdb')
    if debugger is None:
        raise FileNotFoundError('Existing GDB required; this helper does not install it')
    work.mkdir(parents=True, exist_ok=True)
    meta, _ = screen.compile_candidate(root, work, 'baseline', body)
    (work / 'trace.o').unlink(missing_ok=True)
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
                    *screen.PROFILES['owner'], '-o', 'trace.o', 'baseline.c'))
    result = subprocess.run(command, cwd=work, capture_output=True, text=True)
    log = result.stdout + result.stderr
    (work / 'debugger.txt').write_text(log)
    record = validate_trace(root, work, result.returncode, log)
    record.update(baseline=meta, source_sha256=hashlib.sha256((work / 'baseline.c').read_bytes()).hexdigest())
    (work / 'trace.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', choices=('early', 'late'), default='late')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    key = 'capture-declaration-after-record' if args.candidate == 'early' else 'flag-branches-captured'
    record = trace_nodes(root, root / 'conker/build/game-text-measurer-ugen-nodes',
                         args.candidate, dict(screen.candidates())[key])
    print(json.dumps(dict(candidate=args.candidate, event_count=record['event_count'],
                         code_unchanged=record['code_unchanged'], baseline=record['baseline']), indent=2))


if __name__ == '__main__':
    main()
