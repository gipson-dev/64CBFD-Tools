"""Execute both original accessors, both PRNGs and the complete polar lookup."""
import itertools,json,math,struct
from tools.tests import game_map_trail_samples_15106610_oracle as g
from tools.tests.test_game_random_selector_outputs_match import next_seed
from tools.tests.game_random_basis_position_oracle import lookup,TABLE,SEED,FACTOR
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

LOOKUP=0x151423D8;U64=(1<<64)-1
SPECS=((g.GET_SEGMENTS,0x133690,3),(g.GET_POINTS,0x13369C,10),
       (g.INTEGER,0xDAED0,18),(g.FLOAT,0xDAF18,25),(g.POLAR,0x170D24,25),(LOOKUP,0x16F888,27))

def fixture(c,seed,table,factor):
    abstract=g.fixture(c);m=dict(abstract);segments=g.RECORD+136;points=segments+c.count*52
    for i in range(c.count*52):m[segments+i]=abstract[g.SEGMENTS+i]
    for i in range((c.count+2)*12+16):m[points+i]=abstract[g.POINTS+i]
    g.put(m,SEED,seed,8);g.put(m,FACTOR,factor)
    m.update({TABLE+i:v for i,v in enumerate(table)})
    return m

def reference(initial,c):
    m=dict(initial);segments=g.RECORD+136;points=segments+c.count*52
    first,second=g.STACK+c.phase-32,g.STACK+c.phase-28
    calls=[(g.GET_SEGMENTS,(g.RECORD,)),(g.GET_POINTS,(g.RECORD,))]
    for axis in range(3):g.put(m,points+4*axis,g.read(m,g.RECORD+20+4*axis))
    for axis in range(3):g.put(m,points+(c.count+1)*12+4*axis,g.read(m,g.RECORD+56+4*axis))
    for i in range(1,c.count+1):
        seed=next_seed(g.read(m,SEED,8));g.put(m,SEED,seed,8);random=seed&255
        calls.append((g.INTEGER,()))
        seed=next_seed(seed);g.put(m,SEED,seed,8)
        unit=g.mul(g.bits(float(seed&65535)),g.read(m,FACTOR));calls.append((g.FLOAT,()))
        radius=g.mul(unit,g.read(m,g.RECORD+76))
        calls.extend(((g.POLAR,(random,radius,first,second)),(LOOKUP,(random,)),(LOOKUP,((random-64)&255,))))
        g.put(m,first,g.mul(radius,lookup(m,random-64)));g.put(m,second,g.mul(radius,lookup(m,random)))
        segment=segments+(i-1)*52
        for axis in range(3):
            value=g.add(g.add(g.mul(g.read(m,segment+28+4*axis),g.read(m,first)),
                            g.mul(g.read(m,segment+40+4*axis),g.read(m,second))),g.read(m,segment+4+4*axis))
            g.put(m,points+i*12+4*axis,value)
    return m,calls

class Connected(g.SampleOracle):
    def __init__(self,words,memory,c,code):
        super().__init__(words,memory,c);self.code.update(code)
    def record_call(self,target):
        if target==LOOKUP:self.calls.append((target,(g.u32(self.r[4]),)))
        else:super().record_call(target)
    def hook(self,target):raise AssertionError(('Unexpected opaque provider',hex(target)))
    def execute(self,w):
        op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==17 and rs==16 and fn==7:self.f[sh]=self.f[rd]^0x80000000;return
        if op==17 and rs==20 and fn==32:self.f[sh]=g.bits(float(g.signed(self.f[rd])));return
        island=g.INTEGER<=self.current_pc<g.INTEGER+72 or g.FLOAT<=self.current_pc<g.FLOAT+100
        if op in(55,63):
            p=g.u32(self.r[rs]+((w&65535)^32768)-32768);assert p%8==0
            if op==55:self.r[rt]=self.get(p,8)
            else:self.put(p,self.r[rt],8)
        elif op==0 and fn in(56,58,60,62,63):
            value=self.r[rt]&U64
            if fn in(56,60):value<<=sh+(32 if fn==60 else 0)
            elif fn in(58,62):value>>=sh+(32 if fn==62 else 0)
            else:value=(value if value<1<<63 else value-(1<<64))>>(sh+32)
            self.r[rd]=value&U64
        elif island and op==0 and fn in(37,38):self.r[rd]=(self.r[rs]|self.r[rt])if fn==37 else(self.r[rs]^self.r[rt])
        else:
            before=self.r[:];super().execute(w)
            if island:
                dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
                for i,v in enumerate(before):
                    if i!=dest and v>0xFFFFFFFF:self.r[i]=v
        self.r[0]=0

def run(root,out,words,retail):
    rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes();code={}
    for entry,offset,n in SPECS:
        raw=rom[offset:offset+n*4];at=elf_slot_offset(image,entry,n*4)
        assert image[at:at+n*4]==raw,(hex(entry),'Original helper differs')
        code.update(zip(range(entry,entry+n*4,4),struct.unpack('>%dI'%n,raw)))
    table_at=TABLE-0x80082B20+0x2275E0;table=rom[table_at:table_at+260]
    factor=struct.unpack_from('>I',rom,FACTOR-0x80082B20+0x2275E0)[0]
    assert image[elf_slot_offset(image,TABLE,260):][:260]==table
    assert image[elf_slot_offset(image,FACTOR,4):][:4]==struct.pack('>I',factor)
    seeds={}
    for seed in range(4096):seeds.setdefault(next_seed(seed)&255,seed)
    assert len(seeds)==256
    rows=[(g.Case(1,angle%8,0,phase),seed)for angle,seed in seeds.items()for phase in(0,8)]
    rows +=[(g.Case(count,i%8,0,phase),seed)for i,(count,seed,phase)in enumerate(itertools.product((0,2,4),
             (0,1,U64,1<<63,0x123456789ABCDEF0,0xFEDCBA9876543210),(0,8)))]
    seen=set();angles=set()
    for c,seed in rows:
        initial=fixture(c,seed,table,factor);expected,calls=reference(initial,c);models=[]
        for body in(words,retail):
            model=Connected(body,initial,c,code).run()
            assert g.public(model.memory)==g.public(expected),(c,seed,'Original provider output')
            assert model.calls==calls,(c,seed,'Original provider trace',model.calls,calls)
            seen.update(model.visits);models.append(model)
        assert g.frame(models[0].memory,c)==g.frame(models[1].memory,c),(c,seed,'Original provider frame')
        angles.update(a[0]for t,a in calls if t==g.POLAR)
    assert set(code)<=seen and len(angles)==256
    report=dict(cases=len(rows),original_helper_words=len(code),all_helper_words_executed=True,angles=256,
                original_accessors_and_64bit_PRNGs_and_polar_lookup=True,opaque_providers=False,
                full_parent_execution=False,hardware_or_gameplay_claim=False)
    (out/'connected.json').write_text(json.dumps(report,indent=2)+'\n');return report
