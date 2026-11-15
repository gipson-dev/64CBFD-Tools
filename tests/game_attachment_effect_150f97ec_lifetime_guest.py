"""Reuse the bounded helper model and reject the apparent 89-word private fit."""
from pathlib import Path
import ast,hashlib,itertools,json,struct
from functools import lru_cache
from tools.experiments import game_attachment_effect_150f97ec_lifetime as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
ENTRY=s.ENTRY;ACTOR=0x30000;MATRIX=0x50000;syms=s.symbols()
TRANS,FLOAT,INTEGER,EFFECT=(syms[n] for n in ('func_15145EA4','func_150ADA68','func_150ADA20','func_15102B38'))
SLOT=syms['D_80088B50'];POINT=syms['D_800A1C48'];OTHER=syms['D_800A1C54']
# Import only the prior model definitions. Its historical script's top-level
# artifact reads, loops and receipts must not run or overwrite old evidence.
legacy=s.ROOT/'tools/tests/game_attachment_effect_150f97ec_guest.py'
assert hashlib.sha256(legacy.read_bytes()).hexdigest()==s.MANIFEST['oracle_sha256']
nodes=[n for n in ast.parse(legacy.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ('fixture','Oracle','validate')]
assert len(nodes)==3;exec(compile(ast.Module(body=nodes,type_ignores=[]),str(legacy),'exec'),globals())
LegacyOracle=Oracle
class Oracle(LegacyOracle):
    def hook(self,t):
        a=self.calls[-1][1]
        if t==TRANS:source,destination=read(self.memory,a[0]),read(self.memory,a[1])
        super().hook(t)
        if t==TRANS:
            # The real point-list interface advances both pointer variables.
            put(self.memory,a[0],source+12);put(self.memory,a[1],destination+12)

def corpus():
    return tuple(itertools.product((0,1),(0,5,255),(0,255,0x100,0xdead01ff),(0,1),(0,1),((0,0),(0xffffffff,0xffffffff),(7,155),(3,156),(0x80000000,0x7fffffff)),(0,0x87654321)))
def public(memory):return {a:b for a,b in memory.items() if not STACK-2048<=a<STACK+512}
def run(words,row):
    attached,index,selector,mutation,seed,rand,context=row;initial=fixture(seed,attached,index)
    m=Oracle(words,initial,selector,context,mutation,rand);before=m.r[:];before_f=m.f[:];m.run();validate(m,attached,index,selector,context,mutation,rand)
    assert m.r[29]==before[29] and m.r[16:24]==before[16:24] and m.r[28]==before[28] and m.f[20:]==before_f[20:]
    return m

class Caller(Oracle):
    def __init__(self,body,initial,selector,mutation,rand,poison=None):
        self.selector=selector;self.context=1;self.mutation=mutation;self.random=rand;self.nfloat=self.nint=0;self.records=[];self.entries=[]
        self.start,self.end=0x1502890c,0x15029ba4
        window=struct.unpack_from('>5I',retail_input(),0x55dbc)
        assert window==(0x93a50773,0x0d43e5fb,0x24060001,0x100004a2,0x24020001)
        connected=dict(zip(range(ENTRY,ENTRY+4*len(body),4),body));connected[self.end]=0
        FactoryOracle.__init__(self,window,initial,Case(),entry=self.start,s={},arguments=(ACTOR,),connected=connected)
        class Code(WindowCode):
            def __getitem__(self,pc):
                if poison is not None and pc==0x15028918:self.owner.r[2]=poison
                return super().__getitem__(pc)
        self.code=Code(self.code,self);self.code.ends=(self.end,)
    def record_call(self,t):
        if t==ENTRY:self.entries.append(tuple(self.arguments(3)));return
        super().record_call(t)

@lru_cache(maxsize=1)
def retail_input():return (s.OUT/'production-baseline/conker/conker.us.bin').read_bytes()

def main():
    s.immutable();programs=s.programs();rows=corpus();count=0;visited={label:set() for label in programs}
    for row in rows:
        machines=[run(p,row) for p in programs.values()]
        for label,m in zip(programs,machines):visited[label].update(m.visits)
        assert all(public(m.memory)==public(machines[0].memory) for m in machines)
        count+=1
    attached,index,selector,mutation,seed,rand,context=rows[0]
    initial=fixture(seed,attached,index);null={label:run(p,rows[0]) for label,p in programs.items()}
    assert null['retail'].memory==null['conditional_triple'].memory
    home_source=STACK-0x70+0x54;home_destination=STACK-0x70+0x50
    assert read(null['early_triple'].memory,home_source)==POINT and read(null['early_triple'].memory,home_destination)==STACK-12
    changed={p for p in initial if null['early_triple'].memory[p]!=null['retail'].memory[p]}
    assert changed and changed<={home_source+i for i in range(4)}|{home_destination+i for i in range(4)}
    faults={};prefix_states={}
    for label in ('retail','early_triple'):
        complete=null[label];cut=next(i for i,event in enumerate(complete.trace) if event[:3]==('R',ACTOR+0x1d4,4))
        m=Oracle(programs[label],initial,selector,context,mutation,rand);m.cut=cut
        try:m.run()
        except AccessBoundary:pass
        else:raise AssertionError('Attachment read boundary did not fire')
        assert (m.dispatched_word>>26)==35 and (m.dispatched_word&65535)==0x1d4
        prefix_states[label]=m.memory;faults[label]=dict(cut=cut,pc=hex(m.current_pc),word=hex(m.dispatched_word))
    assert prefix_states['retail']!=prefix_states['early_triple']
    callers=0
    for row in rows[::19]:
        attached,index,selector,mutation,seed,rand,context=row
        for p in programs.values():
            initial=fixture(seed,attached,index);initial[STACK+0x773]=selector&255;m=Caller(p,initial,selector&255,mutation,rand)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Caller continuation not reached')
            validate(m,attached,index,selector&255,1,mutation,rand);assert m.entries==[(ACTOR,selector&255,1)] and m.r[2]==1
        callers+=1
    poison_cases=0
    for poison in (0,1,0xdeadbeef):
        initial=fixture(0,1,5);initial[STACK+0x773]=255;m=Caller(programs['retail'],initial,255,1,(7,155),poison)
        try:m.run()
        except WindowBoundary:pass
        else:raise AssertionError('Poison caller failed to stop')
        assert m.r[2]==1;poison_cases+=1
    controls=[];base=programs['conditional_pair']
    for label,old,new in (('spread',0x3c014160,0x3c014170),('modulus',0x24010003,0x24010004),('coefficient',0x3c0143c8,0x3c0143c9)):
        altered=base[:];assert altered.count(old)==1;altered[altered.index(old)]=new
        try:run(altered,(1,5,255,1,0,(7,155),0x87654321))
        except AssertionError:controls.append(label)
        else:raise AssertionError(('Ineffective semantic control',label))
    assert len(controls)==3 and all(len(visited[label])==len(words) for label,words in programs.items());s.immutable()
    report=dict(finite_cases_per_stream=count,streams=len(programs),visited_words={label:len(v) for label,v in visited.items()},caller_cases_per_stream=callers,caller_window_words=5,return_poison_controls=poison_cases,effective_semantic_controls=controls,cursor_advancement_modeled=True,null_path_false_fit_rejected=True,false_fit_changed_private_bytes=len(changed),fired_named_attachment_prefixes=faults,conditional_null_private_memory_equal=True,full_private_FP_hardware_and_parent_execution_uncredited=True,c_match_credit=0)
    (s.OUT/'lifetime-guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
