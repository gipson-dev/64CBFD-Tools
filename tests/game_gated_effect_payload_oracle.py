"""Gated sparse payload: preserve seeded guest padding and live factory reads."""
from dataclasses import dataclass,replace
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

ENTRY,OWNER,ALT,OUTPUT,FACTORY,ALLOCATE,COPY,CONSTANT=0x151937F4,0x30000,0x60000,0x50000,0x15134DAC,0x15167A68,0x10022EC0,0x800A81E4
U32=lambda v:v&0xFFFFFFFF
HALF=lambda v:((v&65535)^32768)-32768
GAPS=(1,2,3,9,10,11,0x25,0x2C,0x2D,0x31,0x32,0x33,0x3A,0x3B)
WORDS=(0,0x80000000,0x3F800000,0xBF800000,1,0x7F7FFFFF,0x7FC12345,0x7FA12345)
FIELDS=((8,0,1),(0xC,0xC1E00000,4),(0x10,0x40C00000,4),(0x14,0x3F800000,4),(0x18,0xC2680000,4),(0x1C,0xC0400000,4),(0x20,0xC1F80000,4),(0x24,2,1),(0x26,30,2),(0x28,25,2),(0x2A,750,2),(0x2E,3,1),(0x2F,3,1),(0x30,255,1),(0x38,4,1),(0x39,255,1))
DEFINED=tuple(i for i in range(60)if i not in GAPS)
assert len(DEFINED)==46 and len(GAPS)==14

@dataclass(frozen=True)
class Case:
    owner:int=OWNER
    active:int=1
    tag:int=255
    ignored1:int=0x876543FF
    ignored2:int=1
    constant:int=0x3F800000
    outcome:int=1
    mutation:int=0
    phase:int=0
    seed:int=0
    lazy:bool=False

def cases():
    rows=[Case(tag=tag,phase=p,constant=WORDS[tag%8],mutation=tag%4,ignored2=U32(tag*0x1234567))for tag,p in itertools.product(range(256),(0,8))]
    rows.extend(Case(owner=owner,active=active,phase=p,mutation=m,constant=WORDS[i%8],outcome=i%2,ignored1=(0,1,0x80000000,0xFFFFFFFF)[i%4],ignored2=(0xFFFFFFFF,0x80000000,1,0)[i%4],seed=i%16)for i,(owner,active,p,m)in enumerate(itertools.product((0,OWNER,ALT),(0,1,256,0x80000000,0xFFFFFFFF),(0,8),(0,1,2,3,4,16,17,18,23))))
    rows.extend(Case(owner=owner,active=0,lazy=True,phase=p)for owner,p in itertools.product((0,OWNER),(0,8)))
    rows.extend(Case(seed=seed,phase=p,mutation=m,tag=seed,constant=WORDS[seed%8])for seed,p,m in itertools.product(range(16),(0,8),(0,1,16,19)))
    return rows

def data(m,p,n):return bytes(m[p+i]for i in range(n))
def fixture(c,s):
    home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-4096,2048)}
    for base,n in((OWNER,0x60),(ALT,0x60),(OUTPUT-16,0xA0)):
        assert not STACK-4096<=base<STACK+4096
        m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
    if c.owner:
        put(m,c.owner,c.active);m[c.owner+0x3B]=c.tag
        if c.lazy:m.pop(c.owner+0x3B)
    if not c.lazy:put(m,s['constant'],c.constant)
    return m

def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-4096<=a<STACK+c.phase+2048}

def fill(m,p,c,s):
    m[p]=m[c.owner+0x3B];put(m,p+4,c.owner)
    for at,value,n in FIELDS:put(m,p+at,value,n)
    put(m,p+0x34,read(m,s['constant']))

def effect(m,p,c,s,stage):
    if stage==1:
        if c.mutation&1:m[p]^=0x55;put(m,p+0x28,-123,2)
        if c.mutation&2:
            m[c.owner+0x3B]^=255;put(m,c.owner,0);put(m,s['constant'],0x87654321)
        if c.mutation&4:
            for i in range(3):put(m,STACK+c.phase+4*i,0xABCDE000+i)
        if c.mutation&16:
            for i in GAPS:m[p+i]=(0xD0+i)&255

def reference(initial,c,s,connected=False,home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;p=home-60;calls=[];packets=[]
    if not c.owner or read(m,c.owner)==0:return m,calls,packets
    fill(m,p,c,s);packets.append((p,data(m,p,60)));calls.append((s['factory'],(p,0)))
    if connected:calls.append((ALLOCATE,(0x29,0,128,1,255,1)))
    effect(m,p,c,s,1)
    if c.outcome:
        if connected:calls.append((COPY,(OUTPUT+24,p,60)))
        for i,b in enumerate(data(m,p,60)):m[OUTPUT+24+i]=b
        effect(m,p,c,s,2)
        put(m,OUTPUT+0x54,-HALF(read(m,p+0x28,2)),2);put(m,OUTPUT+0x10,1);put(m,OUTPUT+0x14,0)
        for at in(0x70,0x74,0x78):put(m,OUTPUT+at,0)
    return m,calls,packets

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c,s,entry,connected=None,target=ENTRY):
        self.c,self.s,self.home,self.target=c,s,STACK+c.phase,target
        self.packets=[];self.payload_address=None
        super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(c.owner,c.ignored1,c.ignored2))
    def get(self,p,n):
        if getattr(self,'recording',False)and self.own_instruction:assert all(p+i in self.memory for i in range(n)),('unmapped read',hex(p),n)
        return super().get(p,n)
    def record_call(self,t):
        counts={self.target:3,self.s['factory']:2,ALLOCATE:6,COPY:3};assert t in counts,hex(t)
        a=tuple(U32(v)for v in self.arguments(counts[t]));self.calls.append((t,a))
        if t==self.s['factory']:
            self.payload_address=a[0];self.packets.append((a[0],data(self.memory,a[0],60)))
    def hook(self,t):
        c=self.c;p=self.payload_address;a=self.calls[-1][1]
        if t in(self.s['factory'],ALLOCATE):effect(self.memory,p,c,self.s,1);value=OUTPUT if c.outcome else 0
        else:
            assert t==COPY and a==(OUTPUT+24,p,60)
            packet=data(self.memory,p,60)
            for i,b in enumerate(packet):self.memory[a[0]+i]=b
            effect(self.memory,p,c,self.s,2);value=a[0]
        if t==self.s['factory']and value:
            packet=data(self.memory,p,60)
            for i,b in enumerate(packet):self.memory[value+24+i]=b
            effect(self.memory,p,c,self.s,2);put(self.memory,value+0x54,-HALF(read(self.memory,p+0x28,2)),2)
            put(self.memory,value+0x10,1);put(self.memory,value+0x14,0)
            for at in(0x70,0x74,0x78):put(self.memory,value+at,0)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=U32(value)

def state(m):return m.memory,m.r,m.f,m.trace,m.calls,m.packets,m.hi,m.lo,m.current_pc,m.delay_of,m.all_accesses

def programs(output,layout):
    s=json.loads((output/'private-layout-v2.json').read_text())['layouts'][layout];entry=s['entry'];words=[]
    for label in('original','C'):
        image=(output/('layout-%d-%s.elf'%(layout,label))).read_bytes();at=elf_slot_offset(image,entry,240);words.append(list(struct.unpack_from('>60I',image,at)))
    assert words[0]==words[1]
    return entry,s,words

def compare(models,c,expected,calls,packets):
    for m in models:
        assert(public(m.memory,c),m.calls,m.packets)==(public(expected,c),calls,packets),(c,m.calls,calls)
        assert m.r[29]==STACK+c.phase
    assert state(models[0])==state(models[1]),c

def qualify(root,output):
    count=0;seen=set();tags=set();all_padding=set()
    for layout in range(3):
        entry,s,words=programs(output,layout)
        for c in cases():
            initial=fixture(c,s);expected,calls,packets=reference(initial,c,s)
            models=[Oracle(code,initial,c,s,entry,target=entry).run()for code in words]
            compare(models,c,expected,calls,packets);count+=1;seen.update(v-layout*0x1000000 for m in models for v in m.visits)
            if packets:
                tags.add(packets[0][1][0]);p,packet=packets[0]
                assert all(packet[i]==initial[p+i]for i in GAPS)
                all_padding.update(packet[i]for i in GAPS)
    assert seen==set(range(ENTRY,ENTRY+240,4))and tags==set(range(256))and len(all_padding)>100
    prefixes=0;entry,s,words=programs(output,0)
    for c in(Case(owner=0),Case(active=0,lazy=True),Case(),Case(owner=ALT,phase=8,mutation=31)):
        initial=fixture(c,s);full=Oracle(words[0],initial,c,s,entry).run()
        for cut in range(full.all_accesses):
            models=[]
            for code in words:
                m=Oracle(code,initial,c,s,entry);m.cut=cut
                try:m.run()
                except faults.AccessBoundary:pass
                else:raise AssertionError('Access prefix did not fire')
                models.append(m)
            assert state(models[0])==state(models[1]);prefixes+=1
    return dict(success=True,cases=count,executions=count*2,corpus=len(cases()),layouts=3,covered_words=60,all256_owner_tags=True,initialized_payload_bytes=46,seeded_padding_bytes=14,padding_values_seen=len(all_padding),full60byte_packets_compared=True,all_GPR_FP_memory_calls_PC_delay_and_trace_equal=True,access_prefix_pairs=prefixes,lazy_gates_and_guest_incoming_home_changes=True,no_portable_native_padding_claim=True)

def helpers(root,output):
    rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes();connected={}
    for entry,off,n in((FACTORY,0x16225C,39),(COPY,0x22EC0,11)):
        raw=rom[off:off+n*4];at=elf_slot_offset(image,entry,n*4);assert image[at:at+n*4]==raw
        connected.update(zip(range(entry,entry+n*4,4),struct.unpack('>%dI'%n,raw)))
    entry,s,words=programs(output,0);seen=set();count=0
    for tag,constant,outcome,mutation,phase in itertools.product((0,128,255),WORDS,(0,1),(0,1,2,3,16,17,19),(0,8)):
        c=Case(tag=tag,constant=constant,outcome=outcome,mutation=mutation,phase=phase,seed=tag%16)
        initial=fixture(c,s);expected,calls,packets=reference(initial,c,s,connected=True)
        models=[Oracle(code,initial,c,s,entry,connected=connected).run()for code in words]
        compare(models,c,expected,calls,packets)
        if outcome:
            for m in models:
                source=packets[0][0];read_at=next(i for i,e in enumerate(m.trace)if e[:3]==('R',source+0x28,2));last_copy=max(i for i,e in enumerate(m.trace)if e[0]=='W'and OUTPUT+24<=e[1]<OUTPUT+84);assert read_at>last_copy
        seen.update(v for m in models for v in m.visits);count+=1
    assert set(connected)<=seen
    return dict(success=True,cases=count,executions=count*2,original_factory_words=39,original_copy_words=11,all50_helper_words_executed=True,retained_helpers_equal_original=True,allocation_success_and_failure=True,full60byte_copy_with_seeded_or_mutated_padding=True,post_copy_halfword_read_order_and_negation=True,allocator_mutation_probes_are_guest_only=True,only_allocator_is_opaque=True)


def padding_control(root,output,source,headers):
    from tools.experiments.game_remaining_donor_candidates import compile_owner
    from tools.experiments.game_four_head_lookup_match import payload
    import subprocess
    zero=''.join('        ((u8 *)&payload)[%d] = 0;\n'%i for i in GAPS)
    body=source.replace('        func_15134DAC(&payload, 0);',zero+'        func_15134DAC(&payload, 0);')
    assert body!=source
    obj,diag=compile_owner(root,output,headers+body,'padding-zero-negative');assert not diag
    raw,refs=payload(obj,'func_151937F4');assert len(raw)!=240 or raw!=payload(output/'selected-final.o','func_151937F4')[0]
    path=output/'padding-zero-negative.elf'
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(output/'layout-0-C.ld'),'-e','func_151937F4','--defsym=D_800A81E4=0x800A81E4','--defsym=func_15134DAC=0x15134DAC','-o',str(path),str(obj)],capture_output=True,check=True)
    image=path.read_bytes();at=elf_slot_offset(image,ENTRY,len(raw));code=struct.unpack_from('>%dI'%(len(raw)//4),image,at)
    entry,s,originals=programs(output,0);c=Case();initial=fixture(c,s)
    original=Oracle(originals[0],initial,c,s,entry).run();negative=Oracle(code,initial,c,s,entry).run()
    a=original.packets[0][1];b=negative.packets[0][1]
    assert bytes(a[i]for i in DEFINED)==bytes(b[i]for i in DEFINED)
    assert all(b[i]==0 for i in GAPS)and any(a[i]!=b[i]for i in GAPS)
    assert public(original.memory,c)!=public(negative.memory,c)
    return dict(success=True,effective=True,defined_fields_equal=True,copied_padding_observably_different=True,no_portable_native_padding_claim=True)
