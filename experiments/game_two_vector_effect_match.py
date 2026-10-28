"""Two-vector effect: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1514F308','generated_179F30'
ENTRY,ROM,BODY,SIZE=0x1514F308,0x17C7B8,196,196
SOURCE='conker/src/game/generated_179F30.c'
OBJECT='conker/build/src/game/generated_179F30.c.o'
ASM='conker/asm/179F30.s'
BUILD='conker/build/game-two-vector-effect-match'
RODATA_SYMBOL=None
RAW_SHA="2b6c74eddcd215c26450367f9b19426ca6d2c17e849949875cdf8c5bfa8be3f0"
SNAPSHOT_SHA="89fab26fe6e46f4b61fb474d0884e72f9ebbfa97f24d2279988d379939a0c6f6"
BEFORE_ELF_SHA="40040146d7a6d2ee87ade76ba8bd2351f8c53f595c6884adaf554802091794d9"
TRUTH_SHA="26abbf6a80fe4e65989a2f4b4723ff98645a76423801d553463d5d86daa35724"
PARENT,TABLE,EFFECT,VEC_A,VEC_B,PARAM=0x1514D15C,0x8008AA70,0x15160CDC,0x800A5970,0x800A597C,0x800A5E58
TABLE_ROM=0x22F530
BINDINGS={16:[('R_MIPS_HI16','D_800A5970')],20:[('R_MIPS_LO16','D_800A5970')],28:[('R_MIPS_HI16','D_800A597C')],32:[('R_MIPS_LO16','D_800A597C')],120:[('R_MIPS_HI16','D_800A5E58')],124:[('R_MIPS_LO16','D_800A5E58')],172:[('R_MIPS_26','func_15160CDC')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="typedef struct { f32 x, y, z; } GameEffectVector;\nextern GameEffectVector D_800A5970, D_800A597C;\nextern f32 D_800A5E58;\nvoid *func_15160CDC(u8 *, u8, GameEffectVector *, GameEffectVector *, f32,\n                   u8, s16, s32, s32, s32, s32, u8, u8, u8, u8, s32);\n\n"
SELECTED="/* Submit a type-five effect using the two stored vector presets. */\nvoid func_1514F308(u8 *owner) {\n    GameEffectVector first = D_800A5970;\n    GameEffectVector second = D_800A597C;\n    func_15160CDC(owner, 5, &first, &second, D_800A5E58, 2, 300,\n                 255, 255, 255, 255, 1, 0, 0, 255, 1);\n}"


def check_owner_diagnostics(text):
    normalized=re.sub(r'(?m)^(cfe: Warning 712: )[^\n]+?(, line (?:152|190): illegal combination of pointer and integer)$',r'\1<owner>\2',text)
    if hashlib.sha256(normalized.encode()).hexdigest()!='a9ff8c20b881721762b41277218dcc0d62f438d203efd90b9255cb1205b2e17d':raise ValueError('Inherited two-vector effect owner diagnostics changed')
    return 4

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=196 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Two-vector effect body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1514F308() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Two-vector effect placeholder changed')
    return before.replace(stub,(DECLARATIONS+SELECTED).strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Two-vector effect snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Two-vector effect frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Two-vector effect predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Two-vector effect live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Two-vector effect strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Two-vector effect original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # New references reorder these four closed GNU hash-chain groups. Rebuild
    # their names and records entirely from the frozen predecessor definitions.
    # All values, types, extents and section indices are retained by name.
    off=struct.unpack_from('>I',before,32)[0];size,count=struct.unpack_from('>HH',before,46)
    hs=[struct.unpack_from('>10I',before,off+i*size)for i in range(count)]
    symtabs=[h for h in hs if h[1]==2]
    if len(symtabs)!=1:raise ValueError('Expected one symbol table')
    strings=hs[symtabs[0][6]]
    groups=((('D_80099530','D_80095B30','D_8009EF30'),('D_8009EF30','D_80099530','D_80095B30')),
            (('D_800A5E58','D_800A1B58'),('D_800A1B58','D_800A5E58')),
            (('func_1502AAF8','D_8009E7F0'),('D_8009E7F0','func_1502AAF8')),
            (('D_800A5970','D_800A1670','D_80097C20'),('D_800A1670','D_80097C20','D_800A5970')))
    for old_order,new_order in groups:
        records=[named[n]for n in old_order]
        if any(len(v)!=1 for v in records)or set(old_order)!=set(new_order):raise ValueError('Invalid closed symbol group')
        slots=[v[0][0]for v in records];fields={n:named[n][0][1]for n in old_order};start=fields[old_order[0]][0]
        if slots!=list(range(slots[0],slots[0]+16*len(slots),16)):raise ValueError('Symbol group is not contiguous')
        expected_index=start
        for n in old_order:
            if fields[n][0]!=expected_index:raise ValueError('String group is not contiguous')
            expected_index+=len(n)+1
        old_text=b''.join(n.encode()+b'\0'for n in old_order)
        if before[strings[4]+start:strings[4]+expected_index]!=old_text:raise ValueError('Frozen string names changed')
        cursor=start
        for slot,n in zip(slots,new_order):
            f=fields[n];struct.pack_into('>IIIBBH',result,slot,cursor,*f[1:]);cursor+=len(n)+1
        if cursor!=expected_index:raise ValueError('String group length changed')
        result[strings[4]+start:strings[4]+expected_index]=b''.join(n.encode()+b'\0'for n in new_order)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Two-vector effect image differs from body and extent prediction')
    expected=Counter((n,f[1],196 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Two-vector effect named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='91cfc61697b2f874f74475c5dadac1faec1f2e3c4f2a515d593b62d15b71ba03':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1514F308.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_179F30.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_179F30.c.o","make-shadow/src/game/generated_179F30.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Two-vector effect artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Two-vector effect artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Two-vector effect raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Two-vector effect evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Two-vector effect Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_179F30.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Two-vector effect Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Two-vector effect private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Two-vector effect changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Two-vector effect protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=96,alignment_words=0,slot_words=49,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
