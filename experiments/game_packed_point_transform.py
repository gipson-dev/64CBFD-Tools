"""Recover the packed point-slot provider and its sixteen-output transform."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_macro_lifetime as previous
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly

BUILD='conker/build/game-packed-point-transform'
OWNER='generated_C1D70'
PATHS,BASELINE,build=previous.PATHS,previous.BASELINE,previous.build
TARGETS={'func_150948C0':(0x150948C0,0xC1D70,55),'func_1509499C':(0x1509499C,0xC1E4C,71)}
DECLARATIONS='''typedef struct {
    u8 padding0;
    u8 slotRange;
    u8 padding2[2];
    s16 (*points)[8];
} PackedPointSource948C0;

extern f32 (*D_800D2C20)[4];
void func_1509499C(PackedPointSource948C0 *, s16 **);
void func_150A7960(f32 matrix[4][4], f32 x, f32 y, f32 z,
                   f32 *outX, f32 *outY, f32 *outZ);

'''
PROVIDER='''void func_1509499C(PackedPointSource948C0 *source, s16 **slots) {
    u8 range = source->slotRange;
    s16 *point = (s16 *)source->points;
    s32 index = 0;
    s16 first = range & 0xF;
    s16 end = (range >> 4) + 1;

    while (index < first) {
        slots[index++] = NULL;
    }
    while (index < end) {
        slots[index++] = point;
        point += 8;
    }
    while (index < 16) {
        slots[index++] = NULL;
    }
}'''
TRANSFORM='''/* Transform populated signed-coordinate slots; leave all other outputs intact. */
void func_150948C0(PackedPointSource948C0 *source, f32 output[][3]) {
    s16 *slots[16];
    s32 index;
    s16 **cursor;
    s16 *point;
    f32 *destination;

    func_1509499C(source, slots);
    index = 0;
    cursor = slots;
    do {
        point = *cursor;
        if (point != NULL) {
            destination = output[index];
            func_150A7960(D_800D2C20, point[0], point[1], point[2],
                           destination, destination + 1, destination + 2);
        }
        index++;
        cursor++;
    } while (index != 16);
}'''
SCREEN_INITIAL=(TRANSFORM,PROVIDER)
PREDECESSOR_FREEZE=previous.freeze


def freeze(root,out):
    from tools.tests import packed_point_transform_checkpoint as checkpoint
    read=Path.read_bytes
    with patch.object(Path,'read_bytes',lambda p:checkpoint.previous_input(read(p),p,root)):
        PREDECESSOR_FREEZE(root,out)


def forms():
    yield 'initial',SCREEN_INITIAL
    provider=PROVIDER.replace('    s32 index = 0;', '    s32 prefixIndex;\n    s16 index;').replace(
        '    while (index < first) {\n        slots[index++] = NULL;\n    }',
        '    for (prefixIndex = 0; prefixIndex < first; prefixIndex++) {\n'
        '        slots[prefixIndex] = NULL;\n    }').replace(
        '    while (index < end) {\n        slots[index++] = point;\n        point += 8;\n    }',
        '    for (index = first; index < end; index++) {\n        slots[index] = point;\n        point += 8;\n    }').replace(
        '    while (index < 16) {\n        slots[index++] = NULL;\n    }',
        '    for (; index < 16; index++) {\n        slots[index] = NULL;\n    }')
    for array in (False,True):
        for offset in (False,True):
            transform=TRANSFORM
            if array:
                transform=transform.replace('func_1509499C(source, slots);','func_1509499C(source, (s16 **)&slots);')
            if offset:
                transform=transform.replace('destination = output[index];','destination = (f32 *)(index * 12 + (u8 *)output);')
            yield 'array-'+str(int(array))+'-offset-'+str(int(offset)),(transform,provider)
    guarded='''void func_1509499C(PackedPointSource948C0 *source, s16 **slots) {
    u8 range = source->slotRange;
    s16 *point = (s16 *)source->points;
    s32 prefixIndex = 0;
    s16 first = range & 0xF;
    s16 end = (range >> 4) + 1;
    s16 index;

    if (first > 0) {
        do {
            slots[prefixIndex] = NULL;
            prefixIndex++;
        } while (prefixIndex != first);
    }
    index = first;
    if (index < end) {
        do {
            slots[index] = point;
            index++;
            point += 8;
        } while (index != end);
    }
    if (index < 16) {
        do {
            slots[index] = NULL;
            index++;
        } while (index < 16);
    }
}'''
    indexed=TRANSFORM.replace('    s16 **cursor;\n','').replace('    cursor = slots;\n','').replace(
        'point = *cursor;', 'point = slots[index];').replace('        cursor++;\n','')
    yield 'guarded-cursor',(TRANSFORM,guarded)
    yield 'guarded-indexed',(indexed,guarded)
    yield 'guarded-indexed-offset',(indexed.replace('destination = output[index];',
        'destination = (f32 *)(index * 12 + (u8 *)output);'),guarded)
    transform=indexed.replace('destination = output[index];','destination = (f32 *)(index * 12 + (u8 *)output);')
    one=guarded.replace('    s16 index;\n','').replace('prefixIndex','index')
    yield 'guarded-one-index',(transform,one)
    yield 'guarded-wide-index',(transform,guarded.replace('    s16 index;', '    s32 index;'))
    post=one.replace('            slots[index] = NULL;\n            index++;',
        '            slots[index++] = NULL;')
    for kind in ('u8','s16','s32'):
        yield 'post-clear-'+kind,(transform,post.replace('    u8 range =','    '+kind+' range =',1))
    address=transform.replace('    f32 *destination;', '    f32 *destination;\n    f32 (**matrixAddress)[4];',1).replace(
        '    index = 0;', '    matrixAddress = &D_800D2C20;\n    index = 0;',1).replace(
        'func_150A7960(D_800D2C20,', 'func_150A7960(*matrixAddress,',1)
    yield 'matrix-address',(address,one)
    yield 'matrix-address-post',(address,post)


SELECTED=dict(forms())['guarded-indexed-offset'][0]
FUNCTION,ENTRY,ROM,WORDS='func_150948C0',0x150948C0,0xC1D70,55
RAW_SHA256='ec77730c11f7586e3749fbbace26b2fa2d575272ac174ee1c09a2fa1ae968d10'
SLOT_SHA256='052c22bf6fbe9f23e5d4c3ffd9b9d1e5a2bc6192f556a42fa6845216127da0ad'
RELOCATIONS={36:[('R_MIPS_26','func_1509499C')],44:[('R_MIPS_HI16','D_800D2C20')],
    52:[('R_MIPS_LO16','D_800D2C20')],164:[('R_MIPS_26','func_150A7960')]}
GUARDS={48:(0x00008025,0x26522C20),52:(0x26522C20,0x00008025)}


def recovered_owner(before,bodies=None):
    result=before
    targets={FUNCTION:SELECTED} if bodies is None else dict(zip(TARGETS,bodies))
    for name,body in targets.items():
        lo,hi=build.function_span(result,name)
        if result[lo:hi]!='s32 '+name+'() {\n    return 0;\n}':
            raise ValueError('Unknown packed-point stub predecessor')
        result=result[:lo]+body+result[hi:]
    anchor='#include <ultra64.h>\n'
    if result.count(anchor)!=1:
        raise ValueError('Unknown packed-point declaration anchor')
    declarations=DECLARATIONS if bodies is not None else DECLARATIONS.replace(
        'void func_1509499C(PackedPointSource948C0 *, s16 **);','s32 func_1509499C();')
    return result.replace(anchor,anchor+declarations,1)


def measure(root,out,label='selected',bodies=None):
    if label=='baseline':
        raise ValueError('Reserved immutable fixture manifest label')
    freeze(root,out)
    obj,diagnostics=build.compile_owner(root,out,recovered_owner((out/'before-packet_owner').read_text(),bodies),label)
    raw,functions,rel=parse_object(obj)
    linked,placed=build.link_owner(root,out,obj,OWNER)
    rows={}
    for name,(_,rom,size) in TARGETS.items():
        f=functions[name]
        p=placed[name]
        words=struct.unpack_from('>%dI'%(f['size']//4),linked,p['value'])
        truth=struct.unpack_from('>%dI'%size,(out/'before-retail_rom').read_bytes(),rom)
        rows[name]=dict(words=len(words),differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-size),
            frame=(-words[0])&65535 if words[0]>>16==0x27BD else 0,
            raw_sha256=hashlib.sha256(raw[f['value']:f['value']+f['size']]).hexdigest(),
            relocations={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
            different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    result=dict(label=label,diagnostics=diagnostics,functions=rows,pools={n:d.hex() for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d})
    (out/(label+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    return obj,result


def proposed_guards(before):
    reader=csv.DictReader(io.StringIO(before.decode()))
    existing=list(reader)
    if any(row['filename']==OWNER and row['function']==FUNCTION for row in existing):
        raise ValueError('Unexpected prior packed-point guards')
    output=io.StringIO(newline='')
    writer=csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\r\n' if before.endswith(b'\r\n') else '\n')
    for offset,(expected,replacement) in GUARDS.items():
        if offset==52:
            expected&=0xFFFF0000
        if offset==48:
            replacement&=0xFFFF0000
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset=hex(offset),expected='0x%08X'%expected,
            replacement='0x%08X'%replacement,expected_relocations='-' if offset==48 else 'R_MIPS_LO16:D_800D2C20',
            replacement_relocations='R_MIPS_LO16:D_800D2C20' if offset==48 else '-',
            note='Normalize independent packed-point matrix-address and count initialization schedule',omit='false'))
    if not before.endswith(b'\n'):
        raise ValueError('Unexpected packed-point predecessor CSV ending')
    return before+output.getvalue().encode()


def checked_object(obj):
    text,functions,rel=parse_object(obj)
    f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=220 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown packed-point transform object/bindings/pools')
    return raw,bindings


def qualify(root,out):
    obj,result=measure(root,out,'qualified')
    checked_object(obj)
    row=result['functions'][FUNCTION]
    if (result['diagnostics'],row['words'],row['frame'],row['differences'])!=('',55,144,2):
        raise ValueError('Unknown packed-point transform compiler shape')
    if {at:(int(a,16),int(b,16)) for at,a,b in row['different_words']}!=GUARDS:
        raise ValueError('Unknown packed-point transform schedule')
    guards=out/'proposed-guards.csv'
    guards.write_bytes(proposed_guards((out/'before-guards').read_bytes()))
    padded=out/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj,root/PATHS['packet_original'],filename=OWNER,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),str(padded)],
        check=True,capture_output=True)
    data,placed=build.link_owner(root,out,padded.with_suffix('.o'),OWNER)
    slot=data[placed[FUNCTION]['value']:placed[FUNCTION]['value']+220]
    if slot!=(out/'before-retail_rom').read_bytes()[ROM:ROM+220]:
        raise ValueError('Packed-point transform is not byte exact')
    target=out/'predicted-slot.bin'
    if not target.exists():
        target.write_bytes(slot)
    if target.read_bytes()!=slot:
        raise ValueError('Changed packed-point first slot prediction')
    row=dict(row,diagnostics='',guards=2,byte_exact=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded.with_suffix('.o'),list(struct.unpack('>55I',slot)),None,row


def slot_expected_image(before,slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:
        raise ValueError('Unknown packed-point predecessor image')
    if len(slot)!=220 or hashlib.sha256(slot).hexdigest()!=SLOT_SHA256:
        raise ValueError('Unknown packed-point candidate slot')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,12):
        raise ValueError('Unknown packed-point predecessor extent')
    result=bytearray(before)
    at=elf_slot_offset(before,ENTRY,220)
    result[at:at+220]=slot
    struct.pack_into('>I',result,row[0]+8,220)
    rows={r[1]:r for r in symbol_rows(before)}
    first,second=rows['func_151AF388'],rows['D_80089974']
    names=[(r[1]+'\0').encode() for r in (first,second)]
    start,end=first[3],second[3]+len(names[1])
    if second[0]!=first[0]+16 or second[3]!=start+len(names[0]) or before[start:end]!=b''.join(names):
        raise ValueError('Unknown packed-point metadata serialization pair')
    result[first[0]:first[0]+16]=before[second[0]:second[0]+16]
    result[second[0]:second[0]+16]=before[first[0]:first[0]+16]
    struct.pack_into('>I',result,first[0],first[2][0])
    struct.pack_into('>I',result,second[0],first[2][0]+len(names[1]))
    result[start:end]=names[1]+names[0]
    return bytes(result)


def expected_inputs(root,out):
    return dict(elf=slot_expected_image((out/'before-elf').read_bytes(),(out/'predicted-slot.bin').read_bytes()),
        packet_owner=recovered_owner((out/'before-packet_owner').read_text()).encode(),
        guards=proposed_guards((out/'before-guards').read_bytes()))


def prelink_prediction(root,out):
    from tools.experiments import game_projected_packet_draw as core
    with patch.multiple(core,PATHS=PATHS,BASELINE=BASELINE,qualify=qualify,expected_inputs=expected_inputs):
        row=core.prelink_prediction(root,out)
    row.pop('draw_guards')
    row.pop('projected_guards')
    row.update(slot_bytes=220,body_bytes=220,new_guards=2,matched_functions=1,metadata_exclusions=0)
    row['metadata_serialization_bytes']=40
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--screens',action='store_true')
    parser.add_argument('--filter',default='')
    parser.add_argument('--qualify',action='store_true')
    parser.add_argument('--prelink',action='store_true')
    args=parser.parse_args()
    if args.qualify or args.prelink:
        print(json.dumps(prelink_prediction(args.root,args.root/BUILD) if args.prelink else
            qualify(args.root,args.root/BUILD)[-1],indent=2))
        return
    if args.screens:
        for label,bodies in forms():
            if args.filter and args.filter not in label:
                continue
            result=measure(args.root,args.root/BUILD,label,bodies)[1]
            print(json.dumps(dict(label=label,diagnostics=result['diagnostics'],functions={name:
                {k:row[k] for k in ('words','frame','differences')} for name,row in result['functions'].items()})),flush=True)
    else:
        print(json.dumps(measure(args.root,args.root/BUILD)[1],indent=2))


if __name__=='__main__':
    main()
