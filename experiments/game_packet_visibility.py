"""Recover packet dimensions, view-dependent scaling and visible rectangle outputs."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_visible_depth_packet as previous
from tools.tests import visible_depth_packet_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD='conker/build/game-packet-visibility'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_C1D70','func_15095B08',0x15095B08,0xC2FB8,129
PATHS=dict(previous.PATHS,visibility_scale_writer='conker/src/init_39C0.c')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    visibility_scale_writer='c5e508d7ea1d716ec15788a5c7683bafc524d6ed8f7e4167c036cc3832445757')
build=previous.build
DECLARATIONS='''extern f32 D_800380A0, D_800380A4;
extern f32 D_800D2C70, D_800D2C74, D_800D2C78, D_800D2C7C;
extern f32 D_800D2C80, D_800D2C84, D_800D2C88;
'''
PACKET='''
typedef struct {
    s16 coordinates[3];
    s16 extentX, extentY;
    u8 paddingA[6];
    structC1D70Descriptor *descriptor;
} ProjectedPacket95B08;
'''
VIEW_FIELDS='''    f32 flatScaleX, flatScaleY;
    f32 projectedScaleX, projectedScaleY;
    f32 clipTop, clipBottom, clipLeft, clipRight;'''
INITIAL='''/* Scale the packet rectangle, test viewport overlap, and publish draw inputs. */
void func_15095B08(s32 packetAddress, f32 x, f32 y, f32 divisor, s32 projected, s32 *visible) {
    ProjectedPacket95B08 *packet = (ProjectedPacket95B08 *)packetAddress;
    ProjectedViewFrame95760 *view;
    structC1D70Descriptor *descriptor;
    s32 extentX;
    s32 extentY;
    f32 scaleX;
    f32 scaleY;
    f32 inverse;
    f32 width;
    f32 height;

    *visible = 0;
    extentX = packet->extentX;
    if (extentX != 0) {
        extentY = packet->extentY;
        if (extentY != 0) {
            scaleX = (f32)extentX * D_800380A0;
            scaleY = (f32)extentY * D_800380A4;
            if (projected != 0) {
                view = (ProjectedViewFrame95760 *)D_800BE628 + D_80082FA4;
                scaleX *= view->projectedScaleX;
                scaleY *= view->projectedScaleY;
            } else {
                view = (ProjectedViewFrame95760 *)D_800BE628 + D_80082FA4;
                scaleX *= view->flatScaleX;
                scaleY *= view->flatScaleY;
            }
            descriptor = packet->descriptor;
            inverse = 1.0f / divisor;
            width = (f32)(u32)descriptor->unk4 * scaleX * inverse;
            height = (f32)(u32)descriptor->unk6 * scaleY * inverse;
            x -= width * 0.5f;
            y -= height * 0.5f;
            if (view->clipLeft <= x + width && x < view->clipRight &&
                view->clipTop <= y + height && y < view->clipBottom) {
                *visible = 1;
            }
            D_800D2C70 = scaleX;
            D_800D2C74 = scaleY;
            D_800D2C78 = x;
            D_800D2C7C = y;
            D_800D2C80 = divisor;
            D_800D2C84 = width;
            D_800D2C88 = height;
        }
    }
}
'''
SELECTED=INITIAL


def forms():
    yield 'initial',INITIAL
    staged=INITIAL.replace('            scaleX = (f32)extentX * D_800380A0;\n'
        '            scaleY = (f32)extentY * D_800380A4;',
        '            scaleX = (f32)extentX;\n            scaleY = (f32)extentY;\n'
        '            scaleX *= D_800380A0;\n            scaleY *= D_800380A4;')
    yield 'staged-casts',staged
    yield 'half-extents',INITIAL.replace('    s32 extentX;\n    s32 extentY;',
        '    s16 extentX;\n    s16 extentY;')
    yield 'half-staged-casts',staged.replace('    s32 extentX;\n    s32 extentY;',
        '    s16 extentX;\n    s16 extentY;')
    yield 'staged-pixels',staged.replace('    f32 inverse;',
        '    u32 pixelsX;\n    u32 pixelsY;\n    f32 inverse;').replace(
        '            inverse = 1.0f / divisor;',
        '            pixelsX = descriptor->unk4;\n            inverse = 1.0f / divisor;').replace(
        'width = (f32)(u32)descriptor->unk4', 'width = (f32)pixelsX').replace(
        '            height = (f32)(u32)descriptor->unk6',
        '            pixelsY = descriptor->unk6;\n            height = (f32)pixelsY')
    separate=INITIAL.replace('    f32 scaleX;', '    f32 baseScaleX;\n    f32 baseScaleY;\n    f32 scaleX;').replace(
        '            scaleX = (f32)extentX * D_800380A0;', '            baseScaleX = (f32)extentX * D_800380A0;').replace(
        '            scaleY = (f32)extentY * D_800380A4;', '            baseScaleY = (f32)extentY * D_800380A4;').replace(
        'scaleX *= view->', 'scaleX = baseScaleX * view->').replace('scaleY *= view->', 'scaleY = baseScaleY * view->')
    yield 'separate-base-scales',separate
    captured=INITIAL.replace('    f32 inverse;', '    f32 left;\n    f32 top;\n    f32 inverse;').replace(
        '            x -= width * 0.5f;', '            left = x - width * 0.5f;').replace(
        '            y -= height * 0.5f;', '            top = y - height * 0.5f;').replace(
        '<= x + width && x <', '<= left + width && left <').replace(
        '<= y + height && y <', '<= top + height && top <').replace(
        'D_800D2C78 = x;', 'D_800D2C78 = left;').replace('D_800D2C7C = y;', 'D_800D2C7C = top;')
    yield 'separate-position',captured
    yield 'float-extents',INITIAL.replace('    s32 extentX;\n    s32 extentY;',
        '    f32 extentX;\n    f32 extentY;')
    u16=INITIAL.replace('    f32 inverse;', '    u16 pixelsX;\n    u16 pixelsY;\n    f32 inverse;').replace(
        '            inverse = 1.0f / divisor;',
        '            pixelsX = descriptor->unk4;\n            inverse = 1.0f / divisor;').replace(
        'width = (f32)(u32)descriptor->unk4', 'width = (f32)(u32)pixelsX').replace(
        '            height = (f32)(u32)descriptor->unk6',
        '            pixelsY = descriptor->unk6;\n            height = (f32)(u32)pixelsY')
    yield 'half-pixels',u16
    yield 'half-pixels-direct',u16.replace('(f32)(u32)pixels','(f32)pixels')
    yield 'float-view',INITIAL.replace('    ProjectedViewFrame95760 *view;', '    f32 *view;').replace(
        'view = (ProjectedViewFrame95760 *)D_800BE628 + D_80082FA4;',
        'view = (f32 *)(D_800BE628 + D_80082FA4 * 0x180);').replace(
        'view->projectedScaleX','view[7]').replace('view->projectedScaleY','view[8]').replace(
        'view->flatScaleX','view[5]').replace('view->flatScaleY','view[6]').replace(
        'view->clipTop','view[9]').replace('view->clipBottom','view[10]').replace(
        'view->clipLeft','view[11]').replace('view->clipRight','view[12]')
    declarations='    f32 scaleX;\n    f32 scaleY;\n    f32 inverse;\n    f32 width;\n    f32 height;'
    names=('scaleX','scaleY','inverse','width','height')
    for i in range(1,5):
        order=names[i:]+names[:i]
        yield 'declarations-'+str(i),INITIAL.replace(declarations,'\n'.join('    f32 '+n+';' for n in order))
    yield 'declarations-reversed',INITIAL.replace(declarations,'\n'.join('    f32 '+n+';' for n in reversed(names)))
    globals_first=INITIAL.replace('            scaleX = (f32)extentX * D_800380A0;\n'
        '            scaleY = (f32)extentY * D_800380A4;',
        '            scaleX = D_800380A0;\n            scaleY = D_800380A4;\n'
        '            scaleX = (f32)extentX * scaleX;\n            scaleY = (f32)extentY * scaleY;')
    yield 'globals-first',globals_first
    yield 'reversed-global-operands',INITIAL.replace('(f32)extentX * D_800380A0','D_800380A0 * (f32)extentX').replace(
        '(f32)extentY * D_800380A4','D_800380A4 * (f32)extentY')
    yield 'left-assignments',INITIAL.replace('x -= width * 0.5f;', 'x = x - (width * 0.5f);').replace(
        'y -= height * 0.5f;', 'y = y - (height * 0.5f);')
    yield 'early-rejection',INITIAL.replace('    if (extentX != 0) {\n',
        '    if (extentX == 0) {\n        return;\n    }\n    {\n').replace(
        '        if (extentY != 0) {\n','        if (extentY == 0) {\n            return;\n        }\n        {\n')
    named=globals_first.replace('    f32 inverse;', '    f32 globalScaleX;\n    f32 globalScaleY;\n    f32 inverse;').replace(
        '            scaleX = D_800380A0;', '            globalScaleX = D_800380A0;').replace(
        '            scaleY = D_800380A4;', '            globalScaleY = D_800380A4;').replace(
        '(f32)extentX * scaleX','(f32)extentX * globalScaleX').replace(
        '(f32)extentY * scaleY','(f32)extentY * globalScaleY')
    yield 'named-global-scales',named
    yield 'named-casts-first',named.replace('            globalScaleX = D_800380A0;',
        '            scaleX = (f32)extentX;\n            scaleY = (f32)extentY;\n            globalScaleX = D_800380A0;').replace(
        'scaleX = (f32)extentX * globalScaleX;', 'scaleX *= globalScaleX;').replace(
        'scaleY = (f32)extentY * globalScaleY;', 'scaleY *= globalScaleY;')
    yield 'global-scales-between-casts',globals_first.replace('            scaleX = D_800380A0;',
        '            scaleX = (f32)extentX;\n            scaleY = (f32)extentY;\n            scaleX *= D_800380A0;').replace(
        '            scaleY = D_800380A4;', '            scaleY *= D_800380A4;').replace(
        '            scaleX = (f32)extentX * scaleX;\n            scaleY = (f32)extentY * scaleY;\n','')


def freeze(root,out):
    with patch.multiple(previous,PATHS=PATHS,BASELINE=BASELINE):
        previous.freeze(root,out)


def recovered_owner(before,selected=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15095B08(s32 arg0, f32 arg1, f32 arg2, f32 arg3, s32 arg4, s32 *arg5) {\n    return 0;\n}':
        raise ValueError('Unknown packet-visibility predecessor')
    result=before[:lo]+(SELECTED if selected is None else selected).rstrip()+before[hi:]
    for old,new in (
            ('extern f32 D_8009DEC0;\n','extern f32 D_8009DEC0;\n'+DECLARATIONS),
            ('    u8 padding14[0x20];',VIEW_FIELDS),
            ('} structC1D70Descriptor;\n','} structC1D70Descriptor;\n'+PACKET),
            ('s32 func_15095B08(s32, f32, f32, f32, s32, s32 *);',
             'void func_15095B08(s32, f32, f32, f32, s32, s32 *);')):
        if result.count(old)!=1:
            raise ValueError('Unknown packet-visibility declaration anchor')
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
    truth=struct.unpack_from('>129I',(out/'before-retail_rom').read_bytes(),ROM)
    row=dict(label=label,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),diagnostics=diag,
        raw_sha256=hashlib.sha256(raw[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


SELECTED=dict(forms())['globals-first']
RAW_SHA256='eef5e7c981574013d8192371d63534a1a3ea879664207c564e7b98b69c98f182'
RELOCATIONS={64:[('R_MIPS_HI16','D_800380A0')],72:[('R_MIPS_LO16','D_800380A0')],
    76:[('R_MIPS_HI16','D_800380A4')],80:[('R_MIPS_LO16','D_800380A4')],
    96:[('R_MIPS_HI16','D_80082FA4')],100:[('R_MIPS_HI16','D_80082FA4')],
    116:[('R_MIPS_LO16','D_80082FA4')],120:[('R_MIPS_HI16','D_800BE628')],
    124:[('R_MIPS_LO16','D_800BE628')],172:[('R_MIPS_LO16','D_80082FA4')],
    176:[('R_MIPS_HI16','D_800BE628')],180:[('R_MIPS_LO16','D_800BE628')]}
for _at,_name in ((328,'D_800D2C70'),(452,'D_800D2C74'),(460,'D_800D2C78'),
        (468,'D_800D2C7C'),(476,'D_800D2C80'),(484,'D_800D2C84'),(492,'D_800D2C88')):
    RELOCATIONS[_at]=[('R_MIPS_HI16',_name)]
    RELOCATIONS[448 if _at==328 else _at+4]=[('R_MIPS_LO16',_name)]
GUARDS={0x3C:(0x44834000,0x44833000),0x44:(0x468021A0,0x46802020),
    0x48:(0xC42080A0,0xC42880A0),0x50:(0xC42280A4,0xC42A80A4),
    0x58:(0x468042A0,0x468030A0),0x5C:(0x46003002,0x46080002),0x68:(0x46025082,0x460A1082)}


def proposed_guards(before):
    if any(r['function']==FUNCTION for r in csv.DictReader(io.StringIO(before.decode()))):
        raise ValueError('Unexpected existing packet-visibility guards')
    if not before.endswith(b'\n'):
        raise ValueError('Packet-visibility guard predecessor lacks newline')
    suffix=io.StringIO(newline='')
    writer=csv.writer(suffix,lineterminator='\n')
    for at,(expected,replacement) in GUARDS.items():
        binding=RELOCATIONS.get(at)
        relocation=':'.join(binding[0]) if binding else '-'
        mask=0xFFFF0000 if binding else 0xFFFFFFFF
        writer.writerow((OWNER,FUNCTION,'0x%X'%at,'0x%08X'%(expected&mask),'0x%08X'%(replacement&mask),
            relocation,relocation,'Normalize closed packet-visibility initial FP scratch roles','','','false'))
    return before+suffix.getvalue().encode()


def initial_dag(words):
    """Keep exact operand order, memory reads and all non-scratch live outputs."""
    g={i:('gpr',i) for i in range(32)}
    f={i:('fpr',i) for i in range(32)}
    reads=[]
    for word in words[0x38//4:0x6C//4]:
        op,rs,rt,rd,dest,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        offset=(word&65535)-65536 if word&32768 else word&65535
        if op==15:
            g[rt]=(word&65535)<<16
        elif op in (35,49):
            address=(g[rs]+offset)&0xFFFFFFFF if isinstance(g[rs],int) else (g[rs],offset)
            reads.append((op,address))
            (g if op==35 else f)[rt]=('load32',address)
        elif op==17 and rs==4:
            f[rd]=('bits',g[rt])
        elif op==17 and rs==20 and fn==32:
            f[dest]=('cvt.s.w',f[rd])
        elif op==17 and rs==16 and fn==2:
            f[dest]=('mul.s',f[rd],f[rt])
        else:
            raise ValueError('Unknown packet-visibility initial operation')
    return g,{r:v for r,v in f.items() if r not in (6,8,10)},reads


def fp_roles(word):
    op,rs,rt,rd,dest,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
    if op in (49,53):
        return set(),{rt,rt+1} if op==53 else {rt}
    if op in (57,61):
        return ({rt,rt+1} if op==61 else {rt}),set()
    if op!=17 or rs==8:
        return set(),set()
    if rs==0:
        return {rd},set()
    if rs==4:
        return set(),{rd}
    if rs==20 and fn==32:
        return {rd},{dest}
    if rs==16 and fn in (0,1,2,3,60,62):
        return {rd,rt},set() if fn in (60,62) else {dest}
    raise ValueError('Unknown packet-visibility downstream FP role')


def closed_scratch(words):
    """Every later CFG path must define an old scratch value before reading it."""
    todo=[(0x6C,frozenset((6,8,10)))]
    seen=set()
    def step(at,pending):
        reads,writes=fp_roles(words[at//4])
        if reads&pending:
            raise ValueError('Packet-visibility old scratch value remains live')
        return frozenset(pending-writes)
    while todo:
        at,pending=todo.pop()
        if (at,pending) in seen:
            continue
        seen.add((at,pending))
        if not 0x6C<=at<516:
            raise ValueError('Packet-visibility CFG escaped its function')
        word=words[at//4]
        op,rs,rt=word>>26,word>>21&31,word>>16&31
        pending=step(at,pending)
        if word==0x03E00008:
            step(at+4,pending)
            continue
        if op in (1,4,20) or op==17 and rs==8:
            offset=(word&65535)-65536 if word&32768 else word&65535
            todo.append((at+4+offset*4,step(at+4,pending)))
            if not (op==4 and rs==rt==0):
                likely=op==20 or op in (1,17) and bool(rt&2)
                todo.append((at+8,pending if likely else step(at+4,pending)))
        elif op in (1,2,3,5,6,7,21,22,23) or op==0 and word&63 in (8,9):
            raise ValueError('Unknown packet-visibility downstream control flow')
        else:
            todo.append((at+4,pending))
    return len(seen)


def checked_object(obj):
    text,funcs,rel=parse_object(obj)
    f=funcs[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=516 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown packet-visibility physical words, bindings or pools')
    return raw,bindings


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    truth=list(struct.unpack_from('>129I',(out/'before-retail_rom').read_bytes(),ROM))
    if (row['words'],row['frame'],row['differences'],row['diagnostics'])!=(129,24,7,''):
        raise ValueError('Unknown packet-visibility compiler shape')
    if {i*4:(a,b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b}!=GUARDS:
        raise ValueError('Unknown packet-visibility normalization sites')
    if initial_dag(words)!=initial_dag(truth):
        raise ValueError('Packet-visibility initial expression or memory order changed')
    paths=closed_scratch(words)
    closed_scratch(truth)
    guards=out/'proposed-guards.csv'
    guards.write_bytes(proposed_guards((out/'before-guards').read_bytes()))
    padded=out/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj,root/PATHS['packet_original'],filename=OWNER,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),str(padded)],check=True,capture_output=True)
    data,fs=build.link_owner(root,out,padded.with_suffix('.o'),OWNER)
    f=fs[FUNCTION]
    if data[f['value']:f['value']+516]!=(out/'before-retail_rom').read_bytes()[ROM:ROM+516]:
        raise ValueError('Packet-visibility normalized linked body is not exact')
    row=dict(row,guards=7,linked_differences=0,closed_CFG_states=paths)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded.with_suffix('.o'),words,row


def slot_expected_image(before,rom):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:
        raise ValueError('Unknown packet-visibility predecessor ELF')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,28):
        raise ValueError('Unknown packet-visibility predecessor extent')
    result=bytearray(before)
    at=elf_slot_offset(before,ENTRY,516)
    result[at:at+516]=rom[ROM:ROM+516]
    struct.pack_into('>I',result,row[0]+8,516)
    return bytes(result)


def expected_inputs(root,out):
    return dict(elf=serialize_symbols(slot_expected_image((out/'before-elf').read_bytes(),(out/'before-retail_rom').read_bytes())),
        packet_owner=recovered_owner((out/'before-packet_owner').read_text()).encode(),
        guards=proposed_guards((out/'before-guards').read_bytes()))


def serialize_symbols(initial):
    from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols, SYMBOL
    if hashlib.sha256(initial).hexdigest()!='dbdd63f0ade4c09b9b7f790f4e52d762f48564b84ad37706dd4a8c477c63db99':
        raise ValueError('Unknown packet-visibility structural prediction')
    swaps=(('D_800D2C80','func_151A8584'),('D_800D2C7C','.L1514EAE8_game_data'),
        ('D_80099444','D_800A3C94'),('D_800994A4','D_800A3CF4'),('D_800D23A4','D_800899A4'),
        ('D_800D2C74','D_8009DD3C'),('D_800D2C70','D_8008AC70'))
    definitions={name:(int(name[2:],16),0,16,0,65521) for pair in swaps for name in pair if name.startswith('D_')}
    definitions.update(func_151A8584=(0x151A8584,80,18,0,5),**{
        '.L1514EAE8_game_data':(0x1514EAE8,0,16,0,5)})
    for name in ('D_800A3C94','D_800A3CF4','D_8008AC70'):
        definitions[name]=(*definitions[name][:-1],6)
    rows={name:(at,fields,string) for at,name,fields,string in symbol_rows(initial) if name in definitions}
    result=bytearray(initial)
    for names in swaps:
        at0,fields,first=rows[names[0]]
        cursor,base=first,first-fields[0]
        for i,name in enumerate(names):
            at,fields,string=rows[name]
            encoded=name.encode()+b'\0'
            if at!=at0+i*SYMBOL.size or string!=cursor or fields[1:]!=definitions[name] or initial[string:string+len(encoded)]!=encoded:
                raise ValueError('Changed packet-visibility metadata swap')
            cursor+=len(encoded)
        result[first:cursor]=b''.join(name.encode()+b'\0' for name in reversed(names))
        cursor=first
        for i,name in enumerate(reversed(names)):
            SYMBOL.pack_into(result,at0+i*SYMBOL.size,cursor-base,*definitions[name])
            cursor+=len(name)+1
    if canonical_symbols(result)!=canonical_symbols(initial) or sum(a!=b for a,b in zip(result,initial))!=157:
        raise ValueError('Changed packet-visibility serialization accounting')
    return bytes(result)


def prelink_prediction(root,out):
    freeze(root,out)
    structural=slot_expected_image((out/'before-elf').read_bytes(),(out/'before-retail_rom').read_bytes())
    rejected=out/'slot-only-rejected.elf'
    if not rejected.exists():
        rejected.write_bytes(structural)
    if rejected.read_bytes()!=structural:
        raise ValueError('Changed rejected packet-visibility slot-only prediction')
    def adapter(root,out):
        obj,padded,words,row=qualify(root,out)
        return obj,padded,words,None,row
    core=previous.previous
    with patch.multiple(core,PATHS=PATHS,BASELINE=BASELINE,qualify=adapter,
            expected_inputs=expected_inputs,slot_expected_image=slot_expected_image):
        row=core.prelink_prediction(root,out)
    row.pop('draw_guards')
    row.pop('projected_guards')
    row.update(slot_bytes=516,guards=7,metadata_serialization_bytes=157)
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
