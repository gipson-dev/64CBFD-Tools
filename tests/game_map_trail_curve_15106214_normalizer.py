"""Closed derivation of private frame padding and an independent opening move.

Only the two stack adjustments and four opening positions change. Every source
instruction occurs once. No arithmetic, public access, FP order or binding is
changed. No private address is passed to any callee. This is not a fault/timing
equivalence claim.
"""
import hashlib
import struct

def derive(raw, refs):
    assert len(raw)==168*4
    assert hashlib.sha256(raw).hexdigest()=='aa7f42dc99ffc1882930fc6e3a2b85ada999a1267dec9319e6e7b808560b0d52'
    words=list(struct.unpack('>168I',raw))
    assert words[0]==0x27BDFF78 and words[167]==0x27BD0088
    assert words[19:23]==[0x00408825,0x00009025,0x19C00083,0x46001506]
    assert not any(index*4 in refs for index in(0,19,20,21,22,167))
    # All frame-relative data are inside the retained 128-byte frame. No SP
    # materialization leaves via arguments; callees may overwrite outgoing homes.
    homes=[]
    for index,word in enumerate(words):
        op,rs,rt=word>>26,word>>21&31,word>>16&31
        immediate=((word&65535)^32768)-32768
        if rs==29 and op in(32,33,35,36,37,40,41,43,49,53,57,61):
            size=8 if op in(53,61)else 4 if op in(35,43,49,57)else 2 if op in(33,37,41)else 1
            assert 0x10<=immediate and immediate+size<=128,(index,hex(word))
            homes.append((index,immediate,size))
        elif rs==29 and op==9:
            assert rt==29 and index in(0,167),'Exposed private address'
    assert len(homes)==32,len(homes)
    origin=list(range(168))
    origin[19:23]=[20,21,22,19]
    assert sorted(origin)==list(range(168))
    output=[words[i]for i in origin]
    output[0]=(output[0]&0xFFFF0000)|((output[0]+8)&65535)
    output[20]=(output[20]&0xFFFF0000)|((output[20]+1)&65535)
    output[167]=(output[167]&0xFFFF0000)|((output[167]-8)&65535)
    assert output[20]&65535==0x84
    # The moved branch still reaches index153; its original FP delay executes
    # on both outcomes. S1 is written only on the nonempty path and is restored
    # from its saved entry value on both exits.
    assert 20+1+(output[20]&65535)==153
    return struct.pack('>168I',*output),dict(refs),dict(frame_before=136,frame_after=128,
        origins=origin,private_accesses=homes,insertions=0,omissions=0,
        public_and_FP_instructions_unchanged=True,private_addresses_exposed=False)
