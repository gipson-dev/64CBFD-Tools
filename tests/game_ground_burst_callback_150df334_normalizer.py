"""Pinned source-role normalization, justified by independent finite-path proof."""
import hashlib,json,struct
def normalize(data,refs):
 pins={'raw_sha256': 'f8e291bf34688b5249d86ac35e41b783a6f3a4cc1a438af3a31f1b84561f0d78', 'bindings_sha256': '1e095c884dcf15c3325e9bd00c6c67432cbe9a9412fc0cd7440962460247d757', 'selected_source_sha256': '3a4a1d5d9bcf6442e871299b3bd0c01920469620ff5a36914acfc70212e6bfe8'}
 if hashlib.sha256(data).hexdigest()!=pins['raw_sha256']or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=pins['bindings_sha256']:raise ValueError('Ground-burst source words or bindings changed')
 words=list(struct.unpack('>98I',data));assert words[25]==words[40]==0x26030028 and words[35]==0x00602025 and words[41]==0xafa3003c and words[55]==0x8fa2003c and words[56]==0x51000003 and words[57]==words[59]==0x8c410000
 order=[*range(26),'base-v0',*range(26,35),36,37,39,38,*range(42,49),50,49,*range(51,58),'select-contact',*range(58,98)]
 assert len(order)==97 and sorted(i for i in order if isinstance(i,int))==[i for i in range(98)if i not in(35,40,41)]
 positions={i:n for n,i in enumerate(order)if isinstance(i,int)};out=[];bindings={}
 for src in order:
  dst=len(out)
  if src=='base-v0':out.append((words[25]&~(31<<16))|(2<<16));continue
  if src=='select-contact':out.append(0x10000000|((positions[59]-dst-1)&65535));continue
  word=words[src];op=word>>26;rs=word>>21&31;imm=word&65535
  # Shift the entire escaped vector/result block four bytes downward.
  # Frame size, callee saves, outgoing homes and selected-pointer home stay fixed.
  if rs==29 and op in(9,32,33,35,36,37,40,41,43,49,57)and 76<=imm<152:word=(word&0xffff0000)|(imm-4)
  if src==25:word=(word&~(31<<16))|(4<<16) # Default first argument, not CSE carrier V1.
  if src in(26,31):
   assert op==49 and rs==16 and imm in(40,48);word=(word&~((31<<21)|65535))|(2<<21)|(imm-40)
  if src==55:word=(words[25]&~(31<<16))|(2<<16) # Rematerialize immutable owner+0x28.
  if src==57:word=0 # The common load remains at source59 on both paths.
  if op in(4,5,6,7,20,21,22,23):
   target=src+1+(((imm^32768)-32768))
   if target==41:target=42 # Omitted unescaped CSE cache store.
   if src==56:word=(word&0x03ffffff)|(4<<26);target=59 # Branch-likely to ordinary choice.
   word=(word&0xffff0000)|((positions[target]-dst-1)&65535)
  if src*4 in refs:bindings[dst*4]=refs[src*4]
  out.append(word)
 return struct.pack('>97I',*out),bindings
