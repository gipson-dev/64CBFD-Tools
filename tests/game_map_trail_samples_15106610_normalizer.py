"""Derive the retail register cycle and fold a duplicated loop-entry copy."""
import hashlib,struct

def rename(word):
    op=word>>26;roles={18:19,19:20,20:18}
    fields=[]
    if op==0:fields=[21,16,11]
    elif op in(4,5,8,9,10,11,12,13,14,20,21,40,41,43):fields=[21,16]
    elif op in(32,33,35,36,37):fields=[21,16]
    elif op in(49,53,57,61):fields=[21]
    elif op==15:fields=[16]
    elif op==17 and(word>>21&31)in(0,2,4,6):fields=[16]
    for shift in fields:
        reg=word>>shift&31
        if reg in roles:word=(word&~(31<<shift))|(roles[reg]<<shift)
    return word

def derive(raw,refs):
    assert hashlib.sha256(raw).hexdigest()=='662775b2c0f5173013bca0dca5bd2ce2b05280d1c54be0a31e8e5bf074172fb3'
    words=list(struct.unpack('>107I',raw))
    assert words[0]==0x27BDFF90 and words[106]==0x27BD0070
    assert words[43]==words[94]==0x02408825
    assert words[42]==0x14200034 and words[93]==0x5020FFCE
    assert [words[i]for i in(64,66,67)]==[0x26940001,0x2652000C,0x26730034]
    assert words[51]==0x46002182
    assert words[23]==0x27BE0054 and words[26]==0x27B70050
    # The moved increments touch only the three private induction registers.
    # Every crossed instruction is FP work or a public/private data access
    # based on a different register; the late count load writes T9 only.
    for index in(65,*range(68,92)):
        word=words[index];op=word>>26;rs=word>>21&31;rt=word>>16&31
        if op==17:assert rs==16
        elif op in(49,57):assert rs not in(18,19,20)
        elif op==35:assert rs not in(18,19,20)and rt not in(18,19,20)
        else:assert word==0,(index,hex(word))
    origins=[*range(64),65,*range(68,92),64,66,92,93,67,*range(95,107)]
    assert len(origins)==106 and sorted(origins)==[i for i in range(107)if i!=94]
    output=[rename(words[i])if 18<=i<=93 else words[i]for i in origins]
    output[42]=(output[42]&0xFFFF0000)|0x33
    output[51]=(output[51]&~((31<<16)|(31<<11)))|((output[51]>>16&31)<<11)|((output[51]>>11&31)<<16)
    output[92]&=~0x40000000 # BEQL -> BEQ; loop-entry copy is now shared.
    bound={origins.index(offset//4)*4:rows for offset,rows in refs.items()}
    assert bound==refs,'Call bindings moved unexpectedly'
    assert [output[i]for i in(43,45,89,90,93)]==[0x02608825,0x02808025,0x26520001,0x2673000C,0x26940034]
    private=lambda stream:[w for w in stream if (w>>21&31)==29 and w>>26 in(9,35,43,49,57)]
    assert private(words)==private(output),'Frame or exposed private-access sequence changed'
    assert 42+1+(output[42]&65535)==94
    assert 92+1+((output[92]&65535)^32768)-32768==43
    proof=dict(origins=origins,omitted_origins=[94],omission='duplicated taken-edge output-cursor copy',
               saved_register_cycle={18:19,19:20,20:18},frame=112,
               exposed_float_homes=[80,84],radius_multiply_commuted=True,
               public_access_and_call_order_preserved=True,private_access_sequence_identical=True,
               moved_increment_crossings_independent=True,ordinary_finite_FP_contract=True)
    return struct.pack('>106I',*output),bound,proof
