"""Direct selector callback factory and strict legacy owner/caller/image gates."""

import hashlib
import json
import re
from pathlib import Path
import shlex
import sys
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

SOURCE, OWNER, ASM = 'conker/src/game_1897A0.c', 'game_1897A0', 'conker/asm/nonmatchings/game_1897A0/func_1515D088.s'
BUILD = 'conker/build/game-selector-callback-factory/qualified'
OBJECT = 'conker/build/src/game_1897A0.c.o'
BEFORE_OBJECT_SHA = "69c300c3ea7b8d81f4e343b725f0f1ccc7333717ad3b7643382f5fbb197c533f"
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/include/2.0L/ultra64.h": "334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d",
    "conker/include/2.0L/PR/ultratypes.h": "1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/build/conker.us.elf": "8ccd597559500389b092ed638e6e2b2e5f3c0ee996e4c792a35a5d7cec80d119",
    "conker/retail_word_patches.us.csv": "633b877110c36117635f293063e929c0a7c161480742271ee49f4259406a687f",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/src/game_1897A0.c": "60926bb6fa0fdb3dbc02194615c9d224179999ce4e884e8258399acf0dfb6aba",
    "conker/asm/nonmatchings/game_1897A0/func_1515D088.s": "d5279a5f40ad7851012de012fafb2148a294afcbe26a9bc154d24e409c7cf580",
    "conker/src/game_40490.c": "a0459450661634b512cb791490976bba714b1d9702c0801835b3888a1c9d12ae",
    "conker/build/src/game_40490.c.o": "f7791694bf224220587ba1c26dbfb1ccf76ea4c14b69726c1fc74cadf543b626",
    "conker/src/game/done/game_1765E0.c": "19dd4f8a4e0561ad2de70ee59e12e50c11a9938357816dd0eacb2334d8c0c5af",
    "conker/build/src/game/done/game_1765E0.c.o": "e25e23423217e12289d36ef8ddd82eb68ba757c7b708340995f7a7d8a987aabf",
    "conker/src/libultra/libc/string.c": "6c66f2298d39e0b159e2645570caed26c869928215aedc41e600daebfc7b98d0"
}
TARGETS = {
    'func_1515D088': dict(entry=0x1515D088, rom=0x18A538, size=168,
        SHA256='46ca32cb598d709f37b3e4d629e873924a6c0606f82af53bb52cfb7b805727b3'),
}
FUNCTIONS = tuple(TARGETS)
DECLARATIONS = "typedef struct {\n    void *source;\n    f32 value;\n    u8 selector;\n    u8 reserved[3];\n} SelectorCallbackPayload;\n"
ISOLATED_HEADER = '#include <ultra64.h>\nvoid *func_151491F4(s16, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, size_t);\n'
SELECTED = {'func_1515D088': "/* Create a selector-0/1 callback record with its source and zero parameter. */\nvoid *func_1515D088(void *source) {\n    u8 *created;\n    SelectorCallbackPayload data;\n    s32 selector;\n\n    data.selector = *(s32 *)((u8 *)source + 0x18);\n    selector = (u8)data.selector;\n    if (selector < 0 || selector >= 2) {\n        return NULL;\n    }\n    data.source = source;\n    data.value = 0.0f;\n    created = (u8 *)func_151491F4(0x12C, -1, 0x11, 0, 0xD, 0xC, 0xFF, 1);\n    if (created != NULL) {\n        memcpy(created + 0x28, &data, sizeof(data));\n    }\n    return created;\n}"}
PREDECESSOR = "void *func_1515D088(u8 *arg0) {\n    struct {\n        void *unk0;\n        f32 unk4;\n        s8 unk8;\n        u8 pad[3];\n    } data;\n    u8 *temp_v0;\n    s32 value = *(s32 *)(arg0 + 0x18);\n\n    data.unk8 = value;\n    if ((value & 0xFF) >= 2) {\n        return NULL;\n    }\n\n    data.unk0 = arg0;\n    data.unk4 = 0.0f;\n    temp_v0 = (u8 *)func_151491F4(0x12C, -1, 0x11, 0, 0xD, 0xC, 0xFF, 1);\n    if (temp_v0 != NULL) {\n        memcpy(temp_v0 + 0x28, &data, 0xC);\n    }\n    return temp_v0;\n}"
BINDINGS = {108: [('R_MIPS_26', 'func_151491F4')], 136: [('R_MIPS_26', 'memcpy')]}
CALLER_SOURCE = 'conker/src/game_40490.c'
CALLER_OBJECT = 'conker/build/src/game_40490.c.o'
CALLER_OWNER = 'game_40490'




def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Selector callback factory historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Selector callback factory padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Selector callback factory frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Selector callback factory predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Selector callback factory snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    anchor = '} Func1515CF9CPosition;'
    if before.count(anchor) != 1:
        raise ValueError('Selector callback factory type anchor changed')
    result = before.replace(anchor, anchor + '\n\n' + DECLARATIONS.rstrip(), 1)
    lo, hi = function_span(result, FUNCTIONS[0])
    if result[lo:hi] != PREDECESSOR:
        raise ValueError('Selector callback factory semantic predecessor changed')
    return result[:lo] + SELECTED[FUNCTIONS[0]] + result[hi:]


def recovered_caller(before):
    anchor = 'struct17 *func_1515F1B0(u8 *arg0);'
    if before.count(anchor) != 1 or 'void *func_1515D088(void *);' in before:
        raise ValueError('Selector callback factory caller prototype predecessor changed')
    return before.replace(anchor, anchor + '\nvoid *func_1515D088(void *);', 1)


def emit_owner(root, output, obj, owner, assembly):
    subprocess.run([sys.executable, str(root/'tools/pad_c_object.py'), str(obj),
        str(root/'conker/retail_layout.us.txt'), owner, str(assembly),
        '--word-patches', str(root/'conker/retail_word_patches.us.csv')],
        check=True, capture_output=True)
    padded = assembly.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root/'conker/include'), '-o', str(padded), str(assembly)], check=True, capture_output=True)
    return padded


def payload(obj, name):
    text, functions, bindings = parse_object(obj)
    info = functions[name]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero selector callback factory alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output, name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('ActorSelectorOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-' + name,
        (root / ASM).read_text(), name)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    if diagnostics(da) != diagnostics(db):
        raise ValueError('Selector callback factory owner diagnostics changed: ' + da + db)
    rows = []
    for name, target in TARGETS.items():
        isolated, dc = compile_owner(root, output, ISOLATED_HEADER + DECLARATIONS + SELECTED[name], 'selected-' + name)
        raw, bindings = payload(isolated, name)
        truth = values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]
        if dc or len(raw) != target['size'] or digest(raw) != target['SHA256'] or bindings != BINDINGS:
            raise ValueError('Selector callback factory isolated direct C differs: ' + name)
        if payload(after, name) != (raw, bindings) or payload(original(root, output, name), name) != (raw, bindings):
            raise ValueError('Selector callback factory whole owner/GNU original differs: ' + name)
        text, functions = link_owner(root, output, isolated, OWNER)
        at = functions[name]['value']
        if text[at:at + target['size']] != truth:
            raise ValueError('Selector callback factory linked C differs')
        rows.append(dict(function=name, words=len(raw)//4, frame=64, bindings=2, new_guards=0))
    neighbors = same_functions(before, after, FUNCTIONS)
    if neighbors != 7 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Selector callback factory raw owner neighbor/pool changed')
    padded = output / 'qualified-padded.s'
    obj = emit_owner(root, output, after, OWNER, padded)
    old = output / 'before-padded.o'
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Selector callback factory frozen object changed')
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    changed_ranges = []
    for name, target in TARGETS.items():
        if expected[name]['size'] != 164:
            raise ValueError('Unknown selector callback factory predecessor extent')
        expected[name]['size'] = target['size']
        at = fb[name]['value'];changed_ranges.append((at, at + target['size']))
        slot = elf_slot_offset(values['conker/build/conker.us.elf'], target['entry'], target['size'])
        if a[at:at + target['size']] != values['conker/build/conker.us.elf'][slot:slot + target['size']]:
            raise ValueError('Selector callback factory predecessor object/ELF mismatch')
        if b[at:at + target['size']] != values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]:
            raise ValueError('Selector callback factory padded target differs')
    if expected != fb or len(a) != len(b):
        raise ValueError('Selector callback factory padding changed function metadata')
    if any(x != y and not any(lo <= at < hi for lo, hi in changed_ranges) for at, (x, y) in enumerate(zip(a, b))):
        raise ValueError('Selector callback factory padding changed another body')
    if same_functions(old, obj, FUNCTIONS) != 7 or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Selector callback factory padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    cb, ca = qualify_caller(root, output, values)
    report = dict(targets=rows, total_words=42, compiler_only=True, new_guards=0,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        preserved_neighbors=neighbors, all_owner_addresses_fixed=True,
        target_sizes_before=[164], target_sizes_after=[168], caller_functions=32, caller_object_identical=True)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

def qualify_caller(root, output, values):
    before, db = compile_owner(root, output, values[CALLER_SOURCE].decode(), 'before-caller')
    wanted = recovered_caller(values[CALLER_SOURCE].decode())
    after, da = compile_owner(root, output, wanted, 'after-caller')
    if diagnostics(db) != diagnostics(da) or same_functions(before, after) != 32 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Selector callback factory changed caller functions/pools/diagnostics')
    obj = emit_owner(root, output, after, CALLER_OWNER, output/'qualified-caller.s')
    if obj.read_bytes() != values[CALLER_OBJECT]:
        raise ValueError('Selector callback factory changed the complete caller object')
    (output/'proposed-caller.c').write_text(wanted)
    return before, after


def make_shadow(root, output):
    values = freeze(root, output)
    if (output/'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Selector callback factory shadow owner changed')
    if (output/'proposed-caller.c').read_text() != recovered_caller(values[CALLER_SOURCE].decode()):
        raise ValueError('Selector callback factory shadow caller changed')
    conker, shadow = root/'conker', output/'make-shadow'
    (shadow/'src').mkdir(parents=True, exist_ok=True)
    targets = [(shadow/'src'/name).relative_to(conker).as_posix() for name in ('game_1897A0.c.o','game_40490.c.o')]
    plan = subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),*targets],
        cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    replacements = {'src/game_1897A0.c':(output/'proposed-owner.c').relative_to(conker).as_posix(),
                    'src/game_40490.c':(output/'proposed-caller.c').relative_to(conker).as_posix()}
    for line in plan.stdout.replace('\\\n','').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
            raise ValueError('Unexpected selector factory Make command: '+repr(args))
        args = [replacements.get(a,a) for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown selector factory Make redirect')
            redirect = (conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        process = subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected = ''
        if args[0] == '../ido/ido5.3_recomp/cc':
            label = 'after-owner' if args[-1] == replacements['src/game_1897A0.c'] else 'after-caller'
            expected = (output/(label+'-diagnostics.txt')).read_text()
        if process.returncode or diagnostics(process.stderr+(process.stdout if redirect is None else '')) != diagnostics(expected):
            raise ValueError('Selector factory Make command failed: '+process.stdout+process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    compilers = [a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    if len(commands)!=8 or len(compilers)!=2 or any(not all(f in a for f in ('-O2','-g3')) or any('-loopunroll' in f for f in a) for a in compilers):
        raise ValueError('Selector factory actual Make profile changed')
    for target,label,owner,count,padded in zip(targets,('after-owner','after-caller'),(OWNER,CALLER_OWNER),(8,32),('qualified-padded.o','qualified-caller.o')):
        actual = conker/target
        if same_functions(output/(label+'.o'),Path(str(actual)+'.compact')) != count:
            raise ValueError('Selector factory Make raw owner differs')
        if actual.read_bytes() != (output/padded).read_bytes():
            raise ValueError('Selector factory Make padded object differs')
    report = dict(actual_Make_commands=8,normal_O2_g3=True,all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True,complete_caller_object_identical=True,
        cleanup_skipped=True,inherited_Make_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, rom):
    if digest(before) != INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Selector callback factory strict image predecessor changed')
    result = bytearray(before)
    for name, target in TARGETS.items():
        at = elf_slot_offset(before, target['entry'], target['size'])
        result[at:at + target['size']] = rom[target['rom']:target['rom'] + target['size']]
        rows = [offset for offset, symbol, fields, _ in symbol_rows(before)
                if symbol == name and fields[1:3] == (target['entry'], 164) and fields[3] & 15 == 2]
        if len(rows) != 1:
            raise ValueError('Selector callback factory symbol extent predecessor changed')
        struct.pack_into('>I', result, rows[0] + 8, target['size'])
    return bytes(result)


def check_image(before, actual, rom):
    if actual != predicted_image(before, rom):
        raise ValueError('Selector callback factory image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game_1897A0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown selector callback factory link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'qualified-padded.o').relative_to(root / 'conker').as_posix()))
    elf = output / 'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', link.relative_to(root / 'conker').as_posix(),
        '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
        '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
        '-o', elf.relative_to(root / 'conker').as_posix()], cwd=root / 'conker', check=True, capture_output=True)
    before, actual, rom = values['conker/build/conker.us.elf'], elf.read_bytes(), values['conker/conker.us.bin']
    check_image(before, actual, rom)
    changed = sum(a != b for a, b in zip(before, actual));code = 0
    for target in TARGETS.values():
        at = elf_slot_offset(before, target['entry'], target['size'])
        code += sum(a != b for a, b in zip(before[at:at + target['size']], rom[target['rom']:target['rom'] + target['size']]))
    report = dict(exact_prediction=True, SHA256=digest(actual), changed_bytes=changed,
        code_bytes_changed=code, metadata_bytes_changed=changed-code, metadata_exclusions=0)
    (output / 'first-link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(root, output):
    values = snapshot(output)
    wanted = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'])
    for name, old in values.items():
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else recovered_caller(old.decode()).encode() if name == CALLER_SOURCE else wanted if name == 'conker/build/conker.us.elf' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Selector callback factory installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Selector callback factory independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or set(n for n in a if a[n] != b[n]) != set(FUNCTIONS):
        raise ValueError('Selector callback factory changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'qualified-padded.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'qualified-padded.o'):
        raise ValueError('Selector callback factory installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Selector callback factory protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b)-1, all_addresses_fixed=True,
        target_words=42, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
