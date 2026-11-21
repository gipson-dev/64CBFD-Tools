"""Move the dominated zero return into the default block; preserve every word."""
import hashlib,struct
ORDER=tuple(range(8))+tuple(range(9,87))+(8,)+tuple(range(87,92))
RAW_SHA256='7781565d57520a7af31c3d64a613b1452740b73d692ed77233786e078fa9f3b4'
def emit(blob,refs):
    assert len(blob)==368 and hashlib.sha256(blob).hexdigest()==RAW_SHA256
    words=struct.unpack('>92I',blob)
    assert words[8]==0x00001025 and words[7]==0x1020004f
    assert sorted(ORDER)==list(range(92))
    inverse={old:new for new,old in enumerate(ORDER)}
    result=[];branches=[]
    for new,old in enumerate(ORDER):
        word=words[old]
        if word>>26 in(4,5,6,7,20,21,22,23):
            target=old+1+((word&65535)^32768)-32768
            assert 0<=target<92,(old,target)
            destination=86 if old==7 else inverse[target]
            word=(word&0xffff0000)|((destination-new-1)&65535)
            branches.append(dict(input=old,output=new,old_target=target,new_target=destination))
        result.append(word)
    revised={4*inverse[int(offset)//4]:entries for offset,entries in refs.items()}
    assert len(revised)==len(refs)==17
    return struct.pack('>92I',*result),revised,branches
