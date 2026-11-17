"""Conservative finite-set GPR dataflow over complete original height callees.

This proves only normal-return values. Memory/FP conditions are unknown;
ordinary loads are unknown; opaque calls clobber all o32 caller-save GPRs.
BREAK paths and nonreturning/faulting providers establish no normal result.
"""
from tools.experiments import game_region_emitter_151a5660_recovery as source
from collections import deque
from pathlib import Path
import hashlib,json,re,struct
R=source.ROOT;O=source.OUT;BASE=0x10000000;U=0xffffffff
TOP=None
def val(v):return frozenset((v&U,))
def merge_value(a,b):
 if a is None or b is None:return TOP
 c=a|b;return c if len(c)<=8 else TOP
def binary(a,b,fn):
 if a is None or b is None:return TOP
 c=frozenset(fn(x,y)&U for x in a for y in b);return c if len(c)<=8 else TOP
def signed(v):return(v^0x80000000)-0x80000000
def load_function(name,asm,rom,elf):
 hit=re.search(r'^glabel '+name+r'\s*\n(.*?)^endlabel '+name+r'\s*$',asm,re.M|re.S);assert hit,name
 rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',hit[1]);assert rows
 rom_at,entry=int(rows[0][0],16),int(rows[0][1],16);words=[int(x[2],16)for x in rows]
 assert [int(x[1],16)for x in rows]==list(range(entry,entry+4*len(words),4))
 blob=struct.pack('>%dI'%len(words),*words);assert rom[rom_at:rom_at+len(blob)]==blob
 shoff=struct.unpack_from('>I',elf,32)[0];ent,count=struct.unpack_from('>HH',elf,46)
 sections=[struct.unpack_from('>10I',elf,shoff+i*ent)for i in range(count)]
 hits=[s for s in sections if s[1]!=8 and s[3]<=entry and entry+len(blob)<=s[3]+s[5]];assert len(hits)==1
 s=hits[0];at=s[4]+entry-s[3];assert elf[at:at+len(blob)]==blob,('callee production not literal',name)
 return entry,words,dict(name=name,entry=hex(entry),ROM=hex(rom_at),words=len(words),retail_sha256=hashlib.sha256(blob).hexdigest(),production_literal=True)
def ranges(entry,words,summaries):
 states={};queue=deque();returns=set();breaks=set();seen=set();steps=0
 def push(pc,r,mem):
  assert pc%4==0 and 0<=pc<len(words)*4,('escaped function',hex(pc))
  r=tuple(r)
  if pc not in states:states[pc]=(r,dict(mem));queue.append(pc);return
  old,om=states[pc];nr=tuple(merge_value(a,b)for a,b in zip(old,r))
  nm={at:merge_value(om[at],mem[at])for at in om.keys()&mem.keys()};nm={at:v for at,v in nm.items()if v is not None}
  if(nr,nm)!=states[pc]:states[pc]=(nr,nm);queue.append(pc)
 def instruction(r,mem,w):
  op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==0:
   if fn in(0,2,3):r[rd]=binary(r[rt],val(sa),{0:lambda x,y:x<<y,2:lambda x,y:x>>y,3:lambda x,y:signed(x)>>y}[fn])
   elif fn in(4,6,7):r[rd]=binary(r[rt],r[rs],{4:lambda x,y:x<<(y&31),6:lambda x,y:x>>(y&31),7:lambda x,y:signed(x)>>(y&31)}[fn])
   elif fn in(32,33,34,35,36,37,38,39,42,43):
    funcs={32:lambda a,b:a+b,33:lambda a,b:a+b,34:lambda a,b:a-b,35:lambda a,b:a-b,36:lambda a,b:a&b,37:lambda a,b:a|b,38:lambda a,b:a^b,39:lambda a,b:~(a|b),42:lambda a,b:int(signed(a)<signed(b)),43:lambda a,b:int(a<b)}
    if fn in(42,43)and(r[rs]is None or r[rt]is None):r[rd]=frozenset((0,1))
    elif fn==37 and r[rs]==val(0):r[rd]=r[rt]
    elif fn==37 and r[rt]==val(0):r[rd]=r[rs]
    else:r[rd]=binary(r[rs],r[rt],funcs[fn])
   elif fn in(16,18):r[rd]=TOP
   else:assert fn in(24,25,26,27,15),('unhandled R instruction',hex(w))
  elif op in(8,9):r[rt]=binary(r[rs],val(imm),lambda a,b:a+b)
  elif op in(10,11):r[rt]=binary(r[rs],val(imm),lambda a,b:int(signed(a)<signed(b))if op==10 else int(a<b))if r[rs]is not None else frozenset((0,1))
  elif op in(12,13,14):r[rt]=binary(r[rs],val(w&65535),{12:lambda a,b:a&b,13:lambda a,b:a|b,14:lambda a,b:a^b}[op])
  elif op==15:r[rt]=val((w&65535)<<16)
  elif op in(32,33,34,35,36,37,38):
   address=binary(r[rs],val(imm),lambda a,b:a+b)
   r[rt]=mem.get(next(iter(address)),TOP)if op==35 and address is not None and len(address)==1 else TOP
  elif op in(40,41,42,43,46):
   address=binary(r[rs],val(imm),lambda a,b:a+b)
   if address is not None and len(address)==1:
    at=next(iter(address))
    if BASE-4096<=at<BASE+64:
     if op==43 and r[rt]is not None:mem[at]=r[rt]
     else:mem.pop(at,None)
  elif op==17:
   if rs in(0,2):r[rt]=TOP
   else:assert rs in(4,6,16,17,20,21),('unhandled COP1',hex(w))
  else:assert op in(49,53,57,61),('unhandled opcode',op,hex(w))
  r[0]=val(0)
 def condition(r,w):
  op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op==17:return {False,True}
  a,b=r[rs],r[rt]
  if op in(4,5,20,21):
   out={x==y for x in a for y in b}if a is not None and b is not None else{False,True}
   return {not x for x in out}if op in(5,21)else out
  if op==1:
   assert rt in(0,1,2,3),('unhandled REGIMM',hex(w))
   out={signed(x)<0 for x in a}if a is not None else{False,True};return {not x for x in out}if rt&1 else out
  assert op in(6,7,22,23)
  return {signed(x)<=0 if op in(6,22)else signed(x)>0 for x in a}if a is not None else{False,True}
 r=[TOP]*32;r[0]=val(0);r[29]=val(BASE);push(0,r,{})
 while queue:
  pc=queue.popleft();r0,mem0=states[pc];r=list(r0);mem=dict(mem0);steps+=1;assert steps<100000
  w=words[pc//4];seen.add(pc);op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
  if op in(1,4,5,6,7,20,21,22,23)or op==17 and rs==8:
   for take in condition(r,w):
    nr=r[:];nm=dict(mem)
    if op in(4,5,20,21)and nr[rs]is not None and nr[rt]is not None:
     equal=take if op in(4,20)else not take
     pairs=[(x,y)for x in nr[rs]for y in nr[rt]if (x==y)==equal]
     assert pairs,('inconsistent constant edge',hex(pc),take)
     nr[rs]=frozenset(x for x,y in pairs);nr[rt]=frozenset(y for x,y in pairs)
    likely=op in(20,21,22,23)or op==17 and bool(rt&2)or op==1 and rt in(2,3)
    if take or not likely:instruction(nr,nm,words[(pc+4)//4]);seen.add(pc+4)
    dest=pc+4+4*(((w&65535)^32768)-32768)if take else pc+8;push(dest,nr,nm)
  elif op==3:
   r[31]=val(entry+pc+8);instruction(r,mem,words[(pc+4)//4]);seen.add(pc+4)
   target=((entry+pc+4)&0xf0000000)|((w&0x3ffffff)<<2)
   for reg in(1,2,3,*range(4,16),24,25):r[reg]=TOP
   r[2]=summaries.get(target,TOP)
   if r[29]is not None:
    for sp in r[29]:
     for i in range(0,16,4):mem.pop(sp+i,None)
   push(pc+8,r,mem)
  elif op==2:
   instruction(r,mem,words[(pc+4)//4]);seen.add(pc+4);target=((entry+pc+4)&0xf0000000)|((w&0x3ffffff)<<2);push(target-entry,r,mem)
  elif op==0 and fn==8:
   assert rs==31,('computed jump requires further proof',hex(pc));instruction(r,mem,words[(pc+4)//4]);seen.add(pc+4)
   assert r[2]is not None,('unknown normal result',hex(entry+pc));returns.update(r[2])
  elif op==0 and fn==13:breaks.add(pc)
  else:instruction(r,mem,w);push(pc+4,r,mem)
 return frozenset(returns),dict(dataflow_steps=steps,visited_words=len(seen),excluded_BREAK_offsets=[hex(v)for v in sorted(breaks)])
def main():
 dest=O/'height-return-range.json';assert not dest.exists()
 paths=('conker/asm/71820.s','conker/src/game/generated_71820.c','conker/conker.us.bin','conker/build/conker.us.elf')
 frozen={p:hashlib.sha256((R/p).read_bytes()).hexdigest()for p in paths}
 asm=(R/paths[0]).read_text();rom=(R/paths[2]).read_bytes();elf=(R/paths[3]).read_bytes()
 summaries={};rows=[];programs={}
 for name,expected in [('func_1504697C',{0,1}),('func_15047004',{0,1,2}),('func_15046C80',{0,1})]:
  entry,words,row=load_function(name,asm,rom,elf);values,flow=ranges(entry,words,summaries)
  assert values==expected,(name,values,expected)
  summaries[entry]=values;row.update(normal_return_values=sorted(values),**flow);rows.append(row);programs[name]=(entry,words)
 entry,words=programs['func_1504697C'];bad=words[:];sites=[i for i,w in enumerate(words)if w==0x24020001];assert sites
 bad[sites[0]]=0x24020100;values,_=ranges(entry,bad,{})
 assert 256 in values,'ineffective return-range control'
 corrupted=dict(summaries);corrupted[entry]=values
 wrapper_entry,wrapper_words=programs['func_15046C80'];wrapper_values,_=ranges(wrapper_entry,wrapper_words,corrupted)
 assert 256 in wrapper_values,'ineffective connected wrapper control'
 assert all((v&255)==v for v in summaries[0x15046C80])
 report=dict(functions=rows,inputs=frozen,normal_return_only=True,callee_effects_claimed=False,opaque_call_clobbers=True,branch_likely_annul=True,all_memory_and_FP_conditions_overapproximated=True,byte_narrowing_lossless=True,control='one secondary return1 changed to256 expands wrapper contract',corrupted_secondary_values=sorted(values),corrupted_wrapper_values=sorted(wrapper_values),source_installed=source.installed(),c_match_credit=0)
 dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items()if k!='inputs'}),flush=True)
if __name__=='__main__':main()
