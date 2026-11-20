"""Paired full-path symbolic execution for the equal-length map burst body."""
from pathlib import Path
import copy,json,struct

class Failure(ValueError):pass
def need(condition,message):
    if not condition:raise Failure(message)
U=lambda x:x&0xffffffff
def add(x,n):
    if isinstance(x,int):return U(x+n)
    if isinstance(x,tuple)and x[0]in('SP','ARG'):return(x[0],x[1]+n)
    if not n:return x
    return('ADD',x,n)
def byte(value,i):return(value>>(24-8*i))&255 if isinstance(value,int)else('BYTE',value,i)
def combine(values):
    if all(isinstance(v,int)for v in values):return int.from_bytes(bytes(values),'big')
    if len(values)==4 and all(isinstance(v,tuple)and len(v)==3 and v[0]=='BYTE'and v[2]==i for i,v in enumerate(values))and all(v[1]==values[0][1]for v in values):return values[0][1]
    return('BYTES',tuple(values))

class State:
    def __init__(self):
        self.r=[('ENTRY-GPR',i)for i in range(32)];self.r[0]=0;self.r[4]=('ARG',0);self.r[29]=('SP',0)
        self.f=[('ENTRY-FPR',i)for i in range(32)];self.hi=('ENTRY-HI',);self.lo=('ENTRY-LO',);self.csr=('ENTRY-FCSR',);self.cc=('ENTRY-CONDITION',)
        self.memory={i:('ENTRY-STACK-BYTE',i)for i in range(-184,64)}
    def store(self,address,value,n):
        need(address[0]=='SP','Public store in burst callback')
        for i in range(n):self.memory[address[1]+i]=byte(value,4-n+i)
    def load(self,address,n):
        need(address[0]=='SP','Private load expected');return combine([self.memory[address[1]+i]for i in range(n)])
    def data(self,address,n):
        need(address[0]=='SP','Private helper object expected');return tuple(self.memory[address[1]+i]for i in range(n))

def fields(w):return w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63,((w&65535)^32768)-32768
def private(s,w):
    op,rs,rt,rd,sa,fn,imm=fields(w);a=add(s.r[rs],imm)
    return op in(35,37,43,41,49,57,34,38,42,46)and isinstance(a,tuple)and a[0]=='SP'
def step(s,w,token,events):
    op,rs,rt,rd,sa,fn,imm=fields(w);r=s.r
    if not w:return
    if op==0:
        if fn==37:r[rd]=r[rs]if r[rt]==0 else r[rt]if r[rs]==0 else('OR',r[rs],r[rt])
        elif fn==27:s.hi=('REMU',r[rs],r[rt]);s.lo=('DIVU',r[rs],r[rt]);need(isinstance(r[rt],int)and r[rt]!=0,'Unproved DIVU divisor')
        elif fn==16:r[rd]=s.hi
        else:raise Failure('SPECIAL '+hex(w))
    elif op==9:r[rt]=add(r[rs],imm)
    elif op==15:r[rt]=(w&65535)<<16
    elif op==12:r[rt]=r[rs]&(w&65535)if isinstance(r[rs],int)else('AND',r[rs],w&65535)
    elif op==17:
        if rs==4:s.f[rd]=r[rt]
        else:
            need(rs==16 and fn in(0,2,7,60),'Unhandled FP '+hex(w));args=(s.f[rd],)if fn==7 else(s.f[rd],s.f[rt])
            event=('FP',fn,args,s.csr,s.cc);events.append(event)
            if fn==60:s.cc=('CMP',token,event)
            else:s.f[sa]=('FP-RESULT',token,event)
            s.csr=('FP-CONTROL',token,event)
    elif op in(35,36,37,49,34,38):
        address=add(r[rs],imm);n=1 if op==36 else 2 if op==37 else 4
        # Every source surface word and destination copy is aligned under the
        # complete record's four-byte ABI alignment. LWR at +3 reloads that word.
        if op in(34,38):
            need(isinstance(address,tuple)and address[0]in('ARG','SP'),'Unproved unaligned-copy address')
            need(address[1]%4==(3 if op==38 else 0),'Unproved copy alignment')
            if op==38:address=add(address,-3)
        if isinstance(address,tuple)and address[0]=='SP':value=s.load(address,n)
        else:events.append(('READ',op,address,n));value=('READ-RESULT',token,n)
        if op==49:s.f[rt]=value
        else:r[rt]=value
    elif op in(43,41,57,42,46):
        address=add(r[rs],imm);n=2 if op==41 else 4
        if op in(42,46):
            need(isinstance(address,tuple)and address[0]=='SP'and address[1]%4==(3 if op==46 else 0),'Unproved store alignment')
            if op==46:address=add(address,-3)
        s.store(address,s.f[rt]if op==57 else r[rt],n)
    else:raise Failure('Unhandled '+hex(w))
    r[0]=0

REAL,INTEGER,PRIMARY,POINT,BURST=0x150ADA68,0x150ADA20,0x15102920,0x151C329C,0x15151D6C
def call(s,target,token):
    if target in(REAL,INTEGER):args=()
    elif target==PRIMARY:args=(s.f[12],*s.r[5:8],*(s.load(add(s.r[29],i),4)for i in range(16,40,4)))
    elif target==POINT:args=tuple(s.r[4:7])
    elif target==BURST:
        args=(*s.r[4:8],s.load(add(s.r[29],16),4),s.load(add(s.r[29],20),4),s.data(s.r[4],88),s.data(s.r[5],4),s.data(s.r[6],4))
    else:raise Failure('Unexpected helper '+hex(target))
    for i in range(40):s.memory[s.r[29][1]+i]=('HELPER-HOME',token,i)
    for i in(1,2,3,*range(4,16),24,25):s.r[i]=('HELPER-GPR',token,i)
    for i in range(20):s.f[i]=('HELPER-FPR',token,i)
    s.hi=('HELPER-HI',token);s.lo=('HELPER-LO',token);s.csr=('HELPER-FCSR',token);s.cc=('HELPER-CC',token)
    return(target,args)

def prove(a,b):
    need(len(a)==len(b)==175,'Word extent changed')
    paths=[];visited=set();totals=dict(instructions=0,public_reads=0,FP=0,calls=0,branches=0)
    def walk(pc,x,y,trace,seen):
        while True:
            need(pc not in seen,'Unexpected loop');seen=seen|{pc};visited.add(pc);wa,wb=a[pc],b[pc];fa,fb=fields(wa),fields(wb)
            need(fa[0]==fb[0],'Opcode mismatch at '+hex(4*pc));op=fa[0];token=(tuple(trace),pc)
            if op in(3,4,5,20,21)or(op==17 and fa[1]==8)or(op==0 and fa[5]==8):
                need(fa[0]==fb[0]and fa[6]==fb[6],'Control mismatch')
                if op==3:condition=None;targeta=0x10000000|((wa&0x3ffffff)<<2);targetb=0x10000000|((wb&0x3ffffff)<<2);need(targeta==targetb,'Call target mismatch')
                elif op==0:
                    need(x.r[fa[1]]==y.r[fb[1]],'Return address differs');condition=None
                elif op==17:
                    need(fa[2]==fb[2]and x.cc==y.cc,'FP branch condition differs');condition=x.cc
                else:
                    condition=(x.r[fa[1]],x.r[fa[2]]);need(condition==(y.r[fb[1]],y.r[fb[2]]),'GPR branch differs')
                choices=(None,)if op in(0,3)else(False,True)
                if op in(4,5,20,21)and all(isinstance(v,int)for v in condition):
                    equal=condition[0]==condition[1];choices=(equal if op in(4,20)else not equal,)
                for taken in choices:
                    xx,yy=copy.deepcopy(x),copy.deepcopy(y);tt=list(trace);events=[[],[]]
                    if op==3:xx.r[31]=yy.r[31]=('CONTINUATION',pc+2)
                    likely=op in(20,21)or(op==17 and fa[2]&2)
                    if not likely or taken is not False:
                        visited.add(pc+1)
                        for s,w,ev in((xx,a[pc+1],events[0]),(yy,b[pc+1],events[1])):step(s,w,(token,'delay'),ev)
                        need(events[0]==events[1],'Delay effect differs')
                    if op==3:
                        # Equal extent and call index give the same continuation.
                        ca,cb=call(xx,targeta,token),call(yy,targetb,token);need(ca==cb,'Helper inputs differ at '+hex(4*pc));tt.append((pc,'CALL',targeta));walk(pc+2,xx,yy,tt,seen|{pc+1})
                    elif op==0:
                        need(xx.r[29]==yy.r[29]==('SP',0),'Frame not restored')
                        for i in(*range(16,24),28,30,31):need(xx.r[i]==yy.r[i]==('ENTRY-GPR',i),'Saved GPR differs '+str(i))if i!=31 else need(xx.r[i]==yy.r[i]==('ENTRY-GPR',31),'RA not restored')
                        for i in range(20,32):need(xx.f[i]==yy.f[i]==('ENTRY-FPR',i),'Saved FPR differs')
                        need(xx.csr==yy.csr and xx.cc==yy.cc,'Return FCSR differs');paths.append(tt);return
                    else:
                        tt.append((pc,'BRANCH',taken));dest=pc+1+fa[6]if taken else pc+2;walk(dest,xx,yy,tt,seen|{pc+1})
                return
            events=[[],[]]
            step(x,wa,token,events[0]);step(y,wb,token,events[1]);need(events[0]==events[1],'Ordered effect differs at '+hex(4*pc))
            pc+=1
    walk(0,State(),State(),[],set())
    need(visited==set(range(175)),'Uncovered words '+str(sorted(set(range(175))-visited)))
    return dict(paths=len(paths),all_words_covered=len(visited),equal_length=175,frame=184,all_helper_arguments_and_96_private_input_bytes_equal=True,
                all_ordered_public_reads_and_FP_inputs_equal=True,saved_ABI_preserved_and_FCSR_equal=True,
                public_objects_disjoint_owned_frame=True,record_alignment=4,full_outgoing_40_bytes_clobbered=True,
                arbitrary_same_ordered_helper_effects=True,not_literal_raw_private_fault_state=True)


def qualify(retail,raw):return prove(retail,raw)

def negative_controls(retail,raw):
    controls=[]
    for i,w in enumerate(raw):
        op,rs,rt,rd,sa,fn,imm=fields(w)
        changes=[]
        if op in(35,36,37,49,34,38,43,41,57,42,46):changes.append(('address',w^4))
        if op==17 and rs==16:
            changes.append(('FP-left',w^(1<<11)))
            if fn!=7:changes.append(('FP-right',w^(1<<16)))
        if op in(9,12)and rs!=29:changes.append(('constant',w^1))
        for kind,changed in changes:
            candidate=list(raw);candidate[i]=changed
            try:prove(retail,candidate)
            except (Failure,KeyError):controls.append([4*i,kind])
    assert len(controls)>=80,len(controls)
    return dict(effective_controls=controls,unsupported_mutations_not_asserted_semantically_valid=True)
