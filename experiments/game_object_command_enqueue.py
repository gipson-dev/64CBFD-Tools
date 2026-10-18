"""Qualify the object's ordered twenty-entry command-queue append."""
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

from tools.experiments import game_route_projection_setup as parent
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.experiments import game_route_neighbor_preference as proof
from tools.experiments.game_record_color_fade_match import registers

BUILD='conker/build/game-object-command-enqueue-match'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_15AA10','func_1512D560',0x1512D560,0x15AA10,41
INPUTS=dict(parent.INPUTS,**{
    'conker/src/game/generated_15AA10.c':'07e3e099446cf291e07faad4ceeb54fc63d8052d4056b8e637216bee5b6fef0e',
})
INITIAL='''/* Append an object command and payload; wrap only when the cursor reaches 20. */
void func_1512D560(u8 *object, s32 command, void *payload) {
    u32 stride = 0xB0;
    u8 *queue;

    queue = D_800DC2B0 + object[0x23D] * stride;
    *(s32 *)(queue + *(u32 *)(queue + 0xAC) * 8) = command;
    queue = D_800DC2B0 + object[0x23D] * stride;
    *(void **)(queue + *(u32 *)(queue + 0xAC) * 8 + 4) = payload;
    queue = D_800DC2B0 + object[0x23D] * stride;
    *(u32 *)(queue + 0xAC) += 1;
    queue = D_800DC2B0 + object[0x23D] * stride;
    if (*(u32 *)(queue + 0xAC) == 20) {
        *(u32 *)(queue + 0xAC) = 0;
    }
}
'''
SELECTED=INITIAL
RAW_SHA='ccab39cd1f02cba8c92321870c51d236e02df4408a89db98500eef8e7d4d85e0'
BINDINGS={0:[('R_MIPS_HI16','D_800DC2B0')],4:[('R_MIPS_LO16','D_800DC2B0')]}
AFTER={
    'conker/build/conker.us.elf':'6157cecd5d2927c718121fffe1e6aae986b0cc3b65b9ed29bd2d1aa03a375265',
    'conker/src/game/generated_15AA10.c':'31ed15c56622255fc358fdcedf654450f8358ceed976a793d8939eb39324f458',
    'conker/retail_word_patches.us.csv':'d6a8f7c3b993d0449c712b15e083077017266394458b483d22e091f0c942e5fa',
}
raw_read,raw_text=Path.read_bytes,Path.read_text


def forms():
    yield 'initial',INITIAL
    yield 'signed-counter',INITIAL.replace('*(u32 *)','*(s32 *)')
    body=INITIAL.replace('    u32 stride = 0xB0;','    u8 **queueSource = &D_800DC2B0;\n    u32 stride = 0xB0;')
    yield 'table-source',body.replace('queue = D_800DC2B0','queue = *queueSource')
    yield 'index-first',INITIAL.replace('D_800DC2B0 + object[0x23D] * stride','object[0x23D] * stride + D_800DC2B0')
    yield 'integer-address',INITIAL.replace('D_800DC2B0 + object[0x23D] * stride',
        '(u8 *)((u32)D_800DC2B0 + object[0x23D] * stride)')


def freeze(root,out):
    with patch.object(parent.checkpoint,'INPUTS',INPUTS):return parent.checkpoint.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1512D560() {\n    return 0;\n}':raise ValueError('Unknown command-enqueue placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,name,body):
    inputs=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(inputs['conker/src/game/'+OWNER+'.c'].decode(),body),name)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    truth=struct.unpack_from('>41I',inputs['conker/conker.us.bin'],ROM)
    row=dict(name=name,words=len(words),differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-41),
        raw_sha256=hashlib.sha256(raw).hexdigest(),diagnostics=diagnostics,
        bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']})
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def normalize(raw,bindings):
    if len(raw)!=164 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown command-enqueue body or bindings')
    words=list(struct.unpack('>41I',raw));result=list(words)
    mapping={0:{7:3},1:{7:3},2:{3:7},3:{14:15},4:{7:3,24:14},6:{14:15,3:7},7:{15:24},
        8:{15:24,24:14},13:{10:11},14:{7:3,12:10},15:{10:11,3:7},16:{11:12},17:{11:12,12:10},
        19:{14:15},20:{14:15,15:14},21:{15:14},22:{24:25},23:{7:3,8:24},24:{24:25,3:7},25:{25:8},
        26:{25:8,8:24},28:{10:11},29:{10:11},30:{11:12},31:{7:3,13:10},32:{11:12,3:7},33:{12:13},
        34:{12:13,13:10},35:{14:15},36:{14:15}}
    for index,rename in mapping.items():result[index]=registers(words[index],rename)
    for index in (8,17,26,34):
        word=result[index]
        if word&0xFC00003F!=33:raise ValueError('Changed commutative queue-address instruction')
        result[index]=(word&~0x03FF0000)|(word>>21&31)<<16|(word>>16&31)<<21
    if sum(a!=b for a,b in zip(words,result))!=30:raise ValueError('Changed queue normalization extent')
    return struct.pack('>41I',*result),dict(bindings)


def relocate(raw,bindings,address=0x800DC2B0):
    words=list(struct.unpack('>41I',raw))
    if bindings!=BINDINGS:raise ValueError('Changed queue address bindings')
    for at,entries in bindings.items():
        kind,_=entries[0]
        value=(address+0x8000)>>16 if kind=='R_MIPS_HI16' else address
        words[at//4]=words[at//4]&0xFFFF0000|value&65535
    return words


def symbolic_paths(words):
    """Compare both complete paths as ordered byte-memory operations, not colors."""
    if len(words)!=41 or words[36]>>26!=5 or words[36]&65535!=2 or \
            words[37]!=0 or words[39:]!=[0x03E00008,0]:
        raise ValueError('Unknown enqueue branch/return boundary')
    regs=[0,*(('input',i) for i in range(1,32))];events=[];stores=[];lo=None
    def execute(word):
        nonlocal lo
        op,rs,rt,rd=word>>26,word>>21&31,word>>16&31,word>>11&31
        imm=((word&65535)^32768)-32768;fn=word&63
        address=proof.expression('add',regs[rs],imm)
        if op==0:
            if fn==0:regs[rd]=proof.expression('shl',regs[rt],word>>6&31)
            elif fn in (33,37):regs[rd]=proof.expression('add' if fn==33 else 'or',regs[rs],regs[rt])
            elif fn==25:lo=('mullo',*sorted((regs[rs],regs[rt]),key=repr))
            elif fn==18 and lo is not None:regs[rd]=lo
            else:raise ValueError('Unsupported enqueue symbolic R instruction')
        elif op==9:regs[rt]=address
        elif op==15:regs[rt]=(word&65535)<<16
        elif op in (35,36):
            size=4 if op==35 else 1
            value=('read',address,size,tuple(stores));regs[rt]=value
            events.append(('read',address,size,value))
        elif op==43:
            value=regs[rt];stores.append((address,4,value));events.append(('write',address,4,value))
        else:raise ValueError('Unsupported enqueue symbolic instruction')
        regs[0]=0
    for word in words[:36]:execute(word)
    branch=words[36];condition=('eq',*sorted((regs[branch>>21&31],regs[branch>>16&31]),key=repr))
    preserved=tuple(regs[i] for i in (*range(16,24),28,29,30,31))
    expected=tuple(('input',i) for i in (*range(16,24),28,29,30,31))
    if preserved!=expected:raise ValueError('Queue append changes preserved ABI state')
    result={(condition,False):(tuple(events),preserved,regs[31])}
    execute(words[38])
    result[(condition,True)]=(tuple(events),preserved,regs[31])
    return result


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    normalize(raw,bindings);return raw,bindings


def normalization_proof(raw,bindings,retail,address=0x800DC2B0):
    normalized,moved=normalize(raw,bindings)
    if relocate(normalized,moved,address)!=list(retail):raise ValueError('Normalized enqueue differs from independent retail')
    a=symbolic_paths(relocate(raw,bindings,address));b=symbolic_paths(list(retail))
    if a!=b:raise ValueError('Enqueue ordered memory/control/ABI proof failed')
    return dict(paths=len(a),ordered_reads_all_writes_and_preserved_ABI_equal=True,
        void_return_not_dead_GPRs=True,four_commutative_address_sums=True)


def recovered_guards(before,raw,bindings,retail):
    normalized,moved=normalize(raw,bindings);normalization_proof(raw,bindings,retail)
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):raise ValueError('Existing enqueue guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated guard prefix')
    rows=[]
    for i,(old,new) in enumerate(zip(struct.unpack('>41I',raw),struct.unpack('>41I',normalized))):
        if old==new:continue
        entries=';'.join(k+':'+n for k,n in bindings.get(i*4,[])) or '-'
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%old,
            replacement='0x%08X'%new,expected_relocations=entries,replacement_relocations=entries,
            note='Normalize proven queue-append register lifetimes and commutative address sums',
            insert_after='',insert_after_relocations='',omit='false'))
    output=io.StringIO(newline='');writer=csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\n')
    writer.writerows(rows);return before+output.getvalue().encode()


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified',SELECTED);raw,bindings=checked_object(obj)
    retail=list(struct.unpack_from('>41I',values['conker/conker.us.bin'],ROM))
    row['proof']=normalization_proof(raw,bindings,retail)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/'+OWNER+'.c'].decode(),'owner-before')
    row['neighbors']=proof.same_functions(before,obj,(FUNCTION,))
    if diagnostics or row['diagnostics'] or (row['words'],row['differences'],row['neighbors'])!=(41,30,3) or \
            proof.normalized_pools(before)!=proof.normalized_pools(obj):raise ValueError('Changed enqueue owner/pools/shape')
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings,retail))
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/15AA10.s',filename=OWNER,word_patches_path=guards))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=164 or data[f['value']:f['value']+164]!=values['conker/conker.us.bin'][ROM:ROM+164]:
        raise ValueError('Padded enqueue differs from retail')
    (out/'qualified-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,words,row


def predicted_image(before,rom):
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    result=bytearray(before);at=proof.elf_slot_offset(before,ENTRY,164)
    result[at:at+164]=rom[ROM:ROM+164]
    rows=[r for r in symbol_rows(before) if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Unknown enqueue predecessor extent')
    struct.pack_into('>I',result,rows[0][0]+8,164)
    return bytes(result)


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=raw_text(root/'conker/build/conker.ld');old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unknown enqueue linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes()
    if image!=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin']):
        raise ValueError('Enqueue prediction changes unrelated ELF bytes')
    successor={'conker/build/conker.us.elf':image,
        'conker/src/game/'+OWNER+'.c':recovered_owner(values['conker/src/game/'+OWNER+'.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for name,data in successor.items():
        path=out/('after-elf' if name.endswith('.elf') else 'after-owner' if name.endswith('.c') else 'after-guards')
        if path.exists() and raw_read(path)!=data:raise ValueError('Changed first enqueue successor')
        if not path.exists():path.write_bytes(data)
    row=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in successor.items()},other_ELF_bytes_fixed=True,
        words=41,guards=30,changed_bytes=sum(a!=b for a,b in zip(values['conker/build/conker.us.elf'],image)))
    (out/'prediction.json').write_text(json.dumps(row,indent=2)+'\n');return row


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:raise ValueError('Changed enqueue successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(parent.checkpoint,INPUTS=INPUTS,AFTER=AFTER,expected_inputs=expected_inputs):yield


@contextmanager
def historical_view(root,out):
    with checkpoint_context(),parent.checkpoint.historical_view(root,out):yield


def audit(root,out):
    with checkpoint_context():parent.checkpoint.verify(root,out,True)
    for index,(name,digest) in enumerate(INPUTS.items()):
        if hashlib.sha256(raw_read(out/('before-%02d'%index))).hexdigest()!=digest or \
                hashlib.sha256(raw_read(root/name)).hexdigest()!=AFTER.get(name,digest):
            raise ValueError('Changed enqueue audit input: '+name)
    actual=raw_read(root/'conker/build/conker.us.elf');before=raw_read(out/'before-01')
    if actual!=predicted_image(before,raw_read(root/'conker/conker.us.bin')) or actual!=raw_read(out/'after-elf'):
        raise ValueError('Enqueue actual ELF differs from exact first prediction')
    from tools.match_progress import load_elf_functions
    from tools.check_game_data_layout import audit_layout
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Enqueue changed unrelated functions')
    proof.same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    raw,bindings=checked_object(out/'qualified.o')
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,bindings,
            struct.unpack_from('>41I',raw_read(root/'conker/conker.us.bin'),ROM)):
        raise ValueError('Enqueue changed guard history')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Enqueue changed protected Game data')
    result=dict(functions=len(a),only_target_code_and_size_changed=True,all_addresses_preserved=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=30,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--predict',action='store_true')
    parser.add_argument('--qualify',action='store_true');parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.predict or args.qualify or args.audit:
        print(json.dumps(audit(root,out) if args.audit else predict(root,out) if args.predict else qualify(root,out)[3],indent=2))
        raise SystemExit(0)
    for name,body in forms():print(json.dumps(measure(root,out,name,body)[2]),flush=True)
