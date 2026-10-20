"""Guarded semantic C search with closed instruction-origin and image gates."""

import csv
import io
import hashlib
import json
import re
from pathlib import Path
import shlex
import shutil
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout


FUNCTION, ENTRY, ROM, SIZE = 'func_151CE634', 0x151CE634, 0x1FBAE4, 156
SOURCE, OWNER, ASM = 'conker/src/game/generated_1FA770.c', 'generated_1FA770', 'conker/asm/1FA770.s'
BUILD = 'conker/build/game-context-node-search/qualified'
INPUTS = {
    'conker/include/variables.h': '1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8',
    SOURCE: 'b26e4abd7c88911196644982d6309a4c3a4e6d7cc09f89db3f82a823f347926d',
    ASM: 'cce3e047754e3253d0c7f0d9279cbb86cc922f615e9ef9b79ed786155bde9b60',
    'conker/build/conker.us.elf': '68e65c6edf8656812c4a8708a0789e1202185415a055241252f6bda855d39406',
    'conker/retail_word_patches.us.csv': '7ca8a25f8ea41d9e2e4a795281619c21048f5c24b252d48a9367eb5cd5e36e76',
    'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/Makefile': '54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf',
    'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be',
}
RAW_SHA256 = '4dcc35467748ab2090726c14bdc92749fff1c0cd5185bb5a4c369048874d24a1'
RAW_BINDINGS = {4:[('R_MIPS_HI16','D_800DD190')],24:[('R_MIPS_LO16','D_800DD190')],
                8:[('R_MIPS_HI16','D_800A5760')],20:[('R_MIPS_LO16','D_800A5760')],
                12:[('R_MIPS_HI16','D_800DCE50')],16:[('R_MIPS_LO16','D_800DCE50')]}
ORIGINS = (0,1,6,7,8,9,2,10,11,3,4,14,15,16,18,17,20,21,22,23,24,25,26,27,28,29,30,31,17,32,33,12,34,35,36,37,38,39,40)
DECLARATIONS = '''extern u8 D_800DCE50[0x340];
extern s8 D_800DD190;
extern s32 D_800A5760[2];
'''
SELECTED = '''/* Find the first type-11 node whose associated payload names this context. */
void *func_151CE634(void *context) {
    u8 phase;
    u8 *row;
    void **column;
    void *node;

    for (phase = 0; phase < 2; phase++) {
        row = D_800DCE50;
        column = (void **)(row + D_800A5760[phase] * 4);
        do {
            node = *column;
            while (node != 0) {
                if (*(s32 *)((u8 *)node + 0x20) == 11 &&
                    *(void **)((u8 *)*(void **)((u8 *)node + 0x98) + 0x48) == context) {
                    return node;
                }
                node = *(void **)((u8 *)node + 8);
            }
            row += 0x1A0;
            column = (void **)((u32)column + 0x1A0);
        } while (row != (u8 *)&D_800DD190);
    }
    return 0;
}'''


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Context-node search historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Context-node search predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Context-node search snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151CE634() {\n    return 0;\n}':
        raise ValueError('Unknown context-node-search source predecessor')
    return before[:lo] + DECLARATIONS + '\n' + SELECTED + before[hi:]


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero context-node-search alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('HeadingOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-context-node-search',
        (root / ASM).read_text(), FUNCTION)


def normalized(raw, bindings, reference):
    if digest(raw) != RAW_SHA256 or bindings != RAW_BINDINGS:
        raise ValueError('Context search closed C input words/bindings changed')
    wanted, relocations = reference
    if len(wanted) != 156 or len(ORIGINS) != 39 or set(range(41)) - set(ORIGINS) != {5,13,19}:
        raise ValueError('Context search origin accounting changed')
    a, b = struct.unpack('>41I',raw), struct.unpack('>39I',wanted)
    for target, origin in enumerate(ORIGINS):
        x, y = a[origin], b[target]
        if (origin,target) == (18,14):
            if (x>>26,y>>26) != (4,20):
                raise ValueError('Context search empty-edge annul contract changed')
        elif (x>>26,x&63 if x>>26==0 else None) != (y>>26,y&63 if y>>26==0 else None):
            raise ValueError('Context search output has no C opcode origin')
        if x>>26==0 and x&63==0 and (x>>6&31)!=(y>>6&31):
            raise ValueError('Context search source shift changed')
        if x>>26 not in (0,4,5,20,21) and origin*4 not in bindings and target*4 not in relocations:
            if x&65535 != y&65535:
                raise ValueError('Context search non-address immediate changed')
    if a[5]>>26!=9 or a[13]&63!=37 or a[19]!=0 or ORIGINS.count(17)!=2:
        raise ValueError('Context search address/copy/nop folds or split advance changed')
    return wanted, relocations


def guard_bytes(values, raw, bindings, reference):
    wanted, relocations = normalized(raw,bindings,reference)
    before = values['conker/retail_word_patches.us.csv']
    rows = list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['function']==FUNCTION for r in rows) or not before.endswith(b'\n'):
        raise ValueError('Unknown context search guard predecessor')
    fields = list(rows[0])
    result = io.StringIO()
    writer = csv.DictWriter(result,fieldnames=fields,lineterminator='\n')
    at = 0
    def encoded(items):
        return ';'.join(kind+':'+name for kind,name in items) or '-'
    for index,word in enumerate(struct.unpack('>41I',raw)):
        omit = index in (5,13,19)
        output = struct.unpack_from('>I',wanted,at*4)[0] if not omit else word
        row = dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(index*4),
            expected='0x%08X'%word,replacement='0x%08X'%output,
            expected_relocations=encoded(bindings.get(index*4,[])),
            replacement_relocations=encoded(relocations.get(at*4,[])) if not omit else '-',
            note='Context search closed C origin/schedule normalization',
            insert_after='',insert_after_relocations='',omit='true' if omit else 'false')
        if not omit:
            at += 1
        if index==17:
            row['insert_after']='0x%08X'%struct.unpack_from('>I',wanted,at*4)[0]
            row['insert_after_relocations']=encoded(relocations.get(at*4,[]))
            at += 1
        writer.writerow(row)
    if at!=39:
        raise ValueError('Context search guard extent is not 39 words')
    return before+result.getvalue().encode()


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da)!=diagnostics(db) or dc:
        raise ValueError('Context search compiler diagnostics changed: '+da+db+dc)
    raw, bindings = payload(isolated)
    if payload(after)!=(raw,bindings):
        raise ValueError('Context search isolated/full owner differ')
    reference = payload(original(root,output))
    normalized(raw,bindings,reference)
    guards = output/'qualified-guards.csv'
    guards.write_bytes(guard_bytes(values,raw,bindings,reference))
    neighbors = same_functions(before,after,(FUNCTION,))
    if not neighbors or normalized_pools(before)!=normalized_pools(after):
        raise ValueError('Context search raw neighbors/pools changed')
    padded = output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old = output/'before-padded.o'
    if not old.exists():
        shutil.copyfile(root/'conker/build/src/game/generated_1FA770.c.o',old)
    a,fa = link_owner(root,output,old,OWNER)
    b,fb = link_owner(root,output,obj,OWNER)
    expected = {n:dict(info) for n,info in fa.items()}
    if expected[FUNCTION]['size']!=12:
        raise ValueError('Unknown context search padded predecessor extent')
    expected[FUNCTION]['size']=SIZE
    at=fb[FUNCTION]['value']
    truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]:
        raise ValueError('Context search predecessor object/ELF differ')
    if b[at:at+SIZE]!=truth or expected!=fb or a[:at]!=b[:at] or a[at+SIZE:]!=b[at+SIZE:]:
        raise ValueError('Context search padding changed another body/address/extent')
    if same_functions(old,obj,(FUNCTION,))!=neighbors or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('Context search padded neighbors/pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(raw_words=41,words=39,frame=0,differences=0,compiler_only=False,new_guard_rows=41,
        input_bindings=6,output_bindings=6,unique_C_origins=38,folded_origins=[5,13,19],duplicated_origin=17,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True,target_size_before=12,target_size_after=156)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Context-node search shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_1FA770.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected context-node-search Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_1FA770.c' else (output / 'qualified-guards.csv').relative_to(conker).as_posix()
                if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown context-node-search Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Context-node search Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Context-node search Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Context-node search actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Context-node search actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Context-node search strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Context-node search symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Context-node search image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1FA770.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown context-node-search link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'qualified-padded.o').relative_to(root / 'conker').as_posix()))
    elf = output / 'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', link.relative_to(root / 'conker').as_posix(),
        '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
        '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
        '-o', elf.relative_to(root / 'conker').as_posix()], cwd=root / 'conker', check=True, capture_output=True)
    before, actual = values['conker/build/conker.us.elf'], elf.read_bytes()
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    check_image(before, actual, truth)
    changed = sum(a != b for a, b in zip(before, actual))
    at = elf_slot_offset(before, ENTRY, SIZE)
    code = sum(a != b for a, b in zip(before[at:at + SIZE], truth))
    report = dict(exact_prediction=True, SHA256=digest(actual), changed_bytes=changed,
        code_bytes_changed=code, metadata_bytes_changed=changed - code, metadata_exclusions=0)
    (output / 'first-link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(root, output):
    values = snapshot(output)
    wanted = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + SIZE])
    for name, old in values.items():
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else wanted if name == 'conker/build/conker.us.elf' else guard_bytes(values,*payload(output/'after-owner.o'),payload(original(root,output))) if name=='conker/retail_word_patches.us.csv' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Context-node search installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Context-node search independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Context-node search changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Context-node search protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=39, raw_C_words=41, compiler_only=False, new_guard_rows=41,
        strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
