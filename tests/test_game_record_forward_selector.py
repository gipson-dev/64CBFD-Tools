"""Forward projection selection, ordered output aliases and retained-ASM caller."""
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_forward_selector as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests.test_game_record_heading_setter import SetterOracle
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
RECORDS,OTHER,OUTPUT=0x30000,0x60000,0x20000
HEADER='#include <ultra64.h>\nextern u8 *D_800872A0;\nextern s8 D_800D2398;\nextern u8 D_800CC2D0[];\n'


def signed(v,width=32):return ((v&((1<<width)-1))^(1<<(width-1)))-(1<<(width-1))
def addr(v):return v&0xFFFFFFFF
def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x400}


def fixture(count=3,index=0,direction=0,pattern=0,active=True,alias=0,
        table=source.TABLE,count_address=source.COUNT,actors=source.ACTORS,limit=source.LIMIT):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x400)}
    for a,n in ((table,4),(count_address,4),(limit,4),(OUTPUT,16)):
        memory.update({a+i:0xA5 for i in range(n)})
    for bank in (RECORDS,OTHER):
        memory.update({bank+i:0xA5 for i in range(128*0x84)})
        for i in range(128):
            row=bank+i*0x84
            put(memory,row,base.bits(float(100+i)) if bank==RECORDS else OTHER)
            put(memory,row+0xC,base.bits(1.));put(memory,row+0x10,base.bits(0.5))
            put(memory,row+0x2F,0 if pattern!=6 else (128 if i==index or i%2 else 129),1)
            put(memory,row+0x31,(i+(1 if bank==OTHER else 0))%16,1)
    for i in range(-128,128):
        actor=addr(actors+i*0x32C)
        x,z=-float(20-i%16),float(i%3)
        if pattern==1 and i in (1,2):x,z=-4.,0.
        elif pattern==2:x,z=abs(x),abs(z)
        elif pattern==3:x,z=(-0. if i==1 else 0.),0.
        elif pattern==4:x,z=-10000.,0.
        elif pattern==5 and i in (1,2):x,z=(float('nan') if i==1 else -float('inf')),0.
        put(memory,actor+0x14,base.bits(x));put(memory,actor+0x1C,base.bits(z))
        put(memory,actor+0x124,(i+1)&255,1)
    own=RECORDS+index*0x84;own_id=index%16;origin=addr(actors+own_id*0x32C)
    put(memory,origin+0x14,0);put(memory,origin+0x1C,0)
    if pattern==7:put(memory,origin+0x124,2,1)
    elif pattern==8:
        put(memory,origin+0x124,0,1);put(memory,RECORDS+0x84+0x31,255,1)
    elif pattern==9:
        put(memory,own+0xC,base.bits(0.5));put(memory,own+0x10,base.bits(-2.))
        put(memory,origin+0x14,base.bits(2.));put(memory,origin+0x1C,base.bits(-3.))
    put(memory,table,RECORDS if active else 0);put(memory,count_address,count,1);put(memory,limit,base.bits(10000.))
    out_value,out_tag=OUTPUT,OUTPUT+4
    if alias==1:out_tag=out_value
    elif alias==2:
        out_value=RECORDS+0x84+0x2C;put(memory,RECORDS+0x84,0x3F800080)
    elif alias==3:
        out_tag=RECORDS+0x84+0x30;put(memory,RECORDS+0x84+0x2F,128,1)
    elif alias==4:
        out_value=count_address;put(memory,RECORDS+0x84,0)
    elif alias==5:
        out_value=table;put(memory,RECORDS+0x84,OTHER)
    elif alias==6:out_value=origin+0x14
    elif alias==7:out_tag=count_address
    elif alias==8:
        out_value=RECORDS+2*0x84+0x30;put(memory,RECORDS+0x84,0x000F0000)
    return memory,(index,direction&0xFFFFFFFF,out_value,out_tag)


def reference(initial,args,table=source.TABLE,count_address=source.COUNT,actors=source.ACTORS,limit=source.LIMIT):
    memory=dict(initial);trace=[]
    def get(a,n=4):
        a=addr(a);v=read(memory,a,n);trace.append(('R',a,n,v));return v
    def store(a,v):
        a=addr(a);trace.append(('W',a,4,v&0xFFFFFFFF));put(memory,a,v)
    bank=get(table)
    if bank==0:return memory,0,trace
    own=addr(bank+args[0]*0x84);actor=addr(actors+signed(get(own+0x31,1),8)*0x32C)
    sign=base.bits(-1. if signed(args[1])>=0 else 1.)
    x=base.mul(get(own+0xC),sign);z=base.mul(get(own+0x10),sign)
    count=signed(get(count_address,1),8);tag=signed(get(own+0x2F,1),8)
    ax,az=get(actor+0x14),get(actor+0x1C);excluded=signed(get(actor+0x124,1)-1,8)
    bias=base.add(base.mul(x,ax),base.mul(z,az))^0x80000000
    minimum=get(limit);selected=0;i=0
    while i<count:
        row=addr(get(table)+i*0x84);candidate=signed(get(row+0x31,1),8);i+=1
        if candidate==excluded:continue
        if tag and signed(get(row+0x2F,1),8)!=tag:continue
        actor=addr(actors+candidate*0x32C);ax,az=get(actor+0x14),get(actor+0x1C)
        distance=base.add(base.add(base.mul(x,ax),base.mul(z,az)),bias)
        if 0.<base.floating(distance)<base.floating(minimum):
            value=get(row);minimum=distance;store(args[2],value)
            store(args[3],signed(get(row+0x2F,1),8))
            candidate=signed(get(row+0x31,1),8);count=signed(get(count_address,1),8)
            selected=addr(actors+candidate*0x32C)
    return memory,selected,trace


class ForwardOracle(SetterOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None):
        self.trace=[];self.setter_reads=[];self.setter_writes=[];self.forwarded=[]
        base.PointProjectionOracle.__init__(self,words,memory,args,[],phase,entry,connected)

    def execute(self,word):
        if word>>26==17 and (word>>21)&31==16 and word&63==7:
            self.f[(word>>6)&31]=self.f[(word>>11)&31]^0x80000000;return
        return super().execute(word)

    def get(self,a,n):
        v=super().get(a,n)
        if self.own_instruction and not STACK-0x400<=a<STACK+0x400:self.trace.append(('R',a,n,v))
        return v

    def put(self,a,v,n):
        super().put(a,v,n)
        if self.own_instruction and not STACK-0x400<=a<STACK+0x400:self.trace.append(('W',a,n,v&((1<<(n*8))-1)))

    def record_call(self,target):
        if target!=source.ENTRY:raise AssertionError('Unexpected forward selector call')
        self.forwarded.append(self.arguments(4))

    def hook(self,target):raise AssertionError('Forward selector has no opaque helpers')


def controls():
    b=source.SELECTED
    return {
        'unsigned-count':b.replace('i < D_800D2398','i < (u8)D_800D2398'),
        'wrong-direction':b.replace('direction >= 0','direction > 0'),
        'include-excluded':b.replace('*(s8 *)(record + 0x31) != excluded','1'),
        'ignore-tag':b.replace('(direction == 0 || *(s8 *)(record + 0x2F) == direction)','1'),
        'wrong-stride':b.replace('i * 0x84','i * 0x80'),
        'include-zero':b.replace('0.0f < distance','0.0f <= distance'),
        'last-tie':b.replace('distance < minimum','distance <= minimum'),
        'wrong-normal':b.replace('record + 0x10','record + 0x0C'),
        'cached-id':b.replace('    s8 excluded;','    s8 excluded;\n    s8 candidateId;').replace(
            '                minimum = distance;', '                candidateId = *(s8 *)(record + 0x31);\n                minimum = distance;').replace(
            'selected = D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C;', 'selected = D_800CC2D0 + candidateId * 0x32C;'),
        'swapped-stores':b.replace('                *outValue = *(f32 *)record;\n                *outTag = *(s8 *)(record + 0x2F);',
            '                *outTag = *(s8 *)(record + 0x2F);\n                *outValue = *(f32 *)record;'),
        'cached-count':b.replace('    s32 i;','    s32 i;\n    s32 count = D_800D2398;').replace('i < D_800D2398','i < count'),
        'cached-table':b.replace('record = D_800872A0 + i * 0x84;', 'record = table + i * 0x84;'),
    }


NATIVE=HEADER+r'''
typedef struct {f32 value;u8 pad4[8];f32 x,z;u8 pad14[27];s8 tag;u8 pad30;s8 id;u8 tail[82];} Record;
typedef struct {u8 pad0[20];f32 x;u8 pad18[4];f32 z;u8 pad20[260];u8 slot;u8 tail[519];} Actor;
static Record records[128];Actor actors[16] __asm__("D_800CC2D0");
static u8 recordBefore[sizeof(records)],actorBefore[sizeof(actors)];
u8 *D_800872A0;s8 D_800D2398;f32 D_8009DA00=10000.0f;
struct Case {u32 count,index,direction,pattern,active,actor,value,tag;};
static const struct Case cases[]={ROWS};
static f32 real(u32 b){union{u32 u;f32 f;}v;v.u=b;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
u8 *func_150883B0(s32,s32,f32*,s32*);
static int check(const struct Case*c){u32 i,j,own=c->index%16;f32 value=real(0xA5A5A5A5u);s32 tag=(s32)0xA5A5A5A5u;u8*got;
 for(i=0;i<sizeof(records);i++)((u8*)records)[i]=0xA5;
 for(i=0;i<sizeof(actors);i++)((u8*)actors)[i]=0xA5;
 for(i=0;i<128;i++){records[i].value=(f32)(100+i);records[i].x=1.0f;records[i].z=0.5f;
 records[i].tag=c->pattern==6?(i==c->index||i%2?(s8)-128:(s8)-127):0;records[i].id=(s8)(i%16);}
 for(i=0;i<16;i++){f32 x=-(f32)(20-i),z=(f32)(i%3);
 if(c->pattern==1&&(i==1||i==2)){x=-4.0f;z=0.0f;}
 else if(c->pattern==2)x=-x;
 else if(c->pattern==3){x=i==1?-0.0f:0.0f;z=0.0f;}
 else if(c->pattern==4){x=-10000.0f;z=0.0f;}
 else if(c->pattern==5&&(i==1||i==2)){x=real(i==1?0x7FC00000u:0xFF800000u);z=0.0f;}
 actors[i].x=x;actors[i].z=z;actors[i].slot=(u8)(i+1);}
 actors[own].x=actors[own].z=0.0f;
 if(c->pattern==7)actors[own].slot=2;
 else if(c->pattern==9){records[c->index].x=0.5f;records[c->index].z=-2.0f;actors[own].x=2.0f;actors[own].z=-3.0f;}
 D_800872A0=c->active?(u8*)records:0;*(u8*)&D_800D2398=(u8)c->count;
 for(i=0;i<sizeof(records);i++)recordBefore[i]=((u8*)records)[i];
 for(i=0;i<sizeof(actors);i++)actorBefore[i]=((u8*)actors)[i];
 got=func_150883B0((s32)c->index,(s32)c->direction,&value,&tag);
 if(got!=(c->actor==0xFFFFFFFFu?0:(u8*)&actors[c->actor])||word(value)!=c->value||(u32)tag!=c->tag)return 23;
 if(D_800872A0!=(c->active?(u8*)records:0)||(u8)D_800D2398!=c->count||D_8009DA00!=10000.0f)return 23;
 for(i=0;i<sizeof(records);i++)if(recordBefore[i]!=((u8*)records)[i])return 23;
 for(j=0;j<sizeof(actors);j++)if(actorBefore[j]!=((u8*)actors)[j])return 23;return 0;}
static int run(void){u32 i;int status;
 if(sizeof(void*)!=4||sizeof(Record)!=0x84||sizeof(Actor)!=0x32C||__builtin_offsetof(Record,tag)!=0x2F||
 __builtin_offsetof(Record,id)!=0x31||__builtin_offsetof(Actor,slot)!=0x124)return 29;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){status=check(cases+i);if(status)return status;}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


def native_rows():
    for n,index,direction,p,active in itertools.chain(
            itertools.product(range(256),(0,3),(-1,0,1),(0,1,6),(True,)),
            itertools.product((0,3,16,127,128),(0,3,127),(-2147483648,-1,0,2147483647),(2,3,4,5,7,9),(False,True))):
        memory,args=fixture(n,index,direction,p,active);expected,selected,_=reference(memory,args)
        yield (n,index,direction&0xFFFFFFFF,p,int(active),
            (selected-source.ACTORS)//0x32C if selected else 0xFFFFFFFF,read(expected,OUTPUT),read(expected,OUTPUT+4))


class ForwardSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD;cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=struct.unpack_from('>107I',cls.rom,source.ROM)
        cls.fixed=source.normalized(cls.words)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase=0,bodies=None,entry=source.ENTRY,anchors=()):
        expected,result,trace=reference(memory,args,*anchors);models=[]
        for words in (bodies or (self.words,self.fixed,self.truth)):
            m=ForwardOracle(words,memory,args,phase,entry).run()
            self.assertEqual((public(m.memory),m.r[2],m.trace),(public(expected),result,trace))
            self.assertEqual(m.f[20:],m.saved_f);self.assertFalse(m.calls)
            for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            models.append(m)
        self.assertEqual((models[1].r,models[1].f),(models[2].r,models[2].f));return models

    def test_01_guest_signed_scans_outputs_aliases_and_complete_slot(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(107,32,37,72))
        self.assertEqual(self.fixed,list(self.truth));seen=set();count=0
        for n,d in itertools.product(range(256),(-1,0)):
            memory,args=fixture(n,direction=d);models=self.compare(memory,args);seen.update(models[0].visits);count+=1
        for index,d,p,active,phase in itertools.product((0,3,127),(-2147483648,0,2147483647),range(10),(False,True),(0,8)):
            memory,args=fixture(3,index,d,p,active);models=self.compare(memory,args,phase);seen.update(models[0].visits);count+=1
        for alias,n,d,phase in itertools.product(range(1,9),(2,3,16),(0,-1),(0,8)):
            memory,args=fixture(n,direction=d,alias=alias);self.compare(memory,args,phase);count+=1
        for own_id,candidate_id,slot,value in itertools.product((-128,-1,0,127),(-128,-1,127),(0,128,255),(0x80000000,0x7FC12345)):
            memory,args=fixture(2)
            origin=addr(source.ACTORS+own_id*0x32C);candidate=addr(source.ACTORS+candidate_id*0x32C)
            put(memory,RECORDS+0x31,own_id,1);put(memory,RECORDS+0x84+0x31,candidate_id,1)
            put(memory,candidate+0x14,base.bits(-2.));put(memory,candidate+0x1C,0)
            put(memory,origin+0x14,0);put(memory,origin+0x1C,0);put(memory,origin+0x124,slot,1)
            put(memory,RECORDS+0x84,value);self.compare(memory,args);count+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+428,4))<=seen)
        self.receipt('guest',three_way_cases=count,all256_count_bytes=True,all107_words=True,
            alias_patterns=8,signed_actor_ID_and_exclusion_wrap_boundaries=72,
            ordered_reads_and_writes=True,complete_public_memory=True,saved_F20_F21_F22_F23=True)

    def test_02_native32_O2_O0_UBSan_and_result_controls(self):
        rows=list(native_rows());driver=self.out/'native-driver.c'
        driver.write_text(NATIVE.replace('ROWS',','.join('{'+','.join('0x%Xu'%v for v in row)+'}' for row in rows)))
        native_controls={n:b for n,b in controls().items() if n not in ('cached-id','swapped-stores','cached-count','cached-table')}
        # A deliberately wrong stride is guest-only: it leaves the typed native Record domain.
        native_controls.pop('wrong-stride')
        native_controls.pop('include-excluded')
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in native_controls.items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            c=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(driver),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            self.assertEqual(subprocess.run([str(exe)],timeout=180,capture_output=True).returncode,status,name)
        self.receipt('native',cases_per_profile=len(rows),UBSan=True,controls=len(native_controls),
            valid_typed_nonalias_objects_only=True,no_negative_actor_ID_native_claim=True,no_FCSR_claim=True)

    def test_03_guest_controls_change_results_not_only_private_scratch(self):
        seeds=[fixture(3,index=i,direction=d,pattern=p,alias=a) for i,d,p,a in
            itertools.chain(itertools.product((0,3),(-1,0),range(10),(0,)),itertools.product((0,),(0,), (0,),range(1,9)))]
        seeds+=[fixture(128,index=127)]
        for name,body in controls().items():
            # Removing a predicate may leave an intentionally dead local in this control.
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name)
            self.assertFalse(diagnostics)
            data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            for memory,args in seeds:
                expected,result,_=reference(memory,args)
                try:m=ForwardOracle(words,memory,args).run()
                except (KeyError,AssertionError):continue
                if (public(m.memory),m.r[2])!=(public(expected),result):break
            else:self.fail('Ineffective forward selector control: '+name)
        self.receipt('controls',observable_guest_controls=len(controls()),crash_only_not_accepted=True)

    def test_04_independent_original_raw_padded_relocations(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-forward',source.raw_text(self.root/'conker/asm/B3020.s'),source.FUNCTION)
        raws=[]
        for obj in (self.obj,self.padded):
            text,functions,rel=source.parse_object(obj);f=functions[source.FUNCTION]
            raws.append((text[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}))
        count=0
        for k,(entry,table,cnt,actors,limit) in enumerate(((source.ENTRY,source.TABLE,source.COUNT,source.ACTORS,source.LIMIT),
                (0x16218004,0x12347FFC,0x800D8004,0x80508004,0x80097FFC),
                (0x18FFF000,0x12348004,0x800D7FFC,0x80507FFC,0x80098004))):
            anchors=dict(D_800872A0=table,D_800D2398=cnt,D_800CC2D0=actors,D_8009DA00=limit);objects=[original]
            for label,(raw,bindings) in zip(('raw','padded'),raws):
                text,missing=emit_function(raw,dict(value=0,size=len(raw)),bindings,source.FUNCTION,anchors);self.assertFalse(missing)
                path=self.out/('rebase-%s-%d.s'%(label,k));path.write_text(text);obj=path.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True);objects.append(obj)
            bodies=[]
            for j,obj in enumerate(objects):
                script=self.out/('rebase-%d-%d.ld'%(k,j));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>107I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[2]);self.assertEqual(source.normalized(bodies[1]),bodies[0])
            for n,p,a,phase in itertools.product((0,3,128),(0,6,8),(0,2,3,4,5),(0,8)):
                memory,args=fixture(n,pattern=p,alias=a,table=table,count_address=cnt,actors=actors,limit=limit)
                # compare expects raw, padded, original order for full normalized state.
                self.compare(memory,args,phase,(bodies[1],bodies[2],bodies[0]),entry,(table,cnt,actors,limit));count+=1
        self.receipt('rebases',independent_original_raw_padded_links=9,three_way_cases=count,ten_bindings=True)

    def test_05_access_fault_prefixes(self):
        count=0
        for n,a,phase in itertools.product((0,3,128),(0,2,3,4,5),(0,8)):
            memory,args=fixture(n,alias=a);full=ForwardOracle(self.fixed,memory,args,phase).run()
            for fault in range(full.all_accesses):
                models=[]
                for words in (self.words,self.fixed,self.truth):
                    m=ForwardOracle(words,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual((models[0].memory,models[0].trace),(models[2].memory,models[2].trace))
                self.assertEqual(base.state(models[1]),base.state(models[2]));count+=1
        self.receipt('faults',states=30,public_fault_prefixes=count,full_normalized_retail_state=True,
            raw_dead_registers_not_claimed=True,no_hardware_fault_or_FCSR_emulation=True)

    def test_06_retained_assembly_caller_window(self):
        old=source.raw_read(self.out/'before-01');entry=0x150539E0;stop=0x15053A0C
        slot=source.elf_slot_offset(old,0x150538CC,4108)
        self.assertEqual(old[slot:slot+4108],self.rom[0x80D7C:0x81D88])
        self.assertIn('#pragma GLOBAL_ASM("asm/nonmatchings/game_77AD0/func_150538CC.s")',source.raw_text(self.root/'conker/src/game_77AD0.c'))
        caller=struct.unpack_from('>11I',self.rom,entry-0x14FD2B50)
        self.assertEqual(caller[:6],(0x8FA400DC,0x8FA500C0,0x27A600C4,0x27A700BC,0x0D4220EC,0xE7B000CC))
        count=0
        for n,d,p,phase in itertools.product((0,3,128),(-1,0),(0,6,8),(0,8)):
            memory,args=fixture(n,direction=d,pattern=p);sp=STACK+phase
            args=(*args[:2],sp+0xC4,sp+0xBC);expected,result,_=reference(memory,args)
            put(memory,sp+0xDC,args[0]);put(memory,sp+0xC0,args[1]);origin=0x90000
            for words in (self.words,self.fixed):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+428,4),words))
                # Stop after the real post-call BEQ's ADDIU delay, without executing other parent branches.
                connected[stop]=0x8FBF00F0;connected[stop+4]=0x03E00008;connected[stop+8]=0
                m=ForwardOracle(caller,memory,args,phase,entry,connected);m.r[16]=origin
                m.r[4:8]=[0x12345678]*4;m.f[16]=0x3F123456
                put(m.memory,origin+0x124,1,1);put(m.memory,sp+0xF0,m.r[31]);m.before[16]=origin
                m.run();self.assertEqual(m.forwarded,[args]);self.assertEqual((m.r[2],m.r[3]),(result,result))
                self.assertEqual((read(m.memory,sp+0xC4),read(m.memory,sp+0xBC)),(read(expected,sp+0xC4),read(expected,sp+0xBC)))
                self.assertEqual((m.f[16],m.r[13]),(0x3F123456,addr(result+0x32C)))
            count+=1
        self.receipt('caller',paired_bounded_windows=count,whole_parent_slot_retail_exact=True,
            actual_four_arguments_and_F16_delay_save_reload=True,return_consumed=True,full_parent_execution_not_claimed=True)

    def test_07_fail_closed_inputs_words_bindings_guards_and_installation(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION];raw,bindings=source.checked_object(self.obj)
        for i in range(107):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        reader=csv.DictReader(io.StringIO(source.raw_read(self.out/'qualified-guards.csv').decode()));all_rows=list(reader)
        for row in source.owner_guards(raw,bindings):
            path=self.out/'bad-guard.csv';wrong=[dict(r,expected='0x%08X'%(int(r['expected'],16)^1))
                if (r['filename'],r['function'],r['offset'])==(row['filename'],row['function'],row['offset']) else r for r in all_rows]
            with path.open('w',newline='') as stream:
                w=csv.DictWriter(stream,fieldnames=reader.fieldnames);w.writeheader();w.writerows(wrong)
            with self.assertRaisesRegex(ValueError,source.FUNCTION):
                source.emit_padded_assembly(self.obj,self.root/'conker/asm/B3020.s',filename=source.OWNER,word_patches_path=path)
        with source.historical_view(self.root,self.out):
            read_bytes=Path.read_bytes
            for index,p in enumerate(source.INPUTS):
                for path in (self.root/p,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda x:read_bytes(x)+b'\n' if x==path else read_bytes(x)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':unittest.main()
