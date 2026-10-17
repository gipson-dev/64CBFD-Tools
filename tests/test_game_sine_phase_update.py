"""Complete updater ABI, real retail math, guard/rebase and whole-image gates."""
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

from tools.experiments import game_sine_phase_update as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_trig_match as trig
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.game_animation_timeline_oracle import signed
from tools.check_game_data_layout import audit_layout

STACK,ACTOR=point.STACK,0x20000
SINE,WRAP,CLOCK,BOUND=0x15047D60,0x15144B68,0x800BE9A4,0x800A56A4
CALLER,FREE,TABLE,TICK=0x1513B798,0x1516972C,0x80089C18,0x800BE9E4
SYMBOLS=dict(sinf=SINE,func_15144B68=WRAP,D_800BE9A4=CLOCK)
PATTERNS=((1.,-2.5,.25,-.5,2.,-3.),(0.,-0.,0.,-0.,1.,1.),
    (-0.,0.,-0.,0.,-1.,2.),(12.5,-15.75,3.,-4.,.125,8.),
    (0x7FC12345,1.,.5,-.25,2.,3.),(.00001,-.00002,.00003,.00004,0x7F800000,0xFF800000))


def word(value):return value if isinstance(value,int) else point.bits(value)


def fixture(pattern=0,offset=0,clock=1.,alias=-1,symbols=None):
    s=symbols or SYMBOLS
    state=ACTOR+offset+0xF8 if alias<0 else s['D_800BE9A4']-alias*4
    actor=(state-offset-0xF8)&0xffffffff
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x180)}
    for base,size in ((actor-16,0x220),(state-16,80),(s['D_800BE9A4']-16,36)):
        for i in range(size):memory.setdefault(base+i,(i*13+0x57)&255)
    for at,value in trig.GLOBALS.items():put(memory,at,value)
    put(memory,BOUND,0x40C90FDB)
    for i,value in enumerate((*PATTERNS[pattern],0.,0.,0.,99.,-99.)):put(memory,state+i*4,word(value))
    put(memory,s['D_800BE9A4'],point.bits(clock));put(memory,actor+0x50,offset)
    return memory,(actor,),state


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x180}


def wrap(value):
    bound=0x40C90FDB
    for _ in range(256):
        if point.floating(value)>point.floating(bound):value=point.sub(value,bound)
        elif point.floating(value)<0.:value=point.add(value,bound)
        else:return value
    raise ValueError('Outside bounded finite-wrap reference')


def effects(memory,actor,state,ordinal,mode,clock):
    if mode and ordinal==1:
        put(memory,actor+0x50,0x4000);put(memory,state+16,point.bits(7.))
    if mode and ordinal==3:
        put(memory,clock,point.bits(2.));put(memory,state+4,point.bits(-3.));put(memory,state+12,point.bits(.75))


def reference(initial,args,mode=0,symbols=None):
    s=symbols or SYMBOLS;memory=dict(initial);actor=args[0]
    state=(actor+signed(read(memory,actor+0x50))+0xF8)&0xffffffff;calls=[]
    def call(target,value):
        calls.append((target,value))
        result=trig.reference(value) if target==s['sinf'] else wrap(value)
        effects(memory,actor,state,len(calls),mode,s['D_800BE9A4'])
        return result
    value=call(s['sinf'],read(memory,state));put(memory,state+36,point.mul(value,read(memory,state+16)))
    value=call(s['sinf'],read(memory,state+4));put(memory,state+40,point.mul(value,read(memory,state+20)))
    value=point.add(read(memory,state),point.mul(read(memory,state+8),read(memory,s['D_800BE9A4'])))
    put(memory,state,call(s['func_15144B68'],value))
    value=point.add(read(memory,state+4),point.mul(read(memory,state+12),read(memory,s['D_800BE9A4'])))
    put(memory,state+4,call(s['func_15144B68'],value))
    return public(memory),calls


class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None,mode=0,symbols=None):
        self.io=[];self.targets=symbols or SYMBOLS;self.actor=args[0];self.mode=mode
        self.selected=(args[0]+signed(read(memory,args[0]+0x50))+0xF8)&0xffffffff
        super().__init__(words,memory,args,[],phase,entry,connected)
        self.mode=mode

    def execute(self,word):
        op,rs,rt,rd,shift,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        if op==0 and fn==3:self.r[rd]=signed(self.r[rt])>>shift&0xffffffff
        elif op==17 and rs==16 and fn==7:self.f[shift]=self.f[rd]^0x80000000
        elif op==17 and rs==16 and fn==13:self.f[shift]=math.trunc(point.floating(self.f[rd]))&0xffffffff
        elif op==32:
            super().execute(word|0x10000000)
            if rt:self.r[rt]=((self.r[rt]^128)-128)&0xffffffff
            self.dispatched_word=word
        else:super().execute(word)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        if target in (self.targets['sinf'],self.targets['func_15144B68']):
            self.calls.append((target,self.f[12]))
            self.observations.append(tuple(read(self.memory,self.selected+i*4) for i in range(11)))
        elif target in (source.ENTRY,FREE):self.calls.append((target,(self.r[4],)))
        else:raise AssertionError('Unexpected sine-phase provider '+hex(target))

    def hook(self,target):
        if target==FREE:
            put(self.memory,self.r[4]+0x10,0,1);value=0
        else:
            value=trig.reference(self.f[12]) if target==self.targets['sinf'] else wrap(self.f[12])
            effects(self.memory,self.actor,self.selected,len(self.calls),self.mode,self.targets['D_800BE9A4'])
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=value


def state(m):return point.state(m),m.condition,m.io


class SinePhaseUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>38I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-sine-phase',
            (cls.out/'before-phase_original').read_text(),source.FUNCTION)
        cls.connected={SINE+i*4:w for i,w in enumerate(struct.unpack_from('>104I',cls.rom,0x75210))}
        cls.connected.update({WRAP+i*4:w for i,w in enumerate(struct.unpack_from('>24I',cls.rom,0x172018))})

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase=0,mode=0,connected=None,images=None,entry=source.ENTRY,symbols=None):
        want,calls=reference(memory,args,mode,symbols)
        machines=[Oracle(words,memory,args,phase,entry,connected,mode,symbols).run() for words in (images or [self.truth,*self.images])]
        for m in machines:
            self.assertEqual((public(m.memory),m.calls),(want,calls));self.assertEqual(m.r[2],1)
            self.assertEqual(state(m),state(machines[0]))
        return machines[0]

    def test_01_complete_words_bindings_and_actual_guard_failure(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['new_guards'],self.row['unchanged_raw_padded_neighbors']),(38,32,1,8))
        self.assertEqual(self.images[1],self.truth);raw,bindings=source.parts(self.obj)
        for i in range(38):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'changed')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        data,fs,_=source.parse_object(self.obj);f=fs[source.FUNCTION]
        # Locate the actual text section through the ELF section parser.
        from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER
        allbytes=bytearray(self.obj.read_bytes());header=ELF_HEADER.unpack_from(allbytes)
        rows=[SECTION_HEADER.unpack_from(allbytes,header[6]+i*header[11]) for i in range(header[12])]
        textrow=next(r for r in rows if r[1]==1 and r[2]&4)
        allbytes[textrow[4]+f['value']+0x10]^=1
        wrong=self.out/'guard-control.o';wrong.write_bytes(allbytes)
        with self.assertRaises((ValueError,AssertionError)):source.padded_object(self.root,self.out,wrong,'guard-control')
        self.receipt('emission',**self.row,word_controls=38,binding_controls=8,actual_guard_failure=True,
            ADDU_modulo_32bit_commutativity=True)

    def test_02_scripted_ABI_lifetime_reload_alias_and_private_order(self):
        count=0;seen=set()
        for pattern,offset,clock,phase,mode in itertools.product(range(6),(-0xF8,-0xD0,0,16),(0.,1.,-1.,4.),(0,8),(0,1)):
            memory,args,_=fixture(pattern,offset,clock)
            m=self.compare(memory,args,phase,mode);seen.update(m.visits);count+=1
        aliases=0
        for alias,pattern,phase in itertools.product((0,1,2,3,4,5,9,10),(0,1,3),(0,8)):
            memory,args,_=fixture(pattern,alias=alias)
            self.compare(memory,args,phase);aliases+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+source.SIZE,4))<=seen)
        self.receipt('guest',three_way_cases=count,alias_cases=aliases,all_38_words=True,
            adversarial_float_call_clobbers=True,captured_state_pointer=True,clock_and_amplitude_reload=True,
            full_private_state_access_order=True,model_not_hardware_FCSR=True)

    def test_03_actual_connected_retail_sine_and_wrap(self):
        count=0
        for pattern,offset,clock,phase in itertools.product(range(6),(-0xF8,0,16),(0.,1.,-1.,4.),(0,8)):
            memory,args,_=fixture(pattern,offset,clock)
            self.compare(memory,args,phase,connected=self.connected);count+=1
        self.assertEqual(struct.unpack_from('>I',self.rom,0x24A164)[0],0x40C90FDB)
        self.receipt('connected',three_way_cases=count,actual_sine_words=104,actual_wrap_words=24,
            real_argument_home_store=True,independent_existing_sine_reference=True,
            finite_bounded_wrap_and_NaN=True,Inf_and_huge_phase_completion_not_claimed=True)

    def test_04_every_real_access_fault_prefix(self):
        count=0
        for connected,pattern,phase,mode in itertools.product((None,self.connected),(0,3,4),(0,8),(0,1)):
            if connected and mode:continue
            memory,args,_=fixture(pattern)
            good=Oracle(self.truth,memory,args,phase,connected=connected,mode=mode).run()
            for at in range(good.all_accesses):
                machines=[Oracle(w,memory,args,phase,connected=connected,mode=mode) for w in (self.truth,*self.images)]
                for m in machines:
                    m.access_fault=at
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,at)
                for m in machines[1:]:self.assertEqual(state(m),state(machines[0]))
                count+=1
        self.receipt('faults',three_way_prefixes=count,real_helpers_and_adversarial_hooks=True,
            no_observer_reads=True,portable_C_fault_or_hardware_exception_parity_not_claimed=True)

    def test_05_independent_relocations_and_guard_commutativity(self):
        count=0
        for index,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            symbols=SYMBOLS if index==0 else dict(sinf=0x15088004+index*0x10000,
                func_15144B68=0x15197FFC+index*0x10000,D_800BE9A4=0x80348000+index*0x100000)
            images=[]
            for label,obj in (('original',self.original),('raw',self.obj),('padded',self.padded)):
                data,fs,rs=source.parse_object(obj);text,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols)
                self.assertEqual(unknown,[]);stem=self.out/('rebase-%d-%s'%(index,label))
                asm=stem.with_suffix('.s');asm.write_text(text);compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>38I',source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[2])
            self.assertEqual([i for i,(a,b) in enumerate(zip(images[0],images[1])) if a!=b],[4])
            for offset,phase,mode in itertools.product((-0xF8,-0xD0,0,16),(0,8),(0,1)):
                memory,args,_=fixture(3,offset,symbols=symbols)
                self.compare(memory,args,phase,mode,images=images,entry=entry,symbols=symbols);count+=1
        values=(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF,0x12345678)
        for a,b in itertools.product(values,repeat=2):
            memory,args,_=fixture();machines=[Oracle([w,0x03E00008,0],memory,args) for w in (0x01C48021,0x008E8021)]
            for m in machines:m.r[4]=a;m.r[14]=b;m.before[16]=(a+b)&0xffffffff;m.run()
            self.assertEqual(state(machines[0]),state(machines[1]))
        self.receipt('rebases',independent_links=9,three_way_cases=count,bindings=8,
            signed_low_carry=True,isolated_guard_cases=36,guard_has_no_relocations=True)

    def test_06_native32_separate_typed_caller_and_effective_controls(self):
        head='#include <ultra64.h>\n'+source.TYPE
        driver=self.out/'native-driver.c';driver.write_text(head+NATIVE)
        controls={'output':source.SELECTED.replace('state[9] =','state[8] ='),
            'rate':source.SELECTED.replace('state[2] *','state[3] *')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=256,profiles=['O2','O0'],UBSan=True,
            separately_typed_caller=True,effective_controls=4,scripted_float_providers_not_retail_math=True,
            valid_nonaliased_objects_only=True)

    def test_07_effective_IDO_reload_and_output_controls(self):
        controls={'output':source.SELECTED.replace('state[9] =','state[8] ='),
            'clock-cache':source.SELECTED.replace('    f32 *state;','    f32 *state;\n    f32 clock = D_800BE9A4;').replace('* D_800BE9A4','* clock')}
        before=(self.out/'before-phase_owner').read_text()
        for label,body in controls.items():
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'control-'+label);self.assertFalse(diag)
            with self.assertRaises(ValueError):source.checked_parts(*source.parts(obj))
            data,fs=source.build.link_owner(self.root,self.out,obj,source.OWNER);f=fs[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            memory,args,_=fixture()
            good=Oracle(self.truth,memory,args,mode=1).run();wrong=Oracle(words,memory,args,mode=1).run()
            self.assertNotEqual(public(wrong.memory),public(good.memory),label)
        self.receipt('controls',effective_IDO_controls=2,clock_mutation_exercises_reload=True)

    def test_08_actual_timer_dispatcher_slot_three(self):
        caller=list(struct.unpack_from('>41I',self.rom,0x168C48));count=0
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22E6E4)[0],source.ENTRY)
        for timer,counter,tick,callback,phase in itertools.product((0,1),(-32768,-1,0,1,3,32767),(0,1,3),(-1,3),(0,8)):
            memory,args,_=fixture();actor=args[0]
            put(memory,actor+0x10,timer,1);put(memory,actor+0x11,callback,1);put(memory,actor+0x14,counter,2)
            put(memory,TICK,tick);put(memory,TABLE+12,source.ENTRY);want=dict(memory);calls=[]
            stop=False
            if timer:
                put(want,actor+0x14,counter-tick,2);stop=point.half(read(want,actor+0x14,2))<0
            if not stop and callback==3:
                public_want,math_calls=reference(want,args);want.update(public_want);calls=[(source.ENTRY,(actor,)),*math_calls]
            if stop:put(want,actor+0x10,0,1);calls.append((FREE,(actor,)))
            machines=[]
            for words in (self.truth,*self.images):
                connected=dict(self.connected);connected.update({source.ENTRY+i*4:w for i,w in enumerate(words)})
                machines.append(Oracle(caller,memory,args,phase,CALLER,connected).run())
            for m in machines:
                self.assertEqual((public(m.memory),m.calls),(public(want),calls));self.assertEqual(state(m),state(machines[0]))
            count+=1
        self.receipt('caller',complete_caller_words=41,three_way_cases=count,table_slot=3,
            actual_retail_sine_and_wrap=True,scripted_free_boundary=True,gameplay_or_full_heap_not_claimed=True)

    def test_09_every_protected_live_and_frozen_input(self):
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
                    with self.assertRaisesRegex(ValueError,'Changed sine-phase '+kind+' input'):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),effective_controls=count)

    def test_10_entire_first_image_and_fail_closed_checkpoint(self):
        from tools.experiments import game_sine_phase_update_installation as install
        from tools.tests import sine_phase_update_checkpoint as checkpoint
        from tools.match_progress import load_elf_functions
        from tools.tests.test_game_one_shot_timer_match import symbol_rows
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        self.assertEqual(install.predict_compatibility(self.root,out),checkpoint.EXTRA_AFTER)
        expected.update(install.compatibility_inputs(self.root,out))
        if not (out/'after-elf').exists():
            self.receipt('installation',installed=False,first_image_qualified=True);return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),dict(checkpoint.AFTER,**checkpoint.EXTRA_AFTER)[key])
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                target=out/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed sine-phase checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
            wrong=bytearray(data);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong);count+=1
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        baseline=(out/'before-elf').read_bytes()
        old,_,oa=load_elf_functions(str(out/'before-elf'),'mips-linux-gnu-objdump')
        new,_,na=load_elf_functions(str(out/'after-elf'),'mips-linux-gnu-objdump')
        self.assertEqual(oa,na);self.assertEqual(set(old),set(new))
        self.assertEqual([n for n in old if old[n]!=new[n]],[source.FUNCTION])
        old_symbols=[(n,(f[1],source.SIZE if n==source.FUNCTION else f[2],*f[3:])) for _,n,f,_ in symbol_rows(baseline)]
        self.assertEqual(sorted(old_symbols),sorted((n,f[1:]) for _,n,f,_ in symbol_rows(expected['elf'])))
        for key,path in source.PATHS.items():
            if key not in expected:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())
        self.receipt('installation',installed=True,entire_first_image_exact=True,metadata_exclusions=0,
            checkpoint_controls=count,game_data=report,compared_function_bodies=len(old),
            only_target_changed=True,all_function_addresses_unchanged=True,
            symbol_definitions_unchanged_except_target_extent=True,all_other_protected_inputs_unchanged=True)


NATIVE=r'''
s32 func_150F2480(u8 *);
typedef struct {u8 pad[80];s32 offset;u8 tail[164];f32 values[16];} Actor;
static Actor actor;
static f32 *selected;
static int ordinal;
f32 D_800BE9A4;
f32 sinf(f32 angle){ordinal++;if(ordinal==1)actor.offset=0x4000;return angle*.5f+1.f;}
f32 func_15144B68(f32 angle){ordinal++;if(ordinal==3){D_800BE9A4=2.;selected[1]=-3.;selected[3]=.75f;}return angle-.25f;}
static int run(void){int i,j;
if(sizeof(void*)!=4||__builtin_offsetof(Actor,offset)!=80||__builtin_offsetof(Actor,values)!=248)return 20;
for(i=0;i<256;i++){f32 a,b,r0,r1,out0,out1;
actor.offset=(i&1)*16;selected=actor.values+(i&1)*4;ordinal=0;D_800BE9A4=1.;
for(j=0;j<12;j++)selected[j]=(f32)(j+i%7)*.25f;
a=selected[0];b=selected[1];r0=selected[2];r1=.75f;
out0=(a*.5f+1.f)*selected[4];out1=(b*.5f+1.f)*selected[5];
a=(a+r0)-.25f;b=(-3.f+r1*2.f)-.25f;
if(func_150F2480((u8 *)&actor)!=1||ordinal!=4||selected[0]!=a||selected[1]!=b||selected[9]!=out0||selected[10]!=out1)return 22;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
