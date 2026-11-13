"""Compare retail, raw C and guarded streams with an independent byte model."""
from pathlib import Path
import json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_view_render_pass_oracle import STACK

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-settings-validator-151dd9e4-durable'
rom=(root/'conker/conker.us.bin').read_bytes();elf=(root/'conker/build/conker.us.elf').read_bytes()
symbols={r[1]:r[2][1] for r in symbol_rows(elf)}
entry=0x151dd9e4;settings=0x800e0be0;defaults=0x8008fe54;minimum=0x8008fe6c;maximum=0x8008fe84
programs=[list(struct.unpack_from('>108I',rom,0x20ae94))]
for path in ('return-00.o','generated-guarded.o','c-guarded.o'):
    programs.append(bound_blob(*payload(out/path,'func_151DD9E4'),symbols))
assert programs[0]==programs[2]==programs[3]
signed=lambda x:(x^128)-128
def memory(index,value,mode):
    m={STACK+i:(i*17+0xa5)&255 for i in range(-64,64)}
    for addr in range(defaults-8,maximum+32):m[addr]=(addr*31+mode*19)&255
    for addr in range(settings-8,settings+36):m[addr]=(addr*13+mode*23)&255
    for i in range(23):
        m[defaults+i]=(i*11+mode*17)&255
        if mode==0:
            m[minimum+i]=rom[0x23492c+i];m[maximum+i]=rom[0x234944+i]
        else:
            m[minimum+i]=(i*17+mode*29)&255;m[maximum+i]=(i*37+mode*7)&255
        m[settings+i]=(value+i*13+mode*5)&255
    m[settings+index]=value
    return m
def reference(m):
    m=m.copy()
    for i in range(23):
        v=signed(m[settings+i])
        if v<signed(m[minimum+i]) or v>signed(m[maximum+i]):m[settings+i]=m[defaults+i]
    return m
def main():
    cases=0
    for mode in range(2):
        for index in range(23):
            for value in range(256):
                m=memory(index,value,mode);expected=reference(m)
                for p in programs:
                    machine=FactoryOracle(p,m.copy(),Case(),entry=entry,s={},arguments=())
                    machine.run()
                    assert machine.r[2]==23 and machine.memory==expected,(mode,index,value,machine.r[2])
                cases+=1
    report={'cases':cases,'streams':len(programs),'all_byte_values_per_field':True,
            'retail_and_synthetic_bounds':True,'independent_memory_model':True,'return_value':23,'uncredited':True}
    (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
if __name__=='__main__':main()
