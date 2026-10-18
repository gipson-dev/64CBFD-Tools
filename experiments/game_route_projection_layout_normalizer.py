"""Experimental closed route-projection layout recipe; never installs guards."""
import hashlib
import struct

from tools.experiments import game_route_projection_call_lifetime_fit as source

GP={
    10:{6:2},12:{6:2},15:{12:11},19:{12:11},23:{6:2},25:{11:10},26:{11:10},28:{12:11,2:3},
    31:{2:3},32:{6:2},33:{9:7},34:{9:7},35:{10:9},36:{7:8},37:{8:6},39:{6:2,14:12},
    40:{13:12,14:13},41:{15:14},42:{10:9,15:14},43:{6:2},44:{24:15},45:{11:10,24:15},
    46:{6:2},47:{6:2},48:{6:2},49:{4:3},50:{8:6},52:{9:7},56:{4:3,13:24},
    57:{25:24,13:25,14:12},58:{14:12,15:13},59:{7:8,15:13},63:{24:15},64:{4:3,25:14},
    65:{24:14,25:15,13:24},66:{13:24,14:25},67:{7:8,14:25},72:{4:3},73:{8:6},74:{3:4},
    75:{9:7},78:{15:13},79:{4:3,24:12},80:{15:12,24:13,25:14},81:{25:14,13:15},
    82:{7:8,13:15},85:{3:4},86:{14:25},87:{4:3,15:24},88:{14:24,15:25,24:12},
    89:{24:12,25:13},90:{7:8,25:13},91:{3:4},93:{3:4},94:{8:6,3:4},95:{3:4},96:{9:7},
    97:{13:15},98:{3:4},100:{13:14,14:15,15:3},101:{15:3},102:{7:8},103:{3:4},105:{3:4},
    106:{14:3,15:25},107:{7:8,15:25},108:{3:4},109:{3:4},110:{3:4},111:{8:6,3:4},
    112:{3:4},113:{9:7},114:{24:13},115:{3:4,25:12},117:{24:12,25:13,13:3},
    118:{13:3},119:{7:8},120:{3:4},122:{3:4},123:{25:3,13:15},124:{7:8,13:15},
    125:{3:4},126:{3:4},127:{3:4},128:{8:6,3:4},129:{12:11,2:3},130:{9:7},131:{14:25},
    132:{3:4,15:24},134:{14:24,15:25,24:3},135:{24:3,25:12},136:{7:8,25:12},
    137:{3:4},139:{12:11,2:3},140:{15:3,24:13},141:{7:8,24:13},142:{12:11,2:3},
    143:{3:4},144:{12:11,2:3},145:{2:3,6:2},146:{6:2},147:{6:2,2:3},156:{3:9},
    157:{25:15},158:{13:14},163:{3:9},166:{25:14,13:15},167:{14:24},168:{15:25},
    170:{14:24},174:{15:25},176:{3:9},191:{19:9,3:19},192:{25:15},197:{24:8},198:{24:8},
    200:{19:9},203:{19:9,25:13},205:{2:13,25:2},211:{20:8},214:{20:8,13:12},
    215:{2:12,13:2},216:{19:9},218:{20:8},242:{19:9},249:{13:12},250:{14:13},
    252:{13:12},255:{14:13},259:{15:14},262:{15:14},276:{18:6},280:{18:6},284:{18:6},
    286:{18:6},290:{18:6},294:{18:6},297:{18:6},299:{18:6},300:{18:6},301:{18:6},
    302:{18:6},307:{24:2},308:{24:2},309:{24:2},310:{24:2},311:{24:2},
}
FP={296:{6:10},298:{18:6},301:{6:10},302:{18:6}}
PAYLOAD_STORES=(289,293,297,300,304,309,311,312,314,315,316)
NORMALIZED_SHA='5936953663607ec290a2477db4347861ac88136b1ba4a02f64e0a5e2486b733a'


def origins(words):
    blocks=[i for i,w in enumerate(words[:164]) if w==0x81220000]
    moves=[i for i,w in enumerate(words[:164]) if w==0x00801825]
    if len(blocks)!=5 or len(moves)!=2:raise ValueError('Unknown split-scan structure')
    skip=set(moves);replace={}
    for b in blocks[2:]:
        if words[b+2]!=0 or any(words[b+n]>>26!=35 for n in (3,11)):
            raise ValueError('Unknown duplicate scan-address computation')
        replace[b]=[b,b+3,b+4,b+1,b+5,b+6,b+7,b+8,b+9,b+10,b+14]
        skip.update(range(b+1,b+15))
    result=[]
    for i in range(len(words)):
        if i not in skip:result.extend(replace.get(i,[i]))
    i,j=result.index(36),result.index(37);result[i],result[j]=result[j],result[i]
    i,j=result.index(168),result.index(169);result[i],result[j]=result[j],result[i]
    result.remove(299);result.insert(result.index(278),299)
    i=result.index(308)
    if result[i:i+9]!=list(range(308,317)):raise ValueError('Unknown payload schedule')
    result[i:i+9]=[309,310,308,311,313,312,314,315,316]
    if len(result)!=321 or len(set(result))!=321:raise ValueError('Unknown contraction extent')
    return result


def fields(word):
    op,rs,fn=word>>26,word>>21&31,word&63
    if op==0:
        if fn==0:return (16,11),()
        if fn in (33,37,42):return (21,16,11),()
        if fn==8:return (21,),()
    if op in (4,5,20,21,9,12,32,33,35,36,37,40,41,43):return (21,16),()
    if op in (6,7):return (21,),()
    if op==15:return (16,),()
    if op==3:return (),()
    if op in (49,57):return (21,),(16,)
    if op==17:
        if rs==4:return (16,),(11,)
        if rs==8:return (),()
        if rs==20 and fn==32:return (),(11,6)
        if rs==16 and fn in (0,1,2,3,4,6,60):
            return (),((16,11) if fn==60 else (11,6) if fn in (4,6) else (16,11,6))
    raise ValueError('Unsupported projection layout instruction: %08X'%word)


def normalize(raw,bindings):
    if len(raw)!=1340 or hashlib.sha256(raw).hexdigest()!=source.RAW_SHA or bindings!=source.BINDINGS:
        raise ValueError('Unknown joint projection body or bindings')
    words=list(struct.unpack('>335I',raw));order=origins(words)
    destination={old:new for new,old in enumerate(order)};result=[]
    for new,old in enumerate(order):
        word=words[old];op,rs=word>>26,word>>21&31
        if op in (4,5,6,7,20,21) or op==17 and rs==8:
            target=old+1+(((word&65535)^32768)-32768)
            if target not in destination:raise ValueError('Removed branch destination')
            offset=destination[target]-new-1
            if not -32768<=offset<32768:raise ValueError('Projection branch out of range')
            word=word&0xFFFF0000|offset&65535
        if old in PAYLOAD_STORES:
            if op not in (43,57) or rs!=18 or not 0x4C<=word&65535<=0x80:
                raise ValueError('Unknown projection payload base')
            word=word&0xFFFF0000|((word&65535)-0x4C)
        for shifts,rename in zip(fields(word),(GP.get(new,{}),FP.get(new,{}))):
            present={word>>shift&31 for shift in shifts}
            if not set(rename)<=present or any(not 0<=v<32 for v in rename.values()):
                raise ValueError('Unknown projection register recipe')
            original=word
            for shift in shifts:
                reg=original>>shift&31
                word=word&~(31<<shift)|rename.get(reg,reg)<<shift
        result.append(word)
    moved={destination[at//4]*4:entries for at,entries in bindings.items()}
    if len(moved)!=18:raise ValueError('Lost projection binding')
    normalized=struct.pack('>321I',*result)
    if hashlib.sha256(normalized).hexdigest()!=NORMALIZED_SHA:raise ValueError('Changed projection layout recipe')
    return normalized,moved


def relocate(raw,bindings,anchors):
    words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    for at,entries in bindings.items():
        if len(entries)!=1:raise ValueError('Unknown projection relocation group')
        kind,name=entries[0];value=anchors[name]
        if kind=='R_MIPS_HI16':words[at//4]=words[at//4]&0xFFFF0000|((value+0x8000)>>16)&65535
        elif kind=='R_MIPS_LO16':words[at//4]=words[at//4]&0xFFFF0000|value&65535
        elif kind=='R_MIPS_26':
            if value&3 or value>>28!=source.source.ENTRY>>28:raise ValueError('Invalid projection call rebase')
            words[at//4]=words[at//4]&0xFC000000|(value>>2)&0x3FFFFFF
        else:raise ValueError('Unknown projection relocation kind')
    return words
