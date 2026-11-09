"""All 64 original JAL/delay windows with explicit register/load preconditions."""
import json,struct,sys
from dataclasses import replace
from pathlib import Path
from tools.experiments.game_resource_resolver_1510d0ec_match import ROOT,BUILD,NEW_SOURCE,HEADERS
root=ROOT;out=root/BUILD
from tools.tests import game_resource_resolver_1510d0ec_oracle as guest
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_resource_resolver_1510d0ec_match import CALLER_SITES
SITES=CALLER_SITES
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();programs=[guest.words(out/n)for n in('retail-reference.o','qualified-padded.o','qualified-owner.o','predecessor-owner.o')];count=0;records=[]
 for site in SITES:
  pc,at,delay=site['entry'],site['ROM'],site['delay'];window=list(struct.unpack_from('>2I',rom,at));assert window==[0x0D44343B,delay]
  for c in(guest.Case(),guest.Case(size=0),guest.Case(cache=0x81234567),guest.Case(failure=1),guest.Case(failure=2)):
   initial=guest.fixture(c);initial.update({guest.STACK+c.phase+i:(i*17+0xA5)&255 for i in range(1024,0x500)});probe=guest.Oracle([delay],initial,c,pc+4);probe.r[31]=pc+8
   op,rs,rt,rd,fn=delay>>26,delay>>21&31,delay>>16&31,delay>>11&31,delay&63
   desired=(guest.u32(c.identity),guest.output(c),guest.u32(c.priority),guest.u32(c.retain))
   if op==0 and rd in range(4,8):
    assert fn in(33,37),(hex(delay),fn);value=desired[rd-4]
    if rs:probe.r[rs]=value
    if rt:probe.r[rt]=0 if rs else value
   elif op==35 and rt in range(4,8):
    offset=((delay&65535)^32768)-32768
    if rs!=29:probe.r[rs]=0x90000
    p=guest.u32(probe.r[rs]+offset);guest.put(probe.memory,p,desired[rt-4])
   elif op==9:pass
   else:assert op in(0,40,43,57),hex(delay)
   initial=dict(probe.memory);registers=probe.r[:];fp=probe.f[:];probe.execute(delay)
   actual=tuple(probe.r[4:8]);assert actual[0]==guest.u32(c.identity)and actual[1]in(0,guest.OUTPUT),tuple(map(hex,actual))
   cc=replace(c,identity=guest.signed(actual[0]),output=0 if actual[1]==0 else 1,priority=guest.signed(actual[2]),retain=guest.signed(actual[3]))
   prepared=dict(probe.memory);want,calls,result,observations=guest.reference(prepared,cc);calls=[(guest.ENTRY,actual),*calls];pairs=[]
   for program in programs:
    code=dict(zip(range(guest.ENTRY,guest.ENTRY+len(program)*4,4),program));code[pc+8]=0;m=guest.Oracle(window,initial,cc,pc,connected=code);m.r=registers[:];m.f=fp[:];m.code=WindowCode(m.code,m);m.code.ends=(pc+8,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller return boundary')
    assert(guest.public(m.memory),m.calls,m.r[2],m.observations)==(guest.public(want),calls,result,observations),(hex(pc),cc)
    assert m.r[29]==guest.STACK+c.phase and m.r[16:24]==probe.r[16:24]
    home=guest.STACK+c.phase;assert all(m.memory[a]==value for a,value in want.items()if home+16<=a<home+2048)
    if actual[1]:assert guest.read(m.memory,actual[1])==guest.read(want,actual[1])
    pairs.append(m)
   assert guest.state(pairs[0])==guest.state(pairs[1]);count+=1
  records.append(dict(entry=hex(pc),ROM=hex(at),assembly=site['assembly'],delay_word=hex(delay),legacy_ignored_GLOBAL_ASM=site.get('legacy_ignored_GLOBAL_ASM',False)))
 report=dict(actual_JAL_sites=len(SITES),windows=records,words_per_window=2,cases=count,executions=count*4,four_root_bodies=True,all_allocation_outcomes=True,register_and_load_preconditions_explicit=True,original_and_normalized_literal_state_equal=True,ABI_unchanged='u32(s32,s32*,s32,s32)',full_parent_routines_claimed=False)
 (out/'caller-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='windows'},indent=2),flush=True)
if __name__=='__main__':main()
