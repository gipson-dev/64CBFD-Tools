"""Two closed floating-load words with a moved relocation and strict whole image."""
import hashlib,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_phase_motion_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_path_heading_turn_match import padded_pools
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=284,candidate.BUILD
OBJECT='conker/build/src/game/generated_185560.c.o'
ASM='conker/asm/185560.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
REGISTRY='conker/asm/data/22E220.rodata.s'
BASELINE_SHA='00e9bcfb500382daa9eb5e83eefade3abebbaaf4ba16bf05c27ab70ac249e5db'
GUARD_SHA='915496ebc88595fb6fa685dd89a03b174c869de5d070398620cd74f07086abd9'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE9E4')], 12: [('R_MIPS_LO16', 'D_800BE9E4')], 96: [('R_MIPS_26', 'func_151423D8')], 124: [('R_MIPS_26', 'func_151423D8')], 144: [('R_MIPS_HI16', 'D_800BE9A4')], 180: [('R_MIPS_LO16', 'D_800BE9A4')], 204: [('R_MIPS_26', 'func_15144B68')], 216: [('R_MIPS_26', 'sinf')]}
RETAIL_BINDINGS={k:v for k,v in BINDINGS.items()if k!=0xB4};RETAIL_BINDINGS[0xB8]=BINDINGS[0xB4]
SCHEDULE=((0xB4,0xC4300000,0xC6080020),(0xB8,0xC6080020,0xC4300000))
sha=lambda b:hashlib.sha256(b).hexdigest()

def proposed_guards(before):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Phase-motion predecessor guards changed')
    raw=Counter((word,tuple(BINDINGS.get(at,())))for at,word,_ in SCHEDULE)
    new=Counter((word,tuple(RETAIL_BINDINGS.get(at,())))for at,_,word in SCHEDULE)
    if raw!=new:raise ValueError('Phase-motion load origins/bindings are not closed')
    nl=b'\r\n' if b'\r\n'in before else b'\n'
    fmt=lambda rows:'|'.join(k+':'+n for k,n in rows)or'-'
    rows=[f'{FILENAME},{FUNCTION},0x{at:x},0x{a:08x},0x{b:08x},{fmt(BINDINGS.get(at,()))},{fmt(RETAIL_BINDINGS.get(at,()))},Normalize independent phase-motion rate and global-scale loads,,,false'.encode()for at,a,b in SCHEDULE]
    return before+nl.join(rows)+nl

def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        values=json.loads((out/'discovery-input-sha256.json').read_text(encoding='utf-8'))
        for n,h in values.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Phase-motion discovery changed: '+n)
        names=set(values)|{REGISTRY,'conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.ld'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((root/n).read_bytes())
        p.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(p.read_text(encoding='utf-8'));allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Frozen fade input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Protected fade input changed: '+n)
    if(root/GUARDS).read_bytes()not in((dest/GUARDS).read_bytes(),proposed_guards((dest/GUARDS).read_bytes())):raise ValueError('Phase-motion guard history differs')
    return len(values)

def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def checked(raw,bindings,truth,normalized=False):
    wanted=RETAIL_BINDINGS if normalized else BINDINGS
    if len(raw)!=SIZE or len(truth)!=SIZE or bindings!=wanted:raise ValueError('Phase-motion extent/bindings changed')
    expected=bytearray(truth)
    for at,rows in RETAIL_BINDINGS.items():
        w=struct.unpack_from('>I',expected,at)[0];mask=0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000
        struct.pack_into('>I',expected,at,w&mask)
    for at,a,b in SCHEDULE:
        if struct.unpack_from('>I',expected,at)[0]!=b:raise ValueError('Phase-motion retail schedule changed')
        if not normalized:struct.pack_into('>I',expected,at,a)
    if raw!=bytes(expected):raise ValueError('Phase-motion complete body changed')
    return raw,bindings

def raw_pool_audit(old,new):
    a,b=alloc_pools(old),alloc_pools(new)
    if set(a)!=set(b):raise ValueError('Phase-motion raw pool set changed')
    expected=dict(a);info=list(a['.reginfo']);raw=bytearray(info[4])
    if struct.unpack_from('>I',raw,8)[0]!=0x000F5777:raise ValueError('Phase-motion original FPR mask changed')
    struct.pack_into('>I',raw,8,0x000F7FF7);info[4]=bytes(raw);expected['.reginfo']=tuple(info)
    if b!=expected:raise ValueError('Phase-motion raw pool delta exceeded its explicit FPR mask')
    return dict(section='.reginfo',offset=8,before='0x000F5777',after='0x000F7FF7',other_bytes_and_bindings_fixed=True)

def paired_diagnostics(before,after):
    import re
    normalize=lambda value:re.sub(r'build/game-phase-motion-callback-1515A11C-match/match-(?:predecessor|qualified)-compact\.c, line \d+', '<same-owner-location>',value)
    a,b=normalize(before),normalize(after)
    if a!=b or a.count('Warning 712:')!=4 or a.count('func_100043B4(')!=2 or a.count('func_15158A20(')!=2:raise ValueError('Phase-motion existing diagnostic set changed')
    return a

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/'generated_185560.c.o'
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Phase-motion literal predecessor changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Phase-motion predecessor symbol extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Phase-motion literal image differs: '+repr((len(before),len(after),len(diff),list(map(hex,diff[:40])))))
    want=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if want!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Phase-motion named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();ws=struct.unpack('>%dI'%(len(rom)//4),rom)
    r=dict(calls=[4*i for i,w in enumerate(ws)if w==0x0C000000|((ENTRY>>2)&0x3FFFFFF)],tails=[4*i for i,w in enumerate(ws)if w==0x08000000|((ENTRY>>2)&0x3FFFFFF)],pointers=[4*i for i,w in enumerate(ws)if w==ENTRY])
    if r!=dict(calls=[],tails=[],pointers=[0x22E250]):raise ValueError('Phase-motion registration census changed')
    if '/* 22E250 80089790 1515A11C */ .word func_1515A11C'not in(root/REGISTRY).read_text(encoding='utf-8'):raise ValueError('Phase-motion registration changed')
    return r

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text(encoding='utf-8'))
    old,od=candidate.compile_owner(root,out,bs,'match-predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'match-qualified-compact')
    diagnostics=paired_diagnostics(od,nd)
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=checked(*function_blob(new),truth)
    rn=same_functions(old,new,(FUNCTION,))
    pool_delta=raw_pool_audit(old,new)
    before_csv=out/'match-frozen'/GUARDS;after_csv=out/'proposed-guards.csv';after_csv.write_bytes(proposed_guards(before_csv.read_bytes()))
    oo=assemble_owner(root,out,old,'match-predecessor-owner',before_csv);no=assemble_owner(root,out,new,'match-qualified-owner',after_csv)
    if(oo if not installed else no).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Phase-motion live owner differs')
    checked(*function_blob(no),truth,normalized=True);pn=same_functions(oo,no,(FUNCTION,))
    if padded_pools(oo)!=padded_pools(no):raise ValueError('Phase-motion padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,oo,'phase-predecessor-image');ne=harness.link_image(root,out,no,'phase-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Phase-motion live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>71I',truth)):raise ValueError('Phase-motion body/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Phase-motion protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=71,raw_words=71,slot_words=71,alignment_words=0,raw_word_differences=2,frame=40,guards=2,bindings=8,raw_neighbors=rn,neighbors=pn,raw_pool_delta=pool_delta,padded_pools_unchanged=True,existing_compiler_warnings=4,new_compiler_diagnostics=0,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(after_csv.read_bytes()),guard_predecessor_sha256=GUARD_SHA,strict_changed_bytes=delta,strict_exclusions=0,metadata_permutations=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,caller_census=census(root))
    (out/'proposed-owner.c').write_text(ns,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
