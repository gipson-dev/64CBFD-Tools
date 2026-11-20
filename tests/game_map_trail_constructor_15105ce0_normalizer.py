"""Derive arithmetic/register groups from the complete source payload."""
import hashlib,json,struct
from pathlib import Path
SPEC=json.loads((Path(__file__).resolve().parents[1]/'experiments/game_map_trail_constructor_15105ce0_match_manifest.json').read_text())
# Closed schedule of descriptor initialization and address materialization.
ORDER={85: 111,
 86: 112,
 92: 85,
 93: 86,
 94: 92,
 95: 93,
 96: 94,
 97: 95,
 98: 96,
 99: 97,
 100: 98,
 101: 99,
 102: 100,
 103: 101,
 104: 102,
 105: 103,
 106: 104,
 107: 105,
 108: 106,
 109: 107,
 110: 108,
 111: 109,
 112: 110,
 113: 115,
 114: 116,
 115: 113,
 116: 114,
 117: 119,
 118: 120,
 119: 117,
 120: 118,
 121: 124,
 122: 129,
 123: 121,
 124: 122,
 125: 123,
 126: 132,
 127: 125,
 128: 126,
 129: 127,
 130: 128,
 131: 137,
 132: 130,
 133: 131,
 134: 133,
 135: 140,
 136: 134,
 137: 135,
 138: 136,
 139: 141,
 140: 138,
 141: 139,
 142: 145,
 143: 174,
 144: 142,
 145: 143,
 146: 144,
 147: 175,
 148: 146,
 149: 147,
 150: 148,
 151: 149,
 152: 150,
 153: 151,
 154: 152,
 155: 153,
 156: 154,
 157: 155,
 158: 156,
 159: 157,
 160: 158,
 161: 159,
 162: 160,
 163: 161,
 164: 162,
 165: 163,
 166: 164,
 167: 165,
 168: 166,
 169: 167,
 170: 168,
 171: 169,
 172: 170,
 173: 171,
 174: 172,
 175: 173}

def rename(word,mapping):
 op,fn,rs=word>>26,word&63,word>>21&31
 fields=(21,16,11)if op==0 else(21,16)if op in(4,5,6,7,9,10,11,12,13,15,32,33,35,36,37,40,41,43)else(21,)if op in(49,53,57,61)else(16,)if op==17 and rs in(0,4)else()
 for shift in fields:
  old=word>>shift&31
  if old in mapping:word=(word&~(31<<shift))|(mapping[old]<<shift)
 return word

def groups(raw,refs):
 words=list(struct.unpack('>233I',raw));result=words[:]
 # Keep the input count in V0 until the allocator delay transfers it to S1.
 result[17]=(words[17]&~(31<<16))|(2<<16)
 result[20]=(words[20]&~(31<<21))|(3<<21)
 for at in range(21,30):result[at]=rename(words[at],{16:2})
 result[30]=rename(words[30],{17:16})
 # Undo 12*n+24 -> 12*(n+2); the independent CFG proof checks this algebra.
 assert words[31]&65535==24
 result[31]=(9<<26)|(2<<21)|(3<<16)|2
 result[32]=rename(words[32],{17:16})
 for at in range(44,48):result[at]=rename(words[at],{16:17})
 result[48]=(words[48]&~(31<<11))|(25<<11)
 stop=next(at//4 for at,rs in refs.items()if rs==[('R_MIPS_26','func_15106214')])
 scratch={8:25,9:8,10:9,11:10,12:11,13:12,14:13,15:14,24:15,25:24,16:17,17:16}
 for at in range(49,stop):result[at]=rename(words[at],scratch)
 post=next(at//4 for at,rs in refs.items()if rs==[('R_MIPS_26','bzero')])+2
 for at in(post,post+3,post+4):result[at]=rename(words[at],{9:8,10:9})
 result[post+5]=(words[post+5]&~(31<<16))|(9<<16)
 # Every source word has one output origin. Add only the live saved-count
 # transfer and the original FP pipeline NOP; neither is a retail-word array.
 order=list(range(20))+[31]+list(range(20,31))+[32,33,35,34,None]+list(range(36,233))
 items=[(origin,(0x25|(2<<21)|(17<<11))if origin is None else result[origin])for origin in order]
 second=next(i for i,(_,w)in enumerate(items)if w==0x46105482)
 items.insert(second,(None,0))
 assert len(items)==235
 return items

def branches(items,words):
 positions={origin:i for i,(origin,_)in enumerate(items)if origin is not None}
 output=[]
 for i,(origin,w)in enumerate(items):
  if origin is not None and w>>26 in(1,4,5,6,7,20,21,22,23):
   destination=origin+1+(((words[origin]&65535)^32768)-32768)
   assert destination in positions,(origin,destination)
   w=(w&0xFFFF0000)|((positions[destination]-i-1)&65535)
  output.append(w)
 return output

def normalize(raw,refs):
 if len(raw)!=932 or hashlib.sha256(raw).hexdigest()!=SPEC['raw_sha256'] or json.loads(json.dumps(refs))!=SPEC['refs']:
  raise ValueError('Constructor source words or bindings changed')
 source=list(struct.unpack('>233I',raw));items=groups(raw,refs)
 assert set(ORDER)==set(ORDER.values())
 ordered=[items[ORDER.get(i,i)]for i in range(235)]
 assert sorted(origin for origin,_ in ordered if origin is not None)==list(range(233))
 words=branches(ordered,source);bindings={}
 for i,(origin,_)in enumerate(ordered):
  if origin is not None and origin*4 in refs:bindings[4*i]=refs[4*origin]
 inserted=[i for i,(origin,_)in enumerate(ordered)if origin is None]
 assert inserted==[36,176]
 return struct.pack('>235I',*words),bindings
