"""Pinned source-derived home/register/control schedule, independently proved."""
import hashlib,json,struct
def normalize(data,refs):
 pins={'raw_sha256': '227b22bf18158df738fdd6a5cfd87663ba32cb9a4372c147f1eba10c8dd9d555', 'bindings_sha256': 'dedb355dd58065d0c297ca2d3b7ef8e1e0f0a2c510c8259da20f4f911f25c157', 'selected_source_sha256': '265f002898e814079b993c89c7b3e4ef939ba441071a59ed4422c94746944dd7'}
 if hashlib.sha256(data).hexdigest()!=pins['raw_sha256']or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=pins['bindings_sha256']:raise ValueError('Command decoder source words or bindings changed')
 words=list(struct.unpack('>95I',data));entries=[]
 def emit(src,reg=None,home=None,target=None,op=None,swap=False):entries.append((src,reg or{},home,target,op,swap))
 for i in range(6):emit(i)
 emit(7,{24:15});emit(8,{24:15},target=44);emit(6,{15:3})
 for i in range(10,16):emit(i,target={10:19,13:27}.get(i))
 emit(16,target=36,op=20);emit(9,{15:3},home=24);emit(18,target=45);emit(41,{25:3})
 for store,call,spill,branch,restore,jump,zero in((9,20,21,22,23,24,25),(9,26,27,28,29,30,31)):
  emit(store,{15:3},home=24);emit(call);emit(spill,home=40);emit(39,{25:3},home=24);emit(branch,target=44);emit(restore,home=40);emit(jump,target=96);emit(zero)
 emit(9,{15:3},home=24);emit(32);emit(33,home=40);emit(34);emit(39,{25:3},home=24);emit(35,target=44);emit(36,home=40);emit(37,target=96);emit(38)
 emit(41,{25:3});emit(42,target=69,op=5);emit(40,{8:24})
 table={8:24,9:25,10:8,11:9,12:10,13:11,25:3}
 for i in range(44,51):emit(i,table)
 emit(51,{2:12});emit(52,table);emit(53,{13:11,3:2});emit(54,{3:2},target=61);emit(55);emit(56,target=96);emit(57)
 emit(58,{2:12},target=68);emit(59,{2:12,4:7});emit(60);emit(61);emit(62,{3:2,14:13});emit(63,target=69);emit(64,{14:13,2:12},swap=True);emit(65,{4:7,3:2})
 emit(66,{2:3});emit(67,{2:3},target=94);emit(68,{9:8});emit(69,{2:3},home=24);emit(70);emit(71,home=40);emit(72,home=40);emit(74,home=24);emit(73,{24:15});emit(75,{15:14});emit(76,{15:14,24:15});emit(77,target=91)
 emit(79,{5:24});emit(78,{8:25});emit(80,{5:24},target=93);emit(81,{8:25});emit(83,{8:25});emit(82);emit(83,{8:24,4:5});emit(85);emit(84,target=94);emit(88,{9:8});emit(86,target=96);emit(87);emit(88,{9:8});emit(89);emit(90,{9:8})
 for i in range(91,95):emit(i)
 assert len(entries)==100
 result=[];bindings={}
 for dst,(src,reg,home,target,op,swap)in enumerate(entries):
  w=words[src];oldop=w>>26;fields=(21,16,11)if oldop==0 and w else(16,)if oldop==15 else(21,)if oldop==1 else(21,16)if oldop!=3 and w else()
  for shift in fields:
   value=w>>shift&31;w=(w&~(31<<shift))|(reg.get(value,value)<<shift)
  if swap:a=w>>21&31;b=w>>16&31;w=(w&~((31<<21)|(31<<16)))|(b<<21)|(a<<16)
  if home is not None:assert oldop in(35,43)and w>>21&31==29;w=(w&0xffff0000)|home
  if op is not None:w=(w&0x03ffffff)|(op<<26)
  if target is not None:assert w>>26 in(1,4,5,20,21);w=(w&0xffff0000)|((target-dst-1)&65535)
  if src*4 in refs:bindings[dst*4]=refs[src*4]
  result.append(w)
 return struct.pack('>100I',*result),bindings
