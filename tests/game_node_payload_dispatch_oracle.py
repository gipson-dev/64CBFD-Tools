"""Independent mutable-list contract and bounded O32 instruction oracle."""
import itertools,struct
from dataclasses import dataclass,replace
from tools.experiments import game_node_payload_dispatch_candidates as candidate
from tools.experiments import game_node_payload_dispatch_match as match
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_recursive_node_search import reference as search_reference
from tools.tests.test_game_recursive_node_search import half,WindowBoundary
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.pad_generated_object import parse_object

OWNER,NODES,ROWS=0x20000,(0x24000,0x24040,0x24080),0x100000
SEARCH,LEAF=0x1514D4B8,0x1514EB8C
HANDLERS=(0x1514E89C,0x1514E920,0x1514E9DC,0x1514E9FC,0x1514EA1C,0x1514EB6C,0x1514F130,LEAF)
u32=lambda x:x&0xFFFFFFFF

def symbols():return dict(D_8008AB64=0x8008AB64,D_8008ABE8=0x8008ABE8,func_1514D4B8=SEARCH)
@dataclass(frozen=True)
class Case:
    kinds:tuple=(0,1,2)
    slots:tuple=(0,1,2,3,4,5,6,7)
    returns:tuple=(1,0,0x80000000)
    root:int=0
    first:int=0x12345678
    second:int=0xFEDCBA98
    phase:int=0
    mutation:int=0
    connected:bool=True
    actual:bool=False
    leaf:bool=False
    empty:bool=False

def args(c):return OWNER,u32(c.root),u32(c.first),u32(c.second)
def public(m):return {p:v for p,v in m.items()if not STACK-0x5000<=p<STACK+0x1000}
def fixture(c,context=None,s=None):
    s=symbols()if s is None else s;sp=STACK+c.phase
    m={sp+i:(i*17+0xA5)&255 for i in range(-0x4000,0x900)}
    m.update({OWNER+i:0xA5 for i in range(0x310)})
    put(m,OWNER+0x2F4,0 if c.empty else NODES[0])
    for i,node in enumerate(NODES):
        m.update({node+j:(i*41+j*13)&255 for j in range(0x24)})
        put(m,node+0x10,0x31000+i*16);put(m,node+0x14,NODES[i+1]if i<2 else 0)
        put(m,node+0x1C,c.kinds[i],2)
    if c.empty:return m
    if c.actual:
        pointers=context['pointers'];rows=[x['cells']for x in context['nodes']]
    else:
        pointers=[ROWS+i*16 for i in range(30)]
        rows=[[c.slots[i%8],0,1 if i==0 else -1,i+1 if i<6 else -1]for i in range(30)]
    for i,p in enumerate(pointers):put(m,s['D_8008ABE8']+i*4,p)
    if not c.actual:put(m,s['D_8008ABE8']+256*4,pointers[0])
    for p,row in zip(pointers,rows):
        for j,v in enumerate(row):put(m,p+j*2,v,2)
    for i,target in enumerate(HANDLERS+(0,0,0)):put(m,s['D_8008AB64']+4*i,target)
    return m

def effect(m,c,s,node,kind):
    if node!=NODES[0]:return
    if kind=='search'and c.mutation==1:
        put(m,node+0x1C,3,2);put(m,node+0x10,0xCAFEBABE)
    if (kind=='search'and c.mutation==2)or(kind=='callback'and c.mutation==3):put(m,node+0x14,NODES[2])
    if kind=='callback'and c.mutation==4:
        p=read(m,s['D_8008ABE8']+half(c.root)*4);put(m,p+4,-1,2)
        put(m,s['D_8008AB64']+4,HANDLERS[7])
    if kind=='callback'and c.mutation==5:
        p=read(m,s['D_8008ABE8']+half(read(m,NODES[1]+0x1C,2))*4);put(m,p,-1,2)
    if kind=='callback'and c.mutation==6:put(m,OWNER+0x2F4,0)

def reference(initial,c,s=None):
    s=symbols()if s is None else s;m=dict(initial);calls=[];outer=[];result=0
    node=read(m,OWNER+0x2F4);steps=0
    while node:
        steps+=1;assert steps<12,'reference list cycle'
        kind=half(read(m,node+0x1C,2));selected=kind==half(c.root)
        if not selected:
            p=read(m,s['D_8008ABE8']+half(c.root)*4);index=half(read(m,p+4,2))
            value,nested,_=search_reference(m,index,kind,entry=s['func_1514D4B8'],table=s['D_8008ABE8'])
            a=(u32(index),u32(kind));calls.append((s['func_1514D4B8'],a))
            outer.append(dict(kind='search',node=node,target=s['func_1514D4B8'],args=a,value=value))
            if c.connected:calls.extend(nested)
            else:effect(m,c,s,node,'search')
            selected=bool(value)
        if selected:
            kind=half(read(m,node+0x1C,2));p=read(m,s['D_8008ABE8']+kind*4);slot=half(read(m,p,2))
            if slot!=-1:
                target=read(m,s['D_8008AB64']+slot*4)
                assert target in HANDLERS,('unowned callback',target)
                a=(read(m,node+0x10),u32(c.first),u32(c.second))
                value=1 if c.leaf and target==LEAF else u32(c.returns[NODES.index(node)])
                calls.append((target,a));outer.append(dict(kind='callback',node=node,target=target,args=a,value=value))
                if not(c.leaf and target==LEAF):effect(m,c,s,node,'callback')
                result=int(bool(value))
        node=read(m,node+0x14)
    return dict(memory=m,calls=calls,outer=outer,value=result)

def helper_code(rom,c):
    code={}
    for entry,off,n,enabled in((SEARCH,0x17A968,43,c.connected),(LEAF,0x17C03C,6,c.leaf)):
        if enabled:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,off)))
    return code

def bound(obj,s):
    data,fs,rs=parse_object(obj);f=fs[candidate.FUNCTION];start,size=f['value'],f['size'];words=list(struct.unpack_from('>%dI'%(size//4),data,start))
    for at,rows in rs.items():
        if start<=at<start+size:
            word=words[(at-start)//4]
            for kind,name in rows:
                value=s[name]
                if kind=='R_MIPS_26':word=(word&0xFC000000)|((value>>2)&0x3FFFFFF)
                elif kind=='R_MIPS_HI16':word=(word&0xFFFF0000)|(((value+0x8000)>>16)&65535)
                elif kind=='R_MIPS_LO16':word=(word&0xFFFF0000)|(value&65535)
                else:raise AssertionError(kind)
            words[(at-start)//4]=word
    return words

class ProbeCode(faults.TrackedCode):
    ends=()
    def __getitem__(self,pc):
        if pc in self.ends:self.owner.current_pc=pc;self.owner.delay_of=None;raise WindowBoundary(pc)
        return super().__getitem__(pc)

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=match.ENTRY,connected=None,expected=None,arguments=None,dispatch_entry=None,dispatch_size=None):
        s=symbols()if s is None else s
        self.expected=expected;self.outer_index=0;self.call_index=0;self.last_outer=None
        super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=args(c)if arguments is None else arguments)
        self.dispatch_entry=entry if dispatch_entry is None else dispatch_entry;self.dispatch_size=len(words)*4 if dispatch_size is None else dispatch_size
        self.minimum_sp=self.r[29];self.code=ProbeCode(self.code,self)
    def execute(self,word):
        super().execute(word);self.minimum_sp=min(self.minimum_sp,self.r[29])
    def record_call(self,t):
        if t==self.dispatch_entry:count=4
        elif t==self.syms['func_1514D4B8']:count=2
        else:assert t in HANDLERS,hex(t);count=3
        a=tuple(map(u32,self.arguments(count)));self.calls.append((t,a));self.events.append(('CALL',t,a))
        outer=self.dispatch_entry<=self.current_pc<self.dispatch_entry+self.dispatch_size
        if self.expected is not None and t!=self.dispatch_entry:
            assert self.call_index<len(self.expected['calls']),('extra call',t,a)
            assert(t,a)==self.expected['calls'][self.call_index],('call contract',self.call_index,(t,a),self.expected['calls'][self.call_index])
            self.call_index+=1
            if outer:
                self.last_outer=self.expected['outer'][self.outer_index];self.outer_index+=1
                assert(t,a)==(self.last_outer['target'],self.last_outer['args'])
    def hook(self,t):
        if self.expected is None:
            assert self.case.mutation==0
            value=0 if t==self.syms['func_1514D4B8']else 1
        else:
            row=self.last_outer;assert row['target']==t;effect(self.memory,self.case,self.syms,row['node'],row['kind']);value=row['value']
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def cases():
    for kinds,root,slots,returns,phase in itertools.product(((0,1,2),(3,0,1),(6,2,0),(1,1,1)),(0,2,5),
            (tuple(range(8)),(-1,1,2,3,4,5,6,7),(0,-1,-1,3,4,5,6,7)),((0,0,0),(1,0,0),(0,1,0),(0xFFFFFFFF,0,0x80000000)),(0,8)):
        yield Case(kinds=kinds,root=root,slots=slots,returns=returns,phase=phase)
    for mutation,connected,first,second,phase in itertools.product(range(7),(False,True),(0,0x100,0xFFFFFFFF,0x80000000),(0x100,0xFEDCBA98),(0,8)):
        if connected and mutation in(1,2):continue
        yield Case(kinds=(1,2,3),mutation=mutation,connected=connected,first=first,second=second,phase=phase)
    for raw,phase in itertools.product((0x12340000,0xFFFF0001,0x80000002),(0,8)):
        yield Case(root=raw,phase=phase)
    for phase in(0,8):yield Case(empty=True,phase=phase)
    for phase in(0,8):yield Case(kinds=(256,6,6),root=256,phase=phase,returns=(1,0,0))

def controls():
    b=candidate.SELECTED
    return dict(any_success=b.replace('result = 0;\n                }','result = result;\n                }'),
      initial_true=b.replace('s32 result = 0;','s32 result = 1;'),
      wrong_link=b.replace('[root][2]','[root][3]'),
      no_bypass=b.replace('node->unk1C == root ||','0 ||'),
      low_root=b.replace('    while (node != NULL) {','    root = (u8)root;\n    while (node != NULL) {'),
      narrow_arguments=b.replace('node->unk10, first, second','node->unk10, (u8)first, (u8)second'),
      skip_zero=b.replace('(u32)-1 != (u32)callback','callback != -1 && callback != 0'),
      raw_result=b.replace('if (D_8008AB64[callback](node->unk10, first, second)) {\n                    result = 1;\n                } else {\n                    result = 0;\n                }','result = D_8008AB64[callback](node->unk10, first, second);'),
      wrong_payload=b.replace('node->unk10, first','(s32)node->next, first'),
      cached_next=b.replace('    s16 callback;','    s16 callback;\n    GameListNode *next;').replace('    while (node != NULL) {','    while (node != NULL) {\n        next = node->next;').replace('node = node->next;','node = next;'),
      cached_kind=b.replace('    s16 callback;','    s16 callback;\n    s16 kind;').replace('    while (node != NULL) {','    while (node != NULL) {\n        kind = node->unk1C;').replace('D_8008ABE8[node->unk1C][0]','D_8008ABE8[kind][0]'))
