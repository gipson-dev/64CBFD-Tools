"""Sequence command dispatch with explicit address/control scheduling and strict image gates."""
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
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION, ENTRY, ROM, SIZE = 'func_1509E640', 0x1509E640, 0xCBAF0, 176
BODY = SIZE
OWNER, SOURCE, ASM = 'generated_CBAF0', 'conker/src/game/generated_CBAF0.c', 'conker/asm/CBAF0.s'
OBJECT = 'conker/build/src/game/generated_CBAF0.c.o'
BUILD = 'conker/build/game-sequence-event-dispatch/qualified'
SNAPSHOT_SHA = '5eaca27d4ba6c8a8dbdf4a13b44e733c31af0ea876359364e7873991d6a6bbf1'
BEFORE_OBJECT_SHA = '4dc735fe6d86563c29830189c7e4fbe2d4d3d52ba7c0220f07bbcec47a373874'
RETAIL_SHA = '593065996ce157a660ff459f1931856f28fa03706f334a6ed28ffd4c9b9225ed'
HEADERS = '#include <ultra64.h>\n'
DECLARATIONS = '''extern s32 D_800D3840;
void func_1001263C(s32, s32, s32);
void func_151F2D6C(s32, s32);
void func_151F2BA8(void);
'''
SYMBOLS={'D_800D3840':0x800D3840,'func_1001263C':0x1001263C,'func_151F2D6C':0x151F2D6C,'func_151F2BA8':0x151F2BA8}
BINDINGS={12:[('R_MIPS_HI16','D_800D3840')],48:[('R_MIPS_LO16','D_800D3840')],
    72:[('R_MIPS_26','func_1001263C')],24:[('R_MIPS_HI16','D_800D3840')],
    88:[('R_MIPS_LO16','D_800D3840')],112:[('R_MIPS_26','func_151F2D6C')],
    128:[('R_MIPS_26','func_151F2D6C')],144:[('R_MIPS_26','func_151F2BA8')]}
RAW_SHA='4d6ba0007690260651de4ff3f2da7ef73a1702922a48493445e770b4ee1342dd'
GUARD_SHA='43cb13987e7ff85caae6bd18ca277b1d616ea0fe5a75708c8842bb84c5a53e65'
SELECTED='''/* Dispatch sequence start, level, and stop requests from the script packet. */
s32 func_1509E640(s32 sequence, s32 command, s32 *packet) {
    s32 level;

    switch (command) {
        case 0:
            level = 0x7FFF;
            if (D_800D3840 >= 3) {
                level = packet[2];
            }
            func_1001263C(sequence, level, 0x40);
            return 1;
        case 1:
            if (D_800D3840 == 4) {
                func_151F2D6C(packet[2], packet[3]);
            } else {
                func_151F2D6C(packet[2], 0);
            }
            return 1;
        case 2:
            func_151F2BA8();
            return 1;
    }
    return 0;
}'''

def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    import re
    return re.sub(r"line\s+\d+","line #",re.sub(r"\S+\.c","<unit>",text))


def snapshot(output):
    raw = (output / 'input-snapshot.json').read_bytes()
    if digest(raw) != SNAPSHOT_SHA:
        raise ValueError('Sequence event frozen input manifest changed')
    manifest = json.loads(raw)
    values = {}
    for name, wanted in manifest['INPUTS'].items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Sequence event historical input changed: ' + name)
        values[name] = data
    if digest((output / 'before-padded.o').read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Sequence event predecessor object changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE]) != RETAIL_SHA:
        raise ValueError('Sequence event retail slot changed')
    return values


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1509E640() {\n    return 0;\n}':raise ValueError('Unknown sequence command placeholder')
    return before[:lo]+DECLARATIONS+'\n'+SELECTED+before[hi:]
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi] != 'void func_15169850(s32 arg0, u8 arg1, s32 arg2, s32 arg3, s32 arg4) {\n}':
        raise ValueError('Unknown sequence event placeholder')
    marker='/* Non-matching C placeholders for asm/nonmatchings/game_1944C0/func_15169850.s. */\n'
    if before.count(marker)!=1:raise ValueError('Sequence event placeholder marker changed')
    return (before[:lo]+SELECTED+before[hi:]).replace(marker,'')
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151A4ECC() {\n    return 0;\n}':
        raise ValueError('Unknown sequence-event event predecessor')
    return before[:lo] + SELECTED + before[hi:]



def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero sequence-event event alignment tail')
    relative = {at-info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value']+end*4}
    return raw[:end*4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('LinkedOwnerOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-sequence-event',
        (root / ASM).read_text(), FUNCTION)


def normalized(raw,bindings):
    if len(raw)!=176 or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Sequence raw body/bindings changed')
    words=list(struct.unpack('>44I',raw));order=list(range(44))
    order[6:22]=list(range(7,22))+[6]
    order[24:34]=[25,33,27,28,29,30,31,26,32,24]
    if sorted(order)!=list(range(44)):raise ValueError('Sequence instruction permutation is not closed')
    fit=[words[i]for i in order]
    for i,delta in((2,-1),(5,-1),(7,1),(9,1),(19,1),(29,1)):
        if fit[i]>>26 not in(4,5):raise ValueError('Sequence crossing branch changed')
        fit[i]=(fit[i]&0xFFFF0000)|((fit[i]+delta)&65535)
    if fit[24]>>26!=5 or fit[31]!=0 or fit[25]!=fit[26] or fit[25]!=0x8CC40008:
        raise ValueError('Sequence two-arm delay layout changed')
    fit[24]=(fit[24]&0x03FF0000)|(21<<26)|((fit[24]+1)&65535)
    fit[31]=fit[25]
    moved={4*order.index(at//4):rows for at,rows in bindings.items()}
    if sum(a!=b for a,b in zip(words,fit))!=27 or len(moved)!=8:
        raise ValueError('Sequence measured word/binding set changed')
    return struct.pack('>44I',*fit),moved
    if len(raw)!=BODY or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Sequence event raw body/bindings changed')
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
        raise ValueError('Sequence event allocation cycle is not closed')
    return struct.pack('>41I',*words),dict(bindings)
    if len(raw) != SIZE or digest(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Sequence event raw extent or binding changed')
    words = list(struct.unpack('>44I', raw))
    for offset, wanted in EXPECTED.items():
        if words[offset // 4] != wanted:
            raise ValueError('Sequence event checked spill input changed')
        words[offset // 4] = REPLACEMENT[offset]
    return struct.pack('>44I', *words), dict(bindings)


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Sequence guard prefix changed')
    fields=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations',
            'note','insert_after','insert_after_relocations','omit']
    reader=csv.DictReader(io.StringIO(old.decode()))
    if reader.fieldnames!=fields or any(row['function']==FUNCTION for row in reader):raise ValueError('Sequence guard schema/history changed')
    fit,moved=normalized(raw,bindings);newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Sequence guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator=newline);count=0
    reloc=lambda rows:';'.join(kind+':'+name for kind,name in rows)or'-'
    for i,(a,b)in enumerate(zip(struct.unpack('>44I',raw),struct.unpack('>44I',fit))):
        at=4*i;before,after=bindings.get(at,[]),moved.get(at,[])
        if a!=b or before!=after:
            writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,
                expected='0x%08X'%a,replacement='0x%08X'%b,
                expected_relocations=reloc(before),replacement_relocations=reloc(after),
                note='Restore derived address rotation and two-arm call schedule; retain the unreachable duplicate load',
                omit='false'))
            count+=1
    if count!=27:raise ValueError('Sequence guard count changed')
    return old+stream.getvalue().encode()
    if digest(old) != GUARD_SHA:
        raise ValueError('Sequence event guard prefix changed')
    fields = ['filename','function','offset','expected','replacement','expected_relocations',
              'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    reader = csv.DictReader(io.StringIO(old.decode()))
    if reader.fieldnames != fields or any(row['function'] == FUNCTION for row in reader):
        raise ValueError('Sequence event guard prefix/schema changed')
    newline = '\r\n' if old.endswith(b'\r\n') else '\n'
    if not old.endswith(newline.encode()):
        raise ValueError('Sequence event guard terminator missing')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator=newline)
    for offset, wanted in EXPECTED.items():
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%offset,
            expected='0x%08X'%wanted,replacement='0x%08X'%REPLACEMENT[offset],
            expected_relocations='-',replacement_relocations='-',
            note='Normalize the closed v0/v1 sequence-event allocation cycle',omit='false'))
    return old + stream.getvalue().encode()


def check_inputs(root, output, installed=False):
    values = snapshot(output)
    for name, before in values.items():
        expected = recovered_owner(before.decode()).encode() if installed and name == SOURCE else (
            predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM+SIZE])
            if installed and name == 'conker/build/conker.us.elf' else
            guard_bytes(before,*payload(output/'after-owner.o')) if installed and name == 'conker/retail_word_patches.us.csv' else before)
        if (root / name).read_bytes() != expected:
            raise ValueError('Sequence event current input differs: ' + name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    isolated,dc=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED,'selected')
    if diagnostics(da)!=diagnostics(db) or dc:raise ValueError('Sequence event owner diagnostics changed: '+da+db+dc)
    truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    raw,bindings=payload(isolated)
    if payload(after)!=(raw,bindings) or payload(original(root,output))!=normalized(raw,bindings):
        raise ValueError('Sequence event raw/fitted/original payload differs')
    linked,functions=link_owner(root,output,original(root,output),OWNER);at=functions[FUNCTION]['value']
    if linked[at:at+SIZE]!=truth:raise ValueError('Sequence event original full slot differs')
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],raw,bindings))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(info)for n,info in fa.items()}
    if expected[FUNCTION]['size']!=12:raise ValueError('Sequence event old extent changed')
    expected[FUNCTION]['size']=BODY;at=fb[FUNCTION]['value'];slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]:raise ValueError('Sequence event predecessor differs')
    if expected!=fb or b[at:at+SIZE]!=truth or a[:at]!=b[:at] or a[at+SIZE:]!=b[at+SIZE:]:
        raise ValueError('Sequence event padded owner extent/body/address differs: '+repr((expected[FUNCTION],fb[FUNCTION])))
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:raise ValueError('Sequence event neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Sequence event pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(body_words=44,slot_words=44,alignment_words=0,frame=24,bindings=8,new_guards=27,compiler_only=False,
        raw_SHA256=digest(raw),retail_SHA256=digest(truth),preserved_neighbors=neighbors,
        instruction_permutation_closed=True,crossing_branch_repairs=6,likely_branch_repairs=1,unreachable_duplicate_load_words=1,
        target_size_before=12,target_size_after=BODY,owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report
    values = check_inputs(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, HEADERS+DECLARATIONS+SELECTED, 'selected')
    if da or db or dc:
        raise ValueError('Sequence event compiler diagnostics: ' + da + db + dc)
    truth = values['conker/conker.us.bin'][ROM:ROM+SIZE]
    raw, bindings = payload(isolated)
    if len(raw) != SIZE or payload(after) != (raw, bindings) or payload(original(root, output)) != normalized(raw, bindings):
        raise ValueError('Sequence event direct C or independent original differs')
    original_object = original(root, output)
    linked, functions = link_owner(root, output, original_object, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at+SIZE] != truth or sum(map(len, bindings.values())) != 1:
        raise ValueError('Sequence event linked body or bindings differ')
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
        raise ValueError('Unknown sequence-event event predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE] != values['conker/build/conker.us.elf'][slot:slot+SIZE]:
        raise ValueError('Sequence event predecessor object/image disagreement')
    if expected != fb or b[at:at+SIZE] != truth or a[:at] != b[:at] or a[at+SIZE:] != b[at+SIZE:]:
        raise ValueError('Sequence event padding changed another extent/body/address')
    neighbors = same_functions(before,after,(FUNCTION,))
    if neighbors != 22 or same_functions(old,obj,(FUNCTION,)) != neighbors:
        raise ValueError('Sequence event neighbors changed')
    if normalized_pools(before) != normalized_pools(after) or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Sequence event owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report = dict(words=44,frame=32,relocations=1,new_guards=2,compiler_only=False,
        raw_SHA256=digest(raw),retail_SHA256=digest(truth),preserved_neighbors=neighbors,all_owner_addresses_fixed=True,
        target_size_before=12,target_size_after=SIZE,compiler_diagnostics_empty=True,helper_stub_unchanged=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    shadow = output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
    conker = root/'conker'
    target = (shadow/'src/game/generated_CBAF0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
        cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n','').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
            raise ValueError('Unexpected sequence-event event Make command: '+repr(args))
        args = [(output/'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_CBAF0.c' else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()
                if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown sequence-event event Make redirect')
            redirect = (conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p = subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'after-owner-diagnostics.txt').read_text() if args[0]=='../ido/ido5.3_recomp/cc' else ''
        if p.returncode or diagnostics(p.stderr)!=diagnostics(expected) or (redirect is None and p.stdout):
            raise ValueError('Sequence event Make command failed: '+p.stdout+p.stderr)
        if redirect is not None:
            redirect.write_text(p.stdout)
        commands.append(args)
    actual = conker/target
    compilers = [a for a in commands if a[0] == '../ido/ido5.3_recomp/cc']
    processors = [a for a in commands if a[0] == 'python3' and a[1] == '../tools/asm-processor/asm_processor.py']
    if len(commands) != 3 or processors or len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2','-g3')):
        raise ValueError('Sequence event normal Make profile changed')
    if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),()) != len(parse_object(output/'after-owner.o')[1]):
        raise ValueError('Sequence event actual Make compact functions differ')
    if actual.read_bytes() != (output/'qualified-padded.o').read_bytes():
        raise ValueError('Sequence event actual Make object differs')
    report = dict(actual_Make_commands=3,normal_O2_g3=True,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_Make_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, truth):
    if digest(before) != '2538bae4ed9f6bb240faf0a26235db7983717b0a57fb16b566d8c0cc1d34e1c5' or digest(truth) != RETAIL_SHA:
        raise ValueError('Sequence event strict image predecessor/body changed')
    result = bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows = [offset for offset,name,fields,_ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY,12) and fields[3]&15 == 2]
    if len(rows) != 1:
        raise ValueError('Sequence event symbol predecessor extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before,truth):
        raise ValueError('Sequence event image differs from strict body/size prediction')


def predict(root, output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_CBAF0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown sequence-event event link input')
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
        raise ValueError('Sequence event independent image or object changed')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Sequence event changed another function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes']) != (True,189088,720,0):
        raise ValueError('Sequence event protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
