"""Compare matched instruction results and memory accesses across two streams."""
from pathlib import Path
import importlib.util,itertools,json,sys
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import Case
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable'
from tools.tests import game_texture_tile_151ed29c_guest as g
programs=[g.programs[0],bound_blob(*payload(out/'coords-02.o','func_151ED29C'),g.symbols)]
origins=json.loads((out/'flow-alignment.json').read_text())['origins']
class TrackedCode(dict):
    def __init__(self,code,machine):super().__init__(code);self.machine=machine
    def __getitem__(self,pc):
        self.machine.pc=pc;word=super().__getitem__(pc);op=word>>26
        if op in (4,5):
            rs,rt=word>>21&31,word>>16&31
            equal=self.machine.r[rs]==self.machine.r[rt]
            self.machine.values.setdefault((pc-g.entry)//4,[]).append(('branch',equal if op==4 else not equal))
        return word
class Trace(g.Machine):
    def __init__(self,words,memory,args):
        super().__init__(words,memory,Case(),entry=g.entry,s={},arguments=args)
        self.code=TrackedCode(self.code,self);self.values={}
    def execute(self,word):
        at=(self.pc-g.entry)//4;op=word>>26;fn=word&63;rt=word>>16&31;rd=word>>11&31
        prior=len(self.trace);super().execute(word)
        access=self.trace[prior:]
        if op==0 and fn==25:value=('mult',self.hi,self.lo)
        elif op==0 and word:value=('register',self.r[rd])
        elif op in (8,9,10,11,12,13,14,15,32,33,35,36,37):value=('register',self.r[rt])
        else:value=None
        if access:value=(value,tuple(access))
        if value is not None:self.values.setdefault(at,[]).append(value)
def main():
    cases=0;issues=[]
    for mode,offset,w,h,fmt,size in itertools.product(('normal','size-image','commands-image'),(0,4,8),(0,1,3,16,65535),(0,4,65535),(0,3,7),(0,1,2,3)):
        cmd,img,dest=g.commands,g.image,g.sizeout
        if mode=='size-image':dest=img+offset
        if mode=='commands-image':cmd=img+offset
        initial=g.fixture(w,h,fmt,size)
        for base,n in ((cmd,32),(img,16),(dest,4)):
            for addr in range(base-16,base+n+16):initial.setdefault(addr,0xa5)
        try:
            a=Trace(programs[0],initial.copy(),(cmd,img,dest)).run();b=Trace(programs[1],initial.copy(),(cmd,img,dest)).run()
        except (AssertionError,KeyError) as e:
            issues.append({'case':[mode,offset,w,h,fmt,size],'fault':str(e)[:100]});break
        for retail,compiled in enumerate(origins):
            if a.values.get(retail)!=b.values.get(compiled):
                issues.append({'case':[mode,offset,w,h,fmt,size],'retail':retail,'compiled':compiled,
                               'original':a.values.get(retail),'candidate':b.values.get(compiled)});break
        if issues:break
        cases+=1
    report={'completed_cases':cases,'first_issue':issues[:1],'structural_alignment_only':True,'uncredited':True}
    (out/'dataflow-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    assert cases==1620 and not issues
if __name__=='__main__':main()
