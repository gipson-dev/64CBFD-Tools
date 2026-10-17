"""Bank the uninstalled two-record gate recovery and its measured private gap."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_actor_state_update as previous
from tools.tests import actor_state_checkpoint as checkpoint
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-actor-record-gate-recovery'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11FF10','func_150F2A60',0x150F2A60,0x11FF10,556
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
changed={previous.PATHS[k]:v for k,v in checkpoint.AFTER.items()}
for key,path in PATHS.items():
    if path in changed:BASELINE[key]=changed[path]
for key,path,sha in (
    ('record_gate_owner','conker/src/game/generated_11FF10.c','bd3957b6f97e62f3ac609afe2c215a4af95c217b123d199fd74479a5dadd65a6'),
    ('record_gate_original','conker/asm/11FF10.s','693f75ac9e36cc7d5f903d7655792c7690009e367b2742fee9613204ef5ecab7')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='''extern u8 *D_800CC5EC;
extern u8 *D_800DBEF4;
extern s32 *D_800DBF94;
extern u8 D_800CC40C;
extern u8 D_800CC49A;
extern u8 D_800CC2D0[];
extern u8 **D_800BE4F0;
u8 *func_151149AC(u8);
void func_15060F28(u8 *, s32);
void func_15136C3C(u8 *, s32, s32, s32, s32, s32, s32, s32);
void func_10010630(s32, u8 *, s32, s32, s32);
void func_15145A50(u8 *);
void func_1507CD64(u8 *, s32);
u8 *func_15083E90(s32);
void func_15196318(u8 *, s32, s32);
'''
SELECTED='''/* Check two actor records, refresh the active actor, then set four handle offsets. */
void func_150F2A60(u8 *actor) {
    s32 i;
    s32 value;
    u8 *object;

    if (D_800CC5EC != NULL && !D_800CC5EC[0x120]) {
        for (i = 0; i < 2; i++) {
            if (D_800DBF94[(func_151149AC(250 - i) - D_800DBEF4) / 0xA0] & 1) {
                if (D_800CC40C) {
                    func_15060F28(D_800CC2D0 + (D_800CC40C * 0x32C - 0x13D30), 0);
                }
                D_800CC49A = 0;
                func_15136C3C(D_800CC2D0, 0, 0, 1, 1, 0, 255, 1);
                func_10010630(0x627, D_800CC2D0, 0x6D60, 500, 1000);
                func_15145A50(D_800CC2D0);
                func_1507CD64(D_800CC2D0, 6);
                break;
            }
        }
        object = func_15083E90(14);
        if (object != NULL) {
            value = *(s32 *)(object + 0x2E4);
        } else {
            value = 0;
        }
        func_15196318(D_800BE4F0[0], value, 0);
        func_15196318(D_800BE4F0[1], 0, -value);
        func_15196318(D_800BE4F0[2], value, 0);
        func_15196318(D_800BE4F0[3], -value, 0);
    }
}'''
SYMBOLS={'D_800CC5EC':0x800CC5EC,'D_800DBEF4':0x800DBEF4,'D_800DBF94':0x800DBF94,
    'D_800CC40C':0x800CC40C,'D_800CC49A':0x800CC49A,'D_800CC2D0':0x800CC2D0,
    'D_800BE4F0':0x800BE4F0,'func_151149AC':0x151149AC,'func_15060F28':0x15060F28,
    'func_15136C3C':0x15136C3C,'func_10010630':0x10010630,'func_15145A50':0x15145A50,
    'func_1507CD64':0x1507CD64,'func_15083E90':0x15083E90,'func_15196318':0x15196318}
RAW_SHA='28c65059860b7a8f40b59166beecbfbe9fecf1c6b7b392a130d9a74d42dcf125'

def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import indexed_threshold_mask_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed record-gate live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed record-gate frozen input: '+key)

def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150F2A60() {\n    return 0;\n}':raise ValueError('Unknown record-gate predecessor')
    anchor='#include <ultra64.h>'
    if before.count(anchor)!=1:raise ValueError('Unknown record-gate declarations')
    return (before[:lo]+body+before[hi:]).replace(anchor,anchor+'\n'+TYPE,1)

def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}

def linked(root,out,obj,label,entry=ENTRY,symbols=None):
    data,fs,rs=parse_object(obj);s=symbols or SYMBOLS
    text,unknown=emit_function(data,fs[FUNCTION],rs,FUNCTION,s)
    if unknown:raise ValueError('Unknown record-gate bindings '+repr(unknown))
    stem=out/label;asm=stem.with_suffix('.s');asm.write_text(text);compiled=stem.with_suffix('.o')
    script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',FUNCTION,
        *['--defsym=%s=0x%X'%p for p in s.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
    count=fs[FUNCTION]['size']//4
    return list(struct.unpack_from('>%dI'%count,projection.sections(elf)['.text'][1]))

def measure(root,out,label,body=SELECTED,flags=('-O2','-g3')):
    before=(out/'before-record_gate_owner').read_text();content=recovered_owner(before,body)
    if flags==('-O2','-g3','-Wo,-loopunroll,0'):obj,diag=compile_owner(root,out,content,label,no_unroll=True)
    else:obj,diag=build.compile_owner(root,out,content,label,flags)
    if diag:raise ValueError(diag)
    words=linked(root,out,obj,label+'-linked');raw,bindings=parts(obj)
    truth=list(struct.unpack_from('>139I',(out/'before-retail_rom').read_bytes(),ROM))
    frames=[(-(w&65535))&65535 for w in words[:24] if w>>16==0x27BD and w&0x8000]
    row=dict(label=label,words=len(words),frame=frames[0] if frames else None,flags=list(flags),
        raw_sha=hashlib.sha256(raw).hexdigest(),differences=sum(a!=b for a,b in zip(words,truth)),
        extent_gap=len(words)-139,bindings=bindings,installed=False)
    return obj,words,row

def forms():
    yield 'semantic',SELECTED,('-O2','-g3')
    yield 'nounroll',SELECTED,('-O2','-g3','-Wo,-loopunroll,0')
    yield 'o2',SELECTED,('-O2',)
    yield 'o1',SELECTED,('-O1',)
    indexed=SELECTED.replace('    s32 i;','    s32 i;\n    s32 index;').replace(
        '            if (D_800DBF94[(func_151149AC(250 - i) - D_800DBEF4) / 0xA0] & 1) {',
        '            index = (func_151149AC(250 - i) - D_800DBEF4) / 0xA0;\n            if (D_800DBF94[index] & 1) {')
    yield 'named-index',indexed,('-O2','-g3')
    retry=indexed.replace('        for (i = 0; i < 2; i++) {','        i = 0;\nretry:\n        {').replace(
        '            if (D_800DBF94[index] & 1) {','            i++;\n            if (!(D_800DBF94[index] & 1)) {\n                if (i < 2) goto retry;\n            } else {').replace(
        '                break;\n','')
    yield 'retry-scan',retry,('-O2','-g3')
    yield 'object-condition',SELECTED.replace('        object = func_15083E90(14);\n        if (object != NULL) {',
        '        if ((object = func_15083E90(14)) != NULL) {'),('-O2','-g3')

def qualify(root,out):
    freeze(root,out);obj,words,row=measure(root,out,'semantic')
    if (len(words),row['frame'],row['differences'],row['raw_sha'])!=(137,64,118,RAW_SHA):
        raise ValueError('Changed uninstalled record-gate candidate')
    before=(out/'before-record_gate_owner').read_text();old,diag=compile_owner(root,out,before,'owner-before')
    if diag:raise ValueError(diag)
    if normalized_pools(obj)!=normalized_pools(old):raise ValueError('Changed record-gate owner pools')
    neighbors=same_functions(old,obj,(FUNCTION,))
    pads=[]
    for label,target in (('candidate',obj),('owner-before',old)):
        text=emit_padded_assembly(target,out/'before-record_gate_original',filename=OWNER,word_patches_path=out/'before-guards')
        path=out/(label+'-padded.s');path.write_text(text);padded=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(path)],capture_output=True,check=True);pads.append(padded)
    if same_functions(pads[0],pads[1],(FUNCTION,))!=neighbors:raise ValueError('Changed record-gate padded neighbors')
    data,functions=build.link_owner(root,out,pads[0],OWNER)
    padded_words=struct.unpack_from('>139I',data,functions[FUNCTION]['value'])
    truth=struct.unpack_from('>139I',(out/'before-retail_rom').read_bytes(),ROM)
    padded_differences=sum(a!=b for a,b in zip(padded_words,truth))
    if padded_differences!=120:raise ValueError('Changed unmatched record-gate full slot')
    rows=[row]
    for label,body,flags in list(forms())[1:]:rows.append(measure(root,out,label,body,flags)[2])
    if any(r['words']==139 and r['differences']==0 for r in rows):raise ValueError('Unexpected match: inspect new evidence')
    result=dict(candidate=row,screen=rows,unchanged_raw_padded_neighbors=neighbors,owner_pools_unchanged=True,
        padded_full_slot_differences=padded_differences,production_and_guards_unchanged=True,
        installed=False,no_matching_credit=True)
    (out/'measurements.json').write_text(json.dumps(result,indent=2)+'\n')
    return obj,words,result

if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    result=qualify(root,root/BUILD)[-1]
    print(json.dumps({**result,'candidate':{k:v for k,v in result['candidate'].items() if k!='bindings'},
        'screen':[{k:v for k,v in row.items() if k!='bindings'} for row in result['screen']]},indent=2),flush=True)
