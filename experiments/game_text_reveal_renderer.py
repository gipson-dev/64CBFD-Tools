"""Recover the 102-word text reveal renderer directly from semantic C."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_text_buffer_constructor as previous
from tools.tests import text_buffer_constructor_checkpoint as predecessor

BUILD='conker/build/game-text-reveal-renderer'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_FC5F0','func_150D032C',0x150D032C,0xFD7DC,408
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE,**predecessor.ALL_AFTER)
PATHS['reveal_constants']='conker/asm/data/245340.rodata.s'
BASELINE['reveal_constants']='8fea2ca82d367e8a351e4357179b3e68a4a7e6949db442a9eb94be3a02c9bee6'
PATHS['constructor_checkpoint']='tools/tests/text_buffer_constructor_checkpoint.py'
BASELINE['constructor_checkpoint']='4168984f080ac743e50b43fc8abcb0c292855934db7ec2d491b8e225911c7e9c'
PATHS['constructor_tests']='tools/tests/test_game_text_buffer_constructor.py'
BASELINE['constructor_tests']='7a9e343dd2550bb80611b2355b33d4193cc1bb5536a911042481ff4844d6a777'
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='''typedef struct {
    f32 fraction;
    s16 characters;
    u8 reserved[2];
} TextRevealPayloadFC5F0;
typedef struct { u8 bytes[5]; } TextRevealHeaderFC5F0;
extern TextRevealHeaderFC5F0 D_800A0880;
extern f32 D_800A0888;
void func_1504332C(u8, u8, u8, u8);
void func_15042D94(s32, s32, u8, s32, ...);
'''
SELECTED='''/* Reveal the current line and append the cursor after the visible characters. */
s32 func_150D032C(u8 *record) {
    u8 *state;
    TextRevealPayloadFC5F0 *payload;
    u8 message[80];
    TextRevealHeaderFC5F0 header = D_800A0880;

    state = record + 0x28;
    payload = *(TextRevealPayloadFC5F0 **)(record + 0x48);
    if (record[0x30] & 1) {
        payload->characters = 0;
        payload->fraction = 0.0f;
    }
    if (payload->fraction < (f32)(u32)state[0x14]) {
        payload->fraction += D_800A0888 * D_800BE9A4;
        if (1.0f < payload->fraction) {
            do {
                payload->characters++;
                if ((s32)state[0x14] < payload->characters) {
                    payload->characters = state[0x14];
                }
                payload->fraction -= 1.0f;
            } while (1.0f < payload->fraction);
        }
    }
    memcpy(message, header.bytes, 4);
    memcpy(message + 4, ((void **)(state + 0x18))[state[0x15]], payload->characters);
    message[payload->characters + 4] = 0x20;
    message[payload->characters + 5] = 0xBB;
    message[payload->characters + 6] = 0;
    func_1504332C(0, 255, 0, 150);
    func_15042D94(15, 190, 128, (s32)message);
    return 1;
}'''
RAW_SHA='c213b777db37ae9607c4ca1e902d168a968c62a0c3115db119e8f64b1c56d3d8'
BINDINGS={12:[('R_MIPS_HI16','D_800A0880')],16:[('R_MIPS_LO16','D_800A0880')],
    132:[('R_MIPS_HI16','D_800A0888')],136:[('R_MIPS_LO16','D_800A0888')],
    140:[('R_MIPS_HI16','D_800BE9A4')],144:[('R_MIPS_LO16','D_800BE9A4')],
    252:[('R_MIPS_26','memcpy')],288:[('R_MIPS_26','memcpy')],
    360:[('R_MIPS_26','func_1504332C')],380:[('R_MIPS_26','func_15042D94')]}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import text_reveal_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed reveal live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed reveal frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150D032C() {\n    return 0;\n}' or before.count('#include <ultra64.h>\n')!=1:
        raise ValueError('Unknown text reveal predecessor')
    return (before[:lo]+body+before[hi:]).replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+TYPE,1)


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete text reveal words/bindings')


def padded_object(root,out,obj,label):
    return previous.padded_object(root,out,obj,label,out/'before-guards')


def qualify(root,out):
    freeze(root,out);before=(out/'before-tile_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Text reveal compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Text reveal owner pools changed')
    neighbors=previous.same_functions(old,obj,(FUNCTION,))
    padded=padded_object(root,out,obj,'candidate')
    if previous.same_functions(padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Text reveal padded neighbors changed')
    images=[]
    for path in (obj,padded):
        data,fs=build.link_owner(root,out,path,OWNER)
        images.append(list(struct.unpack_from('>102I',data,fs[FUNCTION]['value'])))
    truth=list(struct.unpack_from('>102I',(out/'before-retail_rom').read_bytes(),ROM))
    if images[0]!=truth or images[1]!=truth:raise ValueError('Incomplete text reveal match')
    row=dict(words=102,frame=128,header_home=32,message_home=40,message_bytes=80,payload_home=120,
        state_home=28,saved_ra_home=20,bindings=10,new_guards=0,unchanged_raw_padded_neighbors=neighbors,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
