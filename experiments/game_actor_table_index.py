"""Direct C actor-actor table index, including closed overflow-removal accounting."""

import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, read_c_string, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object


FUNCTION, ENTRY, ROM, SIZE = 'func_1505E7CC', 0x1505E7CC, 0x8BC7C, 168
SOURCE, OWNER = 'conker/src/game_83300.c', 'game_83300'
BUILD = 'conker/build/game-actor-table-index/qualified'
OBJECT = 'conker/build/src/game_83300.c.o'
BEFORE_OBJECT_SHA = "01d4bdd1febfa3501e55db0289ac55d3a70b159862f5d0ea867aad87678b205f"
OVERFLOW = '__retail_overflow_' + FUNCTION
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
    "conker/build/conker.us.elf": "beaa3ec7b8fe3915458d40e2b3f5a6850e6d03328b32412bdc930d1882dc7dc9",
    "conker/retail_word_patches.us.csv": "633b877110c36117635f293063e929c0a7c161480742271ee49f4259406a687f",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/src/game_83300.c": "8ab68786c757c4ebcaa85e806adc337649aa67aefc4a7a2d64d7bd67bf1da846",
    "conker/src/game_981E0.c": "3d36f0fd850fa6e1f6cabc3269fae9a24a646dd8ab5ef930eb218580fb8b7e22",
    "conker/asm/nonmatchings/game_83300/func_1505E7CC.s": "0d262f4faa884f4ff1216fda48139813bd8d8e40fe433e3017f48d753f28ad39",
    "conker/asm/nonmatchings/game_83300/func_150562FC.s": "f31f5d54c42a3cd647c962fab7408acc67e888d7e2b54a32551f674ed78bc8c6",
    "conker/asm/nonmatchings/game_83300/func_1505B5F8.s": "142f67eb87dcb089cf78bd1eb56f9f7b5450c54220719a86333b1563f003dcfc",
    "conker/asm/nonmatchings/game_83300/func_1505B9C4.s": "3c0f80439e83ddcf2ae9efe90c7590272994d5ad5714422cbc8c3ec3e3dc570d"
}
DECLARATIONS = '#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\n'
SELECTED = "/* Find the first matching record in the actor's 0x18-byte table. */\nu32 func_1505E7CC(s32 key, struct127 *actor) {\n    u8 *header;\n    u8 *entries;\n    u8 *cursor;\n    u32 count;\n    u32 index;\n    u8 id = actor->id;\n\n    if (id == 0xFF) {\n        return 0;\n    }\n    header = (u8 *)D_800D1588[id];\n    if (header == NULL) {\n        return 0;\n    }\n    count = *(u32 *)(header - 4);\n    if (count == 0) {\n        return 0;\n    }\n    count /= 0x18;\n    entries = *(u8 **)(header - 8);\n    if (entries == NULL) {\n        return 0;\n    }\n\n    index = 0;\n    if (count != 0) {\n        cursor = entries;\n        do {\n            if (key == cursor[0]) {\n                return index;\n            }\n            index++;\n            cursor += 0x18;\n        } while (index < count);\n    }\n    return 0;\n}"
PREDECESSOR = "u32 func_1505E7CC(s32 arg0, struct127 *arg1) {\n    u8 id = arg1->id;\n    u8 *table;\n    u32 count;\n    u32 i;\n\n    if (id == 0xFF) {\n        return 0;\n    }\n\n    table = (u8 *)D_800D1588[id];\n    if (table == NULL) {\n        return 0;\n    }\n\n    count = *(u32 *)(table - 4);\n    if (count == 0) {\n        return 0;\n    }\n\n    count /= 0x18;\n    table = *(u8 **)(table - 8);\n    if (table == NULL) {\n        return 0;\n    }\n\n    for (i = 0; i < count; i++) {\n        if (arg0 == table[0]) {\n            return i;\n        }\n        table += 0x18;\n    }\n    return 0;\n}"
BINDINGS = {12: [('R_MIPS_HI16', 'D_800D1588')], 36: [('R_MIPS_LO16', 'D_800D1588')]}



def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {name: (output / ('before-' + name.replace('/', '_'))).read_bytes() for name in INPUTS}
    for name, data in values.items():
        if digest(data) != INPUTS[name]:
            raise ValueError('Actor table index historical input changed: ' + name)
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Actor table index predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Actor table index frozen input changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != PREDECESSOR:
        raise ValueError('Unknown actor table index semantic predecessor')
    return before[:lo] + SELECTED + before[hi:]


def payload(obj):
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero actor table index object tail')
    return raw[:end * 4], {at - f['value']: rows for at, rows in relocations.items()
                          if f['value'] <= at < f['value'] + end * 4}


def assemble(root, path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    asm = path.with_suffix('.s')
    asm.write_text(text)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                    '-I', str(root / 'conker/include'), '-o', str(path), str(asm)],
                   capture_output=True, check=True)
    return path


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('ActorTableOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original',
        (root/'conker/asm/nonmatchings/game_83300/func_1505E7CC.s').read_text(), FUNCTION)


def qualify(root, output):
    values = freeze(root, output)
    if digest((output/'before-padded.o').read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Actor table index predecessor object changed')
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Actor table index compiler diagnostics changed')
    raw, bindings = payload(isolated)
    if len(payload(before)[0]) != 284:
        raise ValueError('Actor table index old unrolled body changed')
    linked, funcs = link_owner(root, output, isolated, OWNER)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    at = funcs[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or payload(after) != (raw, bindings) or len(raw) != SIZE or digest(raw) != 'adf9aef8c2e9454921e55ec1086031234310a3f158bb4ffc36b2c47e824b6442':
        raise ValueError('Actor table index direct C/whole owner is not exact')
    if payload(original(root, output)) != (raw, bindings) or bindings != BINDINGS:
        raise ValueError('Actor table index independent original/bindings differ')
    if same_functions(before, after, (FUNCTION,)) != 88 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Actor table index changed a neighbor or pool')
    obj = assemble(root, output / 'padded/game_83300.c.o', pad_c_object.emit_padded_assembly(
        after, root / 'conker/retail_layout.us.txt', OWNER,
        word_patches_path=root / 'conker/retail_word_patches.us.csv'))
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game_83300.c.o', old)
    if same_functions(old, obj, (FUNCTION,)) != 88 or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Actor table index changed a padded neighbor/pool')
    a, b = sections(old), sections(obj)
    if a['.game_overflow'][1][:-284] != b['.game_overflow'][1]:
        raise ValueError('Actor table index did not remove only its old terminal overflow')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=42, frame=0, differences=0, relocations=2, guards=0, compiler_only=True,
                  unchanged_raw_and_padded_neighbors=88, pools_unchanged=True,
                  old_raw_words=71, old_slot_words=42, removed_overflow_bytes=284,
                  owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    freeze(root, output)
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game_83300.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
                          cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('python3', '../ido/ido5.3_recomp/cc', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected actor table index Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game_83300.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unexpected Make redirection')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        p = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        diagnostic = (output / 'after-owner-diagnostics.txt').read_text() if args[0].endswith('/cc') else ''
        if p.returncode or diagnostics(p.stderr + (p.stdout if redirect is None else '')) != diagnostics(diagnostic):
            raise ValueError('Actor table index Make command failed: ' + p.stdout + p.stderr)
        if redirect is not None:
            redirect.write_text(p.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [a for a in commands if a[0].endswith('/cc')]
    if len(commands) != 5 or len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2', '-g3')):
        raise ValueError('Actor table index Make profile changed')
    if same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != 89:
        raise ValueError('Actor table index actual Make raw functions differ')
    for name in ('.text', '.game_overflow'):
        if sections(actual)[name] != sections(output / 'padded/game_83300.c.o')[name]:
            raise ValueError('Actor table index actual Make padded content differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
                  cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def image_prediction(before_path, truth):
    before = before_path.read_bytes()
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Actor table index image predecessor/retail body changed')
    a = sections(before_path)
    sa = {n: f[1:] for _, n, f, _ in symbol_rows(before)}
    expected = dict(sa)
    address, size, *_ = expected.pop(OVERFLOW)
    if size != 284 or len(a['.game_overflow'][1]) != 2912:
        raise ValueError('Unknown actor table index overflow extent')
    moved = {}
    for name, fields in sa.items():
        if name.startswith('__retail_overflow_') and fields[0] > address:
            expected[name] = (fields[0]-284, *fields[1:])
            moved[fields[0]] = fields[0]-284
    if len(moved) != 7:
        raise ValueError('Actor table index later overflow set changed')
    rom_start = sa['game_overflow_ROM_START'][0]
    rom_end = (rom_start + 2912 - 284 + 15) & ~15
    for name in ('debugger_overflow_ROM_START','__romPos'):
        if sa[name][0] != (rom_start+2912+15)&~15:
            raise ValueError('Actor table index overflow ROM-end predecessor changed')
        expected[name] = (rom_end,*sa[name][1:])
    offset = address-a['.game_overflow'][0]
    expected_overflow = a['.game_overflow'][1][:offset]+a['.game_overflow'][1][offset+284:]
    game = bytearray(a['.game'][1]);start = ENTRY-a['.game'][0]
    game[start:start+SIZE] = truth
    trampolines = []
    for i in range(0,len(game),4):
        if start <= i < start+SIZE:
            continue
        word = struct.unpack_from('>I',game,i)[0]
        target = ((a['.game'][0]+i+4)&0xF0000000)|((word&0x3FFFFFF)<<2)
        if word>>26 == 2 and target in moved:
            struct.pack_into('>I',game,i,(word&0xFC000000)|(moved[target]>>2&0x3FFFFFF))
            trampolines.append(a['.game'][0]+i)
    if trampolines != [0x150768DC,0x15076D3C,0x150781F4,0x150A7D00]:
        raise ValueError('Actor table index relocated trampoline set changed')
    header = list(ELF_HEADER.unpack_from(before))
    headers = [list(SECTION_HEADER.unpack_from(before,header[6]+i*header[11]))for i in range(header[12])]
    if (header[10],header[12],headers[8][3],headers[9][1],headers[10][1]) != (7,12,0x15F00000,2,3):
        raise ValueError('Unknown actor table index ELF layout')
    strings = a['.strtab'][1]
    literal,anchor = OVERFLOW.encode()+b'\0',b'D_8008CAE0\0'
    if strings.count(literal)!=1 or strings.count(anchor)!=1:
        raise ValueError('Unknown actor table index suffix-shared symbol names')
    new_strings = strings.replace(literal,b'')
    at = new_strings.index(anchor)+len(anchor)
    new_strings = new_strings[:at]+FUNCTION.encode()+b'\0'+new_strings[at:]
    new_symbols = bytearray()
    for at in range(0,len(a['.symtab'][1]),SYMBOL.size):
        fields = list(SYMBOL.unpack_from(a['.symtab'][1],at))
        name = read_c_string(strings,fields[0])
        if name == OVERFLOW:
            continue
        if name:
            fields[0] = new_strings.index(name.encode()+b'\0')
            fields[1:] = expected[name]
        new_symbols.extend(SYMBOL.pack(*fields))
    predicted = bytearray(before[:headers[8][4]])
    slot = elf_slot_offset(before,a['.game'][0],len(game))
    predicted[slot:slot+len(game)] = game
    predicted.extend(expected_overflow);headers[8][5] -= 284
    for index,content in ((9,bytes(new_symbols)),(10,new_strings),(11,a['.shstrtab'][1])):
        align = max(1,headers[index][8])
        predicted.extend(b'\0'*(-len(predicted)%align))
        headers[index][4],headers[index][5] = len(predicted),len(content)
        if index == 9:
            headers[index][7] -= 1
        predicted.extend(content)
    predicted.extend(b'\0'*(-len(predicted)%4));header[6] = len(predicted)
    for fields in headers:
        predicted.extend(SECTION_HEADER.pack(*fields))
    ELF_HEADER.pack_into(predicted,0,*header)
    ph_at = header[5]+6*header[9];ph = list(struct.unpack_from('>8I',before,ph_at))
    if ph[2]!=a['.game_overflow'][0] or ph[4:6]!=[2912,2912]:
        raise ValueError('Unknown actor table index overflow program header')
    ph[4]-=284;ph[5]-=284;struct.pack_into('>8I',predicted,ph_at,*ph)
    report = dict(retail_entry_addresses_fixed=True,unchanged_owner_neighbors=88,
        moved_overflow_bodies=7,moved_overflow_instructions_unchanged=True,
        removed_overflow_bytes=284,relocated_trampolines=trampolines,
        overflow_ROM_end_shift=sa['__romPos'][0]-rom_end,
        closed_symbol_changes=True,protected_sections_equal=True,complete_ELF_byte_prediction=True,
        metadata_exclusions=0,old_ELF_bytes=len(before),new_ELF_bytes=len(predicted))
    return bytes(predicted),report


def inspect_image(before_path,after_path,truth,conker):
    predicted,report = image_prediction(before_path,truth)
    if after_path.read_bytes() != predicted:
        raise ValueError('Actor table index complete ELF differs from closed byte prediction')
    data = audit_layout(after_path,conker)
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes']) != (True,189088,720,0):
        raise ValueError('Actor table index protected Game data changed')
    report['game_data'] = data
    return report


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game_83300.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown actor table index link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'padded/game_83300.c.o').relative_to(root / 'conker').as_posix()))
    elf = output / 'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', link.relative_to(root / 'conker').as_posix(),
                    '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
                    '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
                    '-o', elf.relative_to(root / 'conker').as_posix()], cwd=root / 'conker', check=True, capture_output=True)
    report = inspect_image(output / 'before-conker_build_conker.us.elf', elf,
                           values['conker/conker.us.bin'][ROM:ROM + SIZE], root / 'conker')
    report['SHA256'] = digest(elf.read_bytes())
    (output / 'first-link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(root, output):
    values = snapshot(output)
    for name, old in values.items():
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else (
            (output / 'first-linked.elf').read_bytes() if name == 'conker/build/conker.us.elf' else old)
        if (root / name).read_bytes() != expected:
            raise ValueError('Actor table index installed input differs: ' + name)
    report = inspect_image(output / 'before-conker_build_conker.us.elf', root / 'conker/build/conker.us.elf',
                           values['conker/conker.us.bin'][ROM:ROM + SIZE], root / 'conker')
    report.update(first_link_reproduced_byte_for_byte=True, target_words=42, guards=0)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
