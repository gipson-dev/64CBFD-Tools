"""Closed allocation/schedule transform; no retail byte input or text recipe."""
import hashlib,json,struct
RAW='f236366ba057e97e04bf655a5a1c71852f8cd8293b6edbc83eaee22b7316cbf6'
BINDINGS='a61fc8fe497e2fc3f5aebb793f9fa057ad92ef5d8f63205a64ceeee9f88ac678'
ORDER=[0,6,1,7,2,3,4,5,*range(8,52),53,52,*range(54,105),'record-copy','slot-shift',105,107,106,108,123,'primary-index-copy',111,110,109,112,*range(113,123),*range(124,138),152,'secondary-index-copy',140,139,138,141,*range(142,152),*range(153,167),168,167,*range(169,175),176,175,*range(177,184),'link-join',*range(184,197)]
POS={old:i for i,old in enumerate(ORDER)}
def fields(w,**kw):
 for name,value in kw.items():
  shift,bits={'rs':(21,5),'rt':(16,5),'rd':(11,5),'sa':(6,5),'fn':(0,6),'imm':(0,16)}[name]
  w=(w&~(((1<<bits)-1)<<shift))|((value&((1<<bits)-1))<<shift)
 return w
def rename(w,m):
 shifts=(21,16,11)if w>>26==0 else(21,16)
 for shift in shifts:w=(w&~(31<<shift))|(m.get(w>>shift&31,w>>shift&31)<<shift)
 return w
def normalize(data,refs):
 if hashlib.sha256(data).hexdigest()!=RAW or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=BINDINGS:raise ValueError('Texture scroll source words or bindings changed')
 ws=[x[0]for x in struct.iter_unpack('>I',data)]
 assert len(ws)==197 and len(ORDER)==202 and sorted(x for x in ORDER if isinstance(x,int))==list(range(197))
 out=[];bindings={}
 for old in ORDER:
  at=len(out)
  if isinstance(old,str):
   if old=='record-copy':w=fields(ws[105],rd=18)
   elif old=='slot-shift':w=fields(ws[40],rt=5,rd=10,sa=1)
   elif old in('primary-index-copy','secondary-index-copy'):w=fields(ws[26],rs=2,rd=5)
   else:
    assert old=='link-join';w=fields(ws[89],imm=POS[185]-at-1)
   out.append(w);continue
  w=ws[old]
  if old==2:w=fields(w,rd=17)
  elif old==7:w=fields(w,rd=16)
  elif old==15:w=fields(w,rt=7)
  elif 17<=old<=41:
   w=rename(w,{10:12,11:13,12:10,13:11,18:2,17:18,19:20,20:19,2:3,3:5})
  elif 42<=old<=69:
   w=rename(w,{18:2,17:18,20:19,2:3,5:7})
   if old==52:w=fields(w,imm=-4)
  elif 70<=old<=103:
   w=rename(w,{10:12,11:13,12:10,13:11})
   if old in(81,85):w=fields(w,rs=w>>16&31,rt=w>>21&31)
   if old in(99,101):w=fields(w,rt=24)
  elif old==104:w=fields(w,rs=4,rt=24)
  elif old in(105,133):w=fields(w,rs=6,rt=10,rd=11,fn=33)
  elif old==106:w=fields(w,rt=5,rd=12,fn=33)
  elif old==107:w=fields(w,rs=11,rt=2)
  elif old in(108,130):w=fields(w,rs=12,rt=25)
  elif old==109:w=fields(w,rt=5,rd=14)
  elif old==110:w=fields(w,rd=3)
  elif old==111:w=fields(w,rs=25)
  elif old==112:w=fields(w,rs=16,rt=14,rd=13)
  elif 113<=old<=122:w=rename(w,{18:2,2:3,17:13,11:12})
  elif old in(123,124,152,153):w=rename(w,{3:10})
  elif old in(125,154):w=rename(w,{10:11})
  elif old in(127,156):w=rename(w,{11:12})
  elif old in(128,136,157):w=fields(w,rs=11,rt=2)
  elif old in(129,158):w=fields(w,rt=2)
  elif old==131:w=fields(w,rs=18)
  elif old==132:w=fields(ws[40],rt=0,rd=10,sa=1)
  elif old==135:w=fields(w,rd=12,fn=33)
  elif old in(137,159):w=fields(w,rs=12,rt=14)
  elif old==138:w=fields(w,rt=5)
  elif old==139:w=fields(w,rd=3)
  elif old==140:w=fields(w,rs=14)
  elif old==141:w=fields(w,rs=17,rd=13)
  elif 142<=old<=151:w=rename(w,{18:2,2:3,17:13,11:12,25:24,14:25})
  elif old==160:w=fields(w,rt=11)
  elif old in(161,185):w=fields(w,rs=11)
  elif old in(163,174,186):w=fields(w,rs=11,rt=14)
  elif old==164:w=fields(w,rs=11,rt=5)
  elif old==165:w=fields(w,rd=3)
  elif old==166:w=fields(w,rs=14)
  elif old==167:w=fields(w,rt=5,rd=10)
  elif old==168:w=fields(w,rt=2)
  elif old in(169,179):w=fields(w,rs=11,rt=24)
  elif old==170:w=fields(w,rs=2,rt=15)
  elif old==171:w=fields(w,rs=3,rt=3)
  elif old==172:w=fields(w,rs=24,rt=10,rd=25)
  elif old==173:w=fields(w,rs=25,rt=15)
  elif old==175:w=fields(w,rs=2,rt=2)
  elif old==176:w=fields(w,rs=10,rt=10)
  elif old==177:w=fields(w,rs=3,rt=14)
  elif old==180:w=fields(w,rs=11)
  elif old==181:w=fields(w,rd=11)
  elif old==184:w=fields(w,rd=11)
  elif old==189:w=fields(w,rt=12)
  if w>>26 in(1,4,5,6,7,20,21,22,23):
   target=old+1+(((ws[old]&65535)^32768)-32768)
   target={111:124,129:123,140:153,158:152}.get(old,target)
   w=fields(w,imm=POS[target]-at-1)
  if old*4 in refs:bindings[at*4]=refs[old*4]
  out.append(w)
 return struct.pack('>202I',*out),bindings
