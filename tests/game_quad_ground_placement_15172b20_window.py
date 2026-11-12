"""Qualify only the original quad creator's argument-preparation window."""
import json,struct
from tools.tests import game_quad_ground_placement_15172b20_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob

START=0x15171DC4;END=0x15171E08;RECORD=g.VERTICES-0x10;ASSET=0x51000;TABLE=0x8008CA4C
class Caller(g.Oracle):
    def record_call(self,t):
        if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(8))
        else:super().record_call(t)

def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes()
 data,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_15172B20']['value'],fs['func_15172B20']['size']
 refs={i-a:v for i,v in rs.items() if a<=i<a+n}
 lookup={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())}
 candidate=bound_blob(data[a:a+n],refs,{nm:lookup[nm] for es in refs.values() for _,nm in es})
 retail=struct.unpack_from('>74I',rom,0x19FFD0)
 window=struct.unpack_from('>17I',rom,START-0x15000000+0x2d4b0)
 assert window[-2:]==(0x0d45cac8,0xafb8001c)
 count=0
 for c in g.cases():
     calls,result=g.reference(c)
     for words in (retail,candidate):
         m=Caller(words,c);m.entered=False;m.r[29]=g.STACK-0x180
         m.r[3]=RECORD;m.r[4]=g.VERTICES
         m.f[12],m.f[14],m.f[2]=c.xyz;m.f[4]=c.angle
         g.put(m.memory,m.r[29]+0x4c,c.radius);g.put(m.memory,m.r[29]+0x50,0x12345678)
         m.memory[RECORD+0x58]=1
         for base,length in ((TABLE,8),(ASSET,8)):
             m.memory.update({base+i:0 for i in range(length)})
         g.put(m.memory,TABLE+4,ASSET);g.put(m.memory,ASSET+6,c.image&0xffff,2)
         code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words))
         code.update(zip(range(START,END,4),window));code[END]=0
         m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
         try:m.run()
         except WindowBoundary:pass
         else:raise AssertionError('caller boundary not reached')
         assert m.entered and m.target_args==(g.VERTICES,*c.xyz,c.angle,c.radius,0x12345678,c.image&0xffff),(c,m.target_args)
         assert (m.calls,m.r[2])==(calls,result),(c,m.calls,calls,hex(m.r[2]),hex(result))
         assert m.r[29]==g.STACK-0x180 and m.r[31]==END and g.read(m.memory,g.MARK)==0x11223344
     count+=1
 report=dict(cases=count,caller='func_15171D4C argument-preparation call window',helpers='modeled',caller_window_only=True,full_parent_qualified=False,source_installed=False)
 (g.out/'caller_15172B20_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
