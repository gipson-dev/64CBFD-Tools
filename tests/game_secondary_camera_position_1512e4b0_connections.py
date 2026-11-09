"""Actual retail sine/cosine connections in the target angle domain."""
import itertools,json,struct,sys
from pathlib import Path
from tools.tests import game_secondary_camera_position_1512e4b0_oracle as guest
from tools.match_progress import load_elf_functions
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_secondary_camera_position_1512e4b0_match as match
root=match.ROOT;out=root/match.BUILD
def connection_checks():
    rom=(root/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>77I',rom,0x15B960));raw=guest.raw_words()
    actual,_,_=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    code={}
    for name,entry,offset,n in(('cosf',guest.COS,0x750B0,88),('sinf',guest.SIN,0x75210,104)):
     words=list(struct.unpack_from('>%dI'%n,rom,offset));assert actual[name]==words
     code.update(zip(range(entry,entry+n*4,4),words))
    elf=(out/'frozen/conker/build/conker.us.elf').read_bytes()
    for address,value in {**guest.trig.GLOBALS,**guest.trig.COS_GLOBALS}.items():
     at=elf_slot_offset(elf,address,4);assert struct.unpack_from('>I',elf,at)[0]==value,(hex(address),hex(value))
    n=0;visits=set();cases=[]
    for heading,speed,view,phase in itertools.product((0,1,0x7FFF,0x8000,0xFFFF,1800),(0.,.125,-.125,300.),(0,3),(0,8)):
     c=guest.Case(heading=heading,speed=guest.bits(speed),view=view,phase=phase);initial=guest.fixture(c);pair=[]
     for words in(truth,raw):
      m=guest.Oracle(words,initial,c,connected=code,real=True).run();guest.check(m,initial,c,connected=True);pair.append(m);visits.update(m.visits)
     assert guest.state(pair[0])==guest.state(pair[1]);n+=1
    report=dict(cases_per_body=n,original_sine_slot_words=104,original_cosine_slot_words=88,
                sine_words_visited=sum(guest.SIN<=p<guest.SIN+416 for p in visits),cosine_words_visited=sum(guest.COS<=p<guest.COS+352 for p in visits),
                target_words_visited=sum(guest.ENTRY<=p<guest.ENTRY+308 for p in visits),
                all_helper_words_and_constants_baseline_exact=True,independent_rounding_polynomial_model=True,
                actual_reachable_angle_domain=True,FCSR_or_hardware_claim=False)
    (out/'trig-connections.json').write_text(json.dumps(report,indent=2)+'\n');return report
