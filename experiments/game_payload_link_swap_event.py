"""Payload-link swap callback, checked register-role cycle and alignment tail."""
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

BUILD = 'conker/build/game-payload-link-swap-event/qualified'
SNAPSHOT_SHA = '849e8adb8f770939758036a4fb893fc4f407c1fd994e05c386b668660ef9ca89'
BEFORE_OBJECT_SHA = 'dba1daa56e29f2a9c18cfa468a32b9eb68c22e9583fcb9e32fcbbafca15a7dc7'
GUARD_SHA = '9098e84194afe81708a9940a961f287660cf04db4518a1e3fdbcee923d81116c'
BEFORE_ELF_SHA = 'd17262679d4a53f6f0621bf2dddd7b072f121850af56383f9bd670c0676e69f5'
SOURCE = 'conker/src/game/generated_1BFDD0.c'
OBJECT = 'conker/build/src/game/generated_1BFDD0.c.o'
FUNCTION, ENTRY, ROM, SIZE, SLOT_SIZE = 'func_151932E0', 0x151932E0, 0x1C0790, 172, 176
DECLARATIONS = 'typedef struct { u8 *owner; u8 identity; u8 opaque5[3]; } EmbeddedOwnerLink;\ntypedef struct { u8 *before; u8 *after; u8 before_identity; u8 after_identity; u8 opaqueA[2]; } OwnerLinkEvent;\n'
SELECTED = {'func_151932E0': '/* Retarget the payload owner link or release its matching actor. */\nvoid func_151932E0(struct260 *owner, s32 eventAddress, u8 command) {\n    EmbeddedOwnerLink *link = (EmbeddedOwnerLink *)((u8 *)owner + 0x28);\n    OwnerLinkEvent *event = (OwnerLinkEvent *)eventAddress;\n\n    if (command == 0x2D) {\n        u8 *current = link->owner;\n        if (current == event->before) {\n            link->owner = event->after;\n            link->identity = event->after_identity;\n        } else if (current == event->after) {\n            link->owner = event->before;\n            link->identity = event->before_identity;\n        }\n    } else if (command == 0) {\n        u8 *first = event->before;\n        if (first == link->owner || link->identity == ((u8 *)event)[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    }\n}'}
TARGETS = {'func_151932E0': dict(entry=ENTRY,rom=ROM,size=SIZE,slot_size=SLOT_SIZE,offset=0x28,
    owner='generated_1BFDD0',asm='conker/asm/1BFDD0.s',source=SOURCE,
    raw_SHA256='00311607be3f803315d4dc1683cd884d1fe3dd2dd4cfc6aa0c38c74e301e89d2',
    parent=0x15149434,parent_size=92,parent_source='conker/src/game/done/game_1765E0.c',
    table=0x8008A8D8,table_rom=0x22F398,count=74,index=22,selector=0x13)}

ISOLATED_HEADERS = '#include <ultra64.h>\n#include "structs.h"\nvoid func_1516972C(struct102 *);\n'
FUNCTIONS = tuple(TARGETS)
BINDINGS = {148: [('R_MIPS_26', 'func_1516972C')]}
RAW_ROLE_WORDS = {10: 2353201152, 11: 2359558144, 20: 1417216019, 22: 2890137600}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def object_path(target):
    return 'conker/build/src/game/' + target['owner'] + '.c.o'


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def input_hashes(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:
        raise ValueError('Link-swap frozen manifest changed')
    return json.loads(raw)['INPUTS']


def snapshot(output):
    values={}
    for name,wanted in input_hashes(output).items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:
            raise ValueError('Link-swap frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:
        raise ValueError('Link-swap predecessor object changed')
    return values


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,old in values.items():
        expected=(recovered_owner(FUNCTION,old.decode()).encode()if installed and name==SOURCE else
                  guard_bytes(old)if installed and name=='conker/retail_word_patches.us.csv'else
                  predicted_image(old,values['conker/conker.us.bin'])if installed and name=='conker/build/conker.us.elf'else old)
        if(root/name).read_bytes()!=expected:
            raise ValueError('Link-swap current input differs: '+name)
    return values


def freeze(root,output):
    return check_inputs(root,output)


def recovered_owner(name,before):
    lo,hi=function_span(before,name)
    if before[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:
        raise ValueError('Unknown link-swap placeholder')
    return before[:lo]+SELECTED[name]+before[hi:]


def payload(obj, name):
    text, functions, bindings = parse_object(obj)
    info = functions[name]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero owner-link alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output, name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('OwnerLinkOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-' + name,
        (root / TARGETS[name]['asm']).read_text(), name)


def role_word(word, commute=False):
    op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
    if op not in (4, 21, 35, 36, 40, 43):
        raise ValueError('Unexpected instruction in closed owner-link role window')
    rename = {3: 4, 4: 3}
    rs, rt = rename.get(rs, rs), rename.get(rt, rt)
    if commute:
        if op != 21:
            raise ValueError('Only the commutative BNEL operands may exchange')
        rs, rt = rt, rs
    return (word & ~0x03FF0000) | rs << 21 | rt << 16


def normalized(name, raw, bindings):
    if len(raw) != 172 or digest(raw) != TARGETS[name]['raw_SHA256'] or bindings != BINDINGS:
        raise ValueError('Owner-link raw body/bindings changed: ' + name)
    words = list(struct.unpack('>43I', raw))
    if any(words[i] != word for i, word in RAW_ROLE_WORDS.items()) or words[12] != 0x54640007:
        raise ValueError('Owner-link role inputs changed')
    fitted = list(words)
    # Both equality tests commute; the symmetric first test remains byte-identical.
    for i in range(10, 25):
        fitted[i] = role_word(words[i], commute=i in (12, 20))
    if {i for i in range(43) if words[i] != fitted[i]} != set(RAW_ROLE_WORDS):
        raise ValueError('Owner-link role cycle is not closed at its four declared words')
    return struct.pack('>43I', *fitted), dict(bindings)


def guard_bytes(old):
    if digest(old) != GUARD_SHA:
        raise ValueError('Owner-link guard prefix changed')
    reader = csv.DictReader(io.StringIO(old.decode()))
    fields = ['filename','function','offset','expected','replacement','expected_relocations',
              'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    if reader.fieldnames != fields or any(row['function'] in FUNCTIONS for row in reader):
        raise ValueError('Owner-link guard schema/predecessor changed')
    newline = '\r\n' if old.endswith(b'\r\n') else '\n'
    if not old.endswith(newline.encode()):
        raise ValueError('Owner-link guard newline changed')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator=newline)
    for name, target in TARGETS.items():
        for i, word in RAW_ROLE_WORDS.items():
            writer.writerow(dict(filename=target['owner'], function=name, offset='0x%03X' % (4*i),
                expected='0x%08X' % word, replacement='0x%08X' % role_word(word, commute=i == 20),
                expected_relocations='-', replacement_relocations='-',
                note='Normalize closed embedded-owner pointer register cycle and equality operand order',
                insert_after='', insert_after_relocations='', omit='false'))
    return old + stream.getvalue().encode()


def qualify(root, output):
    values = freeze(root, output)
    guards = output / 'qualified-guards.csv'
    guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv']))
    rows = []
    for name, target in TARGETS.items():
        wanted = recovered_owner(name, values[target['source']].decode())
        before, da = compile_owner(root, output, values[target['source']].decode(), name+'-before')
        after, db = compile_owner(root, output, wanted, name+'-after')
        isolated, dc = compile_owner(root, output, ISOLATED_HEADERS+DECLARATIONS+SELECTED[name], name+'-selected')
        if diagnostics(da) != diagnostics(db) or dc:
            raise ValueError('Owner-link diagnostics changed: '+name+'\n'+da+db+dc)
        raw, bindings = payload(isolated, name)
        fitted, rb = normalized(name, raw, bindings)
        if payload(after, name) != (raw, bindings) or payload(original(root, output, name), name) != (fitted, rb):
            raise ValueError('Owner-link complete owner/GNU original differs: '+name)
        data, fs = link_owner(root, output, isolated, target['owner'])
        actual = data[fs[name]['value']:fs[name]['value']+172]
        truth = values['conker/conker.us.bin'][target['rom']:target['rom']+172]
        expected = bytearray(truth)
        for i, word in RAW_ROLE_WORDS.items():
            struct.pack_into('>I', expected, i*4, word)
        if actual != expected:
            raise ValueError('Owner-link has undeclared linked raw differences: '+name)
        neighbors = same_functions(before, after, (name,))
        old = output / 'before-padded.o'
        if neighbors != len(parse_object(old)[1])-1 or normalized_pools(before) != normalized_pools(after):
            raise ValueError('Owner-link raw neighbors/pools changed: '+name)
        assembly = output / 'qualified-padded.s'
        assembly.write_text(emit_padded_assembly(after, root / target['asm'],
            word_patches_path=guards, filename=target['owner']))
        padded = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-I',str(root/'conker/include'),'-o',str(padded),str(assembly)],capture_output=True,check=True)
        a, fa = link_owner(root, output, old, target['owner'])
        b, fb = link_owner(root, output, padded, target['owner'])
        expected_fs = {symbol:dict(info) for symbol,info in fa.items()}
        if expected_fs[name]['size'] != 12:
            raise ValueError('Unknown owner-link predecessor extent')
        expected_fs[name]['size'] = 172
        at = fb[name]['value'];slot = elf_slot_offset(values['conker/build/conker.us.elf'],target['entry'],172)
        if a[at:at+172] != values['conker/build/conker.us.elf'][slot:slot+172]:
            raise ValueError('Owner-link predecessor object/ELF mismatch')
        if expected_fs != fb or b[at:at+172] != truth or a[:at] != b[:at] or a[at+172:] != b[at+172:]:
            raise ValueError('Owner-link padding changed another body/address/extent')
        if same_functions(old,padded,(name,)) != neighbors or normalized_pools(old) != normalized_pools(padded):
            raise ValueError('Owner-link padded neighbors/pools changed')
        (output/'proposed-owner.c').write_text(wanted)
        rows.append(dict(function=name,words=43,frame=24,bindings=1,new_guards=4,
            raw_differences=4,preserved_neighbors=neighbors,raw_SHA256=digest(raw)))
    report=dict(targets=rows,total_words=43,new_guards=4,compiler_only=False,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,
        all_owner_addresses_fixed=True,preserved_neighbors=sum(row['preserved_neighbors']for row in rows),
        slot_words=44,alignment_tail_words=1)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output);conker = root/'conker';shadow = output/'make-shadow'
    (shadow/'src/game').mkdir(parents=True,exist_ok=True);reports=[]
    for name,target in TARGETS.items():
        proposal=output/'proposed-owner.c'
        if proposal.read_text()!=recovered_owner(name,values[target['source']].decode()):
            raise ValueError('Owner-link shadow source changed')
        target_path=(shadow/('src/game/'+target['owner']+'.c.o')).relative_to(conker).as_posix()
        plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target_path],
            cwd=conker,capture_output=True,text=True,check=True)
        (output/(name+'-Make-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
        for line in plan.stdout.replace('\\\n','').splitlines():
            args=shlex.split(line)
            if not args or args[0]=='rm':continue
            if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
                raise ValueError('Unexpected owner-link Make command')
            args=[proposal.relative_to(conker).as_posix()if a==target['source'][7:]else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown Make redirect')
                redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
            q=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            expected=(output/(name+'-after-diagnostics.txt')).read_text()if args[0]=='../ido/ido5.3_recomp/cc'else ''
            if q.returncode or diagnostics(q.stderr+(q.stdout if redirect is None else ''))!=diagnostics(expected):
                raise ValueError('Owner-link Make command failed: '+q.stdout+q.stderr)
            if redirect is not None:redirect.write_text(q.stdout)
            commands.append(args)
        cc=[args for args in commands if args[0]=='../ido/ido5.3_recomp/cc']
        actual=conker/target_path
        if len(commands)!=3 or len(cc)!=1 or not all(flag in cc[0]for flag in('-O2','-g3')):
            raise ValueError('Owner-link actual compiler recipe/profile changed')
        if same_functions(output/(name+'-after.o'),Path(str(actual)+'.compact'))!=len(parse_object(output/(name+'-after.o'))[1]):
            raise ValueError('Owner-link Make raw owner differs')
        if link_owner(root,output,actual,target['owner'])!=link_owner(root,output,output/'qualified-padded.o',target['owner']):
            raise ValueError('Owner-link Make padded owner differs')
        reports.append(dict(function=name,actual_Make_commands=3,normal_O2_g3=True))
    report=dict(targets=reports,actual_Make_commands=3,all_raw_functions_equal=True,padded_code_and_metadata_equal=True)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predicted_image(before, rom):
    if digest(before)!=BEFORE_ELF_SHA:
        raise ValueError('Owner-link strict image predecessor changed')
    tail=rom[ROM+SIZE:ROM+SLOT_SIZE]
    at=elf_slot_offset(before,ENTRY,SLOT_SIZE)
    if tail!=bytes(4)or before[at+SIZE:at+SLOT_SIZE]!=tail:
        raise ValueError('Link-swap single alignment word changed')
    result=bytearray(before)
    for name,target in TARGETS.items():
        at=elf_slot_offset(before,target['entry'],172);result[at:at+172]=rom[target['rom']:target['rom']+172]
        rows=[offset for offset,symbol,fields,_ in symbol_rows(before)
              if symbol==name and fields[1:3]==(target['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('Owner-link symbol extent predecessor changed')
        struct.pack_into('>I',result,rows[0]+8,172)
    return bytes(result)


def check_image(before, actual, rom):
    if actual!=predicted_image(before,rom):
        raise ValueError('Owner-link image differs from strict body/size prediction')


def predict(root, output):
    values=freeze(root,output);script=(root/'conker/build/conker.ld').read_text()
    for target in TARGETS.values():
        old=object_path(target)[7:]
        if script.count(old)!=1:raise ValueError('Unknown owner-link link input')
        script=script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix())
    link=output/'first-link.ld';link.write_text(script);elf=output/'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt',
        '-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
        '--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(root/'conker').as_posix()],
        cwd=root/'conker',capture_output=True,check=True)
    before=values['conker/build/conker.us.elf'];actual=elf.read_bytes();rom=values['conker/conker.us.bin']
    check_image(before,actual,rom);changed=sum(a!=b for a,b in zip(before,actual));code=0
    for target in TARGETS.values():
        at=elf_slot_offset(before,target['entry'],172)
        code+=sum(a!=b for a,b in zip(before[at:at+172],rom[target['rom']:target['rom']+172]))
    report=dict(exact_prediction=True,SHA256=digest(actual),changed_bytes=changed,
        code_bytes_changed=code,metadata_bytes_changed=changed-code,metadata_exclusions=0)
    (output/'first-link.json').write_text(json.dumps(report,indent=2)+'\n');return report


def audit(root, output):
    values=snapshot(output);rom=values['conker/conker.us.bin'];wanted=predicted_image(values['conker/build/conker.us.elf'],rom)
    sources={t['source']:name for name,t in TARGETS.items()}
    for name,old in values.items():
        expected=recovered_owner(sources[name],old.decode()).encode()if name in sources else guard_bytes(old)if name=='conker/retail_word_patches.us.csv'else wanted if name=='conker/build/conker.us.elf'else old
        if(root/name).read_bytes()!=expected:raise ValueError('Owner-link installed input differs: '+name)
    if(output/'first-linked.elf').read_bytes()!=wanted:raise ValueError('Owner-link first image changed')
    for target in TARGETS.values():
        if(root/object_path(target)).read_bytes()!=(output/'qualified-padded.o').read_bytes():
            raise ValueError('Owner-link installed object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or {name for name in a if a[name]!=b[name]}!=set(FUNCTIONS):
        raise ValueError('Owner-link changed another body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Owner-link protected data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,
        total_words=43,new_guards=4,strict_first_link_reproduced=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
