from pathlib import Path
import sys,struct,itertools
from tools.experiments import game_fixed_effect_150afc68_match as packet_module
root=packet_module.ROOT
from tools.tests.test_game_factory_preset_wrapper import PresetOracle,state,AccessFault,STACK
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
out=packet_module.OUT;ENTRY=0x150afc68;CALLEE=0x1516d99c;S={'func_1516D99C':CALLEE}
def packet(args):
 result=[0]*49
 for index,value in ((0,1),(3,13),(12,4),(16,255),(17,255),(18,255),(20,255),(22,1),(27,170),(28,170),(29,170),(30,170),(31,args[2]),(32,args[3]),(34,args[0]),(35,240),(36,80),(37,80),(38,1),(39,4),(41,1),(45,args[1]),(47,args[4]&255),(48,args[5])):result[index]=value&0xffffffff
 return tuple(result)
def program(path):
 d,r=payload(path,'func_150AFC68');return bound_blob(d,r,S)
def programs():
 rom=(root/'conker/conker.us.bin').read_bytes();return [struct.unpack_from('>82I',rom,0xdd118)]+[program(out/(x+'.o')) for x in ('after','generated','generic')]
def cases():
 yield (0,0,0,0,0,0)
 yield (0xffffffff,)*6
 yield (0x80000000,0x87654321,0xfedcba98,0xabcdef87,0x12345680,0x76543210)
 for i in range(64):yield tuple((i*1664525+j*0x372159ab+1013904223)&0xffffffff for j in range(6))
def run():
 progs=programs();count=0
 for args,phase,mode in itertools.product(cases(),(0,8),range(3)):
  models=[PresetOracle(words,args,phase,mode,entry=ENTRY,callee=CALLEE).run() for words in progs];a=models[0]
  assert all(state(m)==state(a) for m in models[1:]),(args,phase,mode)
  assert a.calls==[(CALLEE,*packet(args))] and a.r[29]==STACK+phase,(args,a.calls,packet(args))
  count+=1
 print('complete 49-word packet:',count,'cases per stream with home-slot mutations',flush=True)
def fault_prefixes():
 progs=programs();args=(0x87654321,0xfedcba98,0xabcdef87,0x80000001,0x12345680,0x76543210);count=0
 for phase in (0,8):
  full=PresetOracle(progs[0],args,phase,2,entry=ENTRY,callee=CALLEE).run()
  for fault in range(full.accesses):
   models=[PresetOracle(words,args,phase,2,fault,entry=ENTRY,callee=CALLEE) for words in progs]
   for m in models:
    try:m.run();raise AssertionError(('missing fault',phase,fault))
    except AccessFault:pass
   assert all(state(m)==state(models[0]) for m in models[1:]),(phase,fault);count+=1
 print('retail and C streams:',count,'access-boundary prefixes',flush=True)
