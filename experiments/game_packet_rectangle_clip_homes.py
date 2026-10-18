"""Observe clipping homes for the installed six-difference rectangle body."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_clip_phases as previous
from tools.experiments import game_packet_rectangle_compiler_trace as compiler
from tools.experiments import game_packet_rectangle_macro_lifetime as macro

BUILD = 'conker/build/game-packet-rectangle-clip-homes'
OWNER, FUNCTION, ENTRY, ROM, WORDS = (
    previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS)
INITIAL = SELECTED = previous.SELECTED
build = previous.previous.build
INPUTS = dict(previous.INPUTS, **{
    'conker/src/game/generated_C1D70.c': '27194aad3aa8465ab2fc1569ffdfa0672e4740efcbdd2c379652ca923eb6e32b',
    'conker/build/conker.us.elf': '42fd81f02acabbf952709ae45c24c310e48d68a658b8ed70fb4c4a5399ef475d',
    'tools/experiments/game_packet_rectangle_clip_phases.py': '85874200632a7ffe85df6bf994d95af76aa370940c1cc888a5cad8ba564adb71',
    'tools/experiments/game_packet_rectangle_compiler_trace.py': '901ac98ddb89fa16f8f8ad2c89dc665c91c3a4b21ab23f4a16db2c82d2f975df',
    'tools/experiments/game_actor_callback_frame_trace.py': 'b8e4ee3f4e562687dfd985b389a628cfec94142b0a2331c38e1a2af0cb62d717',
})
SIGNATURE = {previous.SELECTED_RAW_SHA256:
    '6f15273cc09304bf1324a83acc427bd35436e66e7d8fe2ed8599a5f9db458c57'}


def freeze(root, out):
    values = {}
    for relative, digest in INPUTS.items():
        raw = (root / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Changed current clipping input: ' + relative)
        values[relative] = raw
    out.mkdir(parents=True, exist_ok=True)
    snapshots = {('before-%02d' % i): raw for i, raw in enumerate(values.values())}
    snapshots['before-packet_owner'] = values['conker/src/game/generated_C1D70.c']
    snapshots['baseline.json'] = (json.dumps(INPUTS, indent=2) + '\n').encode()
    for name, raw in snapshots.items():
        path = out / name
        if path.exists() and path.read_bytes() != raw:
            raise ValueError('Changed current clipping fixture: ' + name)
        if not path.exists():
            path.write_bytes(raw)
    return values


def recovered_owner(before, body=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != INITIAL.split('\n', 1)[1].rstrip():
        raise ValueError('Unknown six-difference clipping body')
    return before[:lo] + body.split('\n', 1)[1].rstrip() + before[hi:]


def measure(root, out, label='selected', body=SELECTED):
    values = freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner(values['conker/src/game/generated_C1D70.c'].decode(), body), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    retail = list(struct.unpack_from('>346I', values['conker/conker.us.bin'], ROM))
    words, bindings, row = previous.facts(obj, data, functions, retail)
    row.update(raw_sha256=row['sha256'], diagnostics=diagnostics, bindings=bindings)
    if body == SELECTED:
        previous.checked_object(obj)
        if (row['words'], row['frame'], row['differences'], diagnostics) != (346, 136, 6, ''):
            raise ValueError('Changed six-difference compiler baseline')
    return obj, words, row


@contextmanager
def current_context():
    adapter = SimpleNamespace(FUNCTION=FUNCTION, build=build, freeze=freeze,
        measure=measure, recovered_owner=recovered_owner)
    with patch.object(compiler, 'source', adapter), patch.object(compiler, 'SIGNATURES', SIGNATURE):
        yield


def trace(root, out, label='selected-gates'):
    freeze(root, out)
    with current_context(), patch.object(compiler, 'debugger_script', macro.gate_script):
        return compiler.trace(root, out, label, SELECTED)


def allocation(root, out, label='selected'):
    freeze(root, out)
    with current_context():
        return compiler.trace_allocation(root, out, label, SELECTED, 5)


def checked_events(events, constraints):
    selections = [(18,0),(73,0),(107,1),(135,2),(145,3),(152,0),(235,0),(262,0),
        (303,1),(316,1),(335,2),(347,2),(349,1),(354,3),(355,4),(357,1),
        (381,2),(389,2),(396,4),(401,5)]
    route = ['spilltemps'] + ['spill-selected'] * 20 + ['spilltemps-return', 'gettemp', 'gettemp-return']
    if ([e['sequence'] for e in events] != list(range(1,25)) or
            [e['event'] for e in events] != route or len({(e['inferior'],e['pid']) for e in events}) != 1 or
            any(e['pid'] <= 0 or e['inferior'] <= 0 for e in events)):
        raise ValueError('Changed current clipping temporary route')
    pcs = {'spilltemps':0x450490, 'spill-selected':0x450902, 'spilltemps-return':0x48FC31,
        'gettemp':0x4174D0, 'gettemp-return':0x438F1C}
    picked = {row['expression']:row for row in constraints}
    members = [[] for _ in range(6)]
    blockers, direct = {}, {}
    for event in events:
        rows = macro.decoded_pool(event)
        if event['host_pc'] != pcs[event['event']]:
            raise ValueError('Changed current clipping native probe PC')
        if event['event'] == 'spill-selected':
            index, slot = selections[event['sequence'] - 2]
            raw = bytes.fromhex(event['ichain_raw'])
            if (event['index'] != index or event['temporary'] != rows[slot]['pointer'] or
                    len(raw) != 40 or not 0 < event['ichain'] < 0x80000000 or
                    struct.unpack_from('<I',raw)[0] & 65535 != index):
                raise ValueError('Changed current clipping expression identity/home')
            vector = event['forbidden']
            raw_vector = bytes.fromhex(vector['raw'])
            if vector['blocks'] != 4 or len(raw_vector) != 64 or not 0 < vector['pointer'] < 0x80000000 or any(raw_vector[4:]):
                raise ValueError('Changed current clipping forbidden vector')
            bits = struct.unpack_from('<I',raw_vector)[0]
            forbidden = [i for i in range(32) if bits & (0x80000000 >> i)]
            if any(i >= len(rows) for i in forbidden) or next(
                    r['index'] for r in rows if r['index'] not in forbidden) != slot:
                raise ValueError('Changed current clipping native first-fit decision')
            conflicts = set(picked[index]['interference'])
            if any(member in conflicts for member in members[slot]):
                raise ValueError('Current clipping home contradicts interference')
            if index in (347,354):
                blockers[index] = [sorted(conflicts.intersection(group)) for group in members[:slot]]
                direct[index] = dict(forbidden=forbidden, selected=slot, offset=rows[slot]['offset'])
            members[slot].append(index)
        elif event['event'].startswith('gettemp'):
            if event['size'] != 4 or event['caller'] != 0x438F1C or not 0 < event['destination'] < 0x80000000:
                raise ValueError('Changed current clipping gettemp boundary')
        elif event['caller'] != 0x48FC31:
            raise ValueError('Changed current clipping spilltemps boundary')
    before, after = events[-2:]
    old, new = macro.decoded_pool(before), macro.decoded_pool(after)
    if ([r['available'] for r in old] != [True]*4+[False]*2 or
            [r['available'] for r in new] != [False]+[True]*3+[False]*2 or
            before['destination'] != after['destination'] or after['result'] != new[0]['pointer']):
        raise ValueError('Changed current clipping gettemp reuse')
    if blockers != {347:[[73,235],[107]],354:[[235],[107,349],[347]]} or direct != {
            347:dict(forbidden=[0,1],selected=2,offset=-132),
            354:dict(forbidden=[0,1,2],selected=3,offset=-136)}:
        raise ValueError('Changed current clipping native/graph blockers')
    return dict(events=24, selected_expressions=20, blockers=blockers, native_gates=direct,
        intermediate_extent=144, emitted_M_extent=136, installable=False)


def validate(root, out):
    freeze(root, out)
    work = out / 'compiler-selected-gates'
    allocation_work = out / 'allocation-selected-5'
    with current_context():
        parsed = compiler.validate(root, work)
        allocated = compiler.validate_allocation(root, allocation_work)
    if (work / 'ugen-frame.gdb').read_text() != macro.gate_script(root, work):
        raise ValueError('Changed clipping gate observation script')
    lines = (work / 'debugger.txt').read_text().splitlines()
    events = [json.loads(line[10:]) for line in lines if line.startswith('RECT_TEMP ')]
    result = checked_events(events, allocated['constraints'])
    positions = [i for i, line in enumerate(lines) if line.startswith('RECT_TEMP ')]
    child = parsed['inputs'][0]['inferior']
    if (lines.count('RECT_TEMP_INSTALLED') != 1 or lines.count('RECT_TEMP_REMOVED') != 1 or
            not positions or events[0]['inferior'] != child or not
            lines.index('RECT_TEMP_INSTALLED') < min(positions) <= max(positions) <
            lines.index('TRACE_EXIT inferior=%d code=0' % child) < lines.index('RECT_TEMP_REMOVED')):
        raise ValueError('Invalid clipping temporary ownership/lifecycle')
    pid = events[0]['pid']
    if ('process %d is executing new program: %s'%(pid,(root/'ido/ido5.3_recomp/uopt').resolve()) not in lines or
            '[Inferior %d (process %d) exited normally]'%(child,pid) not in lines):
        raise ValueError('Clipping temporary events belong to the wrong compiler child')
    receipt = json.loads((work/'receipt.json').read_text())
    if tuple(receipt['baseline'][k] for k in ('words','frame','differences','raw_sha256','source_sha256',
            'isolated_matches_full_owner')) != (346,136,6,previous.SELECTED_RAW_SHA256,
            '7fd708773e4d996ecf3530d95b0976f2ff4e7f84bb0ec7dcbbae645f6b2c9e91',True):
        raise ValueError('Changed current clipping capture source/body')
    if compiler.signature(work / 'trace.o') != compiler.signature(allocation_work / 'trace.o'):
        raise ValueError('Clipping compiler/allocation bodies disagree')
    result.update(record_counts={name: len(records) for name, records in parsed['records'].items()},
        raw_sha256=previous.SELECTED_RAW_SHA256, differences=6, installable=False)
    (out / 'qualified-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def forms():
    yield 'predecessor', INITIAL
    corners = {
        'X': ('(s32)((u32)integerX << 2)',
            '(s32)((u32)((s32)((f32)widthAdjust + width - 1.0f) + integerX) << 2)',
            '(s32)(((u32)(s32)((f32)widthAdjust + width - 1.0f) << 2) + (u32)integerX)'),
        'Y': ('(s32)((u32)integerY << 2)',
            '(s32)((u32)((s32)(height - 1.0f) + integerY) << 2)',
            '(s32)(((u32)(s32)(height - 1.0f) << 2) + (u32)integerY)'),
    }
    for placement, anchor in (('before-flips','    if (packet->flipFlags != 0) {'),
            ('after-flips','    gSPScisTextureRectangle')):
        for roles in (('X',),('Y',),('X','Y')):
            body, assignments = INITIAL, ''
            for role in roles:
                low, high, quarter_high = corners[role]
                body = previous.replace_once(body, low, 'integer'+role)
                body = previous.replace_once(body, high, quarter_high)
                assignments += '    integer'+role+' = '+low+';\n'
            body = previous.replace_once(body, anchor, assignments+anchor)
            yield 'quarter-phase-'+placement+'-'+''.join(roles), body
        body = previous.replace_once(INITIAL, anchor, '    integerX = (s16)integerX;\n'+anchor)
        yield 'narrow-pixel-X-'+placement, body


def screens(root, out):
    rows = []
    for label, body in forms():
        obj, words, row = measure(root, out, label, body)
        if not rows:
            baseline, pools = obj, previous.normalized_pools(obj)
            baseline_words, different = words, set(row['different'])
        if previous.normalized_pools(obj) != pools:
            raise ValueError('Changed current clipping owner pools')
        row.update(label=label, source_sha256=hashlib.sha256(body.encode()).hexdigest(),
            neighbors=previous.same_functions(baseline,obj,(FUNCTION,)),
            old_exact_losses=sorted(set(row['different'])-different),
            new_exact_words=sorted(different-set(row['different'])), identical_to_predecessor=words==baseline_words)
        row.pop('bindings')
        rows.append(row)
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','old_exact_losses','new_exact_words')}),flush=True)
    (out/'screens.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('action', choices=('trace', 'allocation', 'validate','screens'))
    args = parser.parse_args()
    out = args.root / BUILD
    result = globals()[args.action](args.root, out)
    if args.action == 'allocation':
        result = {k:v for k,v in result.items() if k not in ('variables','constraints')}
    if args.action != 'screens':
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
