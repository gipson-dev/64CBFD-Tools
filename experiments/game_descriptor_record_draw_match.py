"""Closed delay-load/count-copy reorganization and literal whole-image audit.

The C body already owns all71 words, its0x68 frame and saved home44.
The normalizer derives a conditional stride-load hoist/dead sibling, eliminates
a byte-LBU's redundant ANDI255 copy, splits the product MFLO/copy and closes
the saved/scratch register-role cycles. No retail instruction is an input.
"""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_descriptor_record_draw_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=284,candidate.BUILD
OBJECT='conker/build/src/game/generated_1B5CC0.c.o'
ASM='conker/asm/1B5CC0.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
LAYOUT='conker/retail_layout.us.txt'
BASELINE_SHA='5b3e85e83f8b69982c48b619a9ffe9981d5ac55109ab0f85b9e92df58a43f851'
GUARD_SHA='ad8c4e24d535e3ccc7aa3d4c3ae7db4972c569bbf690238f68c65757438993c6'
sha=lambda b:hashlib.sha256(b).hexdigest()
RAW_SHA='07184d83cfebe469ba1ebf87ffe2a4d8c0a565fc07bcae0cbe905824f9d86c6d'
INPUT_BINDINGS={0x44:[('R_MIPS_HI16','D_800BE9C0')],0x58:[('R_MIPS_LO16','D_800BE9C0')],0xC4:[('R_MIPS_26','func_151137D4')]}
def rename(w,m):
    # R-format registers and ordinary I-format base/target fields only.
    op=w>>26
    if op==0:
        return(w&~0x03FFF800)|(m.get(w>>21&31,w>>21&31)<<21)|(m.get(w>>16&31,w>>16&31)<<16)|(m.get(w>>11&31,w>>11&31)<<11)
    assert op in(4,5,6,7,9,12,15,20,21,22,23,32,33,35,36,37,40,41,43),hex(w)
    return(w&~0x03FF0000)|(m.get(w>>21&31,w>>21&31)<<21)|(m.get(w>>16&31,w>>16&31)<<16)
def derive(raw,bindings):
    if hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=INPUT_BINDINGS:raise ValueError('Unqualified complete draw candidate')
    s=list(struct.unpack('>71I',raw));t=list(s)
    # On the nonzero path, w16's zero-extending LBU is the sole definition of
    # V0 through w29. Its ANDI255 is a redundant copy, before the saved bound.
    assert s[16]==0x92620002 and s[18]==0x14400003 and s[19]==0
    assert s[29]==0x304700FF and s[33]==0x00E0B025 and s[36]==0x00008012
    assert s[20]==0x10000027 and s[21]==0x02801025
    assert [s[i]>>26 for i in(22,23,24,25)]==[36,36,36,35]
    # Positive guard's conditional stride load: taken target moves from22 to23.
    # The original dead sibling at22 is a clone of this same ordinary load.
    # Empty path annuls w19 and takes20 to the unchanged epilogue60.
    t[16]=rename(s[16],{2:7})
    t[18]=((s[18]>>26|0x10)<<26)|(7<<21)|(23-19)
    t[19]=rename(s[23],{24:2});t[22]=t[19];t[23]=s[22]
    t[25]=rename(s[25],{5:3});t[26]=rename(s[26],{24:2});t[28]=rename(s[28],{5:3,25:24})
    t[29]=s[30];t[30]=rename(s[33],{22:21});t[31]=s[31]
    t[32]=rename(s[32],{18:16});t[33]=rename(s[34],{21:22});t[34]=rename(s[35],{25:24})
    # Split the exact same MFLO result into a volatile product then its saved
    # induction word. This replaces the proven redundant count-mask slot.
    t[35]=rename(s[36],{16:5});t[36]=(5<<21)|(18<<11)|0x25
    t[37]=rename(s[37],{2:7});t[38]=rename(s[38],{12:11})
    for i,m in{39:{9:8},40:{8:25},41:{16:18,11:10},42:{9:8,8:25},43:{10:9},50:{10:9,11:10},
                51:{18:16},52:{21:22},53:{16:18},54:{18:16,22:21},56:{5:3},57:{12:11},59:{5:3,12:11}}.items():t[i]=rename(s[i],m)
    moved={0x44:bindings[0x44],0x5C:bindings[0x58],0xC4:bindings[0xC4]}
    return struct.pack('>71I',*t),moved

OUTPUT_BINDINGS={0x44:INPUT_BINDINGS[0x44],0x5C:INPUT_BINDINGS[0x58],0xC4:INPUT_BINDINGS[0xC4]}
def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def checked(raw,bindings,truth):
    if len(raw)!=SIZE or bindings!=OUTPUT_BINDINGS:raise ValueError('Draw normalized extent/bindings changed')
    result=bound_blob(raw,bindings,dict(D_800BE9C0=0x800BE9C0,func_151137D4=0x151137D4))
    if result!=list(struct.unpack('>71I',truth)):raise ValueError('Draw normalized complete body differs')
def guard_manifest(before,raw,bindings):
    if sha(before)!=GUARD_SHA:raise ValueError('Draw predecessor guards changed')
    normalized,moved=derive(raw,bindings);rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['function']==FUNCTION for r in rows):raise ValueError('Draw already has guards')
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');count=0
    spec=lambda rs:';'.join(k+':'+n for k,n in rs)or'-'
    for i,(a,b)in enumerate(zip(struct.unpack('>71I',raw),struct.unpack('>71I',normalized))):
        at=4*i
        if a==b and bindings.get(at,[])==moved.get(at,[]):continue
        writer.writerow(dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=spec(bindings.get(at,[])),replacement_relocations=spec(moved.get(at,[])),note='Normalize closed matrix-batch register and conditional-load reorganization',insert_after='',insert_after_relocations='',omit='false'));count+=1
    if count!=30:raise ValueError('Draw guard derivation changed')
    tail=stream.getvalue().encode();tail=tail.replace(b'\n',b'\r\n')if b'\r\n'in before else tail
    return before+tail
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Draw discovery input changed: '+n)
        names=set(initial)|{'conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml','conker/asm/data/232040.rodata.s','conker/build/asm/data/232040.rodata.s.o'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Draw frozen input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Draw protected input changed: '+n)
    return len(values)
def same_pools(old,new):
    a,b=alloc_pools(old),alloc_pools(new)
    if set(a)!=set(b)or[n for n in a if a[n]!=b[n]]!=['.reginfo']:raise ValueError('Draw data pool or metadata set changed')
    x,y=a['.reginfo'],b['.reginfo']
    if x[:4]!=y[:4]or x[5:]!=y[5:]:raise ValueError('Draw register section shape/bindings changed')
    x,y=(struct.unpack('>6I',v[4])for v in(x,y))
    if x[1:]!=y[1:]or(x[0],y[0])!=(0xA31FDFFE,0xA3FFDFFE):raise ValueError('Draw GPR mask delta changed')
    return dict(all_data_bytes_and_bindings_fixed=True,raw_GPR_before=hex(x[0]),raw_GPR_after=hex(y[0]),added_registers=['S5','S6','S7'],all_other_metadata_fixed=True)
def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o
def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Draw literal predecessor changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Draw predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:raise ValueError('Draw literal whole image differs: '+str([hex(i)for i,(a,b)in enumerate(zip(expected,after))if a!=b][:30]))
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Draw named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text());old,od=candidate.compile_owner(root,out,before,'match-predecessor');new,nd=candidate.compile_owner(root,out,after,'match-qualified')
    if diagnostic_rows(od)!=diagnostic_rows(nd)or od or nd:raise ValueError('Draw owner gained diagnostics')
    raw_neighbors=same_functions(old,new,(FUNCTION,));raw_pools=same_pools(old,new)
    raw,bindings=function_blob(new);normalized,moved=derive(raw,bindings);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];checked(normalized,moved,truth)
    guards=(out/'match-frozen'/GUARDS).read_bytes();proposed=guard_manifest(guards,raw,bindings);old_guard=out/'predecessor-guards.csv';new_guard=out/'proposed-guards.csv';old_guard.write_bytes(guards);new_guard.write_bytes(proposed)
    if(root/GUARDS).read_bytes()!=(proposed if installed else guards):raise ValueError('Draw live guard/source phase mismatch')
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',new_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Draw live padded owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,))
    if alloc_pools(oo)!=alloc_pools(no):raise ValueError('Draw padded pools/register metadata changed')
    padded_pools=dict(all_data_bytes_and_bindings_fixed=True,all_register_metadata_fixed=True);checked(*function_blob(no),truth)
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'draw-predecessor-image');ne=harness.link_image(root,out,no,'draw-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Draw live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>71I',truth)):raise ValueError('Draw complete body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Draw protected data differs')
    (out/'proposed-owner.c').write_text(after)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,words=71,slot_words=71,alignment_words=0,frame=104,guards=30,raw_word_differences=30,bindings=3,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,raw_pool_audit=raw_pools,padded_pool_audit=padded_pools,compiler_diagnostics=0,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(proposed),strict_changed_bytes=delta,strict_exclusions=0,metadata_permutations=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,helper_and_parent_remain_unmatched=True)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
