"""Symbolic alias-aware proof of the post-sine instruction schedule and roles.

The two private frame layouts are identified by their three logical pointer
arrays. This proves the straight-line public memory trace and live roles;
it does not claim equality of arbitrary private bytes or instruction faults.
"""
from tools.tests.game_animation_timeline_oracle import signed

def expression(op,a,b):
    if op=='add' and b==0:return a
    if op=='add' and a==0:return b
    if isinstance(a,int) and isinstance(b,int):
        value={'add':lambda:a+b,'sub':lambda:a-b,'shl':lambda:a<<b,'sra':lambda:signed(a)>>b}[op]()
        return value&0xffffffff
    return op,a,b

def run(words):
    r=[('r',i) for i in range(32)];f=[('f',i) for i in range(32)]
    r[0]=0;r[17]=0x800a7210;memory=('initial-memory',);events=[]
    for w in words[54:121]:
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        imm=((w&65535)^32768)-32768
        if op==0:
            if not w:continue
            if fn==0:r[rd]=expression('shl',r[rt],sa)
            elif fn==3:r[rd]=expression('sra',r[rt],sa)
            elif fn in (33,35):r[rd]=expression('add' if fn==33 else 'sub',r[rs],r[rt])
            else:raise AssertionError(('Unexpected R operation',hex(w)))
        elif op==15:r[rt]=(w&65535)<<16
        elif op==9:r[rt]=expression('add',r[rs],imm)
        elif op in (35,36,49,41,57):
            address=expression('add',r[rs],imm);size=1 if op==36 else 2 if op==41 else 4
            if op in (41,57):
                value=f[rt] if op==57 else ('low16',r[rt])
                events.append(('W',address,size,value));memory=('write',memory,address,size,value)
            else:
                value=('read',memory,address,size);events.append(('R',address,size,value))
                if op==49:f[rt]=value
                else:r[rt]=value
        elif op==17:
            if rs==0:r[rt]=f[rd]
            elif rs==16 and fn==13:f[sa]=('trunc-s32',f[rd])
            elif rs==16 and fn in (0,1,2):f[sa]=({0:'fadd',1:'fsub',2:'fmul'}[fn],f[rd],f[rt])
            else:raise AssertionError(('Unexpected FP operation',hex(w)))
        else:raise AssertionError(('Unexpected opcode',hex(w)))
        r[0]=0
    live=(tuple(r[i] for i in (2,16,17,18,19,20,21)),tuple(f[i] for i in (0,4,20,22)))
    return events,memory,live

def qualify(raw,guarded):
    assert len(raw)==len(guarded)==140
    # Initial phase, amplitude, factor, selected bank and array iterators agree
    # logically at entry. The only earlier changes are mapped private homes.
    assert raw[47:54]==guarded[47:54]
    original=run(raw);actual=run(guarded);assert original==actual,'Wave memory trace or live-role proof failed'
    # At least one effective value-changing control must invalidate the proof.
    changed=guarded[:];assert changed[105]&65535==0xffee;changed[105]^=1
    assert run(changed)!=actual,'Wave symbolic control was ineffective'
    return dict(instructions=67,memory_events=len(actual[0]),alias_aware=True,live_roles=True,effective_control=True)
