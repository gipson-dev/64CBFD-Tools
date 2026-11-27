"""Conservative all-path byte-return proof and original classifier/table pinning."""
from tools.experiments import game_owner_action_dispatch_1514d15c_match as target_packet
from pathlib import Path
from collections import deque
import hashlib,json,re,struct
r=target_packet.ROOT;o=target_packet.OUT;ENTRY=0x1514CA80;COUNT=439;RET=-1;MASK=0xFFFFFFFF

def at(data,va,n):
 shoff=struct.unpack_from('>I',data,32)[0];size,count=struct.unpack_from('>HH',data,46)
 hits=[v for i in range(count)if (v:=struct.unpack_from('>10I',data,shoff+i*size))[1]==1 and v[3]<=va and va+n<=v[3]+v[5]];assert len(hits)==1;v=hits[0];return data[v[4]+va-v[3]:v[4]+va-v[3]+n]

def object_stub(path):
 data=path.read_bytes();shoff=struct.unpack_from('>I',data,32)[0];size,count=struct.unpack_from('>HH',data,46);sections=[struct.unpack_from('>10I',data,shoff+i*size)for i in range(count)];found=[]
 for table in sections:
  if table[1]!=2:continue
  strings=sections[table[6]];names=data[strings[4]:strings[4]+strings[5]]
  for pos in range(table[4],table[4]+table[5],table[9]):
   name,value,n,info,other,index=struct.unpack_from('>IIIBBH',data,pos)
   if names[name:].split(b'\0',1)[0]==b'func_1514CA80':
    section=sections[index];assert info&15==2 and n==12;found.append(data[section[4]+value-section[3]:section[4]+value-section[3]+n])
    for rel in sections:
     if rel[1]==9 and rel[7]==index:
      for at in range(rel[4],rel[4]+rel[5],rel[9]):offset,_=struct.unpack_from('>II',data,at);assert not value<=offset<value+n
 assert len(found)==1;return found[0]

def proof(words,targets):
 code=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words));assert all(t in code for t in targets)
 initial=(0,)+(MASK,)*31;states={(ENTRY,None):initial};todo=deque(states);visited=set();returns=[];iterations=0
 def enqueue(pc,pending,regs):
  if pc==RET:returns.append(regs[2]);return
  assert pc in code,hex(pc);key=(pc,pending);old=states.get(key);merged=tuple(a|b for a,b in zip(old,regs))if old else tuple(regs)
  if merged!=old:states[key]=merged;todo.append(key)
 while todo:
  key=todo.popleft();pc,pending=key;reg=list(states[key]);w=code[pc];op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=w&65535;simm=(imm^32768)-32768;visited.add(pc);iterations+=1;assert iterations<100000
  control=op in(1,2,3,4,5,6,7,20,21,22,23)or(op==0 and fn in(8,9))
  if pending is not None:assert not control,'Nested branch in classifier delay'
  if control:
   assert op!=3 and not(op==0 and fn==9),'Classifier unexpectedly invokes helper'
   if op==2:dest=(pc+4)&0xF0000000|(w&0x3FFFFFF)*4;enqueue(pc+4,dest,reg)
   elif op==0:
    for dest in([RET]if rs==31 else targets):enqueue(pc+4,dest,reg)
   else:
    always=op in(4,20)and rs==rt;never=op in(5,21)and rs==rt
    if not never:enqueue(pc+4,pc+4+4*simm,reg)
    if not always:
     if op in(20,21,22,23)or(op==1 and rt in(2,3,18,19)):enqueue(pc+8,None,reg)
     else:enqueue(pc+4,pc+8,reg)
   continue
  if op==0:
   if fn==0:reg[rd]=(reg[rt]<<sh)&MASK
   elif fn==2:reg[rd]=reg[rt]>>sh
   elif fn==3:reg[rd]=MASK if reg[rt]&0x80000000 else reg[rt]>>sh
   elif fn in(33,35):reg[rd]=reg[rs]if reg[rt]==0 else reg[rt]if reg[rs]==0 and fn==33 else MASK
   elif fn==36:reg[rd]=reg[rs]&reg[rt]
   elif fn in(37,38):reg[rd]=reg[rs]|reg[rt]
   elif fn in(42,43):reg[rd]=1
   else:raise ValueError(('unsupported SPECIAL',hex(pc),hex(w)))
  elif op==9:reg[rt]=(simm&MASK)if rs==0 else MASK
  elif op in(10,11):reg[rt]=1
  elif op==12:reg[rt]=reg[rs]&imm
  elif op in(13,14):reg[rt]=reg[rs]|imm
  elif op==15:reg[rt]=imm<<16
  elif op in(32,33,35):reg[rt]=MASK
  elif op==36:reg[rt]=255
  elif op==37:reg[rt]=65535
  elif op in(40,41,43):pass
  else:raise ValueError(('unsupported opcode',hex(pc),hex(w)))
  reg[0]=0;enqueue(pc+4 if pending is None else pending,None,reg)
 assert returns,'No return proved'
 if any(mask&~255 for mask in returns):raise ReturnRangeError(returns)
 return dict(reachable_instruction_words=len(visited),abstract_states=len(states),iterations=iterations,return_masks=sorted(set(returns)),all_normal_returns_zero_extend_u8=True,unknown_incoming_register_masks=True,all_frozen_jump_table_targets_overapproximated_at_every_indirect_JR=True,branch_delays_and_likely_annulment=True)
class ReturnRangeError(Exception):pass

def main():
 asm=(o/'baseline/conker/asm/179F30.s').read_text();text=asm.split('glabel func_1514CA80\n',1)[1].split('endlabel func_1514CA80',1)[0];rows=re.findall(r'/\*\s*([0-9A-F]+)\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',text);blob=bytes.fromhex(''.join(v[2]for v in rows));rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();assert len(blob)==COUNT*4 and blob==rom[0x179F30:0x17A60C];assert at(elf,ENTRY,12)==bytes.fromhex('0000102503e0000800000000')
 tables=[];targets=set()
 for name,va,end in(('jtbl_800A59AC',0x800A59AC,0x800A5C98),('jtbl_800A5C98',0x800A5C98,0x800A5D70),('jtbl_800A5D70',0x800A5D70,0x800A5DBC),('jtbl_800A5DBC',0x800A5DBC,0x800A5DE4)):
  data=at(elf,va,end-va);offset=va-0x800A5940+0x24A400;assert rom[offset:offset+len(data)]==data,(name,hex(offset));values=struct.unpack('>'+str(len(data)//4)+'I',data);targets.update(values);tables.append(dict(name=name,VA=hex(va),entries=len(values),sha256=hashlib.sha256(data).hexdigest(),frozen_ELF_ROM_equal=True))
 assert object_stub(o/'before-owner.o')==object_stub(o/'selected-owner.o')==bytes.fromhex('0000102503e0000800000000')
 words=list(struct.unpack('>439I',blob));p=proof(words,sorted(targets));stores=[w for w in words if w>>26 in(40,41,43)];assert stores and all(w>>26==43 and w>>21&31 in(5,6,7)and w&65535==0 for w in stores)
 controls=[]
 for name,index,word in(('unbounded-initial-flags',1,0x00801825),('return-bit8',436,0x34620100)):
  bad=list(words);assert bad[index]!=word;bad[index]=word
  try:proof(bad,sorted(targets))
  except ReturnRangeError:controls.append(dict(name=name,range_comparison_rejected=True))
  else:raise AssertionError('Ineffective range control '+name)
 q=dict(function='func_1514CA80',original_words=439,ASM_ROM_equal=True,original_sha256=hashlib.sha256(blob).hexdigest(),production_still_12byte_stub=True,selected_private_u8_return_does_not_change_stub_words_or_bindings=True,intended_O32_arguments=['owner','first_out','second_out','third_out'],stores=len(stores),only_three_word_output_store_forms=True,proof=p,effective_controls=controls,tables=tables,source_installed=target_packet.installed(),helper_matching_credit=0,matching_credit=0,no_dynamic_helper_or_gameplay_acceptance_from_static_range_proof=True)
 (o/'classifier_abi.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
