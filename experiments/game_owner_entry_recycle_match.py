"""Owner-chain recycling: semantic C, closed normalization and strict image audit."""
from pathlib import Path
import csv,io,hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150C1198','generated_EDE60'
ENTRY,ROM,BODY,SIZE,RAW_SIZE=0x150C1198,0xEE648,188,200,192
SOURCE='conker/src/game/generated_EDE60.c'
OBJECT='conker/build/src/game/generated_EDE60.c.o'
ASM='conker/asm/EDE60.s'
BUILD='conker/build/game-owner-entry-recycle-match'
RODATA_SYMBOL=None
BINDINGS={}
sha=lambda b:hashlib.sha256(b).hexdigest()
RAW_SHA='dead4e217db1b30585c2456dcefc0b257064798a9f6c75df6fe8963f8e088fd5'
NORMALIZED_SHA='95de15db035c99796749593aec8e86e7fddb5019b4f1f0411651d1c8323259c3'
SNAPSHOT_SHA='4e4a3f93d4a7597ee98764e1c624992fce2bda876a1eff826f7c1b590d9ac431'
BEFORE_ELF_SHA='088882c693427a28682a2ebb91aef44b98081d212f79b1b2306dce81b607b67c'
TRUTH_SHA='c2ab24e4db53a0fbe2cfb0866e488a5703192b28463a03193e88ba607c788dfe'
HEADERS='#include <ultra64.h>\ntypedef struct { void *actor; s16 next; s16 unused; } OwnerChainEntry150C1198;\n'
DECLARATIONS='typedef struct { void *actor; s16 next; s16 unused; } OwnerChainEntry150C1198;\n'
SELECTED="/* Unlink the actor from its owner's active chain, then prepend its slot to the free chain. */\nvoid func_150C1198(u8 *actor) {\n    u8 *owner;\n    s32 found;\n    s16 previous;\n    s16 index;\n    s16 head;\n    OwnerChainEntry150C1198 *entries;\n    OwnerChainEntry150C1198 *entry;\n\n    owner = *(u8 **)(actor + 0xA8);\n    found = 0;\n    previous = -1;\n    index = *(s16 *)(owner + 0x44);\n    head = index;\n    while (index != -1 && !found) {\n        entries = *(OwnerChainEntry150C1198 **)(owner + 0x40);\n        if (entries[index].actor == actor) {\n            found = 1;\n        } else {\n            previous = index;\n            index = entries[index].next;\n        }\n    }\n    if (found) {\n        entries = *(OwnerChainEntry150C1198 **)(owner + 0x40);\n        entry = (OwnerChainEntry150C1198 *)((s32)entries + index * 8);\n        if (index == head) {\n            *(s16 *)(owner + 0x44) = entry->next;\n        } else {\n            entries[previous].next = entry->next;\n            /* The link store may change the shared entry-table pointer. */\n            entry = (OwnerChainEntry150C1198 *)((s32)*(OwnerChainEntry150C1198 **)(owner + 0x40) + index * 8);\n        }\n        entry->next = *(s16 *)(owner + 0x46);\n        *(s16 *)(owner + 0x46) = index;\n    }\n}\n"
GUARDS=[{'offset': 16, 'expected': '0x84460044', 'replacement': '0x84470044', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}, {'offset': 28, 'expected': '0x00063C00', 'replacement': '0x00073400', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}, {'offset': 32, 'expected': '0x00077C03', 'replacement': '0x00067C03', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}, {'offset': 36, 'expected': '0x10CA0011', 'replacement': '0x11EA0011', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}, {'offset': 40, 'expected': '0x01E03825', 'replacement': '0x01E03025', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}, {'offset': 108, 'expected': '0x10600012', 'replacement': '0x10600011', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}, {'offset': 124, 'expected': '0x01034821', 'replacement': '0x14C70004', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}, {'offset': 128, 'expected': '0x14C70004', 'replacement': '0x01034821', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}, {'offset': 132, 'expected': '0x01202025', 'replacement': '0x01202025', 'expected_relocations': [], 'replacement_relocations': [], 'omit': True}, {'offset': 168, 'expected': '0x03032021', 'replacement': '0x03034821', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}, {'offset': 176, 'expected': '0xA4990004', 'replacement': '0xA5390004', 'expected_relocations': [], 'replacement_relocations': [], 'omit': False}]
NEW_GUARDS=[16, 28, 32, 36, 40, 108, 124, 128, 132, 168, 176]
BEFORE_GUARDS_SHA='9cd65675bf6bfca1ab216bdc540937a1bf50f36f2a112eb0c043605bdc4a85b0'

OWNER_DIAGNOSTICS='cfe: Warning 712: <source>, line 14: illegal combination of pointer and integer\n     func_150C0A48(arg0);\n ------------------^\ncfe: Warning 712: <source>, line 19: illegal combination of pointer and integer\n     func_150C0A48(arg0);\n ------------------^\n'

def check_owner_diagnostics(text):
    normalized=re.sub(r'cfe: Warning 712: [^\n]+?, line ','cfe: Warning 712: <source>, line ',text)
    if normalized!=OWNER_DIAGNOSTICS:raise ValueError('Owner-chain inherited diagnostics changed')
    return 2

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=RAW_SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner-chain raw body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150C1198() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Owner-chain placeholder changed')
    return before.replace(stub,(DECLARATIONS+SELECTED).strip(),1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner-chain recycle snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner-chain recycle frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner-chain recycle predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner-chain recycle live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner-chain image predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner-chain original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner-chain image differs from literal slot and extent prediction')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner-chain named ELF definitions changed')

def guard_manifest(before):
    if sha(before)!=BEFORE_GUARDS_SHA:raise ValueError('Inherited guards changed')
    if any(row['function']==FUNCTION for row in csv.DictReader(io.StringIO(before.decode()))):raise ValueError('Owner-chain already guarded')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,next(csv.reader(io.StringIO(before.decode()))),lineterminator='\r\n')
    for row in GUARDS:writer.writerow(dict(filename=OWNER,function=FUNCTION,offset=f"0x{row['offset']:03X}",expected=row['expected'],replacement=row['replacement'],expected_relocations='-',replacement_relocations='-',note='Normalize equal signed-index copy and closed released-entry pointer scheduling',insert_after='',insert_after_relocations='',omit=str(row['omit']).lower()))
    return before+stream.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings)
    words=list(struct.unpack('>48I',raw));assert words[0x84//4]==0x01202025 and words[0x7C//4]==0x01034821 and words[0x80//4]==0x14C70004
    # Change only the initial assignment of the equal signed head/current values.
    v=list(words)
    def fields(at,**updates):
     i=at//4;word=v[i]
     for name,reg in updates.items():shift={'rs':21,'rt':16,'rd':11}[name];word=(word&~(31<<shift))|(reg<<shift)
     v[i]=word
    fields(0x10,rt=7);fields(0x1C,rt=7,rd=6);fields(0x20,rt=6);fields(0x24,rs=15);fields(0x28,rd=6)
    # The actor in a0 is dead after the search. Its only remaining uses are this
    # pointer copy, the else-arm pointer recomputation and the final next-link store.
    # Keep that private pointer in t1 throughout; move the independent add into
    # the head-test branch delay slot and remove the now-redundant copy.
    fields(0xA8,rd=9);fields(0xB0,rs=9)
    order=list(range(48));order[31],order[32]=order[32],order[31];order.remove(33);position={old:new for new,old in enumerate(order)}
    for i,w in enumerate(words):
     op=w>>26
     if op in(4,5,6,7,20,21,22,23):
      imm=w&65535;imm=imm if imm<32768 else imm-65536;target=i+1+imm;assert i in position and target in position
      v[i]=(v[i]&0xFFFF0000)|((position[target]-position[i]-1)&65535)
    normalized=struct.pack('>47I',*[v[i]for i in order]);assert sha(normalized)==NORMALIZED_SHA
    guards=[]
    ordered_words=[v[i]for i in order]
    for i,a in enumerate(words):
     b=a if i==33 else ordered_words[i-(i>33)]
     if a!=b or i==33:guards.append(dict(offset=i*4,expected=f'0x{a:08X}',replacement=f'0x{b:08X}',expected_relocations=[],replacement_relocations=[],omit=i==33))
    assert guards==GUARDS
    return normalized,{}

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected.o', 'original-func_150C1198.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected.c', 'selected-processed.c', 'selected.o', 'selected-diagnostics.txt', 'selected-input.c', 'make-shadow/src/game/generated_EDE60.c.o.compact', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_EDE60.c.o', 'make-shadow/src/game/generated_EDE60.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner-chain recycle artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner-chain recycle artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner-chain recycle raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner-chain recycle evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner-chain recycle Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_EDE60.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner-chain recycle Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=11 or q['exclusions']!=0:raise ValueError('Owner-chain recycle private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner-chain recycle changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner-chain recycle protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,compiler_words=48,frame=0,alignment_words=3,slot_words=50,omitted_words=1,strict_first_link_reproduced=True,guards=11,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
