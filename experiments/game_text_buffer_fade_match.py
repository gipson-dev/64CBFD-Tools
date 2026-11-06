"""Text-buffer fade: six closed scheduling words and a literal whole-image gate."""
import hashlib,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_text_buffer_fade_candidates as candidate
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
SIZE,BUILD=276,candidate.BUILD
OBJECT='conker/build/src/game/generated_FC5F0.c.o'
ASM='conker/asm/FC5F0.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
REGISTRY='conker/asm/data/22D350.rodata.s'
BASELINE_SHA='a085abfe66c18a183f8cbe8464dd72a9df1557af1f0d67ec15282095fa3c95f4'
GUARD_SHA='31a596ab2aed75f8e41e1119155b7381d597b7ae51ceda71eaa56b9c78854cd8'
BINDINGS={60:[('R_MIPS_HI16','D_800BE9E4')],80:[('R_MIPS_LO16','D_800BE9E4')],128:[('R_MIPS_26','func_1504332C')],168:[('R_MIPS_26','func_15042D94')],204:[('R_MIPS_26','func_1504332C')],244:[('R_MIPS_26','func_15042D94')]}
SCHEDULE=((0xB4,0x8FA20030,0x240400CE),(0xB8,0x24420028,0x8FA20030),(0xBC,0xAFA20020,0x240500C4),(0xC0,0x240400CE,0x24060061),(0xC4,0x240500C4,0x24420028),(0xC8,0x24060061,0xAFA20020))
sha=lambda b:hashlib.sha256(b).hexdigest()

def proposed_guards(before):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Text fade predecessor guards changed')
    if Counter(a for _,a,_ in SCHEDULE)!=Counter(b for _,_,b in SCHEDULE):raise ValueError('Text fade schedule is not closed')
    nl=b'\r\n' if b'\r\n' in before else b'\n'
    rows=[f'{FILENAME},{FUNCTION},0x{at:x},0x{a:08x},0x{b:08x},-,-,Normalize closed text-buffer fade descriptor and color-argument schedule,,,false'.encode() for at,a,b in SCHEDULE]
    return before+nl.join(rows)+nl

def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze fade predecessor first')
        screen=json.loads((out/'screen-inputs.json').read_text(encoding='utf-8'))
        for n,h in screen.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Fade screen input changed: '+n)
        names=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,MAKE,REGISTRY,'conker/build/conker.us.bin','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json','conker/undefined_syms_auto.txt','conker/symbol_addrs.us.txt','conker/src/game_70200.c']
        names += [q.relative_to(root).as_posix() for q in(root/'conker/include').rglob('*.h')]
        values={}
        for n in sorted(set(names)):
            data=(root/n).read_bytes();q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data);values[n]=sha(data)
        p.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(p.read_text(encoding='utf-8'));allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Frozen fade input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Protected fade input changed: '+n)
    old=(dest/GUARDS).read_bytes();new=proposed_guards(old)
    if(root/GUARDS).read_bytes() not in(old,new):raise ValueError('Fade guard history changed')
    return len(values)

def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def checked(raw,bindings,truth,normalized=False):
    if len(raw)!=SIZE or len(truth)!=SIZE or bindings!=BINDINGS:raise ValueError('Fade extent/bindings changed')
    expected=bytearray(truth)
    for at,rows in BINDINGS.items():
        w=struct.unpack_from('>I',expected,at)[0];mask=0xFC000000 if rows[0][0]=='R_MIPS_26' else 0xFFFF0000
        struct.pack_into('>I',expected,at,w&mask)
    for at,a,b in SCHEDULE:
        if struct.unpack_from('>I',expected,at)[0]!=b:raise ValueError('Fade retail schedule changed')
        if not normalized:struct.pack_into('>I',expected,at,a)
    if raw!=bytes(expected):raise ValueError('Fade complete body changed')
    return raw,bindings

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/'generated_FC5F0.c.o'
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards,rodata_symbol='D_800A0860'),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Fade literal predecessor changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Fade predecessor symbol extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Fade literal image differs: '+repr((len(before),len(after),len(diff),list(map(hex,diff[:40])))))
    want=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if want!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Fade named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();ws=struct.unpack('>%dI'%(len(rom)//4),rom)
    r=dict(calls=[4*i for i,w in enumerate(ws)if w==0x0C000000|((ENTRY>>2)&0x3FFFFFF)],tails=[4*i for i,w in enumerate(ws)if w==0x08000000|((ENTRY>>2)&0x3FFFFFF)],pointers=[4*i for i,w in enumerate(ws)if w==ENTRY])
    if r!=dict(calls=[],tails=[],pointers=[0x22D360]):raise ValueError('Fade registration census changed')
    if '/* 22D360 800888A0 150D01A0 */ .word func_150D01A0'not in(root/REGISTRY).read_text(encoding='utf-8'):raise ValueError('Fade registration changed')
    return r

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text(encoding='utf-8'))
    old,od=candidate.compile_owner(root,out,bs,'match-predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'match-qualified-compact')
    if od or nd:raise ValueError('Fade owner diagnostics changed: '+od+nd)
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=checked(*function_blob(new),truth)
    rn=same_functions(old,new,(FUNCTION,))
    if alloc_pools(old)!=alloc_pools(new):raise ValueError('Fade compact owner pools changed')
    before_csv=out/'match-frozen'/GUARDS;after_csv=out/'proposed-guards.csv';after_csv.write_bytes(proposed_guards(before_csv.read_bytes()))
    oo=assemble_owner(root,out,old,'match-predecessor-owner',before_csv);no=assemble_owner(root,out,new,'match-qualified-owner',after_csv)
    if(oo if not installed else no).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Fade live owner differs')
    checked(*function_blob(no),truth,normalized=True);pn=same_functions(oo,no,(FUNCTION,))
    if padded_pools(oo)!=padded_pools(no):raise ValueError('Fade padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,oo,'fade-predecessor-image');ne=harness.link_image(root,out,no,'fade-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Fade live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>69I',truth)):raise ValueError('Fade body/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Fade protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=69,raw_words=69,raw_word_differences=6,frame=48,guards=6,bindings=6,raw_neighbors=rn,neighbors=pn,all_pools_unchanged=True,diagnostics='',qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(after_csv.read_bytes()),guard_predecessor_sha256=GUARD_SHA,strict_changed_bytes=delta,strict_exclusions=0,metadata_permutations=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,caller_census=census(root))
    (out/'proposed-owner.c').write_text(ns,encoding='utf-8');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
