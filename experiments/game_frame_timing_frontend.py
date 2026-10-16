"""Observe timing byte promotion and address carriers before UGEN emission."""
import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_frame_timing_fitting as source
from tools.experiments import game_text_measurer_frontend_trace as capture
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-frame-timing-frontend'


def procedure_records(records, procedure):
    starts = [i for i,r in enumerate(records) if r['name']=='ent' and r['block']==procedure]
    if len(starts) != 1:
        raise ValueError('Missing/duplicate timing procedure')
    result = []
    for row in records[starts[0]:]:
        if result and row['name']=='ent':
            raise ValueError('Timing procedure end missing')
        result.append(row)
        if row['name']=='end':
            return result
    raise ValueError('Incomplete timing procedure')


def phase_summary(record, content, obj, variant):
    expected = {
        'predecessor':(276,6,4,[],2,3,9),
        'unsigned-zero':(277,4,3,[5],2,3,8),
    }
    if variant not in expected:
        raise ValueError('Unknown timing phase summary variant')
    if record.get('code_unchanged') is not True:
        raise ValueError('Unqualified timing frontend capture')
    gate = 'if (divisor != 0U) {' if variant=='unsigned-zero' else 'if (divisor != 0) {'
    statements = {'byte':'divisor = D_800BEA0C;', 'step':'D_800BEA08 = D_800BE9E4;',
        'gate':gate, 'total':'total = D_800BE610 + (u32)D_800BE9E4;'}
    lines = content.splitlines()
    positions = {}
    for name, statement in statements.items():
        found = [i+1 for i,line in enumerate(lines) if line.strip()==statement]
        if len(found)!=1:
            raise ValueError('Missing/ambiguous timing source marker')
        positions[name] = found[0]
    def at(records, name, opcode, storage, dtype=None):
        result, current = [], None
        for row in records:
            if row['name']=='loc':
                current = row['words'][1]
            if current==positions[name] and row['name']==opcode and row['storage']==storage and (dtype is None or row['dtype']==dtype):
                result.append(row)
        return result
    def unique(rows):
        if len(rows)!=1:
            raise ValueError('Missing/duplicate timing phase binding')
        return rows[0]
    divisor = unique(at(record['records'], 'byte', 'str', 'M'))
    front = procedure_records(record['records'], divisor['block'])
    optimized = procedure_records(record['optimizer_records'], divisor['block'])
    total = unique(at(front, 'total', 'str', 'M', 'L'))
    residual = unique(at(front, 'total', 'lod', 'S', 'L'))
    byte = unique(at(optimized, 'byte', 'str', 'R', 'L'))
    step = unique(at(optimized, 'step', 'str', 'R', 'J'))
    gate_signed = unique(at(optimized, 'gate', 'str', 'R', 'J'))
    extra = at(optimized, 'gate', 'str', 'R', 'L')
    accumulator = unique(at(optimized, 'total', 'str', 'R', 'L'))
    address = unique([r for r in optimized if r['name']=='rlda' and r['storage']=='S'
        and r['block']==residual['block'] and r['offset']==residual['offset']])
    text, functions, relocations = parse_object(obj)
    f = functions[source.FUNCTION]
    materializations = [(a-f['value'], int.from_bytes(text[a:a+4], 'big')) for a,bindings in relocations.items()
        if f['value']<=a<f['value']+f['size'] and bindings==[('R_MIPS_HI16','D_800BE610')]]
    if len(materializations)!=1 or materializations[0][1]>>26!=15 or materializations[0][1]>>16&31!=address['words'][2]:
        raise ValueError('Timing optimized address does not match emitted carrier')
    if divisor['length']!=1 or divisor['dtype']!='L' or total['length']!=4 or not 0<=address['words'][2]<32:
        raise ValueError('Changed timing variable widths or address register')
    observed = (len(front),byte['offset'],gate_signed['offset'],[r['offset'] for r in extra],
        step['offset'],accumulator['offset'],address['words'][2])
    if (observed != expected[variant] or len(optimized)!=427 or divisor['offset']!=-2
            or total['offset']!=-8 or materializations[0][0]!=0x64):
        raise ValueError('Changed measured timing phase roles')
    return dict(variant=variant, source_lines=positions, frontend_procedure=divisor['block'],
        frontend_byte_home=divisor['offset'], frontend_total_home=total['offset'],
        frontend_procedure_records=len(front), optimized_procedure_records=len(optimized),
        optimized_byte_register=byte['offset'], optimized_signed_gate_register=gate_signed['offset'],
        optimized_extra_unsigned_gate_registers=[r['offset'] for r in extra],
        optimized_step_register=step['offset'], optimized_total_register=accumulator['offset'],
        optimized_residual_register=address['words'][2], emitted_residual_hi_offset=materializations[0][0],
        allocation_precedes_UGEN=True, whole_owner_ugen_events=record['complete']['event_count'],
        ugen_events_not_uniquely_attributed_to_target=True, installable=False)


def comparison_forms():
    for zero, one in ((True,False), (False,True), (True,True)):
        body = source.INITIAL
        if zero:
            body = body.replace('divisor != 0', 'divisor != 0U')
        if one:
            body = body.replace('divisor == 1', 'divisor == 1U')
        yield 'unsigned-' + ('zero-one' if zero and one else 'zero' if zero else 'one'), body


def step_word_forms():
    for name, access in (('unsigned-step-view', '(*(u32 *)&D_800BE9E4)'),
            ('unsigned-step-pointer', '(*stepWord)')):
        body = source.INITIAL
        if name.endswith('pointer'):
            body = body.replace('    u8 historyIndex;', '    u32 *stepWord = (u32 *)&D_800BE9E4;\n    u8 historyIndex;')
        body = body.replace('(f32)D_800BE9E4', '(f32)(s32)STEP_VALUE').replace(
            'D_800BEA08 = D_800BE9E4;', 'D_800BEA08 = (s32)STEP_VALUE;')
        if name.endswith('pointer'):
            head, body = body.split('    u8 historyIndex;', 1)
            body = head + '    u8 historyIndex;' + body.replace('D_800BE9E4', access)
        else:
            body = body.replace('D_800BE9E4', access)
        body = body.replace('STEP_VALUE', access)
        yield name, body


def switch_forms():
    body = source.INITIAL
    edits = (
        ('    if (divisor != 0) {\n        if (divisor == 1) {', '    switch (divisor) {\n        case 1: {'),
        ('        } else {\n            total = D_800BE610', '            break;\n        }\n        default: {\n            total = D_800BE610'),
        ('        }\n    } else {\n        D_800BE9A4 = (f32)D_800BE9E4 * 0.5f;\n    }',
            '            break;\n        }\n        case 0: {\n            D_800BE9A4 = (f32)D_800BE9E4 * 0.5f;\n            break;\n        }\n    }'))
    for old, new in edits:
        if body.count(old) != 1:
            raise ValueError('Unknown timing divider switch boundary')
        body = body.replace(old, new, 1)
    yield 'switch-byte', body
    yield 'switch-word', body.replace('switch (divisor)', 'switch ((u32)divisor)')


def global_divisor_forms():
    body = source.INITIAL
    for old,new in (('    u8 divisor;\n',''), ('    divisor = D_800BEA0C;\n',''),
            ('divisor != 0','D_800BEA0C != 0'), ('divisor == 1','D_800BEA0C == 1'),
            ('(f32)(u32)divisor','(f32)(u32)D_800BEA0C'),
            ('total >= divisor','total >= (u32)D_800BEA0C'),
            ('total / divisor','total / (u32)D_800BEA0C')):
        if body.count(old) != 1:
            raise ValueError('Unknown timing global divisor use')
        body = body.replace(old,new,1)
    yield 'global-byte-divisor', body


def home_forms():
    declarations = ('    u8 historyIndex;', '    u8 divisor;', '    u32 total;', '    f32 sum;', '    s32 i;')
    original = '\n'.join(declarations)
    if source.INITIAL.count(original) != 1:
        raise ValueError('Unknown timing local declarations')
    for name, order in (('divisor-first',(1,0,2,3,4)), ('total-first',(2,0,1,3,4)),
            ('index-first',(4,0,1,2,3)), ('sum-first',(3,0,1,2,4)),
            ('divisor-total-history',(1,2,0,3,4)), ('total-divisor-history',(2,1,0,3,4)),
            ('index-total-divisor',(4,2,1,0,3)), ('sum-index-total-divisor',(3,4,2,1,0))):
        yield name, source.INITIAL.replace(original, '\n'.join(declarations[i] for i in order), 1)


def signed_gate_forms():
    for kind in ('s32', 's16', 'u16'):
        yield kind + '-gate', source.INITIAL.replace('    u8 divisor;', '    ' + kind + ' divisor;', 1)


def capture_owner(root, variant='predecessor'):
    out = root / BUILD
    source.freeze(root, out)
    live = {key:hashlib.sha256((root/path).read_bytes()).hexdigest() for key,path in source.PATHS.items()}
    if live != source.BASELINE:
        raise ValueError('Changed timing frontend inputs')
    content = (out/'before-dispatch_owner').read_text()
    if variant == 'unsigned-zero':
        content = source.recovered_owner(content, dict(comparison_forms())[variant])
    elif variant != 'predecessor':
        raise ValueError('Unknown timing frontend variant')
    def normal(root, work, name, body):
        if body != content:
            raise ValueError('Changed timing frontend source')
        obj, diagnostics = source.build.compile_owner(root, work, body, name)
        if variant == 'predecessor':
            source.previous.checked_object(obj)
        else:
            text, functions, _ = parse_object(obj)
            f = functions[source.FUNCTION]
            if f['size'] != 760 or hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest() != '495cf7b8fcd35a9148c69f8dc39cf5c5da55c540dbe1a85493b43c380a10263c':
                raise ValueError('Changed unsigned-zero frontend object')
        text, functions, _ = parse_object(obj)
        f = functions[source.FUNCTION]
        digest = hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest()
        return dict(owner=source.OWNER, function=source.FUNCTION, diagnostics=diagnostics,
            raw_sha256=digest, flags=['-O2','-g3']), None
    with patch.object(capture.trace.screen, 'compile_candidate', normal), patch.dict(
            capture.trace.screen.PROFILES, owner=('-O2','-g3')):
        result = capture.capture_frontend(root, out, variant, content)
    if (out/variant/'baseline.c').read_text() != content:
        raise ValueError('Timing captured source changed')
    if {key:hashlib.sha256((root/path).read_bytes()).hexdigest() for key,path in source.PATHS.items()} != live:
        raise ValueError('Timing frontend capture changed live inputs')
    result['unchanged_live_inputs'] = live
    summary = phase_summary(result, content, out/variant/'baseline.o', variant)
    result['phase_summary'] = summary
    (out/variant/'frontend.json').write_text(json.dumps(result, indent=2)+'\n')
    (out/variant/'phase-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens', action='store_true')
    parser.add_argument('--step-words', action='store_true')
    parser.add_argument('--switches', action='store_true')
    parser.add_argument('--global-divisor', action='store_true')
    parser.add_argument('--homes', action='store_true')
    parser.add_argument('--signed-gates', action='store_true')
    parser.add_argument('--variant', choices=('predecessor','unsigned-zero'), default='predecessor')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.screens or args.step_words or args.switches or args.global_divisor or args.homes or args.signed_gates:
        for name, body in (signed_gate_forms() if args.signed_gates else home_forms() if args.homes else global_divisor_forms() if args.global_divisor else switch_forms() if args.switches else step_word_forms() if args.step_words else comparison_forms()):
            row = source.measure(root, root/BUILD, name, body)[2]
            print(json.dumps({k:row[k] for k in ('label','words','frame','differences','raw_sha256')}), flush=True)
        raise SystemExit(0)
    result = capture_owner(root, args.variant)
    print(json.dumps(dict(frontend_records=result['record_count'],
        optimizer_records=result['optimizer_record_count'],
        ugen_events=result['complete']['event_count'],
        code_unchanged=result['code_unchanged'], live_inputs=len(result['unchanged_live_inputs']),
        phase_summary=result['phase_summary']), indent=2))
