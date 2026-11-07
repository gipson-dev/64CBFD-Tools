"""Two unescaped integer RNG capture homes; complete owner and image audit."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_random_effect_forwarder_candidates as candidate
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
OBJECT='conker/build/src/game/generated_1F2730.c.o'
ASM='conker/asm/1F2730.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='87dea8d709b296170b7aa059bf1c5536b12f81aa8b31776a0c9e558ce38da2a1'
GUARD_SHA='c15388177b685143a54749a4611773ee2444c29bd631fca43e3236e31f8479ad'
RAW_SHA='9acf2dc58ae04415fddaaa159df11fa297f84da9d846376273a66bdbd25b213d'
BINDINGS={24: [('R_MIPS_26', 'func_150ADA68')], 32: [('R_MIPS_HI16', 'D_800AAABC')], 36: [('R_MIPS_LO16', 'D_800AAABC')], 52: [('R_MIPS_HI16', 'D_800AAAC0')], 56: [('R_MIPS_LO16', 'D_800AAAC0')], 68: [('R_MIPS_26', 'func_150ADA68')], 96: [('R_MIPS_HI16', 'D_800AAAC4')], 100: [('R_MIPS_LO16', 'D_800AAAC4')], 112: [('R_MIPS_26', 'func_150ADA20')], 120: [('R_MIPS_26', 'func_150ADA20')], 128: [('R_MIPS_26', 'func_150ADA68')], 188: [('R_MIPS_HI16', 'D_800AAA90')], 224: [('R_MIPS_LO16', 'D_800AAA90')], 192: [('R_MIPS_HI16', 'D_800AAA9C')], 220: [('R_MIPS_LO16', 'D_800AAA9C')], 144: [('R_MIPS_HI16', 'D_800AAAC8')], 148: [('R_MIPS_LO16', 'D_800AAAC8')], 260: [('R_MIPS_26', 'func_15102B38')]}
sha=lambda b:hashlib.sha256(b).hexdigest()

def derive(raw,bindings):
    if sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Unqualified complete effect forwarder')
    words=list(struct.unpack('>71I',raw))
    for at in(0x7C,0x84,0x9C):
        i=at//4;w=words[i]
        if w>>21&31!=29 or w>>26 not in(35,43):raise ValueError('Only private word-sized stack homes may move')
        words[i]=(w&0xFFFF0000)|((w&65535)-4)
    return struct.pack('>71I',*words),dict(bindings)


def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def home_closure(raw,bindings):
    normalized,_=derive(raw,bindings);words=struct.unpack('>71I',raw)
    moves={0x48:0x44,0x4C:0x48};observed=[]
    for i,w in enumerate(words):
        if w>>21&31==29 and w>>26 in(32,33,35,36,37,40,41,43,49,57)and w&65535 in moves:observed.append(4*i)
    if observed!=[0x7C,0x84,0x9C]:raise ValueError('Effect private home use is not closed')
    # The sole address escape is the disjoint two-float pair SP+0x50.
    addresses=[w&65535 for w in words if w>>26==9 and w>>21&31==29 and w>>16&31!=29]
    if addresses!=[0x50]:raise ValueError('Effect local address escape changed')
    if words[0]!=0x27BDFFA8 or words[1]!=0xAFBF003C:raise ValueError('Effect frame/saved RA differs')
    return dict(moved_homes={'0x48':'0x44','0x4c':'0x48'},word_accesses=observed,escaped_pair='SP+0x50',frame_unchanged=88,all_operations_registers_bindings_fixed=True,no_insertions_or_omissions=True,retail_words_not_an_input=True,raw_private_home_alpha_mapping_only=True)


def guard_manifest(before,raw,bindings):
    if sha(before)!=GUARD_SHA:raise ValueError('Effect forwarder predecessor guards changed')
    normalized,moved=derive(raw,bindings);rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['function']==FUNCTION for r in rows):raise ValueError('Effect forwarder already guarded')
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');count=0
    for i,(a,b)in enumerate(zip(struct.unpack('>71I',raw),struct.unpack('>71I',normalized))):
        if a==b:continue
        at=4*i;assert at not in bindings
        writer.writerow(dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Normalize closed effect RNG capture word homes',insert_after='',insert_after_relocations='',omit='false'));count+=1
    if count!=3:raise ValueError('Effect forwarder guard derivation changed')
    tail=stream.getvalue().encode();return before+(tail.replace(b'\n',b'\r\n')if b'\r\n'in before else tail)

def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Effect forwarder discovery changed: '+n)
        names=set(initial)|{'conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Effect forwarder protected input changed: '+n)
    return len(values)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Effect forwarder predecessor image changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Effect forwarder predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    # Exact GNU name/definition serialization; preserve every named attribute.
    named={n:(p,f,s)for p,n,f,s in symbol_rows(before)}
    groups=(('D_800AAABC','func_10007DA0'),('D_800AAA9C','D_800A114C'),('func_150F5590','D_8009E8C8'),('D_800AAAC4','func_15006010'),('func_15173C60','D_8009E4B4'),('D_800AAA90','D_800A1140'))
    for names in groups:
        pair=[named[n]for n in names];labels=[n.encode()+b'\0'for n in names];start=pair[0][2]
        if pair[1][0]!=pair[0][0]+16 or pair[1][2]!=start+len(labels[0])or before[start:start+sum(map(len,labels))]!=b''.join(labels):raise ValueError('Effect named metadata group changed')
        expected[start:start+sum(map(len,labels))]=b''.join(labels[::-1])
        for slot,index in enumerate((1,0)):struct.pack_into('>IIIBBH',expected,pair[slot][0],pair[0][1][0]+(len(labels[1])if slot else 0),*pair[index][1][1:])
    if bytes(expected)!=after:raise ValueError('Effect forwarder literal full image differs')
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Effect forwarder named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text());old,od=candidate.compile_owner(root,out,before,'match-predecessor');new,nd=candidate.compile_owner(root,out,after,'match-qualified')
    if od or nd:raise ValueError('Effect forwarder owner diagnostics changed')
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    if alloc_pools(old)!=alloc_pools(new):raise ValueError('Effect forwarder raw pools or register metadata changed')
    raw,bindings=function_blob(new);normalized,moved=derive(raw,bindings);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
    if bound_blob(normalized,moved,{n:int(n.split('_')[1],16)for entries in BINDINGS.values()for _,n in entries})!=list(struct.unpack('>71I',truth)):raise ValueError('Effect forwarder complete normalized words differ')
    guards=(out/'match-frozen'/GUARDS).read_bytes();proposed=guard_manifest(guards,raw,bindings);old_guard=out/'predecessor-guards.csv';new_guard=out/'proposed-guards.csv';old_guard.write_bytes(guards);new_guard.write_bytes(proposed)
    if(root/GUARDS).read_bytes()!=(proposed if installed else guards):raise ValueError('Effect forwarder source/guard phase differs')
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',new_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Effect forwarder live owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,))
    if alloc_pools(oo)!=alloc_pools(no):raise ValueError('Effect forwarder padded pools/metadata differ')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'effect-predecessor-image');ne=harness.link_image(root,out,no,'effect-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Effect forwarder live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>71I',truth)):raise ValueError('Effect forwarder body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Effect forwarder protected data differs')
    (out/'proposed-owner.c').write_text(after)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,words=71,slot_words=71,alignment_words=0,frame=88,guards=3,raw_word_differences=3,bindings=18,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,all_raw_and_padded_pools_and_metadata_fixed=True,compiler_diagnostics=0,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(proposed),strict_changed_bytes=delta,strict_exclusions=0,metadata_pair_permutations=6,all_named_definition_attributes_fixed=True,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
