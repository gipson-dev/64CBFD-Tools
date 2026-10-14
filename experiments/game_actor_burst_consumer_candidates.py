"""Recover the complete burst consumer, including its old-value count branch."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_burst_packet_candidates as packet
from tools.experiments import game_record_constructor_candidates as compiler

PROFILES = dict(compiler.PROFILES, retail_no_unroll=('-O2', '-g3', '-Wo,-loopunroll,0'))

ENTRY, ROM, WORDS = 0x151A6F00, 0x1D43B0, 315
FUNCTION = 'func_151A6F00'
SOURCE = 'conker/src/game/generated_1D43B0.c'
ORIGINAL = 's32 func_151A6F00() {\n    return 0;\n}'
MARKER = 'extern s32 D_800BE9E4;'
RECORD = packet.RECORD + '''
typedef struct { f32 x, y, z; } BurstVector1D43B0;
typedef struct {
    f32 field00, field04, field08, field0C;
    f32 rotation[3], scale[3];
    BurstVector1D43B0 position, velocity;
    f32 field40, field44, field48, field4C;
    u32 flags;
    s16 duration, id;
    u8 field58, reserved59[3];
    u32 field5C;
    u8 field60, field61, field62, field63;
    u8 field64, field65, field66, field67, field68;
    u8 reserved69, field6A, reserved6B;
    u32 field6C;
    u8 field70, reserved71;
    s16 field72, field74;
    u8 reserved76[2];
} BurstCreationDescriptor1D43B0;
typedef struct {
    f32 field00;
    u8 *animation;
    u8 field08, field09;
    s16 field0A, field0C;
    u8 reserved0E[2];
} BurstExtra1D43B0;
typedef struct {
    f32 *x, *y, *z;
    f32 rate, parameter;
    s16 duration;
    u8 flags, kind;
    u8 reserved18[4];
} BurstAnimationPacket1D43B0;
typedef char BurstDescriptorSize1D43B0[(sizeof(BurstCreationDescriptor1D43B0) == 0x78) ? 1 : -1];
typedef char BurstExtraSize1D43B0[(sizeof(BurstExtra1D43B0) == 16) ? 1 : -1];
typedef char BurstAnimationSize1D43B0[(sizeof(BurstAnimationPacket1D43B0) == 28) ? 1 : -1];
'''
DECLARATIONS = '''s32 func_150ADA20(void);
f32 func_150ADA68(void);
f32 func_151423D8(u8);
void *func_15132A4C(void *, s32, s32, s32, u8, s32);
void *func_15134908(void *, s32, u8, s32);
void *memcpy(void *, const void *, unsigned int);
extern f32 D_800A8DC0;
extern f32 D_800A8DC4;
'''
SYMBOLS = dict(func_150ADA20=0x150ADA20, func_150ADA68=0x150ADA68,
    func_151423D8=0x151423D8, func_15132A4C=0x15132A4C,
    func_15134908=0x15134908, memcpy=0x10022EC0,
    D_800A8DC0=0x800A8DC0, D_800A8DC4=0x800A8DC4)
LOCALS = '''    BurstCreationDescriptor1D43B0 descriptor;
    BurstExtra1D43B0 payload;
    f32 retainedScale;
    f32 cosine0, sine0, cosine1, sine1;
    f32 radius, horizontal;
    f32 planarSpeed, verticalSpeed;
    f32 speed, directedSpeed;
    f32 horizontalSpeed, scaleValue;
    BurstAnimationPacket1D43B0 animation;
    u8 *created;
    BurstExtra1D43B0 *attached;
    u8 *animationResult;
    u8 angle0, angle1;
    u8 mode = kind;
    u8 player = slot;
    s16 remaining = params->count;'''
BASE = '''void func_151A6F00(ActorBurstPacket97AA0 *params, s32 kind, s32 slot, s32 context) {
''' + LOCALS + '''

    descriptor.scale[0] = 1.0f;
    descriptor.scale[1] = 1.0f;
    descriptor.scale[2] = 1.0f;
    descriptor.flags = 0x21E9;
    descriptor.field58 = 0;
    descriptor.id = 0x1B;
    descriptor.rotation[0] = 0.0f;
    descriptor.rotation[1] = 0.0f;
    descriptor.rotation[2] = 0.0f;
    descriptor.field44 = 0.0f;
    descriptor.duration = params->duration;
    descriptor.field04 = D_800A8DC0;
    payload.field00 = -18.0f;
    payload.field08 = params->unk54;
    payload.field09 = params->unk55;
    payload.field0A = params->unk56;
    descriptor.field5C = 0;
    descriptor.field60 = 255;
    descriptor.field61 = 1;
    descriptor.field62 = 5;
    descriptor.field63 = 4;
    descriptor.field64 = 0;
    descriptor.field65 = 0;
    descriptor.field66 = 1;
    descriptor.field67 = 0;
    descriptor.field68 = 0;
    descriptor.field6A = 0;
    descriptor.field6C = 0;
    descriptor.field70 = 0;
    descriptor.field72 = 0x20;
    descriptor.field74 = 7;
    payload.field0C = params->unk58;
    while (remaining--) {
        angle0 = (u32)func_150ADA20() % (u32)(params->range0 + 1) + params->angle0;
        angle1 = (u32)func_150ADA20() % (u32)(params->range1 + 1) + params->angle1;
        cosine0 = func_151423D8((angle0 - 64) & 255);
        sine0 = func_151423D8(angle0);
        cosine1 = func_151423D8((angle1 - 64) & 255);
        sine1 = func_151423D8(angle1);
        radius = func_150ADA68() * params->radius;
        horizontal = radius * sine1;
        descriptor.position.x = params->position[0] + horizontal * cosine0;
        descriptor.position.y = params->position[1] - radius * cosine1;
        descriptor.position.z = params->position[2] + horizontal * sine0;
        switch (mode) {
            case 0:
                planarSpeed = func_150ADA68() * params->speedRange + params->speed;
                verticalSpeed = func_150ADA68() * params->unk2C + params->unk28;
                descriptor.velocity.x = planarSpeed * cosine0;
                descriptor.velocity.y = verticalSpeed;
                descriptor.velocity.z = planarSpeed * sine0;
                break;
            case 1:
                speed = func_150ADA68() * params->speedRange + params->speed;
                horizontalSpeed = speed * sine1;
                descriptor.velocity.x = horizontalSpeed * cosine0;
                descriptor.velocity.y = -speed * cosine1;
                descriptor.velocity.z = horizontalSpeed * sine0;
                break;
            case 2:
                descriptor.velocity = *(BurstVector1D43B0 *)params->direction;
                break;
            case 3:
                directedSpeed = func_150ADA68() * params->speedRange + params->speed;
                descriptor.velocity.x = params->direction[0] * directedSpeed;
                descriptor.velocity.y = params->direction[1] * directedSpeed;
                descriptor.velocity.z = params->direction[2] * directedSpeed;
                break;
        }
        scaleValue = func_150ADA68() * params->scaleRange + params->scale;
        descriptor.field0C = scaleValue;
        descriptor.field08 = scaleValue;
        retainedScale = scaleValue;
        descriptor.field00 = scaleValue * 30.0f;
        descriptor.field4C = func_150ADA68() * params->unk48 + params->unk44;
        descriptor.field40 = func_150ADA68() * params->unk50 + params->unk4C;
        descriptor.field48 = func_150ADA68() * params->unk50 + params->unk4C;
        created = func_15132A4C(&descriptor, 0, 0, sizeof(payload), player, context);
        if (created != NULL) {
            attached = (BurstExtra1D43B0 *)(created + 0x170);
            memcpy(attached, &payload, sizeof(payload));
            animation.x = (f32 *)(created + 0x38);
            animation.y = (f32 *)(created + 0x3C);
            animation.z = (f32 *)(created + 0x40);
            animation.rate = 15.0f * descriptor.field0C;
            animation.duration = 300;
            animation.flags = 0;
            animation.kind = 1;
            animation.parameter = D_800A8DC4;
            attached->animation = NULL;
            animationResult = func_15134908(&animation, 4, player, context);
            attached->animation = animationResult;
            if (animationResult != NULL) {
                memcpy(animationResult + 0x40, &retainedScale, sizeof(retainedScale));
            }
        }
    }
}'''


def reused_temporaries(speed=True, horizontal=True, result=True):
    body = BASE
    if speed:
        body = body.replace('    f32 planarSpeed, verticalSpeed;', '    f32 verticalSpeed;').replace(
            '    f32 speed, directedSpeed;', '    f32 speed;').replace('planarSpeed', 'speed').replace('directedSpeed', 'speed')
    if horizontal:
        body = body.replace('    f32 horizontalSpeed, scaleValue;', '    f32 scaleValue;').replace('horizontalSpeed', 'horizontal')
    if result:
        body = body.replace('    u8 *animationResult;\n', '').replace('animationResult', 'created')
    return body


def byte_arguments(body, angles_first=False):
    body = body.replace('s32 kind, s32 slot', 'u8 kind, u8 slot').replace(
        '    u8 mode = kind;\n', '').replace('    u8 player = slot;\n', '')
    body = body.replace('switch (mode)', 'switch (kind)').replace('player, context', 'slot, context')
    if angles_first:
        body = body.replace('    u8 angle0, angle1;\n', '').replace(
            '    BurstCreationDescriptor1D43B0 descriptor;',
            '    u8 angle0, angle1;\n    BurstCreationDescriptor1D43B0 descriptor;')
    return body


def structured_forms():
    for reuse_horizontal, if_chain, chained_scale in itertools.product((False, True), repeat=3):
        body = byte_arguments(reused_temporaries(True, reuse_horizontal, False), True)
        body = body.replace('u8 angle0, angle1;', 'u32 angle0, angle1;')
        for axis in (0, 1):
            expression = '(u32)func_150ADA20() %% (u32)(params->range%d + 1) + params->angle%d' % (axis, axis)
            body = body.replace(expression + ';', '(' + expression + ') & 255;')
        if if_chain:
            start, tail = body.split('        switch (kind) {\n', 1)
            switch, tail = tail.split('        scaleValue = ', 1)
            branches = []
            for kind in range(4):
                code = switch.split('            case %d:\n' % kind, 1)[1].split('                break;', 1)[0]
                branches.append('        %sif (kind == %d) {\n' % ('else ' if kind else '', kind) + code + '        }\n')
            body = start + ''.join(branches) + '        scaleValue = ' + tail
        if chained_scale:
            body = body.replace('    f32 scaleValue;\n', '').replace(
                '    f32 horizontalSpeed, scaleValue;', '    f32 horizontalSpeed;')
            body = body.replace('        scaleValue = func_150ADA68() * params->scaleRange + params->scale;\n'
                '        descriptor.field0C = scaleValue;\n        descriptor.field08 = scaleValue;\n'
                '        retainedScale = scaleValue;\n        descriptor.field00 = scaleValue * 30.0f;',
                '        retainedScale = descriptor.field08 = descriptor.field0C =\n'
                '            func_150ADA68() * params->scaleRange + params->scale;\n'
                '        descriptor.field00 = retainedScale * 30.0f;')
        yield 'structured-horizontal%d-if%d-chain%d' % (reuse_horizontal, if_chain, chained_scale), body


SEMANTIC = dict(structured_forms())['structured-horizontal0-if0-chain1']


def private_layout_forms():
    for float_first, pointers_first in itertools.product((False, True), repeat=2):
        body = SEMANTIC
        if float_first:
            body = body.replace('    f32 horizontalSpeed;\n', '').replace(
                '    BurstExtra1D43B0 payload;', '    f32 horizontalSpeed;\n    BurstExtra1D43B0 payload;')
        if pointers_first:
            body = body.replace('    u8 *created;\n', '').replace('    BurstExtra1D43B0 *attached;\n', '').replace(
                '    BurstAnimationPacket1D43B0 animation;',
                '    u8 *created;\n    BurstExtra1D43B0 *attached;\n    BurstAnimationPacket1D43B0 animation;')
        yield 'private-float%d-pointers%d' % (float_first, pointers_first), body


PRIVATE_SELECTED = dict(private_layout_forms())['private-float1-pointers1']


def branch_scratch_forms():
    for planar, radial, horizontal in itertools.product((False, True), repeat=3):
        if not (planar or radial or horizontal):
            continue
        body = PRIVATE_SELECTED
        for kind in (0, 1, 3):
            if not (planar if kind == 0 else radial):
                continue
            marker = '            case %d:\n' % kind
            start, tail = body.split(marker, 1)
            branch, tail = tail.split('                break;', 1)
            scratch = 'sine1' if kind == 0 else 'radius'
            branch = branch.replace('                speed = ', '                %s = ' % scratch)
            branch = branch.replace('= speed *', '= %s *' % scratch).replace(
                '= -speed *', '= -%s *' % scratch).replace('* speed;', '* %s;' % scratch)
            body = start + marker + branch + '                break;' + tail
        if planar and radial:
            body = body.replace('    f32 speed;\n', '')
        if horizontal:
            body = body.replace('    f32 horizontalSpeed;\n', '').replace('horizontalSpeed', 'horizontal')
            body = body.replace('    f32 radius, horizontal;', '    f32 horizontal;').replace(
                '    BurstExtra1D43B0 payload;', '    f32 radius;\n    BurstExtra1D43B0 payload;')
        yield 'branch-scratch-planar%d-radial%d-horizontal%d' % (planar, radial, horizontal), body


BRANCH_SELECTED = dict(branch_scratch_forms())['branch-scratch-planar0-radial1-horizontal0']


def branch_angle_forms():
    expressions = ('(angle%d - 64) & 255', 'angle%d - 64', '(u8)(angle%d - 64)')
    for first, third in itertools.product(range(3), repeat=2):
        body = BRANCH_SELECTED
        for axis, choice in ((0, first), (1, third)):
            body = body.replace('func_151423D8((angle%d - 64) & 255)' % axis,
                'func_151423D8(%s)' % (expressions[choice] % axis))
        yield 'branch-angle-first%d-third%d' % (first, third), body


LIFETIME_SELECTED = dict(branch_angle_forms())['branch-angle-first1-third1']


def branch_flow_forms():
    for goto, braces, all_cases in itertools.product((False, True), repeat=3):
        if not (goto or braces):
            continue
        body = LIFETIME_SELECTED
        for kind in range(4) if all_cases else (0, 1):
            marker = '            case %d:\n' % kind
            start, tail = body.split(marker, 1)
            branch, tail = tail.split('                break;', 1)
            exit_statement = 'goto velocityReady;' if goto else 'break;'
            if braces:
                branch = '                {\n' + branch + '                }\n'
            body = start + marker + branch + '                ' + exit_statement + tail
        if goto:
            body = body.replace('        retainedScale =', 'velocityReady:\n        retainedScale =')
        yield 'branch-flow-goto%d-braces%d-all%d' % (goto, braces, all_cases), body
    start, tail = LIFETIME_SELECTED.split('        switch (kind) {\n', 1)
    switch, tail = tail.split('        retainedScale =', 1)
    branches = []
    for kind in range(4):
        branch = switch.split('            case %d:\n' % kind, 1)[1].split('                break;', 1)[0]
        branches.append('        %sif (kind == %d) {\n' % ('else ' if kind else '', kind) + branch + '        }\n')
    yield 'branch-flow-if-chain', start + ''.join(branches) + '        retainedScale =' + tail


def initialization_forms():
    for duration_first, payload_early in itertools.product((False, True), repeat=2):
        body = LIFETIME_SELECTED
        if duration_first:
            body = body.replace('    descriptor.duration = params->duration;\n', '').replace(
                '    descriptor.id =', '    descriptor.duration = params->duration;\n    descriptor.id =')
        if payload_early:
            body = body.replace('    payload.field0C = params->unk58;\n', '').replace(
                '    descriptor.field5C =', '    payload.field0C = params->unk58;\n    descriptor.field5C =')
        yield 'initialization-duration%d-payload%d' % (duration_first, payload_early), body


INITIALIZATION_SELECTED = dict(initialization_forms())['initialization-duration1-payload1']
SELECTED = INITIALIZATION_SELECTED


def velocity_store_forms():
    for comma, scalar_pointer, all_cases in itertools.product((False, True), repeat=3):
        if not (comma or scalar_pointer):
            continue
        body = INITIALIZATION_SELECTED
        for kind in (0, 1, 3) if all_cases else (0, 1):
            marker = '            case %d:\n' % kind
            start, tail = body.split(marker, 1)
            branch, tail = tail.split('                break;', 1)
            if scalar_pointer:
                for axis, component in enumerate(('x', 'y', 'z')):
                    branch = branch.replace('descriptor.velocity.%s' % component,
                        '((f32 *)&descriptor.velocity)[%d]' % axis)
            if comma:
                lines = branch.splitlines(keepends=True)
                stores = [i for i, line in enumerate(lines) if ('descriptor.velocity.' in line or
                    '((f32 *)&descriptor.velocity)' in line)]
                assert len(stores) == 3
                for index in stores[:2]:
                    lines[index] = lines[index].replace(';\n', ',\n')
                branch = ''.join(lines)
            body = start + marker + branch + '                break;' + tail
        yield 'velocity-stores-comma%d-pointer%d-all%d' % (comma, scalar_pointer, all_cases), body


def candidates():
    yield 'base', BASE
    yield from branch_scratch_forms()
    yield from branch_angle_forms()
    yield from branch_flow_forms()
    yield from initialization_forms()
    yield from velocity_store_forms()
    for rate, size in itertools.product((False, True), repeat=2):
        if not (rate or size):
            continue
        body = PRIVATE_SELECTED
        if rate:
            body = body.replace('    while (remaining--) {',
                '    while (remaining--) {\n        f32 rateMultiplier = 15.0f;').replace(
                '15.0f * descriptor.field0C', 'rateMultiplier * descriptor.field0C')
        if size:
            body = body.replace('    while (remaining--) {',
                '    while (remaining--) {\n        f32 sizeMultiplier = 30.0f;').replace(
                'retainedScale * 30.0f', 'retainedScale * sizeMultiplier')
        yield 'constant-locals-rate%d-size%d' % (rate, size), body
    yield from private_layout_forms()
    yield from structured_forms()
    for name, body in structured_forms():
        if name == 'structured-horizontal0-if1-chain1':
            for size, rate in itertools.product(('30', '30.0'), ('15', '15.0', '15.0f')):
                yield 'literals-size%s-rate%s' % (size, rate), body.replace('30.0f', size).replace('15.0f', rate)
    for speed, horizontal, result in ((True, False, False), (True, True, False),
            (True, True, True), (False, False, True)):
        yield 'reuse-speed%d-horizontal%d-result%d' % (speed, horizontal, result), reused_temporaries(speed, horizontal, result)
    for reuse, angles_first in itertools.product((0, 1, 2), (False, True)):
        body = BASE if reuse == 0 else reused_temporaries(True, reuse == 2, False)
        yield 'byte-args-reuse%d-anglesfirst%d' % (reuse, angles_first), byte_arguments(body, angles_first)
    for integer_angles, use_if in itertools.product((False, True), (False, True)):
        body = BASE
        if integer_angles:
            body = body.replace('u8 angle0, angle1;', 'u32 angle0, angle1;')
            for axis in (0, 1):
                expression = '(u32)func_150ADA20() %% (u32)(params->range%d + 1) + params->angle%d' % (axis, axis)
                body = body.replace(expression + ';', '(' + expression + ') & 255;')
        if use_if:
            body = body.replace('    while (remaining--) {',
                '    if (remaining != 0) {\n        do {').replace(
                '        }\n    }\n}', '        }\n        } while (--remaining != 0);\n    }\n}')
        if integer_angles or use_if:
            yield 'angles%d-countif%d' % (integer_angles, use_if), body


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.dict(compiler.PROFILES, PROFILES), patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(root, out, name, body, profile)
    adjustments = [(i, (-(w & 65535)) & 65535) for i, w in enumerate(words) if w >> 16 == 0x27BD and w & 32768]
    if len(adjustments) != 1:
        raise ValueError('Expected one actual SP adjustment: %r' % adjustments)
    record['prologue_word'], record['frame'] = adjustments[0]
    return record, words


def analyze_velocity_delay_schedule(words):
    """Diagnostic inverse of two filled delay slots, not a build normalizer."""
    sites = []
    for store in (0xE7A60124, 0xE7A80124):
        if words.count(store) != 1:
            raise ValueError('Expected one specific velocity-Z store')
        index = words.index(store) - 1
        if index < 0 or words[index] >> 16 != 0x1000:
            raise ValueError('Velocity-Z store is not an unconditional branch delay')
        sites.append(index)
    rewritten, positions = [], {}
    index = 0
    while index < len(words):
        if index in sites:
            positions[index], positions[index + 1] = len(rewritten) + 1, len(rewritten)
            rewritten.extend((words[index + 1], words[index], 0))
            index += 2
        else:
            positions[index] = len(rewritten)
            rewritten.append(words[index])
            index += 1
    positions[len(words)] = len(rewritten)
    for index, word in enumerate(words):
        if word >> 26 not in (4, 5):
            continue
        immediate = word & 65535
        target = index + 1 + (immediate if immediate < 32768 else immediate - 65536)
        if target not in positions or target in (site + 1 for site in sites):
            raise ValueError('Branch targets an external index or a moved delay store')
        delta = positions[target] - positions[index] - 1
        if not -32768 <= delta < 32768:
            raise ValueError('Rebased branch exceeds its signed immediate')
        rewritten[positions[index]] = (word & 0xFFFF0000) | (delta & 65535)
    return rewritten, sites


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-burst-consumer'
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        for profile in PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
