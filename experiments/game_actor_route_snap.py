"""Recover actor placement after advancing past type-four route neighbors."""
import argparse
from contextlib import contextmanager
import csv
import hashlib
import itertools
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_record_heading_clamp import compile_owner
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-actor-route-snap'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_15088D58',0x15088D58,0xB6208,118
INPUTS={
    'conker/src/game/generated_B3020.c':'b217d1beb819cb666f43d16d8e449604251cedaccb1670846542ebfc7ffcb506',
    'conker/build/conker.us.elf':'285d0b3d53d8d3332d6ecca37d6468d06c99ba08c48d1778bb92c6061cdd40df',
    'conker/retail_word_patches.us.csv':'2f534213effe5b5071b57336303029e8a7e7b8f12de2fc8366b51184f0b974ee',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/B3020.s':'26ef139d5592329ed22f9287267c13fefadf7f17290bc5ef1085cbe20e80b187',
    'conker/Makefile':'840897f11d9fea8109c4e67c57e927efa6e1686de2b399fec2c9025828b92d49',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/include/structs.h':'081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/include/2.0L/PR/sched.h':'40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
    'conker/asm/nonmatchings/game_A9D90/func_1507D1D8.s':'897f8cbe8bc7f6449c0d8256ffa9677ea0f07c05f9af9b7ec08a53b9902a30f7',
    'conker/asm/76C90.s':'45f439d3beb500a34a1ac6a681b270d878681313347b6e095d0fdc6ee517d27e',
}
INITIAL='''/* Advance past type-four route links, then place and orient the actor. */
void func_15088D58(u8 *actor) {
    extern s32 func_15088F30();
    extern f32 func_150498A4(f32 *, s32, f32, f32 *);
    extern f32 func_150497E0(f32 *, s32, f32);
    extern u16 func_1505A630(f32, f32, s32);
    extern f32 func_15144BC8(f32);
    extern f32 D_8009DA04;
    f32 slopeX;
    f32 slopeZ;
    f32 x[4];
    f32 y[4];
    f32 z[4];
    s32 index;
    u8 *record;
    u8 *routes;
    u8 *neighbors;
    u8 *candidate;
    s32 kind;
    s32 i;
    s32 neighbor;
    s32 rotation;
    f32 heading;

    index = func_1508855C((s32)actor);
    if (index >= 0) {
        record = D_800872A0 + index * 0x84;
        *(f32 *)(record + 0) = 0.5f;
        *(f32 *)(record + 4) = 0.5f;
        *(f32 *)(record + 8) = 0.5f;
        do {
            routes = D_800D2350;
            kind = 0;
            neighbors = routes + record[0x2C] * 0x10;
            for (i = 0; i < 5; i++) {
                neighbor = neighbors[i + 9];
                if (neighbor != 0xFF) {
                    candidate = routes + neighbor * 0x10;
                    if (candidate[0xE] == 4) {
                        kind = candidate[0xF];
                    }
                }
            }
            if (kind != 0) {
                func_15088A08(record, 1.0f);
            }
        } while (kind != 0);
        *(f32 *)(record + 8) = 0.0f;
        func_15088F30(record, x, y, z);
        *(f32 *)(actor + 0x14) = func_150498A4(x, 0, *(f32 *)(record + 8), &slopeX);
        *(f32 *)(actor + 0x18) = func_150497E0(y, 0, *(f32 *)(record + 8));
        *(f32 *)(actor + 0x1C) = func_150498A4(z, 0, *(f32 *)(record + 8), &slopeZ);
        heading = func_15144BC8((func_1505A630(*(f32 *)(record + 0x10),
            *(f32 *)(record + 0xC), 0) + 0x8000) * 0.0054931640625f);
        *(f32 *)(actor + 0x40) = heading;
        rotation = (s32)(heading * D_8009DA04) - 0x4000;
        *(s16 *)(actor + 0x7A) = rotation;
        *(s16 *)(actor + 0x78) = rotation;
        *(s16 *)(actor + 0x76) = rotation;
    }
}
'''
SELECTED=INITIAL
raw_read,raw_text=Path.read_bytes,Path.read_text


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15088D58() {\n    return 0;\n}':raise ValueError('Unknown actor route-snap placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def forms():
    yield 'initial',INITIAL
    yield 'cursor',INITIAL.replace('neighbors[i + 9]','neighbors[9]').replace('for (i = 0; i < 5; i++)','for (i = 0; i < 5; i++, neighbors++)')
    yield 'do-cursor',INITIAL.replace('            for (i = 0; i < 5; i++) {','            i = 0;\n            do {').replace(
        'neighbors[i + 9]','neighbors[9]').replace('            if (kind != 0) {','            if (kind != 0) {',1).replace(
        '            }\n            if (kind != 0)', '                i++;\n                neighbors++;\n            } while (i != 5);\n            if (kind != 0)')
    cursor=INITIAL.replace('neighbors[i + 9]','neighbors[9]').replace('for (i = 0; i < 5; i++)','for (i = 0; i < 5; i++, neighbors++)')
    for name,body in (('indexed',INITIAL),('cursor',cursor)):
        for label,form in (
                ('direct-heading',body.replace('    f32 heading;\n','').replace('        heading = func_',
                    '        *(f32 *)(actor + 0x40) = func_').replace('        *(f32 *)(actor + 0x40) = heading;\n','').replace(
                    '(heading * D_8009DA04)','(*(f32 *)(actor + 0x40) * D_8009DA04)')),
                ('shared-index',body.replace('    s32 rotation;\n','').replace('rotation','index')),
                ('inline-candidate',body.replace('    u8 *candidate;\n','').replace('                    candidate = routes + neighbor * 0x10;\n','').replace(
                    'candidate[0xE]','routes[neighbor * 0x10 + 0xE]').replace('candidate[0xF]','routes[neighbor * 0x10 + 0xF]')),
                ('shared-cursor',body.replace('    u8 *neighbors;\n','').replace('neighbors','candidate'))):
            yield name+'-'+label,form
    transforms=(
        lambda b:b.replace('    f32 heading;\n','').replace('        heading = func_',
            '        *(f32 *)(actor + 0x40) = func_').replace('        *(f32 *)(actor + 0x40) = heading;\n','').replace(
            '(heading * D_8009DA04)','(*(f32 *)(actor + 0x40) * D_8009DA04)'),
        lambda b:b.replace('    s32 rotation;\n','').replace('rotation','index'),
        lambda b:b.replace('    u8 *candidate;\n','').replace('                    candidate = routes + neighbor * 0x10;\n','').replace(
            'candidate[0xE]','routes[neighbor * 0x10 + 0xE]').replace('candidate[0xF]','routes[neighbor * 0x10 + 0xF]'))
    for flags in itertools.product((0,1),repeat=3):
        if sum(flags)<2:continue
        body=INITIAL
        for flag,transform in zip(flags,transforms):
            if flag:body=transform(body)
        yield 'compact-'+''.join(map(str,flags)),body
    for label,body in (('initial',INITIAL),('inline',transforms[2](INITIAL)),('cursor',cursor)):
        yield 'word-return-'+label,body.replace('void func_15088D58','s32 func_15088D58').replace(
            '        *(s16 *)(actor + 0x76) = rotation;','        *(s16 *)(actor + 0x76) = rotation;\n        return rotation;').replace(
            '    }\n}\n','    }\n    return index;\n}\n')
        yield 'short-rotation-'+label,body.replace('    s32 rotation;','    s16 rotation;')
    compact=transforms[2](INITIAL)
    for names in (('rotation',),('heading',),('rotation','heading'),('index','rotation'),('index','heading'),('index','rotation','heading')):
        declarations={'rotation':'    s32 rotation;\n','heading':'    f32 heading;\n','index':'    s32 index;\n'}
        body=compact
        for name in names:body=body.replace(declarations[name],'')
        body=body.replace('    f32 slopeX;',''.join(declarations[n] for n in names)+'    f32 slopeX;')
        yield 'early-'+ '-'.join(names),body


def measure(root,out,label='selected',body=None):
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>118I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),diagnostics=diagnostics,frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


SELECTED=dict(forms())['early-rotation-heading']
RAW_SHA='e5095217500b82349000ff9e2aa2ab853d8e954f9d26471ec8f29c26a0f88fde'
AFTER={
    'conker/build/conker.us.elf':'a5c5541dc8f6863ebefac2896237ce0bc39a88e3893711c35cd0393fd851ecd7',
    'conker/src/game/generated_B3020.c':'ce0cf9b5504e5b41b267c09d69c3bdc9ed2f24533ed7de0dd68935bd678f467f',
    'conker/retail_word_patches.us.csv':'eb4dc7f42da17c278c908b8e5ab721c4b420edd2210b4a691c343b8aa0fcfd42',
}


def normalized(words):
    if len(words)!=118:raise ValueError('Actor route snap requires all 118 words')
    result=list(words)
    w=result[40]
    if w>>26!=4:raise ValueError('Expected symmetric sentinel equality branch')
    result[40]=(w&~(1023<<16))|(((w>>16)&31)<<21)|(((w>>21)&31)<<16)
    if (result[101],result[103])!=(0x44022000,0x2442C000):raise ValueError('Unknown final rotation temporary')
    result[101]=0x440D2000
    result[103]=0x25A2C000
    return result


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={44:[('R_MIPS_26','func_1508855C')],60:[('R_MIPS_HI16','D_800872A0')],68:[('R_MIPS_LO16','D_800872A0')],
        92:[('R_MIPS_HI16','D_800D2350')],100:[('R_MIPS_LO16','D_800D2350')],208:[('R_MIPS_26','func_15088A08')],
        256:[('R_MIPS_26','func_15088F30')],276:[('R_MIPS_26','func_150498A4')],296:[('R_MIPS_26','func_150497E0')],
        320:[('R_MIPS_26','func_150498A4')],340:[('R_MIPS_26','func_1505A630')],376:[('R_MIPS_26','func_15144BC8')],
        388:[('R_MIPS_HI16','D_8009DA04')],392:[('R_MIPS_LO16','D_8009DA04')]}
    if len(raw)!=472 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown actor route-snap body or fourteen bindings')
    return raw,bindings


def owner_guards(raw,bindings):
    words=list(struct.unpack('>118I',raw));fixed=normalized(words);rows=[]
    for i,(a,b) in enumerate(zip(words,fixed)):
        if a==b:continue
        if bindings.get(i*4):raise ValueError('Unexpected bound rotation/sentinel word')
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',
            note='Normalize actor route sentinel equality and final rotation temporary',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=3:raise ValueError('Expected three actor route-snap guards')
    return rows


def recovered_guards(before,raw,bindings):
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):raise ValueError('Preexisting actor route-snap guards')
    if not before.endswith(b'\n'):raise ValueError('Guard prefix lacks line terminator')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\r\n')
    writer.writerows(owner_guards(raw,bindings));return before+out.getvalue().encode()


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified');raw,bindings=checked_object(obj)
    truth=list(struct.unpack_from('>118I',values['conker/conker.us.bin'],ROM))
    if normalized(words)!=truth:raise ValueError('Actor route normalization differs from retail')
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences']!=3 or row['frame']!=168 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed actor route diagnostics/shape/pools')
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings))
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/B3020.s',filename=OWNER,word_patches_path=guards))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=472 or data[f['value']:f['value']+472]!=values['conker/conker.us.bin'][ROM:ROM+472]:
        raise ValueError('Padded actor route snap differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected actor route-snap linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,472)
    if image[at:at+472]!=values['conker/conker.us.bin'][ROM:ROM+472]:raise ValueError('Actor route prediction slot mismatch')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor route prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else 'after-guards' if p.endswith('.csv') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first actor route successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=118,
        raw_differences=3,guards=3,frame=168,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:raise ValueError('Changed exact actor route successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(checkpoint,INPUTS=INPUTS,AFTER=AFTER,expected_inputs=expected_inputs):yield


def verify(root,out,installed=False):
    with checkpoint_context():return checkpoint.verify(root,out,installed)


@contextmanager
def historical_view(root,out):
    with checkpoint_context(),checkpoint.historical_view(root,out):yield


def audit(root,out):
    verify(root,out,True)
    from tools.match_progress import load_elf_functions
    from tools.tests.test_game_one_shot_timer_match import canonical_symbols,symbol_rows
    from tools.check_game_data_layout import audit_layout
    before=raw_read(out/'before-01');actual=raw_read(root/'conker/build/conker.us.elf')
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Actor route image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor route changed other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],472,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Actor route changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    raw,bindings=checked_object(out/'qualified.o')
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,bindings):
        raise ValueError('Actor route guards differ from appended rows')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor route changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=3,old_guard_prefix_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms',action='store_true');parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    if args.forms:
        for name,body in forms():
            row=measure(root,root/BUILD,name,body)[2]
            print(json.dumps({k:row[k] for k in ('words','frame','differences','raw_sha256','diagnostics')}|{'name':name}),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
