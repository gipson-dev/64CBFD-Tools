"""Relational proof of the defined-shift C and original selector-mask schedule.

All mapped public reads are symbolic and ordered. Helpers may change the five
incoming selector homes and caller-saved state. Private stack is valid and does
not alias public records in this proof; finite overlap checks are separate.
This proves normal instruction behavior, not identical fault-register state.
"""
from copy import deepcopy
from tools.tests import game_record_initializer_150169a0_proof as engine


def either(a,b):
    values=[];constant=0
    def add(v):
        nonlocal constant
        if isinstance(v,int):constant|=v
        elif isinstance(v,tuple) and v[0]=='UNION':
            for x in v[1:]:add(x)
        else:values.append(v)
    add(a);add(b);values=list(set(values))
    if constant:values.append(constant)
    values=sorted(values,key=repr)
    return 0 if not values else values[0] if len(values)==1 else ('UNION',*values)


class State(engine.State):
    def __init__(self):
        super().__init__('common','selector');self.mem={};self.r[29]=('STACK',0)
        self.r[31]=('RETURN',);self.r[4]=('ACTOR',)
        self.r[16]=('ENTRY',16)
        for i in range(3):self.r[5+i]=('ARG',i)
        self.mem[16]=('ARG',3);self.mem[20]=('ARG',4)

    def store(self,address,size,value):
        if engine.tagged(address,'STACK'):
            assert size in(1,4)
            assert size==1 or address[1]%4==0
            self.mem[(address[1],size)]=engine.bitop('AND',value,(1<<(size*8))-1)
        else:super().store(address,size,value)

    def load(self,address,size,pool):
        if not engine.tagged(address,'STACK'):return super().load(address,size,pool)
        offset=address[1]
        if (offset,size) in self.mem:return self.mem[(offset,size)]
        aligned=offset&~3
        value=self.mem.get((aligned,4),self.mem.get(aligned,('PRIVATE',aligned)))
        if size==2:
            assert offset%4==2
            return engine.bitop('AND',value,65535)
        assert size==4 and offset%4==0,(offset,size)
        return value


class Program(engine.Program):
    def step(self,s,w):
        if w>>26==0 and w&63==37:
            rs,rt,rd=w>>21&31,w>>16&31,w>>11&31
            s.r[rd]=either(s.r[rs],s.r[rt]);s.r[0]=0
        else:super().step(s,w)

    def call(self,s,target):
        assert target==0x1514ece0
        assert s.r[5]==19 and s.r[6]==('STACK',-8)
        s.trace.append(('CALL',target,tuple(s.r[4:7])))
        s.mem[(-8,4)]=('LOOKUP_NODE',)
        # Arbitrary post-callback values, including full incoming word bits.
        for i in range(5):s.mem[(4+4*i,4)]=('AFTER_ARG',i)
        for i in range(4):s.mem[(-64+4*i,4)]=('CALL_HOME',i)
        for reg in (1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',reg)
        s.r[2]=('LOOKUP_RESULT',)
        for reg in range(20):s.f[reg]=('CALLER_FP',reg)
        s.hi,s.lo,s.fcsr=('CALL_HI',),('CALL_LO',),('CALL_FCSR',)


def prove(raw,normal):
    assert len(raw)==100 and len(normal)==90
    assert raw[:17]==normal[:17]
    a=Program(raw,b'',0x1515942c).paths(0,{-4:'return'},State())
    b=Program(normal,b'',0x1515942c).paths(0,{-4:'return'},State())
    assert a.keys()==b.keys(),('branch predicates differ',len(a),len(b))
    assert len(a)==65
    for key,x in a.items():
        y=b[key]
        assert x.trace==y.trace,('ordered access/call trace',x.trace,y.trace)
        assert x.mem==y.mem,('private stack differs',x.mem,y.mem)
        assert x.r[2]==y.r[2] and x.r[29]==y.r[29]==('STACK',0)
        assert x.r[31]==y.r[31]==('RETURN',)
        assert all(x.r[i]==y.r[i]==('ENTRY',i) for i in (*range(16,24),28,30))
        assert x.f==y.f and x.fcsr==y.fcsr and x.hi==y.hi and x.lo==y.lo
    return dict(symbolic_paths=len(a),ordered_public_accesses=True,all_private_homes_equal=True,
                arbitrary_callback_argument_homes=True,callee_saved_state_equal=True,
                defined_five_bit_shifts=True,unrestricted_private_aliases=False,
                full_fault_register_equivalence=False)


def main():
    import json,struct
    from pathlib import Path
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_actor_state_tick_integration import symbol_rows
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    root=Path.cwd();out=root/'conker/build/game-selector-mask-1515942c-match'
    symbols={x[1]:x[2][1] for x in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
    raw=bound_blob(*payload(out/'ordered-tree.o','func_1515942C'),symbols)
    normal=list(struct.unpack_from('>90I',(root/'conker/conker.us.bin').read_bytes(),0x1868dc))
    report=prove(raw,normal);controls=[]
    for name,index,change in [('field-address',55,lambda w:w+1),('mask',25,lambda w:w^1),('shift',76,lambda w:w^(1<<21))]:
        altered=normal[:];altered[index]=change(altered[index]);assert altered!=normal
        try:prove(raw,altered)
        except AssertionError:controls.append(name)
        else:raise AssertionError(('ineffective proof control',name))
    changed_raw=raw[:];assert changed_raw[27]&65535==31;changed_raw[27]^=16
    try:prove(changed_raw,normal)
    except AssertionError:controls.append('defined-shift-mask')
    else:raise AssertionError('raw five-bit mask control was ineffective')
    report['effective_controls']=controls
    (out/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
