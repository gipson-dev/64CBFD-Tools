"""Fit the recovered rectangle's captured divisor and live integer temporaries."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_packet_rectangle as previous
from tools.tests import packet_rectangle_checkpoint as checkpoint
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.experiments.game_actor_classifier_candidates import sections

BUILD='conker/build/game-packet-rectangle-fitting'
OWNER,FUNCTION,ENTRY,ROM,WORDS=previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,previous.WORDS
PATHS=previous.PATHS
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER)
build=previous.build
INITIAL=previous.SELECTED


def freeze(root,out):
    with patch.object(previous,'BASELINE',BASELINE):
        previous.freeze(root,out)


def recovered_owner(before,selected=None):
    lo,hi=build.function_span(before,FUNCTION)
    body=INITIAL.split('\n',1)[1].rstrip()
    if before[lo:hi]!=body:
        raise ValueError('Unknown rectangle-fitting predecessor')
    selected=SELECTED if selected is None else selected
    return before[:lo]+selected.split('\n',1)[1].rstrip()+before[hi:]


def measure(root,out,label='selected',selected=None):
    if label=='baseline':
        raise ValueError('Reserved immutable fixture manifest label')
    with patch.multiple(previous,BASELINE=BASELINE,recovered_owner=recovered_owner):
        return previous.measure(root,out,label,selected)


def forms():
    yield 'predecessor',INITIAL
    head,tail=INITIAL.split('    width = D_800D2C84;',1)
    global_inset=head.replace(' / divisor',' / D_800D2C80')+'    width = D_800D2C84;'+tail
    yield 'global-inset-divisor',global_inset
    copied=INITIAL.replace('    f32 divisor = D_800D2C80;',
        '    f32 insetDivisor = D_800D2C80;\n    f32 divisor = insetDivisor;')
    head,tail=copied.split('    width = D_800D2C84;',1)
    yield 'copied-inset-divisor',head.replace(' / divisor',' / insetDivisor')+'    width = D_800D2C84;'+tail
    late=INITIAL.replace('    f32 divisor = D_800D2C80;','    f32 divisor;').replace(
        '    if (insetTOffset != 0) {','    divisor = D_800D2C80;\n    if (insetTOffset != 0) {',1)
    yield 'late-divisor',late
    for label,body in (('base',INITIAL),('global-inset',global_inset)):
        for target in ('stepS','integerScaleX','fractionalT','animationDelta'):
            reordered=body.replace('    s32 flipFlags;\n','').replace(
                '    s32 '+target, '    s32 flipFlags;\n    s32 '+target,1)
            if reordered==body:
                continue
            yield label+'-flip-before-'+target,reordered
        yield label+'-reverse-integers',body.replace(
            '    s32 stepS;\n    s32 stepT;\n    s32 integerX;\n    s32 integerY;\n'
            '    s32 textureS;\n    s32 textureT;\n    s32 fractionalT;\n    s32 animationDelta;\n    s32 flipFlags;',
            '    s32 flipFlags;\n    s32 animationDelta;\n    s32 fractionalT;\n    s32 textureT;\n'
            '    s32 textureS;\n    s32 integerY;\n    s32 integerX;\n    s32 stepT;\n    s32 stepS;')
    numerator=global_inset.replace('    s32 stepS;', '    s32 numerator;\n    s32 stepS;').replace(
        '(s32)((u32)(s32)divisor << 10) /','numerator /')
    for label,anchor in (('before-floor','    if (width < 2.0f)'),('after-floor','    stepS ='),
            ('before-dimensions','    width = D_800D2C84;')):
        yield 'numerator-'+label,numerator.replace(anchor,
            '    numerator = (s32)((u32)(s32)divisor << 10);\n'+anchor,1)
    originals=global_inset.replace('    s32 stepS;',
        '    s32 originalStepS;\n    s32 originalStepT;\n    s32 stepS;').replace(
        '    stepS = (s32)((u32)(s32)divisor << 10) / integerScaleX;',
        '    originalStepS = (s32)((u32)(s32)divisor << 10) / integerScaleX;').replace(
        '    stepT = (s32)((u32)(s32)divisor << 10) / integerScaleY;',
        '    originalStepT = (s32)((u32)(s32)divisor << 10) / integerScaleY;\n'
        '    stepS = originalStepS;\n    stepT = originalStepT;').replace(
        '(u32)stepS','(u32)originalStepS').replace('(u32)stepT','(u32)originalStepT')
    yield 'original-steps',originals
    for label,body in (('global-inset',global_inset),('original-steps',originals)):
        yield label+'-integer-32',body.replace('32.0f','32')
        yield label+'-half-flags',body.replace('    s32 flipFlags;', '    u8 flipFlags;')
        yield label+'-local-32',body.replace('    f32 divisor =',
            '    f32 textureUnit = 32.0f;\n    f32 divisor =').replace('32.0f -','textureUnit -')
        yield label+'-local-32-product',body.replace('    f32 divisor =',
            '    f32 textureUnit = 32.0f;\n    f32 divisor =').replace('* 32.0f','* textureUnit')
        yield label+'-late-integer-coordinates',body.replace('    integerY = (s32)top;\n','').replace(
            '    flipFlags = packet->flipFlags;','    integerY = (s32)top;\n    flipFlags = packet->flipFlags;')
        yield label+'-flags-after-Y',body.replace('    flipFlags = packet->flipFlags;\n','').replace(
            '    if (flipFlags != 0) {','    flipFlags = packet->flipFlags;\n    if (flipFlags != 0) {')
    named=numerator.replace('    if (width < 2.0f)',
        '    numerator = (s32)((u32)(s32)divisor << 10);\n    if (width < 2.0f)',1)
    yield 'named-global-fraction-divisor',named.replace('* divisor','* D_800D2C80')
    yield 'named-global-numerator',named.replace('numerator = (s32)((u32)(s32)divisor',
        'numerator = (s32)((u32)(s32)D_800D2C80')
    for label,old,new in (('outer-integer','32.0f -','32 -'),('product-integer','* 32.0f','* 32'),
            ('outer-short-float','32.0f -','32.f -'),('product-short-float','* 32.0f','* 32.f'),
            ('outer-long-float','32.0f -','32.000f -'),('product-long-float','* 32.0f','* 32.000f'),
            ('outer-cast-integer','32.0f -','(f32)32 -'),('product-cast-integer','* 32.0f','* (f32)32')):
        yield 'named-'+label,named.replace(old,new)
    yield 'named-flags-after-Y',named.replace('    flipFlags = packet->flipFlags;\n','').replace(
        '    if (flipFlags != 0) {','    flipFlags = packet->flipFlags;\n    if (flipFlags != 0) {')
    for position in ('S','T'):
        old=('    textureS = (s32)((u32)(s32)(((32.0f - (left - (f32)integerX) * 32.0f) * divisor) /\n'
            '        (f32)integerScaleX) + (u32)sOffset + 0x2000u);') if position=='S' else (
            '    fractionalT = (s32)(((32.0f - (top - (f32)integerY) * 32.0f) * divisor) / (f32)integerScaleY);')
        expr=('((32.0f - (left - (f32)integerX) * 32.0f) * divisor) / (f32)integerScaleX' if position=='S'
            else '((32.0f - (top - (f32)integerY) * 32.0f) * divisor) / (f32)integerScaleY')
        new='    fractional = '+expr+';\n'+('    textureS = (s32)((u32)(s32)fractional + (u32)sOffset + 0x2000u);'
            if position=='S' else '    fractionalT = (s32)fractional;')
        split=named.replace('    f32 divisor =','    f32 fractional;\n    f32 divisor =').replace(old,new)
        yield 'named-split-float-'+position,split
    for label,body in (('named',named),('mixed-32',named.replace('* 32.0f','* 32'))):
        direct=body.replace('    s32 flipFlags;\n','').replace('    flipFlags = packet->flipFlags;\n','').replace(
            'flipFlags','packet->flipFlags').replace('packet->packet->flipFlags','packet->flipFlags')
        yield label+'-direct-flags',direct
        yield label+'-unsigned-flags',body.replace('    s32 flipFlags;', '    u32 flipFlags;')
        yield label+'-condition-flags',body.replace('    flipFlags = packet->flipFlags;\n','').replace(
            'if (flipFlags != 0)', 'if ((flipFlags = packet->flipFlags) != 0)')
        for flags,shape in (('cached',body),('direct',direct)):
            yield label+'-'+flags+'-descriptor',shape.replace('    structC1D70Descriptor *descriptor;\n','').replace(
                '    descriptor = packet->descriptor;\n','').replace('descriptor->unkA','packet->descriptor->unkA')
    direct_descriptor=named.replace('    structC1D70Descriptor *descriptor;\n','').replace(
        '    descriptor = packet->descriptor;\n','').replace('descriptor->unkA','packet->descriptor->unkA')
    for label,body in (('named',named),('direct-descriptor',direct_descriptor),
            ('mixed',named.replace('* 32.0f','* 32')),
            ('mixed-direct-descriptor',direct_descriptor.replace('* 32.0f','* 32'))):
        for role in ('flipFlags','animationDelta','integerX'):
            reused=body.replace('    s32 '+role+';\n','').replace(role,'numerator').replace(
                'packet->numerator','packet->flipFlags')
            yield label+'-reuse-numerator-as-'+role,reused
        yield label+'-reuse-X-scale-as-flags',body.replace('    s32 flipFlags;\n','').replace(
            'flipFlags','integerScaleX').replace('packet->integerScaleX','packet->flipFlags')
    for label,body in (('named',named),('direct-descriptor',direct_descriptor),
            ('mixed-direct-descriptor',direct_descriptor.replace('* 32.0f','* 32'))):
        for role in ('fractionalT','flipFlags','textureT','stepT'):
            yield label+'-register-'+role,body.replace('    s32 '+role+';', '    register s32 '+role+';')
    fractional='(s32)(((32.0f - (top - (f32)integerY) * 32.0f) * divisor) / (f32)integerScaleY)'
    common=direct_descriptor.replace('    s32 fractionalT;\n','').replace(
        '    fractionalT = '+fractional+';\n','').replace('fractionalT','('+fractional+')')
    yield 'common-fractional-T',common
    yield 'common-fractional-T-mixed-product',common.replace('* 32.0f','* 32')
    yield 'common-fractional-T-mixed-outer',common.replace('32.0f -','32 -')


SELECTED=dict(forms())['named-cached-descriptor']
RAW_SHA256='ecb44344191b7e1034df986d516cad2e17810783fcddb537b0685a4e1b13288b'
SLOT_SHA256='7e43dc8602f4d50f636a85909c399025c80d1e7f7f55d6287a9890ab9434f1d4'
RELOCATIONS={}
for _hi,_lo,_name in ((16,20,'D_800D2C70'),(24,28,'D_800D2C74'),(32,36,'D_800D2C78'),
        (44,48,'D_800D2C7C'),(60,64,'D_800D2C80'),(88,92,'D_800D2C84'),(104,108,'D_800D2C88'),
        (156,160,'D_800D2C84'),(180,184,'D_800D2C88'),(200,228,'D_800D2DAB'),
        (348,356,'D_800D2DA8'),(360,364,'D_800D2DA9'),(380,384,'D_800D2DAA'),(1192,1212,'D_800BE9A0')):
    RELOCATIONS[_hi]=[('R_MIPS_HI16',_name)]
    RELOCATIONS[_lo]=[('R_MIPS_LO16',_name)]


def checked_object(obj):
    text,funcs,rel=parse_object(obj)
    f=funcs[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=1384 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown rectangle-fitting physical words, bindings or pools')
    return raw,bindings


def candidate_slot(data):
    if len(data)!=1384 or hashlib.sha256(data).hexdigest()!=SLOT_SHA256:
        raise ValueError('Unknown rectangle-fitting linked slot')
    return data


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    truth=list(struct.unpack_from('>346I',(out/'before-retail_rom').read_bytes(),ROM))
    if (row['words'],row['frame'],row['differences'],row['diagnostics'])!=(346,136,71,''):
        raise ValueError('Unknown rectangle-fitting compiler shape')
    if words[:104]!=truth[:104] or words[-91:]!=truth[-91:]:
        raise ValueError('Lost rectangle-fitting literal prefix or suffix')
    padded=out/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj,root/PATHS['packet_original'],filename=OWNER,
        word_patches_path=out/'before-guards'))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),str(padded)],
        check=True,capture_output=True)
    data,fs=build.link_owner(root,out,padded.with_suffix('.o'),OWNER)
    f=fs[FUNCTION]
    slot=candidate_slot(data[f['value']:f['value']+1384])
    if f['size']!=1384 or slot!=struct.pack('>346I',*words):
        raise ValueError('Rectangle-fitting padder changed the emitted body')
    target=out/'predicted-slot.bin'
    if not target.exists():
        target.write_bytes(slot)
    if target.read_bytes()!=slot:
        raise ValueError('Changed rectangle-fitting first slot prediction')
    row=dict(row,new_guards=0,raw_match=False,body_bytes=1384,slot_bytes=1384,
        literal_prefix_words=104,literal_suffix_words=91)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded.with_suffix('.o'),words,row


def slot_expected_image(before,slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:
        raise ValueError('Unknown rectangle-fitting predecessor ELF')
    candidate_slot(slot)
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,1380):
        raise ValueError('Unknown rectangle-fitting predecessor extent')
    result=bytearray(before)
    at=elf_slot_offset(before,ENTRY,1384)
    result[at:at+1384]=slot
    struct.pack_into('>I',result,row[0]+8,1384)
    return bytes(result)


def expected_inputs(root,out):
    return dict(elf=slot_expected_image((out/'before-elf').read_bytes(),(out/'predicted-slot.bin').read_bytes()),
        packet_owner=recovered_owner((out/'before-packet_owner').read_text()).encode())


def prelink_prediction(root,out):
    def adapter(root,out):
        obj,padded,words,row=qualify(root,out)
        return obj,padded,words,None,row
    core=previous.previous.previous.previous
    with patch.multiple(core,PATHS=PATHS,BASELINE=BASELINE,qualify=adapter,expected_inputs=expected_inputs):
        row=core.prelink_prediction(root,out)
    row.pop('draw_guards')
    row.pop('projected_guards')
    row.update(slot_bytes=1384,body_bytes=1384,new_guards=0,raw_match=False,unresolved_differences=71,
        metadata_serialization_bytes=0,literal_prefix_words=104,literal_suffix_words=91)
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
        row=qualify(args.root,args.root/BUILD)[-1]
        print(json.dumps({k:row[k] for k in ('words','frame','differences','raw_sha256','literal_prefix_words','literal_suffix_words')}))
        print('Padded slot SHA',hashlib.sha256((args.root/BUILD/'predicted-slot.bin').read_bytes()).hexdigest())
        return
    for label,body in forms() if args.screens else [('selected',SELECTED)]:
        row=measure(args.root,args.root/BUILD,label,body)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics')}),flush=True)


if __name__=='__main__':
    main()
