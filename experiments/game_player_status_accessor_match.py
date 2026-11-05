"""Direct status accessor, existing switch pool and complete caller ABI audit."""
import csv,hashlib,json,re,struct,subprocess
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_player_status_accessor_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly,ELF_HEADER,SECTION_HEADER,SYMBOL,RELOCATION,read_c_string
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game/generated_B21B0.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/B21B0.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin';BUILD='conker/build/game-player-status-accessor-150859AC-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,SLOT_SIZE=272,272
TABLE,TABLE_ROM=0x8009D9A0,0x242460
CASE_OFFSETS=(0x4C,0x64,0x80,0x9C,0xB8,0xD4,0xF0)
RAW_SHA256='1ed345c0c1cf006446afb25619e3a68cc4e2ad547f928a466a01c6372dd70bfe'
RETAIL_SHA256='79a2ee6a2d895bb5d251e23f34f0a77d4ddb4cfd136fa09f91d8075245e18731'
BASELINE_ELF_SHA256='cb8850d1e353bf3ac38ebcc8ed36d7852472aa46f11eb6f1d98aaa53a6e36b90'
SYMBOL_GROUPS=((0x2A796C,('func_150A547C','D_8009E93C')),(0x2B668C,('D_800D213C','D_800DBE3C')),
               (0x2C98CC,('D_8009A6A0','D_8009E580')),(0x2D7C3C,('func_151412BC','D_8009E5A4')))
BINDINGS={56:[('R_MIPS_HI16','.rodata')],64:[('R_MIPS_LO16','.rodata')],76:[('R_MIPS_HI16','D_800D2340')],80:[('R_MIPS_LO16','D_800D2340')],
112:[('R_MIPS_HI16','D_800D213C')],124:[('R_MIPS_LO16','D_800D213C')],140:[('R_MIPS_HI16','D_800D2140')],152:[('R_MIPS_LO16','D_800D2140')],
168:[('R_MIPS_HI16','D_800D2144')],180:[('R_MIPS_LO16','D_800D2144')],196:[('R_MIPS_HI16','D_800D2145')],208:[('R_MIPS_LO16','D_800D2145')],
224:[('R_MIPS_HI16','D_800D2146')],236:[('R_MIPS_LO16','D_800D2146')],252:[('R_MIPS_HI16','D_800D2148')],260:[('R_MIPS_LO16','D_800D2148')]}
RETAIL_BINDINGS={at:[(kind,'jtbl_8009D9A0'if name=='.rodata'else name)for kind,name in rows]for at,rows in BINDINGS.items()}
source_states=candidate.source_states
sha=lambda b:hashlib.sha256(b).hexdigest()

def function_blob(obj):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in relocations.items()if start<=at<start+size}

def original_bytes(root):return(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Status accessor raw body or bindings changed')
    if len(truth)!=SIZE or sha(truth)!=RETAIL_SHA256:raise ValueError('Status accessor retail body changed')
    expected=bytearray(truth)
    for at in RETAIL_BINDINGS:struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFFFF0000)
    if raw!=bytes(expected):raise ValueError('Status accessor direct body differs')
    return raw

def check_target_pool(obj):
    wanted={'.rodata':(bytes(32),tuple((4*i,FUNCTION,off)for i,off in enumerate(CASE_OFFSETS))),'.data':None}
    if normalized_pools(obj)!=wanted:raise ValueError('Status accessor compiler switch pool differs')
    return dict(bytes=32,case_entries=7,alignment_bytes=4,case_offsets=list(CASE_OFFSETS))

def alloc_pools(obj):
    """Retain every allocatable non-text byte and canonicalize its R32 targets."""
    data=Path(obj).read_bytes();h=ELF_HEADER.unpack_from(data)
    headers=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11])for i in range(h[12])]
    names=headers[h[13]];strings=data[names[4]:names[4]+names[5]];named={read_c_string(strings,s[0]):(i,s)for i,s in enumerate(headers)}
    symtab=named['.symtab'][1];strtab=headers[symtab[6]];symbol_names=data[strtab[4]:strtab[4]+strtab[5]]
    symbols=[SYMBOL.unpack_from(data,i)for i in range(symtab[4],symtab[4]+symtab[5],symtab[9]or SYMBOL.size)]
    functions=parse_object(obj)[1];result={};section_names={i:n for n,(i,s)in named.items()}
    for name,(index,s)in named.items():
        if not s[2]&2 or name=='.text':continue
        raw=bytearray(s[5])if s[1]==8 else bytearray(data[s[4]:s[4]+s[5]]);relocations=[]
        for rel in headers:
            if rel[1]!=9 or rel[7]!=index:continue
            for at in range(rel[4],rel[4]+rel[5],rel[9]or RELOCATION.size):
                offset,info=RELOCATION.unpack_from(data,at);symbol=symbols[info>>8]
                if info&255!=2:raise ValueError('Unsupported status caller pool relocation')
                addend=struct.unpack_from('>I',raw,offset)[0];value=(symbol[1]+addend)&0xFFFFFFFF
                if symbol[5]==named['.text'][0]:
                    owners=[(n,value-f['value'])for n,f in functions.items()if f['value']<=value<f['value']+f['size']]
                    if len(owners)!=1:raise ValueError('Unowned status caller pool target')
                    anchor=('text',*owners[0])
                elif symbol[5]in section_names:anchor=('section',section_names[symbol[5]],value)
                else:anchor=('external',read_c_string(symbol_names,symbol[0]),value,symbol[5])
                relocations.append((offset,info&255,anchor));struct.pack_into('>I',raw,offset,0)
        result[name]=(s[1],s[2],s[3],s[8],bytes(raw),tuple(relocations))
    return result

def census(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();rows=list(csv.reader((Path(root)/'conker/retail_layout.us.txt').read_text().splitlines()));calls=[];pointers=[]
    for offset in range(0,len(image)-3,4):
        word=struct.unpack_from('>I',image,offset)[0]
        if word==ENTRY:pointers.append(offset)
        if word>>26 not in(2,3)or(word&0x3FFFFFF)*4!=ENTRY&0xFFFFFFF:continue
        address=0x15000000+offset-0x2D4B0
        owners=[r for r in rows if len(r)>=5 and r[0]=='game'and int(r[3],0)<=address<int(r[4],0)]
        if len(owners)!=1 or word>>26!=3:raise ValueError('Status accessor call registry changed')
        row=owners[0];calls.append(dict(rom=offset,address=address,owner=row[1],function=row[2]))
    if len(calls)!=40 or len({r['owner']for r in calls})!=15 or pointers:raise ValueError('Status accessor caller census changed')
    return calls

def qualify_callers(root,out,installed):
    baseline=json.loads((out/'call-census.json').read_text());owners={r['owner']:r for r in baseline};report=[]
    header=root/'conker/include/functions.h';before_header,after_header,header_installed=candidate.repair_states('conker/include/functions.h',header.read_text())
    if header_installed!=installed:raise ValueError('Status accessor header/source installation differs')
    overlays={}
    for label,text in(('before',before_header),('after',after_header)):
        path=out/('header-'+label)/'functions.h';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);overlays[label]=path.relative_to(root/'conker').as_posix()
    for owner,row in sorted(owners.items()):
        path=row['source'];live=(root/path).read_text()
        if path in candidate.REPAIRS:
            before,after,current=candidate.repair_states(path,live)
            if current!=installed:raise ValueError('Status accessor caller repair installation differs')
        else:before=after=live
        for profile,flags in(('normal',('-O2','-g3')),('no-unroll',('-O2','-g3','-Wo,-loopunroll,0')))if owner=='generated_B3020'else(('normal',('-O2','-g3')),):
            objects=[];diagnostics=[]
            for label,text in(('before',before),('after',after)):
                text=re.sub(r'(?m)^#\s*include\s*["<]functions\.h[">]',lambda _: '#include "'+overlays[label]+'"',text)
                obj,diag=compile_owner(root,out,text,'caller-'+owner+'-'+profile+'-'+label,flags);objects.append(obj);diagnostics.append(harness.diagnostics(diag))
            if diagnostics[0]!=diagnostics[1]:raise ValueError('Status caller diagnostics changed: '+owner)
            count=same_functions(*objects)
            if alloc_pools(objects[0])!=alloc_pools(objects[1]):raise ValueError('Status caller non-text sections changed: '+owner)
            report.append(dict(owner=owner,profile=profile,unchanged_functions=count,allocatable_pools_unchanged=True))
    (out/'caller-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def assemble_owner(root,out,obj,label):
    path=out/label;path.mkdir(parents=True,exist_ok=True);assembly=path/(FILENAME+'.c.s');owner=path/(FILENAME+'.c.o')
    assembly.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=root/GUARDS,filename=FILENAME,rodata_symbol='jtbl_8009D9A0'))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(owner),str(assembly)],capture_output=True,check=True)
    return owner

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_ELF_SHA256 or len(truth)!=SIZE or sha(truth)!=RETAIL_SHA256:raise ValueError('Status accessor strict image inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,fields)for off,name,fields,string in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Status accessor predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    target_only=bytes(expected);symbols={name:(off,fields,string)for off,name,fields,string in symbol_rows(before)}
    for start,names in SYMBOL_GROUPS:
        group=[symbols[name]for name in names];strings=b''.join((name+'\0').encode()for name in names)
        base_name=group[0][1][0];base_string=group[0][2];cursor=0
        for i,(name,(off,fields,string))in enumerate(zip(names,group)):
            if off!=start+16*i or string!=base_string+cursor or fields[0]!=base_name+cursor:raise ValueError('Status accessor predecessor symbol group changed')
            cursor+=len(name)+1
        if before[base_string:base_string+len(strings)]!=strings:raise ValueError('Status accessor predecessor string block changed')
        text=b''
        for i,j in enumerate((1,0)):
            struct.pack_into('>IIIBBH',expected,start+16*i,base_name+len(text),*group[j][1][1:]);text+=(names[j]+'\0').encode()
        expected[base_string:base_string+len(strings)]=text
    if sum(a!=b for a,b in zip(target_only,expected))!=96:raise ValueError('Status accessor named serialization extent changed')
    if bytes(expected)!=after:
        offsets=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Status accessor literal image differs: '+repr((len(before),len(after),len(offsets),list(map(hex,offsets[:35])))))
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=source_states((root/SOURCE).read_text())
    for path in candidate.REPAIRS:
        if candidate.repair_states(path,(root/path).read_text())[2]!=installed:raise ValueError('Partial status accessor installation: '+path)
    old,od=candidate.compile_owner(root,out,before_source,'predecessor-compact');new,nd=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if harness.diagnostics(od)!=harness.diagnostics(nd):raise ValueError('Status accessor owner diagnostics changed')
    normalized(*function_blob(new),original_bytes(root));pool=check_target_pool(new)
    if normalized_pools(old)!={'.rodata':None,'.data':None}:raise ValueError('Status accessor predecessor pools changed')
    raw_neighbors=same_functions(old,new,(FUNCTION,));old_owner=assemble_owner(root,out,old,'predecessor-owner');new_owner=assemble_owner(root,out,new,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Status accessor live owner differs')
    if function_blob(new_owner)!=(function_blob(new)[0],RETAIL_BINDINGS):raise ValueError('Status accessor padded body differs')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if normalized_pools(old_owner)!=normalized_pools(new_owner):raise ValueError('Status accessor padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Status accessor live ELF differs')
    delta=strict_image(before,after,original_bytes(root))
    a,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    changed=[name for name in b if a[name]!=b[name]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>68I',original_bytes(root))):raise ValueError('Status accessor body/address closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Status accessor protected data differs')
    call_report=qualify_callers(root,out,installed)
    registry=census(root);report=dict(function=FUNCTION,source_installed=installed,words=68,slot_words=68,frame=0,guards=0,bindings=16,raw_neighbors=raw_neighbors,neighbors=neighbors,
        qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),strict_changed_bytes=delta,strict_exclusions=0,named_symbol_serialization_bytes=96,
        all_addresses_fixed=True,functions=len(b),changed_bodies=changed,compiler_pool=pool,protected_data=data,direct_calls=len(registry),caller_owners=15,caller_profiles=call_report)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=old_elf,qualified_elf=new_elf)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
