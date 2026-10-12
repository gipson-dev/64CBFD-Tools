"""Capture CFE/UOPT wire streams while preserving the complete normal compile."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_text_measurer_logic_candidates as logic
from tools.experiments import game_text_measurer_ugen_nodes as trace

CFE_SHA256 = 'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9'
PREFIX = 'FRONTEND_CAPTURE '
TABLE_PREFIX = 'UCODE_TABLES_CAPTURE '
OPTIMIZER_PREFIX = 'OPTIMIZER_CAPTURE '


def compiler_fingerprints(root):
    hashes = trace.compiler_fingerprints(root)
    hashes['cfe'] = hashlib.sha256((root / 'ido/ido5.3_recomp/cfe').read_bytes()).hexdigest()
    return hashes


def decode_ucode(payload, table, types):
    """Wire layout follows the prepared UGEN's readuinstr/ugetint routines."""
    if (not payload or len(payload) % 8 or not isinstance(table, list) or len(table) != 154
            or not isinstance(types, dict) or set(types) != {'dtypes', 'mtypes'}
            or any(not isinstance(value, str) or not value.isascii() for value in types.values())
            or len(types['dtypes']) != 20 or len(types['mtypes']) != 8):
        raise ValueError('Invalid ucode payload or descriptor/type tables')
    programs = []
    for opcode, entry in enumerate(table):
        if (not isinstance(entry, dict) or entry.get('opcode') != opcode or not isinstance(entry.get('name'), str)
                or not entry['name'].isascii() or not 1 <= len(entry['name']) <= 4
                or not isinstance(entry.get('descriptor'), list) or len(entry['descriptor']) != 19
                or any(type(value) is not int or not 0 <= value <= 255 for value in entry['descriptor'])
                or entry['descriptor'][15] not in (0, 1)
                or entry['descriptor'][16] not in (2, 4, 6, 8)):
            raise ValueError('Invalid ucode descriptor')
        fields = entry['descriptor'][:10]
        if 22 not in fields:
            # The prepared table has unused EOF/FOO slots, never valid stream records.
            if not any(entry['descriptor'][:16]) and entry['name'] in ('eof', 'foo'):
                programs.append(None)
                continue
            raise ValueError('Unterminated ucode operand descriptor')
        program = fields[:fields.index(22)]
        if any(value > 21 for value in program):
            raise ValueError('Unknown ucode operand descriptor')
        programs.append(program)
    records = []
    position = 0
    while position < len(payload):
        start = position
        opcode, type_storage = payload[start], payload[start + 1]
        if opcode >= len(table):
            raise ValueError('Unknown ucode opcode')
        entry = table[opcode]
        program = programs[opcode]
        if program is None:
            raise ValueError('Unsupported ucode operand descriptor')
        size = entry['descriptor'][16] * 4
        if start + size > len(payload):
            raise ValueError('Truncated ucode record')
        words = list(struct.unpack_from('>' + 'I' * (size // 4), payload, start))
        position += size
        constants = []
        if entry['descriptor'][15]:
            if len(payload) - position < 8:
                raise ValueError('Truncated ucode constant prefix')
            constants = list(struct.unpack_from('>2I', payload, position))
            position += 8
            dtype = type_storage & 31
            if ((0x004E8000 << dtype) & 0x80000000) or opcode == 0x13:
                padded = ((constants[0] + 7) // 8) * 8
                if position + padded > len(payload):
                    raise ValueError('Truncated ucode constant payload')
                position += padded
        dtype, storage = type_storage & 31, type_storage >> 5
        # LOC and other metadata records do not define every header operand.
        if 0 in program and (dtype >= len(types['dtypes']) or types['dtypes'][dtype] == '\0'):
            raise ValueError('Unknown ucode data type')
        records.append(dict(byte_offset=start, name=entry['name'], opcode=opcode,
                            type_storage=type_storage, operands=program,
                            dtype=types['dtypes'][dtype] if 0 in program else None,
                            storage=types['mtypes'][storage] if 1 in program else None,
                            level=words[0] & 65535 if 2 in program else None,
                            block=words[1] if any(value in program for value in (3, 4, 5)) else None,
                            words=words, constants=constants,
                            length=words[2] if 10 in program and len(words) > 2 else None,
                            offset=((words[3] ^ 0x80000000) - 0x80000000) if 13 in program and len(words) > 3 else None))
    if records[0]['name'] != 'bgn' or records[-1]['name'] != 'stp':
        raise ValueError('Incomplete ucode stream')
    return records


def debugger_script(root, work):
    script = trace.debugger_script(root)
    setup = '''from pathlib import Path
import hashlib
cfe_program = ''' + json.dumps(str((root / 'ido/ido5.3_recomp/cfe').resolve())) + '''
uopt_program = ''' + json.dumps(str((root / 'ido/ido5.3_recomp/uopt').resolve())) + '''
front_exits = []
optimizer_exits = []
optimizer_output = None
def front_exited(event):
    if event.inferior.progspace.filename == cfe_program:
        front_exits.append(getattr(event, 'exit_code', 'unknown'))
    if event.inferior.progspace.filename == uopt_program:
        optimizer_exits.append(getattr(event, 'exit_code', 'unknown'))
gdb.events.exited.connect(front_exited)
'''
    script = script.replace('import json\nprogram =', 'import json\n' + setup + 'program =', 1)
    capture = '''if gdb.current_progspace().filename == uopt_program:
    if front_exits != [0]:
        raise gdb.GdbError('CFE producer did not complete successfully')
    inferior = gdb.selected_inferior()
    argv = Path('/proc/%d/cmdline' % inferior.pid).read_bytes().rstrip(b'\\0').split(b'\\0')
    arguments = [argument.decode() for argument in argv]
    inputs = [Path(argument) for argument in arguments if argument.startswith('/tmp/ctmf')]
    if len(inputs) != 1 or not inputs[0].is_file() or inputs[0].is_symlink():
        raise gdb.GdbError('No unique regular owned CFE input')
    optimizer_output = Path(arguments[arguments.index(str(inputs[0])) + 1])
    if not str(optimizer_output).startswith('/tmp/ctmo'):
        raise gdb.GdbError('Unexpected owned UOPT output')
    payload = inputs[0].read_bytes()
    if not payload:
        raise gdb.GdbError('Empty CFE input')
    Path(''' + json.dumps(str(work / 'frontend.ucode')) + ''').write_bytes(payload)
    gdb.write('FRONTEND_CAPTURE ' + json.dumps(dict(pid=inferior.pid, inferior=inferior.num,
              argv=arguments, input=str(inputs[0]), bytes=len(payload),
              optimizer_output=str(optimizer_output),
              sha256=hashlib.sha256(payload).hexdigest(), producer_exits=front_exits)) + '\\n')
if gdb.current_progspace().filename == program:
    if optimizer_exits != [0] or optimizer_output is None or not optimizer_output.is_file() or optimizer_output.is_symlink():
        raise gdb.GdbError('UOPT producer did not complete successfully')
    inferior = gdb.selected_inferior()
    arguments = [argument.decode() for argument in Path('/proc/%d/cmdline' % inferior.pid).read_bytes().rstrip(b'\\0').split(b'\\0')]
    if str(optimizer_output) not in arguments:
        raise gdb.GdbError('UGEN does not consume the captured UOPT output')
    payload = optimizer_output.read_bytes()
    if not payload:
        raise gdb.GdbError('Empty UOPT output')
    Path(''' + json.dumps(str(work / 'optimizer.ucode')) + ''').write_bytes(payload)
    gdb.write('OPTIMIZER_CAPTURE ' + json.dumps(dict(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                    input=str(optimizer_output), argv=arguments, producer_exits=optimizer_exits)) + '\\n')
'''
    script = script.replace('if gdb.current_progspace().filename == program:\n',
                            capture + 'if gdb.current_progspace().filename == program:\n', 1)
    tables = '''        table_path = Path(''' + json.dumps(str(work / 'ucode-table.json')) + ''')
        if not table_path.exists():
            entries = [dict(opcode=opcode,
                            name=bytes(byte(0x10005b40 + opcode * 4 + i) for i in range(4)).decode('ascii').strip(),
                            descriptor=[byte(0x1001a6c0 + opcode * 19 + i) for i in range(19)])
                       for opcode in range(154)]
            table_path.write_text(json.dumps(entries, indent=2) + '\\n')
            Path(''' + json.dumps(str(work / 'ucode-types.json')) + ''').write_text(json.dumps(dict(
                dtypes=bytes(byte(0x10005db0 + i) for i in range(20)).decode('ascii'),
                mtypes=bytes(byte(0x10005dc4 + i) for i in range(8)).decode('ascii'))) + '\\n')
            gdb.write('UCODE_TABLES_CAPTURE ' + json.dumps(dict(
                descriptors=hashlib.sha256(table_path.read_bytes()).hexdigest(),
                types=hashlib.sha256(Path(''' + json.dumps(str(work / 'ucode-types.json')) + ''').read_bytes()).hexdigest())) + '\\n')
'''
    return script.replace('        record = dict(node=node,', tables + '        record = dict(node=node,', 1)


def validate_capture(root, work, log, complete):
    receipt = work / 'frontend.json'
    record = dict(code_unchanged=False, installable=False)
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    lines = log.splitlines()
    captures = [json.loads(line.removeprefix(PREFIX)) for line in lines if line.startswith(PREFIX)]
    if (len(captures) != 1 or not complete.get('code_unchanged')
            or complete.get('installable') is not False):
        raise ValueError('Incomplete or missing frontend capture')
    trace.validate_trace(root, work, complete.get('exit_code', 1), log)
    capture = captures[0]
    if (not isinstance(capture, dict) or set(capture) != {'pid', 'inferior', 'argv', 'input', 'optimizer_output', 'bytes', 'sha256', 'producer_exits'}
            or any(type(capture[key]) is not int or capture[key] <= 0 for key in ('pid', 'inferior', 'bytes'))
            or not isinstance(capture['argv'], list) or not all(isinstance(arg, str) for arg in capture['argv'])
            or not isinstance(capture['sha256'], str)):
        raise ValueError('Malformed frontend capture')
    producer, consumer = capture.get('producer_exits'), capture.get('inferior')
    if (producer != [0] or type(consumer) is not int
            or 'TRACE_EXIT inferior=%d code=0' % consumer not in lines
            or trace.qualified.EXIT_MARKER not in lines):
        raise ValueError('Frontend producer/consumer/driver did not complete')
    table_events = [json.loads(line.removeprefix(TABLE_PREFIX)) for line in lines if line.startswith(TABLE_PREFIX)]
    if (len(table_events) != 1
            or not lines.index(next(line for line in lines if line.startswith(PREFIX)))
            < lines.index('TRACE_EXIT inferior=%d code=0' % consumer)
            < lines.index(trace.INSTALLED)
            < lines.index(next(line for line in lines if line.startswith(TABLE_PREFIX)))
            < lines.index(trace.CHILD_EXIT)):
        raise ValueError('Missing or misordered frontend descriptor probe')
    if compiler_fingerprints(root) != dict(trace.qualified.COMPILERS, ugen=trace.UGEN_SHA256, cfe=CFE_SHA256):
        raise ValueError('Prepared compiler fingerprint changed')
    payload = (work / 'frontend.ucode').read_bytes()
    if (not payload or len(payload) != capture.get('bytes')
            or hashlib.sha256(payload).hexdigest() != capture.get('sha256')):
        raise ValueError('Frontend capture hash/size mismatch')
    table_data, type_data = (work / 'ucode-table.json').read_bytes(), (work / 'ucode-types.json').read_bytes()
    if table_events[0] != dict(descriptors=hashlib.sha256(table_data).hexdigest(), types=hashlib.sha256(type_data).hexdigest()):
        raise ValueError('Captured ucode tables changed')
    table, types = json.loads(table_data), json.loads(type_data)
    records = decode_ucode(payload, table, types)
    optimizer_events = [json.loads(line.removeprefix(OPTIMIZER_PREFIX)) for line in lines if line.startswith(OPTIMIZER_PREFIX)]
    if len(optimizer_events) != 1:
        raise ValueError('Missing optimizer capture')
    optimizer_position = lines.index(next(line for line in lines if line.startswith(OPTIMIZER_PREFIX)))
    if not lines.index('TRACE_EXIT inferior=%d code=0' % consumer) < optimizer_position < lines.index(trace.INSTALLED):
        raise ValueError('Optimizer capture outside producer/consumer lifetime')
    optimizer = optimizer_events[0]
    optimized_payload = (work / 'optimizer.ucode').read_bytes()
    if (optimizer.get('producer_exits') != [0] or optimizer.get('input') != capture['optimizer_output']
            or capture['optimizer_output'] not in optimizer.get('argv', [])
            or len(optimized_payload) != optimizer.get('bytes')
            or hashlib.sha256(optimized_payload).hexdigest() != optimizer.get('sha256')):
        raise ValueError('Optimizer capture provenance/hash/size mismatch')
    optimized_records = decode_ucode(optimized_payload, table, types)
    record.update(complete=complete, frontend=capture, optimizer=optimizer, optimizer_records=optimized_records,
                  optimizer_record_count=len(optimized_records), cfe_sha256=CFE_SHA256,
                  code_unchanged=True, records=records, record_count=len(records))
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    return record


def capture_frontend(root, out, name, body):
    root, out = Path(root).resolve(), Path(out).resolve()
    work = (out / name).resolve()
    if (Path(name).name != name or name in ('', '.', '..')
            or not work.is_relative_to(root / 'conker/build')):
        raise ValueError('Frontend output must stay inside conker/build')
    if compiler_fingerprints(root) != dict(trace.qualified.COMPILERS, ugen=trace.UGEN_SHA256, cfe=CFE_SHA256):
        raise ValueError('Prepared compiler fingerprint mismatch')
    work.mkdir(parents=True, exist_ok=True)
    for filename in ('frontend.ucode', 'optimizer.ucode', 'ucode-table.json', 'ucode-types.json', 'frontend.json'):
        (work / filename).unlink(missing_ok=True)
    script = debugger_script(root, work)
    with patch.object(trace, 'debugger_script', return_value=script):
        complete = trace.trace_nodes(root, out, name, body)
    log = (work / 'debugger.txt').read_text()
    return validate_capture(root, work, log, complete)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[2]
    body = dict(logic.carrier_candidates())['carrier-simple-named']
    record = capture_frontend(root, root / 'conker/build/game-text-measurer-frontend', 'simple-named', body)
    print(json.dumps(dict(baseline=record['complete']['baseline'], bytes=record['frontend']['bytes'],
                         records=record['record_count'], optimizer_bytes=record['optimizer']['bytes'],
                         optimizer_records=record['optimizer_record_count'], code_unchanged=record['code_unchanged']), indent=2))


if __name__ == '__main__':
    main()
