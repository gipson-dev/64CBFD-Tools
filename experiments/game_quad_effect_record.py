"""Direct-C quad-effect record allocator and strict owner/image gates."""
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

FUNCTION, ENTRY, ROM, SIZE = 'func_15171CA0', 0x15171CA0, 0x19F150, 172
OWNER, SOURCE, ASM = 'generated_19F150', 'conker/src/game/generated_19F150.c', 'conker/asm/19F150.s'
OBJECT = 'conker/build/src/game/generated_19F150.c.o'
BUILD = 'conker/build/game-quad-effect-record/qualified'
SNAPSHOT_SHA = '5ba7716e31943926474d489a1363e3889f1d393962d6c1b0a7d6f34423d4534b'
BEFORE_OBJECT_SHA = '72eabb7e74a3ade088a744b39401867daccc32275315219e6dd7ef9b00a36a81'
RETAIL_SHA = 'e9f73f215b5d0002fde49fdc162ef94cbd2cf859a159eeb6082c6da25f8e995d'

DECLARATIONS = '''typedef struct {
    u8 opaque0[0x10];
    Vtx vertices[4];
    s16 lifetime;
    s16 frame;
    s16 frameStep;
    u16 color;
    u8 imageIndex;
    u8 flags;
    u8 opaque5A[6];
} QuadEffect19F150;

void *func_15167A68(s32, s32, s32, s32, u8, u8);
'''
ISOLATED_DECLARATIONS = DECLARATIONS
ALLOCATE = 0x15167A68

SELECTED = '''/* Allocate an animated quad and initialize its metadata and vertex flags. */
void *func_15171CA0(s16 lifetime, u16 color, u8 imageIndex, s32 flags,
                    s32 frameStep, s32 alternate, u8 slot, s32 context) {
    QuadEffect19F150 *record;

    record = func_15167A68(alternate == 0 ? 0xF : 0x43, context,
                          sizeof(QuadEffect19F150), 1, slot, 1);
    if (record == NULL) {
        return NULL;
    }
    record->lifetime = lifetime;
    record->frame = 0;
    record->frameStep = frameStep;
    record->color = color;
    record->imageIndex = imageIndex;
    record->flags = flags;
    record->vertices[0].v.flag = 0;
    record->vertices[1].v.flag = 0;
    record->vertices[2].v.flag = 0;
    record->vertices[3].v.flag = 0;
    return record;
}'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    raw = (output / 'input-snapshot.json').read_bytes()
    if digest(raw) != SNAPSHOT_SHA:
        raise ValueError('Quad-effect record frozen input manifest changed')
    manifest = json.loads(raw)
    values = {}
    for name, wanted in manifest['INPUTS'].items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Quad-effect record historical input changed: ' + name)
        values[name] = data
    if digest((output / 'before-padded.o').read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Quad-effect record predecessor object changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE]) != RETAIL_SHA:
        raise ValueError('Quad-effect record retail slot changed')
    return values


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15171CA0() {\n    return 0;\n}':
        raise ValueError('Unknown quad-effect record predecessor')
    result = before[:lo] + DECLARATIONS + '\n' + SELECTED + before[hi:]
    return result.replace('/* Non-matching placeholders for the text-only asm slice asm/19F150.s. */',
                          '/* Animated quad records and remaining functions from asm/19F150.s. */')


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero quad-effect record alignment tail')
    relative = {at-info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value']+end*4}
    return raw[:end*4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('FourEntryLoaderOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-four-entry-loader',
        (root / ASM).read_text(), FUNCTION)


def check_inputs(root, output, installed=False):
    values = snapshot(output)
    for name, before in values.items():
        expected = recovered_owner(before.decode()).encode() if installed and name == SOURCE else (
            predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM+SIZE])
            if installed and name == 'conker/build/conker.us.elf' else before)
        if (root / name).read_bytes() != expected:
            raise ValueError('Quad-effect record current input differs: ' + name)
    return values


def qualify(root, output):
    values = check_inputs(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n'+ISOLATED_DECLARATIONS+SELECTED, 'selected')
    if da or db or dc:
        raise ValueError('Quad-effect record compiler diagnostics: ' + da + db + dc)
    truth = values['conker/conker.us.bin'][ROM:ROM+SIZE]
    raw, bindings = payload(isolated)
    if len(raw) != SIZE or payload(after) != (raw, bindings) or payload(original(root, output)) != (raw, bindings):
        raise ValueError('Quad-effect record direct C or independent original differs')
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at+SIZE] != truth or sum(map(len, bindings.values())) != 1:
        raise ValueError('Quad-effect record linked body or bindings differ')
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
        raise ValueError('Unknown quad-effect record predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE] != values['conker/build/conker.us.elf'][slot:slot+SIZE]:
        raise ValueError('Quad-effect record predecessor object/image disagreement')
    if expected != fb or b[at:at+SIZE] != truth or a[:at] != b[:at] or a[at+SIZE:] != b[at+SIZE:]:
        raise ValueError('Quad-effect record padding changed another extent/body/address')
    neighbors = same_functions(before,after,(FUNCTION,))
    if neighbors != 6 or same_functions(old,obj,(FUNCTION,)) != neighbors:
        raise ValueError('Quad-effect record neighbors changed')
    if normalized_pools(before) != normalized_pools(after) or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Quad-effect record owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report = dict(words=43,frame=32,relocations=1,new_guards=0,compiler_only=True,
        raw_SHA256=digest(raw),retail_SHA256=digest(truth),preserved_neighbors=neighbors,all_owner_addresses_fixed=True,
        target_size_before=12,target_size_after=SIZE,compiler_diagnostics_empty=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    shadow = output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
    conker = root/'conker'
    target = (shadow/'src/game/generated_19F150.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
        cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n','').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
            raise ValueError('Unexpected quad-effect record Make command: '+repr(args))
        args = [(output/'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_19F150.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown quad-effect record Make redirect')
            redirect = (conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p = subprocess.run(args,cwd=conker,capture_output=True,text=True)
        if p.returncode or p.stderr or (redirect is None and p.stdout):
            raise ValueError('Quad-effect record Make command failed: '+p.stdout+p.stderr)
        if redirect is not None:
            redirect.write_text(p.stdout)
        commands.append(args)
    actual = conker/target
    compilers = [a for a in commands if a[0] == '../ido/ido5.3_recomp/cc']
    if len(commands) != 3 or len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2','-g3')):
        raise ValueError('Quad-effect record normal Make profile changed')
    if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),()) != 7:
        raise ValueError('Quad-effect record actual Make compact functions differ')
    if actual.read_bytes() != (output/'qualified-padded.o').read_bytes():
        raise ValueError('Quad-effect record actual Make object differs')
    report = dict(actual_Make_commands=3,normal_O2_g3=True,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_Make_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, truth):
    if digest(before) != '85b152c71a51b836b6334efcd8069d1a346d3cdadedad904fd2d510e8b773add' or digest(truth) != RETAIL_SHA:
        raise ValueError('Quad-effect record strict image predecessor/body changed')
    result = bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows = [offset for offset,name,fields,_ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY,12) and fields[3]&15 == 2]
    if len(rows) != 1:
        raise ValueError('Quad-effect record symbol predecessor extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before,truth):
        raise ValueError('Quad-effect record image differs from strict body/size prediction')


def predict(root, output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_19F150.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown quad-effect record link input')
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
        raise ValueError('Quad-effect record independent image or object changed')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Quad-effect record changed another function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes']) != (True,189088,720,0):
        raise ValueError('Quad-effect record protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
