"""Direct-C linked-owner retirement allocator and strict owner/image gates."""
import csv
import hashlib
import io
import json
from pathlib import Path
import shlex
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION, ENTRY, ROM, SIZE = 'func_151A4ECC', 0x151A4ECC, 0x1D237C, 176
OWNER, SOURCE, ASM = 'generated_1D0840', 'conker/src/game/generated_1D0840.c', 'conker/asm/1D0840.s'
OBJECT = 'conker/build/src/game/generated_1D0840.c.o'
BUILD = 'conker/build/game-linked-owner-retirement/qualified'
SNAPSHOT_SHA = '7130acdc73515ce74494186b4722cfa8cf0023adae65210dc16e3d00a989a833'
BEFORE_OBJECT_SHA = '890b92b4db9715298c0dd431682e9925ab70170a391df7aa538a3279d41cd2e1'
RETAIL_SHA = '1ccb298785c6746a86f2c60c85e36e5ce8547b880b9e4413b0876c9b6b5d4134'

HEADERS = '#include <ultra64.h>\n#include "structs.h"\n'
DECLARATIONS = '''typedef struct { u8 *owner; u8 identity; u8 opaque5[3]; } PayloadOwnerLink;
void *func_151A3504(void *, u8);
'''
HELPER, PARENT, TABLE = 0x151A3504, 0x15149264, 0x8008A4E8
BINDINGS = {0x74: [('R_MIPS_26', 'func_151A3504')]}
EXPECTED = {0x70: 0xAFA30018, 0x7C: 0x8FA30018}
REPLACEMENT = {0x70: 0xA3A3001B, 0x7C: 0x93A3001B}
RAW_SHA = '20f50e01826db3824f9a83db98c5bc7ac8817685cc000254b03119101fa9e457'
GUARD_SHA = '9ebbb54699e0676c2a6a02e1702bb7e5f7766059fe040bdc9e766fcd57895876'

SELECTED = '''/* Retire an invalid owner link, submitting the final effect when needed. */
void func_151A4ECC(struct260 *owner) {
    PayloadOwnerLink *link = (PayloadOwnerLink *)((u8 *)owner + 0x28);
    s32 failed = 0;

    if (*(s32 *)link->owner == 0) {
        failed = 1;
    }
    if (link->identity != link->owner[0x3B]) {
        failed = 1;
    }
    if (failed == 0 && *(s32 *)(link->owner + 0x1D4) != 0
        && (link->owner[0x74] & 0xF) != 0xF) {
        func_151A3504(link, ((u8 *)owner)[0xC]);
        failed = 1;
    }
    if (failed != 0) {
        *(s16 *)((u8 *)owner + 0xE) = -1;
        ((u8 *)owner)[0xD] |= 1;
    }
}'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    raw = (output / 'input-snapshot.json').read_bytes()
    if digest(raw) != SNAPSHOT_SHA:
        raise ValueError('Linked-owner retirement frozen input manifest changed')
    manifest = json.loads(raw)
    values = {}
    for name, wanted in manifest['INPUTS'].items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Linked-owner retirement historical input changed: ' + name)
        values[name] = data
    if digest((output / 'before-padded.o').read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Linked-owner retirement predecessor object changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE]) != RETAIL_SHA:
        raise ValueError('Linked-owner retirement retail slot changed')
    return values


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151A4ECC() {\n    return 0;\n}':
        raise ValueError('Unknown linked-owner retirement predecessor')
    return before[:lo] + SELECTED + before[hi:]



def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero linked-owner retirement alignment tail')
    relative = {at-info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value']+end*4}
    return raw[:end*4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('LinkedOwnerOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-linked-owner',
        (root / ASM).read_text(), FUNCTION)


def normalized(raw, bindings):
    if len(raw) != SIZE or digest(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Owner retirement raw extent or binding changed')
    words = list(struct.unpack('>44I', raw))
    for offset, wanted in EXPECTED.items():
        if words[offset // 4] != wanted:
            raise ValueError('Owner retirement checked spill input changed')
        words[offset // 4] = REPLACEMENT[offset]
    return struct.pack('>44I', *words), dict(bindings)


def guard_bytes(old):
    if digest(old) != GUARD_SHA:
        raise ValueError('Owner retirement guard prefix changed')
    fields = ['filename','function','offset','expected','replacement','expected_relocations',
              'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    reader = csv.DictReader(io.StringIO(old.decode()))
    if reader.fieldnames != fields or any(row['function'] == FUNCTION for row in reader):
        raise ValueError('Owner retirement guard prefix/schema changed')
    newline = '\r\n' if old.endswith(b'\r\n') else '\n'
    if not old.endswith(newline.encode()):
        raise ValueError('Owner retirement guard terminator missing')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator=newline)
    for offset, wanted in EXPECTED.items():
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%offset,
            expected='0x%08X'%wanted,replacement='0x%08X'%REPLACEMENT[offset],
            expected_relocations='-',replacement_relocations='-',
            note='Normalize Boolean spill to the retail low byte',omit='false'))
    return old + stream.getvalue().encode()


def check_inputs(root, output, installed=False):
    values = snapshot(output)
    for name, before in values.items():
        expected = recovered_owner(before.decode()).encode() if installed and name == SOURCE else (
            predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM+SIZE])
            if installed and name == 'conker/build/conker.us.elf' else
            guard_bytes(before) if installed and name == 'conker/retail_word_patches.us.csv' else before)
        if (root / name).read_bytes() != expected:
            raise ValueError('Linked-owner retirement current input differs: ' + name)
    return values


def qualify(root, output):
    values = check_inputs(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, HEADERS+DECLARATIONS+SELECTED, 'selected')
    if da or db or dc:
        raise ValueError('Linked-owner retirement compiler diagnostics: ' + da + db + dc)
    truth = values['conker/conker.us.bin'][ROM:ROM+SIZE]
    raw, bindings = payload(isolated)
    if len(raw) != SIZE or payload(after) != (raw, bindings) or payload(original(root, output)) != normalized(raw, bindings):
        raise ValueError('Linked-owner retirement direct C or independent original differs')
    original_object = original(root, output)
    linked, functions = link_owner(root, output, original_object, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at+SIZE] != truth or sum(map(len, bindings.values())) != 1:
        raise ValueError('Linked-owner retirement linked body or bindings differ')
    guards = output / 'qualified-guards.csv'
    guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv']))
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root/ASM,
        word_patches_path=guards, filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)], capture_output=True, check=True)
    old = output/'before-padded.o'
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name:dict(info) for name,info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown linked-owner retirement predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE] != values['conker/build/conker.us.elf'][slot:slot+SIZE]:
        raise ValueError('Linked-owner retirement predecessor object/image disagreement')
    if expected != fb or b[at:at+SIZE] != truth or a[:at] != b[:at] or a[at+SIZE:] != b[at+SIZE:]:
        raise ValueError('Linked-owner retirement padding changed another extent/body/address')
    neighbors = same_functions(before,after,(FUNCTION,))
    if neighbors != 22 or same_functions(old,obj,(FUNCTION,)) != neighbors:
        raise ValueError('Linked-owner retirement neighbors changed')
    if normalized_pools(before) != normalized_pools(after) or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Linked-owner retirement owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report = dict(words=44,frame=32,relocations=1,new_guards=2,compiler_only=False,
        raw_SHA256=digest(raw),retail_SHA256=digest(truth),preserved_neighbors=neighbors,all_owner_addresses_fixed=True,
        target_size_before=12,target_size_after=SIZE,compiler_diagnostics_empty=True,helper_stub_unchanged=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    shadow = output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
    conker = root/'conker'
    target = (shadow/'src/game/generated_1D0840.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
        cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n','').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
            raise ValueError('Unexpected linked-owner retirement Make command: '+repr(args))
        args = [(output/'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_1D0840.c' else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()
                if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown linked-owner retirement Make redirect')
            redirect = (conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p = subprocess.run(args,cwd=conker,capture_output=True,text=True)
        if p.returncode or p.stderr or (redirect is None and p.stdout):
            raise ValueError('Linked-owner retirement Make command failed: '+p.stdout+p.stderr)
        if redirect is not None:
            redirect.write_text(p.stdout)
        commands.append(args)
    actual = conker/target
    compilers = [a for a in commands if a[0] == '../ido/ido5.3_recomp/cc']
    processors = [a for a in commands if a[0] == 'python3' and a[1] == '../tools/asm-processor/asm_processor.py']
    if len(commands) != 5 or len(processors) != 2 or len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2','-g3')):
        raise ValueError('Linked-owner retirement normal Make profile changed')
    if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),()) != 23:
        raise ValueError('Linked-owner retirement actual Make compact functions differ')
    if actual.read_bytes() != (output/'qualified-padded.o').read_bytes():
        raise ValueError('Linked-owner retirement actual Make object differs')
    report = dict(actual_Make_commands=5,normal_O2_g3=True,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_Make_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, truth):
    if digest(before) != 'c67e436c20af22f763e2b2996d9c38fc501cbdd3ff408c6bc6a7f11fbcb387de' or digest(truth) != RETAIL_SHA:
        raise ValueError('Linked-owner retirement strict image predecessor/body changed')
    result = bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows = [offset for offset,name,fields,_ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY,12) and fields[3]&15 == 2]
    if len(rows) != 1:
        raise ValueError('Linked-owner retirement symbol predecessor extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before,truth):
        raise ValueError('Linked-owner retirement image differs from strict body/size prediction')


def predict(root, output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_1D0840.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown linked-owner retirement link input')
    link=output/'first-link.ld';link.write_text(script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix()))
    elf=output/'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',elf.relative_to(root/'conker').as_posix()],cwd=root/'conker',capture_output=True,check=True)
    before,actual=values['conker/build/conker.us.elf'],elf.read_bytes();truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    check_image(before,actual,truth)
    at=elf_slot_offset(before,ENTRY,SIZE);changed=sum(a!=b for a,b in zip(before,actual))
    code=sum(a!=b for a,b in zip(before[at:at+SIZE],truth))
    report=dict(exact_prediction=True,SHA256=digest(actual),changed_bytes=changed,
        code_bytes_changed=code,metadata_bytes_changed=changed-code,metadata_exclusions=0)
    (output/'first-link.json').write_text(json.dumps(report,indent=2)+'\n');return report


def audit(root, output):
    values=check_inputs(root,output,installed=True)
    expected=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
    if (output/'first-linked.elf').read_bytes() != expected or (root/OBJECT).read_bytes() != (output/'qualified-padded.o').read_bytes():
        raise ValueError('Linked-owner retirement independent image or object changed')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Linked-owner retirement changed another function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes']) != (True,189088,720,0):
        raise ValueError('Linked-owner retirement protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
