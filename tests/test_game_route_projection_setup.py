"""Whole projection semantics with real selector/enqueue instructions, no provider stubs."""
import itertools
import json
import math
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_projection_setup as source
from tools.tests import game_view_point_projection_oracle as base
from tools.tests import test_game_route_neighbor_preference as selector

put,read,STACK=base.put,base.read,base.STACK
RECORD,ACTOR,OBJECT,TABLE,QUEUES=0x80000,0x50000,0x60000,0x30000,0x70000
FLAGS,MODE,LIMIT,QUEUE_GLOBAL=0x8008FDBC,0x800D23A8,0x8009DA08,0x800DC2B0
HELPERS={0x1508907C:91,0x1512D560:41}


def div(a,b):
    x,y=base.floating(a),base.floating(b)
    return base.bits(x/y if y else math.nan if not x else math.copysign(math.inf,x*math.copysign(1.,y)))


def fixture(state=3,position=0,mode=0,flag=0,cursor=0,alias=0,count=3,null=0):
    record=RECORD
    if alias in (1,2,3,4,5):record=ACTOR-(0x54,0x4C,0x38,0x34,0x58)[alias-1]
    elif alias==6:record=TABLE-0x4A
    elif alias==7:record=selector.GLOBAL+3-0x4A
    queue=ACTOR+0x318 if alias==8 else ACTOR+0x314 if alias==9 else QUEUES
    if any(STACK-0x400<=at<STACK+0x500 for at in (record,ACTOR,OBJECT,TABLE,queue)):
        raise ValueError('A public projection fixture overlaps the private exclusion window')
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x500)}
    for at,n in ((record,0x400),(ACTOR-0x100,0x600),(OBJECT,0x300),(TABLE-0x100,0x1200),
            (QUEUES-0x100,0x1000),(5,0x300)):
        memory.update({at+i:0xA5 for i in range(n)})
    for at,n in ((FLAGS,2),(MODE,1),(LIMIT,4),(QUEUE_GLOBAL,4),(selector.COUNT,2),(selector.GLOBAL,8)):
        memory.update({at+i:0xA5 for i in range(n)})
    for i in range(256):
        for axis in range(3):put(memory,TABLE+i*16+axis*2,(i*37+axis*19)%511-255,2)
        for j in range(5):put(memory,TABLE+i*16+9+j,255,1)
        put(memory,TABLE+i*16+14,4,1);put(memory,TABLE+i*16+15,0,1)
    points=((0,0,0),(100,20,0),(0,-20,100))
    for i in range(3):
        for axis,v in enumerate(points[i]):put(memory,TABLE+i*16+axis*2,v,2)
        put(memory,TABLE+i*16+9,(i+1)%3,1);put(memory,TABLE+i*16+10,(i+2)%3,1)
        put(memory,TABLE+i*16+15,2 if i==0 else 3,1)
    put(memory,TABLE+14,5,1)
    coordinates=((10.,5.,10.),(99.,20.,0.),(0.,-20.,100.),(1000.,1000.,1000.),
        (-32768.,32767.,-32768.),(0.,0.,0.),(-0.,-0.,-0.),(25000.,30.,-30000.))
    for axis,v in enumerate(coordinates[position]):put(memory,ACTOR+0x14+axis*4,base.bits(v))
    put(memory,ACTOR+0x318,0 if null else OBJECT);put(memory,OBJECT+0x23D,0,1);put(memory,5+0x23D,0,1)
    put(memory,record+0x30,state,1);put(memory,record+0x4A,0,1);put(memory,record+0x4B,255 if state==2 and count<3 else 1,1)
    if state==2 and 0<count<3:put(memory,TABLE+14,4,1)
    put(memory,FLAGS,flag,2);put(memory,MODE,mode,1);put(memory,LIMIT,base.bits(1e9))
    put(memory,selector.COUNT,count,2);put(memory,selector.GLOBAL,TABLE);put(memory,QUEUE_GLOBAL,queue)
    put(memory,queue+0xAC,cursor)
    if alias==7:
        put(memory,record+0x30,3,1);put(memory,record+0x4B,16,1)
        put(memory,TABLE+16*16,100,2);put(memory,TABLE+16*16+2,0,2);put(memory,TABLE+16*16+4,0,2)
        put(memory,ACTOR+0x14,base.bits(99.));put(memory,ACTOR+0x18,base.bits(10.));put(memory,ACTOR+0x1C,0)
        put(memory,selector.COUNT,33,2)
    return memory,(record,ACTOR)


def branching_fixture():
    memory,args=fixture(3,1,flag=64)
    put(memory,TABLE+16+9,2,1);put(memory,TABLE+16+10,3,1)
    put(memory,TABLE+2*16+15,0,1);put(memory,TABLE+3*16+15,1,1)
    return memory,args


def controls():
    b=source.MODEL
    clamp='''        if (best > 1000.0f) {
            best = 1000.0f;
        }
'''
    cached=b.replace('    f32 targetZ;','    f32 targetZ;\n    f32 cachedX, cachedY, cachedZ;')
    marker='        payload = record + 0x4C;'
    head,tail=cached.split(marker,1)
    head+='''        cachedX = *(f32 *)(actor + 0x14);
        cachedY = *(f32 *)(actor + 0x18);
        cachedZ = *(f32 *)(actor + 0x1C);
'''+marker
    for axis,offset in zip('XYZ',('14','18','1C')):tail=tail.replace('*(f32 *)(actor + 0x'+offset+')','cached'+axis)
    fresh=b
    for offset in ('19C','1A4','1A0','1A8'):fresh=fresh.replace('(object + 0x'+offset+')','(*(u8 **)(actor + 0x318) + 0x'+offset+')')
    return {
        'wrong-preferred-bit':b.replace('D_8008FDBC & 0x40','D_8008FDBC & 0x20'),
        'wrong-root-type':b.replace('node[0xE] == 5','node[0xE] == 4'),
        'unsigned-coordinates':b.replace('(f32)*(s16 *)','(f32)*(u16 *)'),
        'clamp-before-normalize':b.replace(clamp,'').replace('        dx /= best;',clamp+'        dx /= best;'),
        'cached-payload-inputs':head+tail,
        'reload-entry-object':fresh,
        'reload-selected-table':b.replace('            previousNode = currentNode;',
            '            previousNode = D_800D2350 + current * 0x10;'),
        'missing-command-five':b.replace('            func_1512D560(*(u8 **)(actor + 0x318), 5, 0);\n',''),
        'wrong-command-seven':b.replace('), 7, payload);','), 6, payload);'),
    }


def reference(initial,args):
    memory=dict(initial);record,actor=args;calls=[];trace=[]
    def get(at,n=4):v=read(memory,at,n);trace.append(('R',at,n,v));return v
    def store(at,v,n=4):put(memory,at,v,n);trace.append(('W',at,n,v&((1<<(n*8))-1)))
    def node(table,i):return (table+i*16)&0xFFFFFFFF
    def neighbor(current,excluded,preferred):
        calls.append((0x1508907C,(current,255,excluded,preferred)))
        count=base.half(get(selector.COUNT,2));result=255
        if current<count:
            table=get(selector.GLOBAL);route=node(table,current)
            for j in range(5):
                c=get(route+9+j,1)
                if c==255 or c==excluded:continue
                selected=node(table,c)
                # The caller passes wildcard type, but the real selector still reads it.
                get(selected+14,1);result=c
                if get(selected+15,1)==preferred:break
        return result
    def enqueue(obj,command,payload):
        calls.append((0x1512D560,(obj,command,payload)))
        def queue():
            channel=get(obj+0x23D,1);base_address=get(QUEUE_GLOBAL);return (base_address+channel*0xB0)&0xFFFFFFFF
        q=queue();index=get(q+0xAC);store((q+(index<<3))&0xFFFFFFFF,command)
        q=queue();index=get(q+0xAC);store((q+(index<<3)+4)&0xFFFFFFFF,payload)
        q=queue();index=get(q+0xAC);store(q+0xAC,index+1)
        q=queue()
        if get(q+0xAC)==20:store(q+0xAC,0)
    def xz(n,actor_first=False):
        if actor_first:
            x=get(actor+0x14);nx=base.half(get(n,2));nz=base.half(get(n+4,2));z=get(actor+0x1C)
        else:
            nx=base.half(get(n,2));nz=base.half(get(n+4,2));x=get(actor+0x14);z=get(actor+0x1C)
        dx=base.sub(x,base.bits(float(nx)));dz=base.sub(z,base.bits(float(nz)))
        return dx,dz,base.add(base.mul(dx,dx),base.mul(dz,dz))
    object=get(actor+0x318)
    if not object:return memory,calls,trace
    preferred=1 if get(FLAGS,2)&64 else 0
    if ((get(record+0x30,1)^128)-128)==2:
        i=0;count=base.half(get(selector.COUNT,2))
        while i<count:
            root=node(get(selector.GLOBAL),i)
            if get(root+14,1)==5 and get(root+15,1)==2:
                store(record+0x4A,i,1);store(record+0x4B,i,1)
                for j in range(5):
                    candidate=get(root+9+j,1)
                    if candidate!=255:
                        mode=get(MODE,1);kind=get(node(get(selector.GLOBAL),candidate)+15,1)
                        if (mode==0)==(kind==3):store(record+0x4B,candidate,1)
                count=base.half(get(selector.COUNT,2));i=count
            i+=1
        current=get(record+0x4B,1);best=get(LIMIT);previous=get(record+0x4A,1);first=current
        for _ in range(260):
            root=node(get(selector.GLOBAL),current);next_id=neighbor(current,previous,preferred)
            dx,dz,distance=xz(root);previous,current=current,next_id
            if base.floating(distance)<base.floating(best):
                best=distance;store(record+0x4A,previous,1);store(record+0x4B,next_id,1)
            if first==current:break
        else:raise ValueError('Reference fixture does not contain a closing route cycle')
        enqueue(get(actor+0x318),5,0);store(record+0x30,3,1)
    current=get(record+0x4B,1);table=get(selector.GLOBAL);current_node=node(table,current)
    actor_x=get(actor+0x14);nx=base.half(get(current_node,2));nz=base.half(get(current_node+4,2));actor_z=get(actor+0x1C)
    previous=get(record+0x4A,1);previous_node=node(table,previous)
    dx=base.sub(actor_x,base.bits(float(nx)));dz=base.sub(actor_z,base.bits(float(nz)))
    current_distance=base.add(base.mul(dx,dx),base.mul(dz,dz))
    px=base.half(get(previous_node,2));pz=base.half(get(previous_node+4,2))
    dx=base.sub(actor_x,base.bits(float(px)));dz=base.sub(actor_z,base.bits(float(pz)))
    distance=base.add(base.mul(dx,dx),base.mul(dz,dz))
    if base.floating(current_distance)<base.floating(distance):
        store(record+0x4A,current,1);next_id=neighbor(current,previous,preferred)
        store(record+0x4B,next_id,1);previous_node=current_node
        dx,dz,_=xz(previous_node,True);distance=current_distance
    y=base.half(get(previous_node+2,2));dy=base.sub(get(actor+0x18),base.bits(float(y)))
    length=base.bits(math.sqrt(base.floating(base.add(base.mul(dy,dy),distance))))
    dx,dy,dz=(div(v,length) for v in (dx,dy,dz))
    if base.floating(length)>1000.:length=base.bits(1000.)
    payload=record+0x4C;store(payload,0)
    for axis in range(3):store(payload+0x20+axis*4,get(actor+0x14+axis*4))
    store(payload+0x14,base.sub(get(actor+0x14),base.mul(dx,length)))
    store(payload+0x18,base.sub(get(actor+0x18),base.mul(dy,length)))
    target_z=base.sub(get(actor+0x1C),base.mul(dz,length))
    store(payload+4,0);store(payload+0x30,base.bits(30.));store(payload+0x34,base.bits(30.))
    store(payload+0x2C,0);store(payload+0x1C,target_z)
    enqueue(get(actor+0x318),7,payload)
    for offset in (0x19C,0x1A4,0x1A0,0x1A8):store(object+offset,base.bits(30.))
    return memory,calls,trace


class ProjectionOracle(base.PointProjectionOracle):
    def __init__(self,words,memory,args,helpers,phase=0):
        self.trace=[]
        super().__init__(words,memory,args,[],phase,source.ENTRY,helpers)

    def get(self,at,n):
        v=super().get(at,n)
        if self.own_instruction and not STACK-0x400<=at<STACK+0x500:self.trace.append(('R',at,n,v))
        return v

    def put(self,at,v,n):
        super().put(at,v,n)
        if self.own_instruction and not STACK-0x400<=at<STACK+0x500:self.trace.append(('W',at,n,v&((1<<(n*8))-1)))

    def execute(self,word):
        if word>>26==32:
            old=self.own_instruction;self.own_instruction=True;self.dispatched_word=word
            try:
                rs,rt=word>>21&31,word>>16&31;offset=((word&65535)^32768)-32768
                self.r[rt]=((self.get((self.r[rs]+offset)&0xFFFFFFFF,1)^128)-128)&0xFFFFFFFF
                self.r[0]=0
            finally:self.own_instruction=old
        elif word>>26==17 and word>>21&31==16 and word&63==4:
            fs,fd=word>>11&31,word>>6&31
            self.f[fd]=base.bits(math.sqrt(base.floating(self.f[fs])))
        else:super().execute(word)

    def record_call(self,target):
        if target not in HELPERS:raise AssertionError('Unexpected projection helper')
        self.calls.append((target,self.arguments(4 if target==0x1508907C else 3)))

    def hook(self,target):raise AssertionError('Both projection helpers must execute actual instructions')


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x500}


class RouteProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.qualify_model(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=list(struct.unpack_from('>321I',cls.rom,source.ROM));cls.helpers={}
        for entry,count in HELPERS.items():cls.helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,cls.rom,entry-0x14FD2B50)))
        if struct.unpack_from('>I',cls.rom,0x2424C8)[0]!=base.bits(1e9):raise ValueError('Wrong retail route distance threshold')

    def test_01_complete_semantics_with_two_actual_helpers(self):
        count=0;trace_equal=0;retail_trace_equal=0;visits=[set(),set()]
        cases=list(itertools.product((2,3,0,128,255),range(8),(0,1,128),(0,64),(0,19)))
        for state,position,mode,flag,cursor in cases:
            memory,args=fixture(state,position,mode,flag,cursor);expected,calls,trace=reference(memory,args)
            for i,words in enumerate((self.words,self.truth)):
                m=ProjectionOracle(words,memory,args,self.helpers,(count&1)*8).run()
                self.assertEqual((public(m.memory),m.calls),(public(expected),calls),(state,position,mode,flag,cursor,i))
                self.assertEqual(m.f[20:],m.saved_f);visits[i].update(m.visits)
                if i==0:trace_equal+=m.trace==trace
                else:retail_trace_equal+=m.trace==trace
            count+=1
        self.assertEqual(retail_trace_equal,count)
        (self.out/'guest-model.json').write_text(json.dumps(dict(paired_cases=count,actual_helpers=2,
            connected_helper_words=132,public_memory_and_calls_equal=True,raw_public_read_traces_equal=trace_equal,
            retail_public_read_traces_equal=retail_trace_equal,visited=[len(v) for v in visits],
            root_words_visited=[sum(source.ENTRY<=pc<source.ENTRY+len(w)*4 for pc in v) for v,w in zip(visits,(self.words,self.truth))],
            installable=False,matching_credit=0),indent=2)+'\n')

    def test_02_guest_aliases_null_and_signed_count_boundaries(self):
        count=0
        cases=[fixture(3,position,alias=alias) for alias,position in itertools.product(range(1,8),range(8))]
        cases.extend(fixture(2,position,alias=8,cursor=0) for position in range(8))
        cases.extend(fixture(2,position,alias=9,cursor=19) for position in range(8))
        cases.extend(fixture(2,count=count) for count in (-32768,-1,0,1,2,3,255,256,32767))
        cases.extend(fixture(state,null=1) for state in (0,2,3,255))
        cases.append(branching_fixture())
        for mode in (0,1,128):
            memory,args=fixture(2,mode=mode)
            put(memory,TABLE+14,4,1);cases.append((dict(memory),args))
            put(memory,TABLE+14,5,1);put(memory,TABLE+15,1,1)
            put(memory,TABLE+2*16+14,5,1);put(memory,TABLE+2*16+15,2,1)
            cases.append((dict(memory),args))
            memory,args=fixture(2,mode=mode,count=300)
            put(memory,TABLE+14,4,1)
            for j,v in enumerate((1,2,255,255,255)):put(memory,TABLE+258*16+9+j,v,1)
            put(memory,TABLE+258*16+14,5,1);put(memory,TABLE+258*16+15,2,1)
            cases.append((memory,args))
        for memory,args in cases:
            expected,calls,_=reference(memory,args)
            for words in (self.words,self.truth):
                m=ProjectionOracle(words,memory,args,self.helpers,(count&1)*8).run()
                self.assertEqual((public(m.memory),m.calls),(public(expected),calls),(count,words is self.truth))
            count+=1
        (self.out/'guest-aliases.json').write_text(json.dumps(dict(paired_cases=count,guest_aliases=9,
            captured_entry_object_and_fresh_calls=True,private_frame_aliases_not_qualified=True,matching_credit=0),indent=2)+'\n')


    def test_03_effective_complete_C_controls(self):
        cases=[branching_fixture(),fixture(2,0),fixture(3,2),fixture(3,3)]
        cases.extend(fixture(3,3,alias=alias) for alias in range(1,8))
        cases.append(fixture(2,3,alias=9,cursor=19))
        witnesses={}
        for name,body in controls().items():
            self.assertNotEqual(body,source.MODEL,name)
            obj,words,row=source.measure(self.root,self.out,'negative-'+name,body,True)
            self.assertFalse(row['diagnostics'])
            for case,(memory,args) in enumerate(cases):
                expected,calls,_=reference(memory,args)
                model=ProjectionOracle(words,memory,args,self.helpers).run()
                if public(model.memory)!=public(expected):witnesses[name]=case;break
            else:self.fail('Ineffective projection control: '+name)
        (self.out/'controls.json').write_text(json.dumps(dict(guest_controls=len(witnesses),
            public_memory_wrong_result_witnesses=witnesses,crashes_not_used=True),indent=2)+'\n')

    def test_04_private_null_path_rejection_and_early_Z_witness(self):
        source.require_retail_contract(self.truth)
        with self.assertRaisesRegex(ValueError,'not installable'):source.require_retail_contract(self.words)
        for phase in (0,8):
            memory,args=fixture(null=1)
            a,b=[ProjectionOracle(w,memory,args,self.helpers,phase).run() for w in (self.words,self.truth)]
            self.assertEqual(public(a.memory),public(b.memory));self.assertNotEqual(a.memory,b.memory)
            self.assertEqual(read(a.memory,STACK+phase-4),0)
            self.assertEqual(read(b.memory,STACK+phase-4),read(memory,STACK+phase-4))
        at=next(i for i,w in enumerate(self.words) if w==0xAE400050)
        self.assertEqual(self.words[at-1],0xC6A8001C)
        bad=list(self.words);bad[at-1],bad[at]=bad[at],bad[at-1]
        memory,args=fixture(3,3,alias=4);expected,_,_=reference(memory,args)
        a=ProjectionOracle(self.words,memory,args,self.helpers).run();b=ProjectionOracle(bad,memory,args,self.helpers).run()
        self.assertEqual(public(a.memory),public(expected));self.assertNotEqual(public(b.memory),public(expected))
        (self.out/'private-boundary.json').write_text(json.dumps(dict(frame=120,raw_words=307,retail_words=321,
            null_private_word_raw='zero at entry-SP-4',null_private_word_retail='untouched',
            early_Z_load_store_control_effective=True,installable=False,matching_credit=0),indent=2)+'\n')

    def test_05_all_raw_words_bindings_and_frozen_inputs_fail_closed(self):
        self.assertEqual(public({RECORD:1,RECORD+0x4B:2}),{RECORD:1,RECORD+0x4B:2})
        raw,bindings=source.checked_model(self.obj);text,functions,rel=source.neighbor.parse_object(self.obj)
        f=functions[source.FUNCTION]
        for at in range(f['value'],f['value']+f['size'],4):
            bad=bytearray(text);bad[at]^=1
            with patch.object(source.neighbor,'parse_object',return_value=(bytes(bad),functions,rel)),self.assertRaises(ValueError):source.checked_model(self.obj)
        for at in (at for at in rel if f['value']<=at<f['value']+f['size']):
            bad=dict(rel);bad.pop(at)
            with patch.object(source.neighbor,'parse_object',return_value=(text,functions,bad)),self.assertRaises(ValueError):source.checked_model(self.obj)
        checks=0
        for index,name in enumerate(source.INPUTS):
            for target in (self.root/name,self.out/('before-%02d'%index)):
                def corrupt(path,*args,**kwargs):
                    data=source.raw_read(path,*args,**kwargs);return data+b'\0' if path==target else data
                with patch.object(Path,'read_bytes',corrupt),self.assertRaises(ValueError):source.freeze(self.root,self.out)
                checks+=1
        self.assertEqual(checks,30);source.freeze(self.root,self.out)
        (self.out/'input-audit.json').write_text(json.dumps(dict(raw_word_corruptions=307,
            missing_bindings=18,input_corruptions=checks),indent=2)+'\n')


    def test_06_local_LB_sqrt_and_access_gate_controls(self):
        address=0x90000
        for value in (0,1,127,128,255):
            memory={address:value}
            m=ProjectionOracle([0x80820000,0x03E00008,0],memory,(address,0),{}).run()
            self.assertEqual(m.r[2],((value^128)-128)&0xFFFFFFFF)
            self.assertEqual(m.trace,[('R',address,1,value)])
            m=ProjectionOracle([0x80820000,0x03E00008,0],memory,(address,0),{});m.access_fault=0
            with self.assertRaises(base.faults.AccessBoundary):m.run()
            self.assertEqual(m.trace,[]);self.assertEqual(m.dispatched_word,0x80820000)
        for value in (0,0x80000000,base.bits(2.),base.bits(4.),0x7F800000,0x7FC12345):
            memory={};put(memory,address,value)
            m=ProjectionOracle([0xC4800000,0x46000084,0x03E00008,0],memory,(address,0),{}).run()
            self.assertEqual(m.f[2],base.bits(math.sqrt(base.floating(value))))
            self.assertEqual(m.trace,[('R',address,4,value)])
        (self.out/'oracle-controls.json').write_text(json.dumps(dict(signed_byte_values=5,
            fired_first_access_fault_controls=5,sqrt_values=6,shared_runner_unchanged=True),indent=2)+'\n')


if __name__=='__main__':unittest.main()
