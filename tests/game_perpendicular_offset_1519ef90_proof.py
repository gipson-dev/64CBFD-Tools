"""Symbolic full-path public/FP proof, independent of the guard mapping.

Public reads may vary at every access, and calls may change public memory,
incoming mode homes, caller-saved state and FCSR. Providers cannot inspect
implementation PCs or unpassed locals. Private locals may have different
homes; output objects do not alias the callee's private stack. Callers' output
aliases are qualified separately. No raw fault-register identity is claimed.
"""
from copy import deepcopy
from tools.tests import game_record_initializer_150169a0_proof as e

class Terms:
    def __init__(self):self.values={}
    def term(self,*values):
        if values not in self.values:self.values[values]=('EXPRESSION',len(self.values))
        return self.values[values]

class State(e.State):
    def __init__(self):
        super().__init__('common','offset');self.mem={};self.r[29]=('STACK',0);self.r[31]=('RETURN',)
        self.r[4],self.r[5],self.r[6]=('RECORD',),('MODE_WORD',),('OUTPUT',)
        for i in (*range(16,24),28,30):self.r[i]=('ENTRY',i)
        self.fp_condition=None;self.fp=[]
    def store(self,address,size,value):
        if e.tagged(address,'STACK'):
            assert size in(1,4) and (size==1 or address[1]%4==0)
            self.mem[address[1],size]=e.bitop('AND',value,(1<<(8*size))-1)
        else:super().store(address,size,value)
    def load(self,address,size,pool):
        if not e.tagged(address,'STACK'):return super().load(address,size,pool)
        offset=address[1]
        if(offset,size) in self.mem:return self.mem[offset,size]
        value=self.mem.get((offset&~3,4),('PRIVATE_ENTRY',offset&~3))
        if size==1:
            assert offset%4==3
            return e.bitop('AND',value,255)
        assert size==4 and offset%4==0
        return value

class Program(e.Program):
    def __init__(self,words,terms):super().__init__(words,b'',0x1519ef90);self.terms=terms
    def step(self,s,w):
        op,fmt,fn=w>>26,w>>21&31,w&63
        if op==17 and fmt==4:s.f[w>>11&31]=s.r[w>>16&31]
        elif op==17 and fmt==16 and fn in(0,1,2,3,4,5,7,60):
            fs,ft,fd=w>>11&31,w>>16&31,w>>6&31
            args=(s.f[fs],s.f[ft]) if fn in(0,1,2,3,60) else(s.f[fs],)
            observation=(fn,args,s.fcsr);s.fp.append(observation)
            value=self.terms.term('FP_VALUE',*observation)
            s.fcsr=self.terms.term('FP_STATUS',*observation)
            if fn==60:s.fp_condition=value
            else:s.f[fd]=value
        else:super().step(s,w)
    def call(self,s,target):
        assert target in(0x15143e08,0x151423d8)
        assert s.r[29]==('STACK',-64)
        ordinal=sum(s.calls.values());s.calls[target]+=1
        s.trace.append(('CALL',target,s.r[4],s.fcsr))
        for i in range(4):s.mem[-64+4*i,4]=('CALL_HOME',ordinal,i)
        s.mem[4,4]=('AFTER_MODE',ordinal)
        for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
        for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
        if target==0x15143e08:s.r[2]=('HEADING',ordinal)
        else:s.f[0]=('SAMPLE',ordinal)
        s.r[31]=('CALL_RETURN',ordinal)
        s.hi,s.lo,s.fcsr=('CALL_HI',ordinal),('CALL_LO',ordinal),('CALL_FCSR',ordinal)
    def paths(self):
        states=[(0,State())];answers={};work=0
        while states:
            pc,s=states.pop();work+=1;s.steps+=1;assert work<5000 and s.steps<150
            if pc==-4:
                key=tuple(sorted(s.facts.items(),key=repr));assert key not in answers;answers[key]=s;continue
            w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
            floating=op==17 and rs==8
            if floating or op in(4,5,20,21):
                condition=s.fp_condition if floating else e.pred('EQ',s.r[rs],s.r[rt])
                if (floating and not rt&1) or op in(5,21):condition=e.negate(condition)
                likely=bool(rt&2) if floating else op in(20,21)
                for taken in e.choices(s,condition):
                    n=deepcopy(s);e.assume(n,condition,taken)
                    if taken or not likely:self.step(n,self.instruction(pc+4))
                    target=pc+4+4*(((w&65535)^32768)-32768) if taken else pc+8
                    states.append((target,n))
            elif op==3:
                s.r[31]=self.entry+pc+8;self.step(s,self.instruction(pc+4))
                self.call(s,0x10000000|((w&0x3ffffff)<<2));states.append((pc+8,s))
            elif op==0 and w&63==8:
                target=s.r[rs];self.step(s,self.instruction(pc+4));assert target==('RETURN',)
                states.append((-4,s))
            else:self.step(s,w);states.append((pc+4,s))
        return answers

def prove(raw,normal):
    assert len(raw)==92 and len(normal)==94 and raw[0]==normal[0]==0x27bdffc0
    terms=Terms();a=Program(raw,terms).paths();b=Program(normal,terms).paths()
    assert a.keys()==b.keys(),('path predicates differ',len(a),len(b))
    assert len(a)==13
    for key,x in a.items():
        y=b[key]
        assert x.trace==y.trace,('ordered public accesses and ABI calls',x.trace,y.trace)
        assert x.fp==y.fp and x.fcsr==y.fcsr,('ordered FP/FCSR operations',x.fp,y.fp)
        assert x.r[2]==y.r[2] and x.r[29]==y.r[29]==('STACK',0) and x.r[31]==y.r[31]==('RETURN',)
        assert all(x.r[i]==y.r[i]==('ENTRY',i) for i in (*range(16,24),28,30))
        assert x.f[20:]==y.f[20:]
    return dict(symbolic_paths=len(a),ordered_public_accesses_and_calls=True,ordered_FP_operations_and_FCSR=True,
                arbitrary_callback_mode_homes=True,original_frame_and_saved_ABI=True,unpassed_private_homes_may_differ=True,
                output_alias_of_callee_private_stack=False,full_fault_register_equivalence=False)

def main():
    import json
    from tools.experiments import game_perpendicular_offset_1519ef90_recovery as s
    streams=s.programs();raw,normal=streams['candidate'],streams['retail'];report=prove(raw,normal);controls=[]
    for name,word,mask in(('multiply-order',0x46120282,(18<<11)|(18<<16)),('offset-sign',0x46000007,2),('height-address',0xc4e20118,4),('parameter-home',0x244e0058,4)):
        changed=normal[:];assert changed.count(word)==1;index=changed.index(word);changed[index]^=mask;assert changed[index]!=word
        try:prove(raw,changed)
        except AssertionError:controls.append(name)
        else:raise AssertionError(('ineffective proof control',name))
    report['effective_controls']=controls
    (s.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
