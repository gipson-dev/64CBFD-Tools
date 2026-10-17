"""Exact point-update emission, O32 stack, provider effects and truncation."""
from functools import lru_cache
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_halfword_point_update as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.check_game_data_layout import audit_layout

STACK,RECORD,OWNER,OTHER,DEST,SECOND=point.STACK,0x20000,0x22000,0x23000,0x24000,0x25000
ROTATE,TRANSFORM=source.SYMBOLS.values()
COS,SIN,SCALE=0x150AD780,0x150AD78C,0x8009F6C0
VALUES=(0.75,-0.75,32767.75,32768.75,65535.75,-65536.75,2147483520.,-2147483648.)


def fixture(pattern=0,alias=0,phase=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x180)}
    for base in (RECORD,OWNER,OTHER,DEST,SECOND,0x30000,0x110000,0x120000):
        memory.update({base+i:0xA5 for i in range(128)})
    put(memory,RECORD+0x18,OWNER)
    destination=(DEST,RECORD+6,OWNER+0x2A,STACK+phase-26)[alias]
    put(memory,RECORD+0x14,destination)
    for base,offset in ((OWNER,0),(OTHER,1)):
        for at,value in ((0x20,(pattern-3)*.25),(0x28,(pattern+1)*-.5),
                (0x38,17.75+offset),(0x3C,-23.5-offset),(0x40,31.25+offset)):
            put(memory,base+at,point.bits(value))
    put(memory,SCALE,point.bits(.25))
    return memory


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x180}


def rotation_effect(memory,mode):
    if mode==1:put(memory,RECORD+0x18,OTHER)
    if mode==2:
        for at,value in ((0x38,-3.25),(0x3C,5.75),(0x40,-7.5)):put(memory,OWNER+at,point.bits(value))


def matrix_values(pattern):
    return [point.bits(1. if i in (0,5,10,15) else .25 if i in (4,6) and pattern&1 else 0.) for i in range(16)]


def outputs(pattern):return tuple(point.bits(3.75 if i==0 else VALUES[(pattern+i)%len(VALUES)]) for i in range(3))


def transformed(memory,matrix):
    return tuple(point.add(point.add(point.mul(read(memory,matrix+axis*4),0),
        point.mul(read(memory,matrix+(axis+4)*4),point.bits(-495.))),
        point.add(point.mul(read(memory,matrix+(axis+8)*4),0),read(memory,matrix+(axis+12)*4))) for axis in range(3))


def reference(initial,pattern=0,mode=0,phase=0,actual=False,symbols=None):
    s=symbols or source.SYMBOLS;memory=dict(initial);matrix=STACK+phase-80;out=STACK+phase-16
    owner=read(memory,RECORD+0x18)
    calls=[(s['func_150A8050'],(matrix,point.mul(read(memory,owner+0x20),point.bits(3.)),0,
        point.mul(read(memory,owner+0x28),point.bits(3.))))]
    for i,value in enumerate(matrix_values(pattern)):put(memory,matrix+i*4,value)
    rotation_effect(memory,mode)
    for i,at in enumerate((0x38,0x3C,0x40)):
        put(memory,matrix+48+i*4,read(memory,read(memory,RECORD+0x18)+at))
    calls.append((s['func_150A7960'],(matrix,0,point.bits(-495.),0,out,out+4,out+8)))
    for i,value in enumerate(transformed(memory,matrix) if actual else outputs(pattern)):put(memory,out+i*4,value)
    if mode==3:put(memory,RECORD+0x14,SECOND)
    for i in range(3):
        value=math.trunc(point.floating(read(memory,out+i*4)))
        assert -2147483648<=value<2147483648
        put(memory,read(memory,RECORD+0x14)+0x0E+i*2,value&65535,2)
    return memory,calls


class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,pattern=0,mode=0,phase=0,entry=source.ENTRY,connected=None,symbols=None):
        self.io=[];self.targets=symbols or source.SYMBOLS;self.pattern=pattern;self.effect_mode=mode
        super().__init__(words,memory,(RECORD,),[],phase,entry,connected)
        self.pattern=pattern

    def execute(self,word):
        op,rs,rd,fd,fn=word>>26,word>>21&31,word>>11&31,word>>6&31,word&63
        if op==17 and rs==16 and fn in (7,13):
            if fn==7:self.f[fd]=self.f[rd]^0x80000000
            else:
                value=math.trunc(point.floating(self.f[rd]));assert -2147483648<=value<2147483648
                self.f[fd]=value&0xffffffff
            self.dispatched_word=word
        else:super().execute(word)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def args(self,count):
        return tuple(self.r[4+i] if i<4 else read(self.memory,self.r[29]+i*4) for i in range(count))

    def record_call(self,target):
        if target in (COS,SIN):args=(self.f[12],)
        else:args=self.args(4 if target==self.targets['func_150A8050'] else 7)
        self.calls.append((target,args));self.observations.append((target,tuple(self.r[16:24]),self.r[29]))

    def hook(self,target):
        result=None
        if target==self.targets['func_150A8050']:
            matrix=self.r[4]
            for i,value in enumerate(matrix_values(self.pattern)):put(self.memory,matrix+i*4,value)
            rotation_effect(self.memory,self.effect_mode)
        elif target==self.targets['func_150A7960']:
            args=self.args(7)
            for address,value in zip(args[4:],outputs(self.pattern)):put(self.memory,address,value)
            if self.effect_mode==3:put(self.memory,RECORD+0x14,SECOND)
        elif target in (COS,SIN):
            # Exact dyadic provider values isolate the real assembly's matrix math.
            result=point.bits(.5 if target==COS else -.25)
        else:raise AssertionError('Unexpected point-update provider '+hex(target))
        # DAC30's overlapping trig leaves do not spill to the argument homes.
        if target not in (COS,SIN):
            for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        if result is not None:self.f[0]=result


def state(m):return point.state(m),m.condition,m.io


class HalfwordPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>64I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-halfword-point',
            (cls.out/'before-phase_original').read_text(),source.FUNCTION)
        cls.point_code={TRANSFORM+i*4:w for i,w in enumerate(struct.unpack_from('>40I',cls.rom,0xD4E10))}
        cls.rotation_code={ROTATE+i*4:w for i,w in enumerate(struct.unpack_from('>83I',cls.rom,0xD5500))}

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,pattern=0,mode=0,alias=0,phase=0,actual=False,images=None,entry=source.ENTRY,symbols=None):
        memory=fixture(pattern,alias,phase);want,calls=reference(memory,pattern,mode,phase,actual,symbols)
        machines=[Oracle(w,memory,pattern,mode,phase,entry,self.point_code if actual else None,symbols).run()
            for w in (images or [self.truth,*self.images])]
        for m in machines:
            self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(want),calls,1));self.assertEqual(state(m),state(machines[0]))
        return machines[0]

    def test_01_words_bindings_pool_and_effective_controls(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['new_guards'],self.row['unchanged_raw_padded_neighbors']),(64,136,0,8))
        raw,bindings=source.parts(self.obj)
        for i in range(64):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'changed')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        before=(self.out/'before-fixed_owner').read_text()
        controls={'scale':source.SELECTED.replace('* 3.0f','* 2.0f'),
            'point':source.SELECTED.replace('-495.0f','-494.0f'),
            'layout':source.SELECTED.replace('    f32 point[3];\n    f32 matrix[4][4];','    f32 matrix[4][4];\n    f32 point[3];')}
        for label,body in controls.items():
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'control-'+label)
            self.assertEqual(diag,'')
            with self.assertRaises(ValueError):source.checked_parts(*source.parts(obj))
        self.receipt('emission',**self.row,word_controls=64,binding_controls=2,compiled_controls=3)

    def test_02_truncation_provider_mutations_and_aliases(self):
        count=0;seen=set()
        for pattern,mode,alias,phase in itertools.product(range(8),range(4),range(4),(0,8)):
            m=self.compare(pattern,mode,alias,phase);seen.update(m.visits);count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+source.SIZE,4)))
        self.receipt('guest',three_way_cases=count,all_64_words=True,SP_phases=2,
            finite_in_range_signed32_truncation_then_low16=True,owner_and_destination_reloads=True,
            halfword_store_redirect_and_private_output_alias=True,full_state_and_instruction_access_order=True,
            extended_aliases_are_guest_only=True)

    def test_03_actual_point_transform_and_rotation_stack(self):
        trig=(self.out/'before-rotation_trig_original').read_text()
        self.assertNotIn('$sp',trig);self.assertNotIn('  jal',trig)
        count=0
        for pattern,mode,phase in itertools.product(range(8),range(3),(0,8)):
            self.compare(pattern,mode,phase=phase,actual=True);count+=1
        joined={**self.rotation_code,**self.point_code};connected=0
        for pattern,phase in itertools.product(range(8),(0,8)):
            memory=fixture(pattern,phase=phase)
            machines=[Oracle(w,memory,pattern,phase=phase,connected=joined).run() for w in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual(state(m),state(machines[0]));self.assertEqual(m.r[2],1)
                self.assertEqual([c[0] for c in m.calls],[ROTATE,COS,SIN,COS,SIN,COS,SIN,TRANSFORM])
                # Independent dyadic Euler matrix, using the original operation order.
                c,s=.5,-.25
                matrix=(c*c,c*s,-s,0.,(s*s)*c-c*s,(s*s)*s+c*c,s*c,0.,
                    (c*s)*c+s*s,(c*s)*s-s*c,c*c,0.)
                at=STACK+phase-80
                self.assertEqual(tuple(read(m.memory,at+i*4) for i in range(12)),tuple(point.bits(v) for v in matrix))
                expected=transformed(m.memory,at)
                self.assertEqual(tuple(read(m.memory,DEST+0x0E+i*2,2) for i in range(3)),
                    tuple(math.trunc(point.floating(v))&65535 for v in expected))
            connected+=1
        self.receipt('connected',actual_point_three_way_cases=count,rotation_and_point_cases=connected,
            point_words=40,rotation_words=83,callee_saved_FPR_and_split_SP_restore=True,
            six_trig_calls_are_scripted_dyadic_boundaries=True,hardware_FCSR_and_gameplay_not_claimed=True)

    def test_04_every_instruction_access_fault_prefix(self):
        count=0
        for mode,alias,phase,connected in itertools.product((0,1,3),(0,1,3),(0,8),(None,self.point_code)):
            memory=fixture(2,alias,phase);good=Oracle(self.truth,memory,2,mode,phase,connected=connected).run()
            for at in range(good.all_accesses):
                machines=[Oracle(w,memory,2,mode,phase,connected=connected) for w in (self.truth,*self.images)]
                for m in machines:
                    m.access_fault=at
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,at)
                for m in machines[1:]:self.assertEqual(state(m),state(machines[0]))
                count+=1
        self.receipt('faults',three_way_prefixes=count,actual_point_helper=True,
            no_observer_accesses=True,portable_C_fault_or_hardware_exception_parity_not_claimed=True)

    def test_05_independent_helper_relocations(self):
        count=0
        for index,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            symbols=source.SYMBOLS if index==0 else {'func_150A8050':0x151A7FFC+index*0x10000,'func_150A7960':0x152A8000+index*0x10000}
            images=[]
            for label,obj in (('original',self.original),('raw',self.obj),('padded',self.padded)):
                data,fs,rs=source.parse_object(obj);text,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols)
                self.assertEqual(unknown,[]);stem=self.out/('rebase-%d-%s'%(index,label));asm=stem.with_suffix('.s');asm.write_text(text)
                compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>64I',source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images,[images[0]]*3)
            for pattern,mode,phase in itertools.product((0,3,7),(0,1,3),(0,8)):
                self.compare(pattern,mode,phase=phase,images=images,entry=entry,symbols=symbols);count+=1
        self.receipt('rebases',independent_links=9,three_way_cases=count,bindings=2)

    def test_06_native32_typed_objects_and_controls(self):
        head='#include <ultra64.h>\nvoid func_150A8050(f32 [4][4],f32,f32,f32);\n'+source.TYPE
        driver=self.out/'native-driver.c';driver.write_text(head+NATIVE)
        controls={'point':source.SELECTED.replace('-495.0f','-494.0f'),
            'scale':source.SELECTED.replace('* 3.0f','* 2.0f'),
            'truncate':source.SELECTED.replace('(s32)point[1]','(s32)(point[1] + 1.0f)')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=32,profiles=['O2','O0'],UBSan=True,separately_typed_caller=True,
            effective_controls=6,valid_complete_objects=True,scripted_helpers=True,
            guest_pointer_alias_and_out_of_range_float_conversion_not_claimed=True)

    def test_07_every_live_and_frozen_input(self):
        source.freeze(self.root,self.out);original=Path.read_bytes;real=hashlib.sha256;cache={};count=0
        for key,path in source.PATHS.items():
            for p in (self.root/path,self.out/('before-'+key)):cache[p]=p.read_bytes()
        @lru_cache(None)
        def digest(data):return real(data)
        for key,path in source.PATHS.items():
            for target,kind in ((self.root/path,'live'),(self.out/('before-'+key),'frozen')):
                wrong=bytearray(cache[target]);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else cache[path] if path in cache else original(path)
                with patch.object(Path,'read_bytes',altered),patch.object(Path,'exists',lambda p:p in cache),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,'Changed halfword-point '+kind+' input'):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),effective_controls=count)

    def test_08_entire_first_image_and_checkpoint(self):
        from tools.experiments import game_halfword_point_update_installation as install
        from tools.tests import halfword_point_checkpoint as checkpoint
        from tools.match_progress import load_elf_functions
        from tools.tests.test_game_one_shot_timer_match import symbol_rows
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out);baseline=(out/'before-elf').read_bytes()
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        if not (out/'after-elf').exists():
            self.receipt('installation',installed=False,first_image_qualified=True);return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            from tools.tests import actor_state_checkpoint as latest
            self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.AFTER[key])
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                target=out/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed halfword-point checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
            wrong=bytearray(data);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong);count+=1
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        old,_,oa=load_elf_functions(str(out/'before-elf'),'mips-linux-gnu-objdump')
        new,_,na=load_elf_functions(str(out/'after-elf'),'mips-linux-gnu-objdump')
        self.assertEqual(oa,na);self.assertEqual(set(old),set(new))
        self.assertEqual([n for n in old if old[n]!=new[n]],[source.FUNCTION])
        old_symbols=[(n,(f[1],source.SIZE if n==source.FUNCTION else f[2],*f[3:])) for _,n,f,_ in symbol_rows(baseline)]
        self.assertEqual(sorted(old_symbols),sorted((n,f[1:]) for _,n,f,_ in symbol_rows(expected['elf'])))
        owned={source.PATHS[k] for k in expected}
        for key,path in source.PATHS.items():
            if path not in owned:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())
        self.receipt('installation',installed=True,entire_first_image_exact=True,metadata_exclusions=0,
            checkpoint_controls=count,game_data=report,compared_function_bodies=len(old),only_target_changed=True,
            all_function_addresses_unchanged=True,symbol_definitions_unchanged_except_target_extent=True,
            all_other_protected_inputs_unchanged=True)


NATIVE=r'''
s32 func_150F25A0(u8 *);
typedef struct {u8 pad[20];u8 *destination;u8 *owner;} Record;
typedef struct {f32 pad[8];f32 x,unused,z;f32 gap[3];f32 tx,ty,tz;} Owner;
typedef union {f32 align;u8 bytes[64];} Destination;
static Record record;static Owner owner,other;static Destination dest,second;
static int mode,pattern,error,calls;
static f32 values[8]={.75f,-.75f,32767.75f,32768.75f,65535.75f,-65536.75f,2147483520.f,-2147483648.f};
void func_150A8050(f32 matrix[4][4],f32 x,f32 y,f32 z){int i;
if(x!=owner.x*3.f||y!=0.f||z!=owner.z*3.f||calls++!=0)error=1;
for(i=0;i<16;i++)((f32 *)matrix)[i]=i%5==0?1.f:0.f;
if(mode==1)record.owner=(u8 *)&other;
if(mode==2){owner.tx=-3.25f;owner.ty=5.75f;owner.tz=-7.5f;}}
void func_150A7960(f32 matrix[4][4],f32 x,f32 y,f32 z,f32 *ox,f32 *oy,f32 *oz){
Owner *o=(Owner *)record.owner;
if(x!=0.f||y!=-495.f||z!=0.f||oy!=ox+1||oz!=ox+2||calls++!=1||matrix[3][0]!=o->tx||matrix[3][1]!=o->ty||matrix[3][2]!=o->tz)error=1;
*ox=3.75f;*oy=values[(pattern+1)%8];*oz=values[(pattern+2)%8];if(mode==3)record.destination=second.bytes;}
static int run(void){int i,j,k;u8 *target;
if(sizeof(void*)!=4||__builtin_offsetof(Record,owner)!=24||__builtin_offsetof(Owner,tx)!=56)return 20;
for(pattern=0;pattern<8;pattern++)for(mode=0;mode<4;mode++){
record.destination=dest.bytes;record.owner=(u8 *)&owner;calls=error=0;
owner.x=(f32)(pattern-3)*.25f;owner.z=(f32)(pattern+1)*-.5f;
owner.tx=17.75f;owner.ty=-23.5f;owner.tz=31.25f;other=owner;other.tx+=1.f;other.ty-=1.f;other.tz+=1.f;
for(i=0;i<64;i++)dest.bytes[i]=second.bytes[i]=0xA5;
if(func_150F25A0((u8 *)&record)!=1||error||calls!=2)return 22;
target=mode==3?second.bytes:dest.bytes;
for(j=0;j<3;j++){s16 expected=(s16)(s32)(j?values[(pattern+j)%8]:3.75f);
if(*(s16 *)(target+14+j*2)!=expected)return 22;}
for(i=0;i<64;i++)if(i<14||i>=20){if(target[i]!=0xA5)return 22;}
for(k=0;k<64;k++)if((mode==3?dest.bytes:second.bytes)[k]!=0xA5)return 22;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
