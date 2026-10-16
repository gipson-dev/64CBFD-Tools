"""Recover the full-view carrier; normalize only closed scratch-register roles."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_view_overlay_pass as previous
from tools.experiments import game_view_overlay_address_candidates as candidates
from tools.tests import view_overlay_checkpoint as checkpoint
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-view-overlay-match'
OWNER,FUNCTION,ENTRY,ROM,WORDS=previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,102
PATHS=previous.PATHS
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER)
SELECTED=dict(candidates.candidates())['address-multiply-distinct-direct']
RAW_SHA256='82f129eefc33dbf4f8df37348dd0d0404992fe2b1a0c905b9f4a49568520007a'
build=previous.build
RELOCATIONS={}
for name,kind,offsets in (
    ('D_800BE628','R_MIPS_HI16',(0x20,0x9C,0x124)),('D_800BE628','R_MIPS_LO16',(0x2C,0xA8,0x130)),
    ('D_800BE9C0','R_MIPS_HI16',(0x24,0xA0,0x128,0x160)),('D_800BE9C0','R_MIPS_LO16',(0x28,0xA4,0x12C,0x164)),
    ('D_80089470','R_MIPS_HI16',(0x7C,)),('D_80089470','R_MIPS_LO16',(0x80,)),
    ('D_800BE9F0','R_MIPS_HI16',(0xD0,)),('D_800BE9F0','R_MIPS_LO16',(0xD4,)),
    ('D_800DC2A0','R_MIPS_HI16',(0x168,)),('D_800DC2A0','R_MIPS_LO16',(0x178,)),
    ('func_1501A490','R_MIPS_26',(0x70,)),('func_1502BAD0','R_MIPS_26',(0xE8,)),
    ('func_151674F8','R_MIPS_26',(0xFC,0x110))):
    for offset in offsets:RELOCATIONS[offset]=[(kind,name)]


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    with patch.multiple(previous.engine,PATHS=PATHS,BASELINE=BASELINE):previous.engine.freeze(root,out)


def recovered_owner(before):
    lo,hi=build.function_span(before,FUNCTION)
    start=previous.SELECTED.index('s32 '+FUNCTION)
    if before[lo:hi]!=previous.SELECTED[start:]:raise ValueError('Unknown unguarded view-overlay predecessor')
    return before[:lo]+SELECTED[SELECTED.index('s32 '+FUNCTION):]+before[hi:]


def checked_object(obj):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:rows for a,rows in relocations.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in previous.sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=408 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown view-overlay match object/bindings/pools')
    return list(struct.unpack('>102I',raw)),bindings


def normalized_instructions(obj):
    words,bindings=checked_object(obj);result={i*4:(word,bindings.get(i*4,[])) for i,word in enumerate(words)}
    roles={
        0xA0:{10:9},0xA4:{10:9},0xB4:{25:8},0xB8:{10:9,11:10},
        0xBC:{25:8,9:25},0xC0:{9:25,11:10,12:11},0xC4:{12:11,13:12},0xC8:{13:12},
        0xD0:{14:13},0xD4:{14:13},0xE0:{14:13},
        0x118:{15:14},0x11C:{15:14},0x120:{15:14},0x124:{8:15},0x128:{11:9},
        0x12C:{11:9},0x130:{8:15},0x138:{25:24},0x13C:{10:24,25:24},
        0x140:{12:25,11:9},0x144:{9:8,8:15,10:24},0x148:{13:10,9:8,12:25},
        0x14C:{14:11,13:10},0x150:{14:11},0x154:{15:12},0x158:{15:12},0x15C:{15:12},
        0x160:{24:13},0x164:{24:13},0x168:{8:15},0x16C:{10:24},0x170:{25:14,24:13},
        0x174:{8:15,25:14},0x178:{8:15},0x180:{11:9,8:15,10:24},0x184:{11:9}}
    for offset,mapping in roles.items():
        result[offset]=(previous.previous.rename(words[offset//4],mapping),bindings.get(offset,[]))
    return result


def guarded_manifest(out,obj):
    before=(out/'before-guards').read_bytes();reader=csv.DictReader(io.StringIO(before.decode()))
    fields=reader.fieldnames
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):raise ValueError('View overlay already guarded')
    words,bindings=checked_object(obj);normalized=normalized_instructions(obj)
    added=io.StringIO(newline='');writer=csv.DictWriter(added,fieldnames=fields,lineterminator='\n')
    spec=lambda rows:';'.join(kind+':'+name for kind,name in rows) or '-'
    rows=[]
    for i,word in enumerate(words):
        offset=i*4;replacement,rel=normalized[offset]
        if word==replacement:continue
        if rel!=bindings.get(offset,[]):raise ValueError('View-overlay binding moved')
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%word,replacement='0x%08X'%replacement,
            expected_relocations=spec(rel),replacement_relocations=spec(rel),
            note='Normalize view-overlay closed temporary-register lifetimes',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=37:raise ValueError('Unknown view-overlay guard count')
    writer.writerows(rows);return before+added.getvalue().encode()


def checked_manifest(data,out,obj):
    if data!=guarded_manifest(out,obj):raise ValueError('Changed view-overlay match manifest')
    return data


def qualify(root,out):
    freeze(root,out);before=(out/'before-dispatch_owner').read_text();content=recovered_owner(before)
    obj,diag=build.compile_owner(root,out,content,'qualified');checked_object(obj)
    baseline,old_diag=build.compile_owner(root,out,before,'neighbor-before')
    if previous.warning_sites(before,old_diag)!=previous.warning_sites(content,diag):raise ValueError('Changed view-overlay diagnostics')
    old,new=parse_object(baseline),parse_object(obj)
    bindings=lambda p,f:{a-f['value']:v for a,v in p[2].items() if f['value']<=a<f['value']+f['size']}
    if set(old[1])!=set(new[1]):raise ValueError('Changed view-overlay owner function set')
    for name,f in old[1].items():
        if name==FUNCTION:continue
        g=new[1][name]
        if old[0][f['value']:f['value']+f['size']]!=new[0][g['value']:g['value']+g['size']] or bindings(old,f)!=bindings(new,g):
            raise ValueError('Changed view-overlay neighbor: '+name)
    manifest=out/'normalized-guards.csv';guards=guarded_manifest(out,obj)
    if not manifest.exists():manifest.write_bytes(guards)
    checked_manifest(manifest.read_bytes(),out,obj)
    path=out/'qualified-padded.s'
    path.write_text(previous.pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,word_patches_path=manifest))
    padded=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(path)],capture_output=True,check=True)
    raw_data,raw_functions=build.link_owner(root,out,obj,OWNER)
    raw=list(struct.unpack_from('>102I',raw_data,raw_functions[FUNCTION]['value']))
    data,functions=build.link_owner(root,out,padded,OWNER)
    slot=data[functions[FUNCTION]['value']:functions[FUNCTION]['value']+408]
    truth=(out/'before-retail_rom').read_bytes()[ROM:ROM+408]
    if functions[FUNCTION]['size']!=408 or slot!=truth:raise ValueError('View-overlay normalized slot is not byte exact')
    row=dict(words=102,frame=64,differences=sum(a!=b for a,b in zip(raw,struct.unpack('>102I',truth))),
        new_guards=37,raw_sha256=RAW_SHA256,slot_sha256=hashlib.sha256(slot).hexdigest(),
        byte_exact=True,unchanged_neighbors=15,diagnostics=diag)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,raw,row


def expected_inputs(root,out):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before=(out/'before-elf').read_bytes();slot=(out/'predicted-slot.bin').read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf'] or len(slot)!=408:raise ValueError('Changed view-overlay match prediction')
    if slot!=(out/'before-retail_rom').read_bytes()[ROM:ROM+408]:raise ValueError('Changed predicted retail view-overlay slot')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,392):raise ValueError('Unknown view-overlay match predecessor extent')
    data=bytearray(before);at=elf_slot_offset(before,ENTRY,408);data[at:at+408]=slot
    struct.pack_into('>I',data,row[0]+8,408)
    return dict(elf=bytes(data),dispatch_owner=recovered_owner((out/'before-dispatch_owner').read_text()).encode(),
        guards=(out/'normalized-guards.csv').read_bytes())


def prelink_prediction(root,out):
    _,padded,_,_=qualify(root,out);capture=out/'link-inputs.json'
    live=lambda:{k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}
    if not capture.exists():
        if live()!=BASELINE:raise ValueError('View-overlay link capture must precede installation')
        for name,path in (('before-linkscript','conker/build/conker.ld'),('before-owner.o','conker/build/src/'+OWNER+'.c.o')):
            (out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed view-overlay match link capture')
    link=(out/'before-linkscript').read_text();needle='build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle)!=1:raise ValueError('Unknown view-overlay match link selector')
    for name,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script=out/(name+'.ld');script.write_text(link.replace(needle,str(obj.relative_to(root/'conker'))+'(.text);',1))
        result=subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+name+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,text=True)
        if result.returncode:raise ValueError(result.stderr)
    if (out/'prelink-baseline.elf').read_bytes()!=(out/'before-elf').read_bytes():raise ValueError('View-overlay match predecessor not reproduced')
    data,functions=build.link_owner(root,out,padded,OWNER)
    slot=data[functions[FUNCTION]['value']:functions[FUNCTION]['value']+408];target=out/'predicted-slot.bin'
    if not target.exists():target.write_bytes(slot)
    if target.read_bytes()!=slot:raise ValueError('Changed first view-overlay match slot')
    expected=expected_inputs(root,out);predicted=(out/'prelink-prediction.elf').read_bytes()
    if predicted!=expected['elf']:raise ValueError('View-overlay match differs outside slot/extent')
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()};initial=out/'initial-prediction.json'
    if not initial.exists():
        if live()!=BASELINE:raise ValueError('View-overlay match prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first view-overlay match prediction')
    row=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip((out/'before-elf').read_bytes(),predicted)),
        body_bytes=408,slot_bytes=408,new_guards=37,metadata_exclusions=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n');return row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(prelink_prediction(root,root/BUILD),indent=2))
