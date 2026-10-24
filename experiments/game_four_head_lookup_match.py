"""Four-head first-match lookup with fixed-body derived allocation/loop guards."""
import csv
import io
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout


OWNER='generated_1D92F0'
SOURCE,ASM,OBJECT='conker/src/game/generated_1D92F0.c','conker/asm/1D92F0.s','conker/build/src/game/generated_1D92F0.c.o'
BUILD='conker/build/game-four-head-lookup-match/qualified'
SNAPSHOT_SHA='8ba855d3a0ad7cce551df5c23f6145a89e40f53bbbd0f0ac13aa6f7e2c86aef0'
BEFORE_OBJECT_SHA='623e098c49303414efc5b5da0fb59d700079cb93fab4d25fdb2cba1f18075a11'
BEFORE_ELF_SHA='4a81856d3680867e99ffd3e6ef5f6328701162418f849ffe023dd444f7dc511c'
HEADERS='#include <ultra64.h>\n'
DECLARATIONS='''/* Only selected head cells and the node's link/key prefix are known here. */
typedef struct LookupNode1D92F0 LookupNode1D92F0;
struct LookupNode1D92F0 {
    u8 reserved00[8];
    LookupNode1D92F0 *next;
    u8 reserved0C[4];
    u8 key;
};
typedef struct {
    LookupNode1D92F0 *cells[104];
} LookupRow1D92F0;

extern u8 D_800DCE50[0x340];
extern s32 D_800A9270[2];
'''
FUNCTION='func_151AE590'
ENTRY,ROM,SIZE=0x151AE590,0x1DBA40,176
BODY=176
TARGETS={FUNCTION:dict(entry=ENTRY,rom=ROM,retail_SHA256='98adf57f48b176f134989f22e64f57e0c91bb98ab109b282a7a9373e980d564a')}
FUNCTIONS=tuple(TARGETS)
SELECTED={FUNCTION:'''/* Search selected columns first, scanning both rows before the next column. */
LookupNode1D92F0 *func_151AE590(u8 key) {
    LookupNode1D92F0 *node, *next;
    u8 outer, row;
    s32 column;

    outer = 0;
    do {
        column = D_800A9270[outer];
        row = 0;
        do {
            node = ((LookupRow1D92F0 *)D_800DCE50)[row].cells[column];
            while (node != NULL) {
                next = node->next;
                if (key == node->key) return node;
                node = next;
            }
            row++;
        } while (row < 2);
        outer++;
    } while (outer < 2);
    return NULL;
}'''}
BINDINGS={8:[('R_MIPS_HI16','D_800DCE50')],24:[('R_MIPS_LO16','D_800DCE50')],12:[('R_MIPS_HI16','D_800A9270')],20:[('R_MIPS_LO16','D_800A9270')]}
GUARD_SHA='a8ba8e601cbacc6259f8261520d065b3679a71b6e772884dcfedc8ca6eba8a3e'
RAW_SHA='71952928fbaef3df6feb05e20f6da60a8c974c6467a7840c9260b4183f204e55'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+','line #',re.sub(r'\S+\.c','<unit>',text))


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Four-head lookup manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Four-head lookup frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Four-head lookup old object changed')
    for name,t in TARGETS.items():
        if digest(values['conker/conker.us.bin'][t['rom']:t['rom']+176])!=t['retail_SHA256']:
            raise ValueError('Four-head lookup retail slot changed: '+name)
    return values


def recovered_owner(before):
    result=before
    for name in FUNCTIONS:
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:raise ValueError('Unknown four-head lookup placeholder')
        result=result[:lo]+SELECTED[name]+result[hi:]
    at=result.index(SELECTED[FUNCTIONS[0]])
    return result[:at]+DECLARATIONS+'\n'+result[at:]


def payload(obj,name):
    data,functions,bindings=parse_object(obj);info=functions[name]
    raw=data[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero four-head lookup alignment tail')
    return raw[:end*4],{at-info['value']:rows for at,rows in bindings.items()if info['value']<=at<info['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ChildFourHeadLookupOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def fields(word,rs=None,rt=None,rd=None):
    for shift,value in ((21,rs),(16,rt),(11,rd)):
        if value is not None:word=(word&~(31<<shift))|(value<<shift)
    return word

def rename(word,mapping):
    op,fn=word>>26,word&63
    rs,rt,rd=word>>21&31,word>>16&31,word>>11&31
    if not word:return word
    if op==0:
        if fn in (0,2,3):return fields(word,rt=mapping.get(rt,rt),rd=mapping.get(rd,rd))
        if fn==8:return fields(word,rs=mapping.get(rs,rs))
        if fn in(33,35,37):return fields(word,rs=mapping.get(rs,rs),rt=mapping.get(rt,rt),rd=mapping.get(rd,rd))
        raise ValueError(('unsupported special',fn))
    if op==15:return fields(word,rt=mapping.get(rt,rt))
    if op in(4,5,9,10,12,35,36,43):return fields(word,rs=mapping.get(rs,rs),rt=mapping.get(rt,rt))
    raise ValueError(('unsupported opcode',op))

def edge(word,source,target,likely=False):
    if likely:word|=16<<26
    return(word&0xFFFF0000)|((target-source-1)&65535)

def normalized(code,rs):
    if len(code)!=172 or digest(code)!=RAW_SHA or rs!=BINDINGS:raise ValueError('Four-head lookup complete raw body or binding changed')
    w=list(struct.unpack('>43I',code));out=[]
    # Fold the map's existing ADDIU relocation into its indexed LW.
    out.extend([w[0],w[1],rename(w[2],{10:9}),rename(w[6],{10:9}),w[4],w[7]])
    out.append(fields(w[3],rt=5))
    out.append(fields(w[8],rs=5,rd=5))
    out.append((fields(w[9],rs=5,rt=5)&0xFFFF0000)|(w[5]&65535))
    out.extend([w[11],rename(w[10],{4:3}),fields(w[12],rt=5,rd=15),fields(w[32],rs=15,rd=5)])
    # The row and node roles form a closed V1/A0 lifetime exchange.
    for index in range(13,18):out.append(rename(w[index],{4:3}))
    out.extend([rename(w[18],{10:9}),rename(w[19],{11:10}),rename(w[20],{11:10,3:4}),rename(w[21],{4:3})])
    out.extend([rename(w[24],{4:3,13:12}),edge(rename(w[23],{3:4}),23,34),w[22]])
    tag=rename(w[25],{3:4,12:11});advance=rename(w[32],{3:4})
    out.extend([tag,rename(w[26],{3:4}),edge(fields(w[27],rs=8,rt=11),27,32,True),advance,w[29],rename(w[30],{3:4})])
    # Preserve the dead assignment and peel the next tag into the likely delay.
    out.extend([advance,edge(w[31],32,26,True),tag,rename(w[33],{13:12}),edge(w[34],35,13),rename(w[35],{4:3,13:12})])
    out.extend([rename(w[36],{14:13}),rename(w[37],{14:13}),edge(w[38],39,5),rename(w[39],{14:13}),w[40],w[41],w[42]])
    result=struct.pack('>44I',*out)
    new={8:rs[8],12:rs[24],24:rs[12],32:rs[20]}
    return result,new



def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Four-head lookup guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    if fields!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:
        raise ValueError('Four-head lookup guard schema changed')
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Four-head lookup rows already exist')
    fitted,moved=normalized(raw,bindings)
    before=struct.unpack('>43I',raw);after=struct.unpack('>44I',fitted)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Four-head lookup guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator=newline);count=0
    encode=lambda rows:';'.join(kind+':'+symbol for kind,symbol in rows)or'-'
    for index,(a,b)in enumerate(zip(before,after)):
        expected=bindings.get(index*4,[]);replacement=moved.get(index*4,[])
        if a==b and expected==replacement and index!=42:continue
        row=dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(index*4),expected='0x%08X'%a,replacement='0x%08X'%b,
            expected_relocations=encode(expected),replacement_relocations=encode(replacement),omit='false',
            note='Derive four-head lookup address setup, register lifetimes and peeled branch scheduling')
        if index==42:row.update(insert_after='0x%08X'%after[43],insert_after_relocations='-')
        writer.writerow(row);count+=1
    if count!=37:raise ValueError('Four-head lookup derived guard count changed')
    return old+stream.getvalue().encode()


def predicted_image(before,truths):
    if digest(before)!=BEFORE_ELF_SHA or set(truths)!=set(FUNCTIONS):raise ValueError('FourHeadLookup image predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=truths[name]
        if digest(truth)!=t['retail_SHA256']:raise ValueError('FourHeadLookup predicted body changed')
        at=elf_slot_offset(before,t['entry'],176);result[at:at+176]=truth
        rows=[offset for offset,n,fields,_ in symbol_rows(before)
              if n==name and fields[1:3]==(t['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('FourHeadLookup old symbol extent changed')
        struct.pack_into('>I',result,rows[0]+8,BODY)
    # The new references reorder one closed BFD symbol/string hash-bucket pair.
    rows={name:(offset,fields,location)for offset,name,fields,location in symbol_rows(before)}
    names=('D_80095BCC','D_8009EFCC');definitions=((0x80095BCC,0,16,0,65521),(0x8009EFCC,0,16,0,6))
    slots=[rows[name]for name in names];start,base=slots[0][2],slots[0][1][0];cursor=0
    for i,(name,(offset,fields,location))in enumerate(zip(names,slots)):
        if (offset-slots[0][0],location-start,fields[0]-base,fields[1:])!=(16*i,cursor,cursor,definitions[i]):
            raise ValueError('Four-head lookup closed symbol cycle changed')
        text=name.encode()+b'\0'
        if before[location:location+len(text)]!=text:raise ValueError('Four-head lookup symbol spelling changed')
        cursor+=len(text)
    new_names=names[::-1];replacement=b''.join(name.encode()+b'\0'for name in new_names)
    if len(replacement)!=cursor:raise ValueError('Four-head lookup string span changed')
    result[start:start+cursor]=replacement;cursor=0
    for(offset,_,_),name in zip(slots,new_names):
        other,_,_=rows[name];result[offset:offset+16]=before[other:other+16]
        struct.pack_into('>I',result,offset,base+cursor);cursor+=len(name)+1
    return bytes(result)


def truths(values):
    rom=values['conker/conker.us.bin']
    return {name:rom[t['rom']:t['rom']+176]for name,t in TARGETS.items()}


def check_image(before,actual,bodies):
    if actual!=predicted_image(before,bodies):raise ValueError('FourHeadLookup strict image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
                  predicted_image(before,truths(values))if installed and name=='conker/build/conker.us.elf'else
                  guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('FourHeadLookup current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('FourHeadLookup owner diagnostics changed: '+da+db)
    bodies=truths(values);rows={}
    for name,t in TARGETS.items():
        isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED[name],'selected-'+name)
        if diag:raise ValueError(diag)
        raw,bindings=payload(isolated,name)
        if len(raw)!=172 or payload(after,name)!=(raw,bindings)or payload(original(root,output,name),name)!=normalized(raw,bindings):
            raise ValueError('FourHeadLookup semantic C/normalized original payload differs')
        linked,fs=link_owner(root,output,original(root,output,name),OWNER);at=fs[name]['value']
        if linked[at:at+176]!=bodies[name]or bindings!=BINDINGS:
            raise ValueError('FourHeadLookup linked words or binding differ')
        rows[name]=dict(words=44,raw_words=43,frame=0,bindings=4,raw_SHA256=digest(raw),retail_SHA256=digest(bodies[name]))
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],*payload(after,FUNCTION)))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};masked_a=bytearray(a);masked_b=bytearray(b)
    for name,t in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('FourHeadLookup predecessor extent changed')
        expected[name]['size']=BODY;at=fb[name]['value']
        slot=elf_slot_offset(values['conker/build/conker.us.elf'],t['entry'],176)
        if a[at:at+176]!=values['conker/build/conker.us.elf'][slot:slot+176]or b[at:at+176]!=bodies[name]:
            raise ValueError('FourHeadLookup predecessor or linked target differs')
        masked_a[at:at+176]=bytes(176);masked_b[at:at+176]=bytes(176)
    if expected!=fb or masked_a!=masked_b:raise ValueError('FourHeadLookup changed another owner extent/body')
    neighbors=same_functions(before,after,FUNCTIONS)
    if neighbors!=len(parse_object(before)[1])-len(FUNCTIONS) or same_functions(old,obj,FUNCTIONS)!=neighbors:raise ValueError('FourHeadLookup neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('FourHeadLookup owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(functions=rows,total_words=44,slot_words=44,alignment_words=0,new_guards=37,inserted_schedule_words=1,compiler_only=False,preserved_neighbors=neighbors,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,
        all_owner_addresses_fixed=True,target_size_before=12,target_size_after=BODY)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    conker=root/'conker';reports=[]
    for label,src,obj,proposal,raw,wanted in(
        ('target',SOURCE,OBJECT,'proposed-owner.c','after-owner.o',output/'qualified-padded.o'),):
        shadow=output/('make-shadow-'+label);relative=obj.removeprefix('conker/build/')
        target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
        plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
            cwd=conker,capture_output=True,text=True,check=True)
        (output/('make-shadow-'+label+'-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
        for line in plan.stdout.replace('\\\n','').splitlines():
            args=shlex.split(line)
            if not args or args[0]=='rm':continue
            if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
                raise ValueError('Unexpected four-head lookup Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown four-head lookup redirect')
                redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
            p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
            if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):
                raise ValueError(p.stdout+p.stderr)
            if redirect is not None:redirect.write_text(p.stdout)
            commands.append(args)
        actual=conker/target;compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
        expected_commands=5
        processors=[a for a in commands if a[0]=='python3'and a[1]=='../tools/asm-processor/asm_processor.py']
        if(len(commands)!=expected_commands or len(compilers)!=1 or len(processors)!=2
                or not all(f in compilers[0]for f in('-O2','-g3'))):
            raise ValueError('FourHeadLookup normal Make profile changed')
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('FourHeadLookup actual Make padded object differs: '+label)
        reports.append(dict(copy=label,actual_Make_commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr))
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_1D92F0.c.o'
    if script.count(old)!=1:raise ValueError('FourHeadLookup link owner changed')
    link=output/'first-link.ld';link.write_text(script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix()))
    elf=output/'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt',
        '-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
        '--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(root/'conker').as_posix()],
        cwd=root/'conker',capture_output=True,check=True)
    before,actual=values['conker/build/conker.us.elf'],elf.read_bytes();bodies=truths(values);check_image(before,actual,bodies)
    changed=sum(a!=b for a,b in zip(before,actual));code=0
    for name,t in TARGETS.items():
        at=elf_slot_offset(before,t['entry'],176);code+=sum(a!=b for a,b in zip(before[at:at+176],bodies[name]))
    report=dict(exact_prediction=True,SHA256=digest(actual),changed_bytes=changed,code_bytes_changed=code,
        metadata_bytes_changed=changed-code,metadata_exclusions=0,closed_symbol_cycles=1)
    (output/'first-link.json').write_text(json.dumps(report,indent=2)+'\n');return report


def audit(root,output):
    values=check_inputs(root,output,installed=True);expected=predicted_image(values['conker/build/conker.us.elf'],truths(values))
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():
        raise ValueError('FourHeadLookup independent image or object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!=set(FUNCTIONS):
        raise ValueError('FourHeadLookup changed other function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('FourHeadLookup protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-len(FUNCTIONS),all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
