"""Recover the complete overlay point projection and coupled clamp state."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_pulsed_overlay_audit as previous
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD='conker/build/game-overlay-projection'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_1AC2F0','func_1517F814',0x1517F814,0x1ACCC4,120
PATHS=dict(previous.PATHS,overlay_reset_owner='conker/src/game/done/game_35EC0.c',overlay_boot_owner='conker/src/init_1050.c')
BASELINE=dict(previous.BASELINE,overlay_reset_owner='79b2611443ab08bfb61504acb4e25d89d810e79bf11593b1129c576ac4fd827c',
    overlay_boot_owner='20f8596c3faf39460b35ba6351994700a81d9f126cf1f8e4a5620b3d6a6a115b')
build=previous.build
DECLARATIONS='''extern f32 D_800D9D10[][4][4];
extern f32 D_800A7280, D_800A7284, D_800A7288;
void func_150A7A00(f32 matrix[4][4], f32 x, f32 y, f32 z,
    f32 *outX, f32 *outY, f32 *outZ, f32 *outW);
'''
INITIAL='''/* Project or accept screen coordinates, clamp, and publish relative offsets. */
void func_1517F814(s32 screenSpace, f32 x, f32 y, f32 z, s32 view) {
    f32 projectedX;
    f32 projectedY;
    f32 projectedZ;
    f32 divisor;
    f32 lower;
    OverlayViewport1AC2F0 *record;

    if (screenSpace == 0) {
        func_150A7A00((f32 (*)[4])((u8 *)D_800D9D10 + (u32)view * 64U),
            x, y, z, &projectedX, &projectedY, &projectedZ, &divisor);
        if (divisor == 0.0f) {
            divisor = 1.0f;
        }
        record = &OVERLAY_VIEWS_1AC2F0[view];
        projectedX = (record->extentX * projectedX) / divisor;
        projectedY = (record->extentY * projectedY) / divisor;
        projectedX += record->extentX;
        projectedY = record->extentY - projectedY;
        projectedX += record->left;
        projectedY += record->top;
    } else {
        projectedX = x;
        projectedY = y;
        record = &OVERLAY_VIEWS_1AC2F0[view];
    }
    if (D_800A7280 < projectedX) {
        lower = D_800A7284;
        projectedX = D_800A7280;
    } else {
        lower = D_800A7288;
        if (projectedX < lower) {
            projectedX = lower;
        }
    }
    if (D_800A7280 < projectedY) {
        projectedY = D_800A7280;
    } else if (projectedY < lower) {
        projectedY = lower;
    }
    D_800DDDE8[view][0] = projectedX - record->extentX;
    D_800DDDE8[view][1] = projectedY - record->extentY;
}'''
SELECTED=INITIAL.replace('D_800A7280','10000.0f').replace('D_800A7284','-10000.0f').replace('D_800A7288','-10000.0f')
POOL_SYMBOL='D_800A7280'
POOL=bytes.fromhex('461c4000c61c4000c61c400000000000')
RAW_SHA='20560682428e8b425af3ad0f2b7c7a7d3aab7466a2ea30128904fcb35c8514e4'
POOL_USES={292,296,304,328,332,344}


def forms():
    floats='    f32 projectedX;\n    f32 projectedY;\n    f32 projectedZ;\n    f32 divisor;\n'
    lower='    f32 lower;\n';record='    OverlayViewport1AC2F0 *record;\n'
    old=floats+lower+record
    for name,new in (('record-lower-first',record+lower+floats),('record-first',record+floats+lower),
            ('lower-first',lower+floats+record),('register-lower',floats+lower.replace('f32','register f32')+record),
            ('register-record',floats+lower+record.replace('Overlay','register Overlay'))):
        yield name,INITIAL.replace(old,new)
    yield 'reuse-z',INITIAL.replace(lower,'').replace('lower','z')
    first=INITIAL.replace(old,record+lower+floats)
    for label,body in (('floats',first),('array',first.replace(floats,'    f32 point[4];\n').replace(
            'projectedX','point[3]').replace('projectedY','point[2]').replace('projectedZ','point[1]').replace('divisor','point[0]'))):
        yield label+'-late-lower',body.replace(lower,'').replace('    if (D_800A7280 <','    {\n    f32 lower;\n    if (D_800A7280 <',1).replace('\n}', '\n    }\n}')
        yield label+'-inline-record',body.replace(record,'').replace('        record = &OVERLAY_VIEWS_1AC2F0[view];\n','').replace('record->','OVERLAY_VIEWS_1AC2F0[view].')
        if label=='array':yield 'array-record-lower-first',body
    for label,expression in (('matrix-index','D_800D9D10[view]'),('matrix-signed','(f32 (*)[4])((u8 *)D_800D9D10 + view * 64)'),
            ('matrix-shift','(f32 (*)[4])((u8 *)D_800D9D10 + ((u32)view << 6))')):
        yield label,first.replace('(f32 (*)[4])((u8 *)D_800D9D10 + (u32)view * 64U)',expression)
    yield 'cached-upper',first.replace('    f32 lower;','    f32 lower, upper;').replace(
        '    if (D_800A7280 < projectedX)', '    upper = D_800A7280;\n    if (upper < projectedX)').replace(
        'projectedX = D_800A7280;', 'projectedX = upper;').replace('if (D_800A7280 < projectedY)',
        'if (upper < projectedY)').replace('projectedY = D_800A7280;', 'projectedY = upper;')
    yield 'literal-bounds',first.replace('D_800A7280','10000.0f').replace('D_800A7284','-10000.0f').replace('D_800A7288','-10000.0f')
    for name in ('x','y'):
        yield 'reuse-'+name,first.replace(lower,'').replace('lower',name)
    for name,body in (('literal-initial',INITIAL),('literal-lower-last',INITIAL.replace(old,floats+record+lower))):
        yield name,body.replace('D_800A7280','10000.0f').replace('D_800A7284','-10000.0f').replace('D_800A7288','-10000.0f')


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import clipped_rectangle_checkpoint as successor
            data=successor.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import overlay_projection_checkpoint as installed
            data=installed.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown overlay projection input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed projection fixture: '+key)


def recovered_owner(before,body=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517F814() {\n    return 0;\n}':raise ValueError('Unknown projection placeholder')
    result=(before[:lo]+(SELECTED if body is None else body)+before[hi:])
    anchor='    u8 padding00[0x24];\n'
    if result.count(anchor)!=1:raise ValueError('Unknown viewport layout')
    result=result.replace(anchor,'    u8 padding00[0xC];\n    f32 extentX, extentY;\n    u8 padding14[0x10];\n',1)
    return result.replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+DECLARATIONS,1)


def parts(obj):
    data,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in relocations.items() if f['value']<=a<f['value']+f['size']}


def measure(root,out,label,body):
    freeze(root,out);before=(out/'before-color_owner').read_text()
    obj,diagnostics=compile_owner(root,out,recovered_owner(before,body),label)
    data,functions=build.link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    wanted=list(struct.unpack_from('>120I',(out/'before-retail_rom').read_bytes(),ROM))
    row=dict(label=label,words=len(words),differences=sum(a!=b for a,b in zip(words,wanted))+abs(len(words)-120),
        frame=(-words[0]&65535) if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(parts(obj)[0]).hexdigest(),bindings=parts(obj)[1])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def padded_object(root,out,obj,label):
    text=emit_padded_assembly(obj,out/'before-color_provider_original',word_patches_path=out/'before-guards',
        filename=OWNER,rodata_symbol=POOL_SYMBOL)
    path=out/(label+'-padded.s');path.write_text(text);target=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(path)],capture_output=True,check=True)
    return target


def checked_parts(data,bindings,pool):
    expected={32:[('R_MIPS_HI16','D_800D9D10')],36:[('R_MIPS_LO16','D_800D9D10')],88:[('R_MIPS_26','func_150A7A00')],
        120:[('R_MIPS_HI16','D_800BE628')],148:[('R_MIPS_LO16','D_800BE628')],24:[('R_MIPS_HI16','D_800BE628')],
        264:[('R_MIPS_LO16','D_800BE628')],428:[('R_MIPS_HI16','D_800DDDE8')],432:[('R_MIPS_LO16','D_800DDDE8')]}
    expected.update({at:[('R_MIPS_HI16' if at in (292,304,328) else 'R_MIPS_LO16','.rodata')] for at in POOL_USES})
    if len(data)!=480 or hashlib.sha256(data).hexdigest()!=RAW_SHA or bindings!=expected or pool!=POOL:
        raise ValueError('Unknown complete projection words, bindings or three-literal pool')


def bound_raw(root,out,obj):
    text,relocations=parts(obj)
    bindings={a:[(kind,POOL_SYMBOL if symbol=='.rodata' else symbol) for kind,symbol in rows] for a,rows in relocations.items()}
    anchors={symbol:int(symbol.split('_',1)[1],16) for rows in bindings.values() for _,symbol in rows}
    assembly,unresolved=emit_function(text,dict(value=0,size=len(text)),bindings,FUNCTION,anchors)
    if unresolved:raise ValueError('Unresolved raw projection pool binding')
    path=out/'bound-raw.s';path.write_text(assembly);target=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(path)],capture_output=True,check=True)
    return target


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED)
    if (row['words'],row['differences'],row['frame'],row['diagnostics'])!=(120,6,64,''):
        raise ValueError('Projection is not a complete direct match: '+json.dumps(row))
    checked_parts(*parts(obj),sections(obj)['.rodata'][1])
    mapped=bound_raw(root,out,obj);data,functions=build.link_owner(root,out,mapped,OWNER)
    if data!=(out/'before-retail_rom').read_bytes()[ROM:ROM+480]:raise ValueError('Raw C pool binding differs')
    linked_words=list(struct.unpack('>120I',data))
    old,diagnostics=compile_owner(root,out,(out/'before-color_owner').read_text(),'owner-before')
    if diagnostics:raise ValueError('Projection predecessor diagnostics')
    neighbors=same_functions(old,obj,(FUNCTION,))
    padded=padded_object(root,out,obj,'qualified')
    old_padded=padded_object(root,out,old,'owner-before')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Padded projection neighbor changed')
    data,functions=build.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=480 or data[f['value']:f['value']+480]!=(out/'before-retail_rom').read_bytes()[ROM:ROM+480]:
        raise ValueError('Padded projection differs')
    row.update(direct=True,guards=0,linked_differences=0,unchanged_raw_padded_neighbors=neighbors,
        literal_bytes_bound=12,alignment_padding_not_installed=4,raw_pool_binding=POOL_SYMBOL)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');return obj,padded,linked_words,row


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--qualify',action='store_true');parser.add_argument('--screens',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.screens:
        for label,body in forms():
            row=measure(root,root/BUILD,label,body)[-1]
            print(json.dumps({k:row[k] for k in ('label','words','differences','frame','diagnostics')}),flush=True)
    else:print(json.dumps((qualify(root,root/BUILD) if args.qualify else measure(root,root/BUILD,'initial',INITIAL))[-1],indent=2),flush=True)
