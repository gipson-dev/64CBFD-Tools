"""Affine random position: provider timing, input/output aliases and original math."""
from dataclasses import dataclass,replace
import itertools,json,math,struct
from tools.tests import game_embedded_integer_oscillator_oracle as machine
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

ENTRY,OWNER,OUTPUT,OTHER,ALT,STATE=0x1514F808,0x30000,0x50000,0x51000,0x52000,0x53000
INTEGER,FLOAT,DIRECTION,LOOKUP,TABLE,SEED,FACTOR=0x150ADA20,0x150ADA68,0x15143874,0x151423D8,0x8009A220,0x800885B0,0x8009F740
STACK=machine.STACK
SHAPES=(-1,0,1,2,4,5,6,7,8,9,10)
PATTERNS=(0.,-0.,1.25,-2.5,16777216.,-16777216.,1e-10,-1e10)
u32=machine.u32
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))

@dataclass(frozen=True)
class Case:
    rng:int=0x876543FF
    unit:int=0x3E800000
    scale:int=0x3FC00000
    pattern:int=0
    out_index:int=-1
    mutation:int=0
    phase:int=0
    seed:int=0x123456789ABCDEF0
    alias:int=0
    output_override:int=0

def cases():
    rows=[]
    for angle,phase in itertools.product(range(256),(0,8)):
        rows.append(Case(rng=0x87654300|angle,unit=(0,0x80000000,0x3E800000,0x3F800000)[angle%4],scale=bits((.25,-.5,1.,2.)[angle%4]),pattern=angle%8,out_index=SHAPES[angle%len(SHAPES)],mutation=angle%8,phase=phase))
    rows.extend(Case(out_index=shape,mutation=mode,phase=phase,pattern=i%8)for i,(shape,mode,phase)in enumerate(itertools.product(SHAPES,(0,1,2,3,4,7,8,16,24,32,63),(0,8))))
    rows.extend(Case(pattern=p,scale=bits(scale),phase=phase)for p,scale,phase in itertools.product(range(8),(0.,-0.,.125,-1.,3.),(0,8)))
    rows.extend(Case(out_index=-2,phase=p,mutation=m)for p,m in itertools.product((0,8),(0,7,24)))
    return rows

def output(c):return c.output_override or (OUTPUT if c.out_index==-1 else STACK+c.phase+0x100 if c.out_index==-2 else OWNER+c.out_index*4)

def fixture(c,table=b''):
    assert all(not STACK-4096<=p<STACK+8192 for p in (OWNER,OUTPUT,OTHER,ALT,STATE))
    home=STACK+c.phase;m={home+i:(i*17+165)&255 for i in range(-4096,4096)}
    for base,size in((OWNER-16,0xA0),(OUTPUT-16,64),(OTHER-16,64),(ALT-16,0xA0),(STATE-16,0x100),(SEED-8,24),(FACTOR-8,24)):
        m.update({base+i:(i*29+c.pattern*13+90)&255 for i in range(size)})
    for base in(OWNER,ALT):
        for i in range(16):put(m,base+i*4,bits(PATTERNS[(i+c.pattern)%len(PATTERNS)]))
    put(m,SEED,c.seed,8);put(m,FACTOR,0x37800080)
    for i,b in enumerate(table):m[TABLE+i]=b
    return m

def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-4096<=a<STACK+c.phase+4096}

def effect(m,c,ordinal,home):
    if ordinal==1 and c.mutation&1:
        for index,value in((10,3.25),(1,-7.),(4,2.)):put(m,OWNER+index*4,bits(value))
    if ordinal==2 and c.mutation&2:
        for index,value in((10,-2.5),(7,11.),(2,13.)):put(m,OWNER+index*4,bits(value))
    if ordinal==3 and c.mutation&4:
        for index,value in((1,17.),(5,-5.),(9,.75)):put(m,OWNER+index*4,bits(value))
    if ordinal==3 and c.mutation&8:put(m,home+4,bits(-.5))
    if ordinal==3 and c.mutation&16:put(m,home+8,OTHER)
    if ordinal==1 and c.mutation&32:put(m,home,ALT)

def lookup(m,angle):
    angle&=255;index=64-(angle&63)if angle&64 else angle&63;word=read(m,TABLE+index*4)
    return word if angle&192 in(0,192)else word^0x80000000

def reference(initial,c,s,home=None,real=False):
    m=dict(initial);home=STACK+c.phase if home is None else home
    put(m,home,OWNER);put(m,home+4,c.scale);put(m,home+8,output(c))
    calls=[(s['integer'],())]
    if real:
        seed=machine.next_seed(read(m,SEED,8));put(m,SEED,seed,8);random=u32(seed)
    else:effect(m,c,1,home);random=c.rng
    calls.append((s['floating'],()))
    if real:
        seed=machine.next_seed(read(m,SEED,8));put(m,SEED,seed,8);unit=mul(bits(float(seed&65535)),read(m,FACTOR))
    else:effect(m,c,2,home);unit=c.unit
    angle=random&255;radius=mul(unit,read(m,OWNER+40));first=home-8;second=home-4
    calls.append((s['direction'],(angle,radius,first,second)))
    if real:
        calls.extend(((LOOKUP,(angle,)),(LOOKUP,((angle-64)&255,))))
        x=mul(radius,lookup(m,angle-64));y=mul(radius,lookup(m,angle))
    else:
        effect(m,c,3,home);x=bits((angle-128)*.125);y=bits((64-angle)*.25)
    put(m,first,x);put(m,second,y)
    dest=read(m,home+8);scale=read(m,home+4)
    for i in range(3):
        value=mul(add(add(mul(read(m,OWNER+(i+4)*4),x),mul(read(m,OWNER+(i+7)*4),y)),read(m,OWNER+(i+1)*4)),scale)
        put(m,dest+i*4,value)
    return m,calls,dest

class Oracle(machine.Oracle):
    def __init__(self,words,memory,c,s,entry,connected=None,target_entry=ENTRY):
        self.target=target_entry
        super().__init__(words,memory,c,s,entry,connected=connected)
        self.home=STACK+c.phase
        self.r[4:7]=[OWNER,c.scale,output(c)]
        self.target_entry=target_entry
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63==7:
            self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
        elif w>>26==17 and w>>21&31==16 and w&63 in(0,2):
            assert all(math.isfinite(floating(self.f[i]))for i in(w>>16&31,w>>11&31))
            super().execute(w)
            assert math.isfinite(floating(self.f[w>>6&31]))
        else:super().execute(w)
    def record_call(self,t):
        if t in(self.s['integer'],self.s['floating']):args=()
        elif t==self.s['direction']:args=tuple(u32(v)for v in self.r[4:8])
        elif t==LOOKUP:args=(u32(self.r[4]),)
        elif t==self.target:args=tuple(u32(v)for v in self.r[4:7])
        else:raise AssertionError(hex(t))
        self.calls.append((t,args))
    def hook(self,t):
        c=self.c
        if t==self.s['integer']:ordinal=1;answer=c.rng
        elif t==self.s['floating']:ordinal=2;answer=0xABCD
        else:assert t==self.s['direction'];ordinal=3;answer=0xABCDE
        effect(self.memory,c,ordinal,self.home)
        if ordinal==3:
            angle,radius,x,y=self.calls[-1][1]
            put(self.memory,x,bits((angle-128)*.125));put(self.memory,y,bits((64-angle)*.25))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(answer)
        if ordinal==2:self.f[0]=c.unit

def state(m):
    return m.memory,m.r,m.f[20:],m.trace,m.calls,m.hi,m.lo,m.current_pc,m.delay_of,m.all_accesses

def programs(output,layout):
    info=json.loads((output/'private-roles-v4.json').read_text());row=info['layouts'][layout];entry=row['entry'];images=[]
    for label in('original','raw'):
        image=(output/('layout-%d-%s.elf'%(layout,label))).read_bytes();at=machine.elf_slot_offset(image,entry,240);images.append(list(struct.unpack_from('>60I',image,at)))
    normalized=images[1][:]
    for at,before,after in info['patches']:assert normalized[at//4]==before;normalized[at//4]=after
    assert normalized==images[0]
    return entry,row,(images[0],normalized,images[1])

def compare(models,c,expected,calls,dest):
    for m in models:
        assert public(m.memory,c)==public(expected,c),(c,m.calls,calls)
        assert m.calls==calls,(c,m.calls,calls)
        assert bytes(m.memory[dest+i]for i in range(12))==bytes(expected[dest+i]for i in range(12)),(c,hex(dest),bytes(m.memory[dest+i]for i in range(12)).hex(),bytes(expected[dest+i]for i in range(12)).hex(),m.calls)
        assert m.r[29]==STACK+c.phase
    assert state(models[0])==state(models[1])==state(models[2]),c

def qualify(root,output):
    count=0;seen=set();angles=set()
    for layout in range(3):
        entry,s,roots=programs(output,layout)
        for c in cases():
            initial=fixture(c);expected,calls,dest=reference(initial,c,s)
            models=[Oracle(words,initial,c,s,entry,target_entry=entry).run()for words in roots]
            compare(models,c,expected,calls,dest);count+=1
            seen.update(v-layout*0x1000000 for m in models for v in m.visits);angles.add(c.rng&255)
    assert seen==set(range(ENTRY,ENTRY+240,4))and angles==set(range(256))
    entry,s,roots=programs(output,0);prefixes=0
    for c in(Case(),Case(out_index=5,mutation=7),Case(out_index=7,phase=8,mutation=63),Case(out_index=-2)):
        initial=fixture(c);full=Oracle(roots[0],initial,c,s,entry).run()
        for cut in range(full.all_accesses):
            models=[]
            for words in roots:
                m=Oracle(words,initial,c,s,entry);m.cut=cut
                try:m.run()
                except machine.AccessBoundary:pass
                else:raise AssertionError('Access prefix did not fire')
                models.append(m)
            assert state(models[0])==state(models[1])==state(models[2]);prefixes+=1
    return dict(success=True,cases=count,executions=count*3,layouts=3,corpus=len(cases()),covered_words=60,all256_angles=True,access_prefix_triples=prefixes,all_memory_and_GPR_and_saved_FP_and_access_trace_equal=True,caller_clobbered_FP_roles_abstractly_proven=True,provider_mutations_and_output_basis_aliases=True,guest_incoming_home_changes_and_caller_stack_outputs=True,finite_binary32_domain=True,no_FCSR_or_NaN_payload_claim=True)

def helpers(root,output):
    rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes();code={}
    specs=((INTEGER,0xDAED0,18),(FLOAT,0xDAF18,25),(DIRECTION,0x170D24,25),(LOOKUP,0x16F888,27))
    for entry,off,n in specs:
        raw=rom[off:off+n*4];at=machine.elf_slot_offset(image,entry,n*4);assert image[at:at+n*4]==raw
        code.update(zip(range(entry,entry+n*4,4),struct.unpack('>%dI'%n,raw)))
    off=TABLE-0x80082B20+0x2275E0;table=rom[off:off+260];at=machine.elf_slot_offset(image,TABLE,260);assert image[at:at+260]==table
    seeds={}
    for seed in range(4096):seeds.setdefault(machine.next_seed(seed)&255,seed)
    assert set(seeds)==set(range(256));cases_real=[Case(seed=seed,out_index=SHAPES[i%len(SHAPES)],pattern=i%8,phase=i%2*8)for i,seed in enumerate(seeds.values())]
    cases_real.extend(Case(seed=seed,out_index=out,phase=p,pattern=i%8)for i,(seed,out,p)in enumerate(itertools.product((0,1,0xFFFFFFFFFFFFFFFF,0x8000000000000000,0x123456789ABCDEF0,0xFEDCBA9876543210),SHAPES,(0,8))))
    entry,s,roots=programs(output,0);seen=set();angles=set()
    for c in cases_real:
        initial=fixture(c,table);expected,calls,dest=reference(initial,c,s,real=True)
        models=[Oracle(words,initial,c,s,entry,connected=code).run()for words in roots]
        compare(models,c,expected,calls,dest);seen.update(v for m in models for v in m.visits);angles.add(calls[2][1][0])
    assert set(code)<=seen and angles==set(range(256))
    return dict(success=True,cases=len(cases_real),executions=len(cases_real)*3,original_helper_words=95,all95_words_executed=True,all256_lookup_angles=True,retained_helpers_and_65word_table_equal_original=True,independent_64bit_seed_and_folded_lookup=True,no_opaque_provider_in_connected_cases=True)
