"""Recover ordered neighbor preference with a closed scalar CFG normalization."""
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

from tools.experiments import game_route_vector_lifetime_fit as baseline
from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_record_color_fade_match import registers
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-route-neighbor-preference'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508907C',0x1508907C,0xB652C,91
INPUTS=dict(baseline.INPUTS)
RAW_SHA='56420d7eed4509cd27f499eed1a6cb0dfc703b0ad64ad42462fc4388d2608593'
RETAIL_SHA='60e1615185f9976a87f2fcb3b5def95ec6945b70a0bad06807aab3f180b68a89'
BINDINGS={56:[('R_MIPS_HI16','D_80087290')],60:[('R_MIPS_LO16','D_80087290')],
    80:[('R_MIPS_HI16','D_800D2350')],92:[('R_MIPS_LO16','D_800D2350')]}
AFTER={
    'conker/build/conker.us.elf':'4b8ab8ed1c080b5f392f60ddf05d2902229e3b4baa6cc880f006881538b7f9ea',
    'conker/src/game/generated_B3020.c':'f7db991ff588fad0fcfde4d10e0b234221abb82c829bea68c8ec5be954e1e17f',
    'conker/retail_word_patches.us.csv':'c40fe51b50da9855fb73bc86bb2d0562e42365dc8afb1eb2c3603018040073a9',
}
SELECTED='''/* Prefer the first matching class; retain the last type match as fallback. */
u8 func_1508907C(u8 id, u8 type, u8 excluded, u8 preferred) {
    s32 i;
    u8 first;
    u8 candidate;
    u8 next;
    u8 result;
    u8 *node;
    u8 *selectedFirst;
    u8 *selected;
    u8 *selectedNext;
    u8 *cursor;

    result = 0xFF;
    if (id >= D_80087290) {
        return 0xFF;
    }
    node = D_800D2350 + id * 0x10;
    first = node[9];
    if (first != 0xFF && first != excluded &&
        ((selectedFirst = D_800D2350 + first * 0x10, selectedFirst[0xE] == type) || type == 0xFF)) {
        result = first;
        if (selectedFirst[0xF] == preferred) {
            return first;
        }
    }
    i = 1;
    cursor = node + 1;
    do {
        candidate = cursor[9];
        if (candidate != 0xFF && candidate != excluded &&
            ((selected = D_800D2350 + candidate * 0x10, selected[0xE] == type) || type == 0xFF)) {
            result = candidate;
            if (selected[0xF] == preferred) {
                return candidate;
            }
        }
        next = cursor[10];
        i += 2;
        if (next != 0xFF && next != excluded &&
            ((selectedNext = D_800D2350 + next * 0x10, selectedNext[0xE] == type) || type == 0xFF)) {
            result = next;
            if (selectedNext[0xF] == preferred) {
                return next;
            }
        }
        cursor += 2;
    } while (i != 5);
    return result;
}
'''
raw_read,raw_text=Path.read_bytes,Path.read_text


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    lo,hi=baseline.model.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1508907C() {\n    return 0;\n}':raise ValueError('Unknown neighbor preference placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>91I',raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown neighbor proof relocation pair')
        kind,name=entries[0];value=anchors[name]
        if kind not in ('R_MIPS_HI16','R_MIPS_LO16'):raise ValueError('Unknown neighbor proof relocation kind')
        words[at//4]=words[at//4]&0xFFFF0000|(((value+0x8000)>>16) if kind=='R_MIPS_HI16' else value)&65535
    return words


def normalize(raw,bindings):
    if len(raw)!=364 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown neighbor preference body or bindings')
    words=list(struct.unpack('>91I',raw));result=list(words)
    mapping={24:{2:4},26:{4:2},27:{4:2,9:4},29:{9:4},30:{2:4},31:{9:4},32:{9:4},
        33:{2:9},34:{2:9},35:{11:12},37:{2:9},38:{11:12},39:{2:4},40:{2:9},41:{9:4},
        45:{9:4},46:{2:4},47:{4:2},48:{4:10},49:{4:10},50:{4:10},51:{4:10},52:{4:10},
        53:{12:2},54:{12:2},55:{11:12},57:{12:2},58:{11:12},59:{4:10},60:{12:2},61:{4:10},
        65:{4:10},66:{4:10},67:{2:4},68:{4:10},70:{4:10},71:{4:10},72:{12:11},73:{12:11},
        74:{11:12},76:{12:11},77:{11:12},79:{12:11},80:{4:10},84:{4:10},85:{2:4}}
    for i,rename in mapping.items():result[i]=registers(words[i],rename)
    if words[17]!=0x00801025 or words[24]!=0x00027900:raise ValueError('Unknown opening identity routing')
    result[17],result[20]=words[20],0
    for i,delay in ((42,0x24020001),(62,0x9124000A)):
        if words[i]>>26!=21 or words[i]&65535!=4 or words[i+1]!=delay or words[i+4]!=delay:
            raise ValueError('Unknown likely branch or duplicated delay lifetime')
        result[i]=(words[i]&0x03FF0000)|(5<<26)|3
        result[i+1]=0
    moved=dict(bindings);moved[68]=moved.pop(80)
    if sum(a!=b for a,b in zip(words,result))!=52:raise ValueError('Changed neighbor normalization extent')
    return struct.pack('>91I',*result),moved


def expression(op,a,b):
    if op=='or' and b==0:return a
    if op=='and':
        if b==0xFFFFFFFF:return a
        if isinstance(a,tuple) and a[0]=='read' and a[2]==1 and not a[3] and b==255:return a
        if isinstance(a,tuple) and a[0]=='and' and a[2]==b:return a
    if op=='add':
        terms=[];constant=0
        for v in (a,b):
            for term in v[1:] if isinstance(v,tuple) and v[0]=='add' else (v,):
                if isinstance(term,int):constant+=term
                else:terms.append(term)
        terms.sort(key=repr);constant&=0xFFFFFFFF
        if constant:terms.append(constant)
        return 0 if not terms else terms[0] if len(terms)==1 else ('add',*terms)
    if isinstance(a,int) and isinstance(b,int):
        return {'and':lambda:a&b,'or':lambda:a|b,'shl':lambda:a<<b,
            'signed-lt':lambda:int(((a^0x80000000)-0x80000000)<((b^0x80000000)-0x80000000))}[op]()&0xFFFFFFFF
    return (op,a,b)


def symbolic_paths(words):
    """Enumerate bounded CFG paths, preserving ordered reads, all stores and ABI.

    Read-after-stores terms are congruent for any ordinary byte-memory
    interpretation, including partial aliases, without needing to simplify
    their values. Only exact last-store forwarding is used. Raw caller-saved
    register values at fault boundaries are not ABI.
    """
    paths={}
    def walk(pc,regs,stores,events,conditions,steps):
        regs,stores,events=list(regs),list(stores),list(events)
        def execute(word):
            op,rs,rt,rd=word>>26,word>>21&31,word>>16&31,word>>11&31
            imm=((word&65535)^32768)-32768;fn=word&63
            address=expression('add',regs[rs],imm)
            if op==0:
                if fn==0:regs[rd]=expression('shl',regs[rt],word>>6&31)
                elif fn in (33,37,42):regs[rd]=expression({33:'add',37:'or',42:'signed-lt'}[fn],regs[rs],regs[rt])
                else:raise ValueError('Unsupported neighbor symbolic R instruction')
            elif op==9:regs[rt]=address
            elif op==12:regs[rt]=expression('and',regs[rs],word&65535)
            elif op==15:regs[rt]=(word&65535)<<16
            elif op in (33,35,36):
                size={33:2,35:4,36:1}[op]
                value=stores[-1][2] if stores and stores[-1][:2]==(address,size) else ('read',address,size,op==33,tuple(stores))
                regs[rt]=value;events.append(('read',address,size,op==33,value))
            elif op==43:
                value=regs[rt];stores.append((address,4,value));events.append(('write',address,4,value))
            else:raise ValueError('Unsupported neighbor symbolic instruction')
            regs[0]=0
        while True:
            if not 0<=pc<len(words)-1 or steps>250:raise ValueError('Unbounded or incomplete neighbor CFG')
            steps+=1;word=words[pc];op,rs,rt=word>>26,word>>21&31,word>>16&31
            if op==0 and word&63==8:
                target=regs[rs];execute(words[pc+1]);key=tuple(conditions)
                result=(regs[2],tuple(regs[i] for i in (*range(16,24),28,29,30,31)),target,tuple(events))
                if key in paths:raise ValueError('Ambiguous neighbor symbolic path')
                paths[key]=result;return
            if op in (4,5,20,21):
                a,b=regs[rs],regs[rt];likely=op>=20;equal=op in (4,20)
                known=a==b or isinstance(a,int) and isinstance(b,int)
                outcomes=(a==b,) if known else (False,True)
                condition=('eq',*sorted((a,b),key=repr))
                for eq in outcomes:
                    taken=eq==equal;saved=list(regs),list(stores),list(events)
                    if taken or not likely:execute(words[pc+1])
                    next_pc=pc+1+(((word&65535)^32768)-32768) if taken else pc+2
                    walk(next_pc,regs,stores,events,conditions if known else (*conditions,(condition,eq)),steps)
                    regs[:],stores[:],events[:]=saved
                return
            execute(word);pc+=1
    walk(0,[0,*(('input',i) for i in range(1,32))],[],[],(),0)
    return paths


def normalization_proof(raw,bindings,retail,anchors=None):
    normalized,moved=normalize(raw,bindings)
    if anchors is None and hashlib.sha256(struct.pack('>91I',*retail)).hexdigest()!=RETAIL_SHA:
        raise ValueError('Unknown independent retail neighbor slot')
    anchors=anchors or {'D_80087290':0x80087290,'D_800D2350':0x800D2350}
    if relocate(normalized,moved,anchors)!=list(retail):raise ValueError('Normalized neighbor words differ from independent retail')
    a=symbolic_paths(relocate(raw,bindings,anchors));b=symbolic_paths(retail)
    if a!=b:raise ValueError('Neighbor scalar routing/CFG/memory/ABI proof failed')
    return dict(symbolic_paths=len(a),independent_retail_words_exact=True,ordered_reads_all_stores_return_and_ABI_equal=True,
        identity_copy_removed=True,opening_HI16_moved=True,two_likely_delays_consolidated=True,
        raw_dead_register_fault_state_not_claimed=True)


def measure(root,out,label='qualified',body=SELECTED):
    values=freeze(root,out)
    obj,diagnostics=baseline.model.compile_owner(root,out,recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body),label)
    data,functions=baseline.model.link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    truth=list(struct.unpack_from('>91I',values['conker/conker.us.bin'],ROM))
    row=dict(words=len(words),frame=(-words[0])&65535,differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-91),
        diagnostics=diagnostics,raw_sha256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    row['proof']=normalization_proof(raw,bindings,truth)
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    normalize(raw,bindings);return raw,bindings


def recovered_guards(before,raw,bindings,retail):
    normalized,moved=normalize(raw,bindings);normalization_proof(raw,bindings,retail)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):raise ValueError('Preexisting neighbor preference guards')
    if not before.endswith(b'\n'):raise ValueError('Guard prefix lacks terminator')
    rows=[];old=struct.unpack('>91I',raw);new=struct.unpack('>91I',normalized)
    def rel(entries):return ';'.join(kind+':'+name for kind,name in entries) or '-'
    for i,(a,b) in enumerate(zip(old,new)):
        if a==b:continue
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=rel(bindings.get(i*4,[])),replacement_relocations=rel(moved.get(i*4,[])),
            note='Normalize proven neighbor scalar routing, opening identity and closed branch-delay lifetimes',
            insert_after='',insert_after_relocations='',omit='false'))
    output=io.StringIO(newline='');writer=csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\r\n')
    writer.writerows(rows);return before+output.getvalue().encode()


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out);raw,bindings=checked_object(obj)
    before,diagnostics=baseline.model.compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if diagnostics or row['diagnostics'] or (row['words'],row['frame'],row['differences'],row['neighbors'])!=(91,8,52,72) or \
            normalized_pools(before)!=normalized_pools(obj):raise ValueError('Changed neighbor preference owner/shape/pools')
    retail=struct.unpack_from('>91I',values['conker/conker.us.bin'],ROM)
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings,retail))
    script=out/'qualified-padded.s';script.write_text(emit_padded_assembly(obj,root/'conker/asm/B3020.s',filename=OWNER,word_patches_path=guards))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=baseline.model.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=364 or data[f['value']:f['value']+364]!=values['conker/conker.us.bin'][ROM:ROM+364]:
        raise ValueError('Padded neighbor preference differs from retail')
    return obj,padded,words,row


def predicted_image(before,rom):
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,364)
    result[at:at+364]=rom[ROM:ROM+364]
    rows=[r for r in symbol_rows(before) if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Unknown neighbor predecessor symbol extent')
    struct.pack_into('>I',result,rows[0][0]+8,364)
    return bytes(result)


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=raw_text(root/'conker/build/conker.ld');old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unknown neighbor linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();expected=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'])
    if image!=expected:raise ValueError('Neighbor prediction changes bytes outside the target slot/symbol size')
    successor={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for p,data in [*successor.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else 'after-guards' if p.endswith('.csv') else p)
        if path.exists() and raw_read(path)!=data:raise ValueError('Changed first neighbor successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in successor.items()},words=91,frame=8,guards=52,
        changed_bytes=sum(a!=b for a,b in zip(values['conker/build/conker.us.elf'],image)),other_ELF_bytes_fixed=True)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:raise ValueError('Changed exact neighbor successor')
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
    from tools.check_game_data_layout import audit_layout
    before=raw_read(out/'before-01');actual=raw_read(root/'conker/build/conker.us.elf')
    if actual!=raw_read(out/'first-predicted.elf') or actual!=predicted_image(before,raw_read(root/'conker/conker.us.bin')):
        raise ValueError('Neighbor actual ELF differs from its exact first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Neighbor changed other bodies/addresses')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    raw,bindings=checked_object(out/'qualified.o')
    retail=struct.unpack_from('>91I',raw_read(root/'conker/conker.us.bin'),ROM)
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,bindings,retail):
        raise ValueError('Neighbor guard prefix/rows changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Neighbor changed protected Game data')
    result=dict(functions=len(a),only_target_code_and_size_changed=True,all_addresses_preserved=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=52,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
