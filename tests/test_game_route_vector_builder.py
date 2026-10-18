"""Qualify vector semantics without accepting the remaining private-frame mismatch."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_vector_builder as source
from tools.tests import game_view_point_projection_oracle as base
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command
from tools.pad_generated_object import emit_padded_assembly

put,read,STACK=base.put,base.read,base.STACK
GLOBAL,RECORD,TABLE,OTHER,OUTPUT=0x800D2350,0x50000,0x30000,0x3F000000,0x20000
HEADER='#include <ultra64.h>\nextern u8 *D_800D2350;\n'
SPEEDS=(0,0x80000000,1,0x80000001,0x00800000,0x3E800000,0x3F000000,0x3F800000,
    0xBF000000,0x40000000,0xC0200000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
COORDS=(-32768,32767,0,-1,1,12345,-23456)


def signed(v):return ((v&65535)^32768)-32768
def public(m):return {a:v for a,v in m.items() if not STACK-0x400<=a<STACK+0x400}


def fixture(mask=0,pattern=242,coordinate=0,speed=0x3F000000,alias=0,global_address=GLOBAL):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x400)}
    for at,length in ((RECORD,132),(OUTPUT,96),(global_address,20),(TABLE,4096),(OTHER,4096)):
        m.update({at+i:0xA5 for i in range(length)})
    for bank in (TABLE,OTHER):
        for i in range(256):
            for axis in range(3):
                value=COORDS[(i+coordinate+axis*2)%len(COORDS)]
                if bank==OTHER:value=signed(value+7)
                put(m,bank+i*16+axis*2,value,2)
            for j in range(5):put(m,bank+i*16+9+j,5+j if (pattern//3**j)%3 else 255,1)
            put(m,bank+i*16+14,0,1);put(m,bank+i*16+15,0,1)
        for j in range(5):put(m,bank+(5+j)*16+14,4 if (pattern//3**j)%3==2 else 1,1)
    for i in range(4):put(m,RECORD+0x2B+i,255 if mask>>i&1 else i,1)
    put(m,RECORD,speed);put(m,global_address,TABLE)
    outputs=[OUTPUT,OUTPUT+32,OUTPUT+64]
    if alias==1:outputs=[OUTPUT]*3
    elif alias==2:outputs=[OUTPUT,OUTPUT+4,OUTPUT+8]
    elif alias in (3,4,5):outputs[alias-3]=RECORD
    elif alias==6:outputs[0]=TABLE
    elif alias==7:outputs[0]=TABLE+4
    elif alias==8:outputs[1]=TABLE+4
    elif alias==9:
        outputs[0]=global_address;put(m,RECORD,base.bits(.5));put(m,TABLE,0,2);put(m,TABLE+5*16,1,2)
        put(m,TABLE+9,5,1);put(m,TABLE+5*16+14,4,1);put(m,RECORD+0x2B,0,1)
    elif alias==10:outputs[0]=RECORD+0x28
    return m,(RECORD,*outputs)


def reference(initial,args,global_address=GLOBAL):
    m=dict(initial);trace=[];record,x,y,z=args
    def get(at,n=4):
        value=read(m,at,n);trace.append(('R',at,n,value));return value
    def store(at,value):
        put(m,at,value);trace.append(('W',at,4,value&0xFFFFFFFF))
    for slot in range(4):
        node=get(record+0x2B+slot,1)
        if node==255:
            store(x,base.bits(float(slot*64)));store(y,0);store(z,0)
        else:
            table=get(global_address);route=table+node*16;other=route
            for j in range(5):
                candidate=get(route+9+j,1)
                if candidate!=255 and get(table+candidate*16+14,1)==4:other=table+candidate*16;break
            current_x=signed(get(route,2));next_x=signed(get(other,2));speed=get(record)
            next_z=signed(get(other+4,2));old_z=signed(get(route+4,2))
            delta_x=base.bits(float(next_x-current_x));delta_z=base.bits(float(next_z-old_z))
            store(x,base.add(base.bits(float(current_x)),base.mul(delta_x,speed)))
            store(y,base.bits(float(signed(get(route+2,2)))))
            fresh_z=signed(get(route+4,2));fresh_speed=get(record)
            store(z,base.add(base.bits(float(fresh_z)),base.mul(delta_z,fresh_speed)))
        x+=4;y+=4;z+=4
    return m,trace


class VectorOracle(base.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,public_fault=None,connected=None):
        self.trace=[];self.public_accesses=0;self.public_fault=public_fault;self.forwarded=[]
        super().__init__(words,memory,args,[],phase,entry,connected)

    def observe(self,at):
        if self.own_instruction and not STACK-0x400<=at<STACK+0x400:
            if self.public_accesses==self.public_fault:raise base.faults.AccessBoundary
            self.public_accesses+=1;return True
        return False

    def get(self,at,n):
        observed=self.observe(at);value=super().get(at,n)
        if observed:self.trace.append(('R',at,n,value))
        return value

    def put(self,at,value,n):
        observed=self.observe(at);super().put(at,value,n)
        if observed:self.trace.append(('W',at,n,value&((1<<(n*8))-1)))

    def record_call(self,target):
        if target==source.ENTRY:self.forwarded.append(self.arguments(4));return
        raise AssertionError('Vector builder must not call helpers')

    def hook(self,target):raise AssertionError('No vector helpers may be opaque')


def corpus():
    for mask,pattern,speed in itertools.product(range(16),range(243),(0x3F000000,0xBF000000)):
        yield (mask,pattern,0,speed,0)
    for mask,pattern,coordinate,speed in itertools.product((0,5,15),(0,2,18,242),range(7),SPEEDS):
        yield (mask,pattern,coordinate,speed,0)
    for alias,mask,pattern,speed in itertools.product(range(1,11),(0,5),(2,242),(0x3F000000,0x3F800000)):
        yield (mask,pattern,0,speed,alias)


def controls():
    b=source.SELECTED
    cached=b.replace('    f32 deltaZ;','    f32 freshZ;\n    f32 deltaZ;').replace(
        '            *x =','            freshZ = (f32)*(s16 *)(route + 4);\n            *x =',1).replace(
        '*z = (f32)*(s16 *)(route + 4) +','*z = freshZ +')
    y=b.replace('    f32 deltaZ;','    f32 freshY;\n    f32 deltaZ;').replace(
        '            *x =','            freshY = (f32)*(s16 *)(route + 2);\n            *x =',1).replace(
        '*y = (f32)*(s16 *)(route + 2);','*y = freshY;')
    table=b.replace('    u8 *table;','    u8 *table = D_800D2350;').replace('            table = D_800D2350;\n','')
    return {
        'last-type-four':b.replace('                    i = 5;\n',''),
        'scan-four':b.replace('i < 5','i < 4'),
        'wrong-type':b.replace('0xE] == 4','0xE] == 3'),
        'wrong-sentinel':b.replace('id != 0xFF','id != 0xFE'),
        'unsigned-coordinate':b.replace('*(s16 *)','*(u16 *)'),
        'narrow-delta':b.replace('(f32)(nextX - currentX)','(f32)(s16)(nextX - currentX)'),
        'wrong-y':b.replace('*y = (f32)*(s16 *)(route + 2);','*y = (f32)*(s16 *)(route + 4);'),
        'wrong-fallback':b.replace('slot * 64','slot * 32'),
        'wrong-output-stride':b.replace('        x++;','        x += 2;'),
        'cached-speed':b.replace('deltaZ * *(f32 *)record','deltaZ * speed'),
        'cached-y':y,'cached-z':cached,'cached-table':table,
    }


def native_case(p):
    memory,args=fixture(*p);expected,_=reference(memory,args)
    arrays=(p,[read(expected,OUTPUT+i*4) for i in range(24)],
        [read(expected,RECORD+i*4) for i in range(4)])
    return '{'+','.join('{'+','.join('0x%Xu'%(v&0xFFFFFFFF) for v in row)+'}' for row in arrays)+'}'


NATIVE=HEADER+r'''
typedef struct {s16 xyz[3];u8 reserved[3],neighbors[5],type,kind;} Route;
typedef union {f32 f[33];u8 bytes[132];} Record;
struct Case {u32 in[5],out[24],record[4];};
static const struct Case cases[]={ROWS};
static const s32 coordinates[]={-32768,32767,0,-1,1,12345,-23456};
static Route routes[256],beforeRoutes[256];static Record record,expectedRecord;static f32 out[24];
u8 *D_800D2350;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=0xA5;}
static int equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
void func_15088F30(u8*,f32*,f32*,f32*);
static int run(void){u32 n,i,j,k,category,alias;const u32*p;f32*x,*y,*z;s32 a,b;
 if(sizeof(void*)!=4||sizeof(Route)!=16||sizeof(Record)!=132)return 29;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){p=cases[n].in;
 fill(routes,sizeof(routes));fill(&record,sizeof(record));fill(out,sizeof(out));
 for(i=0;i<256;i++){for(j=0;j<3;j++)routes[i].xyz[j]=(s16)coordinates[(i+p[2]+j*2)%7];
 for(j=0,k=1;j<5;j++,k*=3){category=(p[1]/k)%3;routes[i].neighbors[j]=(u8)(category?5+j:255);}
 routes[i].type=routes[i].kind=0;}
 for(j=0,k=1;j<5;j++,k*=3)routes[5+j].type=(u8)(((p[1]/k)%3)==2?4:1);
 for(i=0;i<4;i++)record.bytes[0x2B+i]=(u8)((p[0]>>i)&1?255:i);
 record.f[0]=real(p[3]);expectedRecord=record;
 for(i=0;i<4;i++)expectedRecord.f[i]=real(cases[n].record[i]);
 for(i=0;i<sizeof(routes);i++)((u8*)beforeRoutes)[i]=((u8*)routes)[i];
 D_800D2350=(u8*)routes;x=out;y=out+8;z=out+16;alias=p[4];
 if(alias==1)y=z=x;else if(alias==2){y=out+1;z=out+2;}
 else if(alias==3)x=record.f;else if(alias==4)y=record.f;else if(alias==5)z=record.f;
 func_15088F30(record.bytes,x,y,z);
 for(i=0;i<24;i++)if(!same(word(out[i]),cases[n].out[i]))return 23;
 for(i=0;i<4;i++)if(!same(word(record.f[i]),word(expectedRecord.f[i])))return 23;
 if(!equal(record.bytes+16,expectedRecord.bytes+16,116)||!equal(routes,beforeRoutes,sizeof(routes))||D_800D2350!=(u8*)routes)return 23;
 }
 for(i=0;i<65536;i++){a=(s16)i;b=(s16)(i^65535u);fill(routes,sizeof(routes));fill(&record,sizeof(record));
 for(j=0;j<5;j++)routes[0].neighbors[j]=255;
 routes[0].xyz[0]=routes[0].xyz[1]=routes[0].xyz[2]=(s16)a;
 routes[5].xyz[0]=routes[5].xyz[2]=(s16)b;routes[5].type=4;routes[0].neighbors[0]=5;
 for(j=0;j<4;j++)record.bytes[0x2B+j]=0;record.f[0]=.5f;D_800D2350=(u8*)routes;
 func_15088F30(record.bytes,out,out+8,out+16);
 for(j=0;j<4;j++)if(out[j]!=-.5f||out[8+j]!=(f32)a||out[16+j]!=-.5f)return 23;
 }return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''


class RouteVectorBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.qualify_model(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=struct.unpack_from('>83I',cls.rom,source.ROM)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase=0,bodies=None,entry=source.ENTRY,global_address=GLOBAL):
        expected,trace=reference(memory,args,global_address);models=[]
        for words in bodies or (self.words,self.truth):
            m=VectorOracle(words,memory,args,phase,entry).run()
            self.assertEqual((public(m.memory),m.trace),(public(expected),trace));self.assertEqual(m.calls,[])
            self.assertEqual(m.f[20:],m.saved_f)
            for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            models.append(m)
        return models

    def test_01_semantic_model_and_retail_public_results_and_access_order(self):
        count=0;raw_seen=set();retail_seen=set()
        for p in corpus():
            memory,args=fixture(*p);models=self.compare(memory,args,(count&1)*8)
            raw_seen.update(models[0].visits);retail_seen.update(models[1].visits);count+=1
        for node in (0,127,128,254,255):
            memory,args=fixture()
            for j in range(4):put(memory,RECORD+0x2B+j,node,1)
            self.compare(memory,args);count+=1
        self.receipt('guest-model',paired_cases=count,exact_public_memory_and_trace=True,
            raw_words_visited=len(raw_seen),retail_words_visited=len(retail_seen),
            raw_unvisited=[i for i in range(83) if source.ENTRY+i*4 not in raw_seen],
            retail_unvisited=[i for i in range(83) if source.ENTRY+i*4 not in retail_seen],
            all243_neighbor_categories_all16_FF_masks=True,guest_aliases=10,
            hardware_FCSR_and_NaN_payload_not_claimed=True,matching_credit=0,installable=False)

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        cases=[p for p in corpus() if p[4]<=5]
        harness=self.out/'native-driver.c';harness.write_text(NATIVE.replace('ROWS',','.join(map(native_case,cases))))
        controls_native={n:b for n,b in controls().items() if n not in ('cached-y','cached-z','cached-table')}
        exits={}
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in controls_native.items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            c=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            exits[name]=subprocess.run([str(exe)],capture_output=True,timeout=120).returncode
            self.assertEqual(exits[name],status,name)
        self.receipt('native',cases_per_profile=len(cases)+65536,all65536_signed_coordinates=True,
            profiles=['O2','O0'],UBSan=True,valid_float_aliases=5,incompatible_short_pointer_aliases_excluded=True,
            NaN_class_not_payload=True,controls=len(controls_native),exits=exits,matching_credit=0)

    def test_03_guest_controls_change_public_memory(self):
        cases=[fixture(mask,pattern) for mask,pattern in itertools.product((0,5,15),range(243))]
        cases.extend(fixture(0,pattern,speed=speed,alias=alias) for alias,pattern,speed in
            itertools.product(range(1,11),(2,242),(0x3F000000,0x3F800000)))
        witnesses={}
        for name,body in controls().items():
            self.assertNotEqual(body,source.SELECTED)
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name);self.assertFalse(diagnostics)
            _,functions,bindings=source.parse_object(obj);f=functions[source.FUNCTION]
            symbols={symbol:int(symbol.split('_')[1],16) for entries in bindings.values() for _,symbol in entries
                if symbol.startswith('D_')}
            script=self.out/('negative-private-'+name+'.ld');elf=script.with_suffix('.elf')
            script.write_text('SECTIONS { .text 0x15200000 : { *(.text) } .rodata ALIGN(16) : { *(.rodata*) } }\n')
            subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            linked=sections(elf);words=struct.unpack_from('>%dI'%(f['size']//4),linked['.text'][1],f['value'])
            for case,(memory,args) in enumerate(cases):
                expected,_=reference(memory,args);initial=dict(memory)
                for section,(address,data) in linked.items():
                    if section.startswith(('.rodata','.data','.sdata','.lit')):initial.update({address+i:v for i,v in enumerate(data)})
                m=VectorOracle(words,initial,args,entry=0x15200000).run()
                if {a:v for a,v in public(m.memory).items() if a in memory}!=public(expected):
                    witnesses[name]=case;break
            else:self.fail('Ineffective vector control: '+name)
        self.receipt('controls',public_memory_witnesses=witnesses,guest_controls=len(witnesses),private_offsets_not_used=True)

    def test_04_public_fault_prefixes_and_private_stack_rejection(self):
        cases=count=0
        for alias,mask in itertools.product(range(11),(0,15)):
            memory,args=fixture(mask,alias=alias);full=VectorOracle(self.truth,memory,args).run()
            for fault in range(full.public_accesses):
                models=[]
                for words in (self.words,self.truth):
                    m=VectorOracle(words,memory,args,public_fault=fault)
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual((public(models[0].memory),models[0].trace),(public(models[1].memory),models[1].trace));count+=1
            cases+=1
        source.require_retail_stack_contract(self.truth)
        with self.assertRaisesRegex(ValueError,'not installable'):source.require_retail_stack_contract(self.words)
        memory,args=fixture();machines=[]
        for words in (self.words,self.truth):
            m=VectorOracle(words,memory,args);m.access_fault=1
            with self.assertRaises(base.faults.AccessBoundary):m.run()
            machines.append(m)
        self.assertNotEqual(machines[0].memory,machines[1].memory)
        self.assertEqual(read(machines[0].memory,STACK-4),machines[0].before[18])
        self.assertEqual(read(machines[1].memory,STACK-4),machines[1].before[17])
        self.receipt('faults',fixtures=cases,equal_public_fault_prefixes=count,
            first_private_store_raw='S2 at entry-SP-4',first_private_store_retail='S1 at entry-SP-4',
            private_fault_state_differs=True,retail_stack_gate_rejects_raw=True,installable=False,matching_credit=0)

    def test_05_actual_padder_and_independent_rebases(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-vectors',
            source.raw_text(self.root/'conker/asm/B3020.s'),source.FUNCTION)
        script=self.out/'model-padded.s'
        script.write_text(emit_padded_assembly(self.obj,self.root/'conker/asm/B3020.s',filename=source.OWNER,
            word_patches_path=self.root/'conker/retail_word_patches.us.csv'))
        padded=script.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
        raw,bindings=source.checked_model(self.obj);text,functions,rel=source.parse_object(padded);f=functions[source.FUNCTION]
        self.assertEqual(text[f['value']:f['value']+f['size']],raw)
        self.assertEqual({at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']},bindings)
        count=0
        for placement,(entry,global_address) in enumerate(((source.ENTRY,GLOBAL),(0x16218004,0x23457FFC),(0x18FFF000,0x23458004))):
            bodies=[];anchors={'D_800D2350':global_address}
            for label,obj in (('original',original),('raw',self.obj),('padded',padded)):
                if label!='original':
                    text,functions,rel=source.parse_object(obj);f=functions[source.FUNCTION]
                    emitted,missing=emit_function(text,f,rel,source.FUNCTION,anchors);self.assertFalse(missing)
                    path=self.out/('rebase-%s-%d.s'%(label,placement));path.write_text(emitted);obj=path.with_suffix('.o')
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True)
                ld=self.out/('rebase-%s-%d.ld'%(label,placement));elf=ld.with_suffix('.elf')
                ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',source.FUNCTION,'--defsym=D_800D2350=0x%X'%global_address,
                    '-o',str(elf),str(obj)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>83I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[1],bodies[2]);self.assertNotEqual(bodies[0],bodies[1])
            for alias,mask,phase in itertools.product(range(11),(0,5,15),(0,8)):
                memory,args=fixture(mask,alias=alias,global_address=global_address)
                self.compare(memory,args,phase,(bodies[1],bodies[2],bodies[0]),entry,global_address);count+=1
        self.receipt('rebases',links=9,three_way_cases=count,global_carry_boundaries=True,
            actual_padder_preserves_raw_model=True,padded_still_nonmatching=True,production_guards_unchanged=True)

    def test_06_live_C_parent_interface_and_connected_model(self):
        from tools.tests import test_game_actor_route_snap as parent
        owner=source.raw_read(self.out/'before-00').decode()
        candidate=source.recovered_owner(owner);before,after=(source.function_span(v,'func_15088D58') for v in (owner,candidate))
        self.assertNotEqual(owner[slice(*before)],candidate[slice(*after)])
        old_text,old_functions,old_rel=source.parse_object(self.out/'owner-before.o')
        new_text,new_functions,new_rel=source.parse_object(self.obj)
        name='func_15088D58';a,b=old_functions[name],new_functions[name]
        self.assertEqual(old_text[a['value']:a['value']+a['size']],new_text[b['value']:b['value']+b['size']])
        bindings=lambda r,f:{at-f['value']:v for at,v in r.items() if f['value']<=at<f['value']+f['size']}
        self.assertEqual(bindings(old_rel,a),bindings(new_rel,b));self.assertEqual((b['size'],len(bindings(new_rel,b))),(472,14))
        self.assertIn('extern void func_15088F30(u8 *, f32 *, f32 *, f32 *);',candidate)
        helpers={}
        for entry,count in parent.HELPERS.items():
            helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,self.rom,entry-0x14FD2B50)))
        parent_words=struct.unpack_from('>118I',self.rom,parent.source.ROM);count=0
        for actor,steps,mode,angle,alias,phase in itertools.product((0,3),(0,2,7),(0,128),(0,0x8000,0xFFFF),(0,1),(0,8)):
            p=(actor,steps,-1,mode,angle,0x43360B61,0);memory,args=parent.fixture(p,alias);expected,calls=parent.reference(memory,args,angle)
            for vectors in (self.words,self.truth):
                connected=dict(helpers);connected.update(zip(range(source.ENTRY,source.ENTRY+332,4),vectors))
                m=parent.RouteOracle(parent_words,memory,args,angle,connected,phase).run()
                self.assertEqual((public(m.memory),m.calls),(public(expected),calls))
                self.assertEqual(m.f[20:],m.saved_f)
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            count+=1
        self.receipt('caller',paired_complete_parent_cases=count,parent_words=118,parent_bindings=14,
            typed_prototype_does_not_change_parent_object=True,connected_helper_words=555,
            only_atan_is_bounded_provider=True,production_vector_and_splines_still_stubs=True,gameplay_not_claimed=True)

    def test_07_words_bindings_inputs_and_stack_gate_fail_closed(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION]
        raw,bindings=source.checked_model(self.obj)
        for i in range(83):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_model(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_model(self.obj)
        for index,p in enumerate(source.INPUTS):
            for path in (self.root/p,self.out/('before-%02d'%index)):
                with patch.object(Path,'read_bytes',lambda x:source.raw_read(x)+b'\n' if x==path else source.raw_read(x)):
                    with self.assertRaises(ValueError):source.freeze(self.root,self.out)
        for i in (0,1,2):
            bad=list(self.truth);bad[i]^=0x10000
            with self.assertRaises(ValueError):source.require_retail_stack_contract(bad)
        source.freeze(self.root,self.out)
        self.receipt('fail-closed',raw_words=83,relative_bindings=2,live_and_snapshot_inputs=26,
            stack_mutations=3,physical_baseline_unchanged=True,no_production_installation=True)


if __name__=='__main__':unittest.main()
