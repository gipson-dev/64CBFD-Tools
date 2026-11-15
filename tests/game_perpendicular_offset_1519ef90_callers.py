"""All aligned direct calls and original result-use/copy windows, not full parents."""
import itertools,json,struct
from tools.tests import game_perpendicular_offset_1519ef90_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
CTX=0x36000

class StopCode(WindowCode):
    def __getitem__(self,pc):
        if pc in self.ends:self.owner.stopped=pc
        return super().__getitem__(pc)

class Oracle(g.Oracle):
    def record_call(self,target):
        if target==g.s.ENTRY:self.entries.append(tuple(self.arguments(3)));return
        return super().record_call(target)

def main():
    rom=(g.s.ROOT/'conker/conker.us.bin').read_bytes()
    jal=0x0c000000|((g.s.ENTRY>>2)&0x3ffffff)
    sites=[4*i for i,(w,) in enumerate(struct.iter_unpack('>I',rom)) if w==jal]
    pointers=[4*i for i,(w,) in enumerate(struct.iter_unpack('>I',rom)) if w==g.s.ENTRY]
    assert sites==[0x1cc788,0x1ccd48,0x1ccda0] and not pointers,(sites,pointers)
    streams=g.s.programs();streams['guarded']=bound_blob(*payload(g.s.OUT/'guarded.o',g.s.NAME),g.s.symbols());helpers=g.helper_data()[0]
    windows=((0x1519f2c4,0x1519f310,(0x1519f310,)),(0x1519f890,0x1519f8dc,(0x1519f8dc,0x1519fe38)),(0x1519f8e4,0x1519f900,(0x1519f900,0x1519f990)))
    count=0
    for k,(start,end,stops) in enumerate(windows):
        offset=start-0x15000000+0x2d4b0;words=struct.unpack_from('>'+str((end-start)//4)+'I',rom,offset)
        for near,present,mode,heading in itertools.product((False,True),(0,1),(6,7,0x106),range(0,256,17)):
            c=g.Case(dx=0 if near else g.bits(3.),dz=0 if near else g.bits(4.),present=present,mode=mode,heading=heading,height=g.bits(-9600. if heading&1 else -9400.))
            m=g.fixture(c);m.update({CTX+i:(i*13+0x53)&255 for i in range(64)})
            m[CTX+0x23]=mode&255;g.put(m,CTX+0x1e,0x1200,2);g.put(m,g.STACK+0xa6,0x2400,2)
            if k==0:
                g.put(m,g.STACK+0x48,g.STATE);g.put(m,g.RECORD+0x24,g.read(m,g.ACTOR+0x1c))
            want,expected,calls=g.reference(m,c);runs=[]
            for label,ws in streams.items():
                q=Oracle(ws,m.copy(),c,helpers);q.root_words=ws;q.entries=[]
                code=dict(q.code);code.update(zip(range(start,end,4),words));q.code=StopCode(code,q);q.code.ends=stops;q.entry=start
                q.r[3]=g.ACTOR;q.r[7]=mode;q.r[16]=CTX+0x10;q.r[17]=CTX;q.r[19]=g.RECORD;q.r[20]=g.ACTOR;q.f[16]=0
                try:q.run()
                except WindowBoundary:pass
                else:raise AssertionError('Caller boundary did not fire')
                record,out=(g.STACK+0x48,g.STACK+0x98) if k==0 else(g.RECORD,CTX+0x10)
                assert q.entries==[(record,mode&255,out)] and q.calls==calls,(k,label,c,'ABI')
                if want:
                    values=[g.read(expected,g.OUTPUT+4*i) for i in range(3)]
                    assert [g.read(q.memory,out+4*i) for i in range(3)]==values
                    if k<2:
                        destination=g.STACK+0x58 if k==0 else g.RECORD+0x10
                        assert [g.read(q.memory,destination+4*i) for i in range(3)]==values
                if k==0:
                    assert q.stopped==end and q.r[2]==want and g.read(q.memory,g.STACK+0xa6,2)==(0x2400|(4 if want else 0))
                elif k==1:
                    assert q.stopped==(0x1519f8dc if want else 0x1519fe38) and q.r[2]==1
                    assert g.read(q.memory,CTX+0x1e,2)==(0x1200|(4 if want else 0))
                else:assert q.stopped==(0x1519f990 if want else 0x1519f900) and q.r[2]==want
                runs.append(q)
            visible=lambda q:{a:v for a,v in q.memory.items() if not g.STACK-64<=a<g.STACK}
            assert all((visible(q),q.calls,q.fp_ops,q.stopped)==(visible(runs[0]),runs[0].calls,runs[0].fp_ops,runs[0].stopped) for q in runs[1:]),(k,c,'observable caller state')
            count+=1
    report=dict(cases_per_stream=count,streams=3,original_caller_window_words=[(b-a)//4 for a,b,_ in windows],all_three_direct_calls_covered=True,
                code_image_bytes=len(rom),aligned_JAL_ROM_offsets=sites,aligned_entry_pointer_words=0,full_parents_and_computed_calls_unqualified=True)
    (g.s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
