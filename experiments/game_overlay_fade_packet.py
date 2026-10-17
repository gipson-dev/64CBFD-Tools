"""Audit a complete typed overlay-fade candidate without replacing exact assembly."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_overlay_defaults as previous
from tools.tests import overlay_defaults_checkpoint as checkpoint
from tools.experiments import game_actor_callback_frame_trace as compiler
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-overlay-fade-packet'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_1AC2F0', 'func_15182670', 0x15182670, 0x1AFB20, 54
PROVIDER, MEMCPY = 0x15149130, 0x10022EC0
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
EXTRA = {
    'fade_assembly': ('conker/asm/nonmatchings/generated_1AC2F0/func_15182670.s','2c7bb1062806dd5648103f29a41782c3d23036d1eba4907bca73beeb773df1e4'),
    'fade_allocator': ('conker/src/game/done/game_1765E0.c','19dd4f8a4e0561ad2de70ee59e12e50c11a9938357816dd0eacb2334d8c0c5af'),
    'fade_E2DA0_asm': ('conker/asm/E2DA0.s','775b7775ac4fed1473936258f75859545f82f8e414fdd615e76482e1b2fa5500'),
    'fade_1028F0_asm': ('conker/asm/1028F0.s','72d80bc3125215cf183a0e17248d51d7638a0eda31676750250490204ce2799e'),
    'fade_1C1150_asm': ('conker/asm/1C1150.s','fd4078b8d271297e4c614b52d15627803edafdecc78a44a0b553e9fd1a7ccc70'),
    'fade_209B50_asm': ('conker/asm/209B50.s','30cb2777ad483fef662e1010e967ab22ec8bbfeaa35ef5a3827d35c54afa4dcd'),
    'fade_E2DA0_C': ('conker/src/game/generated_E2DA0.c','7ec8239a28aebc51123925df8f5d7c746db566b0f1f7a7cd758df68072d71bb9'),
    'fade_1028F0_C': ('conker/src/game/generated_1028F0.c','846621fb7a9d377081fab017973abcd197af40166ab952324dfd3911fb3aad6b'),
    'fade_1C1150_C': ('conker/src/game/generated_1C1150.c','66ee15eac5fb0afeb629a6814138b806ee5cbb229fff32ce4453f2a96374e355'),
    'fade_209B50_C': ('conker/src/game/generated_209B50.c','96bc301a5d81d3f371336f516cccf4eef14701d58804df2d71d163afafe1c207'),
}
EXTRA.update({'fade_compiler_'+n:('ido/ido5.3_recomp/'+n,sha) for n,sha in compiler.COMPILERS.items()})
for key,(path,sha) in EXTRA.items():
    PATHS[key], BASELINE[key] = path,sha
compile_owner, build, projection = previous.compile_owner, previous.build, previous.projection
DECLARATIONS = '''typedef struct {
    u8 red, green, blue, alpha, channel;
    s16 fade;
} OverlayFadePacket1AC2F0;
void *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);
void *memcpy(void *, const void *, size_t);
'''
SELECTED = '''/* Create a timed color overlay and attach its fade parameters. */
void func_15182670(u8 red, u8 green, u8 blue, u8 alpha, s16 duration,
                  u8 channel, u8 arg6, s32 context) {
    u8 *event;
    OverlayFadePacket1AC2F0 packet;

    if (duration > 0) {
        packet.red = red;
        packet.fade = alpha / duration;
        packet.alpha = alpha;
        packet.green = green;
        packet.blue = blue;
        packet.channel = channel;
        event = func_15149130(duration, -1, 0x39, 3, 1, 0, 8, arg6, context);
        if (event != 0) {
            memcpy(event + 0x28, &packet, 8);
        }
    }
}'''
RAW_SHA = 'f56f0f4328bb1f1cf0dfda3b78763c5b89ecdfa2cf0553a4b1a316025cfa95a8'
BINDINGS = {168:[('R_MIPS_26','func_15149130')],188:[('R_MIPS_26','memcpy')]}
PRAGMA = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_1AC2F0/func_15182670.s")'


def freeze(root, out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data = (root/path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            from tools.tests import scrolling_tile_checkpoint as installed
            data = installed.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Unknown fade audit input: '+key)
        target = out/('before-'+key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed fade audit fixture: '+key)


def recovered_owner(before, body=SELECTED):
    if before.count(PRAGMA) != 1 or before.count('#include <ultra64.h>\n') != 1:
        raise ValueError('Unknown fade assembly predecessor')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+DECLARATIONS,1).replace(PRAGMA,body)


def parts(obj):
    data,functions,relocations = parse_object(obj)
    f = functions[FUNCTION]
    return data[f['value']:f['value']+f['size']], {a-f['value']:v for a,v in relocations.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw, bindings, pool):
    if len(raw)!=212 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS or pool!=projection.POOL:
        raise ValueError('Unknown complete uninstalled fade candidate')


def forms():
    return {'selected':SELECTED,
        'fade-last':SELECTED.replace('        packet.fade = alpha / duration;\n','').replace(
            '        packet.channel = channel;', '        packet.channel = channel;\n        packet.fade = alpha / duration;'),
        'zero-padding':SELECTED.replace('        packet.channel = channel;',
            '        packet.channel = channel;\n        ((u8 *)&packet)[5] = 0;')}


def measure(root, out, label):
    if label not in forms():
        raise ValueError('Unknown bounded fade source form')
    freeze(root,out)
    obj,diagnostics = compile_owner(root,out,recovered_owner((out/'before-color_owner').read_text(),forms()[label]),label)
    if diagnostics:
        raise ValueError('Fade form compiler diagnostics')
    data,functions = build.link_owner(root,out,obj,OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    return obj,words


def candidate(root, out):
    freeze(root,out)
    obj,diagnostics = compile_owner(root,out,recovered_owner((out/'before-color_owner').read_text()),'candidate')
    if diagnostics:
        raise ValueError('Fade candidate compiler diagnostics')
    checked_parts(*parts(obj),projection.sections(obj)['.rodata'][1])
    old,diagnostics = compile_owner(root,out,(out/'before-color_owner').read_text(),'owner-before')
    if diagnostics:
        raise ValueError('Fade assembly predecessor diagnostics')
    neighbors = same_functions(old,obj,(FUNCTION,))
    pools = lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):
        raise ValueError('Fade candidate changed owner pools')
    padded = projection.padded_object(root,out,obj,'candidate')
    old_padded = projection.padded_object(root,out,old,'owner-before')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:
        raise ValueError('Fade candidate changed padded neighbors')
    images = []
    for path in (obj,padded):
        data,functions = build.link_owner(root,out,path,OWNER)
        f = functions[FUNCTION]
        images.append(list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])))
    if images[0] != images[1] or len(images[0])!=53:
        raise ValueError('Normal padding changed the complete fade candidate')
    truth = struct.unpack_from('>54I',(out/'before-retail_rom').read_bytes(),ROM)
    differences = sum(a!=b for a,b in zip(truth,images[0]))+1
    if differences!=45 or images[0][0]!=0x27BDFFC0:
        raise ValueError('Changed fade diagnostic shape')
    row = dict(words=53,retail_words=54,frame=64,ordinal_differences=differences,
        unchanged_raw_padded_neighbors=neighbors,installed=False,byte_exact=False,matching_credit=False,new_guards=0)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(candidate(root,root/BUILD)[-1],indent=2),flush=True)
