"""Recover original fields/schedule from qualified C, with no retail word array."""
from pathlib import Path
import hashlib,json,struct
from tools.experiments import game_attached_accumulator_150ba55c_recovery as source
from tools.tests.game_attached_accumulator_150ba55c_proof import project
PIN=json.loads((Path(__file__).parents[1]/'experiments/game_attached_accumulator_150ba55c_normalizer_manifest.json').read_text())
def verify(words,refs):
 assert len(words)==229 and hashlib.sha256(struct.pack('>229I',*words)).hexdigest()==source.PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in rows]for k,rows in source.PIN['refs'].items()}
def derive(words,refs=None):
 assert len(words)==229
 if refs is not None:verify(words,refs)
 values=[];bindings=None if refs is None else{k:list(v)for k,v in refs.items()}
 for word in words:
  op,rs,rt,fmt=word>>26,word>>21&31,word>>16&31,word>>21&31
  if op==9 and rs==rt==29:
   imm=((word&65535)^32768)-32768;assert abs(imm)==280;word=word&0xffff0000|((264 if imm>0 else -264)&65535)
  elif rs==29 and op in(9,32,33,35,36,37,40,41,43,49,57):
   off=((word&65535)^32768)-32768;word=word&0xffff0000|((project(off-280)+264)&65535)
  fields=(16,)if op in(49,57)else(11,)if op==17 and fmt in(0,4)else(6,11,16)if op==17 and fmt==16 else()
  for shift in fields:
   reg=word>>shift&31
   if str(reg)in PIN['FP_roles']:word=word&~(31<<shift)|(PIN['FP_roles'][str(reg)]<<shift)
  values.append(word)
 hi,lo,load,rotation=PIN['address_roles'];assert(hi,lo,load,rotation)==(75,77,132,197)
 assert words[hi]>>26==15 and words[hi]>>16&31==30
 assert words[lo]>>26==9 and words[lo]>>21&31==words[lo]>>16&31==30
 assert words[load]>>26==49 and words[load]>>21&31==30 and words[load]&65535==0
 assert words[rotation]>>26==9 and words[rotation]>>21&31==29 and words[rotation]>>16&31==5
 values[hi]=values[hi]&~(31<<16)|(1<<16)
 values[lo]=(9<<26)|(29<<21)|(30<<16)|(values[rotation]&65535)
 values[load]=values[load]&~((31<<21)|65535)|(1<<21)|(words[lo]&65535)
 values[rotation]=(30<<21)|(5<<11)|37
 if bindings is not None:
  assert bindings[4*hi]==[('R_MIPS_HI16','D_8009FE40')]and bindings[4*lo]==[('R_MIPS_LO16','D_8009FE40')]and 4*load not in bindings
  bindings[4*load]=bindings.pop(4*lo)
 first,second=PIN['average_fields'];assert(first,second)==(54,55)
 assert all(values[i]>>26==49 and values[i]>>21&31==20 for i in(first,second))
 assert(values[first]&65535,values[second]&65535)==(0x150,0x14c)
 a,b=values[first],values[second];values[first]=(a&0xffff0000)|(b&65535);values[second]=(b&0xffff0000)|(a&65535)
 order=PIN['order'];assert sorted(order)==list(range(229))and order==list(range(75))+list(range(76,132))+[75]+list(range(132,229))
 inverse={old:new for new,old in enumerate(order)};result=[values[old]for old in order]
 for new,old in enumerate(order):
  word=values[old];op=word>>26
  if op in(1,4,5,6,7,20,21,22,23)or op==17 and word>>21&31==8:
   dest=old+1+(((word&65535)^32768)-32768);assert dest in inverse
   result[new]=(word&0xffff0000)|((inverse[dest]-new-1)&65535)
 if bindings is None:return result
 return result,{4*new:bindings[4*old]for new,old in enumerate(order)if 4*old in bindings}
