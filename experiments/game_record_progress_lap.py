"""Recover single-step fractional progress, lap gates, and bounded timer records."""
import argparse
from contextlib import contextmanager
import csv
import hashlib
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

BUILD='conker/build/game-record-progress-lap'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_15088A08',0x15088A08,0xB5EB8,212
SELECTOR,TABLE,EVENT,MODE,GOAL,CLAMP,COUNT,BEST,TOTAL=(
    0x150888A8,0x800D2350,0x800D2390,0x800D23A8,0x800E0BE7,0x800BE616,0x8008FD90,0x800E0C10,0x800E0C18)
INPUTS={
    'conker/src/game/generated_B3020.c':'dde8438e4b98764c530ded940cf659620f4210dbf954161d85d1476d990860f3',
    'conker/build/conker.us.elf':'52311814c017d8714aa125c789243a20fc0eade9c09cb66680f15e5116d45f77',
    'conker/retail_word_patches.us.csv':'73e3a4be767287fcef63d082bacd379919e1477372e6e74d20b25c4505a7ada1',
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
}
SELECTED='''/* Advance one neighbor boundary and update signed lap and bounded timer records. */
s32 func_15088A08(u8 *record, f32 delta) {
    extern s8 D_800D23A8;
    extern s8 D_800D2390;
    extern s8 D_800E0BE7;
    extern u8 D_800BE616;
    extern s16 D_800E0C10[];
    extern s32 D_800E0C18[];
    s32 step = 0;
    f32 fraction;
    u8 middle;
    u8 next;
    u8 *routes;
    u8 kind;
    s32 goal;
    s32 actorId;
    s32 time;
    s32 elapsed;
    s32 finish;
    s16 *best;
    s32 previousBest;

    *(f32 *)(record + 8) += delta;
    fraction = *(f32 *)(record + 8);
    if (fraction < 0.0f) {
        middle = record[0x2C];
        next = record[0x2B];
        record[0x2E] = record[0x2D];
        *(f32 *)(record + 8) = fraction + 1.0f;
        record[0x2D] = middle;
        record[0x2C] = next;
        record[0x2B] = func_150888A8(middle, next, *(s8 *)(record + 0x2F));
        step = -1;
    } else if (fraction >= 1.0f) {
        middle = record[0x2D];
        next = record[0x2E];
        *(f32 *)(record + 8) = fraction - 1.0f;
        record[0x2B] = record[0x2C];
        record[0x2C] = middle;
        record[0x2D] = next;
        record[0x2E] = func_150888A8(middle, next, *(s8 *)(record + 0x2F));
        step = 1;
        routes = D_800D2350;
        kind = routes[record[0x2C] * 0x10 + 0xF];
        if (D_800D23A8 == 0) {
            if (kind == 5) {
                D_800D2390 = 1;
                kind = routes[record[0x2C] * 0x10 + 0xF];
            }
            if (kind == 6) {
                D_800D2390 = 2;
            }
        } else {
            if (kind == 7) {
                D_800D2390 = 1;
                kind = routes[record[0x2C] * 0x10 + 0xF];
            }
            if (kind == 8) {
                D_800D2390 = 2;
                kind = routes[record[0x2C] * 0x10 + 0xF];
            }
            if (kind == 9) {
                D_800D2390 = 3;
            }
        }
    }
    if (step != 0) {
        goal = D_800E0BE7;
        *(s16 *)(record + 0x24) = *(s16 *)(record + 0x24) + step;
        actorId = *(s8 *)(record + 0x31);
        *(s8 *)(record + 0x27) = *(s16 *)(record + 0x24) / *(s8 *)(record + 0x26);
        if (D_800BE616 != 0 && goal < *(s8 *)(record + 0x27)) {
            *(s8 *)(record + 0x27) = goal + 1;
        }
        if (*(s8 *)(record + 0x28) < *(s8 *)(record + 0x27)) {
            *(s8 *)(record + 0x28) = *(s8 *)(record + 0x27);
            if (actorId < D_8008FD90 && *(s8 *)(record + 0x30) == 0) {
                time = *(s32 *)(record + 0x1C);
                if (time > 0) {
                    if (goal >= *(s8 *)(record + 0x28)) {
                        best = D_800E0C10 + actorId;
                        elapsed = (u32)time - *(u32 *)(record + 0x18);
                        if (elapsed >= 32001) {
                            elapsed = 32000;
                        }
                        previousBest = *best;
                        if (previousBest <= 0 || elapsed < previousBest) {
                            *best = elapsed;
                        }
                        *(s32 *)(record + 0x20) = elapsed;
                    }
                    if (goal == *(s8 *)(record + 0x28)) {
                        finish = *(s32 *)(record + 0x1C);
                        if (finish >= 360001) {
                            finish = 360000;
                        }
                        D_800E0C18[actorId] = finish;
                    }
                }
            }
            if (goal == *(s8 *)(record + 0x28)) {
                *(u32 *)(record + 0x18) = 0u - *(u32 *)(record + 0x1C);
            } else if (*(s8 *)(record + 0x28) < goal) {
                *(s32 *)(record + 0x18) = *(s32 *)(record + 0x1C);
            }
        }
    }
    return step;
}
'''
INITIAL=SELECTED
raw_read,raw_text=Path.read_bytes,Path.read_text


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15088A08() {\n    return 0;\n}':raise ValueError('Unknown record progress placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def forms():
    yield 'initial',INITIAL
    yield 'signed-byte-step',INITIAL.replace('s32 step = 0;','s8 step = 0;')
    yield 'word-neighbors',INITIAL.replace('    u8 middle;','    s32 middle;').replace('    u8 next;','    s32 next;')
    yield 'byte-goal-actor',INITIAL.replace('    s32 goal;','    s8 goal;').replace('    s32 actorId;','    s8 actorId;')
    events=INITIAL.replace('        routes = D_800D2350;\n        kind = routes[record[0x2C] * 0x10 + 0xF];\n',
        '        routes = D_800D2350;\n').replace('        if (D_800D23A8 == 0) {',
        '        if (D_800D23A8 == 0) {\n            kind = routes[record[0x2C] * 0x10 + 0xF];').replace(
        '        } else {\n            if (kind == 7)',
        '        } else {\n            kind = routes[record[0x2C] * 0x10 + 0xF];\n            if (kind == 7)')
    yield 'branch-local-kind',events
    for name,b in (('initial',INITIAL),('branch',events)):
        yield name+'-word-kind',b.replace('    u8 kind;','    s32 kind;')
    ordered=INITIAL.replace('    u8 middle;', '    s32 neighbor;\n    s32 middle;').replace('    u8 next;','    s32 next;').replace(
        '        middle = record[0x2C];', '        neighbor = record[0x2D];\n        middle = record[0x2C];',1).replace(
        '        record[0x2E] = record[0x2D];','        record[0x2E] = neighbor;').replace(
        '        middle = record[0x2D];','        neighbor = record[0x2C];\n        middle = record[0x2D];',1).replace(
        '        record[0x2B] = record[0x2C];','        record[0x2B] = neighbor;')
    ordered=ordered.replace('        routes = D_800D2350;\n        kind = routes[record[0x2C] * 0x10 + 0xF];\n','').replace(
        '        if (D_800D23A8 == 0) {','        if (D_800D23A8 == 0) {\n            routes = D_800D2350;\n            kind = routes[record[0x2C] * 0x10 + 0xF];').replace(
        '        } else {\n            if (kind == 7)',
        '        } else {\n            routes = D_800D2350;\n            kind = routes[record[0x2C] * 0x10 + 0xF];\n            if (kind == 7)')
    yield 'ordered',ordered
    yield 'ordered-word-kind',ordered.replace('    u8 kind;','    s32 kind;')
    for dtype in ('u8','s32'):
        separate=ordered.replace('    u8 kind;', '    '+dtype+' kind;\n    '+dtype+' otherKind;')
        lo=separate.index('        } else {\n            routes = D_800D2350;');hi=separate.index('    if (step != 0)')
        yield 'ordered-separate-'+dtype,separate[:lo]+separate[lo:hi].replace('kind','otherKind')+separate[hi:]


SELECTED=dict(forms())['ordered-word-kind']
RAW_SHA='9bfc1a381ef174907ea455041b8cbc71083d2cb46c78169e3c738e70bedd0840'
AFTER={
    'conker/build/conker.us.elf':'285d0b3d53d8d3332d6ecca37d6468d06c99ba08c48d1778bb92c6061cdd40df',
    'conker/src/game/generated_B3020.c':'b217d1beb819cb666f43d16d8e449604251cedaccb1670846542ebfc7ffcb506',
    'conker/retail_word_patches.us.csv':'2f534213effe5b5071b57336303029e8a7e7b8f12de2fc8366b51184f0b974ee',
}


def measure(root,out,label='selected',body=None):
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>212I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),diagnostics=diagnostics,frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def renamed(word,roles):
    op,rs=word>>26,(word>>21)&31
    fields=([21,16,11] if op==0 else [21,16] if op in (1,4,5,6,7,9,10,12,13,20,21,22,23,32,33,35,36,40,41,43) else
        [16] if op==15 or (op==17 and rs in (0,4)) else [21] if op in (49,57) else [])
    if not fields and op not in (3,17):raise ValueError('Unknown progress/lap rename opcode')
    for shift in fields:
        r=(word>>shift)&31;word=(word&~(31<<shift))|(roles.get(r,r)<<shift)
    return word


def normalized(words):
    if len(words)!=212:raise ValueError('Progress/lap normalization requires all 212 words')
    result=list(words)
    # Step zero is dead on each crossing arm before the short-lived snapshots.
    for i in range(17,30):result[i]=renamed(result[i],{8:14,2:15,3:24})
    for i in range(41,53):result[i]=renamed(result[i],{8:25,2:9,3:10})
    # The remainder has one closed temporary-register cycle; argument/FPR roles stay fixed.
    roles={14:11,15:12,24:13,25:14,9:15,10:24,11:25,12:9,13:10}
    for i in range(54,207):result[i]=renamed(result[i],roles)
    for i in (66,75,88,97,107):
        w=result[i]
        if w>>26 or w&63!=33:raise ValueError('Expected commutative route address addition')
        result[i]=(w&~(1023<<16))|(((w>>16)&31)<<21)|(((w>>21)&31)<<16)
    return result


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={112:[('R_MIPS_26','func_150888A8')],204:[('R_MIPS_26','func_150888A8')],
        216:[('R_MIPS_HI16','D_800D23A8')],228:[('R_MIPS_LO16','D_800D23A8')],
        232:[('R_MIPS_HI16','D_800D2350')],248:[('R_MIPS_HI16','D_800D2350')],252:[('R_MIPS_LO16','D_800D2350')],
        272:[('R_MIPS_HI16','D_800D2390')],276:[('R_MIPS_LO16','D_800D2390')],
        308:[('R_MIPS_HI16','D_800D2390')],320:[('R_MIPS_LO16','D_800D2390')],
        340:[('R_MIPS_LO16','D_800D2350')],360:[('R_MIPS_HI16','D_800D2390')],364:[('R_MIPS_LO16','D_800D2390')],
        396:[('R_MIPS_HI16','D_800D2390')],408:[('R_MIPS_LO16','D_800D2390')],
        460:[('R_MIPS_HI16','D_800E0BE7')],468:[('R_MIPS_LO16','D_800E0BE7')],
        488:[('R_MIPS_HI16','D_800BE616')],508:[('R_MIPS_LO16','D_800BE616')],
        548:[('R_MIPS_HI16','D_8008FD90')],608:[('R_MIPS_LO16','D_8008FD90')],
        652:[('R_MIPS_HI16','D_800E0C10')],656:[('R_MIPS_LO16','D_800E0C10')],
        772:[('R_MIPS_HI16','D_800E0C18')],780:[('R_MIPS_LO16','D_800E0C18')]}
    if len(raw)!=848 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown progress/lap body or 26 bindings')
    return raw,bindings


def owner_guards(raw,bindings):
    words=list(struct.unpack('>212I',raw));fixed=normalized(words);rows=[]
    for i,(a,b) in enumerate(zip(words,fixed)):
        if a==b:continue
        binding=';'.join(kind+':'+name for kind,name in bindings.get(i*4,[])) or '-'
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=binding,replacement_relocations=binding,
            note='Normalize progress lap snapshot and temporary register roles and route addresses',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=88:raise ValueError('Expected eighty-eight progress/lap guards')
    return rows


def recovered_guards(before,raw,bindings):
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):raise ValueError('Preexisting progress/lap guards')
    if not before.endswith(b'\n'):raise ValueError('Guard prefix lacks line terminator')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\r\n')
    writer.writerows(owner_guards(raw,bindings));return before+out.getvalue().encode()


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified');raw,bindings=checked_object(obj)
    truth=list(struct.unpack_from('>212I',values['conker/conker.us.bin'],ROM))
    if normalized(words)!=truth:raise ValueError('Progress/lap register normalization differs from retail')
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences']!=88 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed progress/lap diagnostics/shape/pools')
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings))
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/B3020.s',filename=OWNER,word_patches_path=guards))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=848 or data[f['value']:f['value']+848]!=values['conker/conker.us.bin'][ROM:ROM+848]:
        raise ValueError('Padded progress/lap updater differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected progress/lap linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,848)
    if image[at:at+848]!=values['conker/conker.us.bin'][ROM:ROM+848]:raise ValueError('Progress/lap prediction slot mismatch')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Progress/lap prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else 'after-guards' if p.endswith('.csv') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first progress/lap successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=212,
        raw_differences=88,guards=88,frame=24,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:raise ValueError('Changed exact progress/lap successor')
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
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Progress/lap image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Progress/lap changed other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],848,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Progress/lap changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    raw,bindings=checked_object(out/'qualified.o')
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,bindings):
        raise ValueError('Progress/lap guards differ from appended rows')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Progress/lap changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=88,old_guard_prefix_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms',action='store_true');parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    if args.forms:
        for name,body in forms():
            row=measure(root,root/BUILD,name,body)[2]
            print(json.dumps({k:row[k] for k in ('words','frame','differences','raw_sha256')}|{'name':name}),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
