"""Prove the original caller kills the parent result before any use."""
import json,struct
from tools.experiments import game_record_initializer_150169a0_candidates as g

def prove(rom,changed_caller=False,changed_killer=False):
    def word(pc):return struct.unpack_from('>I',rom,pc-0x15000000+0x2d4b0)[0]
    old=('old-v0',);unknown=lambda n:('input',n)
    r=[unknown(i)for i in range(32)];r[0]=0;r[2]=old;r[29]=('stack',0)
    memory={};calls=[];seen=[]
    def add(a,b):
        if isinstance(a,int)and isinstance(b,int):return(a+b)&0xffffffff
        if isinstance(a,tuple)and a[0]=='stack'and isinstance(b,int):return('stack',a[1]+b)
        return('add',a,b)
    def value(reg):
        assert r[reg]!=old,('Incoming parent result read',seen[-1],reg)
        return r[reg]
    def equal(a,b):
        if isinstance(a,int)and isinstance(b,int):return a==b
        if isinstance(a,tuple)and a[0]=='stack'and b==0:return False
        if isinstance(b,tuple)and b[0]=='stack'and a==0:return False
        if a==b:return True
        raise AssertionError(('Unresolved branch',a,b))
    def execute(pc,w):
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        imm=((w&65535)^32768)-32768;destination=None;answer=None
        if not w:return False
        if op==15:destination,answer=rt,(w&65535)<<16
        elif op==9:destination,answer=rt,add(value(rs),imm)
        elif op==13:
            a=value(rs);assert isinstance(a,int);destination,answer=rt,a|(w&65535)
        elif op==0:
            destination=rd
            if fn==0:
                a=value(rt);assert isinstance(a,int);answer=(a<<sa)&0xffffffff
            elif fn in(33,37):
                a,b=value(rs),value(rt)
                if fn==33:answer=add(a,b)
                elif b==0:answer=a
                else:assert isinstance(a,int)and isinstance(b,int);answer=a|b
            elif fn==36:
                a,b=value(rs),value(rt)
                if isinstance(a,tuple)and a[0]=='stack'and b==0xfffffffc:answer=('stack',a[1]&~3)
                else:assert isinstance(a,int)and isinstance(b,int);answer=a&b
            else:raise AssertionError(('Unsupported prefix opcode',hex(pc),hex(w)))
        elif op in(35,43):
            address=add(value(rs),imm)
            if op==35:destination,answer=rt,memory.get(address,('load',address))
            else:memory[address]=value(rt)
        else:raise AssertionError(('Unexpected non-control prefix',hex(pc),hex(w)))
        if destination is not None:
            if destination==2:
                assert pc==0x1502acac and w==0x3c02800c
                r[2]=answer;return True
            if destination:r[destination]=answer
        return False
    pc=0x15007ed8
    for _ in range(100):
        assert 0x15007ed8<=pc<=0x15007ee4 or 0x15005290<=pc<=0x150052dc or 0x1502b5c8<=pc<=0x1502b64c or 0x1502ac88<=pc<=0x1502acb4,hex(pc)
        w=word(pc)
        if changed_caller and pc==0x15007ed8:assert w==0x3c04800c;w=0x00402025
        if changed_killer and pc==0x1502acac:assert w==0x3c02800c;w=0x3c03800c
        seen.append(hex(pc));op=w>>26
        if op==3:
            target=0x10000000|((w&0x3ffffff)<<2);calls.append(target)
            assert calls==[0x15005290,0x1502b5c8,0x1502ac88][:len(calls)]
            r[31]=pc+8;seen.append(hex(pc+4));assert not execute(pc+4,word(pc+4));pc=target
        elif op in(4,5):
            outcome=equal(value(w>>21&31),value(w>>16&31));outcome=outcome if op==4 else not outcome
            seen.append(hex(pc+4));assert not execute(pc+4,word(pc+4))
            imm=((w&65535)^32768)-32768;pc=pc+4+4*imm if outcome else pc+8
        else:
            if execute(pc,w):
                assert calls==[0x15005290,0x1502b5c8,0x1502ac88]
                return dict(instructions=len(seen),calls=[hex(t)for t in calls],killer=hex(pc),aligned_nonwrapping_valid_stack=True,unknown_category_preserved=True)
            pc+=4
    raise AssertionError('No dominating result overwrite')

def main():
    rom=(g.ROOT/'conker/conker.us.bin').read_bytes();report=prove(rom)
    for caller,killer in((True,False),(False,True)):
        try:prove(rom,caller,killer)
        except AssertionError:pass
        else:raise AssertionError('Ineffective result-use control')
    report.update(effective_controls=2,result_ignored_proven=True,complete_caller_or_provider_claimed=False)
    (g.OUT/'return-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
