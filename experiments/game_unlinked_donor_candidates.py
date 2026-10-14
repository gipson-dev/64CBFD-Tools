"""Requalify nine newly found, unlinked donor bodies in their active owners."""
import difflib
import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-unlinked-byte-exact-donors'
BASELINE_ELF = '65a9c8e783574fbff76c11d3ab000af8015c604a17061f138f5d354e2a2e3968'
BASELINE_MAKEFILE = 'a7e4fcee0cc3a4dd785e786f1a9f94fd4dedb3656fa4f2210d976b144ee5ec4d'
TARGETS = {
    'func_150E2DB4': dict(owner='generated_10EF60', words=60, body='''/* Forward the preset inputs to the 0x27 factory with its 40/400 defaults. */
void func_150E2DB4(void *arg0, u8 arg1, s16 arg2, s32 arg3, f32 arg4, f32 arg5, f32 arg6, f32 arg7, f32 arg8, f32 arg9, s16 arg10, s16 arg11, u16 arg12, u8 arg13) {
    func_150E1AB0(0, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 40.0f, 400.0f, (s16) (s32) arg12, 0x27U, 1, (s16) (s32) arg10, (s16) (s32) arg11, arg0, (u8) (s32) arg1, (u8) (s32) arg2, arg3, 0U, (u8) (s32) arg13, arg4, arg5, arg6, arg7, arg8, arg9);
}'''),
    'func_150E2EA4': dict(owner='generated_10EF60', words=59, body='''/* Forward the configurable ranges and scalar to the 0x27 factory. */
void func_150E2EA4(void *arg0, u8 arg1, s16 arg2, s32 arg3, f32 arg4, f32 arg5, f32 arg6, f32 arg7, f32 arg8, f32 arg9, s16 arg10, s16 arg11, u16 arg12, f32 arg13, f32 arg14, u8 arg15, f32 arg16) {
    func_150E1AB0(0, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, arg16, 0.0f, arg13, arg14, (s16) (s32) arg12, 0x27U, 1, (s16) (s32) arg10, (s16) (s32) arg11, arg0, (u8) (s32) arg1, (u8) (s32) arg2, arg3, 0U, (u8) (s32) arg15, arg4, arg5, arg6, arg7, arg8, arg9);
}'''),
    'func_150ED234': dict(owner='generated_11A680', words=25, body='''/* Query the heading helper using relative X/Z and the actor scalar at 0x40. */
f32 func_150ED234(void *actor, void *other) {
    return func_150ED1D0((f32) (func_1505A630((*(f32 *)((char *)(other) + 0x14)) - (*(f32 *)((char *)(actor) + 0x14)), (*(f32 *)((char *)(actor) + 0x1C)) - (*(f32 *)((char *)(other) + 0x1C)), 0) + 0x4000) * 0.005493164f, (*(f32 *)((char *)(actor) + 0x40)));
}'''),
    'func_150FFBDC': dict(owner='generated_12C1E0', words=24, body='''/* Submit the descriptor and index using the actor offset and global row. */
void func_150FFBDC(void *arg0, void * arg1, s32 arg2) {
    void * *sp1C;
    s32 sp18;

    sp1C = (void **)&D_800A2130;
    sp18 = arg2;
    func_15145EA4(&sp1C, &sp18, (*(s32 *)((char *)(arg0) + 0x1D4)) + (D_80088BB0 << 6), 1);
}'''),
    'func_151E4264': dict(owner='generated_20AE20', words=44, body='''/* Consume the one-shot flag or advance the callback/audio transition state. */
void func_151E4264(void) {
    if (D_8008FD80 != 0) {
        D_8008FD80 = 0;
        return;
    }
    func_151E530C();
    if (((s16) D_800E0B9A != 0) || (D_800C35EA != 1)) {
        if ((D_800C35EA == 1) && (func_151F2CDC() == 1)) {
            func_151F2D6C(0, 0x2DE0);
        }
        D_800E0B94 = 7;
        D_800E0A88 = (s32)func_151E2834;
        D_8008FD74 = 8;
    }
}'''),
    'func_150B1E20': dict(owner='generated_DF260', words=48, body='''/* Update event-driven actor flags and the attached record's target scalar. */
void func_150B1E20(void *actor) {
    void *temp_v0;

    if (func_1509BE40(1, 0x4054, 6, 0x9000) != 0) {
        (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) | 0x10000);
    } else {
        (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) & 0xFFFEFFFF);
    }
    if ((func_1509BE40(1, 0x405C, 6, 0x9000) == 0) && (func_1509BE40(1, 0x405B, 6, 0x2000) != 0) && ((*(s32 *)((char *)(actor) + 0x2C)) != 0x40)) {
        temp_v0 = (void *)(*(s32 *)((char *)(actor) + 0x3D0));
        (*(f32 *)((char *)(temp_v0) + 0x17C)) = (f32) ((*(f32 *)((char *)(temp_v0) + 0x180)) + 10.0f);
    }
}'''),
    'func_150BEEB0': dict(owner='generated_EBE60', words=48, body='''/* Update actor bits 0x1010 and 0x01000000 from event queries. */
void func_150BEEB0(void *actor) {
    if ((func_1509BE40(1, 0x4063, 6, 0x2000) != 0) || (func_1509BE40(1, 0x4001, 6, 0x9000) != 0)) {
        (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) | 0x1010);
    } else {
        (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) & ~0x1010);
    }
    if (func_1509BE40(1, 0x4069, 6, 0x2000) != 0) {
        (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) | 0x01000000);
        return;
    }
    (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) & 0xFEFFFFFF);
}'''),
    'func_150C7770': dict(owner='generated_F4C20', words=64, body='''/* Dispatch the context command and update the event-driven actor bits. */
void func_150C7770(void *actor) {
    if (func_1509BE40(3, 0x2000, 0xAC, 0x401B, 0x401C, 0x401D) != 0) {
        func_1509BFB0(1, 0x2000, 0x3B, 2);
    }
    if (func_1509BE40(1, 0x4006, 6, 0x2000) != 0) {
        (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) | 0x400000);
    } else {
        (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) & 0xFFBFFFFF);
    }
    (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) | 0x400000);
    if (func_1509BE40(1, 0x4030, 6, 0x2000) != 0) {
        (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) | 0x01000000);
        return;
    }
    (*(s32 *)((char *)(actor) + 0x84)) = (s32) ((*(s32 *)((char *)(actor) + 0x84)) & 0xFEFFFFFF);
}'''),
    'func_150CCD90': dict(owner='generated_FA240', words=72, body='''/* Compute the three-channel piecewise color ramp. */
void func_150CCD90(f32 level, f32 *red, f32 *green, f32 *blue) {
    f32 temp_f0;
    f32 temp_f0_2;

    if (level > 0.0f) {
        *red = 255.0f;
        *green = 255.0f;
        *blue = 255.0f;
        return;
    }
    if (D_800A0700 < level) {
        temp_f0 = -level * D_800A0704;
        *red = 255.0f - (temp_f0 * 83.0f);
        *green = 255.0f - (temp_f0 * 113.0f);
        *blue = 255.0f - (temp_f0 * 173.0f);
        return;
    }
    temp_f0_2 = -(level + D_800A0708) * D_800A070C;
    *red = 172.0f - (temp_f0_2 * 50.0f);
    *green = 142.0f - (temp_f0_2 * 42.0f);
    *blue = 82.0f - (temp_f0_2 * -1.0f);
}'''),
}

EXTRA = {
'generated_11A680': 'u16 func_1505A630(f32, f32, s32);\nf32 func_150ED1D0(f32, f32);\n',
'generated_12C1E0': 'extern s32 D_800A2130;\nextern u8 D_80088BB0;\nvoid func_15145EA4(void *, void *, s32, s32);\n',
'generated_20AE20': 'extern u8 D_800C35EA;\ns32 func_151F2CDC(void);\nvoid func_151F2D6C(s32, s32);\n',
'generated_DF260': 's32 func_1509BE40(s32, ...);\n',
'generated_EBE60': 's32 func_1509BE40(s32, ...);\n',
'generated_F4C20': 's32 func_1509BE40(s32, ...);\nvoid func_1509BFB0(s32, s32, s32, ...);\n',
'generated_FA240': 'extern f32 D_800A0700;\nextern f32 D_800A0704;\nextern f32 D_800A0708;\nextern f32 D_800A070C;\n',
}
FACTORY_SIGNATURE = '''void func_150E1AB0(s32 arg0, f32 arg1, f32 arg2, f32 arg3, f32 arg4,
    f32 arg5, f32 arg6, f32 arg7, f32 arg8, f32 arg9, f32 arg10,
    s16 arg11, u16 arg12, s8 arg13, s16 arg14, s16 arg15, void *arg16,
    u8 arg17, u8 arg18, s32 arg19, u8 arg20, u8 arg21,
    f32 arg22, f32 arg23, f32 arg24, f32 arg25, f32 arg26, f32 arg27)'''


def path(owner):
    return 'conker/src/game/' + owner + '.c'


def recover(before, owner):
    result = before
    for name, spec in TARGETS.items():
        if spec['owner'] != owner:
            continue
        if owner == 'generated_10EF60':
            lo, hi = build.function_span(result, name)
            while hi < len(result) and result[hi] == '\n':
                hi += 1
            comment = '/* Factory forwarders are compiled in translation_units/10EF60_wrappers.c. */\n\n' if name == 'func_150E2DB4' else ''
            result = result[:lo] + comment + result[hi:]
            continue
        pragma = re.compile(r'#pragma GLOBAL_ASM\("asm/nonmatchings/[^"\n]+/' + name + r'\.s"\)')
        if pragma.search(result):
            result = pragma.sub(lambda match: spec['body'], result, count=1)
        else:
            lo, hi = build.function_span(result, name)
            result = result[:lo] + spec['body'] + result[hi:]
    if owner in EXTRA:
        position = result.index('\n') + 1
        result = result[:position] + EXTRA[owner] + result[position:]
    return result


def emission_source():
    return '#include <ultra64.h>\n\n/* Isolate the recovered caller ABI from the factory placeholder definition. */\n' + FACTORY_SIGNATURE + ';\n\n' + '\n\n'.join(
        spec['body'] for spec in TARGETS.values() if spec['owner'] == 'generated_10EF60') + '\n'


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    owners = sorted({spec['owner'] for spec in TARGETS.values()})
    if not manifest.exists():
        inputs = {owner: (root / path(owner)).read_bytes() for owner in owners}
        inputs.update(elf=(root / 'conker/build/conker.us.elf').read_bytes(),
            guards=(root / 'conker/retail_word_patches.us.csv').read_bytes(),
            progress=(root / 'conker/progress.csv').read_bytes(),
            makefile=(root / 'conker/Makefile').read_bytes())
        if hashlib.sha256(inputs['elf']).hexdigest() != BASELINE_ELF:
            raise ValueError('Refusing to capture a changed ELF baseline')
        for key, data in inputs.items():
            (out / ('before-' + key)).write_bytes(data)
        manifest.write_text(json.dumps({key: hashlib.sha256(data).hexdigest() for key, data in inputs.items()}, indent=2) + '\n')
    pins = json.loads(manifest.read_text())
    if 'makefile' not in pins:
        data = (root / 'conker/Makefile').read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE_MAKEFILE:
            raise ValueError('Refusing to capture a changed Makefile baseline')
        (out / 'before-makefile').write_bytes(data)
        pins['makefile'] = BASELINE_MAKEFILE
        manifest.write_text(json.dumps(pins, indent=2) + '\n')
    for key, digest in json.loads(manifest.read_text()).items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified fixture: ' + key)
    rom = (root / 'conker/conker.us.bin').read_bytes()
    records, patches = [], []
    for owner in owners:
        before = (out / ('before-' + owner)).read_text()
        after = recover(before, owner)
        obj, diagnostics = build.compile_owner(root, out, after, owner)
        emitted, functions = build.link_owner(root, out, obj, owner)
        if owner == 'generated_10EF60':
            obj, diagnostics = build.compile_owner(root, out, emission_source(), 'emission-wrappers')
            emitted, functions = build.link_owner(root, out, obj, owner)
        for name, spec in TARGETS.items():
            if spec['owner'] != owner:
                continue
            entry = int(name[5:], 16)
            info = functions[name]
            raw = emitted[info['value']:info['value'] + info['size']]
            actual = list(struct.unpack('>%dI' % (len(raw) // 4), raw))
            truth = list(struct.unpack_from('>%dI' % spec['words'], rom, entry - 0x15000000 + 0x2D4B0))
            excess = len(actual) - len(truth)
            if excess > 0 and not any(actual[len(truth):]):
                actual = actual[:len(truth)]
            content = actual == truth[:len(actual)] and not any(truth[len(actual):])
            record = dict(function=name, owner=owner, raw_words=len(actual), retail_words=len(truth),
                differences=sum(a != b for a,b in zip(actual, truth)) + sum(word != 0 for word in truth[len(actual):]) + max(0, len(actual)-len(truth)),
                exact_content=content, omitted_alignment_nops=len(truth)-len(actual) if content else None,
                diagnostics=diagnostics)
            print(json.dumps({key:value for key,value in record.items() if key != 'diagnostics'}),flush=True)
            records.append(record)
        diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), n=3, lineterm=''))
        patches.append('*** Update File: ' + str(root / path(owner)) + '\n' +
            '\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')
    patches.append('*** Add File: ' + str(root / 'conker/src/game/translation_units/10EF60_wrappers.c') + '\n' +
        '\n'.join('+' + line for line in emission_source().splitlines()))
    (out / 'source.patch').write_text('*** Begin Patch\n' + '\n'.join(patches) + '\n*** End Patch\n')
    if not all(record['exact_content'] for record in records):
        raise SystemExit('At least one active-ABI body is not qualified')


if __name__ == '__main__':
    main()
