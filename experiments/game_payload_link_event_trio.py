"""Three payload owner-link callbacks with two closed register-allocation cycles."""
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

BUILD = 'conker/build/game-payload-link-event-trio/qualified'
INPUTS = {'conker/include/structs.h': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69', 'conker/include/functions.h': '2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81', 'conker/include/variables.h': '1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8', 'conker/include/macros.h': 'dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769', 'conker/include/2.0L/ultra64.h': '334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d', 'conker/include/2.0L/PR/ultratypes.h': '1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd', 'conker/symbol_addrs.us.txt': 'd0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106', 'conker/undefined_funcs_auto.txt': '3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6', 'conker/undefined_syms_auto.txt': 'a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd', 'conker/undefined_funcs.us.txt': '92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a', 'conker/undefined_syms.us.txt': 'd678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e', 'conker/build/conker.us.elf': 'af40284c5c7c36eb5e4a7edea75fd7680a88275767f0da332e8bc9534260cc57', 'conker/retail_word_patches.us.csv': '514908c88bb9f7608478de0e044172a7d12a6dc7d198b3372a6c954ae5748282', 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382', 'conker/Makefile': '54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf', 'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be', 'conker/include/asm_processor_prelude.inc': 'c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d', 'conker/conker.ld': '217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8', 'conker/retail_layout.us.txt': 'a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5', 'conker/include/libc/string.h': 'ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5', 'conker/include/libc/stddef.h': 'e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721', 'conker/include/2.0L/PR/gbi.h': '155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6', 'conker/include/libc/stdarg.h': '759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4', 'conker/src/game/done/game_1765E0.c': '19dd4f8a4e0561ad2de70ee59e12e50c11a9938357816dd0eacb2334d8c0c5af', 'conker/asm/data/22EF80.rodata.s': '0711a45ed594246cf7054df44d7e73dd1506372423061bf7e6d8f6b147eb7b79', 'conker/src/game_1944C0.c': '328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b', 'conker/build/src/game/done/game_1765E0.c.o': 'e25e23423217e12289d36ef8ddd82eb68ba757c7b708340995f7a7d8a987aabf', 'conker/src/game/generated_1CA420.c': '11037724e7235d20f4cf149a75a56cd7573c8d7da67496c7691f5efafaa894ae', 'conker/asm/1CA420.s': 'baf983dde476097672108e8ef7be0aa4c5aadc15f8b1a6ff36f12833d596ed54', 'conker/src/game/generated_1D0840.c': '24b2a049b1fd2cb260e95cebd56fc0560a92817eec5dd752cd9d4a11e7a4d903', 'conker/asm/1D0840.s': '776840f022dd4079a066a510afdd122e15116e9a284c80698b48d1cf10b8d34e', 'conker/src/game/generated_1D6E80.c': 'e6f4d1e63adc28a0a76e8e223fe26bc8ee47e160a7d0a99388129eba2006e9d0', 'conker/asm/1D6E80.s': '3d203700398c8864a2ec721620c6f412c6b1204ebeb13a955b464476defde90e', 'conker/asm/nonmatchings/generated_1D0840/func_151A5170.s': 'fad3f65b4b826b42e687a654bdb2f7eec8e831162644b215272be03fb36a33b3', 'conker/asm/nonmatchings/generated_1D6E80/func_151A9AA4.s': '718b072753386cfa2eacf75c3344c33763aa4e2af5b82f6426104378a203206c', 'conker/asm/nonmatchings/generated_1D6E80/func_151A9CA0.s': '140fcd2461b78f104e325bf9e8d92f5423db3043e258c15f7a232dea97cf5deb', 'conker/asm/nonmatchings/generated_1D6E80/func_151A9DC0.s': '4ce0b4c76efaf7c835bd467239356aded53039f401d3d463189d988de2c69e91', 'conker/asm/nonmatchings/generated_1D6E80/func_151A9EC0.s': '177feb4283fdf8d9bceda9bb3ec15b25d963802892c61d5803bdfca1e95e6fd1', 'conker/asm/nonmatchings/generated_1D6E80/func_151AA264.s': '212550fc7f977ef1150303c71414fc5261198bd84cb9b871d51e7ced03f418cc', 'conker/asm/nonmatchings/generated_1D6E80/func_151AA30C.s': '4c7524f321b1b0b5ae81cfa6bbd4e1e76b6cc5ae2b00d9801c2432d834fd2e22', 'conker/asm/nonmatchings/generated_1D6E80/func_151AA48C.s': '09427164edc988c0f19cb5e0ea341e0b3475fe93399e30ac502ad9a58b3973d6', 'conker/asm/nonmatchings/generated_1D6E80/func_151AA5A4.s': '0cc8c31e8f0f2122b278f0e9296b2e29b28513c007dbb495d0ab406d6a017988', 'conker/asm/nonmatchings/generated_1D6E80/func_151AA6D8.s': '55e2acce13949f95926ea35e3c4434ceed69f6f98d6d5a751772f68dbd87d433', 'conker/asm/nonmatchings/generated_1D6E80/func_151AAA4C.s': 'b21b5139b0c653d5beef6a5f5353398e0de15b3d96000253ff411bc53a36075c', 'conker/asm/nonmatchings/generated_1D6E80/func_151AAABC.s': 'd3f8e25a7f792927d56e01e3f1cca16660462892250df737a4f5b390cc92fb55', 'conker/asm/nonmatchings/generated_1D6E80/func_151AB180.s': '515024ddf0d996660dbd31da7f2ab03bbb9a0e4c0b189f7f10cf4bc74d74d09f', 'conker/asm/nonmatchings/generated_1D6E80/func_151AB2C4.s': 'ac7eb1ff1815fc6f36059a67289d7724c11893267943e175b77d016987813a2d', 'conker/asm/nonmatchings/generated_1D6E80/func_151AB3A4.s': '122f6dfc7b69e4db62062282a258bdb3afe8c6743059da3146766f51a986cca9', 'conker/asm/nonmatchings/generated_1D6E80/func_151AB6B8.s': 'b6d28be69699c66022e25351687ad76692bfde13ec6c271d6a642bdf3b1ba615', 'conker/asm/nonmatchings/generated_1D6E80/func_151AB788.s': 'e09cf7fef9833536cdaab0e81d3d8ccc8d1529fb8212b1fda4325c751082996b', 'conker/asm/nonmatchings/generated_1D6E80/func_151AB7D8.s': 'cca0bfcea4c9be0e92f264833f137ecf904e035e10f6f8ef98680e4137c767b7'}
OBJECTS = {'conker/build/src/game/generated_1CA420.c.o': '43de87f3ff4799e73b51d43562bc987b58e47d2cc5cd1fe5e5bd7bfc3bca1565', 'conker/build/src/game/generated_1D0840.c.o': '1405212d57a828bb1f727051e54e57bbfb3afb6a1d7bf566267b10550d276de4', 'conker/build/src/game/generated_1D6E80.c.o': '3fef579f4a516b4a0d52abda43db3896b7c8f4fe1a1061c4a9fe4f274b5d2aee'}
DECLARATIONS = 'typedef struct { u8 *owner; u8 identity; u8 opaque5[3]; } PayloadOwnerLink;\ntypedef struct { u8 *before; u8 *after; u8 before_identity; u8 after_identity; u8 opaqueA[2]; } PayloadOwnerLinkEvent;\n'
SELECTED = {'func_1519E570': '/* Retarget the payload owner link or release its matching actor. */\nvoid func_1519E570(struct260 *owner, s32 eventAddress, u8 command) {\n    PayloadOwnerLink *link = (PayloadOwnerLink *)((u8 *)owner + 0x28);\n    PayloadOwnerLinkEvent *event = (PayloadOwnerLinkEvent *)eventAddress;\n\n    if (command == 0) {\n        if (link->owner == event->before || link->identity == ((u8 *)event)[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    } else if (command == 0x2D) {\n        u8 *current = link->owner;\n        if (current == event->before) {\n            link->owner = event->after;\n            link->identity = event->after_identity;\n        } else if (current == event->after) {\n            link->owner = event->before;\n            link->identity = event->before_identity;\n        }\n    }\n}', 'func_151A4D88': '/* Retarget the payload owner link or release its matching actor. */\nvoid func_151A4D88(struct260 *owner, s32 eventAddress, u8 command) {\n    PayloadOwnerLink *link = (PayloadOwnerLink *)((u8 *)owner + 0x28);\n    PayloadOwnerLinkEvent *event = (PayloadOwnerLinkEvent *)eventAddress;\n\n    if (command == 0) {\n        if (link->owner == event->before || link->identity == ((u8 *)event)[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    } else if (command == 0x2D) {\n        u8 *current = link->owner;\n        if (current == event->before) {\n            link->owner = event->after;\n            link->identity = event->after_identity;\n        } else if (current == event->after) {\n            link->owner = event->before;\n            link->identity = event->before_identity;\n        }\n    }\n}', 'func_151ABD54': '/* Retarget the payload owner link or release its matching actor. */\nvoid func_151ABD54(struct260 *owner, s32 eventAddress, u8 command) {\n    PayloadOwnerLink *link = (PayloadOwnerLink *)((u8 *)owner + 0x28);\n    PayloadOwnerLinkEvent *event = (PayloadOwnerLinkEvent *)eventAddress;\n\n    if (command == 0) {\n        if (link->owner == event->before || link->identity == ((u8 *)event)[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    } else if (command == 0x2D) {\n        u8 *current = link->owner;\n        if (current == event->before) {\n            link->owner = event->after;\n            link->identity = event->after_identity;\n        } else if (current == event->after) {\n            link->owner = event->before;\n            link->identity = event->before_identity;\n        }\n    }\n}'}
TARGETS = {'func_1519E570': {'entry': 354018672, 'rom': 1882656, 'size': 172, 'offset': 40, 'owner': 'generated_1CA420', 'source': 'conker/src/game/generated_1CA420.c', 'asm': 'conker/asm/1CA420.s', 'raw_SHA256': '72b888b69c2117b33fe0d428342e9482944c06cd2b6fd7dc0b406bf7d2b07334', 'parent': 353670196, 'parent_size': 92, 'parent_source': 'conker/src/game/done/game_1765E0.c', 'table': 2148051160, 'table_rom': 2290584, 'count': 74, 'index': 2, 'selector': 19}, 'func_151A4D88': {'entry': 354045320, 'rom': 1909304, 'size': 172, 'offset': 40, 'owner': 'generated_1D0840', 'source': 'conker/src/game/generated_1D0840.c', 'asm': 'conker/asm/1D0840.s', 'raw_SHA256': '72b888b69c2117b33fe0d428342e9482944c06cd2b6fd7dc0b406bf7d2b07334', 'parent': 353670196, 'parent_size': 92, 'parent_source': 'conker/src/game/done/game_1765E0.c', 'table': 2148051160, 'table_rom': 2290584, 'count': 74, 'index': 1, 'selector': 19}, 'func_151ABD54': {'entry': 354073940, 'rom': 1937924, 'size': 172, 'offset': 40, 'owner': 'generated_1D6E80', 'source': 'conker/src/game/generated_1D6E80.c', 'asm': 'conker/asm/1D6E80.s', 'raw_SHA256': '72b888b69c2117b33fe0d428342e9482944c06cd2b6fd7dc0b406bf7d2b07334', 'parent': 353670196, 'parent_size': 92, 'parent_source': 'conker/src/game/done/game_1765E0.c', 'table': 2148051160, 'table_rom': 2290584, 'count': 74, 'index': 9, 'selector': 19}}
ISOLATED_HEADERS = '#include <ultra64.h>\n#include "structs.h"\nvoid func_1516972C(struct102 *);\n'
HELPER_CASTS = {'func_1519E570': ['func_1519E61C'], 'func_151A4D88': ['func_151A4F7C'], 'func_151ABD54': []}
FUNCTIONS = tuple(TARGETS)
MAKE_COMMAND_COUNTS = {'generated_1CA420': 3, 'generated_1D0840': 5, 'generated_1D6E80': 5}
BINDINGS = {68: [('R_MIPS_26', 'func_1516972C')]}
RAW_ROLE_WORDS = {9: 2354577408, 10: 2360279040, 24: 2353201152, 25: 2359558144, 34: 1416298501, 36: 2890137600}


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
        raise ValueError('Unknown payload-owner link placeholder')
    result = before[:lo] + SELECTED[name] + before[hi:]
    for neighbor in HELPER_CASTS[name]:
        lo, hi = function_span(result, neighbor)
        body = result[lo:hi]
        if 'u8 *arg0' not in body.split('{')[0] or body.count('func_1516972C(arg0);') != 1:
            raise ValueError('Unknown neighboring release-helper argument: ' + neighbor)
        body = body.replace('func_1516972C(arg0);', 'func_1516972C((struct102 *)arg0);')
        result = result[:lo] + body + result[hi:]
    marker = '#include <ultra64.h>\n'
    if result.count(marker) != 1:
        raise ValueError('Unknown payload-owner header boundary')
    return result.replace(marker, ISOLATED_HEADERS + '\n' + DECLARATIONS, 1)


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


def role_word(word, rename, commute=False):
    op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
    if op not in (4, 21, 35, 36, 40, 43):
        raise ValueError('Unexpected instruction in closed owner-link role window')
    rs, rt = rename.get(rs, rs), rename.get(rt, rt)
    if commute:
        if op not in (4, 21):
            raise ValueError('Only commutative equality operands may exchange')
        rs, rt = rt, rs
    return (word & ~0x03FF0000) | rs << 21 | rt << 16


def fitted_word(index, word):
    if 9 <= index <= 11:
        return role_word(word, {15: 24, 24: 15}, commute=index == 11)
    if 24 <= index <= 38:
        return role_word(word, {3: 4, 4: 3}, commute=index in (26, 34))
    raise ValueError('Word is outside both closed payload-link role windows')


def normalized(name, raw, bindings):
    if len(raw) != 172 or digest(raw) != TARGETS[name]['raw_SHA256'] or bindings != BINDINGS:
        raise ValueError('Owner-link raw body/bindings changed: ' + name)
    words = list(struct.unpack('>43I', raw))
    if (any(words[i] != word for i, word in RAW_ROLE_WORDS.items())
            or words[11] != 0x11F80005 or words[26] != 0x54640007):
        raise ValueError('Owner-link role inputs changed')
    fitted = list(words)
    # Each register cycle is closed; two symmetric comparisons remain unchanged.
    for i in (*range(9, 12), *range(24, 39)):
        fitted[i] = fitted_word(i, words[i])
    if {i for i in range(43) if words[i] != fitted[i]} != set(RAW_ROLE_WORDS):
        raise ValueError('Payload-link cycles are not closed at their six declared words')
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
                expected='0x%08X' % word, replacement='0x%08X' % fitted_word(i, word),
                expected_relocations='-', replacement_relocations='-',
                note='Normalize two closed payload-link register cycles and equality operand order',
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
        rows.append(dict(function=name,words=43,frame=24,bindings=1,new_guards=6,
            raw_differences=6,preserved_neighbors=neighbors,raw_SHA256=digest(raw)))
    report=dict(targets=rows,total_words=129,new_guards=18,compiler_only=False,
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
        if len(commands)!=MAKE_COMMAND_COUNTS[target['owner']] or len(cc)!=1 or not all(flag in cc[0]for flag in('-O2','-g3')):
            raise ValueError('Payload-link actual compiler recipe/profile changed: '+name)
        if same_functions(output/(name+'-after.o'),Path(str(actual)+'.compact'))!=len(parse_object(output/(name+'-after.o'))[1]):
            raise ValueError('Owner-link Make raw owner differs')
        if link_owner(root,output,actual,target['owner'])!=link_owner(root,output,output/('qualified-'+target['owner']+'.o'),target['owner']):
            raise ValueError('Owner-link Make padded owner differs')
        reports.append(dict(function=name,actual_Make_commands=len(commands),normal_O2_g3=True))
    report=dict(targets=reports,actual_Make_commands=13,all_raw_functions_equal=True,padded_code_and_metadata_equal=True)
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
    report=dict(functions=len(b),other_bodies_fixed=len(b)-3,all_addresses_fixed=True,
        total_words=129,new_guards=18,strict_first_link_reproduced=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
