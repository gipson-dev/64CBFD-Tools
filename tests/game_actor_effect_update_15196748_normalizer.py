"""Derive the closed mark-ramp roles and split flag-test branch from C words."""
import hashlib,json,struct
RAW='76c87c881ddf02a35a806d08df997594fcedf4624dd0041a1cc3ae3b33a40874'
BINDINGS='56648f997cf838d34ae086cc64a40afa160eef6aaaa74c66da08a7aedf7c1d43'
position=lambda i:i+(i>130)
FIELDS={126:{16:3},129:{21:3},131:{11:3},135:{11:14},137:{16:14},140:{16:3},141:{16:11},142:{16:13},143:{21:3,16:11,11:3},144:{21:3,16:12},145:{16:13},146:{21:12,11:3},149:{16:3},153:{16:3},154:{21:3},167:{11:24},169:{16:24}}
def rename(w,m):
 op,fn=w>>26,w&63
 shifts=((16,11)if fn in(0,2,3)else(11,)if fn in(16,18)else(21,16)if fn in(25,27)else(21,16,11))if op==0 else(16,)if op==15 else(21,)if op in(49,57)else(21,16)
 for s in shifts:w=(w&~(31<<s))|(m.get(w>>s&31,w>>s&31)<<s)
 return w
def derive(words):
 assert len(words)==256;out=[]
 for i,old in enumerate(words):
  w=old
  if i in(36,111,171):
   a,b=w>>21&31,w>>16&31;w=(w&~((31<<21)|(31<<16)))|(b<<21)|(a<<16)
  for shift,value in FIELDS.get(i,{}).items():w=(w&~(31<<shift))|(value<<shift)
  if 172<=i<=181:w=rename(w,{14:12,15:13,25:14,24:15,11:25})
  if old>>26 in(1,4,5,6,7,20,21,22,23):
   target=i+1+(((old&65535)^32768)-32768);dest=position(target)
   if i==130:
    assert old==0x11E00017;dest+=1;w=(w&0x03FFFFFF)|(20<<26)
   offset=dest-position(i)-1;assert -32768<=offset<32768;w=(w&0xffff0000)|(offset&65535)
  out.append(w)
  if i==130:
   assert words[154]==0x30980004
   clone=(words[154]&~(31<<21))|(3<<21);out.append(clone)
 assert len(out)==257;return out
def normalize(data,refs):
 if hashlib.sha256(data).hexdigest()!=RAW or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=BINDINGS:raise ValueError('Effect-update source words or bindings changed')
 return struct.pack('>257I',*derive([x[0]for x in struct.iter_unpack('>I',data)])),{position(i//4)*4:rows for i,rows in refs.items()}
