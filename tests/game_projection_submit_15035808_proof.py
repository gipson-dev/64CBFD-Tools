"""Instruction-driven whole-prefix and inductive descriptor-loop relation.

No fitting map supplies execution semantics. FP/FCSR transitions are ordered;
opaque o32 providers may mutate public memory and all retained exposed homes.
All 256 private/incoming bytes are observed at each call and each transfer.
Only adjacent public stores with provably disjoint byte addresses commute.
Normal mapped ordinary RAM is assumed; no fault, MMIO or runtime claim.
"""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
from collections import Counter
import json,struct
from tools.tests import game_projection_submit_15035808_oracle as target
from tools.tests import game_projection_submit_15035808_prefix as prefix
from tools.tests import game_growth_curve_151a1fb4_proof as g
e=g.e;OUT=recovery.OUT

class State(prefix.State):
    def __init__(self):
        super().__init__();self.exposed_colors=False;self.exposed_outputs=False

class Program(prefix.Program):
    def step(self,s,w):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==0 and fn==43 and s.r[rs]==0:
            # Exact unsigned identity for every 32-bit operand: 0 < x iff x != 0.
            s.r[rd]=e.boolean(e.negate(e.pred('EQ',s.r[rt],0)));s.r[0]=0
        else:super().step(s,w)
    def call(self,s,address):
        assert address in target.COUNTS,hex(address)
        n=target.COUNTS[address];ordinal=sum(s.calls.values());s.calls[address]+=1
        args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,n-4)))
        if address==target.COLOR:
            assert args[1]==('STACK',-20);s.exposed_colors=True
        if address==target.RESOLVE:
            assert args[2:]==(('STACK',-24),('STACK',-40));s.exposed_outputs=True
        s.trace.append(('CALL',address,args,s.fcsr))
        s.trace.append(('PRIVATE_FRAME',s.frame()))
        for begin,end,active in((-20,-8,s.exposed_colors),(-24,-20,s.exposed_outputs),(-40,-36,s.exposed_outputs)):
            if active:
                for off in range(begin,end):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
        s.epoch+=1
        for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
        for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
        for i in range(max(4,n)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
        s.r[2]=('RESULT',address,ordinal);s.r[31]=('CALL_RETURN',ordinal)
        s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)

def disjoint(a,b):
    ca,ta=e.linear(a[1]);cb,tb=e.linear(b[1])
    if ta!=tb:return False
    return {(ca+i)&e.U32 for i in range(a[2])}.isdisjoint((cb+i)&e.U32 for i in range(b[2]))

def trace(values):
    result=[];pending=[]
    def flush():
        if pending:
            # Fail closed for mixed-base or possibly overlapping store runs.
            if all(disjoint(a,b)for i,a in enumerate(pending)for b in pending[i+1:]):result.extend(sorted(pending,key=repr))
            else:result.extend(pending)
            pending.clear()
    for item in values:
        if item[0]=='WRITE':pending.append(item)
        else:flush();result.append(item)
    flush();return tuple(result)

def roles(words):
    cut=0x368//4
    w=words[cut-1];assert w>>26==35 and w&65535==0x54
    descriptor,next_reg=w>>21&31,w>>16&31
    actor=[w>>21&31 for w in words[cut-3:cut-1]if w>>26==36 and w&65535==0x3b]
    assert len(actor)==1
    return dict(descriptor=descriptor,next=next_reg,actor=actor[0],factor=22,buffer=21)

def relation(s,end,side,words):
    live=()
    if end=='return':
        assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
        assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
        assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
    else:
        assert s.r[29]==('STACK',-216)
        binding=roles(words)
        live=tuple((name,s.r[reg])for name,reg in binding.items())
        w=words[0x368//4];rs,rt=w>>21&31,w>>16&31
        # Source reverses the two equality operands; both actual cached bytes
        # and the next descriptor remain part of the inductive relation.
        ids=(s.r[rs],s.r[rt])if side=='retail'else(s.r[rt],s.r[rs])
        live+=tuple(zip(('node_id','actor_id'),ids))
        for reg in range(16,23):assert s.load(('STACK',-128+4*(reg-16)),4)==('ENTRY',reg)
        assert s.load(('STACK',-100),4)==('RETURN',)
    return trace(s.trace),s.read_set,s.fcsr,s.frame(),live,(s.exposed_colors,s.exposed_outputs)

def refine(value,facts):
    """Evaluate actual boolean bit-vector values under a joint path condition."""
    if not isinstance(value,tuple)or not value:return value
    if e.tagged(value,'BOOL'):
        p=value[1]
        if isinstance(p,bool):return int(p)
        if e.tagged(p,'NOT'):
            q=p[1]
            if q in facts:return int(not facts[q])
        elif p in facts:return int(facts[p])
        return value
    if e.tagged(value,'BYTE'):return g.byte(refine(value[1],facts),value[2])
    if e.tagged(value,'JOIN'):return g.join([refine(v,facts)for v in value[1]])
    if e.tagged(value,'LINEAR'):
        result=value[1]
        for v,k in value[2]:result=e.add(result,e.scale(refine(v,facts),k))
        return result
    if e.tagged(value,'AND')or e.tagged(value,'OR'):
        return e.bitop(value[0],refine(value[1],facts),refine(value[2],facts))
    return tuple(refine(v,facts)for v in value)

def refined_relation(s,end,side,words,facts):
    result=relation(s,end,side,words)
    values=[]
    for part in result:
        if isinstance(part,Counter):
            updated=Counter()
            for key,count in part.items():updated[refine(key,facts)]+=count
            values.append(updated)
        else:values.append(refine(part,facts))
    return tuple(values)

def compare(paths,streams):
    same=paths['raw'].keys()==paths['retail'].keys()
    report=dict(same_path_predicates=same,raw_paths=len(paths['raw']),retail_paths=len(paths['retail']),joint_paths=0,differences=[])
    covered={'raw':set(),'retail':set()}
    for key,sa in paths['raw'].items():
      for other,sb in paths['retail'].items():
        if any(p in sb.facts and sb.facts[p]!=v for p,v in sa.facts.items()):continue
        facts=sa.facts|sb.facts;number=report['joint_paths'];report['joint_paths']+=1
        covered['raw'].add(key);covered['retail'].add(other)
        if key[0]!=other[0]:
            report['differences'].append(dict(path=number,part='successor',raw=key[0],retail=other[0]));continue
        a,b=(refined_relation(s,key[0],side,streams[side],facts)for side,s in(('raw',sa),('retail',sb)))
        if a!=b:
            part=next(i for i,(v,w)in enumerate(zip(a,b))if v!=w)
            row=dict(path=number,end=key[0],part=part)
            if part==0:
                at=next((i for i,(v,w)in enumerate(zip(a[0],b[0]))if v!=w),min(len(a[0]),len(b[0])))
                row.update(event=at,raw=repr(a[0][at]if at<len(a[0])else None)[:1600],retail=repr(b[0][at]if at<len(b[0])else None)[:1600])
            elif part==1:
                row.update(only_raw=repr(a[1]-b[1])[:1600],only_retail=repr(b[1]-a[1])[:1600])
            elif part==3:row['offsets']=[i-216 for i,(v,w)in enumerate(zip(a[3],b[3]))if v!=w]
            else:row.update(raw=repr(a[part])[:1600],retail=repr(b[part])[:1600])
            report['differences'].append(row)
    report['all_abstract_paths_covered']=all(len(covered[side])==len(paths[side])for side in covered)
    return report

def loop_initial(side,words,exposed_outputs):
    s=State();s.mem={off:('LOOP_PRIVATE_BYTE',off)for off in range(-216,40)}
    for i in range(10):s.store(('STACK',4*i),4,('ARG',i))
    for reg in range(16,23):s.store(('STACK',-128+4*(reg-16)),4,('ENTRY',reg))
    s.store(('STACK',-100),4,('RETURN',))
    s.r=[('DEAD_LOOP_GPR',side,i)for i in range(32)];s.r[0]=0;s.r[29]=('STACK',-216)
    for reg in(23,28,30):s.r[reg]=('ENTRY',reg)
    s.f=[('DEAD_LOOP_FP',side,i)if i<20 else('ENTRY_FP',i)for i in range(32)]
    s.fcsr=('LOOP_FCSR',);s.condition=('DEAD_LOOP_CONDITION',side)
    actor=e.add(target.ACTORS,e.scale(('ARG',1),0x32c));node=('DESCRIPTOR',)
    node_id=e.bitop('AND',s.load(node,1),255)
    actor_id=e.bitop('AND',s.load(e.add(actor,0x3b),1),255)
    next_node=s.load(e.add(node,0x54),4)
    values=dict(descriptor=node,next=next_node,actor=actor,factor=('FACTOR',),buffer=target.BUFFER)
    for name,reg in roles(words).items():s.r[reg]=values[name]
    w=words[0x368//4];assert w>>26==5
    rs,rt=w>>21&31,w>>16&31
    s.r[rs],s.r[rt]=(node_id,actor_id)if side=='retail'else(actor_id,node_id)
    s.exposed_colors=True;s.exposed_outputs=exposed_outputs
    return s

def run(raw_path=None,label='transfer-proof'):
    raw=struct.unpack('>344I',(raw_path or OUT/'matrix-normal-form.bin').read_bytes())
    retail=struct.unpack_from('>345I',(ROOT/'conker/conker.us.bin').read_bytes(),0x62cb8)
    terms=g.Terms();streams={'raw':raw,'retail':retail};programs={side:Program(words,terms)for side,words in streams.items()}
    report={}
    for phase in('prefix','first-loop','retained-loop'):
        paths={}
        for side,p in programs.items():
            initial=State()if phase=='prefix'else loop_initial(side,p.words,phase=='retained-loop')
            paths[side]=p.paths(0 if phase=='prefix'else 0x368,{0x368:'loop-header',-4:'return'},initial)
        result=compare(paths,streams);report[phase]=result
        print(json.dumps(dict(phase=phase,**{k:v for k,v in result.items()if k!='differences'},difference_count=len(result['differences']),first_difference=next(iter(result['differences']),None))),flush=True)
    report.update(scope='full prefix plus one arbitrary descriptor transfer with retained-provider homes',matching_credit=0)
    report['coverage']={side:dict(visited_words=len(p.seen),unvisited_offsets=[hex(i*4)for i in range(len(p.words))if i*4 not in p.seen])for side,p in programs.items()}
    report['equivalent']=all(not report[phase]['differences']and report[phase]['all_abstract_paths_covered']for phase in('prefix','first-loop','retained-loop'))and all(not r['unvisited_offsets']for r in report['coverage'].values())
    report.update(ordered_FP_and_FCSR=True,all_256_private_incoming_bytes=True,actual_19_argument_packets=True,
        retained_provider_homes=True,arbitrary_public_aliases=True,normal_ordinary_RAM_only=True,
        full_caller_hardware_or_fault_claim=False)
    assert '/'not in label and '\\'not in label
    report['source_normal_form']=str(raw_path or OUT/'matrix-normal-form.bin')
    (OUT/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'equivalent':report['equivalent'],'coverage':report['coverage']}))
    return report
