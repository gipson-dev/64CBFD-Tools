"""Recover the complete text allocator with twelve bounded scratch-role guards."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_dual_fade_argument_home as previous
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.game_shared_overlay_pass import rename
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-text-buffer-constructor'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_FC5F0','func_150CFF10',0x150CFF10,0xFD3C0,292
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
freeze,build,compile_owner,parse_object,projection=previous.freeze,previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='''typedef struct {
    u8 tag;
    u8 pad01[3];
    u8 *source;
    u8 active;
    u8 pad09[3];
    u8 *start;
    u8 *next;
    u8 length, index;
    u8 pad16[2];
    u8 *buffers[2];
    u8 *payload;
    s8 kind;
    u8 flags;
    u8 pad26[2];
} TextDescriptorFC5F0;
void *func_15149130(s16, s8, s8, s8, u8, u8, u32, u8, s32);
'''
SELECTED='''/* Allocate the descriptor, payload, and two terminated line buffers. */
void *func_150CFF10(u8 tag, u8 *text, s16 duration, s32 payloadBytes, s8 kind,
                    u8 flags, u8 view, s32 owner) {
    TextDescriptorFC5F0 descriptor;
    u8 *record;
    u32 lineBytes;
    TextDescriptorFC5F0 *state;

    descriptor.index = 0;
    descriptor.active = 1;
    descriptor.source = text;
    descriptor.start = text;
    descriptor.flags = flags;
    descriptor.kind = kind;
    descriptor.tag = tag;
    descriptor.length = func_150CFD84(text, &descriptor.next);
    descriptor.buffers[0] = 0;
    descriptor.buffers[1] = 0;
    descriptor.payload = 0;
    lineBytes = (u32)func_150CFDB8(text) + 1;
    record = func_15149130(duration, -1, -1, 5, 3, 0x47,
        (u32)payloadBytes + (lineBytes - 1) * 2 + 0x2A, view, owner);
    if (record != 0) {
        state = (TextDescriptorFC5F0 *)(record + 0x28);
        memcpy(state, &descriptor, 0x28);
        state->payload = (u8 *)state + 0x28;
        state->buffers[0] = (u8 *)((u32)state->payload + (u32)payloadBytes);
        state->buffers[1] = (u8 *)((u32)state->buffers[0] + lineBytes);
        *state->buffers[0] = 0;
        *state->buffers[1] = 0;
        func_150CFE3C(record);
    }
    return record;
}'''
RAW_SHA='ce74046a0bb0ee0f190bdc1463eb0a2214a53ba36a70d6e97023bd3fa10b5390'
BINDINGS={72:[('R_MIPS_26','func_150CFD84')],96:[('R_MIPS_26','func_150CFDB8')],
          176:[('R_MIPS_26','func_15149130')],208:[('R_MIPS_26','memcpy')],264:[('R_MIPS_26','func_150CFE3C')]}
EXPECTED={7:0x93B8007F,8:0x83B9007B,10:0x240E0001,12:0xA3AE0048,16:0xA3B80065,17:0xA3B90064,
          28:0x93B90083,32:0x25D8002A,38:0xAFB80018,43:0xAFB9001C,57:0x8FAF0074,58:0x00AF1821}
WINDOWS=((0,20,{14:24,24:14,25:15,15:25}),
         (26,46,{25:24,24:15,15:25}),(56,60,{15:25,25:15}))
PATCHES={i*4:(word,rename(word,next(mapping for lo,hi,mapping in WINDOWS if lo<=i<hi))) for i,word in EXPECTED.items()}


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='void *func_150CFF10(u8 arg0, u8 *arg1, s16 arg2, s32 arg3, s8 arg4,\n                    u8 arg5, u8 arg6, s32 arg7) {\n    return 0;\n}':
        raise ValueError('Unknown text-constructor predecessor')
    if before.count('#include <ultra64.h>\n')!=1:raise ValueError('Unknown text-constructor include')
    return (before[:lo]+body+before[hi:]).replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+TYPE,1)


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete text-constructor words/bindings')


def normalize(words):
    if len(words)!=73:raise ValueError('Unknown constructor extent')
    result=list(words)
    for lo,hi,mapping in WINDOWS:
        if set(mapping)!=set(mapping.values()):raise ValueError('Non-bijective scratch map')
        for i in range(lo,hi):
            if words[i]>>26==33:
                if any((words[i]>>shift)&31 in mapping for shift in (21,16)):
                    raise ValueError('Unexpected mapped halfword operand')
            else:result[i]=rename(words[i],mapping)
    if {i*4:(a,b) for i,(a,b) in enumerate(zip(words,result)) if a!=b}!=PATCHES:
        raise ValueError('Not the fixed constructor scratch-role mapping')
    return result


def guard_bytes(before):
    rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in rows) or not before.endswith(b'\n'):
        raise ValueError('Unknown constructor guard predecessor')
    fields=next(csv.reader(io.StringIO(before.decode())));out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n')
    for at,(a,b) in sorted(PATCHES.items()):
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%at,
            expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',
            note='Normalize closed text-constructor scratch-register roles without changing homes or schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    return before+out.getvalue().encode()


def padded_object(root,out,obj,label,guards):
    text=emit_padded_assembly(obj,out/'before-tile_original',word_patches_path=guards,
        filename=OWNER,rodata_symbol='D_800A0860')
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-tile_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Text-constructor compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Text-constructor pools changed')
    neighbors=same_functions(old,obj,(FUNCTION,))
    guards=out/'candidate-guards.csv';guards.write_bytes(guard_bytes((out/'before-guards').read_bytes()))
    padded=padded_object(root,out,obj,'candidate',guards)
    if same_functions(padded_object(root,out,old,'owner-before',out/'before-guards'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Text-constructor padded neighbors changed')
    images=[]
    for path in (obj,padded):
        data,fs=build.link_owner(root,out,path,OWNER)
        images.append(list(struct.unpack_from('>73I',data,fs[FUNCTION]['value'])))
    truth=list(struct.unpack_from('>73I',(out/'before-retail_rom').read_bytes(),ROM))
    if normalize(images[0])!=truth or images[1]!=truth:raise ValueError('Incomplete constructor match')
    row=dict(words=73,frame=104,descriptor_home=64,record_home=60,line_bytes_home=56,state_home=48,
             saved_ra_home=44,bindings=5,new_guards=12,unchanged_raw_padded_neighbors=neighbors,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
