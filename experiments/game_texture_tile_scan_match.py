"""Derive closed scratch-register roles and commutative equality operands.

Every instruction, branch displacement, access order, frame, saved register
and binding comes from the complete 71-word semantic C. Retail words are
only the independent acceptance oracle, never a normalizer input.
"""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_texture_tile_scan_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_descriptor_record_draw_match import rename
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS,BUILD=candidate.ENTRY,candidate.ROM,candidate.WORDS,candidate.BUILD
SIZE=284
OBJECT='conker/build/src/game/generated_1C2C60.c.o'
ASM='conker/asm/1C2C60.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='2d333adffe40d55c9cd604becb49ecf83af8786f61f2fbb6a517eb92df48a03c'
GUARD_SHA='66e044ccfd4d99b544ee362bc2db067d80e3d825bc5db9a5031c86d66e625054'
RAW_SHA='e5db95952f62b3bc8b9d7eb65a1f8286a7c70060e5872ca545902a4cb96c999c'
BINDINGS={0xC:[('R_MIPS_HI16','D_800B0E58')],0x18:[('R_MIPS_LO16','D_800B0E58')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
ROLES={13:{11:14},14:{11:14,12:15},28:{15:11},31:{15:11,24:12},32:{24:12,25:13},33:{12:15,13:24},34:{13:24,25:13},41:{11:5},43:{11:5,12:25},44:{12:25},47:{14:11},48:{14:11,15:12},49:{15:12},53:{24:14},55:{25:13},56:{24:14,13:15},57:{13:15},58:{25:13,11:24},59:{11:24},61:{12:25},62:{12:25,14:11},64:{14:11},66:{24:14}}
SWAPS=(15,17,23,25,27,34,44)

def derive(raw,bindings):
    if sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Unqualified complete texture scanner')
    original=list(struct.unpack('>71I',raw));words=list(original)
    for i,m in ROLES.items():words[i]=rename(words[i],m)
    for i in SWAPS:
        w=words[i]
        if w>>26 not in(4,5,20,21):raise ValueError('Only equality/inequality operands may commute')
        words[i]=(w&~0x03FF0000)|((w>>21&31)<<16)|((w>>16&31)<<21)
    for a,b in zip(original,words):
        if a>>26!=b>>26 or (a>>26 and a&65535!=b&65535):raise ValueError('Texture scan operation or immediate changed')
    return struct.pack('>71I',*words),dict(bindings)

def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def role_closure(raw,bindings):
    """Must-equality dataflow over every branch edge and conditional delay.

    Proves the register change for arbitrary initial integer registers and
    memory, including aliases and access faults, independently of retail bytes.
    """
    normalized,_=derive(raw,bindings);a=struct.unpack('>71I',raw);b=struct.unpack('>71I',normalized)
    def successors(node):
        i,pending=node;w=a[i];op=w>>26;rs,rt=w>>21&31,w>>16&31
        if pending is not None:return []if pending==-1 else[(pending,None)]
        if op==0 and w&63==8:return[(i+1,-1)]
        if op in(4,5,20,21):
            dest=i+1+((w&65535)^32768)-32768
            taken=rs!=rt or op in(4,20);untaken=rs!=rt or op in(5,21)
            return ([(i+1,dest)]if taken else[])+([(i+2,None)if op in(20,21)else(i+1,i+2)]if untaken else[])
        return[(i+1,None)]
    def shape(w):
        op=w>>26;rs,rt,rd=w>>21&31,w>>16&31,w>>11&31
        if op==0:
            fn=w&63
            if fn in(0,3):return [rt],rd
            if fn in(33,37):return[rs,rt],rd
            if fn==8:return[rs],None
        if op in(9,10):return[rs],rt
        if op==15:return[],rt
        if op in(32,35):return[rs],rt
        if op==43 or op in(4,5,20,21):return[rs,rt],None
        raise ValueError('Unbounded texture scanner operation: '+hex(w))
    graph={};todo=[(0,None)]
    while todo:
        node=todo.pop()
        if node in graph:continue
        graph[node]=successors(node);todo.extend(graph[node])
    incoming={(0,None):frozenset((i,i)for i in range(32))};todo=[(0,None)];transfers=0
    while todo:
        node=todo.pop();i,_=node;_,x=shape(a[i]);_,y=shape(b[i]);r=incoming[node]
        if x is not None:
            if bool(x)!=bool(y):raise ValueError('Zero register destination changed')
            if x:r=frozenset((p,q)for p,q in r if p!=x and q!=y)|{(x,y)}
        for next_node in graph[node]:
            old=incoming.get(next_node);new=r if old is None else old&r
            if old!=new:incoming[next_node]=new;todo.append(next_node)
        transfers+=1
        if transfers>100000:raise ValueError('Texture scanner role proof failed to converge')
    exits=0
    for node in graph:
        i,pending=node;left,x=shape(a[i]);right,y=shape(b[i]);r=incoming[node]
        if i in SWAPS:right.reverse()
        if len(left)!=len(right)or any((p,q)not in r for p,q in zip(left,right)):raise ValueError('Unclosed texture scanner register use at '+hex(4*i))
        if a[i]>>26!=b[i]>>26 or (a[i]&0x7FF if a[i]>>26==0 else a[i]&65535)!=(b[i]&0x7FF if b[i]>>26==0 else b[i]&65535):raise ValueError('Texture scanner operation/immediate changed')
        if pending==-1:
            after=r
            if x:after=frozenset((p,q)for p,q in r if p!=x and q!=y)|{(x,y)}
            if any((reg,reg)not in after for reg in(0,2,*range(16,24),28,29,30,31)):raise ValueError('Texture scanner exit/ABI relation differs')
            exits+=1
    if set(i for i,p in graph)!=set(range(71))or exits!=1:raise ValueError('Texture scanner CFG coverage differs')
    return dict(CFG_instruction_contexts=len(graph),fixed_point_transfers=transfers,all_71_instructions=True,all_branch_and_annulled_delay_edges=True,arbitrary_register_and_memory_relation=True,all_load_store_addresses_values_and_order_equal=True,return_and_preserved_ABI_equal=True,retail_words_not_an_input=True)

def guard_manifest(before,raw,bindings):
    if sha(before)!=GUARD_SHA:raise ValueError('Texture scanner predecessor guards changed')
    normalized,moved=derive(raw,bindings);rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['function']==FUNCTION for r in rows):raise ValueError('Texture scanner already guarded')
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');count=0
    for i,(a,b)in enumerate(zip(struct.unpack('>71I',raw),struct.unpack('>71I',normalized))):
        if a==b:continue
        at=4*i;assert at not in bindings
        writer.writerow(dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Normalize closed texture scanner scratch registers and equality operand order',insert_after='',insert_after_relocations='',omit='false'));count+=1
    if count!=28:raise ValueError('Texture scanner guard derivation changed')
    tail=stream.getvalue().encode();return before+(tail.replace(b'\n',b'\r\n')if b'\r\n'in before else tail)

def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Texture scanner discovery changed: '+n)
        names=set(initial)|{'conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Texture scanner protected input changed: '+n)
    return len(values)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Texture scanner predecessor image changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Texture scanner predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:raise ValueError('Texture scanner literal full image differs')
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Texture scanner named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text());old,od=candidate.compile_owner(root,out,before,'match-predecessor');new,nd=candidate.compile_owner(root,out,after,'match-qualified')
    if od or nd:raise ValueError('Texture scanner owner diagnostics changed')
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    if alloc_pools(old)!=alloc_pools(new):raise ValueError('Texture scanner raw pools or register metadata changed')
    raw,bindings=function_blob(new);normalized,moved=derive(raw,bindings);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
    if bound_blob(normalized,moved,dict(D_800B0E58=0x800B0E58))!=list(struct.unpack('>71I',truth)):raise ValueError('Texture scanner complete normalized words differ')
    guards=(out/'match-frozen'/GUARDS).read_bytes();proposed=guard_manifest(guards,raw,bindings);old_guard=out/'predecessor-guards.csv';new_guard=out/'proposed-guards.csv';old_guard.write_bytes(guards);new_guard.write_bytes(proposed)
    if(root/GUARDS).read_bytes()!=(proposed if installed else guards):raise ValueError('Texture scanner source/guard phase differs')
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',new_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Texture scanner live owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,))
    if alloc_pools(oo)!=alloc_pools(no):raise ValueError('Texture scanner padded pools/metadata differ')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'texture-scan-predecessor-image');ne=harness.link_image(root,out,no,'texture-scan-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Texture scanner live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>71I',truth)):raise ValueError('Texture scanner body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Texture scanner protected data differs')
    (out/'proposed-owner.c').write_text(after)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,words=71,slot_words=71,alignment_words=0,frame=8,guards=28,raw_word_differences=28,bindings=2,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,all_raw_and_padded_pools_and_metadata_fixed=True,compiler_diagnostics=0,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(proposed),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
