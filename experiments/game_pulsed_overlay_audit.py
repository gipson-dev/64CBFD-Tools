"""Audit the retail pulse-off inherited local; no candidate is installable."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_color_overlay_draw as previous
from tools.tests import color_overlay_draw_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-pulsed-overlay-audit'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_1AC2F0','func_1517F564',0x1517F564,0x1ACA14,111
PATHS=dict(previous.PATHS,pulse_trig_source='conker/src/game_75E60.c',
    pulse_archive='../Another Source/CBFD-Recompiled/conker/conker/src/game/game_1AC2F0.c')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    pulse_trig_source='525c47a276cb6b29ef2ad4dc7e17ce1ba5fbc8601594068ad19d57315278b744',
    pulse_archive='3ddafe8273d904489d081f052ded4fabc39105680c3a592dbc5b87c2fb4830f0')
build=previous.build
DECLARATIONS='extern u8 D_8008D010[];\nf32 func_15048A40(u8);\n'
INITIAL='''/* Diagnostic only: the retail inherited blend remains unresolved. */
Gfx *func_1517F564(Gfx *commands) {
    s32 alpha;
    f32 blend = 0.0f;
    u8 *colors;
    u32 red, green, blue;

    if (D_800DDE08 == 0) {
        return commands;
    }
    if ((alpha = D_800DDD8B) == 0) {
        return commands;
    }
    if (D_800DDD8C != 0) {
        alpha = (u32)D_800DDD8B * ((func_15048A40(D_800DDD89) + 1.0f) * 0.5f);
        blend = 0.0f;
    }
    colors = D_8008D010 + D_800DDD8A * 6;
    red = colors[0];
    green = colors[1];
    blue = colors[2];
    return func_1517F08C(commands, alpha,
        (s32)((s32)(colors[3] - red) * blend + red),
        (s32)((s32)(colors[4] - green) * blend + green),
        (s32)((s32)(colors[5] - blue) * blend + blue), 0);
}'''
SPANS={'pulse':(ENTRY,111),'draw':(0x1517F08C,197),'shift':(0x15048A40,12),
    'wave':(0x150489B0,36),'setter':(0x1517F720,15),'update':(0x1517F7B4,24),'caller':(0x150198FC,175),
    'setter_packet':(0x15025EA4,10)}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown pulse audit input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed pulse audit fixture: '+key)


def recovered_owner(before,body):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517F564() {\n    return 0;\n}':raise ValueError('Unknown pulse placeholder')
    return (before[:lo]+body+before[hi:]).replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+DECLARATIONS,1)


def forms():
    yield 'zero-substitution-rejected',INITIAL
    yield 'uninitialized-rejected',INITIAL.replace('f32 blend = 0.0f;','f32 blend;')
    yield 'explicit-local-rejected',INITIAL.replace('f32 blend = 0.0f;','f32 inherited;\n    f32 blend = inherited;')


def screens(root,out):
    freeze(root,out);before=(out/'before-color_owner').read_text()
    old,diagnostics=compile_owner(root,out,before,'owner-before')
    if diagnostics:raise ValueError('Pulse predecessor diagnostics')
    retail=list(struct.unpack_from('>111I',(out/'before-retail_rom').read_bytes(),ROM));rows=[]
    for label,body in forms():
        obj,diagnostics=compile_owner(root,out,recovered_owner(before,body),label)
        data,functions=build.link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
        words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
        rows.append(dict(label=label,words=len(words),differences=sum(a!=b for a,b in zip(words,retail))+abs(len(words)-111),
            unchanged_raw_neighbors=same_functions(old,obj,(FUNCTION,)),diagnostics=diagnostics,
            installable=False,matching_credit=False,undefined_local='uninitialized' in label or 'explicit-local' in label))
    (out/'source-screens.json').write_text(json.dumps(rows,indent=2)+'\n');return rows


def images(root,out):
    freeze(root,out);rom=(out/'before-retail_rom').read_bytes();elf=(out/'before-elf').read_bytes();result={}
    for name,(entry,length) in SPANS.items():
        offset=entry-0x15000000+0x2D4B0;data=rom[offset:offset+length*4]
        if name not in ('pulse','setter_packet'):
            at=elf_slot_offset(elf,entry,len(data))
            if elf[at:at+len(data)]!=data:raise ValueError('Live pulse chain is not retail: '+name)
        result[name]=list(struct.unpack('>%dI'%length,data))
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(screens(root,root/BUILD),indent=2),flush=True)
