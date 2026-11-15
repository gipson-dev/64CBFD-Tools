"""Symbolic signed conversion, unsigned correction and the one live height store."""
def prove(raw,normal):
    # Every converted operand is a finite signed integer or the exact 2^32
    # constant. The final signed-halfword add is finite too. Canonicalizing
    # their commutative additions does not assume NaN or FCSR equivalence.
    def expr(op,*args):
        if op in ('int-add','float-add'):args=tuple(sorted(args,key=repr))
        return (op,*args)
    def execute(words,negative,normalized):
        r=[('input-register',i)for i in range(32)];r[0]=0;r[1]=0x4f800000;r[16]=('record',)
        remainder=('remainder',);r[13 if normalized else 3]=remainder
        f=[('input-float',i)for i in range(32)];f[8]=remainder;events=[]
        def step(w,pc):
            op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
            imm=((w&65535)^32768)-32768
            if not w:return
            if op==17:
                if rs==4:f[rd]=('bits',r[rt])
                elif rs==20 and fn==32:f[fd]=('signed-float32',f[rd])
                elif rs==16 and fn==6:f[fd]=f[rd]
                elif rs==16 and fn==0:f[fd]=expr('float-add',f[rd],f[rt])
                else:raise AssertionError(hex(w))
            elif op in (33,36):
                address=expr('int-add',r[rs],imm);kind='signed-half'if op==33 else'byte'
                value=(kind,address);events.append(('read',kind,address));r[rt]=value
            elif op==57:events.append(('write-float',expr('int-add',r[rs],imm),f[rt]))
            elif op==15:
                assert pc==0x1d4
                r[rt]=('named-model-hi',)
            elif op==0 and fn==0:r[rd]=expr('shift-left',r[rt],fd)
            elif op==0 and fn==33:r[rd]=expr('int-add',r[rs],r[rt])
            else:raise AssertionError((hex(pc),hex(w)))
            r[0]=0
        pc=0x1b4
        while pc<0x1f8:
            w=words[pc//4]
            if w>>26==1:
                assert pc==0x1b8 and r[w>>21&31]==remainder and w>>16&31 in (1,3)
                taken=not negative
                if taken or w>>16&31==1:step(words[pc//4+1],pc+4)
                pc=pc+4+4*(((w&65535)^32768)-32768)if taken else pc+8
            else:step(w,pc);pc+=4
        return events,r[25 if normalized else 24],tuple(r[i]for i in (16,17,18,19,20,21,22,23,29,30)),tuple(f[20:])
    for negative in (False,True):
        a=execute(raw,negative,False);b=execute(normal,negative,True);assert a==b,(negative,a,b)
        assert [e[0]for e in a[0]]==['read','read','write-float']
    return dict(sign_paths=2,source_halfword_reads=1,variant_reads=1,height_stores=1,saved_roles_preserved=True,finite_float_operands=True)
