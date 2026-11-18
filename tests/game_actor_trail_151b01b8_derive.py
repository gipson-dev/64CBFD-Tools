"""Closed instruction permutation, temporary roles and unexposed pointer home."""
ORDER = (67,66,68,76,69,70,73,77,71,72,74,105,75,79,78,89,80,81,82,83,84,85,86,87,
         88,106,90,91,92,93,94,95,96,97,98,99,100,101,102,103,108,104,110,111,112,113,107,109)
assert len(ORDER) == 48 and set(ORDER) == set(range(66,114))

def field(w, shift, old, new):
    assert w >> shift & 31 == old, (hex(w),shift,old,new)
    return (w & ~(31 << shift)) | (new << shift)

def derive(words, refs=None):
    assert len(words) == 128 and words[0] == 0x27BDFF60 and words[125] == 0x27BD00A0
    result = list(words)
    # The selected record's V0 lifetime maps to V1 and dies at submission.
    for i,shift in ((42,11),(43,21),(55,16),(76,16),(105,21)):
        result[i] = field(result[i],shift,2,3)
    for i in (55,76):
        assert result[i] >> 21 & 31 == 29 and result[i] & 65535 == 0x28
        result[i] = (result[i] & ~65535) | 0x20
    # Four short, disjoint heading/count lifetimes use different round-robin roles.
    for i,fields in ((67,((16,13,15),)),(73,((21,13,15),(16,14,24))),
                     (77,((16,14,24),)),(75,((16,15,13),)),(78,((16,15,13),)),
                     (79,((16,24,14),)),(89,((16,24,14),))):
        for shift,old,new in fields: result[i] = field(result[i],shift,old,new)
    original = result[:]
    for dest,src in enumerate(ORDER,66): result[dest] = original[src]
    if refs is None: return result
    destinations = {src:dest for dest,src in enumerate(ORDER,66)}
    moved = {4*destinations.get(off//4,off//4):rows for off,rows in refs.items()}
    assert len(moved) == len(refs)
    return result,moved
