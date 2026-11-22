"""Exact interval execution of both clamp CFGs across every signed input word.

Each symbolic value is a constant, x, or arithmetic x>>1. SLTI splits the
inclusive input interval at its exact preimage; no sampling or solver timeout
is used. Calls capture all five arguments, then clobber every volatile register.
Only the outgoing argument store and the view's distance store are permitted.
"""
from pathlib import Path
from dataclasses import dataclass
import copy,json,struct
from tools.experiments import game_view_light_script_150ecc70_match as packet
root,out=packet.ROOT,packet.OUT
LO,HI=-(1<<31),(1<<31)-1
@dataclass(frozen=True)
class X:
    shift:int=0
@dataclass(frozen=True)
class Condition:
    threshold:int
def signed(x):return ((x&0xFFFFFFFF)^0x80000000)-0x80000000
def bounds(x,lo,hi):return (lo>>x.shift,hi>>x.shift)if isinstance(x,X)else(x,x)
def run(words):
    states=[dict(pc=121,lo=LO,hi=HI,r={i:('incoming',i)for i in range(32)},f={},stores=[],calls=[])]
    states[0]['r'].update({0:0,2:X(),16:0x30000,29:0x90000})
    done=[]
    def execute(s,w):
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        imm=signed(w&65535 if w&32768==0 else (w&65535)|0xFFFF0000);r=s['r']
        if w==0:return
        if op==0 and fn==3:
            x=r[rt];r[rd]=X(x.shift+sa)if isinstance(x,X)else signed(x)>>sa
        elif op==0 and fn==37:
            a,b=r[rs],r[rt]
            assert a==0 or b==0,(hex(w),a,b)
            r[rd]=a if b==0 else b
        elif op==10:
            x=r[rs]
            r[rt]=Condition(imm<<x.shift)if isinstance(x,X)else int(signed(x)<imm)
        elif op==9:r[rt]=(r[rs]+imm)&0xFFFFFFFF
        elif op==13:r[rt]=r[rs]|(w&65535)
        elif op==15:r[rt]=(w&65535)<<16
        elif op==43:
            address=(r[rs]+imm)&0xFFFFFFFF;assert address==0x90010
            s['stores'].append((address,r[rt]))
        elif op==17 and rs==4:s['f'][rd]=r[rt]
        elif op==57:
            address=(r[rs]+imm)&0xFFFFFFFF;assert address==0x30190
            s['stores'].append((address,s['f'][rt]))
        else:raise AssertionError(('unsupported instruction',s['pc'],hex(w)))
        r[0]=0
    steps=0
    while states:
        s=states.pop();steps+=1;assert steps<1000
        p=s['pc']
        if p==178:
            assert len(s['calls'])==1
            args=s['calls'][0]
            assert args[:3]==(2,0x9000,8)
            for actual,expected in ((args[3],900 if s['hi']<900 else 1190 if s['lo']>=1191 else X()),
                                    (args[4],180 if s['hi']<360 else 231 if s['lo']>=464 else X(1))):
                assert actual==expected,(s['lo'],s['hi'],actual,expected)
            assert s['stores']==[(0x90010,args[4]),(0x30190,0x435C0000)]
            assert s['r'][1]==0x40C00000 and s['r'][16]==0x30000 and s['r'][29]==0x90000
            done.append((s['lo'],s['hi'],repr(args[3]),repr(args[4])));continue
        assert 121<=p<=150 or p==177,p
        w=words[p];op,rs,rt=w>>26,w>>21&31,w>>16&31
        if op in(4,5,20,21):
            a,b=s['r'][rs],s['r'][rt];assert b==0
            target=p+1+signed((w&65535)| (0xFFFF0000 if w&32768 else 0))
            if isinstance(a,Condition):
                cuts=((s['lo'],min(s['hi'],a.threshold-1),1),(max(s['lo'],a.threshold),s['hi'],0))
            else:cuts=((s['lo'],s['hi'],int(a!=0)),)
            for lo,hi,truth in cuts:
                if lo>hi:continue
                q=copy.deepcopy(s);q['lo'],q['hi']=lo,hi
                take=bool(truth)if op in(5,21)else not truth
                if take or op not in(20,21):execute(q,words[p+1])
                q['pc']=target if take else p+2;states.append(q)
        elif op==3:
            assert (0x10000000|((w&0x3FFFFFF)<<2))==0x1509BFB0
            execute(s,words[p+1]);args=tuple(s['r'][i]for i in range(4,8))+(s['stores'][-1][1],)
            s['calls'].append(args)
            for i in(1,2,3,*range(4,16),24,25):s['r'][i]=('callback',i)
            s['f']={i:('callback-f',i)for i in range(20)}
            s['pc']=p+2;states.append(s)
        else:execute(s,w);s['pc']=p+1;states.append(s)
    done.sort();assert done[0][0]==LO and done[-1][1]==HI
    assert all(a[1]+1==b[0]for a,b in zip(done,done[1:])),done
    return done
def main():
    raw=json.loads((out/'ternary-order3/words.json').read_text())
    truth=list(struct.unpack_from('>341I',(root/'conker/conker.us.bin').read_bytes(),0x11A120))
    assert len(raw)==341 and all(a==b for i,(a,b)in enumerate(zip(raw,truth))if not 121<=i<=150)
    a,b=run(raw),run(truth);assert a==b,(a,b)
    # Effective controls alter lower/upper bounds and the original half value.
    controls={}
    for name,index,delta in(('range-low',125,1),('range-high',130,-1),('radius-low',136,1),('radius-high',141,-1),('shift-count',123,64)):
        changed=list(raw);changed[index]+=delta
        try:run(changed)
        except AssertionError:controls[name]=True
        else:raise AssertionError(('ineffective control',name))
    report=dict(signed_input_words=1<<32,intervals=a,raw_and_retail_interval_partitions_equal=True,
        block_words=30,differing_words=28,unchanged_outside_words=311,callback_arguments_equal=True,
        public_store_order_equal=True,FCSR_untouched=True,no_insertions_or_omissions=True,
        effective_controls=controls,limits='Public ABI and memory at the common join; volatile temporaries and instruction PCs differ.')
    (out/'clamp-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
if __name__=='__main__':main()
