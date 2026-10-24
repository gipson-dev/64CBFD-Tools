"""Paired-reference events with a closed register cycle and strict owner/image gates."""
import csv
import hashlib
import io
import json
from pathlib import Path
import shlex
import struct
import subprocess
import sys

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION, ENTRY, ROM, SIZE = 'func_15169850', 0x15169850, 0x196D00, 176
BODY = 164
OWNER, SOURCE, ASM = 'game_1944C0', 'conker/src/game_1944C0.c', 'conker/asm/nonmatchings/game_1944C0/func_15169850.s'
OBJECT = 'conker/build/src/game_1944C0.c.o'
BUILD = 'conker/build/game-pair-reference-event/qualified'
SNAPSHOT_SHA = '0cdf404c3382b66ed7f1a2f846f24f97a19d160e7c4db142b9651d9393e9baf6'
BEFORE_OBJECT_SHA = '563a6047043915c1ea23a4fbee84f479618b6caf967a45f4977226cc93f84e51'
RETAIL_SHA = '4a3960cad441555e10139f5ccabf55f57c7e0c287410d2235be983c1628913b8'
BODY_SHA = 'da2a12cadbf322c388454a2b82b0bd0a156890c0eb4e5402cd943d1fb328cbb9'
HEADERS = '#include <ultra64.h>\n#include "structs.h"\n'
DECLARATIONS = 'void func_1516972C(struct102 *);\n'
HELPER = 0x1516972C
BINDINGS = {0x3C: [('R_MIPS_26', 'func_1516972C')]}
EXPECTED = {0x58:0x8C820000,0x5C:0x8CC30000,0x60:0x54430007,0x80:0x55630005,0x88:0xACC20000}
REPLACEMENT = {0x58:0x8C830000,0x5C:0x8CC20000,0x60:0x54620007,0x80:0x55620005,0x88:0xACC30000}
RAW_SHA = '77ca382addeb0db9b90ba5f5e9da8dc0f2a1fb38693dede1d50750bffac4db1d'
GUARD_SHA = 'b34cd973e3296eaa713abdba47414885e1855bdac1bc9f72efa5b65cbf979f2d'
SELECTED = '''/* Release a matching owner, or exchange a paired reference and its identity tag. */
void func_15169850(s32 pairAddress, u8 command, s32 valueAddress, s32 tagAddress, s32 owner) {
    s32 *pair = (s32 *)pairAddress;
    s32 *value = (s32 *)valueAddress;
    u8 *tag = (u8 *)tagAddress;

    if (command == 0) {
        if ((pair[0] == *value) || (((u8 *)pair)[4] == *tag)) {
            func_1516972C((struct102 *)owner);
        }
    } else if (command == 0x2D) {
        if (pair[0] == *value) {
            *value = pair[1];
            *tag = ((u8 *)pair)[9];
        } else if (pair[1] == *value) {
            *value = pair[0];
            *tag = ((u8 *)pair)[8];
        }
    }
}'''

def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    import re
    return re.sub(r"line\s+\d+","line #",re.sub(r"\S+\.c","<unit>",text))


def snapshot(output):
    raw = (output / 'input-snapshot.json').read_bytes()
    if digest(raw) != SNAPSHOT_SHA:
        raise ValueError('Pair-reference event frozen input manifest changed')
    manifest = json.loads(raw)
    values = {}
    for name, wanted in manifest['INPUTS'].items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Pair-reference event historical input changed: ' + name)
        values[name] = data
    if digest((output / 'before-padded.o').read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Pair-reference event predecessor object changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE]) != RETAIL_SHA:
        raise ValueError('Pair-reference event retail slot changed')
    return values


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi] != 'void func_15169850(s32 arg0, u8 arg1, s32 arg2, s32 arg3, s32 arg4) {\n}':
        raise ValueError('Unknown pair reference placeholder')
    marker='/* Non-matching C placeholders for asm/nonmatchings/game_1944C0/func_15169850.s. */\n'
    if before.count(marker)!=1:raise ValueError('Pair reference placeholder marker changed')
    return (before[:lo]+SELECTED+before[hi:]).replace(marker,'')
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151A4ECC() {\n    return 0;\n}':
        raise ValueError('Unknown pair-reference event predecessor')
    return before[:lo] + SELECTED + before[hi:]



def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero pair-reference event alignment tail')
    relative = {at-info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value']+end*4}
    return raw[:end*4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('LinkedOwnerOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-pair-reference',
        (root / ASM).read_text(), FUNCTION)


def normalized(raw, bindings):
    if len(raw)!=BODY or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Pair reference raw body/bindings changed')
    words=list(struct.unpack('>41I',raw))
    def register(reg):return {2:3,3:2}.get(reg,reg)
    changed={}
    for index in range(22,35):
        word=words[index];op=word>>26
        if op in (35,43):other=(word&~(31<<16))|(register(word>>16&31)<<16)
        elif op==21:other=(word&~((31<<21)|(31<<16)))|(register(word>>21&31)<<21)|(register(word>>16&31)<<16)
        else:other=word
        if other!=word:changed[index*4]=(word,other);words[index]=other
    if changed!={at:(v,REPLACEMENT[at])for at,v in EXPECTED.items()}:
        raise ValueError('Pair reference allocation cycle is not closed')
    return struct.pack('>41I',*words),dict(bindings)
    if len(raw) != SIZE or digest(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Pair-reference event raw extent or binding changed')
    words = list(struct.unpack('>44I', raw))
    for offset, wanted in EXPECTED.items():
        if words[offset // 4] != wanted:
            raise ValueError('Pair-reference event checked spill input changed')
        words[offset // 4] = REPLACEMENT[offset]
    return struct.pack('>44I', *words), dict(bindings)


def guard_bytes(old):
    if digest(old) != GUARD_SHA:
        raise ValueError('Pair-reference event guard prefix changed')
    fields = ['filename','function','offset','expected','replacement','expected_relocations',
              'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    reader = csv.DictReader(io.StringIO(old.decode()))
    if reader.fieldnames != fields or any(row['function'] == FUNCTION for row in reader):
        raise ValueError('Pair-reference event guard prefix/schema changed')
    newline = '\r\n' if old.endswith(b'\r\n') else '\n'
    if not old.endswith(newline.encode()):
        raise ValueError('Pair-reference event guard terminator missing')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator=newline)
    for offset, wanted in EXPECTED.items():
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%offset,
            expected='0x%08X'%wanted,replacement='0x%08X'%REPLACEMENT[offset],
            expected_relocations='-',replacement_relocations='-',
            note='Normalize the closed v0/v1 pair-reference allocation cycle',omit='false'))
    return old + stream.getvalue().encode()


def check_inputs(root, output, installed=False):
    values = snapshot(output)
    for name, before in values.items():
        expected = recovered_owner(before.decode()).encode() if installed and name == SOURCE else (
            predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM+SIZE])
            if installed and name == 'conker/build/conker.us.elf' else
            guard_bytes(before) if installed and name == 'conker/retail_word_patches.us.csv' else before)
        if (root / name).read_bytes() != expected:
            raise ValueError('Pair-reference event current input differs: ' + name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    isolated,dc=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED,'selected')
    if diagnostics(da)!=diagnostics(db) or dc:raise ValueError('Pair reference owner diagnostics changed: '+da+db+dc)
    truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    raw,bindings=payload(isolated)
    if payload(after)!=(raw,bindings) or payload(original(root,output))!=normalized(raw,bindings):
        raise ValueError('Pair reference raw/fitted/original payload differs')
    linked,functions=link_owner(root,output,original(root,output),OWNER);at=functions[FUNCTION]['value']
    if linked[at:at+SIZE]!=truth:raise ValueError('Pair reference original full slot differs')
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv']))
    padded=output/'qualified-padded.s'
    padded.write_text(pad_c_object.emit_padded_assembly(after,root/'conker/retail_layout.us.txt',OWNER,word_patches_path=guards))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(info)for n,info in fa.items()}
    if expected[FUNCTION]['size']!=24:raise ValueError('Pair reference old extent changed')
    expected[FUNCTION]['size']=BODY;at=fb[FUNCTION]['value'];slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]:raise ValueError('Pair reference predecessor differs')
    if expected!=fb or b[at:at+SIZE]!=truth or a[:at]!=b[:at] or a[at+SIZE:]!=b[at+SIZE:]:
        raise ValueError('Pair reference padded owner extent/body/address differs: '+repr((expected[FUNCTION],fb[FUNCTION])))
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:raise ValueError('Pair reference neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Pair reference pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(body_words=41,slot_words=44,alignment_words=3,frame=24,bindings=1,new_guards=5,compiler_only=False,
        raw_SHA256=digest(raw),retail_SHA256=digest(truth),preserved_neighbors=neighbors,
        target_size_before=24,target_size_after=BODY,owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report
    values = check_inputs(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, HEADERS+DECLARATIONS+SELECTED, 'selected')
    if da or db or dc:
        raise ValueError('Pair-reference event compiler diagnostics: ' + da + db + dc)
    truth = values['conker/conker.us.bin'][ROM:ROM+SIZE]
    raw, bindings = payload(isolated)
    if len(raw) != SIZE or payload(after) != (raw, bindings) or payload(original(root, output)) != normalized(raw, bindings):
        raise ValueError('Pair-reference event direct C or independent original differs')
    original_object = original(root, output)
    linked, functions = link_owner(root, output, original_object, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at+SIZE] != truth or sum(map(len, bindings.values())) != 1:
        raise ValueError('Pair-reference event linked body or bindings differ')
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
        raise ValueError('Unknown pair-reference event predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE] != values['conker/build/conker.us.elf'][slot:slot+SIZE]:
        raise ValueError('Pair-reference event predecessor object/image disagreement')
    if expected != fb or b[at:at+SIZE] != truth or a[:at] != b[:at] or a[at+SIZE:] != b[at+SIZE:]:
        raise ValueError('Pair-reference event padding changed another extent/body/address')
    neighbors = same_functions(before,after,(FUNCTION,))
    if neighbors != 22 or same_functions(old,obj,(FUNCTION,)) != neighbors:
        raise ValueError('Pair-reference event neighbors changed')
    if normalized_pools(before) != normalized_pools(after) or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Pair-reference event owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report = dict(words=44,frame=32,relocations=1,new_guards=2,compiler_only=False,
        raw_SHA256=digest(raw),retail_SHA256=digest(truth),preserved_neighbors=neighbors,all_owner_addresses_fixed=True,
        target_size_before=12,target_size_after=SIZE,compiler_diagnostics_empty=True,helper_stub_unchanged=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    shadow = output/'make-shadow';(shadow/'src').mkdir(parents=True,exist_ok=True)
    conker = root/'conker'
    target = (shadow/'src/game_1944C0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
        cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n','').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
            raise ValueError('Unexpected pair-reference event Make command: '+repr(args))
        args = [(output/'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game_1944C0.c' else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()
                if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown pair-reference event Make redirect')
            redirect = (conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p = subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'after-owner-diagnostics.txt').read_text() if args[0]=='../ido/ido5.3_recomp/cc' else ''
        if p.returncode or diagnostics(p.stderr)!=diagnostics(expected) or (redirect is None and p.stdout):
            raise ValueError('Pair-reference event Make command failed: '+p.stdout+p.stderr)
        if redirect is not None:
            redirect.write_text(p.stdout)
        commands.append(args)
    actual = conker/target
    compilers = [a for a in commands if a[0] == '../ido/ido5.3_recomp/cc']
    processors = [a for a in commands if a[0] == 'python3' and a[1] == '../tools/asm-processor/asm_processor.py']
    if len(commands) != 3 or processors or len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2','-g3')):
        raise ValueError('Pair-reference event normal Make profile changed')
    if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),()) != len(parse_object(output/'after-owner.o')[1]):
        raise ValueError('Pair-reference event actual Make compact functions differ')
    if actual.read_bytes() != (output/'qualified-padded.o').read_bytes():
        raise ValueError('Pair-reference event actual Make object differs')
    report = dict(actual_Make_commands=3,normal_O2_g3=True,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_Make_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, truth):
    if digest(before) != '722cbc9e2520db992ef0b045f2c6bb22aba24fba8051b7b3bf1d4d1d5b8075f8' or digest(truth) != RETAIL_SHA:
        raise ValueError('Pair-reference event strict image predecessor/body changed')
    result = bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows = [offset for offset,name,fields,_ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY,24) and fields[3]&15 == 2]
    if len(rows) != 1:
        raise ValueError('Pair-reference event symbol predecessor extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before,truth):
        raise ValueError('Pair-reference event image differs from strict body/size prediction')


def predict(root, output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game_1944C0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown pair-reference event link input')
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
        raise ValueError('Pair-reference event independent image or object changed')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Pair-reference event changed another function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes']) != (True,189088,720,0):
        raise ValueError('Pair-reference event protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
