"""Exact bit-expression proof and new preimages for the existing packed caller."""
from pathlib import Path
import csv,hashlib,io,json,struct,sys
from tools.experiments import game_actor_byte_command_1506160c_match as packet
root,out=packet.ROOT,packet.OUT
NAME='func_150721A4';ENTRY=0x150721A4
def vector(n):return tuple(n>>i&1 for i in range(32))
def number(v):
 assert all(isinstance(b,int)for b in v),v
 return sum(b<<i for i,b in enumerate(v))
def proof(ws):
 r=[vector(0)for _ in range(32)];r[29]=vector(0x90000);r[31]=tuple(('RA',i)for i in range(32));initial=list(r);mem={};calls=[]
 packed=tuple(('P',i)for i in range(32));actor=tuple(('A',i)for i in range(32));pc=0
 def execute(w):
  op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=w&65535
  if w==0:return
  if op==15:r[rt]=vector(imm<<16)
  elif op==9:r[rt]=vector((number(r[rs])+((imm^32768)-32768))&0xFFFFFFFF)
  elif op==35:
   address=(number(r[rs])+((imm^32768)-32768))&0xFFFFFFFF
   r[rt]=packed if address==0x800D1580 else actor if address==0x800D154C else mem[address]
  elif op==43:mem[(number(r[rs])+((imm^32768)-32768))&0xFFFFFFFF]=r[rt]
  elif op==12:r[rt]=tuple(bit if imm>>i&1 else 0 for i,bit in enumerate(r[rs]))
  elif op==0 and fn==3:r[rd]=r[rt][sa:]+(r[rt][31],)*sa
  elif op==0 and fn==37:
   assert r[rt]==vector(0);r[rd]=r[rs]
  else:raise AssertionError(hex(w))
  r[0]=vector(0)
 while pc<len(ws):
  w=ws[pc]
  if w>>26==3:
   assert (0x10000000|((w&0x3FFFFFF)<<2))==0x1506160C
   execute(ws[pc+1]);calls.append(tuple(r[i]for i in range(4,8))+(mem[number(r[29])+16],))
   for reg in(1,2,3,*range(4,16),24,25):r[reg]=tuple(('CALLEE',reg,i)for i in range(32))
   r[31]=vector(ENTRY+4*(pc+2));pc+=2
  elif w>>26==0 and w&63==8:
   assert r[31]==initial[31];execute(ws[pc+1]);assert r[29]==initial[29];pc=len(ws)
  else:execute(w);pc+=1
 def bits(start):return tuple(('P',i)if i<start+8 else 0 for i in range(start,32))+(0,)*start
 expected=(actor,bits(16),bits(0),bits(8),vector(0));assert calls==[expected]
 return calls
