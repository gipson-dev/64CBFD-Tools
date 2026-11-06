"""Closed saved-register cycle and strict owner/image qualification."""
import csv
import hashlib
import io
import json
import struct
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_group_record_actor_dispatch_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_path_heading_turn_match import padded_pools
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object', pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION, FILENAME, SOURCE, ASM = candidate.FUNCTION, candidate.OWNER, candidate.SOURCE, candidate.ASM
ENTRY, ROM, WORDS, BUILD = candidate.ENTRY, candidate.ROM, candidate.WORDS, candidate.BUILD
OBJECT = 'conker/build/src/game/generated_49D30.c.o'
ELF, GUARDS, MAKE, LINKER = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv', 'conker/Makefile', 'conker/build/conker.ld'
ROM_IMAGE = 'conker/conker.us.bin'
BASELINE_SHA = 'ccb55cd901f68c8b8a148bc1ab233a833fe693035b05f8ecc764bbd4d07ee974'
OLD_GUARD_SHA = 'd4dffc34fb8b6371d8090bffe66ef9c93b5216cb347facd74e694cb8e15cf833'
RAW_SHA = '4ece5a2ee26996658238e80a5a40897e3c452687f9a8daf70ed81be0d1f4d2f7'
BINDINGS = {48:[('R_MIPS_HI16','D_800C363A')],52:[('R_MIPS_LO16','D_800C363A')],76:[('R_MIPS_HI16','D_800C35D0')],80:[('R_MIPS_LO16','D_800C35D0')],84:[('R_MIPS_HI16','D_800C35F0')],96:[('R_MIPS_LO16','D_800C35F0')],88:[('R_MIPS_HI16','D_800C35C8')],92:[('R_MIPS_LO16','D_800C35C8')],184:[('R_MIPS_26','func_15083E90')],204:[('R_MIPS_26','func_1502178C')]}
RENAME = {22:19, 23:20, 30:21, 19:22, 21:23, 20:30}
sha = lambda b: hashlib.sha256(b).hexdigest()

def symbols():
    return dict(D_800C363A=0x800c363a,D_800C35D0=0x800c35d0,D_800C35C8=0x800c35c8,D_800C35F0=0x800c35f0,func_15083E90=0x15083e90,func_1502178C=0x1502178c)

def function_blob(obj):
    t,f,r=parse_object(obj);v=f[FUNCTION];a,n=v['value'],v['size']
    return t[a:a+n],{p-a:b for p,b in r.items() if a<=p<a+n}

def checked(raw, bindings, truth=None):
    if len(raw)!=280 or bindings!=BINDINGS: raise ValueError('Group-record size or relocation ownership changed')
    if truth is None:
        if sha(raw)!=RAW_SHA: raise ValueError('Group-record compiler body changed')
    elif bound_blob(raw,bindings,symbols())!=list(struct.unpack('>70I',truth)):
        raise ValueError('Group-record normalized body differs')

def renamed(word):
    op,rs,rt,rd=word>>26,word>>21&31,word>>16&31,word>>11&31
    if op not in (0,3,4,5,6,9,15,20,21,35,36,37,43): raise ValueError('Unexpected register-cycle instruction')
    if op==3: return word
    value=(word&~0x03ff0000)|(RENAME.get(rs,rs)<<21)|(RENAME.get(rt,rt)<<16)
    if op==0: value=(value&~0xf800)|(RENAME.get(rd,rd)<<11)
    if op in (35,43) and rs==29 and rt in RENAME:
        reg=RENAME[rt];home=0x38 if reg==30 else 0x18+4*(reg-16)
        value=(value&0xffff0000)|home
    return value

def scheduling(raw, bindings):
    checked(raw,bindings);w=list(struct.unpack('>70I',raw));origins=list(range(70))
    origins[4:12]=[7,6,8,4,5,9,10,11]
    origins[62:68]=[65,66,67,62,64,63]
    rows=[];ledger=[];output=[]
    for slot,origin in enumerate(origins):
        value=renamed(w[origin]);rel=bindings.get(slot*4,[])
        if rel!=bindings.get(origin*4,[]): raise ValueError('Cycle moved a relocation')
        reason='Retain the same semantic role through the closed six-register allocation cycle'
        if slot!=origin: reason='Order the original saved-register access in its retail physical-register home'
        if value!=w[slot]:
            text=';'.join(k+':'+s for k,s in rel) or '-'
            rows.append(dict(filename=FILENAME,function=FUNCTION,offset='0x%03X'%(slot*4),expected='0x%08X'%w[slot],replacement='0x%08X'%value,expected_relocations=text,replacement_relocations=text,note=reason,insert_after='',insert_after_relocations='',omit='false'))
        ledger.append(dict(output=slot,source=origin,reason=reason if value!=w[slot] else 'Unmodified compiler word'))
        output.append(value)
    if len(rows)!=21: raise ValueError('Register-cycle closure changed')
    return struct.pack('>70I',*output),bindings,rows,ledger

def proposed_guards(before,rows):
    if sha(before)!=OLD_GUARD_SHA: raise ValueError('Group-record guard predecessor changed')
    nl='\r\n' if b'\r\n' in before else '\n';fields=csv.DictReader(before.decode().splitlines()).fieldnames
    s=io.StringIO(newline='');writer=csv.DictWriter(s,fieldnames=fields,lineterminator=nl);writer.writerows(rows)
    return before+s.getvalue().encode()

def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        values=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in values.items():
            if sha((root/n).read_bytes())!=h: raise ValueError('Discovery input changed: '+n)
        names=set(values)|{'conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.ld'}
        names.update('ido/ido5.3_recomp/'+n for n in ('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes()) for n in sorted(names)}
        for n in values:
            q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((root/n).read_bytes())
        p.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(p.read_text());allowed={SOURCE,OBJECT,ELF,'conker/build/conker.us.bin','graphify-out/graph.json',GUARDS}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h: raise ValueError('Frozen input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h: raise ValueError('Protected input changed: '+n)
    return len(values)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=280: raise ValueError('Image predecessor differs')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,280);expected[at:at+280]=truth
    rows=[(p,f) for p,n,f,s in symbol_rows(before) if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12): raise ValueError('Predecessor symbol differs')
    struct.pack_into('>I',expected,rows[0][0]+8,280)
    if bytes(expected)!=after: raise ValueError('Literal whole-image closure failed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    frozen=freeze(root,out);bs,ns,installed=candidate.source_states((root/SOURCE).read_text())
    if bs!=(out/'match-frozen'/SOURCE).read_text(): raise ValueError('Source predecessor differs')
    old,od=candidate.compile_owner(root,out,bs,'match-predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'match-qualified-compact')
    if od or nd: raise ValueError('Group-record owner introduced diagnostics')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+280];raw,b=function_blob(new);checked(raw,b)
    normal,nb,rows,ledger=scheduling(raw,b);checked(normal,nb,truth)
    guards=proposed_guards((out/'match-frozen'/GUARDS).read_bytes(),rows);(out/'proposed-guards.csv').write_bytes(guards)
    if (root/GUARDS).read_bytes()!=(guards if installed else (out/'match-frozen'/GUARDS).read_bytes()): raise ValueError('Live guard history differs')
    rn=same_functions(old,new,(FUNCTION,))
    if rn!=56 or alloc_pools(old)!=alloc_pools(new): raise ValueError('Raw neighbors or pools changed')
    oo=assemble_owner(root,out,old,'match-predecessor-owner',out/'match-frozen'/GUARDS)
    no=assemble_owner(root,out,new,'match-qualified-owner',out/'proposed-guards.csv');checked(*function_blob(no),truth)
    if (no if installed else oo).read_bytes()!=(root/OBJECT).read_bytes(): raise ValueError('Live owner differs')
    if same_functions(oo,no,(FUNCTION,))!=56 or padded_pools(oo)!=padded_pools(no): raise ValueError('Padded neighbors or pools differ')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,oo,'match-predecessor-image');ne=harness.link_image(root,out,no,'match-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if (after if installed else before)!=(root/ELF).read_bytes(): raise ValueError('Live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump')
    if set(a)!=set(b) or aa!=bb or [n for n in b if a[n]!=b[n]]!=[FUNCTION] or b[FUNCTION]!=list(struct.unpack('>70I',truth)): raise ValueError('Function/address closure differs')
    data=audit_layout(ne,root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0): raise ValueError('Protected data differs')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,raw_words=70,words=70,frame=64,guards=21,omissions=0,raw_word_differences=21,normalized_differences=0,raw_neighbors=rn,neighbors=56,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(guards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=[FUNCTION],protected_data=data,unchanged_existing_warnings=0)
    (out/'proposed-owner.c').write_text(ns);(out/'guard-origin-ledger.json').write_text(json.dumps(dict(rows=rows,origins=ledger),indent=2)+'\n');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)

if __name__=='__main__': print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
