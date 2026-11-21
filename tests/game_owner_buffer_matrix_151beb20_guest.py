"""Selected matrix buffer, live selector reloads and one scale snapshot."""
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import itertools
import json
import struct
import sys

from tools.experiments import game_owner_buffer_matrix_151beb20_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_camera_state_flags_151236d0_guest import static_reachable
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

ENTRY,SIZE,OWNER=0x151BEB20,372,0x30000
PAGE,SCALE,ROTATE=0x800BE9C0,0x800AA8E0,0x150A8050
SYMS=dict(D_800BE9C0=PAGE,D_800AA8E0=SCALE,func_150A8050=ROTATE)
ROTATION=(0,1,2,4,5,6,8,9,10)
SCALES=(0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0x40000000,1,0x00800000,0x7F7FFFFF)

@dataclass(frozen=True)
class Case:
    page:int=0
    scale:int=0x3F000000
    pattern:int=0
    mutation:int=0
    alias:int=0
    phase:int=0

def owner(c):
    return (OWNER,PAGE-0xAC,PAGE-0x7C,SCALE-0xAC,SCALE-0x7C)[c.alias]

def matrix(c):
    return tuple(bits(((i+c.pattern)%5-2)*0.125) if i%4!=3 else bits(1.0 if i==15 else 0.0) for i in range(16))

def fixture(c):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-512,256)}
    base=owner(c)
    memory.update({base+i:(i*13+0x35)&255 for i in range(-16,0x4100)})
    for index in range(256):
        for i,value in enumerate(matrix(c)):
            put(memory,base+0x7C+64*index+4*i,value)
    for offset,value in ((0x54,1.25),(0x58,-2.5),(0x5C,3.75),(0x120,.75)):
        put(memory,base+offset,bits(value))
    put(memory,SCALE,c.scale)
    put(memory,PAGE,c.page,1)
    return memory

def public(memory):
    return {a:b for a,b in memory.items() if not STACK-512<=a<STACK+256}

def effect(memory,c,base):
    if c.mutation&1:
        put(memory,PAGE,(c.page+1)&255,1)
    if c.mutation&2:
        put(memory,SCALE,bits(-.25))
    if c.mutation&4:
        for offset,value in ((0x54,-7.5),(0x58,8.25),(0x5C,-9.0),(0x120,12.0)):
            put(memory,base+offset,bits(value))

def helper(memory,c,arguments):
    for i,value in enumerate(matrix(c)):
        put(memory,arguments[0]+4*i,value)
    effect(memory,c,arguments[0]-0x7C-64*c.page)

def reference(initial,c,base=None):
    memory=dict(initial)
    base=owner(c) if base is None else base
    arguments=(base+0x7C+64*memory[PAGE],0,read(memory,base+0x120),0)
    helper(memory,c,arguments)
    scale=read(memory,SCALE)
    for source,index in ((0x54,12),(0x58,13),(0x5C,14)):
        destination=base+0x7C+64*memory[PAGE]+4*index
        put(memory,destination,read(memory,base+source))
    for index in ROTATION:
        destination=base+0x7C+64*memory[PAGE]+4*index
        put(memory,destination,bits(floating(read(memory,destination))*floating(scale)))
    return public(memory),[(ROTATE,arguments)],1

class Machine(FactoryOracle):
    def __init__(self,words,c,memory):
        self.c=c
        super().__init__(words,memory,c,entry=ENTRY,s=SYMS,arguments=(owner(c),))

    def record_call(self,target):
        assert target==ROTATE,hex(target)
        arguments=tuple(self.arguments(4))
        self.calls.append((target,arguments))
        self.events.append(('CALL',target,arguments))

    def hook(self,target):
        helper(self.memory,self.c,self.calls[-1][1])
        for i in range(4):
            self.put(self.r[29]+4*i,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0xA5000010,0xA5000011
        self.r[2]=0xDEADBEEF

def programs():
    paths=(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/generated_1E73B0.c.o')
    return [bound_blob(*payload(path,'func_151BEB20'),SYMS) for path in paths]

def state(machine):
    return (machine.memory,machine.r,machine.f,machine.hi,machine.lo,machine.condition,machine.trace,machine.calls,machine.current_pc,machine.delay_of)

def corpus():
    for page in range(256):
        yield Case(page=page,pattern=page%4)
    for page,scale,mutation,pattern,phase in itertools.product((0,1,255),SCALES,range(8),(0,3),(0,8)):
        yield Case(page=page,scale=scale,mutation=mutation,pattern=pattern,phase=phase)
    for alias,scale,mutation,phase in itertools.product(range(1,5),(0x3F000000,0xBF800000),range(8),(0,8)):
        yield Case(alias=alias,scale=scale,mutation=mutation,phase=phase)

def compare(streams,c):
    initial=fixture(c)
    expected=reference(initial,c)
    machines=[]
    for words in streams:
        machine=Machine(words,c,dict(initial)).run()
        assert (public(machine.memory),machine.calls,machine.r[2])==expected,('model',c)
        assert machine.r[29]==STACK+c.phase
        for register in (*range(16,24),30):
            assert machine.r[register]==machine.before[register],('saved register',register,c)
        machines.append(machine)
    assert state(machines[0])==state(machines[1])==state(machines[2]),c
    return machines[0]

def run():
    streams=programs()
    assert streams[0]==streams[1]==streams[2]
    coverage=set()
    count=0
    for case in corpus():
        machine=compare(streams,case)
        coverage.update((address-ENTRY)//4 for address in machine.visits if ENTRY<=address<ENTRY+SIZE)
        count+=1
    assert coverage==static_reachable(streams[0])==set(range(93))
    faults=0
    for case in (Case(),Case(page=255,mutation=7),Case(alias=1),Case(alias=4,phase=8)):
        complete=compare(streams,case)
        for cut in range(complete.all_accesses):
            states=[]
            for words in streams:
                machine=Machine(words,case,fixture(case))
                machine.cut=cut
                try:
                    machine.run()
                    raise AssertionError('Missing access cut')
                except AccessBoundary:
                    pass
                states.append(state(machine))
            assert states[0]==states[1]==states[2]
            faults+=1
    controls=[]
    for label,index,replacement in (('wrong-first-translation',23,0xE52400B0),('wrong-product',39,0x46005400),('wrong-return',26,0x24020002)):
        changed=list(streams[0])
        assert changed[index]!=replacement
        changed[index]=replacement
        case=Case()
        machine=Machine(changed,case,fixture(case)).run()
        assert (public(machine.memory),machine.calls,machine.r[2])!=reference(fixture(case),case),label
        controls.append(label)
    report=dict(cases_per_stream=count,streams=3,covered_words=len(coverage),access_fault_prefixes=faults,complete_memory_private_registers_calls_accesses_equal=True,effective_controls=controls,helper_contract='16 seeded matrix words with selector, scale and owner-field mutations plus ABI clobbers',source_installed=packet.installed(),matching_credit=0)
    (out/'guest-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return report

if __name__=='__main__':
    run()
