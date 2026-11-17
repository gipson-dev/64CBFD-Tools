"""Private provider/UV allocation closure, with explicit instruction origins."""
from pathlib import Path
import json,struct
from tools.tests import game_strip_draw_151ad92c_geometry_normalization as geometry
from tools.experiments import game_strip_draw_151ad92c_recovery as source
import hashlib
p=source.OUT
index=geometry.index

def branch(w):return w>>26 in(1,4,5,6,7,20,21,22,23)or w>>26==17 and w>>21&31==8

def derive(raw):
    assert len(raw)==469 and hashlib.sha256(struct.pack('>469I',*raw)).hexdigest()==source.PIN['bound_raw_sha256']
    words,prior=geometry.derive(raw)
    edits=[]
    def change(address,before,after,why):
        i=index(address);assert words[i]==before,(hex(address),hex(words[i]),hex(before))
        words[i]=after;edits.append(dict(index=i,expected=before,replacement=after,reason=why))
    change(0x1FAC,0xAFA80094,0xAFA80124,'captured count home')
    change(0x1FD8,0x8FA80094,0x8FA80124,'reload captured count')
    change(0x2048,0x00001825,0x8FA30128,'reload zero segment cursor after opaque call')
    change(0x209C,0xAFA50090,0xAFA50094,'UV terminal index home')
    change(0x21D0,0x8FAF0090,0x8FAF0094,'reload UV terminal index')
    change(0x20A0,0xAFAF012C,0x01E0B025,'retain packed U in freed S6')
    change(0x2140,0x8FAE012C,0x02C07025,'read retained packed U')
    change(0x2164,0x8FAF012C,0x02C07825,'read retained packed U')
    change(0x2158,0xACF60000,0xACF90000,'consume rematerialized modify-vertex header')
    a,b=index(0x2054),index(0x2090)
    assert words[a]==0x3C160214 and words[b]==0x36D60008
    materialize=[0x3C190214,0x37390008]
    nop=index(0x1CFC)-2
    removed={nop,*range(index(0x1F10),index(0x1F20)),a,b,index(0x2044)}
    for i in {nop,*range(index(0x1F10),index(0x1F20))}:
        assert words[i]==0 and not branch(words[i-1]),('vacant slot',i,hex(words[i]))
    assert words[index(0x2044)]>>26==6
    # Its source operand equals the first guard's operand and has no intervening
    # writer; retaining the former delay instruction preserves index restoration.
    assert words[index(0x2034)]>>26==6
    assert words[index(0x2034)]>>21&31==words[index(0x2044)]>>21&31==5
    assert words[index(0x2038)]>>16&31==17 and words[index(0x203C)]>>11&31==15
    inserts={index(0x1FAC)+1:[0xAFA00128],index(0x2154):materialize[:1],index(0x2158):materialize[1:]}
    output=[];origins={};insertions=[]
    for i,w in enumerate(words):
        for new in inserts.get(i,[]):
            insertions.append(dict(before_source_index=i,output_index=len(output),word=new));output.append(new)
        if i not in removed:origins[i]=len(output);output.append(w)
    def destination(old):
        while old in removed:old+=1
        assert old in origins,('branch destination',old)
        return origins[old]
    branches=[]
    for old,new in origins.items():
        w=words[old]
        if branch(w):
            target=old+1+(((w&65535)^32768)-32768)
            offset=destination(target)-new-1;assert -32768<=offset<=32767
            output[new]=w&0xFFFF0000|offset&65535
            branches.append(dict(source_index=old,output_index=new,source_target=target,output_target=destination(target)))
    assert len(output)==464,len(output)
    return output,dict(origin_map=origins,previous=prior,edits=edits,removed_source_indices=sorted(removed),insertions=insertions,branches=branches,words=len(output),source_installed=False,c_match_credit=0)
