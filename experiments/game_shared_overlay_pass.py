"""Recover the shared overlay and disabled-framebuffer capture pass."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_view_render_pass as previous
from tools.tests import view_render_pass_checkpoint as checkpoint
from tools.experiments import game_packet_rectangle as engine
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools import pad_c_object

BUILD='conker/build/game-shared-overlay-pass'
OWNER,FUNCTION,ENTRY,ROM,WORDS='game_45B80','func_150198FC',0x150198FC,0x46DAC,175
PATHS=dict(previous.PATHS,overlay_assembly='conker/asm/nonmatchings/game_45B80/func_150198FC.s')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    overlay_assembly='9c664a969529dbfa620b6e6b51b027c3dc1b44e4700d9057079c823cfc30c5c7')
build=previous.build
DECLARATIONS='''/* The capture counter is signed; the framebuffer label is indexed backward. */
extern s8 D_80082F90;
extern s32 D_8002AAEC;

'''
INITIAL='''/* Append shared overlays and capture/redraw the disabled framebuffer. */
s32 func_150198FC(Gfx *commands) {
    if (D_800BE575 == 1) {
        commands = (Gfx *)func_151D6778((s32)commands);
    }
    if (D_80082FA0 != 0) {
        D_80082FA4 = (s32)((u32)D_80082FA0 + 1U);
        gSPViewport(commands++, ((u32)D_80082FA4 * 0x180) + D_800BE628 + 0x40);
    } else {
        gSPViewport(commands++, D_800BE628 + 0x40);
    }
    commands = (Gfx *)func_1501A490((s32)commands, 0xFF, 0, 0, 0, 0);
    if (D_800BEAC0 != 0) {
        if (D_80082F90 == 0) {
            gDPSetColorImage(commands++, G_IM_FMT_RGBA, G_IM_SIZ_16b, D_800BE620, D_800BE9C4);
            gDPSetScissor(commands++, G_SC_NON_INTERLACE, 0, 0, D_800BE620, D_800BE624);
            commands = (Gfx *)func_151D5E90((s32)commands, (&D_8002AAEC)[-(s32)D_800BE9C0], 0, 1);
            commands = (Gfx *)func_1501A680((s32)commands);
            D_80082F90 = 1;
        } else if (D_80082F90 < 5) {
            D_80082F90++;
            func_151D61B0(D_800BE9C4);
        }
        commands = (Gfx *)func_151D5E90((s32)commands, D_800BE9C4, 0, 1);
    } else {
        D_80082F90 = 0;
    }
    if (func_1517EFAC(0) == 0) {
        commands = (Gfx *)func_1517E28C((s32)commands, D_800BE9F0);
        commands = (Gfx *)func_15172F70((s32)commands);
        commands = (Gfx *)func_15181EE0((s32)commands);
    }
    commands = (Gfx *)func_1517F564((s32)commands);
    if (D_800BEAC0 == 0 && D_800BEAC1 == 0) {
        commands = (Gfx *)func_1508FD38((s32)commands);
    }
    commands = (Gfx *)func_151674F8(commands, 3, 0, 0);
    commands = (Gfx *)func_151674F8(commands, 3, 0, 1);
    return func_15096934((s32)commands);
}'''
SELECTED=INITIAL


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    with patch.multiple(engine,PATHS=PATHS,BASELINE=BASELINE):engine.freeze(root,out)


def recovered_owner(before,body=SELECTED,declarations=DECLARATIONS):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150198FC() {\n    return 0;\n}':raise ValueError('Unknown shared-overlay predecessor')
    result=before[:lo]+body+before[hi:]
    integer='s32 commandsAddress' in body
    prototype='s32 func_150198FC(s32);' if integer else ('Gfx *func_150198FC(Gfx *);' if 'Gfx *func_150198FC' in body else 's32 func_150198FC(Gfx *);')
    changes=(('/* Non-matching C placeholders for asm/nonmatchings/game_45B80/func_150198FC.s. */\n',''),
        ('s32 func_150198FC();',prototype),
        ('func_150198FC((s32)D_800BE9D0)','func_150198FC((s32)D_800BE9D0)' if integer else 'func_150198FC(D_800BE9D0)'),
        ('/* Generated placeholder declarations. */',declarations+'/* Generated placeholder declarations. */'))
    for old,new in changes:
        if result.count(old)!=1:raise ValueError('Unknown shared-overlay interface: '+old)
        result=result.replace(old,new,1)
    return result


def measure(root,out,label='initial',body=SELECTED,flags=('-O2','-g3'),declarations=DECLARATIONS):
    freeze(root,out)
    content=recovered_owner((out/'before-dispatch_owner').read_text(),body,declarations)
    obj,diagnostics=build.compile_owner(root,out,content,label,flags)
    text,functions,rel=parse_object(obj)
    data,placed=build.link_owner(root,out,obj,OWNER)
    f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth=struct.unpack_from('>175I',(out/'before-retail_rom').read_bytes(),ROM)
    row=dict(label=label,flags=flags,words=len(words),frame=((-words[0])&65535),
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row



RAW_SHA256='a8165e3f7012d81e4bf2d7b78648404f59a037a26ccdd510c6e801eaf49f846f'
RELOCATIONS={
    0x10: [['R_MIPS_HI16','D_800BE575']],
    0x14: [['R_MIPS_LO16','D_800BE575']],
    0x24: [['R_MIPS_26','func_151D6778']],
    0x30: [['R_MIPS_HI16','D_80082FA0']],
    0x34: [['R_MIPS_LO16','D_80082FA0']],
    0x38: [['R_MIPS_HI16','D_80082FA4']],
    0x3C: [['R_MIPS_LO16','D_80082FA4']],
    0x60: [['R_MIPS_HI16','D_800BE628']],
    0x64: [['R_MIPS_LO16','D_800BE628']],
    0x9C: [['R_MIPS_HI16','D_800BE628']],
    0xA0: [['R_MIPS_LO16','D_800BE628']],
    0xC4: [['R_MIPS_26','func_1501A490']],
    0xCC: [['R_MIPS_HI16','D_800BEAC0']],
    0xD0: [['R_MIPS_LO16','D_800BEAC0']],
    0xD8: [['R_MIPS_HI16','D_80082F90']],
    0xE0: [['R_MIPS_HI16','D_80082F90']],
    0xE4: [['R_MIPS_LO16','D_80082F90']],
    0xEC: [['R_MIPS_HI16','D_800BE620']],
    0xF0: [['R_MIPS_HI16','D_800BE9C4']],
    0x104: [['R_MIPS_LO16','D_800BE620']],
    0x124: [['R_MIPS_LO16','D_800BE9C4']],
    0x140: [['R_MIPS_HI16','D_800BE624']],
    0x144: [['R_MIPS_LO16','D_800BE624']],
    0x15C: [['R_MIPS_HI16','D_8002AAEC']],
    0x194: [['R_MIPS_HI16','D_800BE9C0']],
    0x198: [['R_MIPS_LO16','D_800BE9C0']],
    0x1B0: [['R_MIPS_26','func_151D5E90']],
    0x1B4: [['R_MIPS_LO16','D_8002AAEC']],
    0x1B8: [['R_MIPS_26','func_1501A680']],
    0x1C4: [['R_MIPS_HI16','D_80082F90']],
    0x1D0: [['R_MIPS_LO16','D_80082F90']],
    0x1E0: [['R_MIPS_HI16','D_800BE9C4']],
    0x1E4: [['R_MIPS_26','func_151D61B0']],
    0x1E8: [['R_MIPS_LO16','D_800BE9C4']],
    0x1EC: [['R_MIPS_HI16','D_800BE9C4']],
    0x1F0: [['R_MIPS_LO16','D_800BE9C4']],
    0x1FC: [['R_MIPS_26','func_151D5E90']],
    0x20C: [['R_MIPS_LO16','D_80082F90']],
    0x210: [['R_MIPS_26','func_1517EFAC']],
    0x220: [['R_MIPS_HI16','D_800BE9F0']],
    0x224: [['R_MIPS_26','func_1517E28C']],
    0x228: [['R_MIPS_LO16','D_800BE9F0']],
    0x22C: [['R_MIPS_26','func_15172F70']],
    0x234: [['R_MIPS_26','func_15181EE0']],
    0x240: [['R_MIPS_26','func_1517F564']],
    0x248: [['R_MIPS_HI16','D_800BEAC0']],
    0x24C: [['R_MIPS_LO16','D_800BEAC0']],
    0x254: [['R_MIPS_HI16','D_800BEAC1']],
    0x260: [['R_MIPS_LO16','D_800BEAC1']],
    0x26C: [['R_MIPS_26','func_1508FD38']],
    0x284: [['R_MIPS_26','func_151674F8']],
    0x298: [['R_MIPS_26','func_151674F8']],
    0x2A0: [['R_MIPS_26','func_15096934']],
}


def checked_object(obj):
    text,functions,relocations=parse_object(obj)
    f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:rows for a,rows in relocations.items() if f['value']<=a<f['value']+f['size']}
    wanted={offset:[tuple(v) for v in rows] for offset,rows in RELOCATIONS.items()}
    pools={n:d for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=700 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=wanted or pools:
        raise ValueError('Unknown shared-overlay object/bindings/pools')
    return list(struct.unpack('>175I',raw)),bindings


def rename(word,roles):
    op=word>>26
    if op==0:shifts=(21,16,11)
    elif op==17:shifts=(16,) if word>>21&31 in (0,4) else ()
    elif op==15:shifts=(16,)
    elif op in (4,5,9,10,12,13,20,21,32,35,36,40,43):shifts=(21,16)
    elif op==3:shifts=()
    else:raise ValueError('Unknown shared-overlay role opcode')
    for shift in shifts:
        old=(word>>shift)&31
        word=(word&~(31<<shift))|(roles.get(old,old)<<shift)
    return word


def normalized_instructions(obj):
    words,bindings=checked_object(obj)
    result={i*4:[word,list(bindings.get(i*4,()))] for i,word in enumerate(words)}
    def roles(offsets,mapping):
        for offset in offsets:result[offset][0]=rename(result[offset][0],mapping)
    roles(range(0x60,0x80,4),{10:9,11:10,12:11,13:12})
    roles(range(0x8C,0xB0,4),{14:13,15:14,24:15})
    roles((0xCC,0xD0,0xDC),{25:24})
    roles((0xD8,),{9:3})
    roles((0xF4,0xF8),{2:3})
    roles((0xF0,0x124,0x130),{14:12})
    roles((0x108,0x114,0x118,0x11C,0x120),{10:25,11:9,12:10,13:11})
    roles((0x134,0x138),{15:13})
    roles((0x13C,0x148),{24:14})
    roles((0x140,0x144,0x150),{13:10})
    roles(range(0x178,0x194,4),{10:24,11:25,12:9,15:12,24:13,25:14})
    roles((0x194,0x198),{10:15})
    roles((0x1AC,),{13:25})
    roles((0x1C0,0x1D0),{14:3})
    roles((0x1D8,),{2:3,15:11})
    roles((0x254,0x260,0x264),{24:9})
    # Fold the counter's LUI/ADDIU/LB into LUI/LB; rematerialize its high
    # address in the increment arm instead of preserving a scratch pointer.
    if words[0xE4//4]!=0x25290000 or words[0xE8//4]!=0x81220000 or words[0x1DC//4]!=0xA12F0000:
        raise ValueError('Unknown shared-overlay counter address lifetime')
    result[0xE4][0]=(words[0xE4//4]&65535)|(32<<26)|(3<<21)|(3<<16)
    result[0xE8]=[rename(words[0xD8//4],{9:1}),list(bindings[0xD8])]
    result[0x1DC]=[(words[0x1DC//4]&65535)|(40<<26)|(1<<21)|(11<<16),list(bindings[0xE4])]
    # -(page << 2) and (-page) << 2 have identical 32-bit unsigned results.
    if words[0x1A4//4]!=0x000A5823 or words[0x1A8//4]!=0x000B6880:
        raise ValueError('Unknown shared-overlay backward framebuffer index')
    result[0x1A4][0]=(words[0x1A4//4]&~0x03FFF800)|(24<<16)|(25<<11)
    result[0x1A8][0]=(words[0x1A8//4]&~0x03FFF800)|(15<<16)|(24<<11)
    placement={offset:offset for offset in result}
    placement.update({0xEC:0xE8,0x110:0xEC,0xF0:0x10C,0xE8:0x1DC,0x194:0x158,
        0x1A4:0x1A4,0x1A8:0x1A0,0x1DC:0x1E0,0x1E0:0x1D8})
    placement.update({offset:offset-4 for offset in range(0xF4,0x110,4)})
    placement.update({offset:offset-4 for offset in range(0x114,0x15C,4)})
    placement.update({offset:offset-4 for offset in range(0x198,0x1A4,4)})
    placement.update({offset:offset-4 for offset in range(0x1AC,0x1DC,4)})
    if set(placement.values())!=set(result):raise ValueError('Shared-overlay schedule is not a complete permutation')
    placed={}
    for offset,(word,rel) in result.items():
        at=placement[offset]
        if word>>26 in (4,5,20,21):
            target=offset+4+(((word&65535)^0x8000)-0x8000)*4
            word=(word&~65535)|(((placement[target]-at-4)//4)&65535)
        placed[at]=(word,rel)
    return placed


def derived_guards(obj):
    words,bindings=checked_object(obj)
    normalized=normalized_instructions(obj)
    rows=[]
    spec=lambda items:';'.join(kind+':'+name for kind,name in items) or '-'
    for i,word in enumerate(words):
        offset=i*4;replacement,rel=normalized[offset];old=bindings.get(offset,[])
        if word==replacement and old==rel:continue
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%word,replacement='0x%08X'%replacement,
            expected_relocations=spec(old),replacement_relocations=spec(rel),
            note='Normalize overlay temporary roles and capture-address scheduling',
            insert_after='',insert_after_relocations='',omit='false'))
    return rows


def guarded_manifest(out,obj):
    import csv
    import io
    before=(out/'before-guards').read_bytes()
    parsed=csv.DictReader(io.StringIO(before.decode()))
    names=parsed.fieldnames
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in parsed):
        raise ValueError('Shared overlay already has guards')
    added=io.StringIO(newline='')
    writer=csv.DictWriter(added,fieldnames=names,lineterminator='\n')
    writer.writerows(derived_guards(obj))
    return before+added.getvalue().encode()


def checked_manifest(data,out,obj):
    if data!=guarded_manifest(out,obj):raise ValueError('Changed shared-overlay guard manifest')
    return data


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED)
    before=(out/'before-dispatch_owner').read_text()
    baseline,diagnostics=build.compile_owner(root,out,before,'neighbor-before')
    warning_sites=previous.previous.warning_sites
    if warning_sites(before,diagnostics)!=warning_sites(recovered_owner(before),row['diagnostics']):
        raise ValueError('New shared-overlay owner diagnostics')
    old,new=parse_object(baseline),parse_object(obj)
    if set(old[1])!=set(new[1]):raise ValueError('Shared-overlay owner function set changed')
    binding=lambda parsed,f:{a-f['value']:rows for a,rows in parsed[2].items() if f['value']<=a<f['value']+f['size']}
    for name,f in old[1].items():
        if name==FUNCTION:continue
        g=new[1][name]
        if old[0][f['value']:f['value']+f['size']]!=new[0][g['value']:g['value']+g['size']] or binding(old,f)!=binding(new,g):
            raise ValueError('Shared-overlay neighbor code/bindings changed: '+name)
    manifest=out/'normalized-guards.csv'
    guards=guarded_manifest(out,obj)
    if not manifest.exists():manifest.write_bytes(guards)
    if manifest.read_bytes()!=guards:raise ValueError('Changed shared-overlay guard fixture')
    assembly=pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,word_patches_path=manifest)
    path=out/'qualified-padded.s';path.write_text(assembly)
    padded=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(path)],capture_output=True,check=True)
    data,functions=build.link_owner(root,out,padded,OWNER)
    f=functions[FUNCTION];slot=data[f['value']:f['value']+700]
    truth=(out/'before-retail_rom').read_bytes()[ROM:ROM+700]
    row=dict(row,slot_words=f['size']//4,new_guards=len(derived_guards(obj)),
        slot_sha256=hashlib.sha256(slot).hexdigest(),byte_exact=slot==truth,unchanged_neighbors=15)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    if f['size']!=700 or slot!=truth:
        diff=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(struct.unpack('>175I',slot),struct.unpack('>175I',truth))) if a!=b]
        raise ValueError('Shared-overlay guarded slot not byte exact: '+repr(diff))
    return obj,padded,words,row



def slot_expected_image(before,slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:raise ValueError('Unknown shared-overlay predecessor ELF')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,12) or len(slot)!=700:raise ValueError('Unknown shared-overlay extent/slot')
    if slot!=(Path(__file__).resolve().parents[2]/BUILD/'before-retail_rom').read_bytes()[ROM:ROM+700]:
        raise ValueError('Slot differs from independently frozen retail')
    data=bytearray(before)
    at=elf_slot_offset(before,ENTRY,700)
    data[at:at+700]=slot
    struct.pack_into('>I',data,row[0]+8,700)
    return bytes(data)


def expected_inputs(root,out):
    return dict(elf=slot_expected_image((out/'before-elf').read_bytes(),(out/'predicted-slot.bin').read_bytes()),
        dispatch_owner=recovered_owner((out/'before-dispatch_owner').read_text()).encode(),
        guards=(out/'normalized-guards.csv').read_bytes())


def prelink_prediction(root,out):
    _,padded,_,_=qualify(root,out)
    capture=out/'link-inputs.json'
    if not capture.exists():
        if {k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}!=BASELINE:
            raise ValueError('Shared-overlay link capture must precede installation')
        (out/'before-linkscript').write_bytes((root/'conker/build/conker.ld').read_bytes())
        (out/'before-owner.o').write_bytes((root/'conker/build/src'/(OWNER+'.c.o')).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed shared-overlay link capture')
    link=(out/'before-linkscript').read_text()
    needle='build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle)!=1:raise ValueError('Expected one shared-overlay owner selector')
    for name,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script=out/(name+'.ld')
        script.write_text(link.replace(needle,str(obj.relative_to(root/'conker'))+'(.text);',1))
        result=subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+name+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,text=True)
        if result.returncode:raise ValueError(result.stderr)
    before=(out/'before-elf').read_bytes()
    if (out/'prelink-baseline.elf').read_bytes()!=before:raise ValueError('Link inputs do not reproduce shared-overlay predecessor')
    data,functions=build.link_owner(root,out,padded,OWNER)
    slot=data[functions[FUNCTION]['value']:functions[FUNCTION]['value']+700]
    target=out/'predicted-slot.bin'
    if not target.exists():target.write_bytes(slot)
    if target.read_bytes()!=slot:raise ValueError('Changed first shared-overlay slot prediction')
    expected=expected_inputs(root,out)
    predicted=(out/'prelink-prediction.elf').read_bytes()
    if predicted!=expected['elf']:raise ValueError('Shared-overlay link differs from complete slot/extent prediction')
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial=out/'initial-prediction.json'
    if not initial.exists():
        if {k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}!=BASELINE:
            raise ValueError('Shared-overlay prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first shared-overlay prediction')
    row=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip(before,predicted)),
        metadata_exclusions=0,metadata_serialization_bytes=0,slot_bytes=700,body_bytes=700,new_guards=len(derived_guards(out/'qualified.o')))
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--screens',action='store_true')
    p.add_argument('--types',action='store_true')
    p.add_argument('--structures',action='store_true')
    p.add_argument('--cursors',action='store_true')
    p.add_argument('--qualify',action='store_true')
    p.add_argument('--prelink',action='store_true')
    args=p.parse_args()
    if args.prelink:
        print(json.dumps(prelink_prediction(args.root,args.root/BUILD),indent=2))
        return
    if args.qualify:
        print(json.dumps(qualify(args.root,args.root/BUILD)[-1],indent=2))
        return
    forms=[('initial',INITIAL)]
    if args.screens:
        signed=INITIAL.replace('((u32)D_80082FA4 * 0x180)','(D_80082FA4 * 0x180)')
        pointer='(&D_8002AAEC)[-(s32)D_800BE9C0]'
        shifted='*(s32 *)((u32)&D_8002AAEC - ((u32)D_800BE9C0 << 2))'
        forms.append(('signed-viewport',signed))
        forms.append(('shifted-table',signed.replace(pointer,shifted)))
        for ty in ('s8','s32'):
            body=signed.replace(pointer,shifted).replace('    if (D_800BEAC0 != 0) {\n',
                '    if (D_800BEAC0 != 0) {\n        '+ty+' capturePhase = D_80082F90;\n',1)
            body=body.replace('if (D_80082F90 == 0)','if (capturePhase == 0)').replace(
                'if (D_80082F90 < 5)','if (capturePhase < 5)').replace('D_80082F90++;','D_80082F90 = capturePhase + 1;')
            forms.append(('phase-'+ty,body))
            forms.append(('phase-'+ty+'-shared-one',body.replace('D_80082F90 = 1;','D_80082F90 = capturePhase = 1;')))
        forms.extend((name,INITIAL.replace('D_80082F90++;',statement)) for name,statement in (
            ('explicit-increment','D_80082F90 = D_80082F90 + 1;'),
            ('narrow-increment','D_80082F90 = (s8)(D_80082F90 + 1);'),
            ('compound-increment','D_80082F90 += 1;'),('prefix-increment','++D_80082F90;')))
    forms=[(name,body,DECLARATIONS) for name,body in forms]
    if args.types:
        forms=[('cast-byte',INITIAL.replace('D_80082F90','(*(s8 *)&D_80082F90)'),DECLARATIONS.replace('extern s8 D_80082F90','extern s32 D_80082F90')),
            ('array-byte',INITIAL.replace('D_80082F90','D_80082F90[0]'),DECLARATIONS.replace('D_80082F90;','D_80082F90[];')),
            ('struct-byte',INITIAL.replace('D_80082F90','D_80082F90.phase'),DECLARATIONS.replace('extern s8 D_80082F90;','extern struct { s8 phase; } D_80082F90;')),
            ('unsigned-byte',INITIAL.replace('if (D_80082F90 == 0)','if ((s8)D_80082F90 == 0)').replace('if (D_80082F90 < 5)','if ((s8)D_80082F90 < 5)'),DECLARATIONS.replace('extern s8 D_80082F90','extern u8 D_80082F90')),
            ('signed-count-add',INITIAL.replace('(s32)((u32)D_80082FA0 + 1U)','D_80082FA0 + 1'),DECLARATIONS),
            ('signed-scaled-table',INITIAL.replace('(&D_8002AAEC)[-(s32)D_800BE9C0]',
                '*(s32 *)((s32)&D_8002AAEC + (D_800BE9C0 * -4))'),DECLARATIONS)]
    if args.structures:
        load='    if (D_800BEAC0 != 0) {\n'
        phase=INITIAL.replace(load,load+'        s32 phase = D_80082F90;\n',1)
        phase=phase.replace('if (D_80082F90 == 0)','if (phase == 0)').replace('if (D_80082F90 < 5)','if (phase < 5)').replace('D_80082F90++;','D_80082F90 = phase + 1;')
        outside=phase.replace('        s32 phase = D_80082F90;\n','').replace(
            's32 func_150198FC(Gfx *commands) {\n','s32 func_150198FC(Gfx *commands) {\n    s32 phase;\n',1).replace(load,'    phase = D_80082F90;\n'+load,1)
        zero='        if (D_80082F90 == 0) {\n'
        middle='        } else if (D_80082F90 < 5) {\n'
        end='        }\n        commands = (Gfx *)func_151D5E90((s32)commands, D_800BE9C4, 0, 1);'
        switched=INITIAL.replace(zero,'        switch (D_80082F90) {\n            case 0:\n',1).replace(
            middle,'                break;\n            default:\n                if (D_80082F90 < 5) {\n',1).replace(end,'                }\n'+end,1)
        forms=[(name,body,DECLARATIONS) for name,body in (('phase-original-table',phase),('phase-outside-gate',outside),
            ('register-phase',phase.replace('s32 phase =','register s32 phase =')),('counter-switch',switched))]
    if args.cursors:
        integer=INITIAL.replace('s32 func_150198FC(Gfx *commands) {',
            's32 func_150198FC(s32 commandsAddress) {\n    Gfx *commands = (Gfx *)commandsAddress;')
        typed=INITIAL.replace('s32 func_150198FC','Gfx *func_150198FC').replace(
            'return func_15096934((s32)commands);','return (Gfx *)func_15096934((s32)commands);')
        forms=[(name,body,DECLARATIONS) for name,body in (('integer-cursor',integer),('typed-return',typed))]
    for name,body,declarations in forms:
        row=measure(args.root,args.root/BUILD,name,body,declarations=declarations)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','raw_sha256')}),flush=True)


if __name__=='__main__':main()
