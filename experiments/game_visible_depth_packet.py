"""Recover visibility-qualified packet depth with the retail unsigned conversion."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_projected_packet_draw as previous
from tools.tests import projected_packet_draw_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly

BUILD = 'conker/build/game-visible-depth-packet'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_C1D70', 'func_150958B0', 0x150958B0, 0xC2D60, 102
PROJECT, PROVIDER, SCALE = 0x1509563C, 0x15095B08, 0x8009DEC0
PATHS = dict(previous.PATHS,visible_depth_rodata='conker/asm/data/242970.rodata.s')
BASELINE = dict(previous.BASELINE,**checkpoint.AFTER,
    visible_depth_rodata='2a0c6a326c54b22e54221b49bb615fb51bb43df9256d293be2d2b733c45bf3b6')
build = previous.build
SCALE_DECLARATION = 'extern f32 D_8009DEC0;\n'
INITIAL = '''/* Project the packet, update visibility, then emit unsigned primitive depth. */
Gfx *func_150958B0(Gfx *output, s16 *packet, s32 *visible) {
    f32 screenX;
    f32 screenY;
    f32 depth;
    f32 divisor;

    if (func_1509563C(packet[0], packet[1], packet[2],
                      &screenX, &screenY, &depth, &divisor, 4000.0f) == 0) {
        *visible = 0;
        return output;
    }
    func_15095B08((s32)packet, screenX, screenY, divisor, 1, visible);
    if (*visible != 0) {
        gDPPipeSync(output++);
        gDPSetPrimDepth(output++, (u32)((depth / divisor) * D_8009DEC0 + D_8009DEC0), 0);
    }
    return output;
}
'''
SELECTED = INITIAL


def forms():
    yield 'initial', INITIAL
    captured = INITIAL.replace('    f32 divisor;', '    f32 divisor;\n    f32 scale;').replace(
        '    if (*visible != 0) {', '    if (*visible != 0) {\n        scale = D_8009DEC0;').replace(
        '(depth / divisor) * D_8009DEC0 + D_8009DEC0', '(depth / divisor) * scale + scale')
    yield 'captured-scale', captured
    yield 'block-scale', captured.replace('    f32 scale;\n', '').replace(
        '        scale = D_8009DEC0;', '        f32 scale = D_8009DEC0;')
    yield 'register-scale', captured.replace('    f32 scale;', '    register f32 scale;')
    yield 'scale-separate-pipe-increment', captured.replace('        gDPPipeSync(output++);',
        '        gDPPipeSync(output);\n        output++;')
    yield 'scale-explicit-pipe', captured.replace('        gDPPipeSync(output++);',
        '        output->words.w0 = 0xE7000000;\n        output->words.w1 = 0;\n        output++;')
    yield 'scale-explicit-depth', captured.replace('        gDPSetPrimDepth(output++, (u32)((depth / divisor) * scale + scale), 0);',
        '        output->words.w0 = 0xEE000000;\n        output->words.w1 = (u32)((depth / divisor) * scale + scale) << 16;\n        output++;')
    reused = captured.replace('    f32 scale;\n','').replace('        scale = D_8009DEC0;',
        '        screenX = D_8009DEC0;').replace('(depth / divisor) * scale + scale',
        '(depth / divisor) * screenX + screenX')
    yield 'reused-x-storage',reused
    yield 'union-x-scale',reused.replace('    f32 screenX;',
        '    union { f32 screenX; f32 scale; } scratch;').replace('&screenX,','&scratch.screenX,').replace(
        '(s32)packet, screenX,','(s32)packet, scratch.screenX,').replace('        screenX = D_8009DEC0;',
        '        scratch.scale = D_8009DEC0;').replace('(depth / divisor) * screenX + screenX',
        '(depth / divisor) * scratch.scale + scratch.scale')
    shared = captured.replace('    f32 scale;', '    f32 scale;\n    Gfx *command;').replace(
        '        gDPPipeSync(output++);\n        gDPSetPrimDepth(output++, (u32)((depth / divisor) * scale + scale), 0);',
        '        command = output++;\n        command->words.w0 = 0xE7000000;\n        command->words.w1 = 0;\n'
        '        command = output++;\n        command->words.w0 = 0xEE000000;\n'
        '        command->words.w1 = (u32)((depth / divisor) * scale + scale) << 16;')
    yield 'shared-command-scale', shared
    yield 'register-command', shared.replace('    Gfx *command;', '    register Gfx *command;')
    yield 'shared-second-increment',shared.replace('        command = output++;\n        command->words.w0 = 0xEE000000;',
        '        command = output;\n        output++;\n        command->words.w0 = 0xEE000000;')
    yield 'shared-early-return',shared.replace('    if (*visible != 0) {',
        '    if (*visible == 0) {\n        return output;\n    }\n    {')


def freeze(root,out):
    with patch.multiple(previous,PATHS=PATHS,BASELINE=BASELINE):
        previous.freeze(root,out)


def recovered_owner(before,selected=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150958B0() {\n    return 0;\n}':
        raise ValueError('Unknown visible-depth predecessor')
    marker='extern u8 D_800BE9C0;\n'
    if before.count(marker)!=1:
        raise ValueError('Unknown visible-depth declaration anchor')
    result=before[:lo]+(SELECTED if selected is None else selected).rstrip()+before[hi:]
    return result.replace(marker,marker+SCALE_DECLARATION,1)


def measure(root,out,label='selected',selected=None):
    freeze(root,out)
    obj,diag=build.compile_owner(root,out,recovered_owner((out/'before-packet_owner').read_text(),selected),label)
    raw,funcs,rel=parse_object(obj)
    f=funcs[FUNCTION]
    data,fs=build.link_owner(root,out,obj,OWNER)
    linked=fs[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(linked['size']//4),data,linked['value']))
    truth=list(struct.unpack_from('>102I',(out/'before-retail_rom').read_bytes(),ROM))
    row=dict(label=label,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),diagnostics=diag,
        raw_sha256=hashlib.sha256(raw[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


SELECTED = dict(forms())['shared-command-scale']
RAW_SHA256 = 'a4914ad4ab2c1752165bb720e937dd2ceed8b5d95a078d9d12e977f0dc993554'
RELOCATIONS = {100:[('R_MIPS_26','func_1509563C')],156:[('R_MIPS_26','func_15095B08')],
    168:[('R_MIPS_HI16','D_8009DEC0')],196:[('R_MIPS_LO16','D_8009DEC0')]}
GUARDS = {0xD4:(0x02001025,0x02001825),0xD8:(0xAC580000,0xAC780000),
    0x178:(0x00084C00,0x00085400),0x17C:(0xAC490004,0xAC6A0004)}


def proposed_guards(before):
    if any(r['function']==FUNCTION for r in csv.DictReader(io.StringIO(before.decode()))):
        raise ValueError('Unexpected existing visible-depth guards')
    if not before.endswith(b'\n'):
        raise ValueError('Visible-depth guard predecessor has no terminal newline')
    suffix=io.StringIO(newline='')
    writer=csv.writer(suffix,lineterminator='\n')
    for at,(expected,replacement) in GUARDS.items():
        writer.writerow((OWNER,FUNCTION,'0x%X'%at,'0x%08X'%expected,'0x%08X'%replacement,
            '-','-','Normalize closed visible-depth cursor and shifted-result scratch roles','','','false'))
    return before+suffix.getvalue().encode()


def closed_roles(words):
    """The two renamed scratch chains cannot interact with the conversion block."""
    if words[0x180//4]!=0x02001025:
        raise ValueError('Visible-depth return must replace the transient V0 cursor')
    touched=set()
    for word in words[0xDC//4:0x178//4]:
        op,rs,rt,rd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word&63
        if op==17:
            if rs in (0,2,4,6):
                touched.add(rt)
            elif rs!=16:
                raise ValueError('Unknown COP1 role in visible-depth conversion')
        elif op==49:
            touched.add(rs)
        elif op==0 and fn in (0,37):
            touched.update((rs,rt,rd))
        elif op in (1,4,5,9,12,13,15,20,21):
            touched.add(rs)
            if op!=1:
                touched.add(rt)
        else:
            raise ValueError('Unknown visible-depth conversion role')
    if touched&{2,3,9,10}:
        raise ValueError('Visible-depth scratch chain is not closed across conversion')
    return sorted(touched)


def checked_object(obj):
    text,funcs,rel=parse_object(obj)
    f=funcs[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=408 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown visible-depth compiler words, bindings or pools')
    return raw,bindings


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    truth=list(struct.unpack_from('>102I',(out/'before-retail_rom').read_bytes(),ROM))
    if (row['words'],row['frame'],row['differences'],row['diagnostics'])!=(102,72,4,''):
        raise ValueError('Unknown visible-depth body or frame')
    if {i*4:(a,b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b}!=GUARDS:
        raise ValueError('Unknown visible-depth normalization sites')
    roles=closed_roles(words)
    if words[0xDC//4:0x178//4]!=truth[0xDC//4:0x178//4]:
        raise ValueError('Visible-depth FP/FCSR sequence must already match')
    guards=out/'proposed-guards.csv'
    guards.write_bytes(proposed_guards((out/'before-guards').read_bytes()))
    padded=out/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj,root/PATHS['packet_original'],filename=OWNER,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),str(padded)],check=True,capture_output=True)
    data,fs=build.link_owner(root,out,padded.with_suffix('.o'),OWNER)
    f=fs[FUNCTION]
    if data[f['value']:f['value']+408]!=(out/'before-retail_rom').read_bytes()[ROM:ROM+408]:
        raise ValueError('Visible-depth linked body is not byte exact')
    if struct.unpack_from('>I',(out/'before-retail_rom').read_bytes(),0x242980)[0]!=0x467F8000:
        raise ValueError('Unknown retail visible-depth scale literal')
    row=dict(row,guards=4,linked_differences=0,closed_roles=roles,scale_bits='0x467F8000')
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded.with_suffix('.o'),words,row


def slot_expected_image(before,rom):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:
        raise ValueError('Unknown visible-depth predecessor ELF')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,12):
        raise ValueError('Unknown visible-depth predecessor extent')
    result=bytearray(before)
    at=elf_slot_offset(before,ENTRY,408)
    result[at:at+408]=rom[ROM:ROM+408]
    struct.pack_into('>I',result,row[0]+8,408)
    return bytes(result)


def expected_inputs(root,out):
    return dict(elf=serialize_symbols(slot_expected_image((out/'before-elf').read_bytes(),(out/'before-retail_rom').read_bytes())),
        packet_owner=recovered_owner((out/'before-packet_owner').read_text()).encode(),
        guards=proposed_guards((out/'before-guards').read_bytes()))


def serialize_symbols(initial):
    from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols, SYMBOL
    if hashlib.sha256(initial).hexdigest()!='65158999162d23d8fe6329d5e3d257482181df623640085d0eb74d6a2b5e5eba':
        raise ValueError('Unknown visible-depth structural prediction')
    definitions={'D_8009DEC0':(0x8009DEC0,0,16,0,65521),
        'D_80090820':(0x80090820,0,16,0,6),'D_800CC284':(0x800CC284,0,16,0,65521),
        'D_800A3D14':(0x800A3D14,0,16,0,6)}
    rows={name:(at,fields,string) for at,name,fields,string in symbol_rows(initial) if name in definitions}
    result=bytearray(initial)
    for names in (('D_8009DEC0','D_80090820'),('D_800CC284','D_800A3D14')):
        at0,fields,first=rows[names[0]]
        cursor,base=first,first-fields[0]
        for i,name in enumerate(names):
            at,fields,string=rows[name]
            encoded=name.encode()+b'\0'
            if at!=at0+i*SYMBOL.size or string!=cursor or fields[1:]!=definitions[name] or initial[string:string+len(encoded)]!=encoded:
                raise ValueError('Changed visible-depth metadata swap')
            cursor+=len(encoded)
        result[first:cursor]=b''.join(name.encode()+b'\0' for name in reversed(names))
        cursor=first
        for i,name in enumerate(reversed(names)):
            SYMBOL.pack_into(result,at0+i*SYMBOL.size,cursor-base,*definitions[name])
            cursor+=len(name)+1
    if canonical_symbols(result)!=canonical_symbols(initial) or sum(a!=b for a,b in zip(result,initial))!=32:
        raise ValueError('Changed visible-depth serialization accounting')
    return bytes(result)


def prelink_prediction(root,out):
    freeze(root,out)
    structural=slot_expected_image((out/'before-elf').read_bytes(),(out/'before-retail_rom').read_bytes())
    rejected=out/'slot-only-rejected.elf'
    if not rejected.exists():
        rejected.write_bytes(structural)
    if rejected.read_bytes()!=structural:
        raise ValueError('Changed rejected visible-depth slot-only prediction')
    def adapter(root,out):
        obj,padded,words,row=qualify(root,out)
        return obj,padded,words,None,row
    with patch.multiple(previous,PATHS=PATHS,BASELINE=BASELINE,qualify=adapter,
            expected_inputs=expected_inputs,slot_expected_image=slot_expected_image):
        row=previous.prelink_prediction(root,out)
    row.pop('draw_guards')
    row.pop('projected_guards')
    row.update(slot_bytes=408,guards=4,metadata_serialization_bytes=32)
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
    for name,body in forms() if args.screens else (('selected',SELECTED),):
        print(json.dumps(measure(args.root,args.root/BUILD,name,body)[2]),flush=True)


if __name__=='__main__':
    main()
