"""Two embedded-owner callbacks and a closed, scoped four-word role fit."""
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

BUILD = 'conker/build/game-record-key-tag-event/qualified'
INPUTS = {'conker/include/structs.h': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69', 'conker/include/functions.h': '2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81', 'conker/include/variables.h': '1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8', 'conker/include/macros.h': 'dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769', 'conker/include/2.0L/ultra64.h': '334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d', 'conker/include/2.0L/PR/ultratypes.h': '1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd', 'conker/symbol_addrs.us.txt': 'd0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106', 'conker/undefined_funcs_auto.txt': '3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6', 'conker/undefined_syms_auto.txt': 'a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd', 'conker/undefined_funcs.us.txt': '92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a', 'conker/undefined_syms.us.txt': 'd678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e', 'conker/build/conker.us.elf': '6fd87e9c5431f2a0145609d0d9e9bc31038189fba802074b5e6770919dbdd24d', 'conker/retail_word_patches.us.csv': 'bcd49d5d0ecb38b8765efa62ce8561f5e857b8a9b42c5bd75948ffa54d6708cb', 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382', 'conker/Makefile': '54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf', 'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be', 'conker/include/asm_processor_prelude.inc': 'c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d', 'conker/conker.ld': '217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8', 'conker/retail_layout.us.txt': 'a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5', 'conker/include/libc/string.h': 'ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5', 'conker/include/libc/stddef.h': 'e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721', 'conker/include/2.0L/PR/gbi.h': '155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6', 'conker/include/libc/stdarg.h': '759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4', 'conker/src/game/generated_FB600.c': 'a62f4ac88bdc13e642731064e8829d947f6e1004661ee372b9a11d8a11127111', 'conker/asm/FB600.s': '6b88d4730fd4278d33b811696f2c790b8b68ababc52607be60539d1457aa59f4', 'conker/src/game/generated_1028F0.c': '846621fb7a9d377081fab017973abcd197af40166ab952324dfd3911fb3aad6b', 'conker/asm/1028F0.s': '72d80bc3125215cf183a0e17248d51d7638a0eda31676750250490204ce2799e', 'conker/src/game/generated_18D250.c': 'c286bca51d829fa78feebd3334cfed5941262bfea002fb276f2359f1b9eaa64e', 'conker/asm/18D250.s': 'e44265c94a77782706cb602fe5d23f3010b592037b5c70dc9aa463df164fbeca', 'conker/src/game/generated_15D730.c': 'd0f516ae15199af4c85ad039c26414303a0f680193b3273515efed87d4755f16', 'conker/asm/15D730.s': '8fb9c9a1f9f8670726ba0ac21a52478813ca25903b7432146ec952d7b5062657', 'conker/asm/data/22FB90.rodata.s': 'e00d83a0d1b9673caec4f42f0a6defee0d4050c764db1000a6bd518beb3265b9', 'conker/asm/data/22E220.rodata.s': 'a6726700c15ce0ede735ac2cf240510daa6317bac16391c4680cebec4595ddec', 'conker/src/game_1944C0.c': '328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b'}
OBJECTS = {'conker/build/src/game/generated_FB600.c.o': '255a88f1753c2233ce2209ed3f1e8aea6cfef99dc7f1a1e26505161de002d551', 'conker/build/src/game/generated_1028F0.c.o': '67bd8e05f1f672e9607634111d0a4e252ca787d0f766bdb28eda784d032ce6a7'}
DECLARATIONS = '#include "structs.h"\n\ntypedef struct { u8 *owner; u8 identity; u8 opaque5[3]; } EmbeddedOwnerLink;\ntypedef struct { u8 *before; u8 *after; u8 before_identity; u8 after_identity; u8 opaqueA[2]; } OwnerLinkEvent;\n\nvoid func_1516972C(struct102 *);\n'
SELECTED = {'func_150CE694': '/* Retarget an embedded owner reference or release a matching reference. */\nvoid func_150CE694(u8 *owner, s32 eventAddress, u8 command) {\n    EmbeddedOwnerLink *link = (EmbeddedOwnerLink *)(owner + 0x18);\n    OwnerLinkEvent *event = (OwnerLinkEvent *)eventAddress;\n\n    if (command == 0x2D) {\n        u8 *current = link->owner;\n        if (current == event->before) {\n            link->owner = event->after;\n            link->identity = event->after_identity;\n        } else if (current == event->after) {\n            link->owner = event->before;\n            link->identity = event->before_identity;\n        }\n    } else if (command == 0) {\n        u8 *first = event->before;\n        if (first == link->owner || link->identity == ((u8 *)event)[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    }\n}', 'func_150D6E60': '/* Retarget an embedded owner reference or release a matching reference. */\nvoid func_150D6E60(u8 *owner, s32 eventAddress, u8 command) {\n    EmbeddedOwnerLink *link = (EmbeddedOwnerLink *)(owner + 0xA8);\n    OwnerLinkEvent *event = (OwnerLinkEvent *)eventAddress;\n\n    if (command == 0x2D) {\n        u8 *current = link->owner;\n        if (current == event->before) {\n            link->owner = event->after;\n            link->identity = event->after_identity;\n        } else if (current == event->after) {\n            link->owner = event->before;\n            link->identity = event->before_identity;\n        }\n    } else if (command == 0) {\n        u8 *first = event->before;\n        if (first == link->owner || link->identity == ((u8 *)event)[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    }\n}'}
TARGETS = {
    'func_150CE694': dict(entry=0x150CE694, rom=0xFBB44, size=172, offset=0x18,
        owner='generated_FB600', asm='conker/asm/FB600.s',
        source='conker/src/game/generated_FB600.c',
        raw_SHA256='57edf69ea16766717420246c52a6d1682e3562c8cbd61025b524f7e8f854545e',
        parent=0x15160090, parent_size=72, parent_source='conker/src/game/generated_18D250.c',
        table=0x8008B0E4, table_rom=0x22FBA4, count=3, index=2, selector=0x14),
    'func_150D6E60': dict(entry=0x150D6E60, rom=0x104310, size=172, offset=0xA8,
        owner='generated_1028F0', asm='conker/asm/1028F0.s',
        source='conker/src/game/generated_1028F0.c',
        raw_SHA256='5146553c4fe4c90b6eda4a36936cba8139b82cfe68d2e843972572bad852098e',
        parent=0x15131C2C, parent_size=88, parent_source='conker/src/game/generated_15D730.c',
        table=0x80089878, table_rom=0x22E338, count=14, index=8, selector=0x75),
}
FUNCTIONS = tuple(TARGETS)
BINDINGS = {148: [('R_MIPS_26', 'func_1516972C')]}
RAW_ROLE_WORDS = {10: 0x8C430000, 11: 0x8CA40000, 20: 0x54790013, 22: 0xAC440000}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def object_path(target):
    return 'conker/build/src/game/' + target['owner'] + '.c.o'


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Owner-link historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Owner-link predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Owner-link snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    for target in TARGETS.values():
        name = object_path(target)
        old = output / ('before-' + target['owner'] + '.o')
        data = old.read_bytes() if old.exists() else (root / name).read_bytes()
        if digest(data) != OBJECTS[name]:
            raise ValueError('Owner-link predecessor object changed: ' + name)
        if not old.exists():
            old.write_bytes(data)
    return snapshot(output)


def recovered_owner(name, before):
    lo, hi = function_span(before, name)
    if before[lo:hi] != 's32 %s() {\n    return 0;\n}' % name:
        raise ValueError('Unknown owner-link placeholder: ' + name)
    result = before[:lo] + SELECTED[name] + before[hi:]
    marker = '#include <ultra64.h>\n'
    if result.count(marker) != 1:
        raise ValueError('Unknown owner-link include boundary')
    return result.replace(marker, marker + DECLARATIONS, 1)


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
    for i in range(10, 23):
        fitted[i] = role_word(words[i], commute=i in (12, 20))
    if {i for i in range(43) if words[i] != fitted[i]} != set(RAW_ROLE_WORDS):
        raise ValueError('Owner-link role cycle is not closed at its four declared words')
    return struct.pack('>43I', *fitted), dict(bindings)


def guard_bytes(old):
    if digest(old) != INPUTS['conker/retail_word_patches.us.csv']:
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
        isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n'+DECLARATIONS+SELECTED[name], name+'-selected')
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
        old = output / ('before-'+target['owner']+'.o')
        if neighbors != len(parse_object(old)[1])-1 or normalized_pools(before) != normalized_pools(after):
            raise ValueError('Owner-link raw neighbors/pools changed: '+name)
        assembly = output / ('qualified-'+target['owner']+'.s')
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
        (output/('proposed-'+name+'.c')).write_text(wanted)
        rows.append(dict(function=name,words=43,frame=24,bindings=1,new_guards=4,
            raw_differences=4,preserved_neighbors=neighbors,raw_SHA256=digest(raw)))
    report=dict(targets=rows,total_words=86,new_guards=8,compiler_only=False,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,
        all_owner_addresses_fixed=True,preserved_neighbors=sum(row['preserved_neighbors']for row in rows))
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output);conker = root/'conker';shadow = output/'make-shadow'
    (shadow/'src/game').mkdir(parents=True,exist_ok=True);reports=[]
    for name,target in TARGETS.items():
        proposal=output/('proposed-'+name+'.c')
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
        if len(commands)!=5 or len(cc)!=1 or not all(flag in cc[0]for flag in('-O2','-g3')):
            raise ValueError('Owner-link actual compiler recipe/profile changed')
        if same_functions(output/(name+'-after.o'),Path(str(actual)+'.compact'))!=len(parse_object(output/(name+'-after.o'))[1]):
            raise ValueError('Owner-link Make raw owner differs')
        if link_owner(root,output,actual,target['owner'])!=link_owner(root,output,output/('qualified-'+target['owner']+'.o'),target['owner']):
            raise ValueError('Owner-link Make padded owner differs')
        reports.append(dict(function=name,actual_Make_commands=5,normal_O2_g3=True))
    report=dict(targets=reports,actual_Make_commands=10,all_raw_functions_equal=True,padded_code_and_metadata_equal=True)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predicted_image(before, rom):
    if digest(before)!=INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Owner-link strict image predecessor changed')
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
        script=script.replace(old,(output/('qualified-'+target['owner']+'.o')).relative_to(root/'conker').as_posix())
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
        if(root/object_path(target)).read_bytes()!=(output/('qualified-'+target['owner']+'.o')).read_bytes():
            raise ValueError('Owner-link installed object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or {name for name in a if a[name]!=b[name]}!=set(FUNCTIONS):
        raise ValueError('Owner-link changed another body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Owner-link protected data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-2,all_addresses_fixed=True,
        total_words=86,new_guards=8,strict_first_link_reproduced=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
