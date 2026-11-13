"""Execute both original call sites through the validator's return."""
from pathlib import Path
import importlib.util,json,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-settings-validator-151dd9e4-durable'
from tools.tests import game_settings_validator_151dd9e4_guest as g
sites=((0x1500752c,0x15007534,16),(0x151e23ec,0x151e23f4,6))
class Caller(FactoryOracle):
    def __init__(self,pc,program,m,value,field):
        window=list(struct.unpack_from('>2I',g.rom,pc-0x15000000+0x2d4b0))
        code={g.entry+4*i:w for i,w in enumerate(program)};code[pc+8]=0
        super().__init__(window,m,Case(),entry=pc,s={},arguments=(),connected=code)
        if field==16:self.r[6]=g.settings;self.r[5]=value
        else:self.r[3]=g.settings;self.r[15]=value
        self.code=WindowCode(self.code,self);self.code.ends=(pc+8,)
    def record_call(self,t):
        assert t==g.entry;self.calls.append(t)
cases=0
for pc,end,field in sites:
    assert end==pc+8
    for value in range(256):
        initial=g.memory(field,(value*17)&255,value%2)
        expected=initial.copy();expected[g.settings+field]=value
        expected=g.reference(expected)
        for program in (g.programs[0],g.programs[2]):
            m=Caller(pc,program,initial.copy(),value,field)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Expected caller continuation')
            assert m.memory==expected and m.r[2]==23 and m.calls==[g.entry],(hex(pc),value,m.calls)
        cases+=1
report={'call_sites':[hex(x[0]) for x in sites],'cases':cases,'streams':2,
        'covers_delay_slot_and_return':True,'bounded_windows_only':True,'uncredited':True}
(out/'caller-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
