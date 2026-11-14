"""Compare the packet routine with an independent wrap and float model."""
from pathlib import Path
import itertools,json,os,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-coordinate-packet-150f1b48-durable'
rom=(root/'conker/conker.us.bin').read_bytes();symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
entry=0x150f1b48;state=0x800cc298;actors=0x800cc354;ticks=0x800be9e4;lo=0x800a18f4;hi=0x800a18f8;separate=0x300000
programs=[list(struct.unpack_from('>90I',rom,0x11eff8)),bound_blob(*payload(out/os.environ.get('PACKET_OBJECT','formatted.o'),'func_150F1B48'),symbols)]
signed16=lambda n:((n&65535)^0x8000)-0x8000
signed32=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
f32=lambda n:struct.unpack('>f',struct.pack('>f',n))[0]
def fixture(slot,value,dt,active,output):
    m={STACK+i:0xa5 for i in range(-256,256)}
    for base,n in ((state-32,160),(actors-16,4*812+32),(output-16,56)):
        for i in range(n):m.setdefault(base+i,(i*31+0x47)&255)
    put(m,lo,0xc5cccccd);put(m,hi,0x45aaaaab);put(m,ticks,dt);put(m,state+18,value,2)
    put(m,actors+slot*812,0x21 if active else 0x20,2)
    return m
def reference(initial,slot,output):
    m=initial.copy();current=signed16(read(m,state+18,2));step=(read(m,ticks)*546)&0xffffffff
    if read(m,actors+slot*812,2)==0x21:
        new=signed32(current-step);current=new if f32(new)>f32(-6553.60009765625) else -0x1999
    else:
        new=signed32(current+step);current=new if f32(new)<f32(5461.33349609375) else 0x1555
    put(m,state+18,current,2);put(m,output,0xb2,2);value=read(m,state+18,2)
    put(m,output+4,0xb8,2);put(m,output+2,value,2)
    for i in range(2,6):
        value=read(m,state+18,2);put(m,output+4*i,0xb2+i*6,2);put(m,output+4*i-2,value,2)
    put(m,output+22,read(m,state+18,2),2)
    return m
def main():
    cases=0
    for slot,value,dt,active,offset in itertools.product(range(4),(-32768,-6554,-1,0,5461,32767),(0,1,2,0x7fffffff,0x80000000,0xffffffff),(0,1),(None,-8,0,8,12,16,18,20)):
        output=separate if offset is None else state+offset;initial=fixture(slot,value,dt,active,output);expected=reference(initial,slot,output)
        for n,p in enumerate(programs):
            machine=FactoryOracle(p,initial.copy(),Case(),entry=entry,s={},arguments=(output,slot)).run()
            if machine.memory!=expected or machine.r[2]!=(output+24)&0xffffffff:
                different=[(hex(a),initial.get(a),expected.get(a),machine.memory.get(a)) for a in sorted(set(expected)|set(machine.memory)) if expected.get(a)!=machine.memory.get(a)]
                print(json.dumps({'case':[slot,value,dt,active,offset],'stream':n,'return':hex(machine.r[2]),'different':different[:10]}),flush=True);raise SystemExit(1)
        cases+=1
    report={'cases':cases,'streams':2,'wrapped_tick_arithmetic_and_float_thresholds':True,'overlap_tested':True,'uncredited':True}
    (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
if __name__=='__main__':main()
