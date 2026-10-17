"""Recover the complete fixed descriptor and transition payload constructor."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_scrolling_tile_windows as previous
from tools.tests import scrolling_tile_checkpoint as checkpoint
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-fixed-transition-constructor'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_FC5F0','func_150CF680',0x150CF680,0xFCB30,96
SIZE = WORDS*4
FACTORY, ALLOCATOR, MEMCPY, MODE = 0x1515548C,0x15167A68,0x10022EC0,0x80082FA0
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE,**checkpoint.AFTER)
EXTRA = {
    'transition_factory':('conker/asm/nonmatchings/generated_17CAF0/func_1515548C.s','77e398f79da73fa9fa0883f9558201d6af00d821b7b7e85f5b16d8c2c088df7d'),
    'transition_factory_owner':('conker/src/game/generated_17CAF0.c','ef7ce9ba93d701256bdebeb6dac2194115b0e33252b83e3bba4a1bae5661c015'),
    'transition_caller':('conker/asm/50D80.s','58dec15b45859c1dface2fc227f074871296eb4884e6499e4cfee37b8389111c'),
    'transition_caller_owner':('conker/src/game/generated_50D80.c','b24a3bfada6d6003f33b080e1bea3c5f328d1c829e70dd1ab5b067cdaac6e318'),
}
for key,(path,sha) in EXTRA.items():
    PATHS[key],BASELINE[key] = path,sha
build,compile_owner,projection,padded_object = previous.build,previous.compile_owner,previous.projection,previous.padded_object
DECLARATIONS = '''extern s32 D_80082FA0;
/* The view byte occupies the first byte of a word-aligned descriptor cell. */
typedef union {
    u8 byte;
    s32 word;
} TransitionViewFC5F0;
typedef struct {
    f32 position[2];
    f32 scale[2];
    u8 tag;
    s16 id;
    u16 flags;
    s16 size0, size1;
    u8 kind, field1B, field1C, field1D, duration, field1F;
    u8 field20, field21, field22, opacity;
    s32 field24, field28, field2C, field30, field34, field38, field3C;
    u8 field40, field41;
    TransitionViewFC5F0 view;
    f32 field48, field4C, field50, field54;
} TransitionDescriptorFC5F0;
typedef struct {
    u8 state;
    f32 field04, field08, field0C;
} TransitionPayloadFC5F0;
void *func_1515548C(void *, s32, s32 *, s32, s32, u8, s32);
'''
SELECTED = '''/* Create the fixed descriptor and attach its transition payload. */
void func_150CF680(s16 id, u8 slot, s32 context) {
    TransitionDescriptorFC5F0 descriptor;
    TransitionPayloadFC5F0 payload;
    u8 *event;

    descriptor.position[1] = 72.0f;
    descriptor.tag = 0xC1;
    descriptor.id = id;
    descriptor.flags = 0x31;
    descriptor.size0 = 1;
    descriptor.size1 = 0xFF;
    descriptor.kind = 8;
    descriptor.field1B = 0xFF;
    descriptor.field1C = 0xFF;
    descriptor.field1D = 0xFF;
    descriptor.duration = 0xFF;
    descriptor.field1F = 0xFF;
    descriptor.field20 = 0xFF;
    descriptor.field21 = 0xFF;
    descriptor.field22 = 0xFF;
    descriptor.opacity = 0xFF;
    descriptor.field28 = 0x200004;
    payload.state = 0;
    payload.field04 = 0.0f;
    descriptor.position[0] = -300.0f;
    payload.field08 = -300.0f;
    payload.field0C = 0.0f;
    descriptor.scale[1] = 7.5f;
    descriptor.scale[0] = 7.5f;
    descriptor.field24 = 0;
    descriptor.field2C = 0x9F0601;
    descriptor.field40 = 0;
    descriptor.field41 = 10;
    descriptor.field30 = 23;
    descriptor.field34 = 68;
    descriptor.field38 = 128;
    descriptor.field3C = 32;
    descriptor.field4C = 1.0f;
    descriptor.field48 = 1.0f;
    descriptor.field54 = 0.0f;
    descriptor.field50 = 0.0f;
    descriptor.view.byte = D_80082FA0;
    event = func_1515548C(&descriptor, 12, 0, 0, 16, slot, context);
    if (event != 0) {
        memcpy(event + 0x70, &payload, 16);
    }
}'''
RAW_SHA = '85acd74b8db2e84d805a1d4a410d1c876f8a61e6e77544b753f08628b6db79ba'
BINDINGS = {156:[('R_MIPS_HI16','D_80082FA0')],164:[('R_MIPS_LO16','D_80082FA0')],
    340:[('R_MIPS_26','func_1515548C')],360:[('R_MIPS_26','memcpy')]}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data = (root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import fixed_transition_checkpoint as installed
            data = installed.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            raise ValueError('Unknown transition constructor input: '+key)
        target = out/('before-'+key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes()!=data:
            raise ValueError('Changed transition constructor fixture: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi = build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150CF680() {\n    return 0;\n}' or before.count('#include <ultra64.h>\n')!=1:
        raise ValueError('Unknown transition constructor predecessor')
    return (before[:lo]+body+before[hi:]).replace('#include <ultra64.h>\n',
        '#include <ultra64.h>\n'+DECLARATIONS,1)


def parts(obj):
    data,functions,relocations = parse_object(obj); f=functions[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in relocations.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown complete transition constructor words/bindings')


def qualify(root,out):
    freeze(root,out)
    before = (out/'before-tile_owner').read_text()
    obj,diag = compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag = compile_owner(root,out,before,'owner-before')
    if diag or old_diag:
        raise ValueError('Transition constructor compiler diagnostics')
    checked_parts(*parts(obj))
    pools = lambda p:{n:d for n,(_,d) in projection.sections(p).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):
        raise ValueError('Transition constructor pools changed')
    neighbors = same_functions(old,obj,(FUNCTION,))
    padded,old_padded = padded_object(root,out,obj,'candidate'),padded_object(root,out,old,'owner-before')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:
        raise ValueError('Transition constructor padded neighbors changed')
    truth = list(struct.unpack_from('>96I',(out/'before-retail_rom').read_bytes(),ROM))
    images = []
    for path in (obj,padded):
        data,functions = build.link_owner(root,out,path,OWNER); f=functions[FUNCTION]
        words = list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
        if words!=truth:
            raise ValueError('Transition constructor does not emit all 96 retail words')
        images.append(words)
    row = dict(words=96,frame=152,prologue_word=3,bindings=4,new_guards=0,unchanged_raw_padded_neighbors=neighbors)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
