"""Recover the SDK scissored rectangle and byte-sized packet animation state."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_packet_visibility as previous
from tools.tests import packet_visibility_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD='conker/build/game-packet-rectangle'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_C1D70','func_15095D34',0x15095D34,0xC31E4,346
PATHS=dict(previous.PATHS,rectangle_sdk_gbi='conker/include/2.0L/PR/gbi.h',
    rectangle_sdk_mbi='conker/include/2.0L/PR/mbi.h')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    rectangle_sdk_gbi='155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6',
    rectangle_sdk_mbi='8a0b32eb3cc7844a38b1b3ed1b160036b203efac0dc3c0275c53354423e40960')
build=previous.build
DECLARATIONS='''extern u8 D_800D2DA8, D_800D2DA9, D_800D2DAA, D_800D2DAB;
extern u8 D_800BE9A0;
'''
PACKET_FIELDS='''    u8 alpha;
    u8 animationStep;
    u8 animationFrame;
    u8 flipFlags;
    u8 paddingE[2];'''
INITIAL='''/* Emit a scissored textured rectangle, then advance the packet animation byte. */
s32 func_15095D34(s32 outputAddress, s32 packetAddress, s32 sOffset, s32 insetTOffset, s32 widthAdjust) {
    Gfx *output = (Gfx *)outputAddress;
    ProjectedPacket95B08 *packet = (ProjectedPacket95B08 *)packetAddress;
    structC1D70Descriptor *descriptor;
    f32 scaleX = D_800D2C70;
    f32 scaleY = D_800D2C74;
    f32 left = D_800D2C78;
    f32 top = D_800D2C7C;
    f32 divisor = D_800D2C80;
    f32 width;
    f32 height;
    s32 integerScaleX = (s32)scaleX;
    s32 integerScaleY = (s32)scaleY;
    s32 numerator;
    s32 originalStepS;
    s32 originalStepT;
    s32 stepS;
    s32 stepT;
    s32 integerX;
    s32 integerY;
    s32 textureS;
    s32 textureT;
    s32 fractionalT;
    s32 animationDelta;
    u8 flipFlags;
    u8 animationFlags;

    if (insetTOffset != 0) {
        D_800D2C84 -= (scaleX + scaleX) / divisor;
        D_800D2C88 -= (scaleY + scaleY) / divisor;
        left += scaleX / divisor;
        top += scaleY / divisor;
    }
    width = D_800D2C84;
    height = D_800D2C88;
    numerator = (s32)((u32)(s32)divisor << 10);
    if (width < 2.0f) {
        width = 2.0f;
    }
    originalStepS = numerator / integerScaleX;
    originalStepT = numerator / integerScaleY;
    stepS = originalStepS;
    stepT = originalStepT;
    integerX = (s32)left;
    if (D_800D2DAB == 0) {
        gDPSetPrimColor(output++, 1, 0, D_800D2DA8, D_800D2DA9, D_800D2DAA, packet->alpha);
    }
    integerY = (s32)top;
    textureS = (s32)((u32)(s32)(((32.0f - (left - (f32)integerX) * 32.0f) * divisor) /
        (f32)integerScaleX) + (u32)sOffset + 0x2000u);
    flipFlags = packet->flipFlags;
    fractionalT = (s32)(((32.0f - (top - (f32)integerY) * 32.0f) * divisor) / (f32)integerScaleY);
    textureT = (s32)((u32)fractionalT + (u32)insetTOffset + 0x2000u);
    if (flipFlags != 0) {
        if (flipFlags & 1) {
            stepS = (u16)(0u - (u32)originalStepS);
            textureS = (packet->descriptor->unk4 + 255) << 5;
        }
        if (flipFlags & 2) {
            stepT = (u16)(0u - (u32)originalStepT);
            textureT = (s32)((u32)((packet->descriptor->unk6 + 255) << 5) - (u32)fractionalT);
        }
    }
    gSPScisTextureRectangle(output++, (s32)((u32)integerX << 2), (s32)((u32)integerY << 2),
        (s32)((u32)((s32)((f32)widthAdjust + width - 1.0f) + integerX) << 2),
        (s32)((u32)((s32)(height - 1.0f) + integerY) << 2), 0, textureS, textureT, stepS, stepT);

    descriptor = packet->descriptor;
    animationFlags = descriptor->unkA;
    if (animationFlags != 0) {
        animationDelta = packet->animationStep * D_800BE9A0;
        if (animationFlags & 0x80) {
            if (packet->animationFrame & 0x80) {
                packet->animationFrame -= animationDelta;
                if (!(packet->animationFrame & 0x80)) {
                    packet->animationFrame = (packet->animationFrame + animationDelta) & 0x7F;
                }
            } else {
                packet->animationFrame += animationDelta;
                if (packet->animationFrame >= ((descriptor->unkA & 0x7F) << 3)) {
                    packet->animationFrame = (packet->animationFrame - animationDelta) | 0x80;
                }
            }
        } else {
            packet->animationFrame += animationDelta;
            if (packet->animationFrame >= (descriptor->unkA << 3)) {
                packet->animationFrame -= descriptor->unkA << 3;
            }
        }
    }
    return (s32)output;
}
'''
SELECTED=INITIAL


def forms():
    yield 'initial',INITIAL
    inline_height=INITIAL.replace('    f32 height;\n','').replace('    height = D_800D2C88;\n','').replace(
        '(height - 1.0f)','(D_800D2C88 - 1.0f)')
    yield 'inline-height',inline_height
    for name,body in (('reload-globals',INITIAL),('reload-globals-inline-height',inline_height)):
        body=body.replace('    f32 scaleX = D_800D2C70;\n','').replace('    f32 scaleY = D_800D2C74;\n','').replace(
            '    f32 divisor = D_800D2C80;\n','').replace('scaleX','D_800D2C70').replace(
            'scaleY','D_800D2C74').replace('divisor','D_800D2C80')
        yield name,body
        yield name+'-word-flags',body.replace('    u8 flipFlags;', '    s32 flipFlags;').replace(
            '    u8 animationFlags;', '    s32 animationFlags;')
    yield 'word-flags',INITIAL.replace('    u8 flipFlags;', '    s32 flipFlags;').replace(
        '    u8 animationFlags;', '    s32 animationFlags;')
    yield 'typed-output',INITIAL.replace('s32 outputAddress, s32 packetAddress,', 'Gfx *output, s32 packetAddress,').replace(
        '    Gfx *output = (Gfx *)outputAddress;\n','')
    reloaded=inline_height.replace('    f32 scaleX = D_800D2C70;\n','').replace('    f32 scaleY = D_800D2C74;\n','').replace(
        '    f32 divisor = D_800D2C80;\n','').replace('scaleX','D_800D2C70').replace(
        'scaleY','D_800D2C74').replace('divisor','D_800D2C80')
    for name,body in (('inline-height',inline_height),('reload-inline-height',reloaded),
            ('reload-inline-height-word-flags',reloaded.replace('    u8 flipFlags;', '    s32 flipFlags;').replace(
                '    u8 animationFlags;', '    s32 animationFlags;'))):
        typed=body.replace('s32 outputAddress, s32 packetAddress,', 'Gfx *output, s32 packetAddress,').replace(
            '    Gfx *output = (Gfx *)outputAddress;\n','')
        yield 'typed-output-'+name,typed
        yield 'typed-pointers-'+name,typed.replace('Gfx *output, s32 packetAddress,',
            'Gfx *output, ProjectedPacket95B08 *packet,').replace(
            '    ProjectedPacket95B08 *packet = (ProjectedPacket95B08 *)packetAddress;\n','')
    best=reloaded.replace('    u8 flipFlags;', '    s32 flipFlags;').replace(
        '    u8 animationFlags;', '    s32 animationFlags;')
    ordered=best.replace('    f32 left = D_800D2C78;\n','').replace('    f32 top = D_800D2C7C;\n','').replace(
        '    s32 integerScaleX = (s32)D_800D2C70;\n','').replace('    s32 integerScaleY = (s32)D_800D2C74;\n','')
    initializers='''    f32 left = D_800D2C78;
    s32 integerScaleX = (s32)D_800D2C70;
    f32 top = D_800D2C7C;
    s32 integerScaleY = (s32)D_800D2C74;
'''
    ordered=ordered.replace('    f32 width;',initializers+'    f32 width;')
    yield 'retail-initializers',ordered
    statements=ordered.replace(initializers,'''    f32 left;
    s32 integerScaleX;
    f32 top;
    s32 integerScaleY;
''').replace('    if (insetTOffset != 0) {',
        '    left = D_800D2C78;\n    integerScaleX = (s32)D_800D2C70;\n'
        '    top = D_800D2C7C;\n    integerScaleY = (s32)D_800D2C74;\n\n    if (insetTOffset != 0) {',1)
    yield 'retail-statements',statements
    for name,body in (('best',best),('retail',ordered)):
        simple=body.replace('    s32 originalStepS;\n    s32 originalStepT;\n','').replace(
            '    stepS = originalStepS;\n    stepT = originalStepT;\n','').replace(
            'originalStepS','stepS').replace('originalStepT','stepT')
        yield name+'-reuse-steps',simple
        yield name+'-inline-numerator',simple.replace('    s32 numerator;\n','').replace(
            '    numerator = (s32)((u32)(s32)D_800D2C80 << 10);\n','').replace(
            'numerator /','(s32)((u32)(s32)D_800D2C80 << 10) /')
        yield name+'-reuse-steps-no-flag-local',simple.replace('    s32 animationFlags;\n','').replace(
            '    animationFlags = descriptor->unkA;\n','').replace('animationFlags','descriptor->unkA')
        compact=simple.replace('    s32 numerator;\n','').replace(
            '    numerator = (s32)((u32)(s32)D_800D2C80 << 10);\n','').replace(
            'numerator /','(s32)((u32)(s32)D_800D2C80 << 10) /').replace(
            '    s32 animationFlags;\n','').replace('    animationFlags = descriptor->unkA;\n','').replace(
            'animationFlags','descriptor->unkA')
        yield name+'-inline-numerator-no-flag-local',compact
        if name=='best':
            yield 'compact-typed-output',compact.replace('s32 outputAddress, s32 packetAddress,',
                'Gfx *output, s32 packetAddress,').replace('    Gfx *output = (Gfx *)outputAddress;\n','')
            yield 'compact-typed-pointers',compact.replace('s32 outputAddress, s32 packetAddress,',
                'Gfx *output, ProjectedPacket95B08 *packet,').replace(
                '    Gfx *output = (Gfx *)outputAddress;\n','').replace(
                '    ProjectedPacket95B08 *packet = (ProjectedPacket95B08 *)packetAddress;\n','')
            yield 'compact-scales-first',compact.replace('    f32 left = D_800D2C78;\n    f32 top = D_800D2C7C;\n','').replace(
                '    s32 integerScaleY = (s32)D_800D2C74;',
                '    s32 integerScaleY = (s32)D_800D2C74;\n    f32 left = D_800D2C78;\n    f32 top = D_800D2C7C;')
    phased=INITIAL.replace('    f32 width;\n    f32 height;\n','').replace('scaleX','width').replace('scaleY','height')
    phased=phased.replace('    s32 originalStepS;\n    s32 originalStepT;\n','').replace(
        '    stepS = originalStepS;\n    stepT = originalStepT;\n','').replace(
        'originalStepS','stepS').replace('originalStepT','stepT').replace('    s32 numerator;\n','').replace(
        '    numerator = (s32)((u32)(s32)divisor << 10);\n','').replace(
        'numerator /','(s32)((u32)(s32)divisor << 10) /').replace('    u8 flipFlags;','    s32 flipFlags;').replace(
        '    u8 animationFlags;\n','').replace('    animationFlags = descriptor->unkA;\n','').replace(
        'animationFlags','descriptor->unkA')
    yield 'phased-width-height',phased
    yield 'phased-inline-height',phased.replace('    height = D_800D2C88;\n','').replace(
        '(height - 1.0f)','(D_800D2C88 - 1.0f)')
    yield 'phased-reload-divisor',phased.replace('    f32 divisor = D_800D2C80;\n','').replace('divisor','D_800D2C80')
    yield 'phased-retail-multiply',phased.replace('(width + width)','(2.0f * width)').replace(
        '(height + height)','(2.0f * height)')
    yield 'phased-typed-output',phased.replace('s32 outputAddress, s32 packetAddress,',
        'Gfx *output, s32 packetAddress,').replace('    Gfx *output = (Gfx *)outputAddress;\n','')
    yield 'phased-typed-pointers',phased.replace('s32 outputAddress, s32 packetAddress,',
        'Gfx *output, ProjectedPacket95B08 *packet,').replace('    Gfx *output = (Gfx *)outputAddress;\n','').replace(
        '    ProjectedPacket95B08 *packet = (ProjectedPacket95B08 *)packetAddress;\n','')
    selected=phased.replace('s32 outputAddress, s32 packetAddress,',
        'Gfx *output, ProjectedPacket95B08 *packet,').replace('    Gfx *output = (Gfx *)outputAddress;\n','').replace(
        '    ProjectedPacket95B08 *packet = (ProjectedPacket95B08 *)packetAddress;\n','')
    yield 'advisory-late-flip-load',selected.replace('    flipFlags = packet->flipFlags;\n','').replace(
        '    if (flipFlags != 0) {','    flipFlags = packet->flipFlags;\n    if (flipFlags != 0) {')
    yield 'register-divisor',selected.replace('    f32 divisor =', '    register f32 divisor =')


SELECTED=dict(forms())['phased-typed-pointers']
RAW_SHA256='01940fff7f9e3bf97261e6972d885ce3d2eacfe47969e8ff326e10c4662ec106'
SLOT_SHA256='9dbf7b6afd6bfaa3c0e6d995c2d187446dbbed6b4540869a79ae661aba4a49da'
RELOCATIONS={}
for _hi,_lo,_name in ((16,20,'D_800D2C70'),(24,28,'D_800D2C74'),(36,40,'D_800D2C78'),
        (52,56,'D_800D2C7C'),(60,76,'D_800D2C80'),(84,88,'D_800D2C84'),(100,104,'D_800D2C88'),
        (152,160,'D_800D2C84'),(180,188,'D_800D2C88'),(220,264,'D_800D2DAB'),
        (344,352,'D_800D2DA8'),(356,360,'D_800D2DA9'),(376,380,'D_800D2DAA'),(1188,1208,'D_800BE9A0')):
    RELOCATIONS[_hi]=[('R_MIPS_HI16',_name)]
    RELOCATIONS[_lo]=[('R_MIPS_LO16',_name)]


def freeze(root,out):
    with patch.multiple(previous,PATHS=PATHS,BASELINE=BASELINE):
        previous.freeze(root,out)


def recovered_owner(before,selected=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15095D34(s32 arg0, s32 arg1, s32 arg2, s32 arg3, s32 arg4) {\n    return 0;\n}':
        raise ValueError('Unknown packet-rectangle predecessor')
    result=before[:lo]+(SELECTED if selected is None else selected).rstrip()+before[hi:]
    if 'Gfx *output, ProjectedPacket95B08 *packet,' in result:
        result=result.replace('s32 func_15095D34(s32, s32, s32, s32, s32);\n','').replace(
            '} ProjectedPacket95B08;\n','} ProjectedPacket95B08;\n\n'
            's32 func_15095D34(Gfx *, ProjectedPacket95B08 *, s32, s32, s32);\n').replace(
            'func_15095D34(arg0, arg1,', 'func_15095D34((Gfx *)arg0, (ProjectedPacket95B08 *)arg1,')
    elif 'Gfx *output, s32 packetAddress,' in result:
        result=result.replace('s32 func_15095D34(s32, s32, s32, s32, s32);',
            's32 func_15095D34(Gfx *, s32, s32, s32, s32);').replace(
            'func_15095D34(arg0, arg1,', 'func_15095D34((Gfx *)arg0, arg1,')
    for old,new in (('extern f32 D_800D2C80, D_800D2C84, D_800D2C88;\n',
            'extern f32 D_800D2C80, D_800D2C84, D_800D2C88;\n'+DECLARATIONS),
            ('    u8 paddingA[6];',PACKET_FIELDS)):
        if result.count(old)!=1:
            raise ValueError('Unknown packet-rectangle declaration anchor')
        result=result.replace(old,new,1)
    return result


def measure(root,out,label='selected',selected=None):
    freeze(root,out)
    obj,diag=build.compile_owner(root,out,recovered_owner((out/'before-packet_owner').read_text(),selected),label)
    raw,funcs,rel=parse_object(obj)
    f=funcs[FUNCTION]
    data,fs=build.link_owner(root,out,obj,OWNER)
    linked=fs[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(linked['size']//4),data,linked['value']))
    truth=struct.unpack_from('>346I',(out/'before-retail_rom').read_bytes(),ROM)
    row=dict(label=label,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),diagnostics=diag,
        raw_sha256=hashlib.sha256(raw[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def checked_object(obj):
    text,funcs,rel=parse_object(obj)
    f=funcs[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=1380 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown packet-rectangle physical words, bindings or pools')
    return raw,bindings


def candidate_slot(data):
    if len(data)!=1384 or hashlib.sha256(data).hexdigest()!=SLOT_SHA256 or data[-4:]!=b'\0'*4:
        raise ValueError('Unknown semantic packet-rectangle padded slot')
    return data


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    if (row['words'],row['frame'],row['differences'],row['diagnostics'])!=(345,136,331,''):
        raise ValueError('Unknown packet-rectangle compiler shape')
    padded=out/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj,root/PATHS['packet_original'],filename=OWNER,
        word_patches_path=out/'before-guards'))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),str(padded)],
        check=True,capture_output=True)
    data,fs=build.link_owner(root,out,padded.with_suffix('.o'),OWNER)
    f=fs[FUNCTION]
    slot=candidate_slot(data[f['value']:f['value']+1384])
    if f['size']!=1380 or slot[:1380]!=struct.pack('>345I',*words):
        raise ValueError('Packet-rectangle padder changed the semantic body')
    target=out/'predicted-slot.bin'
    if not target.exists():
        target.write_bytes(slot)
    candidate_slot(target.read_bytes())
    row=dict(row,new_guards=0,raw_match=False,body_bytes=1380,slot_bytes=1384)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded.with_suffix('.o'),words,row


def slot_expected_image(before,slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:
        raise ValueError('Unknown packet-rectangle predecessor ELF')
    candidate_slot(slot)
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,28):
        raise ValueError('Unknown packet-rectangle predecessor extent')
    result=bytearray(before)
    at=elf_slot_offset(before,ENTRY,1384)
    result[at:at+1384]=slot
    struct.pack_into('>I',result,row[0]+8,1380)
    return bytes(result)


def expected_inputs(root,out):
    return dict(elf=serialize_symbols(slot_expected_image((out/'before-elf').read_bytes(),(out/'predicted-slot.bin').read_bytes())),
        packet_owner=recovered_owner((out/'before-packet_owner').read_text()).encode())


def serialize_symbols(initial):
    from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols, SYMBOL
    if hashlib.sha256(initial).hexdigest()!='e2e7aeb39263ac4d5eddff1c6e4c0035205932a6ff1b8415aada541df96d443a':
        raise ValueError('Unknown packet-rectangle structural prediction')
    swaps=(('D_800D237C','D_8008997C'),('D_800D2DA8','D_8008ADA8'))
    rows={name:(at,fields,string) for at,name,fields,string in symbol_rows(initial)}
    result=bytearray(initial)
    for names in swaps:
        at0,fields,first=rows[names[0]]
        cursor,base=first,first-fields[0]
        for i,name in enumerate(names):
            at,fields,string=rows[name]
            encoded=name.encode()+b'\0'
            if (at!=at0+i*SYMBOL.size or string!=cursor or
                    fields[1:]!=(int(name[2:],16),0,16,0,65521) or
                    initial[string:string+len(encoded)]!=encoded):
                raise ValueError('Changed packet-rectangle metadata swap')
            cursor+=len(encoded)
        result[first:cursor]=b''.join(name.encode()+b'\0' for name in reversed(names))
        cursor=first
        for i,name in enumerate(reversed(names)):
            SYMBOL.pack_into(result,at0+i*SYMBOL.size,cursor-base,*rows[name][1][1:])
            cursor+=len(name)+1
    if canonical_symbols(result)!=canonical_symbols(initial) or sum(a!=b for a,b in zip(result,initial))!=18:
        raise ValueError('Changed packet-rectangle serialization accounting')
    return bytes(result)


def prelink_prediction(root,out):
    def adapter(root,out):
        obj,padded,words,row=qualify(root,out)
        return obj,padded,words,None,row
    core=previous.previous.previous
    with patch.multiple(core,PATHS=PATHS,BASELINE=BASELINE,qualify=adapter,
            expected_inputs=expected_inputs):
        row=core.prelink_prediction(root,out)
    row.pop('draw_guards')
    row.pop('projected_guards')
    row.update(slot_bytes=1384,body_bytes=1380,new_guards=0,raw_match=False,unresolved_differences=331,
        metadata_serialization_bytes=18)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--screens',action='store_true')
    parser.add_argument('--qualify',action='store_true')
    parser.add_argument('--prelink',action='store_true')
    args=parser.parse_args()
    if args.prelink:
        print(json.dumps(prelink_prediction(args.root,args.root/BUILD),indent=2))
        return
    if args.qualify:
        print(json.dumps(qualify(args.root,args.root/BUILD)[-1],indent=2))
        return
    if args.screens:
        for label,body in forms():
            row=measure(args.root,args.root/BUILD,label,body)[2]
            print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics')}),flush=True)
    else:
        print(json.dumps(measure(args.root,args.root/BUILD)[2],indent=2))


if __name__=='__main__':
    main()
