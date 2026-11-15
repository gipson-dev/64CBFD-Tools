"""Path-complete register-read coupling and a private pointer-cache bijection.

Opaque calls use the o32 contract: arguments and memory agree, callee-saved
state is retained, and caller-saved registers receive shared fresh values.
Dead caller-saved register contents are not claimed as literal raw identity.
"""
import json,struct
from tools.experiments import game_actor_effect_binding_150c4120_match as s
from tools.experiments.game_paired_ground_constructor_match import payload

C=lambda n:('C',n&0xFFFFFFFF)
SP=lambda n:('SP',n)
sign=lambda n:((n&65535)^32768)-32768
ARITY={0x15149130:9,0x15130280:6,0x10022EC0:3,0x150ADA20:0,0x150ADA68:0}

def mask(w):
    op,fn=w>>26,w&63
    if op==0:return {0:0x001FF800,2:0x001FF800,3:0x001FF800,8:0x03E00000,16:0xF800,18:0xF800,27:0x03FF0000,33:0x03FFF800,35:0x03FFF800,36:0x03FFF800,37:0x03FFF800,38:0x03FFF800}.get(fn,0)
    if op in (4,5,9,12,13,32,33,35,36,37,40,41,43):return 0x03FF0000
    if op==15:return 0x001F0000
    if op in (49,57):return 0x03E00000
    return 0

def add(value,n):
    if value[0]=='SP':return SP(value[1]+n)
    if value[0]=='C':return C(value[1]+n)
    return ('add',value,n)

def address(value,raw=False):
    if raw and value==SP(-240+0x38):return SP(-240+0x30)
    if raw and value==SP(-240+0x30):return SP(-240+0x38)
    return value

def shape(a,b):
    assert len(a)==len(b)==225
    changed={i for i in range(225) if a[i]!=b[i]};assert changed==set(s.PATCHES) and len(changed)==70
    for i in changed:
        x,y=a[i],b[i]
        if i in (55,214):
            assert (x,y)==((0xAFA40038,0xAFA40030) if i==55 else (0x8FA30038,0x8FA30030))
        else:assert not (x^y)&~mask(x),(i,hex(x),hex(y))
    for words,home in ((a,0x38),(b,0x30)):
        accesses=[i for i,w in enumerate(words) if w>>26 in (32,33,35,36,37,40,41,43,49,57) and w>>21&31==29 and w&65535 in (0x30,0x38)]
        assert accesses==[55,214] and all(words[i]&65535==home for i in accesses)
        assert not any(w>>26==9 and w>>21&31==29 and w>>16&31!=29 and w&65535 in (0x30,0x38) for w in words)

def proof(a,b):
    shape(a,b);initial=[('G',i) for i in range(32)];initial[0]=C(0);initial[29]=SP(0)
    f=[('F',i) for i in range(32)];queue=[(0,initial[:],initial[:],f[:],f[:],('HI',),('HI',),('LO',),('LO',))]
    visits=set();returns=0;steps=0;calls=set()
    def step(i,x,y,fx,fy,hx,hy,lx,ly):
        nonlocal steps
        visits.add(i);steps+=1;assert steps<100000
        wa,wb=a[i],b[i];op=wa>>26;fn=wa&63
        rsa,rta,rda=wa>>21&31,wa>>16&31,wa>>11&31
        rsb,rtb,rdb=wb>>21&31,wb>>16&31,wb>>11&31
        def same(left,right,commute=False):
            assert left==right or commute and left==right[::-1],('read-role',i,hex(wa),hex(wb),left,right)
        def write(va,vb=None):
            x[rda if op==0 else rta]=va;y[rdb if op==0 else rtb]=va if vb is None else vb
        if op==0:
            if fn in (0,2,3):
                same((x[rta],),(y[rtb],));write(('shift',i))
            elif fn in (16,18):
                same((hx if fn==16 else lx,),(hy if fn==16 else ly,));write(hx if fn==16 else lx)
            elif fn in (33,35,36,37,38):
                same((x[rsa],x[rta]),(y[rsb],y[rtb]),fn in (33,36,37,38));write(('alu',i))
            elif fn==27:
                same((x[rsa],x[rta]),(y[rsb],y[rtb]));hx=hy=('div-hi',i);lx=ly=('div-lo',i)
            else:raise AssertionError(('unexpected scalar',i,hex(wa)))
        elif op in (9,12,13):
            same((x[rsa],),(y[rsb],))
            if op==9:write(add(x[rsa],sign(wa)))
            elif x[rsa][0]=='C':write(C(x[rsa][1]&(wa&65535) if op==12 else x[rsa][1]|(wa&65535)))
            else:write(('immediate',i))
        elif op==15:write(C((wa&65535)<<16))
        elif op in (32,33,35,36,37,40,41,43,49,57):
            same((address(add(x[rsa],sign(wa)),True),),(address(add(y[rsb],sign(wb))),))
            if op in (40,41,43):same((x[rta],),(y[rtb],))
            elif op==57:same((fx[rta],),(fy[rtb],))
            elif op==49:fx[rta]=fy[rtb]=('load-fp',i)
            else:write(('load',i))
        elif op==17:
            assert wa==wb
            fmt=wa>>21&31;ft,fs,fd=wa>>16&31,wa>>11&31,wa>>6&31
            if fmt==4:
                same((x[ft],),(y[ft],));fx[fs]=fy[fs]=('mtc1',i)
            elif fmt==0:
                same((fx[fs],),(fy[fs],));x[ft]=y[ft]=('mfc1',i)
            else:
                assert fmt==16 and fn in (0,1,2)
                same((fx[fs],fx[ft]),(fy[fs],fy[ft]));fx[fd]=fy[fd]=('fp',i)
        else:raise AssertionError(('unexpected instruction',i,hex(wa)))
        x[0]=y[0]=C(0);return hx,hy,lx,ly
    while queue:
        i,x,y,fx,fy,hx,hy,lx,ly=queue.pop();assert 0<=i<225
        wa,wb=a[i],b[i];op=wa>>26;fn=wa&63
        if op==3:
            assert wa==wb;target=((s.ENTRY+4*i+4)&0xF0000000)|((wa&0x3FFFFFF)<<2);assert target in ARITY
            visits.add(i);calls.add(target);x[31]=y[31]=C(s.ENTRY+4*i+8)
            hx,hy,lx,ly=step(i+1,x,y,fx,fy,hx,hy,lx,ly)
            assert x[29]==y[29]
            assert x[4:4+min(4,ARITY[target])]==y[4:4+min(4,ARITY[target])]
            assert x[16:24]==y[16:24] and x[28:32]==y[28:32] and fx[20:]==fy[20:]
            for reg in (1,2,3,*range(4,16),24,25):x[reg]=y[reg]=('call',i,reg)
            for reg in range(20):fx[reg]=fy[reg]=('call-fp',i,reg)
            hx=hy=('call-hi',i);lx=ly=('call-lo',i);queue.append((i+2,x,y,fx,fy,hx,hy,lx,ly));continue
        if op==0 and fn==8:
            visits.add(i);assert x[wa>>21&31]==y[wb>>21&31]
            hx,hy,lx,ly=step(i+1,x,y,fx,fy,hx,hy,lx,ly)
            assert x[2]==y[2] and x[16:24]==y[16:24] and x[28:32]==y[28:32] and fx==fy and hx==hy and lx==ly
            assert x[29]==y[29]==SP(0);returns+=1;continue
        if op in (4,5):
            visits.add(i);left=(x[wa>>21&31],x[wa>>16&31]);right=(y[wb>>21&31],y[wb>>16&31])
            assert left==right or left==right[::-1],('branch-read',i,left,right)
            equal=left[0]==left[1]
            known=equal or left[0][0]==left[1][0]=='C'
            taken=equal if op==4 else not equal
            hx,hy,lx,ly=step(i+1,x,y,fx,fy,hx,hy,lx,ly)
            choices=[i+1+sign(wa)] if known and taken else [i+2] if known else [i+1+sign(wa),i+2]
            for dest in choices:
                assert dest>i
                queue.append((dest,x[:],y[:],fx[:],fy[:],hx,hy,lx,ly))
            continue
        hx,hy,lx,ly=step(i,x,y,fx,fy,hx,hy,lx,ly);queue.append((i+1,x,y,fx,fy,hx,hy,lx,ly))
    assert visits==set(range(225)) and calls==set(ARITY)
    return dict(visited_words=len(visits),abstract_returns=returns,symbolic_transfer_steps=steps,helper_targets=len(calls),cache_bijection_bytes=8,all_operand_reads_coupled=True,abi_outputs_coupled=True,dead_caller_saved_gpr_identity_uncredited=True)

def main():
    truth,raw,normalized=s.programs();assert truth==normalized
    report=proof(raw,truth)
    wrong=raw[:];wrong[80]^=1<<21
    shape(wrong,truth)
    try:proof(wrong,truth)
    except AssertionError as e:assert isinstance(e.args[0],tuple) and e.args[0][0]=='read-role',e
    else:raise AssertionError('Wrong source role accepted')
    report['wrong_source_control_effective']=True
    (s.OUT/'roles-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
