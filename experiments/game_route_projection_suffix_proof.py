"""Paired suffix paths with exact FP terms and inlined retail leaf helpers."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_route_projection_call_lifetime_fit as source
from tools.experiments import game_route_projection_prefix_proof as prefix

ENTRY=source.source.ENTRY
HELPERS={0x1508907C:91,0x1512D560:41}
HELPER_SHA={
    0x1508907C:'60e1615185f9976a87f2fcb3b5def95ec6945b70a0bad06807aab3f180b68a89',
    0x1512D560:'6da18e31a39f0a9aba5f66bb25e91baa4651b2a346b7d2d18cce227030b208ee',
}
PRESERVED=(*range(16,24),28,29,30)
ANCHORS={name:int(name.split('_',1)[1],16) for name in (
    'D_8008FDBC','D_80087290','D_800D2350','D_800D23A8','D_8009DA08','D_800DC2B0',
    'func_1508907C','func_1512D560')}


def rebased_helpers(helpers,anchors):
    result={}
    for entry,body in helpers.items():
        words=list(body);selector=entry==0x1508907C
        pairs=((14,15,'D_80087290'),(17,23,'D_800D2350')) if selector else ((0,1,'D_800DC2B0'),)
        for hi,lo,name in pairs:
            value=anchors[name]
            words[hi]=words[hi]&0xFFFF0000|((value+0x8000)>>16)&65535
            words[lo]=words[lo]&0xFFFF0000|value&65535
        address=anchors['func_1508907C' if selector else 'func_1512D560']
        if address&3 or address>>28!=ENTRY>>28:raise ValueError('Invalid helper code rebase')
        result[address]=words
    if len(result)!=2:raise ValueError('Overlapping helper entry addresses')
    return result


def ordered_effects(events):
    # Sequential reads of one unchanged memory version may commute, not writes.
    result=[];reads=[]
    for event in events:
        if event[0]=='R':reads.append(event)
        else:
            result.extend(sorted(reads,key=repr));reads=[];result.append(event)
    result.extend(sorted(reads,key=repr))
    return tuple(result)


class Suffix:
    def __init__(self,words,helpers,arena,retail=False,strict_fp_memory=False,anchors=None):
        self.words=words;self.a=arena;self.retail=retail
        self.strict_fp_memory=strict_fp_memory
        anchors=ANCHORS if anchors is None else anchors
        self.selector_entry=anchors['func_1508907C'];self.helper_entries=set(helpers)
        pa=dict(zip(('flags','count','table','mode'),(anchors[n] for n in ('D_8008FDBC','D_80087290','D_800D2350','D_800D23A8'))))
        self.gp=prefix.Prefix(words,arena,retail,pa)
        self.code=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words))
        for entry,body in helpers.items():
            if any(at in self.code for at in range(entry,entry+len(body)*4,4)):
                raise ValueError('Overlapping helper code ranges')
            self.code.update(zip(range(entry,entry+len(body)*4,4),body))
        shift=0 if retail else 14
        self.cycle=150+shift;self.loop=158+shift;self.common=199+shift
        self.cuts={ENTRY+self.loop*4:'loop',ENTRY+self.common*4:'common'}
        self.paths={}

    def initial(self,mode):
        a=self.a;regs=[0,*(a.node('suffix-scratch',self.retail,i) for i in range(1,32))]
        for i in PRESERVED:regs[i]=a.node('suffix-saved',i)
        regs[18]=a.node('record');regs[21]=a.node('actor')
        regs[29]=a.add(a.node('entry-sp'),-120)
        regs[31]=a.node('unrelated-ra',self.retail)
        regs.extend((a.node('unrelated-hi',self.retail),a.node('unrelated-lo',self.retail)))
        floats=[a.node('suffix-float-scratch',self.retail,i) for i in range(32)]
        for i in range(20,32):floats[i]=a.node('saved-float',i)
        if mode=='loop':
            regs[9 if self.retail else 3]=a.node('first-id')
            regs[15 if self.retail else 25]=a.node('cached-cycle-table')
            floats[14]=a.node('best-distance')
        if mode=='exit':regs[31]=a.node('exit-ra')
        return regs,floats

    def execute(self,word,regs,floats,memory,events,fp):
        a=self.a;op,rs,rt=word>>26,word>>21&31,word>>16&31
        imm=((word&65535)^32768)-32768
        if op==0 and word&63==25:
            x,y=regs[rs],regs[rt]
            if isinstance(x,int) and isinstance(y,int):regs[32],regs[33]=(x*y>>32)&0xFFFFFFFF,(x*y)&0xFFFFFFFF
            else:
                operands=tuple(sorted((x,y),key=a.order))
                regs[32]=a.node('multu-hi',*operands);regs[33]=a.node('multu-lo',*operands)
        elif op==0 and word&63 in (16,18):regs[word>>11&31]=regs[32 if word&63==16 else 33]
        elif op in (49,57):
            address=a.add(regs[rs],imm)
            if op==49:
                value=a.node('read',memory,address,4,False);floats[rt]=value
                events.append(('R',address,4,False,value))
            else:
                value=floats[rt];events.append(('W',address,4,value))
                memory=a.node('store',memory,address,4,value)
        elif op==17:
            fs,fd,fn=word>>11&31,word>>6&31,word&63
            if rs==4:floats[fs]=regs[rt]
            elif rs==0:regs[rt]=floats[fs]
            elif rs==16 and fn==6:floats[fd]=floats[fs]
            elif rs==20 and fn==32:
                operands=(floats[fs],);value=a.node('fp-cvt.s.w',*operands)
                floats[fd]=value;fp.append(('cvt.s.w',*operands))
                if self.strict_fp_memory:events.append(('F','cvt.s.w',*operands))
            elif rs==16 and fn in (0,1,2,3,4,60):
                name={0:'add.s',1:'sub.s',2:'mul.s',3:'div.s',4:'sqrt.s',60:'c.lt.s'}[fn]
                operands=(floats[fs],) if fn==4 else (floats[fs],floats[rt])
                value=a.node('fp-'+name,*operands);fp.append((name,*operands))
                if self.strict_fp_memory:events.append(('F',name,*operands))
                if fn==60:return memory,value
                floats[fd]=value
            else:raise ValueError('Unsupported suffix FP instruction: %08X'%word)
        else:memory=self.gp.execute(word,regs,memory,events)
        regs[0]=0;return memory,None

    def projection(self,name,regs,floats,memory,events,fp):
        saved=tuple(regs[i] for i in PRESERVED)
        interface=()
        if name=='loop':
            interface=(regs[9 if self.retail else 3],regs[15 if self.retail else 25],floats[14])
        elif name=='return':interface=(regs[31],)
        return name,saved,tuple(floats[20:]),interface,memory,ordered_effects(events),tuple(fp)

    def walk(self,pc,regs,floats,memory,events,fp,conditions,fcc=None,steps=0):
        regs=list(regs);floats=list(floats);events=list(events);fp=list(fp);a=self.a
        while True:
            if steps and pc in self.cuts:
                self.finish(self.cuts[pc],regs,floats,memory,events,fp,conditions);return
            if steps>2000 or pc not in self.code:raise ValueError('Escaped or unbounded suffix CFG')
            steps+=1;word=self.code[pc];op,rs,rt,fn=word>>26,word>>21&31,word>>16&31,word&63
            if op in (4,5,20,21) or op==17 and rs==8:
                condition=fcc if op==17 else a.equal(regs[rs],regs[rt])
                if condition is None:raise ValueError('Undefined floating condition')
                equal=bool(rt&1) if op==17 else op in (4,20)
                likely=bool(rt&2) if op==17 else op in (20,21)
                outcomes=(condition,) if isinstance(condition,bool) else (conditions[condition],) if condition in conditions else (False,True)
                for outcome in outcomes:
                    taken=outcome==equal;nr=list(regs);nf=list(floats);ne=list(events);np=list(fp);nm=memory;nc=fcc
                    predicates=dict(conditions)
                    if not isinstance(condition,bool):predicates[condition]=outcome
                    if taken or not likely:
                        nm,flag=self.execute(self.code[pc+4],nr,nf,nm,ne,np)
                        if flag is not None:nc=flag
                    target=pc+4+(((word&65535)^32768)-32768)*4 if taken else pc+8
                    self.walk(target,nr,nf,nm,ne,np,predicates,nc,steps)
                return
            if op==3:
                target=((word&0x3FFFFFF)<<2)|((pc+4)&0xF0000000)
                if target not in self.helper_entries:raise ValueError('Unknown suffix helper')
                regs[31]=pc+8
                memory,flag=self.execute(self.code[pc+4],regs,floats,memory,events,fp)
                if flag is not None:fcc=flag
                events.append(('C',target,tuple(regs[4:8 if target==self.selector_entry else 7])))
                pc=target;continue
            if op==0 and fn==8:
                target=regs[rs]
                memory,flag=self.execute(self.code[pc+4],regs,floats,memory,events,fp)
                if flag is not None:fcc=flag
                if ENTRY<=pc<ENTRY+len(self.words)*4:
                    if rs!=31 or pc!=ENTRY+(len(self.words)-2)*4:raise ValueError('Unknown root return')
                    self.finish('return',regs,floats,memory,events,fp,conditions);return
                if rs!=31 or not isinstance(target,int) or not ENTRY<=target<ENTRY+len(self.words)*4:
                    raise ValueError('Unknown inlined-helper return')
                pc=target;continue
            memory,flag=self.execute(word,regs,floats,memory,events,fp)
            if flag is not None:fcc=flag
            pc+=4

    def finish(self,name,regs,floats,memory,events,fp,conditions):
        key=tuple(sorted(conditions.items(),key=lambda x:x[0].index))
        if key in self.paths:raise ValueError('Ambiguous suffix symbolic path')
        self.paths[key]=self.projection(name,regs,floats,memory,events,fp)

    def run(self,mode):
        regs,floats=self.initial(mode);pc={'cycle':self.cycle,'loop':self.loop,'common':self.common,'exit':self.gp.exit}[mode]
        self.walk(ENTRY+pc*4,regs,floats,self.a.node('suffix-memory'),[],[],{})
        return self.paths


def prove(words,truth,helpers,anchors=None):
    if set(helpers)!=set(HELPERS) or any(len(helpers[k])!=n for k,n in HELPERS.items()):
        raise ValueError('Unknown suffix helper extents')
    if any(hashlib.sha256(struct.pack('>%dI'%len(body),*body)).hexdigest()!=HELPER_SHA[entry] for entry,body in helpers.items()):
        raise ValueError('Unknown suffix helper words')
    anchors=ANCHORS if anchors is None else anchors
    if set(anchors)!=set(ANCHORS) or any(not 0<=value<=0xFFFFFFFF for value in anchors.values()):
        raise ValueError('Unknown projection anchor map')
    pa=dict(zip(('flags','count','table','mode'),(anchors[n] for n in ('D_8008FDBC','D_80087290','D_800D2350','D_800D23A8'))))
    calls={anchors['func_1508907C']:4,anchors['func_1512D560']:3}
    result={'prefix':prefix.prove(words,truth,pa,calls)};a=prefix.Expressions()
    helpers=rebased_helpers(helpers,anchors)
    for mode in ('cycle','loop','common','exit'):
        left=Suffix(words,helpers,a,anchors=anchors).run(mode);right=Suffix(truth,helpers,a,True,anchors=anchors).run(mode)
        if left!=right:
            shared=set(left)&set(right);different=[k for k in shared if left[k]!=right[k]]
            raise ValueError('Suffix %s disagreement: raw=%d retail=%d missing=%d extra=%d different=%d'%
                (mode,len(left),len(right),len(set(left)-set(right)),len(set(right)-set(left)),len(different)))
        result[mode+'_paths']=len(left)
    result.update(expression_nodes=len(a.nodes),helpers_inlined=True,helper_fingerprints_checked=True,
        exact_FP_terms_and_operation_order=True,stable_shared_FP_environment=True,
        sequential_read_groups_may_commute=True,ordinary_memory_nontrapping_FP_only=True,
        no_exception_PC_or_normalization_claim=True,normalization_emitted=False)
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];out=root/source.BUILD
    source.prior.freeze(root,out)
    obj=out/'qualified.o';source.checked(obj)
    data,functions=source.source.neighbor.baseline.model.link_owner(root,out,obj,source.source.OWNER)
    words=list(struct.unpack_from('>335I',data,functions[source.source.FUNCTION]['value']))
    rom=(root/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>321I',rom,source.source.ROM))
    helpers={entry:list(struct.unpack_from('>%dI'%count,rom,entry-0x14FD2B50)) for entry,count in HELPERS.items()}
    result=prove(words,truth,helpers);print(json.dumps(result,indent=2))
    (out/'suffix-proof.json').write_text(json.dumps(result,indent=2)+'\n')
