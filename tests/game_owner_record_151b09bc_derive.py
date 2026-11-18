"""Closed category role, binding home, initialization schedule and cursor bias."""
def field(w,shift,old,new):
    assert w>>shift&31==old,(hex(w),shift,old,new)
    return(w&~(31<<shift))|(new<<shift)

def immediate(w,old,new):
    assert w&65535==old&65535,(hex(w),old,new)
    return(w&~65535)|(new&65535)

def derive(words,refs=None):
    assert len(words)==115 and words[0]==0x27BDFF20 and words[112]==0x27BD00E0
    result=list(words)
    for i,shifts in ((30,(16,)),(31,(21,11)),(32,(21,16)),(34,(21,)),(39,(21,))):
        for shift in shifts:result[i]=field(result[i],shift,2,3)
    for i,old,new in ((45,0x3C,0x34),(47,0x3C,0x34),(50,0x40,0x38)):
        result[i]=immediate(result[i],old,new)
    result[73]=immediate(result[73],0x44,0x68)
    result[74]=immediate(result[74],0xA4,0xC8)
    for i in(*range(78,89),90):
        w=result[i];assert w>>26==43 and w>>21&31==2 and w>>16&31==0
        result[i]=immediate(w,w&65535,(w&65535)-0x24)
    order=(75,76,64,65,66,67,68,69,70,71,72,73,74)
    assert set(order)==set(range(64,77))
    original=result[:]
    for dest,src in enumerate(order,64):result[dest]=original[src]
    return result if refs is None else(result,dict(refs))
