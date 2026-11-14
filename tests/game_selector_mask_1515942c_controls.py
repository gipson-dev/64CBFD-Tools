from tools.tests.game_selector_mask_1515942c_common import *
cases=[(Scenario((-1,-1,-1,-1,-1),(0,0,0,0,0),True),0x24091e00,0x24091c00),(Scenario((-1,-1,-1,-1,-1),(0,0,0,0,0),True),0x24070007,0x24070006),(Scenario((0,0,1,0,0),(0,0,1,0,0),True),0x90b9002d,0x90b9002e),(Scenario((-1,-1,-1,-1,-1),(0,0,0,0,0),True),0x54580003,0x50580003)]
for i,(c,old,new) in enumerate(cases):
 before=programs['retail'];assert before.count(old)==1,(i,before.count(old));mut=before.copy();mut[before.index(old)]=new;m=fixture(c);good=Oracle(before,m.copy(),c).run();bad=Oracle(mut,m.copy(),c).run();assert good.r[2]==result(c) and bad.r[2]!=good.r[2],(i,good.r[2],bad.r[2]);print('control',i,'rejected',flush=True)
