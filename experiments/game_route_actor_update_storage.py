"""Test disjoint conversion/projection lifetimes, without invented qualifiers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_actor_update_extent as prior

source = prior.source
BUILD = 'conker/build/game-route-actor-update-storage'
SELECTED_NAME = 'error-explicit-call-snapshot'
RAW_SHA = 'baa6bce709baa949c1da3ee5a1b305677aa258f5837b26d77f91e74d95c8e2a6'
BINDING_SHA = '371dd26f78b2f1d162a24c1caa3f266de4c533513676530a343b0d66b72dcf2d'


def coordinate_carrier(body, name):
    for offset, value in ((8, 'D_800D239C'), (10, 'D_800D23A0'), (12, 'D_800D23A4')):
        marker = '            *(s16 *)(D_800D2104[actor[0x13F]] + %d) = (s32)%s;' % (offset, value)
        body = prior.prior.replace_once(body, marker,
            '            %s = (s32)%s;\n' % (name, value) + marker.replace('(s32)' + value, name))
    return body


def conversion_forms():
    body = prior.selected()
    for name in ('i', 'again'):
        yield 'converted-' + name, coordinate_carrier(body, name)
    value = prior.prior.replace_once(body, '    s8 temporary;\n', '    s32 temporary;\n')
    yield 'converted-rank-id32', coordinate_carrier(value, 'temporary')
    marker = '        if (recordIndex < D_800D2398) {\n'
    start = body.index(marker) + len(marker)
    stop = body.index('    } else {\n        *(f32 *)record = 0.0f;', start)
    value = body[:start] + coordinate_carrier(body[start:stop], 'recordIndex') + body[stop:]
    yield 'converted-dead-argument-control', value
    for name, declaration in (('converted', '    s32 converted;\n'),
                              ('converted[0]', '    s32 converted[1];\n')):
        value = prior.prior.replace_once(body, '    f32 gain;\n', '    f32 gain;\n' + declaration)
        yield 'converted-' + ('array' if '[' in name else 'scalar'), coordinate_carrier(value, name)


def projection_forms():
    body = prior.selected()
    marker = '    } else {\n        *(f32 *)record = 0.0f;'
    head, tail = body.split(marker)
    head = prior.prior.replace_once(head, '    f32 positionX;\n', '    f32 startZ;\n    f32 positionX;\n')
    tail = re.sub(r'\bgain\b', 'startZ', tail)
    body = head + marker + tail
    yield 'projection-separate-startZ', body
    for old, new in (('cursor', 'actor'), ('temporary', 'refresh'), ('i', 'active')):
        value = prior.prior.merge_names(body, ((old, new),))
        yield 'projection-startZ-reuse-' + old, value


def loop_forms():
    original = prior.selected()
    call = '            refresh = func_15088A08(record, -valueX);\n            again = 1;'
    early = prior.prior.replace_once(original, call,
        '            again = 1;\n            refresh = func_15088A08(record, -valueX);')
    yield 'loop-flag-before-call', early
    early = prior.prior.replace_once(original, call, '            refresh = func_15088A08(record, -valueX);')
    early = prior.prior.replace_once(early, '            previousError = absoluteError;\n',
        '            previousError = absoluteError;\n            again = 1;\n')
    yield 'loop-flag-before-step', early
    for name, body in (('late-flag', original), ('early-flag', early)):
        start = body.index('            valueX = (error * gain) / chordLength;')
        end = body.index('        iterations++;', start)
        body = body[:start] + re.sub(r'\bvalueX\b', 'absoluteError', body[start:end]) + body[end:]
        yield 'loop-absolute-step-' + name, body
        if name == 'early-flag':
            signed = prior.prior.replace_once(body,
                '    record[0x32] = record[0x33];\n    record[0x33] = D_800BE9E4;',
                '    *(s8 *)(record + 0x32) = *(s8 *)(record + 0x33);\n'
                '    *(s8 *)(record + 0x33) = D_800BE9E4;')
            yield 'loop-absolute-step-signed-ticks', signed
            start = signed.index('        do {\n            again = 1;')
            end = signed.index('        for (i = 0; i < D_800D2398; i++) {', start)
            yield 'loop-absolute-step-and-score', signed[:start] + re.sub(
                r'\bvalueX\b', 'absoluteError', signed[start:end]) + signed[end:]


def declaration_forms():
    body = dict(loop_forms())['loop-flag-before-step']
    body = prior.prior.replace_once(body, '    f32 gain;\n', '')
    body = prior.prior.replace_once(body, '    f32 valueX;\n', '')
    body = prior.prior.replace_once(body, '    f32 positionX;\n',
        '    f32 gain;\n    f32 startZ;\n    f32 positionX;\n')
    body = prior.prior.replace_once(body, '    f32 x[4];\n',
        '    f32 valueX;\n    f32 inverse;\n    f32 x[4];\n')
    body = prior.prior.replace_once(body, '    u8 *actor;\n', '    f32 pointZ;\n    u8 *actor;\n')
    body = prior.prior.replace_once(body,
        '        error = func_150498A4(z, 0, *(f32 *)(record + 8), &slopeZ);',
        '        pointZ = func_150498A4(z, 0, *(f32 *)(record + 8), &slopeZ);')
    body = prior.prior.replace_once(body,
        '        absoluteError = -1.0f / sqrtf(slopeX * slopeX + slopeZ * slopeZ);\n'
        '        slopeX *= absoluteError;\n        slopeZ *= absoluteError;',
        '        inverse = -1.0f / sqrtf(slopeX * slopeX + slopeZ * slopeZ);\n'
        '        slopeX *= inverse;\n        slopeZ *= inverse;')
    body = prior.prior.replace_once(body, 'valueX * slopeX + error * slopeZ', 'valueX * slopeX + pointZ * slopeZ')
    start = body.index('            valueX = (error * gain) / chordLength;')
    end = body.index('        iterations++;', start)
    body = body[:start] + re.sub(r'\bvalueX\b', 'inverse', body[start:end]) + body[end:]
    marker = '    } else {\n        *(f32 *)record = 0.0f;'
    head, tail = body.split(marker)
    body = head + marker + re.sub(r'\bgain\b', 'startZ', tail)
    yield 'decl-independent-float-roles', body
    for name, pairs in (
            ('bank-record', (('cursor', 'record'),)),
            ('rank-byte', (('temporary', 'refresh'),)),
            ('bank-record-rank-byte', (('cursor', 'record'), ('temporary', 'refresh'))),
            ('bank-actor-rank-byte', (('cursor', 'actor'), ('temporary', 'refresh')))):
        yield 'decl-' + name, prior.prior.merge_names(body, pairs)
    for name, counter in (('bank-record-byte-index', 'iterations'), ('bank-record-argument-index', 'active')):
        yield 'decl-' + name, prior.prior.merge_names(body, (('cursor', 'record'), ('i', counter)))


def byte_declaration_forms():
    original = dict(declaration_forms())['decl-independent-float-roles']
    for name, names, merge in (
            ('both-independent', ('temporary', 'iterations'), False),
            ('both-bank-record', ('temporary', 'iterations'), True),
            ('id-bank-record', ('temporary',), True),
            ('iterations-bank-record', ('iterations',), True)):
        body = original
        for variable in names:
            body = prior.prior.replace_once(body, '    s8 ' + variable + ';\n', '')
        body = prior.prior.replace_once(body, '    s8 refresh;\n',
            ''.join('    s8 ' + variable + ';\n' for variable in names) + '    s8 refresh;\n')
        if merge:
            body = prior.prior.merge_names(body, (('cursor', 'record'),))
        yield 'byte-decl-' + name, body


def packed_forms():
    original = dict(byte_declaration_forms())['byte-decl-both-independent']
    original = prior.prior.replace_once(original,
        '    s8 temporary;\n    s8 iterations;\n    s8 refresh;\n',
        '    s8 temporary;\n    s8 refresh;\n    s8 iterations;\n')
    for name, dtype in (('signed', 's8'), ('unsigned', 'u8')):
        body = prior.prior.replace_once(original, '    s32 again;\n', '')
        body = prior.prior.replace_once(body, '    s8 iterations;\n',
            '    s8 iterations;\n    %s again;\n' % dtype)
        yield 'packed-' + name + '-flag', body
        start = body.index('        do {\n            again = 1;')
        end = body.index('        for (i = 0; i < D_800D2398; i++) {', start)
        yield 'packed-' + name + '-flag-local-score', body[:start] + re.sub(
            r'\bvalueX\b', 'inverse', body[start:end]) + body[end:]
    body = prior.prior.replace_once(original, '        recordOffset = (u32)(D_800D2398 - 1);\n', '')
    yield 'packed-inline-rank-bound', prior.prior.replace_once(body,
        'i < (s32)recordOffset;', 'i < D_800D2398 - 1;')


def error_lifetime_forms():
    body = dict(packed_forms())['packed-signed-flag-local-score']
    body = prior.prior.replace_once(body,
        '    record[0x32] = record[0x33];\n    record[0x33] = D_800BE9E4;',
        '    *(s8 *)(record + 0x32) = *(s8 *)(record + 0x33);\n'
        '    *(s8 *)(record + 0x33) = D_800BE9E4;')
    yield 'error-signed-ticks', body
    yield 'error-register-view', prior.prior.registered(body, ('error',))
    start = body.index('        error = (slopeX * positionX + slopeZ * positionZ) + intercept;')
    end = body.index('        iterations++;', start)
    loop = re.sub(r'\berror\b', 'pointZ', body[start:end])
    loop = prior.prior.replace_once(loop, '            refresh = func_15088A08(record, -inverse);',
        '            error = pointZ;\n            refresh = func_15088A08(record, -inverse);\n            pointZ = error;')
    body = body[:start] + loop + body[end:]
    body = prior.prior.replace_once(body, '    func_15042D78(0x80);', '    error = pointZ;\n    func_15042D78(0x80);')
    yield 'error-explicit-call-snapshot', body
    yield 'error-register-call-snapshot', prior.prior.registered(body, ('pointZ',))


def projection_scale_forms():
    original = dict(error_lifetime_forms())['error-explicit-call-snapshot']
    marker = '    } else {\n        *(f32 *)record = 0.0f;'
    head, tail = original.split(marker)
    for name in ('gain', 'inverse'):
        body = prior.prior.replace_once(tail, '        *(f32 *)record = 1.0f;',
            '        %s = 1.0f;\n        *(f32 *)record = %s;' % (name, name))
        body = prior.prior.replace_once(body, 'if (1.0f < chordLength)', 'if (%s < chordLength)' % name)
        if name == 'gain':
            body = prior.prior.replace_once(body, 'absoluteError = 1.0f / chordLength;',
                'absoluteError = gain / chordLength;')
        else:
            body = prior.prior.replace_once(body, 'absoluteError = 1.0f / chordLength;',
                'absoluteError = inverse / chordLength;')
        yield 'projection-unit-' + name, head + marker + body


def offset_type_forms():
    original = dict(error_lifetime_forms())['error-explicit-call-snapshot']
    for name, signed_offset, byte_index in (('signed-offset', True, False),
            ('byte-index', False, True), ('signed-offset-byte-index', True, True)):
        body = original
        if signed_offset:
            body = prior.prior.replace_once(body, '    u32 recordOffset;', '    s32 recordOffset;')
            body = prior.prior.replace_once(body, 'recordOffset = (u32)recordIndex * 0x84u;',
                'recordOffset = (s32)((u32)recordIndex * 0x84u);')
            body = prior.prior.replace_once(body, 'recordOffset = (u32)(D_800D2398 - 1);',
                'recordOffset = D_800D2398 - 1;')
            body = prior.prior.replace_once(body, 'i < (s32)recordOffset;', 'i < recordOffset;')
        if byte_index:
            body = prior.prior.replace_once(body, '    s32 i;', '    s8 i;')
        yield 'type-' + name, body


GROUPS = dict(conversions=conversion_forms, projection=projection_forms, loop=loop_forms,
              declarations=declaration_forms, bytes=byte_declaration_forms, packed=packed_forms,
              error=error_lifetime_forms, unit=projection_scale_forms, types=offset_type_forms)


def selected():
    body = dict(error_lifetime_forms())[SELECTED_NAME]
    return prior.prior.replace_once(body,
        '        pointZ = (slopeX * positionX + slopeZ * positionZ) + intercept;',
        '        /* Reuse the sampled-Z carrier for the signed plane error. */\n'
        '        pointZ = (slopeX * positionX + slopeZ * positionZ) + intercept;')


def check_payload(raw, bindings):
    digest = hashlib.sha256(json.dumps(bindings, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if len(raw) != 2376 or hashlib.sha256(raw).hexdigest() != RAW_SHA or digest != BINDING_SHA:
        raise ValueError('Changed complete source-level local-home recovery or bindings')


def checked(obj):
    text, functions, relocations = source.parse_object(obj)
    f = functions[source.FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {at - f['value']: value for at, value in relocations.items()
                if f['value'] <= at < f['value'] + f['size']}
    check_payload(raw, bindings)
    return raw, bindings


def qualify(root, out):
    values = source.freeze(root, out)
    baseline, diagnostics = source.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected local-home qualification baseline')
    obj, words, row = source.measure(root, out, 'qualified-cursor', selected(), baseline)
    checked(obj)
    if (row['words'], row['frame'], row['differences'], row['diagnostics']) != (594, 456, 450, ''):
        raise ValueError('Changed local-home recovery shape')
    truth = list(struct.unpack_from('>604I', values['conker/conker.us.bin'], source.ROM))
    if words[:15] != truth[:15] or words[-11:] != truth[-11:]:
        raise ValueError('Changed recovered frame/save/argument layout')
    row.update(call_anchored_blocks=prior.call_blocks(truth, words), first15_words_exact=True,
        last11_words_exact=True, extent_restored=False, missing_words=10)
    (out / 'qualified-cursor.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def profile_screens(root, out):
    values = source.freeze(root, out)
    run = subprocess.run
    rows = []
    for opt, debug in (('-O2', '-g0'), ('-O1', '-g0')):
        def adjusted(argv, **kwargs):
            if argv[0] == str(root / 'ido/ido5.3_recomp/cc'):
                argv[argv.index('-O2')] = opt
                argv[argv.index('-g3')] = debug
            elif len(argv) > 1 and str(argv[1]).endswith('/asm_processor.py'):
                if '-O2' in argv:
                    argv[argv.index('-O2')] = opt
                if '-g3' in argv:
                    argv.remove('-g3')
            try:
                return run(argv, **kwargs)
            except subprocess.CalledProcessError as error:
                (out / (name + '-failure.json')).write_text(json.dumps(dict(command=argv,
                    exit=error.returncode, stdout=error.stdout, stderr=error.stderr), indent=2) + '\n')
                raise
        name = 'profile-' + opt[1:] + '-' + debug[1:]
        with patch.object(subprocess, 'run', side_effect=adjusted):
            baseline, diagnostics = source.prior.compile_profile(root, out,
                values['conker/src/game/generated_B3020.c'].decode(), name + '-before')
            if diagnostics:
                raise ValueError('Unexpected alternate-profile baseline diagnostics')
            _, words, row = source.measure(root, out, name, prior.selected(), baseline)
        row.update(optimization=opt, debug=debug, diagnostic_profile_not_original_flag_claim=True)
        prior.disassemble(out, name, words)
        rows.append(row)
        print(json.dumps({key: row[key] for key in ('name', 'words', 'frame', 'differences', 'raw_sha256',
            'diagnostics', 'neighbors')}), flush=True)
    (out / 'profile-screens.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def screen(root, out, group):
    values = source.freeze(root, out)
    baseline, diagnostics = source.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected storage screen baseline diagnostics')
    truth = list(struct.unpack_from('>604I', values['conker/conker.us.bin'], source.ROM))
    rows = []
    for name, body in GROUPS[group]():
        _, words, row = source.measure(root, out, name, body, baseline)
        row.update(call_anchored_blocks=prior.call_blocks(truth, words),
            first15_words_exact=words[:15] == truth[:15], last11_words_exact=words[-11:] == truth[-11:],
            incoming_argument_write_control_only=name == 'converted-dead-argument-control')
        prior.disassemble(out, name, words)
        rows.append(row)
        print(json.dumps({key: row[key] for key in ('name', 'words', 'frame', 'differences',
            'raw_sha256', 'diagnostics', 'neighbors', 'first15_words_exact', 'last11_words_exact')}), flush=True)
    (out / (group + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=GROUPS, default='conversions')
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[2], indent=2))
    elif args.profiles:
        profile_screens(root, root / BUILD)
    else:
        screen(root, root / BUILD, args.group)
