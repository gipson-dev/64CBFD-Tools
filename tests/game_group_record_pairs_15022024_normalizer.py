"""Closed role allocation and frame/exit normalization of the recovered leaf."""
import hashlib,json,struct
RAW='98c4b906f6f2ead08efa9d0ebe1b49498b8f30f1ecbd4e68b4cdb094eacc4c74'
BINDINGS='96a9e7cc1839a9e16c7f6672f6c7851c0dd3c77fee8a26b9643ec6947781f91b'
# Preserve all 79 core operations. Move only the active-table LW after the
# two independent address-low calculations. Remove the count early-return
# pair; inverse the positive guard to the shared zero exit. Allocate the two
# output-pointer roles to S1/S2 and restore their real save lifetimes.
ORDER=[0,'save-second','save-first',1,2,'first','second',*range(3,17),19,20,21,23,24,22,*range(25,85),'restore-first','restore-second',85,86]
EXTRA={'save-second':0xAFB2000C,'save-first':0xAFB10008,'first':0x00808825,'second':0x00A09025,'restore-first':0x8FB10008,'restore-second':0x8FB2000C}
# Operand fields by source instruction and live interval. Distinct temporary
# lifetimes deliberately have distinct mappings; this is not a global rename.
FIELDS={7:dict(rt=3),9:dict(rs=3,rt=7,rd=3),12:dict(rs=3,rt=3),13:dict(rd=2),14:dict(rd=4),15:dict(rs=3),16:dict(rt=5),19:dict(rs=5,rt=4,rd=5),20:dict(rt=9),21:dict(rt=8),22:dict(rs=5,rt=5),23:dict(rs=8,rt=8),24:dict(rs=9,rt=9),25:dict(rt=10),26:dict(rt=7),27:dict(rs=5),28:dict(rs=8,rt=4),30:dict(rs=2,rt=2),32:dict(rt=2,rd=11),33:dict(rt=11,rd=6),34:dict(rs=6,rt=12),35:dict(rs=7,rt=12),36:dict(rs=2,rt=2),37:dict(rt=10),38:dict(rs=6,rt=24),39:dict(rd=13),40:dict(rs=9,rt=13,rd=14),41:dict(rs=14,rt=15),42:dict(rs=15,rt=24),43:dict(rs=2,rt=2),44:dict(rd=2),46:dict(rt=12),47:dict(rs=17,rt=2),48:dict(rt=25),49:dict(rs=18,rt=2),50:dict(rs=25,rt=25),51:dict(rs=17,rt=2),52:dict(rs=4,rt=25,rd=3),53:dict(rs=18,rt=2),54:dict(rs=3,rt=11),55:dict(rt=2,rd=5),56:dict(rs=5,rt=2,rd=5),57:dict(rt=5,rd=5),58:dict(rs=11,rt=5,rd=6),59:dict(rs=6,rt=0),60:dict(rt=0,rd=12),63:dict(rs=6,rt=0),64:dict(rs=18,rt=0),65:dict(rs=18),66:dict(rs=18),67:dict(rs=3,rt=12),68:dict(rs=12,rt=5,rd=6),69:dict(rs=6,rt=0),70:dict(rt=0,rd=12),74:dict(rs=17,rt=0),75:dict(rs=17),76:dict(rs=17),79:dict(rs=2,rt=2),80:dict(rs=2,rt=3),82:dict(rs=5,rt=5)}
def normalize(data,refs):
 if hashlib.sha256(data).hexdigest()!=RAW or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=BINDINGS:raise ValueError('Pair lookup source words or bindings changed')
 words=list(struct.unpack('>87I',data));positions={old:i for i,old in enumerate(ORDER)if isinstance(old,int)};out=[];bindings={}
 assert len(ORDER)==91 and set(positions)==set(range(87))-{17,18}
 assert words[17]>>16==0x1000 and words[18]==0x00001025
 for old in ORDER:
  at=len(out)
  if isinstance(old,str):out.append(EXTRA[old]);continue
  w=words[old]
  for field,v in FIELDS.get(old,{}).items():
   s={'rs':21,'rt':16,'rd':11}[field];w=(w&~(31<<s))|(v<<s)
  op=w>>26
  if op in(4,5,6,7,20,21)or(op==17 and(w>>21&31)==8):
   target=old+1+(((words[old]&65535)^32768)-32768)
   if old==15:assert op==7;w=(w&0x03ffffff)|(6<<26);target=83
   w=(w&0xffff0000)|((positions[target]-at-1)&65535)
  if old==0:w=(w&0xffff0000)|0xfff0
  if old==86:w=(w&0xffff0000)|16
  if 4*old in refs:bindings[4*at]=refs[4*old]
  out.append(w)
 return struct.pack('>91I',*out),bindings
