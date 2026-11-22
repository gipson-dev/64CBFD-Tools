"""Actual callback origin, six-word call/delay window, and helper's narrow ABI."""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_interpolated_particle_emitter_150d1204_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_interpolated_particle_emitter_150d1204_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
TABLE=0x80089B38;PARENT=0x15134E48;WINDOW=0x1513514C;END=0x15135180
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 def words(a,n):return list(struct.unpack_from('>%dI'%n,rom,a-0x15000000+0x2D4B0))
 at=elf_slot_offset(elf,TABLE,36);table=elf[at:at+36]
 assert table==rom[0x22E5F8:0x22E61C]and struct.unpack_from('>I',table,28)[0]==g.ENTRY
 at=elf_slot_offset(elf,PARENT,1188);assert elf[at:at+1188]==struct.pack('>3I',0x00001025,0x03E00008,0)+bytes(1176)
 origin=words(0x151350A0,4);origin_end=0x151350B0
 m=g.Oracle(origin,g.Case(),entry=0x151350A0,connected={origin_end:0});m.r[16]=g.EMITTER
 m.code=WindowCode(m.code,m);m.code.ends=(origin_end,)
 try:m.run();raise AssertionError('missing origin boundary')
 except WindowBoundary:pass
 assert m.r[17]==TABLE
 window=words(WINDOW,13);continuation=words(END,2);assert continuation==[0xC7A20084,0xC7AC0080]
 count=0;visits=set()
 def machine(ws,c,broken=False):
  home=g.STACK+c.phase;memory=g.fixture(c)
  for i,b in enumerate(table):memory[TABLE+i]=b
  code=dict(zip(range(g.ENTRY,g.ENTRY+408,4),ws));code[END]=0
  body=list(window)
  if broken:body[9]=0
  m=g.Oracle(body,c,entry=WINDOW,connected=code,memory=memory)
  g.put(m.memory,home+20,0xBAD00000);m.initial=dict(m.memory)
  m.r[2]=7;m.r[16]=g.EMITTER;m.r[17]=TABLE;m.r[18]=home+0xD4;m.r[19]=home+0xC8;m.r[20]=0xFFFFFFFF
  m.f[20]=c.fraction;m.f[2]=g.bits(123.);m.f[12]=g.bits(-456.)
  m.saved_f=m.f[20:];m.before_f=m.f[:];m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
  return m
 for alias,mode,phase,fraction,rm in itertools.product((0,),(0,1,2,4,7,15),(0,8),(0.,.1,1.,-.5),range(4)):
  c=g.Case(mode=mode,phase=phase,fraction=g.bits(fraction),fcsr=rm,caller=True);states=[]
  for ws in g.streams():
   m=machine(ws,c)
   try:m.run();raise AssertionError('missing callback continuation')
   except WindowBoundary:pass
   expected,calls,observations,fcsr=g.reference(m.initial,c)
   assert m.calls[0]==(g.ENTRY,(*g.pointers(c),c.fraction,g.EMITTER))
   assert m.calls[1:]==calls and g.public(m.memory)==g.public(expected)
   assert [v[:3]for v in m.observations[1:]]==[v[:3]for v in observations]
   assert m.fcsr==fcsr and m.r[16:24]==m.before[16:24]and m.r[29]==g.STACK+phase
   assert g.read(m.memory,g.STACK+phase+0x84)==g.bits(123.)and g.read(m.memory,g.STACK+phase+0x80)==g.bits(-456.)
   states.append(g.state(m));visits.update(m.visits)
  assert states[0]==states[1];count+=1
 m=machine(g.streams()[0],g.Case(caller=True),broken=True)
 try:m.run();raise AssertionError('missing emitter home-store negative was ineffective')
 except AssertionError as e:assert 'unmapped read'in str(e),str(e)
 except WindowBoundary:raise AssertionError('missing emitter store reached continuation')
 # Validate the helper's complete original code binding; inspect load widths in
 # its entry/body rather than assigning all fourteen words an invented int ABI.
 helper=rom[0x208A80:0x208E2C];at=elf_slot_offset(elf,g.EMIT,len(helper));assert elf[at:at+len(helper)]==helper
 helper_words=words(g.EMIT,235)
 required=(0x93AC00C3,0x87A300DE,0x93AD00E3,0x87AC00E6,0x87AD00EA,0x93AE00EF,0x93AD00F3,0x8FAF00F4)
 assert all(w in helper_words for w in required)
 assert helper_words[-5:]==[0x00601025,0x8FBF001C,0x27BD00C0,0x03E00008,0]
 r=dict(cases_per_stream=count,streams=2,actual_origin_words=4,original_call_window_words=13,continuation_words=2,
        callback_index=7,table_entries=9,target_pointer_address='0x80089B54',all_six_arguments_and_delay_checked=True,
        current_parent_is_zero_stub=True,original_caller_window_only=True,callback_return_ignored=True,
        original_helper_words=235,helper_return_is_pointer=True,helper_narrow_argument_loads_checked=True,
        effective_missing_emitter_home_store_control=True,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
