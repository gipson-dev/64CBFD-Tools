"""Direct-C owner-following endpoint callback and strict owner/image gates."""
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

FUNCTION, ENTRY, ROM, SIZE = 'func_150F00EC', 0x150F00EC, 0x11D59C, 172
OWNER, SOURCE, ASM = 'generated_11C2B0', 'conker/src/game/generated_11C2B0.c', 'conker/asm/11C2B0.s'
OBJECT = 'conker/build/src/game/generated_11C2B0.c.o'
BUILD = 'conker/build/game-effect-owner-ray/qualified'
SNAPSHOT_SHA = '0781525b992f6214b5e8ce36dc2209def967f5588cb11b0905f390384e3318d6'
BEFORE_OBJECT_SHA = '7542e3ef5a12a2fe371e0ce7d11cf75613591d7e3ca51585df4293a3576deebb'
RETAIL_SHA = '7155834316b92418b73cdc0c49f35abc0dfc0756d99ae38ccc897057ce7323ba'

DECLARATIONS = '''typedef struct {
    f32 x, y, z;
} EffectRayVector;

typedef struct {
    u8 opaque0[0x18];
    u8 active;
    u8 opaque19[0x17];
    EffectRayVector direction;
} EffectRayMotion;

typedef struct {
    u8 opaque0[0x34];
    EffectRayVector position;
    u8 opaque40[0xD0];
    EffectRayMotion motion;
} EffectRayOwner;

typedef struct {
    u8 opaque0[0x34];
    EffectRayVector position;
    EffectRayVector endPoint;
    u8 opaque4C[0xC];
    u32 flags;
    u8 opaque5C[0x11C];
    EffectRayOwner *owner;
} OwnerRayEffect;

'''

SELECTED = '''/* Follow the active owner's position and project its direction by 500 units. */
s32 func_150F00EC(OwnerRayEffect *effect) {
    EffectRayOwner *owner = effect->owner;
    EffectRayMotion *motion = &owner->motion;

    if (owner->motion.active & 1) {
        effect->position = owner->position;
        effect->endPoint.x = owner->position.x + motion->direction.x * 500.0f;
        effect->endPoint.y = owner->position.y + motion->direction.y * 500.0f;
        effect->endPoint.z = owner->position.z + motion->direction.z * 500.0f;
        effect->flags |= 6;
    } else {
        effect->flags &= ~4;
        effect->flags &= ~2;
    }
    return 1;
}'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    raw = (output / 'input-snapshot.json').read_bytes()
    if digest(raw) != SNAPSHOT_SHA:
        raise ValueError('Owner-ray frozen input manifest changed')
    manifest = json.loads(raw)
    values = {}
    for name, wanted in manifest['INPUTS'].items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Owner-ray historical input changed: ' + name)
        values[name] = data
    if digest((output / 'before-padded.o').read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Owner-ray predecessor object changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE]) != RETAIL_SHA:
        raise ValueError('Owner-ray retail slot changed')
    return values


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_150F00EC() {\n    return 0;\n}':
        raise ValueError('Unknown owner-ray predecessor')
    marker = '#include "structs.h"\n'
    if before.count(marker) != 1:
        raise ValueError('Unknown owner-ray declaration site')
    return (before[:lo] + SELECTED + before[hi:]).replace(marker, marker + '\n' + DECLARATIONS, 1)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero owner-ray alignment tail')
    relative = {at-info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value']+end*4}
    return raw[:end*4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('OwnerRayOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-owner-ray',
        (root / ASM).read_text(), FUNCTION)


def check_inputs(root, output, installed=False):
    values = snapshot(output)
    for name, before in values.items():
        expected = recovered_owner(before.decode()).encode() if installed and name == SOURCE else (
            predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM+SIZE])
            if installed and name == 'conker/build/conker.us.elf' else before)
        if (root / name).read_bytes() != expected:
            raise ValueError('Owner-ray current input differs: ' + name)
    return values


def qualify(root, output):
    values = check_inputs(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n'+DECLARATIONS+SELECTED, 'selected')
    if da or db or dc:
        raise ValueError('Owner-ray compiler diagnostics: ' + da + db + dc)
    truth = values['conker/conker.us.bin'][ROM:ROM+SIZE]
    if payload(isolated) != (truth, {}) or payload(after) != (truth, {}) or payload(original(root, output)) != (truth, {}):
        raise ValueError('Owner-ray direct C or independent original differs')
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
        raise ValueError('Unknown owner-ray predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE] != values['conker/build/conker.us.elf'][slot:slot+SIZE]:
        raise ValueError('Owner-ray predecessor object/image disagreement')
    if expected != fb or b[at:at+SIZE] != truth or a[:at] != b[:at] or a[at+SIZE:] != b[at+SIZE:]:
        raise ValueError('Owner-ray padding changed another extent/body/address')
    neighbors = same_functions(before,after,(FUNCTION,))
    if neighbors != 43 or same_functions(old,obj,(FUNCTION,)) != neighbors:
        raise ValueError('Owner-ray neighbors changed')
    if normalized_pools(before) != normalized_pools(after) or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Owner-ray owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report = dict(words=43,frame=0,relocations=0,new_guards=0,compiler_only=True,
        raw_SHA256=digest(truth),preserved_neighbors=neighbors,all_owner_addresses_fixed=True,
        target_size_before=12,target_size_after=SIZE,compiler_diagnostics_empty=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    shadow = output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
    conker = root/'conker'
    target = (shadow/'src/game/generated_11C2B0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
        cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n','').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
            raise ValueError('Unexpected owner-ray Make command: '+repr(args))
        args = [(output/'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_11C2B0.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown owner-ray Make redirect')
            redirect = (conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p = subprocess.run(args,cwd=conker,capture_output=True,text=True)
        if p.returncode or p.stderr or (redirect is None and p.stdout):
            raise ValueError('Owner-ray Make command failed: '+p.stdout+p.stderr)
        if redirect is not None:
            redirect.write_text(p.stdout)
        commands.append(args)
    actual = conker/target
    compilers = [a for a in commands if a[0] == '../ido/ido5.3_recomp/cc']
    if len(commands) != 3 or len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2','-g3')):
        raise ValueError('Owner-ray normal Make profile changed')
    if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),()) != 44:
        raise ValueError('Owner-ray actual Make compact functions differ')
    if actual.read_bytes() != (output/'qualified-padded.o').read_bytes():
        raise ValueError('Owner-ray actual Make object differs')
    report = dict(actual_Make_commands=3,normal_O2_g3=True,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_Make_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, truth):
    if digest(before) != 'bbb2ee554aaa62b3b0b93ed0e26eb67f8a631681d62d7644d8630b08015a7663' or digest(truth) != RETAIL_SHA:
        raise ValueError('Owner-ray strict image predecessor/body changed')
    result = bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows = [offset for offset,name,fields,_ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY,12) and fields[3]&15 == 2]
    if len(rows) != 1:
        raise ValueError('Owner-ray symbol predecessor extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before,truth):
        raise ValueError('Owner-ray image differs from strict body/size prediction')


def predict(root, output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_11C2B0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown owner-ray link input')
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
        raise ValueError('Owner-ray independent image or object changed')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Owner-ray changed another function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes']) != (True,189088,720,0):
        raise ValueError('Owner-ray protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
