"""Checked instruction permutation for leaf MIPS single-precision kernels.

The expression model permits only operand exchange for add/multiply, never
reassociation. It is a C arithmetic/dataflow check; NaN payloads, FCSR effects
and fault timing require separate evidence. The fitted binary is checked
literally after deriving its instruction permutation and FPR allocation.
"""

from collections import defaultdict, deque


MASK=0xFFFFFFFF


def canonical(fn,left,right):
    if fn in (0,2):left,right=sorted((left,right),key=repr)
    return (('add.s','sub.s','mul.s')[fn],left,right)


def trace(words,base):
    registers=[None]*32;registers[0]=0;registers[4]=base
    floats=[('incoming-fpr',i) for i in range(32)]
    memory={};reads=[];writes=[];labels=[];returned=False
    for ordinal,word in enumerate(words):
        op,rs,rt=word>>26,word>>21&31,word>>16&31
        imm=word&65535;simm=imm if imm<32768 else imm-65536
        if returned:
            if word or ordinal!=len(words)-1:raise ValueError('Nonempty/extra float return delay slot')
            labels.append(('nop',));continue
        if word==0:labels.append(('nop',))
        elif op==15:
            registers[rt]=imm<<16;labels.append(('gpr',word))
        elif op==9:
            if registers[rs] is None:raise ValueError('Undefined float-kernel address register')
            registers[rt]=(registers[rs]+simm)&MASK;labels.append(('gpr',word))
        elif op in (49,57):
            if registers[rs] is None:raise ValueError('Undefined float-kernel memory address')
            at=(registers[rs]+simm)&MASK
            if at&3:raise ValueError('Unaligned float-kernel memory access')
            if op==49:
                floats[rt]=memory.get(at,('input',at));reads.append(at)
                labels.append(('load',at,floats[rt]))
            else:
                memory[at]=floats[rt];writes.append(at)
                labels.append(('store',at,floats[rt]))
        elif op==17 and rs==16 and word&63 in (0,1,2):
            fs,fd,fn=word>>11&31,word>>6&31,word&63
            value=canonical(fn,floats[fs],floats[rt]);floats[fd]=value
            labels.append(('float',fn,value))
        elif word==0x03E00008:
            returned=True;labels.append(('return',))
        else:raise ValueError('Unsupported linear float word %08X'%word)
        registers[0]=0
    if not returned or registers[2]!=1:raise ValueError('Float-kernel return contract changed')
    if any('incoming-fpr' in repr(value) for value in memory.values()):
        raise ValueError('Float kernel consumes an uninitialized FPR')
    return {'memory':memory,'reads':reads,'writes':writes,'labels':labels,'return':registers[2]}


def derive(raw,retail,bases):
    if len(raw)!=len(retail):raise ValueError('Float instruction inventory length differs')
    if not bases:raise ValueError('No float alias layouts supplied')
    before,after=trace(raw,bases[0]),trace(retail,bases[0])
    slots=defaultdict(deque)
    for index,label in enumerate(before['labels']):slots[label].append(index)
    permutation=[]
    for label in after['labels']:
        if not slots[label]:raise ValueError('Float instruction/dataflow inventory differs: '+repr(label))
        permutation.append(slots[label].popleft())
    if sorted(permutation)!=list(range(len(raw))) or any(slots.values()):
        raise ValueError('Float instruction map is not bijective')
    fitted=[]
    for target,index in zip(retail,permutation):
        word=raw[index];op=word>>26
        # Re-encode only FPR operand/result roles. Opcode, address, immediate,
        # format, and arithmetic operation bits must already be identical.
        fpr_mask=(31<<16) if op in (49,57) else ((31<<16)|(31<<11)|(31<<6)) if op==17 else 0
        if (word&~fpr_mask)!=(target&~fpr_mask):
            raise ValueError('Float fit would change a non-FPR instruction field')
        fitted.append((word&~fpr_mask)|(target&fpr_mask))
    if fitted!=retail:raise ValueError('Derived float permutation does not equal retail')
    for base in bases:
        old,new=trace(raw,base),trace(retail,base)
        if (old['memory']!=new['memory'] or sorted(old['reads'])!=sorted(new['reads'])
                or sorted(old['writes'])!=sorted(new['writes']) or old['return']!=new['return']):
            raise ValueError('Float dataflow differs for alias base %08X'%base)
    return {'permutation':permutation,'fitted_words':fitted,'alias_layouts':len(bases),'words':len(raw),
            'loads':len(before['reads']),'stores':len(before['writes']),
            'float_operations':sum(label[0]=='float' for label in before['labels']),
            'changed_words':sum(a!=b for a,b in zip(raw,retail)),
            'only_fpr_roles_and_bijective_schedule':True,'reassociation':False}
