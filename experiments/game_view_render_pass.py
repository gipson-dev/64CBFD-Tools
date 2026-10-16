"""Recover the per-view ordered render provider without changing its callers."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_frame_driver as previous
from tools.tests import frame_driver_checkpoint as checkpoint
from tools.experiments import game_packet_rectangle as engine
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools import pad_c_object

BUILD='conker/build/game-view-render-pass'
OWNER,FUNCTION,ENTRY,ROM,WORDS='game_45B80','func_150195A0',0x150195A0,0x46A50,215
PATHS=dict(previous.PATHS,render_assembly='conker/asm/nonmatchings/game_45B80/func_150195A0.s')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    render_assembly='0887ff197ba5c1388a0d0855d026d5c8f7268e49d0c61a3dbe4413d4aa813717')
build=previous.build
INITIAL='''/* Append the selected view's ordered scene and overlay render passes. */
s32 func_150195A0(Gfx *commands, s16 view) {
    struct108 *state = &D_800DBFF0[view];

    if (D_800BEAC0 != 0) {
        return (s32)commands;
    }
    if (D_80084480 != 0) {
        return (s32)commands;
    }
    if (func_1517EFAC(view) != 0 || (D_800D18A0 & (1U << view)) != 0) {
        return (s32)commands;
    }
    if (D_80082FA0 > 0) {
        commands = (Gfx *)func_1510B7B4((s32)commands, view);
        commands = (Gfx *)func_1515D6D0((s32)commands, view);
        func_1510B958(view);
        gSPViewport(commands++, (view * 0x180) + D_800BE628 + (D_800BE9C0 * 0x10) + 0x40);
        commands = (Gfx *)func_1501A490((s32)commands, view, 0, 0, 0, 0);
    }
    commands = (Gfx *)func_151135C4((s32)commands, 1, view);
    if (D_800BE575 == 2) {
        commands = (Gfx *)func_151D6778((s32)commands);
    }
    commands = (Gfx *)func_151674F8(commands, 6, view, 0);
    commands = (Gfx *)func_151674F8(commands, 6, view, 1);
    commands = (Gfx *)func_15186794((s32)commands, view);
    commands = (Gfx *)func_1501A490((s32)commands, view, 0, 0, 0, 0);
    commands = func_1502BAD0(commands, 1, view);
    commands = (Gfx *)func_15035FE8((s32)commands, view);
    gSPMatrix(commands++, &D_80089470, G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);
    if (state->unk5F0 & 1) {
        commands = (Gfx *)func_15018E88(commands, view);
        commands = (Gfx *)func_151135C4((s32)commands, 0, view);
        commands = (Gfx *)func_15018F08(commands, view);
    } else {
        commands = (Gfx *)func_15018F08(commands, view);
        commands = (Gfx *)func_151135C4((s32)commands, 0, view);
        commands = (Gfx *)func_15018E88(commands, view);
    }
    commands = (Gfx *)func_15188D00((s32)commands, 0, view);
    commands = (Gfx *)func_15188D00((s32)commands, 1, view);
    commands = func_1502BAD0(commands, 2, view);
    commands = (Gfx *)func_151674F8(commands, 2, view, 0);
    return (s32)func_151674F8(commands, 2, view, 1);
}'''


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    with patch.multiple(engine,PATHS=PATHS,BASELINE=BASELINE):
        engine.freeze(root,out)


def recovered_owner(before,body=INITIAL):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150195A0() {\n    return 0;\n}':
        raise ValueError('Unknown view-render predecessor')
    result=before[:lo]+body+before[hi:]
    changes=(('/* Non-matching C placeholders for asm/nonmatchings/game_45B80/func_150195A0.s. */\n',''),
        ('s32 func_150195A0();','s32 func_150195A0(Gfx *, s16);'),
        ('func_150195A0((s32)D_800BE9D0,','func_150195A0(D_800BE9D0,'),
        ('void func_15018E88(void *arg0, s16 arg1)','s32 func_15018E88(void *arg0, s16 arg1)'),
        ('    func_15174AA4(arg0, D_800BE9F0, arg1);','    return func_15174AA4(arg0, D_800BE9F0, arg1);'))
    for old,new in changes:
        if result.count(old)!=1:raise ValueError('Unknown view-render interface: '+old)
        result=result.replace(old,new,1)
    return result


def measure(root,out,label='initial',body=INITIAL,flags=('-O2','-g3')):
    freeze(root,out)
    content=recovered_owner((out/'before-dispatch_owner').read_text(),body)
    obj,diagnostics=build.compile_owner(root,out,content,label,flags)
    text,functions,rel=parse_object(obj)
    data,placed=build.link_owner(root,out,obj,OWNER)
    f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth=struct.unpack_from('>215I',(out/'before-retail_rom').read_bytes(),ROM)
    row=dict(label=label,flags=flags,words=len(words),frame=((-words[0])&65535),
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row




SELECTED=INITIAL
RAW_SHA256='d3279403a00335487cb1c3451eca67956dcbb3028de51ce00f73ae93d7169422'
ROLE_OFFSETS=(0xE8,0xF4,0xF8,0xFC,0x100)
RELOCATIONS={
    0x34: [['R_MIPS_HI16','D_800DBFF0']],
    0x38: [['R_MIPS_LO16','D_800DBFF0']],
    0x40: [['R_MIPS_HI16','D_800BEAC0']],
    0x44: [['R_MIPS_LO16','D_800BEAC0']],
    0x64: [['R_MIPS_HI16','D_80084480']],
    0x68: [['R_MIPS_LO16','D_80084480']],
    0x7C: [['R_MIPS_26','func_1517EFAC']],
    0x88: [['R_MIPS_HI16','D_800D18A0']],
    0x8C: [['R_MIPS_LO16','D_800D18A0']],
    0xA0: [['R_MIPS_HI16','D_80082FA0']],
    0xAC: [['R_MIPS_LO16','D_80082FA0']],
    0xB8: [['R_MIPS_26','func_1510B7B4']],
    0xC4: [['R_MIPS_26','func_1515D6D0']],
    0xD0: [['R_MIPS_26','func_1510B958']],
    0xE8: [['R_MIPS_HI16','D_800BE628']],
    0xEC: [['R_MIPS_HI16','D_800BE9C0']],
    0xF0: [['R_MIPS_LO16','D_800BE9C0']],
    0xF4: [['R_MIPS_LO16','D_800BE628']],
    0x138: [['R_MIPS_26','func_1501A490']],
    0x154: [['R_MIPS_26','func_151135C4']],
    0x15C: [['R_MIPS_HI16','D_800BE575']],
    0x160: [['R_MIPS_LO16','D_800BE575']],
    0x174: [['R_MIPS_26','func_151D6778']],
    0x194: [['R_MIPS_26','func_151674F8']],
    0x1B0: [['R_MIPS_26','func_151674F8']],
    0x1BC: [['R_MIPS_26','func_15186794']],
    0x1E0: [['R_MIPS_26','func_1501A490']],
    0x1F8: [['R_MIPS_26','func_1502BAD0']],
    0x204: [['R_MIPS_26','func_15035FE8']],
    0x210: [['R_MIPS_HI16','D_80089470']],
    0x214: [['R_MIPS_LO16','D_80089470']],
    0x254: [['R_MIPS_26','func_15018E88']],
    0x26C: [['R_MIPS_26','func_151135C4']],
    0x280: [['R_MIPS_26','func_15018F08']],
    0x290: [['R_MIPS_26','func_15018F08']],
    0x2A8: [['R_MIPS_26','func_151135C4']],
    0x2BC: [['R_MIPS_26','func_15018E88']],
    0x2D8: [['R_MIPS_26','func_15188D00']],
    0x2F0: [['R_MIPS_26','func_15188D00']],
    0x308: [['R_MIPS_26','func_1502BAD0']],
    0x324: [['R_MIPS_26','func_151674F8']],
    0x340: [['R_MIPS_26','func_151674F8']],
}


def checked_object(obj):
    text,functions,relocations=parse_object(obj)
    f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:rows for a,rows in relocations.items() if f['value']<=a<f['value']+f['size']}
    wanted={offset:[tuple(v) for v in rows] for offset,rows in RELOCATIONS.items()}
    pools={n:d for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=860 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=wanted or pools:
        raise ValueError('Unknown view-render object/bindings/pools')
    return raw,bindings


def derived_guards(obj):
    raw,bindings=checked_object(obj)
    rows=[]
    for offset in ROLE_OFFSETS:
        word=struct.unpack_from('>I',raw,offset)[0]
        replacement=word
        shifts=(21,16,11) if word>>26==0 else (16,) if word>>26==15 else (21,16)
        for shift in shifts:
            register=(word>>shift)&31
            if register in (24,25):replacement^=1<<shift
        spec=';'.join(kind+':'+name for kind,name in bindings.get(offset,[])) or '-'
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%word,replacement='0x%08X'%replacement,
            expected_relocations=spec,replacement_relocations=spec,
            note='Normalize view-render viewport base and scaled-index temporary roles',
            insert_after='',insert_after_relocations='',omit='false'))
    return rows


def guarded_manifest(out,obj):
    import csv
    import io
    before=(out/'before-guards').read_bytes()
    parsed=csv.DictReader(io.StringIO(before.decode()))
    names=parsed.fieldnames
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in parsed):
        raise ValueError('View render already has guards')
    added=io.StringIO(newline='')
    writer=csv.DictWriter(added,fieldnames=names,lineterminator='\n')
    writer.writerows(derived_guards(obj))
    return before+added.getvalue().encode()


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED)
    before=(out/'before-dispatch_owner').read_text()
    baseline,diagnostics=build.compile_owner(root,out,before,'neighbor-before')
    if previous.warning_sites(before,diagnostics)!=previous.warning_sites(recovered_owner(before),row['diagnostics']):
        raise ValueError('New view-render owner diagnostics')
    old,new=parse_object(baseline),parse_object(obj)
    if set(old[1])!=set(new[1]):raise ValueError('View-render owner function set changed')
    binding=lambda parsed,f:{a-f['value']:rows for a,rows in parsed[2].items() if f['value']<=a<f['value']+f['size']}
    for name,f in old[1].items():
        if name==FUNCTION:continue
        g=new[1][name]
        if old[0][f['value']:f['value']+f['size']]!=new[0][g['value']:g['value']+g['size']] or binding(old,f)!=binding(new,g):
            raise ValueError('View-render neighbor code/bindings changed: '+name)
    guards=guarded_manifest(out,obj)
    manifest=out/'qualified-guards.csv'
    if not manifest.exists():manifest.write_bytes(guards)
    if manifest.read_bytes()!=guards:raise ValueError('Changed view-render guard fixture')
    assembly=pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,word_patches_path=manifest)
    path=out/'qualified-padded.s'
    path.write_text(assembly)
    padded=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(path)],capture_output=True,check=True)
    data,functions=build.link_owner(root,out,padded,OWNER)
    f=functions[FUNCTION]
    slot=data[f['value']:f['value']+860]
    truth=(out/'before-retail_rom').read_bytes()[ROM:ROM+860]
    row=dict(row,slot_words=f['size']//4,new_guards=5,inserted_nops=0,
        slot_sha256=hashlib.sha256(slot).hexdigest(),byte_exact=slot==truth,unchanged_neighbors=15)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    if f['size']!=860 or slot!=truth:raise ValueError('View-render guarded slot not byte exact')
    return obj,padded,words,row


def slot_expected_image(before,slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:raise ValueError('Unknown view-render predecessor ELF')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,12) or len(slot)!=860:raise ValueError('Unknown view-render extent/slot')
    if slot!=(Path(__file__).resolve().parents[2]/BUILD/'before-retail_rom').read_bytes()[ROM:ROM+860]:
        raise ValueError('Slot does not match independently frozen retail')
    data=bytearray(before)
    at=elf_slot_offset(before,ENTRY,860)
    data[at:at+860]=slot
    struct.pack_into('>I',data,row[0]+8,860)
    return bytes(data)


def expected_inputs(root,out):
    return dict(elf=slot_expected_image((out/'before-elf').read_bytes(),(out/'predicted-slot.bin').read_bytes()),
        dispatch_owner=recovered_owner((out/'before-dispatch_owner').read_text()).encode(),
        guards=(out/'qualified-guards.csv').read_bytes())


def prelink_prediction(root,out):
    _,padded,_,_=qualify(root,out)
    capture=out/'link-inputs.json'
    if not capture.exists():
        if {k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}!=BASELINE:
            raise ValueError('View-render link capture must precede installation')
        (out/'before-linkscript').write_bytes((root/'conker/build/conker.ld').read_bytes())
        (out/'before-owner.o').write_bytes((root/'conker/build/src'/(OWNER+'.c.o')).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed view-render link capture')
    link=(out/'before-linkscript').read_text()
    needle='build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle)!=1:raise ValueError('Expected one view-render owner selector')
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
    if (out/'prelink-baseline.elf').read_bytes()!=before:raise ValueError('Link inputs do not reproduce view-render predecessor')
    data,functions=build.link_owner(root,out,padded,OWNER)
    slot=data[functions[FUNCTION]['value']:functions[FUNCTION]['value']+860]
    target=out/'predicted-slot.bin'
    if not target.exists():target.write_bytes(slot)
    if target.read_bytes()!=slot:raise ValueError('Changed first view-render slot prediction')
    expected=expected_inputs(root,out)
    predicted=(out/'prelink-prediction.elf').read_bytes()
    if predicted!=expected['elf']:raise ValueError('View-render link differs from complete slot/extent prediction')
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial=out/'initial-prediction.json'
    if not initial.exists():
        if {k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}!=BASELINE:
            raise ValueError('View-render prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first view-render prediction')
    row=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip(before,predicted)),
        metadata_exclusions=0,metadata_serialization_bytes=0,slot_bytes=860,body_bytes=860,new_guards=5,inserted_nops=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--screens',action='store_true')
    p.add_argument('--qualify',action='store_true')
    p.add_argument('--prelink',action='store_true')
    args=p.parse_args()
    if args.qualify or args.prelink:
        row=prelink_prediction(args.root,args.root/BUILD) if args.prelink else qualify(args.root,args.root/BUILD)[-1]
        print(json.dumps(row,indent=2))
        return
    forms=[('initial',INITIAL)]
    if args.screens:
        expression='(view * 0x180) + D_800BE628 + (D_800BE9C0 * 0x10) + 0x40'
        forms.extend((name,INITIAL.replace(expression,new)) for name,new in (
            ('unsigned-view','((u32)view * 0x180) + D_800BE628 + (D_800BE9C0 * 0x10) + 0x40'),
            ('unsigned-base','(view * 0x180) + (u32)D_800BE628 + (D_800BE9C0 * 0x10) + 0x40'),
            ('nested-base','D_800BE628 + ((view * 0x180) + (D_800BE9C0 * 0x10) + 0x40)')))
    for name,body in forms:
        row=measure(args.root,args.root/BUILD,name,body)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','raw_sha256')}),flush=True)


if __name__=='__main__':main()
