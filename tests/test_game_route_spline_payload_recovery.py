"""Full semantic recovery, real leaf instructions and explicit uninstalled boundary."""
import csv
import itertools
import json
import math
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_spline_payload_recovery as source
from tools.tests import test_game_route_projection_setup as guest
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed

put,read,STACK=guest.put,guest.read,guest.STACK
RECORD,ACTOR,OBJECT,TABLE,QUEUE=0x90000,0x50000,0x60000,0x30000,0x70000
COUNT,GLOBAL,MODE,FRAMES,QUEUES=0x80087290,0x800D2350,0x800D23A8,0x800BE9E4,0x800DC2B0
STOP_VALUE,RATE,SCALE=0x8009DA0C,0x8009DA10,0x8009DA18
POSITION,SELECTOR,ENQUEUE,SPLINE,SIN,COS=0x15086CBC,0x1508907C,0x1512D560,0x150497E0,0x15047D60,0x15047C00
HELPERS={POSITION:35,SELECTOR:91,ENQUEUE:41,SPLINE:49}


def double(value):return struct.unpack('>Q',struct.pack('>d',value))[0]
def from_double(value):return struct.unpack('>d',struct.pack('>Q',value))[0]
def signed_byte(value):return ((value&255)^128)-128


def fixture(stop=0,null=False,initialized=1,valid=4,fraction=0.25,frames=1,heading=45.,bank=0,cursor=0,
        mode=0,count=8,late=False,alias=0):
    record=ACTOR-0x58 if alias==1 else RECORD
    queue=ACTOR+0x318 if alias==2 else QUEUE
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x500)}
    for at,n in ((record,0x100),(ACTOR-0x100,0x800),(OBJECT,0x400),(TABLE,0x1100),
            (QUEUE,0xB0*256),(0x200,0x400)):
        memory.update({at+i:0xA5 for i in range(n)})
    for i in range(270):
        for axis in range(3):put(memory,TABLE+i*16+axis*2,(i*37+axis*19)%511-255,2)
        for j in range(5):put(memory,TABLE+i*16+9+j,255,1)
        put(memory,TABLE+i*16+14,4 if 4<=i<8 else 6,1)
        put(memory,TABLE+i*16+15,0 if 4<=i<8 else (signed_byte(mode)+1)&255,1)
    for i in range(4):
        put(memory,TABLE+i*16+9,(i+1)%4,1);put(memory,TABLE+i*16+10,(i-1)%4,1)
        put(memory,TABLE+i*16+11,i+4,1)
    if late:
        for i in range(258):put(memory,TABLE+i*16+15,3,1)
        put(memory,TABLE+257*16+14,6,1);put(memory,TABLE+257*16+15,(signed_byte(mode)+1)&255,1)
    for i in range(4):put(memory,record+0x44+i,i if i<valid else 255,1)
    for axis,value in enumerate((17.5,-91.25,255.)):
        put(memory,ACTOR+0x14+axis*4,guest.base.bits(value));put(memory,record+0x38+axis*4,guest.base.bits(value*2))
    put(memory,record+0x49,initialized,1);put(memory,record+0x34,guest.base.bits(fraction))
    put(memory,ACTOR+0x40,guest.base.bits(heading));put(memory,ACTOR+0x318,0 if null else OBJECT)
    put(memory,OBJECT+0x23D,bank,1);put(memory,0xA+0x23D,1,1)
    put(memory,COUNT,count,2);put(memory,GLOBAL,TABLE);put(memory,MODE,mode,1);put(memory,FRAMES,frames)
    put(memory,STOP_VALUE,guest.base.bits(999.));put(memory,RATE,guest.base.bits(0.017));put(memory,SCALE,double(0.01745),8)
    put(memory,QUEUES,queue)
    for i in range(256):
        at=queue+i*0xB0+0xAC
        if alias!=2 or i<3:put(memory,at,cursor)
    return memory,(record,ACTOR,stop)


def reference(initial,args):
    memory=dict(initial);record,actor,stop=args;calls=[]
    def get(at,n=4):return read(memory,at,n)
    def store(at,value,n=4):put(memory,at,value,n)
    def enqueue(obj,command,payload):
        calls.append((ENQUEUE,(obj,command,payload)))
        def q():return (get(QUEUES)+get(obj+0x23D,1)*176)&0xFFFFFFFF
        queue=q();index=get(queue+172);store((queue+index*8)&0xFFFFFFFF,command)
        queue=q();index=get(queue+172);store((queue+index*8+4)&0xFFFFFFFF,payload)
        queue=q();store(queue+172,get(queue+172)+1)
        queue=q()
        if get(queue+172)==20:store(queue+172,0)
    def neighbor(node,kind,excluded):
        calls.append((SELECTOR,(node,kind,excluded,0)));result=255
        if node<guest.base.half(get(COUNT,2)):
            table=get(GLOBAL)
            for j in range(5):
                candidate=get(table+node*16+9+j,1)
                if candidate==255 or candidate==excluded:continue
                if get(table+candidate*16+14,1)!=kind:continue
                result=candidate
                if get(table+candidate*16+15,1)==0:break
        return result
    object=get(actor+0x318)
    if not object:return guest.public(memory),calls
    payload=record+76
    if stop:
        store(payload+16,120);store(payload+12,get(STOP_VALUE));enqueue(get(actor+792),10,payload)
        enqueue(get(actor+792),6,get(object+573,1));store(record+73,0,1)
        return guest.public(memory),calls
    if signed_byte(get(record+73,1))==0:
        route=(signed_byte(get(MODE,1))+1)&255;limit=guest.base.half(get(COUNT,2));i=0
        while i<limit:
            node=get(GLOBAL)+i*16
            if get(node+14,1)==6 and get(node+15,1)==route:
                store(record+68,i,1);limit=guest.base.half(get(COUNT,2));i=limit
            i+=1
        store(record+69,neighbor(get(record+68,1),6,255),1)
        store(record+70,neighbor(get(record+69,1),6,get(record+68,1)),1)
        store(record+71,neighbor(get(record+70,1),6,get(record+69,1)),1)
        for axis in range(3):store(record+56+axis*4,get(actor+20+axis*4))
        store(record+52,0);enqueue(get(actor+792),5,get(object+573,1));store(record+73,1,1)
    phase=guest.base.add(get(record+52),guest.base.mul(get(RATE),guest.base.bits(float(signed(get(FRAMES))))))
    store(record+52,phase)
    if guest.base.floating(phase)>=1.:
        node=get(record+70,1)
        if node==255:store(record+52,guest.base.bits(1.))
        else:
            nxt=get(record+71,1);old=get(record+69,1)
            store(record+69,node,1);store(record+52,guest.base.sub(phase,guest.base.bits(1.)))
            store(record+70,nxt,1);store(record+68,old,1)
            store(record+71,neighbor(nxt,6,node),1)
    points=[[],[],[],[],[],[]];previous=False;scale=from_double(get(SCALE,8))
    def position(node,channels,i):
        calls.append((POSITION,(node,*[('channel',c,i) for c in channels])))
        if not (0<=node<guest.base.half(get(COUNT,2))):raise ValueError('Undefined source array fixture')
        table=get(GLOBAL)
        for axis,c in enumerate(channels):points[c].append(guest.base.bits(float(guest.base.half(get(table+node*16+axis*2,2)))))
    for i in range(4):
        node=get(record+68+i,1)
        if node!=255:
            previous=True;position(node,(0,1,2),i);position(neighbor(get(record+68+i,1),4,255),(3,4,5),i)
        elif previous:
            previous=False;angle=guest.base.bits(guest.base.floating(get(actor+64))*scale)
            calls.append((SIN,(angle,)));sine=guest.base.bits(math.sin(guest.base.floating(angle)))
            points[0].append(guest.base.sub(get(record+56),guest.base.mul(sine,guest.base.bits(500.))))
            points[1].append(guest.base.add(get(record+60),guest.base.bits(180.)))
            calls.append((COS,(angle,)));cosine=guest.base.bits(math.cos(guest.base.floating(angle)))
            points[2].append(guest.base.sub(get(record+64),guest.base.mul(cosine,guest.base.bits(500.))))
            points[3].append(get(record+56));points[4].append(guest.base.add(get(record+60),guest.base.bits(120.)));points[5].append(get(record+64))
        else:
            if i<2:raise ValueError('Leading undefined spline history')
            for channel in points:channel.append(guest.base.add(guest.base.sub(channel[-1],channel[-2]),channel[-1]))
    fraction=get(record+52)
    add,mul=guest.base.add,guest.base.mul
    for c,p in enumerate(points):
        calls.append((SPLINE,(tuple(p),0,fraction)))
        half=mul(guest.base.bits(-.5),p[0])
        cubic=add(mul(p[3],guest.base.bits(.5)),add(add(half,mul(guest.base.bits(1.5),p[1])),mul(guest.base.bits(-1.5),p[2])))
        quadratic=add(mul(p[3],guest.base.bits(-.5)),add(add(p[0],mul(guest.base.bits(-2.5),p[1])),add(p[2],p[2])))
        linear=add(mul(p[2],guest.base.bits(.5)),half)
        value=add(mul(add(mul(add(mul(cubic,fraction),quadratic),fraction),linear),fraction),p[1])
        store(payload+20+c*4,value)
    store(payload,0);store(payload+4,0);store(payload+48,guest.base.bits(30.));store(payload+52,guest.base.bits(30.));store(payload+44,0)
    enqueue(get(actor+792),7,payload)
    return guest.public(memory),calls


class PayloadOracle(guest.ProjectionOracle):
    def __init__(self,words,memory,args,helpers,phase=0,retail=False,front=False,literal=False):
        self.trace=[];self.array_top=STACK+phase-(44 if retail or front else 16);self.literal=literal
        guest.base.PointProjectionOracle.__init__(self,words,memory,args,[],phase,source.ENTRY,helpers)

    def get_double(self,index):
        if index%2:raise ValueError('Odd FR=0 source pair')
        return from_double((self.f[index+1]<<32)|self.f[index])

    def set_double(self,index,value):
        if index%2:raise ValueError('Odd FR=0 destination pair')
        bits=double(value);self.f[index]=bits&0xFFFFFFFF;self.f[index+1]=bits>>32

    def execute(self,word):
        op,fmt,ft,fs,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        if op==17 and fmt==16 and fn==33:self.set_double(fd,guest.base.floating(self.f[fs]))
        elif op==17 and fmt==17 and fn==2:self.set_double(fd,self.get_double(fs)*self.get_double(ft))
        elif op==17 and fmt==17 and fn==32:self.f[fd]=guest.base.bits(self.get_double(fs))
        else:super().execute(word)

    def normalized_point(self,address):
        matches=[('channel',c,(address-(self.array_top-c*16))//4) for c in range(6)
            if 0<=address-(self.array_top-c*16)<16 and address%4==0]
        if len(matches)!=1:raise ValueError('Output pointer is not in the pinned array homes')
        return matches[0]

    def record_call(self,target):
        if target==POSITION:
            node,x,y,z=self.arguments(4)
            self.calls.append((target,(node,x,y,z) if self.literal else (node,*[self.normalized_point(a) for a in (x,y,z)])))
        elif target==SELECTOR:self.calls.append((target,self.arguments(4)))
        elif target==ENQUEUE:self.calls.append((target,self.arguments(3)))
        elif target==SPLINE:
            ptr,index,fraction=self.arguments(3)
            values=tuple(read(self.memory,ptr+i*4) for i in range(4))
            self.calls.append((target,(ptr,values,index,fraction) if self.literal else (values,index,fraction)))
        elif target in (SIN,COS):self.calls.append((target,(self.f[12],)))
        else:raise ValueError('Unexpected spline payload call '+hex(target))

    def hook(self,target):
        if target not in (SIN,COS):raise ValueError('All four leaf helpers must execute their real instructions')
        arg=guest.base.floating(self.f[12]);value=guest.base.bits((math.sin if target==SIN else math.cos)(arg))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=value


def cases():
    for initialized,valid,fraction,frames,heading in itertools.product((0,1,128),range(1,5),
            (-1.,-.0,.25,.999,1.,1.5,2.5),(0,1,8),(-179.5,0.,12345.25)):
        yield dict(initialized=initialized,valid=valid,fraction=fraction,frames=frames,heading=heading)
    for stop,null,bank,cursor in itertools.product((1,-1,0x80000000),(False,True),(0,19,255),(0,19)):
        yield dict(stop=stop,null=null,bank=bank,cursor=cursor)
    for mode in range(256):yield dict(initialized=0,mode=mode)
    yield dict(initialized=0,count=258,late=True)
    for frames in (-2147483648,-1,0,1,8,2147483647):yield dict(frames=frames)
    for valid,fraction in itertools.product((2,4),(.25,1.5)):yield dict(valid=valid,fraction=fraction,alias=1)
    for limit,stop in itertools.product((-32768,-1,0,1,258),(0,1)):yield dict(null=True,count=limit,stop=stop)


class SplinePayloadRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.measure(cls.root,cls.out);source.checked(cls.obj)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>305I',cls.rom,source.ROM))
        elf=(cls.root/'conker/build/conker.us.elf').read_bytes()
        cls.helpers={}
        for entry,count in HELPERS.items():
            at=source.prior.prior.elf_slot_offset(elf,entry,count*4)
            if elf[at:at+count*4]!=cls.rom[entry-0x14FD2B50:entry-0x14FD2B50+count*4]:
                raise ValueError('Installed spline payload helper differs from retail')
            cls.helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,elf,at)))

    def receipt(self,name,**values):(self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,**kw):
        initial,args=fixture(**kw);expected=reference(initial,args);machines=[]
        for retail,words in ((False,self.words),(True,self.truth)):
            m=PayloadOracle(words,initial,args,self.helpers,retail=retail).run()
            self.assertEqual((guest.public(m.memory),m.calls),expected,kw);machines.append(m)
        return machines

    def test_01_complete_modes_real_helpers_and_six_channel_outputs(self):
        count=traces=full_memories=0
        for kw in cases():
            a,b=self.compare(**kw);traces+=a.trace==b.trace;full_memories+=a.memory==b.memory;count+=1
        self.assertEqual(count,1069)
        self.receipt('guest',paired_cases=count,actual_helpers=4,helper_words=sum(HELPERS.values()),
            installed_helper_spans_equal_retail=True,complete_public_memory_and_normalized_calls=True,
            complete_memories_equal=full_memories,public_traces_equal=traces,trig_providers_opaque=True)

    def test_02_stop_queue_alias_and_captured_object_channel(self):
        for stop,bank in itertools.product((1,-1),(0,1)):
            self.compare(stop=stop,bank=bank,alias=2)

    def test_03_FR0_double_subset_and_negative_pair_controls(self):
        memory,args=fixture();m=PayloadOracle(self.words,memory,args,self.helpers)
        m.f[8]=guest.base.bits(12345.25)
        m.execute((17<<26)|(16<<21)|(8<<11)|(4<<6)|33)
        self.assertEqual(m.get_double(4),12345.25);m.set_double(22,.01745)
        m.execute((17<<26)|(17<<21)|(22<<16)|(4<<11)|(6<<6)|2)
        self.assertEqual(m.get_double(6),12345.25*.01745)
        m.execute((17<<26)|(17<<21)|(6<<11)|(20<<6)|32)
        self.assertEqual(m.f[20],guest.base.bits(12345.25*.01745))
        with self.assertRaises(ValueError):m.get_double(5)
        with self.assertRaises(ValueError):m.set_double(3,0.)
        self.assertEqual((m.f[22],m.f[23]),(double(.01745)&0xFFFFFFFF,double(.01745)>>32))
        for valid,count in ((0,8),(4,0)):
            memory,args=fixture(valid=valid,count=count)
            with self.assertRaisesRegex(ValueError,'Leading undefined|Undefined source array'):reference(memory,args)

    def test_04_primary_neighbors_pools_and_input_controls(self):
        values=source.freeze(self.root,self.out)
        old,diag=source.prior.prior.compile_profile(self.root,self.out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
        self.assertEqual(diag,'');self.assertEqual(source.prior.same_functions(old,self.obj,(source.FUNCTION,)),72)
        self.assertEqual(normalized_pools(old),normalized_pools(self.obj))
        original=Path.read_bytes
        for path in source.INPUTS:
            target=self.root/path
            def changed(p):return original(p)+b'\0' if p==target else original(p)
            with patch.object(Path,'read_bytes',changed),self.assertRaisesRegex(ValueError,'Changed spline payload input'):
                source.freeze(self.root,self.out)
        with (self.root/'conker/retail_layout.us.txt').open() as stream:rows=list(csv.DictReader(stream))
        opcode=(3<<26)|((source.ENTRY>>2)&0x3FFFFFF);sites=[]
        for row in rows:
            if row['section']!='game':continue
            start,end=int(row['address'],0),int(row['end'],0)
            for at in range(start,end,4):
                if struct.unpack_from('>I',self.rom,at-0x14FD2B50)[0]==opcode:sites.append((row['function'],at))
        self.assertEqual(sites,[('func_15087CC0',0x15087D6C),('func_15087CC0',0x15087D8C)])
        for _,at in sites:self.assertEqual(struct.unpack_from('>I',self.rom,at+8-0x14FD2B50)[0],0x3C02800D)
        self.assertEqual([struct.unpack_from('>I',self.rom,at+4-0x14FD2B50)[0] for _,at in sites],
            [0x00003025,0x24060001])
        self.receipt('caller-interface',direct_sites=sites,third_arguments=[0,1],V0_overwritten_after_each=True,
            private_typed_caller_all72_neighbors_unchanged=True,unknown_indirect_callers_not_qualified=True)

    def test_05_every_source_word_and_binding_is_pinned(self):
        text,functions,bindings=source.parse_object(self.obj);f=functions[source.FUNCTION];total=0
        for i in range(302):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,bindings)),self.assertRaises(ValueError):source.checked(self.obj)
            total+=1
        for at in source.BINDINGS:
            bad=dict(bindings);bad.pop(f['value']+at)
            with patch.object(source,'parse_object',return_value=(text,functions,bad)),self.assertRaises(ValueError):source.checked(self.obj)
            total+=1
        self.assertEqual(total,335)

    def test_06_production_baseline_remains_unmodified(self):
        source.freeze(self.root,self.out)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(302,288,289))
        self.assertFalse(self.row['production_installed']);self.assertEqual(self.row['matching_credit'],0)
        initial,args=fixture(null=True)
        for cut in (0,1):
            machines=[]
            for retail,words in ((False,self.words),(True,self.truth)):
                m=PayloadOracle(words,initial,args,self.helpers,retail=retail);m.access_fault=cut
                with self.assertRaises(guest.base.faults.AccessBoundary):m.run()
                self.assertEqual(m.all_accesses,cut);machines.append(m)
            a,b=machines
            self.assertEqual(b.r[29]-a.r[29],40)
            if cut:self.assertNotEqual(a.memory,b.memory)
        self.receipt('frame-boundary',fired_private_access_prefixes=2,raw_SP_displacement=40,
            raw_fault_parity=False,no_frame_guards_or_installation=True)

    def test_07_effective_compiled_C_controls(self):
        body=source.SELECTED
        controls={
            'wrong-stop-command':(body.replace('), 10, payload);','), 9, payload);'),dict(stop=1)),
            'signed-channel':(body.replace('(void *)(u32)object[0x23D]','(void *)(s32)(s8)object[0x23D]'),dict(stop=1,bank=255)),
            'wrong-phase-decrement':(body.replace('phase - 1.0f','phase - 2.0f'),dict(fraction=2.5,frames=0)),
            'float-angle-scale':(body.replace('(f32)((f64)*(f32 *)(actor + 0x40) * angleScale)',
                '*(f32 *)(actor + 0x40) * (f32)angleScale'),dict(valid=1,heading=.625)),
            'reload-object-channel':(body.replace('object[0x23D]','(*(u8 **)(actor + 0x318))[0x23D]'),dict(stop=1,alias=2)),
        }
        receipts=[]
        for label,(changed,kw) in controls.items():
            self.assertNotEqual(changed,body)
            obj,words,row=source.measure(self.root,self.out,'negative-'+label,changed)
            initial,args=fixture(**kw);m=PayloadOracle(words,initial,args,self.helpers).run()
            self.assertNotEqual((guest.public(m.memory),m.calls),reference(initial,args),label)
            receipts.append(dict(label=label,words=row['words'],frame=row['frame'],ordinary_semantic_mismatch=True))
        self.receipt('C-controls',effective_controls=len(receipts),controls=receipts)

    def test_08_shape_only_screens_are_not_promoted(self):
        labels=[*source.forms(),*source.refinements(),*source.compact_forms(),*source.scope_forms()]
        rows=[]
        for label in labels:
            row=json.loads((self.out/(label+'.json')).read_text())
            text,functions,bindings=source.parse_object(self.out/(label+'.o'));f=functions[source.FUNCTION]
            import hashlib
            self.assertEqual(hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),row['raw_sha256'])
            self.assertGreater(row['differences'],0);self.assertFalse(row['production_installed'])
            raw=struct.unpack('>%dI'%(f['size']//4),text[f['value']:f['value']+f['size']])
            saved_pairs=sum(word>>26==61 for word in raw)
            if row['frame']==248:self.assertEqual(saved_pairs,2)
            rows.append(dict(label=label,words=row['words'],frame=row['frame'],differences=row['differences'],saved_FP_pairs=saved_pairs))
        self.assertEqual(len(rows),30)
        self.receipt('rejected-screens',screens=rows,all_rejected=True,semantic_equivalence_not_claimed=True)

    def test_09_front_declarations_recover_literal_array_homes_not_frame(self):
        body=source.front_floats(source.SELECTED)
        obj,words,row=source.measure(self.root,self.out,'front-qualified',body);source.checked(obj,True)
        self.assertEqual((row['words'],row['frame'],row['differences']),(302,288,289))
        values=source.freeze(self.root,self.out)
        before,diag=source.prior.prior.compile_profile(self.root,self.out,values['conker/src/game/generated_B3020.c'].decode(),'front-before')
        self.assertEqual(diag,'');self.assertEqual(source.prior.same_functions(before,obj,(source.FUNCTION,)),72)
        self.assertEqual(normalized_pools(before),normalized_pools(obj))
        text,functions,_=source.parse_object(obj);f=functions[source.FUNCTION]
        raw=struct.unpack('>302I',text[f['value']:f['value']+f['size']]);frame=(-raw[0])&65535
        homes={w>>16&31:(w&65535)-frame for w in raw if w>>26==9 and w>>21&31==29 and w>>16&31 in range(16,22)}
        self.assertEqual(homes,{17:-44,18:-60,19:-76,20:-92,21:-108,16:-124})
        total=traces=full=0
        for kw in cases():
            initial,args=fixture(**kw);expected,_=reference(initial,args)
            a,b=[PayloadOracle(w,initial,args,self.helpers,retail=retail,front=True,literal=True).run()
                for retail,w in ((False,words),(True,self.truth))]
            self.assertEqual(guest.public(a.memory),expected)
            self.assertEqual((guest.public(a.memory),a.calls),(guest.public(b.memory),b.calls))
            for offset in homes.values():
                self.assertEqual(bytes(a.memory[STACK+offset+i] for i in range(16)),bytes(b.memory[STACK+offset+i] for i in range(16)))
            traces+=a.trace==b.trace;full+=a.memory==b.memory;total+=1
        self.assertEqual((total,traces,full),(1069,1069,0))
        self.receipt('front-homes',cases=total,public_traces_equal=traces,literal_private_call_addresses_equal=True,
            all96_array_bytes_equal=True,complete_memories_equal=full,frame=288,retail_frame=248,
            homes_relative_to_entry_SP=homes,matching_credit=0,installed=False)


if __name__=='__main__':unittest.main()
