"""Owner-pair updater: checked scheduling roles before any matching credit."""
import hashlib,struct
from tools.experiments import game_owner_paired_effect_candidates as candidate
from tools.pad_generated_object import parse_object
sha=lambda b:hashlib.sha256(b).hexdigest()
BUILD=candidate.BUILD
ELF,GUARDS,MAKE='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/Makefile'
ROM_IMAGE='conker/conker.us.bin'

def function_blob(obj,index=0):
    t,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def plus(a,b):
    if isinstance(b,int)and b==0:return a
    if isinstance(a,int)and a==0:return b
    if isinstance(a,int)and isinstance(b,int):return(a+b)&0xFFFFFFFF
    if isinstance(a,int):a,b=b,a
    if isinstance(b,int):
        if isinstance(a,tuple)and a[0]in('ptr','add'):return(*a[:-1],a[-1]+b)
        return('add',a,b)
    return('uadd32',*sorted((a,b),key=repr))

def expr(op,a,b):
    if isinstance(a,int)and isinstance(b,int):
        return {'sub32':lambda:(a-b)&0xFFFFFFFF,'and32':lambda:a&b,'or32':lambda:a|b,'sll32':lambda:a<<b&0xFFFFFFFF,'srl32':lambda:a>>b,'slt32':lambda:int(a<b)}[op]()
    return(op,*sorted((a,b),key=repr))if op in('and32','or32','fadd32','fmul32')else(op,a,b)

class Roles:
    """Small straight-line verifier; unsupported instructions fail closed.

    The live caller record and its owner objects are disjoint from this callee's
    private frame, as required for valid C objects. Public accesses stay ordered;
    independent private writes compare by their final address/width/value. FP
    commutation is a value proof for finite intermediates, not FCSR fault parity.
    """
    def __init__(self,index=0,normalized=False):
        self.r=[('GPR',i)for i in range(32)];self.r[0]=0;self.r[16]=('ptr','record',0);self.r[18]=('ptr','record',4*index);self.r[19]=self.r[20]=index;self.r[29]=('ptr','stack',0);self.r[2]=6*index;self.r[3]=('owner',index)
        self.f=[('FPR',i)for i in range(32)];self.f[0]=('fraction',);self.f[20]=('speed',);self.f[22]=('angle',);self.f[24]=('quarter',);self.f[26]=0 if normalized else('threshold',);self.f[28]=('threshold',)if normalized else 0
        self.events=[];self.private={};self.calls=[];self.branches=[]
    def read(self,p,n,signed=False):
        if isinstance(p,tuple)and p[:2]==('ptr','stack'):return self.private.get((p,n),('private-input',p,n))
        v=('read',len(self.events),p,n);self.events.append(('R',p,n));return('signed16',v)if signed else v
    def write(self,p,v,n):
        if n<4:v=expr('and32',v,(1<<(8*n))-1)
        if isinstance(p,tuple)and p[:2]==('ptr','stack'):self.private[p,n]=v
        else:self.events.append(('W',p,n,v))
    def run(self,words,start,stop,refs=None):
        refs={}if refs is None else refs
        for i in range(start,stop):
            w=words[i];op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768;binding=refs.get(4*i)
            if op==9:self.r[rt]=('global',binding[0][1])if binding else plus(self.r[rs],imm)
            elif op==15:self.r[rt]=('HI',binding[0][1])if binding else(w&65535)<<16
            elif op in(12,13):self.r[rt]=expr('and32'if op==12 else'or32',self.r[rs],w&65535)
            elif op==10:self.r[rt]=expr('slt32',self.r[rs],imm)
            elif op==0 and fn in(0,2):self.r[rd]=expr('sll32'if fn==0 else'srl32',self.r[rt],fd)
            elif op==0 and fn==33:self.r[rd]=plus(self.r[rs],self.r[rt])
            elif op==0 and fn==35:self.r[rd]=expr('sub32',self.r[rs],self.r[rt])
            elif op==0 and fn==37:self.r[rd]=self.r[rs]if self.r[rt]==0 else self.r[rt]if self.r[rs]==0 else expr('or32',self.r[rs],self.r[rt])
            elif op in(35,36,33,49):
                p=('global',binding[0][1])if binding else plus(self.r[rs],imm);n=1 if op==36 else 2 if op==33 else 4;v=self.read(p,n,op==33)
                if op==49:self.f[rt]=v
                else:self.r[rt]=v
            elif op in(40,41,43,57):self.write(plus(self.r[rs],imm),self.f[rt]if op==57 else self.r[rt],{40:1,41:2,43:4,57:4}[op])
            elif op==17:
                if rs==4:self.f[rd]=('int-bits',self.r[rt])if self.r[rt]!=0 else 0
                elif rs==20 and fn==32:
                    v=self.f[rd];assert v[0]=='int-bits';self.f[fd]=('signed-to-float32',v[1])
                else:
                    assert rs==16 and fn in(0,2),(i,hex(w));self.f[fd]=expr('fadd32'if fn==0 else'fmul32',self.f[rd],self.f[rt])
            elif op==3:self.calls.append((i,refs[4*i][0][1]))
            elif op==5:self.branches.append((i,self.r[rs],self.r[rt],i+1+imm))
            else:raise ValueError('Unsupported role instruction '+repr((i,hex(w))))
            self.r[0]=0
        return self

def audit_schedule(raw,updated,raw_refs,updated_refs):
    a,b=(list(struct.unpack('>214I',p))for p in(raw,updated));t=candidate.TARGETS[0]
    if {4*i:(x,y)for i,(x,y)in enumerate(zip(a,b))if x!=y}!=t['patches']:raise ValueError('Owner-pair complete schedule changed')
    changed={i for i,(x,y)in enumerate(zip(a,b))if x!=y};covered=set(range(20,25))|{46,47,49,69,174,176,177}|set(range(120,169))|set(range(179,197))
    if changed-covered:raise ValueError('Owner-pair changes outside proved regions')
    # The original saves and restores the same physical registers. Renaming the
    # two invariant FP roles applies only between that identical save/restore.
    if a[:17]!=b[:17]or a[197:]!=b[197:]or a[0]!=0x27BDFEE0:raise ValueError('Owner-pair frame/saved-register extent changed')
    prefix=[Roles().run(a,17,27,raw_refs),Roles(normalized=True).run(b,17,27,updated_refs)]
    x,y=prefix
    if x.events!=y.events or any(x.r[r]!=y.r[r]for r in(1,19,21,23,29))or(x.f[26],x.f[28])!=(y.f[28],y.f[26]):raise ValueError('Owner-pair invariant setup is not closed')
    # Both branch outcomes preserve the same timer decision and coordinate
    # index. On expiry S4 is copied before the first call's transfer. Otherwise
    # the raw S4 copy is dead before restoration, with no intervening helper.
    if a[46:50]!=[0x07210081,0x0260A025,0x0C000000,0]or b[46:50]!=[0x07230082,0x00131080,0x0C000000,0x0260A025]:raise ValueError('Owner-pair branch-delay proof changed')
    if a[174]!=0xA0730004 or b[174]!=0xA0740004 or a[176:178]!=[0x00141080,0x00541023]or b[176:178]!=[0x00131080,0x00531023]:raise ValueError('Owner-pair index lifetime changed')
    if a[69]!=0x46002182 or b[69]!=0x46040182:raise ValueError('Owner-pair speed multiply order changed')
    obligations=[]
    for index in(0,1):
        x=Roles(index).run(a,120,169,raw_refs);y=Roles(index,True).run(b,120,169,updated_refs)
        if (x.events,x.private,x.r[4:8],x.calls)!=(y.events,y.private,y.r[4:8],y.calls):raise ValueError('Owner-pair factory inputs differ: '+repr((x.events,y.events,x.private,y.private,x.r[4:8],y.r[4:8])))
        if x.calls!=[(167,'func_15147DA0')]:raise ValueError('Owner-pair factory transfer changed')
        obligations.append(dict(index=index,ordered_reads=len(x.events),private_writes=len(x.private),arguments=15))
        x=Roles(index).run(a,179,197);y=Roles(index,True).run(b,179,197)
        if (x.events,x.branches,x.r[19])!=(y.events,y.branches,y.r[19])or x.r[19]!=index+1:raise ValueError('Owner-pair coordinate/index closure changed')
    return dict(frame=288,body_words=214,guards=len(t['patches']),invariant_FP_roles_permuted=True,branch_delay_and_dead_S4_lifetime_closed=True,all15_factory_arguments_and_whole_private_write_map_equal=True,ordered_public_reads_and_coordinate_stores_equal=True,indices=[0,1],induction='zero initialization; unsigned-byte increment; continue below two',finite_FP_value_domain=True,private_frame_disjoint_from_live_input_objects=True,raw_fault_or_scratch_register_identity_not_claimed=True,obligations=obligations)

def derive(raw,bindings,index=0):
    t=candidate.TARGETS[index]
    if index!=0 or len(raw)!=856 or sha(raw)!=t['raw_sha256']or bindings!=t['bindings']:raise ValueError('Owner-pair raw body/bindings changed')
    words=list(struct.unpack('>214I',raw))
    for p,(old,new)in t['patches'].items():
        if words[p//4]!=old:raise ValueError('Owner-pair expected schedule word changed')
        words[p//4]=new
    moved=dict(bindings);moved[84],moved[92]=moved[92],moved[84];updated=struct.pack('>214I',*words);audit_schedule(raw,updated,bindings,moved);return updated,moved

import csv,io,json,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_actor_height_effect_match as metadata
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import paired_diagnostics
from tools.experiments.game_record_address_relocator_match import dependent_sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
BASELINE_SHA='31b57da8521d3c4694656926e081fc2adc198ee3cf32292a6855c9e5c20d2266'
GUARD_SHA='07f10c774595f08f62fd8b543daa18417a7d6f175d623720f77446be2ab0132e'
LINKER='conker/build/conker.ld'
METADATA_GROUPS=((('D_800A7440','D_8009E720'),(1,0)),)

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Owner-pair guard predecessor changed')
    fields=next(csv.reader(io.StringIO(before.decode())))
    if any(r['function']==candidate.TARGETS[0]['function']for r in csv.DictReader(io.StringIO(before.decode()))):raise ValueError('Owner-pair guards already present')
    t=candidate.TARGETS[0];raw_refs=t['bindings'];moved=dict(raw_refs);moved[84],moved[92]=moved[92],moved[84];stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in before else'\n')
    for at,(old,new)in sorted(t['patches'].items()):
        join=lambda rows:';'.join(k+':'+n for k,n in rows)or'-'
        writer.writerow(dict(filename=t['owner'],function=t['function'],offset='0x%X'%at,expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations=join(raw_refs.get(at,[])),replacement_relocations=join(moved.get(at,[])),note='Normalize proved owner-pair register roles and private setup schedule',omit='false'))
    return before+stream.getvalue().encode()

def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text(encoding='utf-8'))
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Owner-pair discovery changed: '+n)
        names=set(initial)|{'conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/undefined_syms_auto.txt','conker/conker.us.yaml','conker/retail_layout.us.txt'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,GUARDS,MAKE,'conker/build/conker.us.bin','graphify-out/graph.json'}|{t[k]for t in candidate.TARGETS for k in('source','object')}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Owner-pair protected input changed: '+n)
    hp=out/'match-include-sha256.json'
    if not hp.exists():
        headers={p.relative_to(root).as_posix():sha(p.read_bytes())for p in sorted((root/'conker/include').rglob('*.h'))}
        for n in headers:p=out/'match-includes'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        hp.write_text(json.dumps(headers,indent=2)+'\n',encoding='utf-8')
    headers=json.loads(hp.read_text(encoding='utf-8'))
    for n,h in headers.items():
        if sha((root/n).read_bytes())!=h or sha((out/'match-includes'/n).read_bytes())!=h:raise ValueError('Owner-pair include changed: '+n)
    return len(values)+len(headers)

def assemble_owner(root,out,obj,index,label,guards):
    t=candidate.TARGETS[index];p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(t['owner']+'.c.o')
    emit=pad_generated_object.emit_padded_assembly if index==0 else pad_c_object.emit_padded_assembly
    s.write_text(emit(obj,root/t['assembly'],filename=t['owner'],word_patches_path=guards,rodata_symbol=candidate.RODATA_SYMBOL),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def pools(before,after,padded=False):
    a,b=alloc_pools(before),alloc_pools(after)
    if not padded:
        a,b=dict(a),dict(b);x,y=(bytearray(d['.reginfo'][4])for d in(a,b))
        if(struct.unpack_from('>I',x)[0],struct.unpack_from('>I',x,8)[0],struct.unpack_from('>I',y)[0],struct.unpack_from('>I',y,8)[0])!=(0xA31FFFFE,0xF0DF1,0xE3FFFFFE,0x3FFF0FF1):raise ValueError('Owner-pair raw register masks changed')
        x[:4]=y[:4];x[8:12]=y[8:12]
        if x!=y:raise ValueError('Owner-pair other reginfo fields changed')
        a['.reginfo']=(*a['.reginfo'][:4],bytes(x),a['.reginfo'][5])
    if a!=b:raise ValueError('Owner-pair whole allocatable pools changed')
    x,y=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if x is None and y is None:return
    if x is None or y is None or x[0][:4]+x[0][5:]!=y[0][:4]+y[0][5:]:raise ValueError('Owner-pair options header changed')
    xx,yy=bytearray(x[1]),bytearray(y[1])
    if not padded:
        if(struct.unpack_from('>I',xx,8)[0],struct.unpack_from('>I',xx,16)[0],struct.unpack_from('>I',yy,8)[0],struct.unpack_from('>I',yy,16)[0])!=(0xA31FFFFE,0xF0DF1,0xE3FFFFFE,0x3FFF0FF1):raise ValueError('Owner-pair options register masks changed')
        xx[8:12]=yy[8:12];xx[16:20]=yy[16:20]
    if xx!=yy:raise ValueError('Owner-pair options payload changed')


def link_image(root,out,owners,label):
    linker=(out/'match-frozen'/LINKER).read_text(encoding='utf-8')
    for t,o in zip(candidate.TARGETS,owners):
        old=t['object'].removeprefix('conker/');new=o.relative_to(root/'conker').as_posix()
        if linker.count(old)!=1:raise ValueError('Owner-pair link owner reference changed')
        linker=linker.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);script=d/'conker.ld';script.write_text(linker,encoding='utf-8');elf=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True);return elf

def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Owner-pair predecessor image changed')
    expected=bytearray(before);sizes={t['function']:t['words']*4 for t in candidate.TARGETS}
    for t in candidate.TARGETS:
        size=4*t['words'];at=elf_slot_offset(before,t['entry'],size);expected[at:at+size]=rom[t['rom']:t['rom']+size]
        rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
        if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Owner-pair predecessor symbol changed')
        struct.pack_into('>I',expected,rows[0][0]+8,size)
    named={n:p for p,n,f,s in symbol_rows(before)}
    groups=tuple((named[names[0]],names,order)for names,order in METADATA_GROUPS)
    with patch.object(metadata,'METADATA_GROUPS',groups):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Owner-pair literal whole image differs: '+repr((len(expected),len(after),len(diff),diff[:32])))
    if Counter((n,f[1],sizes.get(n,f[2]),*f[3:])for p,n,f,s in symbol_rows(before))!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Owner-pair symbol definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);mb=(root/MAKE).read_text(encoding='utf-8');ma=mb;mi=False;assert mb==(out/'match-frozen'/MAKE).read_text(encoding='utf-8');(out/'proposed-Makefile').write_text(ma,encoding='utf-8');rom=(root/ROM_IMAGE).read_bytes();owners=[[],[]];compacts=[];reports=[];phases=[]
    beforeguards=(out/'match-frozen'/GUARDS).read_bytes();afterguards=guard_manifest(beforeguards);gp=[out/'predecessor-guards.csv',out/'proposed-guards.csv'];gp[0].write_bytes(beforeguards);gp[1].write_bytes(afterguards)
    for i,t in enumerate(candidate.TARGETS):
        before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'),i);phases.append(installed)
        if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Owner-pair reconstructed predecessor changed')
        old,od=candidate.compile_owner(root,out,before,'match-predecessor-%d'%i);new,nd=candidate.compile_owner(root,out,after,'match-qualified-%d'%i);diagnostics=paired_diagnostics(od,nd,t['owner']);raw_neighbors=same_functions(old,new,(t['function'],));pools(old,new)
        raw,b=function_blob(new,i);normalized,nb=derive(raw,b,i);symbols={n:int(n.split('_')[1],16)for rr in nb.values()for _,n in rr}
        if bound_blob(normalized,nb,symbols)!=list(struct.unpack_from('>%dI'%t['words'],rom,t['rom'])):raise ValueError('Owner-pair derived complete body differs')
        oo=assemble_owner(root,out,old,i,'match-predecessor-owner-%d'%i,gp[0]);no=assemble_owner(root,out,new,i,'match-qualified-owner-%d'%i,gp[1]);padded_neighbors=same_functions(oo,no,(t['function'],));pools(oo,no,True)
        if function_blob(no,i)!=(normalized,nb):raise ValueError('Owner-pair padder differs')
        if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live lookup owner differs')
        owners[0].append(oo);owners[1].append(no);compacts.append(new);(out/('proposed-%d.c'%i)).write_text(after,encoding='utf-8');reports.append(dict(function=t['function'],words=t['words'],frame=t['frame'],guards=len(t['patches']),bindings=len(b),raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes())))
    if len(set(phases))!=1:raise ValueError('Owner-pair source phases differ')
    installed=phases[0]
    if(root/GUARDS).read_bytes()!=(afterguards if installed else beforeguards):raise ValueError('Owner-pair guard phase differs')
    oe=link_image(root,out,owners[0],'pair-predecessor-image');ne=link_image(root,out,owners[1],'pair-qualified-image');previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Live lookup ELF differs')
    delta=strict_image(previous,updated,rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or set(changed)!={t['function']for t in candidate.TARGETS}:raise ValueError('Owner-pair complete function/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner-pair protected data differs')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=reports,qualified_elf_sha256=sha(updated),guard_sha256=sha(afterguards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return dict(report=report,predecessor_owners=owners[0],qualified_owners=owners[1],qualified_compacts=compacts,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
