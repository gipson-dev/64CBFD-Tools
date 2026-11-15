"""Authentic flag gate and delay-slot slot-7 call; not a whole-parent claim."""
import itertools,json,struct
from tools.tests import game_model_vertex_wave_1517725c_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def main():
    source=g.source;rom=(source.ROOT/'conker/conker.us.bin').read_bytes();start,end=0x15183f28,0x15183f40
    window=struct.unpack_from('>6I',rom,0x1b13d8);assert window[-1]==0x24040007
    programs=[source.bound(*g.payload(source.OUT/n,source.NAME))for n in ('retail.o','selected.o','guarded.o')];count=0
    for flag,mode,phase,seed in itertools.product((0,1,2,255),(0,1,21,63),(0,8),range(4)):
        c=g.Case(flag=flag,mode=mode,phase=phase,seed=seed);initial=g.fixture(c)
        for w in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+len(w)*4,4),w));code[end]=0
            m=g.Oracle(window,initial,c,entry=start,connected=code);m.r[18]=1;m.before_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing caller return boundary')
            if flag==1:g.verify(m,initial,c);assert m.entries==[7]
            else:assert not m.calls and not m.entries and m.memory==initial
        count+=1
    controls=[]
    for label,pc,change,c in (('wrong-angle-source',0x40,0x28,g.Case()),('wrong-outer-radius',0x90,0x34,g.Case()),('wrong-sine-home',0x94,0x30,g.Case(private_sine=True))):
        w=programs[0][:];old=w[pc//4];w[pc//4]=old&0xffff0000|change;assert old!=w[pc//4]
        initial=g.fixture(c)
        try:m=g.Oracle(w,initial,c);m.run();g.verify(m,initial,c)
        except AssertionError as e:assert e.args==(c,),(label,e.args)
        else:raise AssertionError('Ineffective emitted control: '+label)
        controls.append(label)
    report=dict(caller_cases=count,window_words=6,slot=7,streams=3,emitted_controls=controls,whole_parent_claimed=False)
    (source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
