"""Recover per-view overlay matrices, category pass and signed helper argument."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_shared_overlay_pass as previous
from tools.tests import shared_overlay_checkpoint as checkpoint
from tools.experiments import game_packet_rectangle as engine
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools import pad_c_object
from tools.experiments.game_frame_driver import warning_sites

BUILD='conker/build/game-view-overlay-pass'
OWNER,FUNCTION,ENTRY,ROM,WORDS='game_45B80','func_15019CC8',0x15019CC8,0x47178,102
PATHS=dict(previous.PATHS,view_overlay_assembly='conker/asm/nonmatchings/game_45B80/func_15019CC8.s')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    view_overlay_assembly='98f2cb5b156c5531b5962f1b2e830fefbbcf285b766d60cce9803d2522e30bdf')
build=previous.build
INITIAL='''/* Set up a view's overlay matrices and append the category/mode-5 passes. */
s32 func_15019CC8(Gfx *commands, s32 view) {
    s32 narrowedView;

    gSPViewport(commands++, D_800BE628 + ((u32)view * 0x180) + (D_800BE9C0 * 0x10) + 0x40);
    narrowedView = (s16)view;
    commands = (Gfx *)func_1501A490((s32)commands, narrowedView, 0, 0, 0, 0);
    gSPMatrix(commands++, &D_80089470, G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);
    gSPMatrix(commands++, D_800BE628 + ((u32)view * 0x180) + (D_800BE9C0 * 0x40) + 0x100,
        G_MTX_PROJECTION | G_MTX_LOAD | G_MTX_NOPUSH);
    if (D_800BE9F0 == 0x1D) {
        commands = func_1502BAD0(commands, 6, narrowedView);
    }
    commands = (Gfx *)func_151674F8(commands, 5, 0, 0);
    commands = (Gfx *)func_151674F8(commands, 5, 0, 1);
    gSPMatrix(commands++, D_800BE628 + ((u32)view * 0x180) + (D_800BE9C0 * 0x40) + 0x100,
        G_MTX_PROJECTION | G_MTX_LOAD | G_MTX_NOPUSH);
    /* The legacy pointer declaration labels the page-pointer table itself. */
    gSPMatrix(commands++, ((u32 *)&D_800DC2A0)[D_800BE9C0] + ((u32)view * 0x40),
        G_MTX_PROJECTION | G_MTX_MUL | G_MTX_NOPUSH);
    return (s32)commands;
}'''
SELECTED=INITIAL


def forms():
    yield 'initial',INITIAL
    signed=INITIAL.replace('(u32)view','view')
    yield 'signed-index',signed
    for label,base in (('signed',signed),('unsigned',INITIAL)):
        yield label+'-register',base.replace('s32 view)', 'register s32 view)')
        yield label+'-halfword',base.replace('s32 narrowedView;', 's16 narrowedView;')
        early=base.replace('    s32 narrowedView;','    s32 narrowedView = (s16)view;').replace('    narrowedView = (s16)view;\n','')
        yield label+'-early-word',early
        yield label+'-early-halfword',early.replace('s32 narrowedView =','s16 narrowedView =')


def lifetime_forms():
    opening,body=INITIAL.split('{',1)
    for hint in ('','register '):
        yield ('copy-register' if hint else 'copy-local'),opening+'{\n    '+hint+'s32 index = view;'+re.sub(r'\bview\b','index',body)
    expression='((u32)view * 0x180)'
    parts=INITIAL.split(expression)
    assert len(parts)==4
    for mask in range(1,7):
        result=parts[0]
        for i in range(3):result+=('(view * 0x180)' if mask&(1<<i) else expression)+parts[i+1]
        yield 'mixed-index-'+str(mask),result


def cursor_forms():
    yield 'unsigned-parameter',INITIAL.replace('s32 view)', 'u32 view)')
    split=INITIAL.replace('    s32 narrowedView;','    Gfx *output;\n    s32 narrowedView;')
    position=split.index('    commands = (Gfx *)func_1501A490')
    split=split[:position]+split[position:].replace('commands','output').replace('func_1501A490((s32)output,','func_1501A490((s32)commands,',1)
    yield 'split-output',split
    yield 'split-output-unsigned',split.replace('s32 view)', 'u32 view)')
    separate=INITIAL.replace('gSPMatrix(commands++,','gSPMatrix(commands,')
    separate=re.sub(r'(G_MTX_(?:MODELVIEW|PROJECTION) \| G_MTX_(?:LOAD|MUL) \| G_MTX_NOPUSH\);)',r'\1\n    commands++;',separate)
    yield 'separate-advance',separate
    yield 'integer-input',INITIAL.replace('s32 func_15019CC8(Gfx *commands, s32 view) {',
        's32 func_15019CC8(s32 commandsAddress, s32 view) {\n    Gfx *commands = (Gfx *)commandsAddress;')


def integer_forms():
    for ty in ('int','unsigned int'):
        for signed in (False,True):
            body=INITIAL.replace('s32 view)',ty+' view)')
            if signed:body=body.replace('(u32)view','view')
            yield ty.replace(' ','-')+('-signed-offset' if signed else '-unsigned-offset'),body
            yield ty.replace(' ','-')+('-signed-local' if signed else '-unsigned-local'),body.replace('s32 narrowedView;','int narrowedView;')


def carrier_forms():
    body=INITIAL.split('{',1)[1]
    copied=re.sub(r'\bview\b','fullView',body).replace('    s32 narrowedView;',
        '    s32 fullView = view;').replace('    narrowedView = (s16)fullView;','    view = (s16)view;').replace('narrowedView','view')
    yield 'narrow-parameter',INITIAL.split('{',1)[0]+'{'+copied
    yield 'narrow-parameter-early',(INITIAL.split('{',1)[0]+'{'+copied).replace(
        '    view = (s16)view;\n','').replace('    s32 fullView = view;','    s32 fullView = view;\n    view = (s16)view;')
    body=INITIAL.replace('    s32 narrowedView;','    s32 cursor;\n    s32 narrowedView;')
    position=body.index('    commands = (Gfx *)func_1501A490')
    prefix,tail=body[:position],body[position:]
    tail=tail.replace('commands = (Gfx *)func_1501A490((s32)commands,','cursor = func_1501A490((s32)commands,',1)
    tail=tail.replace('gSPMatrix(commands++,','gSPMatrix((Gfx *)cursor,')
    tail=re.sub(r'(G_MTX_(?:MODELVIEW|PROJECTION) \| G_MTX_(?:LOAD|MUL) \| G_MTX_NOPUSH\);)',r'\1\n    cursor += 8;',tail)
    tail=tail.replace('commands = func_1502BAD0(commands,','cursor = (s32)func_1502BAD0((Gfx *)cursor,')
    tail=tail.replace('commands = (Gfx *)func_151674F8(commands,','cursor = (s32)func_151674F8((void *)cursor,')
    tail=tail.replace('return (s32)commands;','return cursor;')
    yield 'word-cursor',prefix+tail


def expression_forms():
    direct=INITIAL.replace('    s32 narrowedView;\n','').replace('    narrowedView = (s16)view;\n','').replace('narrowedView','(s16)view')
    yield 'direct-narrow',direct
    yield 'direct-narrow-register',direct.replace('s32 view)', 'register s32 view)')
    expressions=('(((u32)view << 2) - (u32)view) << 7',
        '(((u32)view * 3) << 7)', '(((u32)view << 7) * 3)',
        '(((u32)view << 8) + ((u32)view << 7))')
    for i,expression in enumerate(expressions):
        yield 'scale-expression-'+str(i),direct.replace('((u32)view * 0x180)', '('+expression+')')
    parts=direct.split('((u32)view * 0x180)')
    assert len(parts)==4
    yield 'scale-mixed',parts[0]+expressions[0]+parts[1]+expressions[1]+parts[2]+expressions[2]+parts[3]


def pointer_forms():
    direct=dict(expression_forms())['direct-narrow']
    yield 'byte-base',direct.replace('D_800BE628 +','(u8 *)D_800BE628 +')
    yield 'char-base',direct.replace('D_800BE628 +','(char *)D_800BE628 +')
    yield 'matrix-base',direct.replace('D_800BE628 + ((u32)view * 0x180) + (D_800BE9C0 * 0x10) + 0x40',
        '(Vp *)((u8 *)D_800BE628 + ((u32)view * 0x180)) + D_800BE9C0 + 4').replace(
        'D_800BE628 + ((u32)view * 0x180) + (D_800BE9C0 * 0x40) + 0x100',
        '(Mtx *)((u8 *)D_800BE628 + ((u32)view * 0x180)) + D_800BE9C0 + 4')
    yield 'matrix-view',direct.replace('D_800BE628 + ((u32)view * 0x180) + (D_800BE9C0 * 0x10) + 0x40',
        '(u8 *)((Mtx *)D_800BE628 + (view * 6)) + (D_800BE9C0 * 0x10) + 0x40').replace(
        'D_800BE628 + ((u32)view * 0x180) + (D_800BE9C0 * 0x40) + 0x100',
        '(Mtx *)D_800BE628 + (view * 6) + D_800BE9C0 + 4')
    yield 'integer-return',direct.replace('s32 func_15019CC8','int func_15019CC8').replace('return (s32)commands','return (int)commands')


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    with patch.multiple(engine,PATHS=PATHS,BASELINE=BASELINE):engine.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15019CC8() {\n    return 0;\n}':raise ValueError('Unknown view-overlay predecessor')
    result=before[:lo]+body+before[hi:]
    integer='s32 commandsAddress' in body
    index_type=next((ty for ty in ('unsigned int','int','u32') if ty+' view)' in body),'s32')
    result_type='int' if 'int func_15019CC8' in body else 's32'
    prototype=result_type+' func_15019CC8('+('s32' if integer else 'Gfx *')+', '+index_type+');'
    changes=(('/* Non-matching C placeholders for asm/nonmatchings/game_45B80/func_15019CC8.s. */\n',''),
        ('s32 func_15019CC8();',prototype),
        ('func_15019CC8((s32)D_800BE9D0,','func_15019CC8((s32)D_800BE9D0,' if integer else 'func_15019CC8(D_800BE9D0,'))
    for old,new in changes:
        if result.count(old)!=1:raise ValueError('Unknown view-overlay interface: '+old)
        result=result.replace(old,new,1)
    return result


def measure(root,out,label='initial',body=SELECTED,flags=('-O2','-g3')):
    freeze(root,out)
    content=recovered_owner((out/'before-dispatch_owner').read_text(),body)
    obj,diagnostics=build.compile_owner(root,out,content,label,flags)
    text,functions,rel=parse_object(obj)
    data,placed=build.link_owner(root,out,obj,OWNER)
    f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth=struct.unpack_from('>102I',(out/'before-retail_rom').read_bytes(),ROM)
    row=dict(label=label,flags=flags,words=len(words),frame=((-words[0])&65535),
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


RAW_SHA256='ae42e63a7e607f8266c98ac290d964a0a6902e33200ca5f485cd21d1b97a2146'
RELOCATIONS={}
for name,kind,offsets in (
    ('D_800BE628','R_MIPS_HI16',(0x20,0x98,0x118)),
    ('D_800BE628','R_MIPS_LO16',(0x2C,0xA4,0x124)),
    ('D_800BE9C0','R_MIPS_HI16',(0x24,0x9C,0x11C,0x14C)),
    ('D_800BE9C0','R_MIPS_LO16',(0x28,0xA0,0x120,0x150)),
    ('D_80089470','R_MIPS_HI16',(0x78,)),('D_80089470','R_MIPS_LO16',(0x7C,)),
    ('D_800BE9F0','R_MIPS_HI16',(0xC4,)),('D_800BE9F0','R_MIPS_LO16',(0xC8,)),
    ('D_800DC2A0','R_MIPS_HI16',(0x154,)),('D_800DC2A0','R_MIPS_LO16',(0x164,)),
    ('func_1501A490','R_MIPS_26',(0x6C,)),('func_1502BAD0','R_MIPS_26',(0xDC,)),
    ('func_151674F8','R_MIPS_26',(0xF0,0x104))):
    for offset in offsets:RELOCATIONS[offset]=[(kind,name)]


def checked_object(obj):
    text,functions,relocations=parse_object(obj)
    f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in relocations.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=392 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown view-overlay object/bindings/pools')
    return list(struct.unpack('>98I',raw)),bindings


def qualify(root,out):
    import csv
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    before=(out/'before-dispatch_owner').read_text()
    baseline,diag=build.compile_owner(root,out,before,'neighbor-before')
    if warning_sites(before,diag)!=warning_sites(recovered_owner(before),row['diagnostics']):
        raise ValueError('Changed view-overlay diagnostics')
    old,new=parse_object(baseline),parse_object(obj)
    if set(old[1])!=set(new[1]):raise ValueError('Changed view-overlay owner functions')
    bindings=lambda p,f:{a-f['value']:v for a,v in p[2].items() if f['value']<=a<f['value']+f['size']}
    for name,f in old[1].items():
        if name==FUNCTION:continue
        g=new[1][name]
        if old[0][f['value']:f['value']+f['size']]!=new[0][g['value']:g['value']+g['size']] or bindings(old,f)!=bindings(new,g):
            raise ValueError('Changed view-overlay neighbor: '+name)
    guards=out/'before-guards'
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in csv.DictReader(guards.read_text().splitlines())):
        raise ValueError('View overlay must have no normalization guards')
    assembly=pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,word_patches_path=guards)
    path=out/'qualified-padded.s';path.write_text(assembly);padded=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(path)],capture_output=True,check=True)
    data,functions=build.link_owner(root,out,padded,OWNER)
    slot=data[functions[FUNCTION]['value']:functions[FUNCTION]['value']+408]
    if functions[FUNCTION]['size']!=392 or slot[:392]!=struct.pack('>98I',*words) or slot[392:]!=bytes(16):
        raise ValueError('Unexpected unguarded view-overlay padding')
    truth=(out/'before-retail_rom').read_bytes()[ROM:ROM+408]
    row=dict(row,body_words=98,slot_words=102,new_guards=0,unchanged_neighbors=15,
        slot_sha256=hashlib.sha256(slot).hexdigest(),byte_exact=False,
        real_word_differences=sum(slot[i:i+4]!=truth[i:i+4] for i in range(0,408,4)))
    if slot==truth:raise ValueError('Unexpected exact view-overlay body; update qualification')
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,words,row


def expected_inputs(root,out):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:raise ValueError('Changed view-overlay predecessor')
    slot=(out/'predicted-slot.bin').read_bytes()
    if len(slot)!=408:raise ValueError('Changed view-overlay predicted slot')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,12):raise ValueError('Unknown view-overlay predecessor extent')
    data=bytearray(before);at=elf_slot_offset(before,ENTRY,408);data[at:at+408]=slot
    struct.pack_into('>I',data,row[0]+8,392)
    return dict(elf=bytes(data),dispatch_owner=recovered_owner((out/'before-dispatch_owner').read_text()).encode())


def prelink_prediction(root,out):
    _,padded,_,row=qualify(root,out)
    capture=out/'link-inputs.json'
    live=lambda:{k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}
    if not capture.exists():
        if live()!=BASELINE:raise ValueError('Link capture must precede installation')
        for name,path in (('before-linkscript','conker/build/conker.ld'),('before-owner.o','conker/build/src/'+OWNER+'.c.o')):
            (out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed view-overlay link capture')
    link=(out/'before-linkscript').read_text();needle='build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle)!=1:raise ValueError('Unknown view-overlay link selector')
    for name,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script=out/(name+'.ld');script.write_text(link.replace(needle,str(obj.relative_to(root/'conker'))+'(.text);',1))
        result=subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+name+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,text=True)
        if result.returncode:raise ValueError(result.stderr)
    if (out/'prelink-baseline.elf').read_bytes()!=(out/'before-elf').read_bytes():
        raise ValueError('View-overlay predecessor reproduction failed')
    data,functions=build.link_owner(root,out,padded,OWNER)
    slot=data[functions[FUNCTION]['value']:functions[FUNCTION]['value']+408]
    target=out/'predicted-slot.bin'
    if not target.exists():target.write_bytes(slot)
    if target.read_bytes()!=slot:raise ValueError('Changed first view-overlay slot')
    expected=expected_inputs(root,out);predicted=(out/'prelink-prediction.elf').read_bytes()
    if predicted!=expected['elf']:raise ValueError('Prediction differs outside view-overlay slot/extent')
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial=out/'initial-prediction.json'
    if not initial.exists():
        if live()!=BASELINE:raise ValueError('Prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first view-overlay prediction')
    receipt=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip((out/'before-elf').read_bytes(),predicted)),
        metadata_exclusions=0,metadata_serialization_bytes=0,slot_bytes=408,body_bytes=392,new_guards=0)
    (out/'prelink-prediction.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--screens',action='store_true')
    p.add_argument('--lifetimes',action='store_true')
    p.add_argument('--profiles',action='store_true')
    p.add_argument('--cursors',action='store_true')
    p.add_argument('--integers',action='store_true')
    p.add_argument('--carriers',action='store_true')
    p.add_argument('--expressions',action='store_true')
    p.add_argument('--pointers',action='store_true')
    p.add_argument('--qualify',action='store_true')
    p.add_argument('--prelink',action='store_true')
    args=p.parse_args()
    if args.qualify or args.prelink:
        print(json.dumps(prelink_prediction(args.root,args.root/BUILD) if args.prelink else qualify(args.root,args.root/BUILD)[3],indent=2))
        return
    rows=[(name,body,('-O2','-g3')) for name,body in (pointer_forms() if args.pointers else expression_forms() if args.expressions else carrier_forms() if args.carriers else integer_forms() if args.integers else cursor_forms() if args.cursors else lifetime_forms() if args.lifetimes else forms() if args.screens else [('initial',SELECTED)])]
    if args.profiles:rows=[('profile-'+name,INITIAL,flags) for name,flags in (('o2',('-O2',)),('o1',('-O1',)),('g',('-g',)))]
    for name,body,flags in rows:
        row=measure(args.root,args.root/BUILD,name,body,flags)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','raw_sha256')}),flush=True)


if __name__=='__main__':main()
