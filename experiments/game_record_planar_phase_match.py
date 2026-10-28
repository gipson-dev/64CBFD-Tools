"""Record planar phase: sequenced C with two checked multiply operand guards, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_15131828','generated_15D730'
ENTRY,ROM,BODY,SIZE=0x15131828,0x15ECD8,192,192
SOURCE='conker/src/game/generated_15D730.c'
OBJECT='conker/build/src/game/generated_15D730.c.o'
ASM='conker/asm/15D730.s'
BUILD='conker/build/game-record-planar-phase-match'
RODATA_SYMBOL=None
RAW_SHA="e7d3ebd81315a88742503cb9600ef1901aeeb1d9a0c4f4d77b88ff8cc4898220"
SNAPSHOT_SHA="77e5bb534186446356ed64f5fb5a6d2fcbecd437e3c9a295f22c3c2485a665af"
BEFORE_ELF_SHA="5ebcc1d909d33b946b7b6218c2852941b1c9ba6dafdd1306b97d914c007f9e31"
TRUTH_SHA="c416a2eacd30b85e362da64fa1007cf18c758f394294059c842eeb0a24f2106a"
TRIG,TICKS,DAMP=0x151423D8,0x800BE9E4,0x15131958
PARENTS=(0x150AF6E4,0x150DA628,0x150E8824,0x151D4D04)
BINDINGS={36:[('R_MIPS_26','func_151423D8')],80:[('R_MIPS_26','func_151423D8')],108:[('R_MIPS_HI16','D_800BE9E4')],116:[('R_MIPS_LO16','D_800BE9E4')]}
HEADERS="#include <ultra64.h>\n\n"
DECLARATIONS="extern s32 D_800BE9E4;\nf32 func_151423D8(u8);\n\n"
SELECTED="/* Write the two phase-driven offsets, then advance the byte phases by the live tick count. */\nvoid func_15131828(u8 *record, f32 *amplitudes, u8 *phases, u8 *rates) {\n    f32 sample;\n\n    sample = func_151423D8((u8)(phases[0] - 0x40));\n    *(f32 *)(record + 0x4C) = sample * amplitudes[0];\n    sample = func_151423D8((u8)(phases[1] - 0x40));\n    *(f32 *)(record + 0x54) = sample * amplitudes[1];\n    phases[0] += rates[0] * (u32)D_800BE9E4;\n    phases[1] += rates[1] * (u32)D_800BE9E4;\n}"
def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected record planar phase diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record planar phase body/bindings changed')
    return raw,bindings

OWNER_DECLARATIONS="f32 func_151423D8(u8);\n\n"

def recovered_owner(before):
    stub='s32 func_15131828() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Record planar phase placeholder changed')
    return before.replace(stub,OWNER_DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record planar phase snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record planar phase frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record planar phase predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record planar phase live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record planar phase strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Record planar phase original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record planar phase image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record planar phase named ELF definitions changed')


def derive_guards():
    """Swap only fs/ft on the two independently checked mul.s words."""
    rows=[]
    for at,word in ((60,0x46002182),(112,0x46004282)):
        assert word>>26==17 and (word>>21)&31==16 and word&63==2
        fs,ft=(word>>11)&31,(word>>16)&31
        replacement=(word&~((31<<11)|(31<<16)))|(fs<<16)|(ft<<11)
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,expected='0x%08X'%word,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Normalize record phase-offset commutative floating multiply operand order',insert_after='',insert_after_relocations='',omit='false'))
    return rows

NEW_GUARDS=derive_guards()
def guard_manifest(before):
    import csv,io
    if sha(before)!='de278c88aaf2aba65667bd3422814c947b7da4db616b190b388450c185486278':raise ValueError('Record phase inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Record phase guards already present')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw)
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if struct.unpack_from('>I',raw,at)[0]!=int(row['expected'],0)or bindings.get(at):raise ValueError('Record phase guarded word/binding changed')
        struct.pack_into('>I',out,at,int(row['replacement'],0))
    result=bytes(out)
    if sha(result)!='49c94c0df53326b2f9468b6c5067aa037f578b96a0eadce6622f1cdd96c385f0':raise ValueError('Record phase normalized body changed')
    return result,bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15131828.o','first-linked.elf','proposed-word-patches.csv')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_15D730.c.o","make-shadow/src/game/generated_15D730.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record planar phase artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record planar phase artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record planar phase raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record planar phase evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record planar phase Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_15D730.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record planar phase Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Record planar phase private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record planar phase changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record planar phase protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=24,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
