"""Run the complete original registered-list caller with either callback stream."""
from pathlib import Path
import csv,hashlib,itertools,json,struct,sys
from tools.experiments import game_strip_update_151ad174_recovery as source
from tools.tests import game_strip_update_151ad174_private_oracle as o
p=source.OUT
from tools.check_game_data_layout import load_section
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
ROOT=source.ROOT;CALLER=0x151671E8;TABLE=o.SYMS['D_8008B4A8'];HEADS=o.SYMS['D_800DCE50'];DEPTH=o.SYMS['D_800DD190'];NEXT=o.SYMS['D_800DD198']
layout=list(csv.DictReader((source.FROZEN/'conker/retail_layout.us.txt').open()));row=next(v for v in layout if v['function']=='func_151671E8')
length=int(row['end_address'],0)-CALLER if 'end_address'in row else int(row['end'],0)-CALLER
assert length==296
rom=(source.FROZEN/'conker/conker.us.bin').read_bytes();at=CALLER-0x15000000+0x2D4B0;words=list(struct.unpack('>74I',rom[at:at+296]))
data_at,data=load_section(source.FROZEN/'conker/build/conker.us.elf','.game_data');table=data[TABLE-data_at:TABLE-data_at+101*52];assert len(table)==5252
def fixture(c,category,row,depth):
 m=o.fixture(c);m.update({TABLE+i:v for i,v in enumerate(table)});m.update({HEADS+i:0 for i in range(0x340)})
 for i in range(64):m[NEXT+i]=(i*29+0x5A)&255
 o.put(m,DEPTH,0xA55A5AA5);m[DEPTH]=depth;o.put(m,HEADS+row*0x1A0+category*4,o.RECORD);o.put(m,o.RECORD+8,0);m[o.RECORD]=category;m[o.RECORD+1]=row
 return m
class Caller(o.Oracle):
 def __init__(self,callback,initial,c,original=words):
  FactoryOracle.__init__(self,original,initial,c,entry=CALLER,s={},arguments=(0,),connected={o.ENTRY+4*i:w for i,w in enumerate(callback)})
  self.service=o.Service(self.memory,c);self.invocations=[];self.saved_g=tuple(self.r[16:24])+(self.r[28],self.r[29],self.r[30]);self.saved_fp=tuple(self.f[20:])
 def record_call(self,t):
  if t==o.ENTRY:
   args=tuple(self.arguments(1));assert args==(o.RECORD,),('callback ABI',args);self.invocations.append(args)
  else:super().record_call(t)
def one(code,c,category,row,depth,original=words):
 initial=fixture(c,category,row,depth);expected,calls=o.reference(initial,c);o.put(expected,NEXT+4*(depth+1),0)
 m=Caller(code,initial,c,original).run();assert m.invocations==[(o.RECORD,)]
 assert o.public(m.memory)==o.public(expected),('caller public',o.asdict(c),category,row,depth,next(((hex(at),v,expected.get(at))for at,v in o.public(m.memory).items()if v!=expected.get(at)),None))
 assert m.service.calls==calls and m.memory[DEPTH]==depth
 return m
def main():
 out=p
 from tools.tests.game_strip_update_151ad174_guest import programs as callback_programs
 programs=callback_programs();seen={v:set()for v in programs};n=0
 for seed,category,row,depth in itertools.product(range(8),(47,78),(0,1),(0,3)):
  c=o.Case(seed=seed,owner=seed&1,impulse=seed>>1&1,pattern=seed%5,phase=(seed&1)*8,mutation=seed*2,handle=65535,query=seed&1)
  executions={}
  for k,code in programs.items():
   execution=one(code,c,category,row,depth);seen[k].update(execution.visits);executions[k]=execution
  for k,execution in executions.items():
   if k!='raw':assert execution.memory==executions['retail'].memory,('caller complete RAM',k,seed,category,row,depth)
  n+=1
 controls=[];sites=[i for i,w in enumerate(words)if w>>26==0 and w&63==9];assert len(sites)==1
 bad=words[:];bad[sites[0]+1]=0x24840004
 try:one(programs['retail'],o.Case(),47,0,0,bad)
 except AssertionError as error:assert error.args[0][0]=='callback ABI',error;controls.append('wrong callback pointer')
 else:raise AssertionError('Wrong callback pointer was accepted')
 report=dict(cases_per_stream=n,streams=list(programs),caller_words=74,caller_words_visited={k:len({a for a in v if CALLER<=a<CALLER+296})for k,v in seen.items()},registered_categories=[47,78],both_rows_and_depths=[0,3],one_pointer_void_ABI=True,complete_public_RAM_and_calls_compared=True,complete_normalized_RAM_and_private_stack_compared=True,effective_controls=controls,original_caller_sha256=hashlib.sha256(rom[at:at+296]).hexdigest(),source_installed=source.installed(),c_match_credit=0)
 (out/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
