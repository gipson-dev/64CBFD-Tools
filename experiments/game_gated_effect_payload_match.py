"""Gated sparse effect payload: direct C, preserved padding and complete-image closure."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-gated-effect-payload-151937F4-match'
BASELINE='40b181d8e957f4afd4d70bab07dabb3874995809488ad1b40ae99a63001a12f4'
LINKED='ca4d0c821f391a246d79dd62c5f32c3ec98d094feb4b48678a568a3a4696d673'
SPECS=(('func_151937F4','generated_1C0B10',0x151937F4,0x1C0CA4),)
PATCHES=()
RAW_SHA='40f1b0223a127988851906e120fff416c934d42696efb791aa0a0fa673385b40'
BINDINGS={100:[('R_MIPS_HI16','D_800A81E4')],108:[('R_MIPS_LO16','D_800A81E4')],216:[('R_MIPS_26','func_15134DAC')]}
sha=lambda data:hashlib.sha256(data).hexdigest()

def checked_payload(raw,bindings):
    if len(raw)!=240 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Gated effect payload payload or bindings changed')
    return raw,bindings

def normalized(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw)
    for at,before,after in PATCHES:
        if struct.unpack_from('>I',out,at)[0]!=before:raise ValueError('Gated effect payload spill guard changed')
        struct.pack_into('>I',out,at,after)
    return bytes(out),bindings

def recovered_owner(before,target):
    function,owner,entry,rom=SPECS[target];lo,hi=function_span(before,function)
    if before[lo:hi]!='s32 '+function+'() {\n    return 0;\n}':raise ValueError('Gated effect payload predecessor changed')
    return before[:lo]+HEADERS.replace('#include <ultra64.h>\n','')+'/* Submit the sparse effect payload when its owner is present and enabled; retain guest padding. */\n'+SELECTED.replace(SPECS[0][0],function).rstrip()+before[hi:]

def snapshot(output):
    index=(output/'input-snapshot.json').read_bytes()
    if sha(index)!=SNAPSHOT_SHA:raise ValueError('Gated effect payload snapshot index changed')
    values={}
    for name,wanted in json.loads(index)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(data)!=wanted:raise ValueError('Gated effect payload frozen input changed: '+name)
        values[name]=data
    return values

def verify_prepared(output):
    index=(output/'prepared-artifacts.json').read_bytes()
    if sha(index)!=ARTIFACT_SHA:raise ValueError('Gated effect payload preparation index changed')
    for name,wanted in json.loads(index).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Gated effect payload preparation changed: '+name)
    return True

def predict(before,rom):
    if sha(before)!=BASELINE:raise ValueError('Gated effect payload image predecessor changed')
    out=bytearray(before)
    for function,owner,entry,offset in SPECS:
        row,=[r for r in symbol_rows(before)if r[1]==function]
        if row[2][1:3]!=(entry,12):raise ValueError('Gated effect payload predecessor extent changed')
        truth=rom[offset:offset+240]
        if len(truth)!=240:raise ValueError('Gated effect payload retail slot missing')
        at=elf_slot_offset(before,entry,240);out[at:at+240]=truth;struct.pack_into('>I',out,row[0]+8,240)
    reorder_metadata(before,out)
    return bytes(out)

def check_image(before,actual,rom):
    if actual!=predict(before,rom):raise ValueError('Gated effect payload entire image differs')

def expected_map(output):
    data=(output/'private-joint-linked.map').read_bytes()
    for _,owner,_,_ in SPECS:
        private=(BUILD.removeprefix('conker/')+'/make-shadow-'+owner+'/src/game/'+owner+'.c.o').encode()
        if data.count(private)!=9:raise ValueError('Gated effect payload map owner count changed')
        data=data.replace(private,('build/src/game/'+owner+'.c.o').encode())
    private=(BUILD.removeprefix('conker/')+'/private-joint-linked.elf').encode()
    if data.count(private)!=1:raise ValueError('Gated effect payload map output changed')
    return data.replace(private,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:
        for i,(_,owner,_,_)in enumerate(SPECS):
            name='conker/src/game/'+owner+'.c';changes[name]=recovered_owner(values[name].decode(),i).encode()
            changes['conker/build/src/game/'+owner+'.c.o']=(output/('qualified-'+owner+'.o')).read_bytes()
        changes.update({'conker/retail_word_patches.us.csv':(output/'proposed-guards.csv').read_bytes(),
            'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin']),
            'conker/build/conker.us.map':expected_map(output)})
    for name,data in values.items():
        if (root/name).read_bytes()!=changes.get(name,data):raise ValueError('Gated effect payload live input changed: '+name)
    return values

def audit(root,output,installed=False):
    from tools.check_game_data_layout import audit_layout
    verify_prepared(output);values=check_inputs(root,output,installed)
    elf=root/'conker/build/conker.us.elf'if installed else output/'private-joint-linked.elf'
    actual=elf.read_bytes();check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'])
    if sha(actual)!=LINKED:raise ValueError('Gated effect payload linked image changed')
    data=audit_layout(elf,root/'conker')
    if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Gated effect payload protected data changed')
    targets={v[0]for v in SPECS};expected=Counter((n,f[1],240 if n in targets else f[2],*f[3:])for _,n,f,_ in symbol_rows(values['conker/build/conker.us.elf']))
    if expected!=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual)):raise ValueError('Gated effect payload named definition changed')
    q=json.loads((output/'private-owner-image-v7.json').read_text());q.update(private_only=not installed,installed=installed,matching_credit=1 if installed else 0,protected_data=data)
    if installed:(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n')
    return q

METADATA_GROUPS=((2751800,('func_15155FD4','D_800AA9BC','D_8009E63C'),(2,0,1)),(3009480,('D_800A81E4','D_8009FB44','D_8009F674','D_80096274'),(1,2,3,0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Gated effect payload named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Gated effect payload symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Gated effect payload metadata length changed')

HEADERS='#include <ultra64.h>\ntypedef struct {\n    u8 ownerTag;\n    u8 padding1[3];\n    u8 *owner;\n    u8 field8;\n    u8 padding9[3];\n    f32 parameters[6];\n    u8 kind;\n    u8 padding25;\n    s16 field26;\n    s16 field28;\n    s16 field2A;\n    u8 padding2C[2];\n    u8 field2E;\n    u8 field2F;\n    s8 field30;\n    u8 padding31[3];\n    f32 coefficient;\n    u8 field38;\n    s8 field39;\n    u8 padding3A[2];\n} GatedEffectPayload;\nextern f32 D_800A81E4;\nvoid *func_15134DAC(GatedEffectPayload *, s32);\n'
SELECTED='void func_151937F4(u8 *owner, s32 unused1, s32 unused2) {\n    GatedEffectPayload payload;\n    if (owner != 0 && *(u32 *)owner != 0) {\n        payload.ownerTag = owner[0x3B];\n        payload.owner = owner;\n        payload.field8 = 0;\n        payload.parameters[0] = -28.0f;\n        payload.parameters[1] = 6.0f;\n        payload.parameters[2] = 1.0f;\n        payload.parameters[3] = -58.0f;\n        payload.parameters[4] = -3.0f;\n        payload.parameters[5] = -31.0f;\n        payload.kind = 2;\n        payload.field26 = 30;\n        payload.field28 = 25;\n        payload.field2A = 750;\n        payload.field2E = 3;\n        payload.field2F = 3;\n        payload.field30 = -1;\n        payload.field38 = 4;\n        payload.field39 = -1;\n        payload.coefficient = D_800A81E4;\n        func_15134DAC(&payload, 0);\n    }\n}\n'
SNAPSHOT_SHA='8dd6def6d083eb86822cc9dc442851c083d828d2f514b643307c7ec6571ae1d0'
ARTIFACT_SHA='4cf97da558e979b29db570597cc961e61dc5c63946b163a6e541575d5803221f'
