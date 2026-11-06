"""Object ID flags: closed opening schedule, table aliases and literal image."""
import csv,hashlib,io,json,re,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_object_id_flags_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_c_object import emit_padded_assembly as emit_root
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=284,candidate.BUILD
OBJECT='conker/build/src/game/generated_68C70.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/68C70.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
CALLER,CALLER_OBJECT=candidate.CALLER,'conker/build/src/game_83300.c.o'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='ab6262907a6a478b78e45d878bdb1a9fa32fdb951a7815face207408d7fd0697'
GUARD_SHA='27673a32272270e3dc8bf10de90f57e5273beb43ec26516e5d449e7e60de990a'
TABLE,TABLE_ROM,TABLE_SIZE=0x8009877C,0x23D23C,188
TABLE_SHA='3604cee2ae24af0c6efdeef9195557fbc8e2becf8cda7b18dc7a80cafc777a9e'
SYMBOL_GROUPS=(
 (0x2A797C,('func_150A547C','D_8009E50C'),(1,0)),
 (0x2BF91C,('D_80098830','D_8009D790','D_8009D3B0','D_800ABA90'),(1,2,3,0)),
 (0x2D1C0C,('D_800AB1BC','D_20000010'),(1,0)),
 (0x2D1C6C,('func_151580B0','D_8009E910'),(1,0)),
 (0x2D2CFC,('D_80098780','D_8009D6B0'),(1,0)),
 (0x2D593C,('D_80098836','D_8008CBF4','D_800A8FBC','D_800A45BC'),(1,2,3,0)),
)
sha=lambda b:hashlib.sha256(b).hexdigest()
RAW_SHA='3794cd2eaa1de290c26f065c70aedf98a5e09acb67f689ceeeb32e5b2e389b3c'
TRUTH_SHA='4945b7f8f3e1a2d8b575337cbd788d5517decb2181ad675f15bd8ce99e413306'
BINDINGS={8: [('R_MIPS_HI16', 'D_80098836')], 16: [('R_MIPS_LO16', 'D_80098836')], 20: [('R_MIPS_HI16', 'D_80098830')], 28: [('R_MIPS_LO16', 'D_80098830')], 76: [('R_MIPS_HI16', 'D_8009877C')], 80: [('R_MIPS_LO16', 'D_8009877C')], 84: [('R_MIPS_HI16', 'D_8009877E')], 112: [('R_MIPS_LO16', 'D_8009877E')], 116: [('R_MIPS_HI16', 'D_80098780')], 120: [('R_MIPS_LO16', 'D_80098780')], 128: [('R_MIPS_HI16', 'D_80098780')], 148: [('R_MIPS_LO16', 'D_80098780')]}
ORIGINAL_BINDINGS={8: [('R_MIPS_HI16', 'D_80098830')], 16: [('R_MIPS_LO16', 'D_80098830')], 20: [('R_MIPS_HI16', 'D_80098836')], 24: [('R_MIPS_LO16', 'D_80098836')], 76: [('R_MIPS_HI16', 'D_8009877C')], 80: [('R_MIPS_LO16', 'D_8009877C')], 84: [('R_MIPS_HI16', 'D_8009877E')], 112: [('R_MIPS_LO16', 'D_8009877E')], 116: [('R_MIPS_HI16', 'D_80098780')], 120: [('R_MIPS_LO16', 'D_80098780')], 128: [('R_MIPS_HI16', 'D_80098830')], 148: [('R_MIPS_LO16', 'D_80098830')]}
PATCHES=(
    (0x8,0x3C020000,0x3C050000,[('R_MIPS_HI16', 'D_80098836')],[('R_MIPS_HI16', 'D_80098830')]),
    (0x10,0x24420000,0x24A50000,[('R_MIPS_LO16', 'D_80098836')],[('R_MIPS_LO16', 'D_80098830')]),
    (0x14,0x3C050000,0x3C020000,[('R_MIPS_HI16', 'D_80098830')],[('R_MIPS_HI16', 'D_80098836')]),
    (0x18,0x94830084,0x24420000,[],[('R_MIPS_LO16', 'D_80098836')]),
    (0x1C,0x24A50000,0x94830084,[('R_MIPS_LO16', 'D_80098830')],[]),
)

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();calls=[];pointers=[]
    for at in range(0,len(rom)-3,4):
        w=struct.unpack_from('>I',rom,at)[0]
        if w==ENTRY:pointers.append(at)
        if w>>26 in(2,3)and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:
            if w>>26!=3:raise ValueError('Object ID flags tail call changed')
            calls.append(at)
    if pointers or calls!=[0x8FC90]:raise ValueError('Object ID flags caller census changed')
    return calls

def freeze(root,out):
    manifest=out/'input-sha256.json'
    if not manifest.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze classifier at predecessor first')
        paths=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,MAKE,CALLER,CALLER_OBJECT,'conker/asm/data/23D1B0.rodata.s','conker/build/conker.us.bin','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json','conker/undefined_syms_auto.txt','conker/symbol_addrs.us.txt']
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/asm/nonmatchings/game_83300').glob('*.s')]
        values={}
        for name in sorted(set(paths)):
            data=(root/name).read_bytes();dest=out/'frozen'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);values[name]=sha(data)
        manifest.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(manifest.read_text());changed={SOURCE,OBJECT,ELF,GUARDS,CALLER,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for name,wanted in values.items():
        if sha((out/'frozen'/name).read_bytes())!=wanted:raise ValueError('Classifier frozen input changed: '+name)
        if name not in changed and sha((root/name).read_bytes())!=wanted:raise ValueError('Classifier protected input changed: '+name)
    return len(values)

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}

def fitted_bindings():
    result={at:r[:]for at,r in BINDINGS.items()}
    for at,old,new,ob,nb in PATCHES:
        if nb:result[at]=nb[:]
        else:result.pop(at,None)
    return result

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Classifier raw words/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Classifier original changed')
    result=bytearray(raw)
    for at,old,new,ob,nb in PATCHES:
        if struct.unpack_from('>I',result,at)[0]!=old or bindings.get(at,[])!=ob:raise ValueError('Classifier opening schedule changed')
        struct.pack_into('>I',result,at,new)
    expected=bytearray(truth)
    for at in ORIGINAL_BINDINGS:struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFFFF0000)
    # The indexed 88-halfword loop uses lower+176; the disassembly names the
    # same address D_80098830. Preserve that ordinary C relocation expression.
    struct.pack_into('>I',expected,148,struct.unpack_from('>I',expected,148)[0]|176)
    aliases=dict(ORIGINAL_BINDINGS);aliases[128]=[('R_MIPS_HI16','D_80098780')];aliases[148]=[('R_MIPS_LO16','D_80098780')]
    if result!=expected or fitted_bindings()!=aliases:raise ValueError('Classifier fitted words/aliases differ')
    before=Counter((old,tuple(ob))for at,old,new,ob,nb in PATCHES);after=Counter((new,tuple(nb))for at,old,new,ob,nb in PATCHES)
    if before!=after:raise ValueError('Classifier schedule is not a closed instruction/relocation permutation')
    return bytes(result)

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Classifier inherited guard bytes changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(r['function']==FUNCTION for r in reader):raise ValueError('Classifier already guarded')
    rows=[]
    for at,old,new,ob,nb in PATCHES:
        reloc=lambda r:';'.join(k+':'+n for k,n in r)or'-'
        rows.append(dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected=hex(old),replacement=hex(new),expected_relocations=reloc(ob),replacement_relocations=reloc(nb),note='Normalize independent classifier opening address and ID-load scheduling',insert_after='',insert_after_relocations='',omit='false'))
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(rows);return before+out.getvalue().encode()

def compact_pools(old,new):
    a,b=alloc_pools(old),alloc_pools(new);expected=(1879048198,2,0,4,bytes.fromhex('a300dffe0000000000000010000000000000000000007ff0'),())
    updated=(*expected[:4],bytes.fromhex('a300fffe0000000000000010000000000000000000007ff0'),())
    if a.get('.reginfo')!=expected or b.get('.reginfo')!=updated:raise ValueError('Classifier compact T5 mask metadata changed')
    if{n:v for n,v in a.items()if n!='.reginfo'}!={n:v for n,v in b.items()if n!='.reginfo'}:raise ValueError('Classifier other compact pools changed')
    return dict(section='.reginfo',before=expected[4].hex(),after=updated[4].hex(),GPR_mask_added='0x2000',register='T5',all_other_bytes_identical=True)

def assemble_owner(root,out,obj,manifest,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);guards=p/'patches.csv';guards.write_bytes(manifest);asm=p/'owner.s';dest=p/'owner.o'
    asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=guards,filename=FILENAME))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(dest),str(asm)],capture_output=True,check=True)
    return dest

def caller_owner(root,out,obj,manifest,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);guards=p/'patches.csv';guards.write_bytes(manifest);asm=p/'caller.s';dest=p/'caller.o'
    asm.write_text(emit_root(obj,root/'conker/retail_layout.us.txt','game_83300',word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(dest),str(asm)],capture_output=True,check=True)
    return dest

def check_caller(root,out,oldtext,newtext,manifest):
    old,od=candidate.compile_owner(root,out,oldtext,'caller-before');new,nd=candidate.compile_owner(root,out,newtext,'caller-after')
    clean=lambda t:re.sub(r'build/[^\n]+?\.c, line \d+:','<caller>:',t)
    if re.findall(r'Warning (\d+)',od)!=['712']*8 or clean(od)!=clean(nd):raise ValueError('Classifier caller diagnostics changed')
    count=same_functions(old,new,())
    if alloc_pools(old)!=alloc_pools(new):raise ValueError('Classifier caller pools changed')
    a=caller_owner(root,out,old,manifest,'caller-before-owner');b=caller_owner(root,out,new,manifest,'caller-after-owner')
    if a.read_bytes()!=b.read_bytes()or a.read_bytes()!=(root/CALLER_OBJECT).read_bytes():raise ValueError('Classifier complete caller object changed')
    return count

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Classifier literal inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Classifier predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    target_only=bytes(expected);symbols={n:(p,f,s)for p,n,f,s in symbol_rows(before)}
    for start,names,order in SYMBOL_GROUPS:
        group=[symbols[n]for n in names];strings=b''.join((n+'\0').encode()for n in names)
        base_name=group[0][1][0];base_string=group[0][2];cursor=0
        for i,(name,(off,fields,string))in enumerate(zip(names,group)):
            if off!=start+16*i or string!=base_string+cursor or fields[0]!=base_name+cursor:raise ValueError('Classifier symbol serialization baseline changed')
            cursor+=len(name)+1
        if before[base_string:base_string+len(strings)]!=strings:raise ValueError('Classifier original string block changed')
        text=b''
        for i,j in enumerate(order):
            struct.pack_into('>IIIBBH',expected,start+16*i,base_name+len(text),*group[j][1][1:]);text+=(names[j]+'\0').encode()
        expected[base_string:base_string+len(strings)]=text
    if sum(a!=b for a,b in zip(target_only,expected))!=161:raise ValueError('Classifier named serialization extent changed')
    if bytes(expected)!=after:
        diffs=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Classifier literal image differs: '+repr((len(before),len(after),len(diffs),list(map(hex,diffs[:35])))))
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Classifier named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text());cb,ca,ci=candidate.caller_states((root/CALLER).read_text())
    if installed!=ci:raise ValueError('Partial classifier prototype installation')
    old_guards=(out/'frozen'/GUARDS).read_bytes();new_guards=guard_manifest(old_guards)
    if(root/GUARDS).read_bytes()!=(new_guards if installed else old_guards):raise ValueError('Partial classifier guard installation')
    old,od=candidate.compile_owner(root,out,bs,'predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'qualified-compact')
    if od or nd:raise ValueError('Classifier owner diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];fitted=normalized(*function_blob(new),truth);raw_neighbors=same_functions(old,new,(FUNCTION,));pools=compact_pools(old,new)
    caller_count=check_caller(root,out,cb,ca,old_guards)
    old_owner=assemble_owner(root,out,old,old_guards,'predecessor-owner');new_owner=assemble_owner(root,out,new,new_guards,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Classifier live owner differs')
    if function_blob(new_owner)!=(fitted,fitted_bindings()):raise ValueError('Classifier padded words/bindings differ')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Classifier padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,old_owner,'predecessor-image');ne=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Classifier live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>71I',truth)):raise ValueError('Classifier body/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Classifier protected data changed')
    at=elf_slot_offset(after,TABLE,TABLE_SIZE);table=after[at:at+TABLE_SIZE]
    if sha(table)!=TABLE_SHA or table!=(root/ROM_IMAGE).read_bytes()[TABLE_ROM:TABLE_ROM+TABLE_SIZE]:raise ValueError('Classifier table contents/layout changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=71,frame=0,guards=5,bindings=len(BINDINGS),raw_neighbors=raw_neighbors,neighbors=neighbors,caller_functions_unchanged=caller_count,compact_metadata=pools,qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(new_guards),strict_changed_bytes=delta,strict_exclusions=0,named_serialization_bytes=161,closed_symbol_groups=6,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,direct_calls=census(root),table_bytes=TABLE_SIZE,table_alias='lower+176 equals primary')
    (out/'proposed-owner.c').write_text(ns);(out/'proposed-caller.c').write_text(ca);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
