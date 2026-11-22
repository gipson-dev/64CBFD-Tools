"""Qualify callback 90 through the complete original/current dispatcher."""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_randomized_map_particle_emitter_150ec6b0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_randomized_map_particle_emitter_150ec6b0_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
PARENT=0x15149264;TABLE=0x8008A4E8;DEATH_TABLE=0x8008A4C0
DEATH=0x150AE790;RELEASE=0x1516972C;TICKS=0x800BE9E4
half=lambda v:((v&65535)^32768)-32768
class Caller(g.Oracle):
    def record_call(self,t):
        if t not in(DEATH,RELEASE):return super().record_call(t)
        args=tuple(map(g.u32,self.arguments(1)));self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        if t not in(DEATH,RELEASE):return super().hook(t)
        if t==DEATH and self.revive:g.put(self.memory,g.RECORD+14,1,2)
        self.clobber(0xDEADBEEF)

def main():
    rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
    table=rom[0x22EFA8:0x22F130];at=elf_slot_offset(elf,TABLE,392)
    assert elf[at:at+392]==table and struct.unpack_from('>I',table,90*4)[0]==g.ENTRY
    death=rom[0x22EF80:0x22EFA8];at=elf_slot_offset(elf,DEATH_TABLE,40);assert elf[at:at+40]==death
    body=rom[0x176714:0x1767C8];at=elf_slot_offset(elf,PARENT,180);assert elf[at:at+180]==body
    caller=list(struct.unpack('>45I',body))
    raw=json.loads((out/'early-payload/words.json').read_text())
    retail=list(struct.unpack_from('>238I',rom,0x119B60))
    def machine(ws,c,flags,life,ticks,callback,death_index,revive,broken=False):
        memory=g.fixture(c);memory[g.RECORD+13]=flags;g.put(memory,g.RECORD+14,life,2)
        memory[g.RECORD+17]=callback;memory[g.RECORD+16]=death_index;g.put(memory,TICKS,ticks)
        memory.update({TABLE+i:b for i,b in enumerate(table)});memory.update({DEATH_TABLE+i:b for i,b in enumerate(death)})
        words=caller[:]
        if broken:words[18]=0x00002025
        connected=dict(zip(range(g.ENTRY,g.ENTRY+len(ws)*4,4),ws))
        m=Caller(words,c,entry=PARENT,connected=connected,memory=memory);m.revive=revive;return m
    count=0;visits=set()
    for flags,life,ticks,callback,death_index,revive,phase in itertools.product((0,1),(1000,0,-1),(0,1),(90,255),(0,255),(False,True),(0,8)):
        c=g.Case(phase=phase,mode=10);pair=[]
        for words in(raw,retail):
            m=machine(words,c,flags,life,ticks,callback,death_index,revive).run()
            expected=dict(m.initial);calls=[];observations=[]
            if flags&1:g.put(expected,g.RECORD+14,half(g.read(expected,g.RECORD+14,2))-ticks,2)
            if callback!=255:
                home=g.STACK+phase-24;observations=[g.snapshot(expected,home,c.fcsr)]
                expected,inner,obs,fcsr=g.reference(expected,c,home=home)
                calls=[(g.ENTRY,(g.RECORD,))]+inner;observations+=obs
            else:fcsr=c.fcsr
            if half(g.read(expected,g.RECORD+14,2))<0:
                if death_index!=255:
                    calls.append((DEATH,(g.RECORD,)))
                    if revive:g.put(expected,g.RECORD+14,1,2)
                if half(g.read(expected,g.RECORD+14,2))<0:calls.append((RELEASE,(g.RECORD,)))
            assert m.calls==calls and m.observations==observations
            assert g.public(m.memory)==g.public(expected)and m.fcsr==fcsr
            assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
            pair.append((m.calls,m.observations,g.public(m.memory),m.fcsr));visits.update(m.visits)
        assert pair[0]==pair[1];count+=1
    bad=machine(raw,g.Case(),0,1000,1,90,255,False,broken=True)
    try:bad.run();raise AssertionError('missing-record control ineffective')
    except AssertionError as error:assert 'unmapped read'in str(error),str(error)
    assert all(PARENT+4*i in visits for i in range(45))and caller[22]==0x8482000E
    r={'cases_per_stream':count,'streams':2,'original_caller_words':45,'current_complete_caller_equal':True,
       'callback_index':90,'callback_pointer':'0x8008A650','table_entries':98,'common_header_argument':True,
       'callback_return_ignored':True,'lifetime_death_release_revival':True,'missing_record_control_effective':True,
       'death_release_internals_contracted':True,'source_installed':packet.installed(),'matching_credit':0}
    (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
