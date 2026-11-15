"""Instruction-driven proof, including every byte exposed to opaque callees.

Valid storage and the normal o32 ABI are preconditions. Opaque helpers may
change public state and passed records, but cannot inspect implementation PCs
or unpassed private storage, or retain private addresses after return. Private
padding is represented by its original stack-byte provenance, not zeroed.
This proves normal observations; it does not equate raw fault scratch state.
"""
from collections import Counter
import json
from tools.tests import game_record_initializer_150169a0_proof as b
from tools.experiments import game_side_effect_constructor_1519f1c8_match as s
COLOR,QUERY,FACTORY,COPY=0x151D8E20,0x1519EF90,0x15147A80,0x10022EC0

def encode(value,n):
    if isinstance(value,int):return [(value>>(8*(n-i-1)))&255 for i in range(n)]
    return [('BYTE',value,n,i) for i in range(n)]

def decode(values):
    n=len(values)
    if all(isinstance(x,int) for x in values):return int.from_bytes(bytes(values),'big')
    if all(b.tagged(x,'BYTE') for x in values):
        first=values[0]
        if values==encode(first[1],first[2]):return first[1]
        if n==1:
            v,width,index=first[1:];shift=8*(width-index-1)
            if shift:v=('LSR',v,shift)
            return b.bitop('AND',v,255)
    return ('BYTES',tuple(values))

class State(b.State):
    def __init__(self,side):
        super().__init__(side,'constructor');self.r[29]=('STACK',0);self.r[16]=('ENTRY',16)
        self.r[31]=('RETURN',);self.r[4]=('ARG',0);self.r[5]=('ARG',1);self.mem={};self.calls=Counter()
    def store(self,address,size,value):
        if b.tagged(address,'STACK'):
            if size<4:value=b.bitop('AND',value,(1<<(8*size))-1)
            for i,v in enumerate(encode(value,size)):self.mem[address[1]+i]=v
        else:self.trace.append(('WRITE',b.plain(address),size,b.bitop('AND',value,(1<<(8*size))-1)))
    def load(self,address,size,pool):
        if b.tagged(address,'STACK'):return decode([self.mem.get(address[1]+i,('INITIAL_BYTE',address[1]+i)) for i in range(size)])
        key=(address,size);epoch=self.reads[key];self.reads[key]+=1
        self.trace.append(('READ',address,size));return ('LOAD',address,size,epoch)
    def snapshot(self,p,n):
        assert b.tagged(p,'STACK');return tuple(self.mem.get(p[1]+i,('INITIAL_BYTE',p[1]+i)) for i in range(n))

class Program(b.Program):
    def step(self,st,w):
        if w>>26==17 and w>>21&31==4:st.f[w>>11&31]=st.r[w>>16&31];return
        return super().step(st,w)
    def call(self,st,target):
        n={COLOR:0,QUERY:3,FACTORY:11,COPY:3}[target]
        args=st.r[4:4+min(n,4)]
        if n>4:args+=[st.load(b.add(st.r[29],16+4*i),4,b'') for i in range(n-4)]
        snap=()
        if target==QUERY:snap=(st.snapshot(args[0],80),st.snapshot(args[2],12))
        elif target==FACTORY:snap=(st.snapshot(args[0],28),)
        elif target==COPY:snap=(st.snapshot(args[1],80),)
        st.trace.append(('CALL',target,tuple(args),snap,st.fcsr));ordinal=st.calls[target];st.calls[target]+=1
        if target==QUERY:
            # Arbitrary writes to every passed packet byte and all output words.
            for p,n in ((args[0],80),(args[2],12)):
                for i in range(0,n,4):st.store(b.add(p,i),4,('QUERY_WRITE',p[1],i))
        elif target==FACTORY:
            for i in range(0,28,4):st.store(b.add(args[0],i),4,('FACTORY_WRITE',i))
        for i in (1,2,3,*range(4,16),24,25):st.r[i]=('CALLER',target,ordinal,i)
        st.r[2]=('RESULT',target,ordinal)
        for i in range(20):st.f[i]=('CALLER_FP',target,ordinal,i)
        st.hi=('CALLER_HI',target,ordinal);st.lo=('CALLER_LO',target,ordinal);st.fcsr=('CALLER_FCSR',target,ordinal)
        for i in range(0,16,4):st.store(b.add(st.r[29],i),4,('CALL_HOME',target,ordinal,i))

def paths(words,side):return Program(words,b'',s.ENTRY).paths(0,{-4:'return'},State(side))

def observation(st):
    return st.trace,st.r[2],tuple(st.r[i] for i in (16,17,18,19,20,21,22,23,28,29,30)),tuple(st.f[20:]),st.fcsr

def prove(raw,normal):
    a,c=paths(raw,'raw'),paths(normal,'retail');assert a.keys()==c.keys() and len(a)==4
    for key in a:assert observation(a[key])==observation(c[key]),('symbolic constructor path',key,observation(a[key]),observation(c[key]))
    controls=[]
    for label,word,mask in (('request-flags',0x24180042,1),('copy-length',0x24060050,1),('mode-home',0xAFA700A8,4)):
        bad=normal[:];assert bad.count(word)==1;bad[bad.index(word)]^=mask
        try:other=paths(bad,label);same=other.keys()==a.keys() and all(observation(other[k])==observation(a[k]) for k in a)
        except (AssertionError,KeyError):same=False
        assert not same,('ineffective proof control',label);controls.append(label)
    return dict(paths=4,ordered_public_reads=True,opaque_helper_effects=True,passed_packet_bytes=80,passed_request_bytes=28,untouched_byte_provenance=True,effective_controls=controls)

def main():
    p=s.programs();report=prove(p['candidate'],p['guarded']);(s.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
