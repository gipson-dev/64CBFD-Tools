"""Direct-C one-shot owner-link payload creator and strict owner/image gates."""
import hashlib
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

FUNCTION, ENTRY, ROM, SIZE = 'func_150FAA40', 0x150FAA40, 0x127EF0, 172
OWNER, SOURCE, ASM = 'generated_126F60', 'conker/src/game/generated_126F60.c', 'conker/asm/126F60.s'
OBJECT = 'conker/build/src/game/generated_126F60.c.o'
BUILD = 'conker/build/game-one-shot-link/qualified'
SNAPSHOT_SHA = 'afd5827baf1d0072974b35ef5c2291228d10d2b97c9c262cd02bf450d0fd492e'
BEFORE_OBJECT_SHA = '7fb6083d5edb715b1465ae005cc0d098919291cff0ed1c53aa1a5cc131fda3ed'
RETAIL_SHA = '63384f6a234b6a078e933a313e0b68fbad92d98b0cdbfc2a1c4df370a9ecfd0e'

DECLARATIONS = '''typedef struct {
    void *first;
    void *second;
    f32 zero;
} OneShotLinkPayload;

extern u8 D_80088B60;
void *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);
void *memcpy(void *, const void *, u32);
'''
ISOLATED_DECLARATIONS = 'extern u8 *D_800D3098;\n' + DECLARATIONS
SPAWN, COPY, ALLOCATE, BZERO = 0x15149130, 0x10022EC0, 0x15167A68, 0x100226F0

SELECTED = '''/* Capture both owner links and attach the payload only once allocation succeeds. */
void func_150FAA40(u8 code, s32 value) {
    OneShotLinkPayload payload;
    u8 *effect;

    if (D_80088B60 == 0) {
        payload.first = D_800D3098 + 0x71C;
        payload.second = D_800D3098 + 0x6E8;
        payload.zero = 0.0f;
        effect = func_15149130(300, -1, 0x57, -1, 0, 0x46, 12, code, value);
        if (effect != 0) {
            D_80088B60 = 1;
        }
        if (effect != 0) {
            memcpy(effect + 0x28, &payload, 12);
        }
    }
}'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    raw = (output / 'input-snapshot.json').read_bytes()
    if digest(raw) != SNAPSHOT_SHA:
        raise ValueError('One-shot link frozen input manifest changed')
    manifest = json.loads(raw)
    values = {}
    for name, wanted in manifest['INPUTS'].items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('One-shot link historical input changed: ' + name)
        values[name] = data
    if digest((output / 'before-padded.o').read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('One-shot link predecessor object changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE]) != RETAIL_SHA:
        raise ValueError('One-shot link retail slot changed')
    return values


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_150FAA40() {\n    return 0;\n}':
        raise ValueError('Unknown one-shot link predecessor')
    return before[:lo] + DECLARATIONS + '\n' + SELECTED + before[hi:]


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero one-shot link alignment tail')
    relative = {at-info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value']+end*4}
    return raw[:end*4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('OneShotLinkOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-one-shot-link',
        (root / ASM).read_text(), FUNCTION)


def check_inputs(root, output, installed=False):
    values = snapshot(output)
    for name, before in values.items():
        expected = recovered_owner(before.decode()).encode() if installed and name == SOURCE else (
            predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM+SIZE])
            if installed and name == 'conker/build/conker.us.elf' else before)
        if (root / name).read_bytes() != expected:
            raise ValueError('One-shot link current input differs: ' + name)
    return values


def qualify(root, output):
    values = check_inputs(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n'+ISOLATED_DECLARATIONS+SELECTED, 'selected')
    if da or db or dc:
        raise ValueError('One-shot link compiler diagnostics: ' + da + db + dc)
    truth = values['conker/conker.us.bin'][ROM:ROM+SIZE]
    raw, bindings = payload(isolated)
    if len(raw) != SIZE or payload(after) != (raw, bindings) or payload(original(root, output)) != (raw, bindings):
        raise ValueError('One-shot link direct C or independent original differs')
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at+SIZE] != truth or sum(map(len, bindings.values())) != 8:
        raise ValueError('One-shot link linked body or bindings differ')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root/ASM,
        word_patches_path=root/'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)], capture_output=True, check=True)
    old = output/'before-padded.o'
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name:dict(info) for name,info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown one-shot link predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE] != values['conker/build/conker.us.elf'][slot:slot+SIZE]:
        raise ValueError('One-shot link predecessor object/image disagreement')
    if expected != fb or b[at:at+SIZE] != truth or a[:at] != b[:at] or a[at+SIZE:] != b[at+SIZE:]:
        raise ValueError('One-shot link padding changed another extent/body/address')
    neighbors = same_functions(before,after,(FUNCTION,))
    if neighbors != 17 or same_functions(old,obj,(FUNCTION,)) != neighbors:
        raise ValueError('One-shot link neighbors changed')
    if normalized_pools(before) != normalized_pools(after) or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('One-shot link owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report = dict(words=43,frame=72,relocations=8,new_guards=0,compiler_only=True,
        raw_SHA256=digest(raw),retail_SHA256=digest(truth),preserved_neighbors=neighbors,all_owner_addresses_fixed=True,
        target_size_before=12,target_size_after=SIZE,compiler_diagnostics_empty=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    shadow = output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
    conker = root/'conker'
    target = (shadow/'src/game/generated_126F60.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
        cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n','').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
            raise ValueError('Unexpected one-shot link Make command: '+repr(args))
        args = [(output/'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_126F60.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown one-shot link Make redirect')
            redirect = (conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p = subprocess.run(args,cwd=conker,capture_output=True,text=True)
        if p.returncode or p.stderr or (redirect is None and p.stdout):
            raise ValueError('One-shot link Make command failed: '+p.stdout+p.stderr)
        if redirect is not None:
            redirect.write_text(p.stdout)
        commands.append(args)
    actual = conker/target
    compilers = [a for a in commands if a[0] == '../ido/ido5.3_recomp/cc']
    if len(commands) != 3 or len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2','-g3')):
        raise ValueError('One-shot link normal Make profile changed')
    if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),()) != 18:
        raise ValueError('One-shot link actual Make compact functions differ')
    if actual.read_bytes() != (output/'qualified-padded.o').read_bytes():
        raise ValueError('One-shot link actual Make object differs')
    report = dict(actual_Make_commands=3,normal_O2_g3=True,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_Make_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, truth):
    if digest(before) != '93964ef8cfe8f569707bfb09c79e34fe17c1f9912c01e4fe8ce2695984c51225' or digest(truth) != RETAIL_SHA:
        raise ValueError('One-shot link strict image predecessor/body changed')
    result = bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows = [offset for offset,name,fields,_ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY,12) and fields[3]&15 == 2]
    if len(rows) != 1:
        raise ValueError('One-shot link symbol predecessor extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before,truth):
        raise ValueError('One-shot link image differs from strict body/size prediction')


def predict(root, output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_126F60.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown one-shot link link input')
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
        raise ValueError('One-shot link independent image or object changed')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('One-shot link changed another function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes']) != (True,189088,720,0):
        raise ValueError('One-shot link protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
