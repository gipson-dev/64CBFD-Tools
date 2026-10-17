"""Direct fixed-state sine updater, real helper ABI and full-image qualification."""
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_fixed_sine_update as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import test_game_sine_phase_update as phase
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.check_game_data_layout import audit_layout

STACK,ACTOR,OTHER=point.STACK,0x20000,0x30000
SINE,WRAP,CLOCK=phase.SINE,phase.WRAP,phase.CLOCK
CALLER,BOUNDS,FREE,TABLE,TICK=0x151321D0,0x1514672C,0x1516972C,0x800898B0,0x800BE9E4
SYMBOLS=phase.SYMBOLS


def fixture(pattern=0,clock=1.,alias=-1,symbols=None):
    s=symbols or SYMBOLS
    actor=ACTOR if alias<0 else s['D_800BE9A4']-(0x20,0x28,0x170,0x174,0x178,0x17C,0x180,0x184)[alias]
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x180)}
    for base in (actor,OTHER):
        for i in range(-16,0x200):memory.setdefault(base+i,(i*13+0x57)&255)
        for i,value in enumerate(phase.PATTERNS[pattern]):put(memory,base+0x170+i*4,phase.word(value))
        put(memory,base+0x20,point.bits(99.));put(memory,base+0x28,point.bits(-99.))
        put(memory,base+0x50,0)
    for at,value in phase.trig.GLOBALS.items():put(memory,at,value)
    put(memory,phase.BOUND,0x40C90FDB)
    put(memory,s['D_800BE9A4'],point.bits(clock))
    return memory,(actor,)


def effects(memory,state,ordinal,mode,clock):
    if mode and ordinal==1:put(memory,state+16,point.bits(7.))
    if mode and ordinal==3:
        put(memory,clock,point.bits(2.));put(memory,state+4,point.bits(-3.));put(memory,state+12,point.bits(.75))


def reference(initial,args,mode=0,symbols=None):
    s=symbols or SYMBOLS;memory=dict(initial);actor=args[0];state=actor+0x170;calls=[]
    def call(target,value):
        calls.append((target,value))
        result=phase.trig.reference(value) if target==s['sinf'] else phase.wrap(value)
        effects(memory,state,len(calls),mode,s['D_800BE9A4'])
        return result
    value=call(s['sinf'],read(memory,state));put(memory,actor+0x20,point.mul(value,read(memory,state+16)))
    value=call(s['sinf'],read(memory,state+4));put(memory,actor+0x28,point.mul(value,read(memory,state+20)))
    value=point.add(read(memory,state),point.mul(read(memory,state+8),read(memory,s['D_800BE9A4'])))
    put(memory,state,call(s['func_15144B68'],value))
    value=point.add(read(memory,state+4),point.mul(read(memory,state+12),read(memory,s['D_800BE9A4'])))
    put(memory,state+4,call(s['func_15144B68'],value))
    return phase.public(memory),calls


class Oracle(phase.Oracle):
    def __init__(self,words,memory,args,phase_offset=0,entry=source.ENTRY,connected=None,mode=0,symbols=None,home_mutation=0,bound=1):
        super().__init__(words,memory,args,phase_offset,entry,connected,mode,symbols)
        self.selected=args[0]+0x170;self.home_mutation=home_mutation;self.bound=bound

    def record_call(self,target):
        if target in (self.targets['sinf'],self.targets['func_15144B68']):
            self.calls.append((target,self.f[12]))
            self.observations.append((self.r[16],read(self.memory,self.r[29]+32),
                tuple(read(self.memory,self.selected+i*4) for i in range(6))))
        elif target in (source.ENTRY,BOUNDS,FREE):self.calls.append((target,(self.r[4],)))
        else:raise AssertionError('Unexpected fixed-sine provider '+hex(target))

    def hook(self,target):
        if target==FREE:
            put(self.memory,self.r[4]+0x60,0);value=0
        elif target==BOUNDS:value=0
        else:
            ordinal=sum(t in (self.targets['sinf'],self.targets['func_15144B68']) for t,_ in self.calls)
            value=phase.trig.reference(self.f[12]) if target==self.targets['sinf'] else phase.wrap(self.f[12])
            effects(self.memory,self.selected,ordinal,self.mode,self.targets['D_800BE9A4'])
            if ordinal==self.home_mutation:put(self.memory,self.r[29]+32,OTHER)
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=value
        if target==BOUNDS:self.r[2]=self.bound


def state(m):return point.state(m),m.condition,m.io


class FixedSineUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>40I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-fixed-sine',
            (cls.out/'before-phase_original').read_text(),source.FUNCTION)
        cls.connected={SINE+i*4:w for i,w in enumerate(struct.unpack_from('>104I',cls.rom,0x75210))}
        cls.connected.update({WRAP+i*4:w for i,w in enumerate(struct.unpack_from('>24I',cls.rom,0x172018))})

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase_offset=0,mode=0,connected=None,images=None,entry=source.ENTRY,symbols=None):
        want,calls=reference(memory,args,mode,symbols)
        machines=[Oracle(w,memory,args,phase_offset,entry,connected,mode,symbols).run() for w in (images or [self.truth,*self.images])]
        for m in machines:
            self.assertEqual((phase.public(m.memory),m.calls,m.r[2]),(want,calls,1))
            self.assertEqual(state(m),state(machines[0]))
        return machines[0]

    def test_01_direct_complete_words_bindings_and_identity_controls(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['new_guards'],self.row['unchanged_raw_padded_neighbors']),(40,32,0,8))
        self.assertEqual(self.images,[self.truth,self.truth]);raw,bindings=source.parts(self.obj)
        for i in range(40):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'changed')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        self.receipt('emission',**self.row,word_controls=40,binding_controls=8,real_actor_home_offset=32)

    def test_02_scripted_ABI_reload_alias_and_complete_private_order(self):
        count=0;seen=set()
        for pattern,clock,stack,mode in itertools.product(range(6),(0.,1.,-1.,4.),(0,8),(0,1)):
            memory,args=fixture(pattern,clock);m=self.compare(memory,args,stack,mode);seen.update(m.visits);count+=1
        aliases=0
        for alias,pattern,stack in itertools.product(range(8),(0,1,3),(0,8)):
            memory,args=fixture(pattern,alias=alias);self.compare(memory,args,stack);aliases+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+source.SIZE,4))<=seen)
        self.receipt('guest',three_way_cases=count,alias_cases=aliases,all_40_words=True,
            caller_saved_clobbers_and_real_homes=True,clock_and_amplitude_reload=True,
            full_private_state_access_order=True,model_not_hardware_FCSR=True)

    def test_03_actual_connected_retail_sine_and_wrap(self):
        count=0
        for pattern,clock,stack in itertools.product(range(6),(0.,1.,-1.,4.),(0,8)):
            memory,args=fixture(pattern,clock);self.compare(memory,args,stack,connected=self.connected);count+=1
        self.receipt('connected',three_way_cases=count,actual_sine_words=104,actual_wrap_words=24,
            real_argument_home_store=True,independent_existing_sine_reference=True,
            bounded_finite_wrap_and_NaN=True,Inf_and_huge_phase_completion_not_claimed=True)

    def test_04_every_real_access_fault_prefix(self):
        count=0
        for connected,pattern,stack,mode in itertools.product((None,self.connected),(0,3,4),(0,8),(0,1)):
            if connected and mode:continue
            memory,args=fixture(pattern);good=Oracle(self.truth,memory,args,stack,connected=connected,mode=mode).run()
            for at in range(good.all_accesses):
                machines=[Oracle(w,memory,args,stack,connected=connected,mode=mode) for w in (self.truth,*self.images)]
                for m in machines:
                    m.access_fault=at
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,at)
                for m in machines[1:]:self.assertEqual(state(m),state(machines[0]))
                count+=1
        self.receipt('faults',three_way_prefixes=count,real_helpers_and_scripted_clobbers=True,
            no_observer_reads=True,portable_C_fault_or_hardware_exception_parity_not_claimed=True)

    def test_05_nine_independent_links_all_eight_sites(self):
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
                images.append(list(struct.unpack_from('>40I',source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images,[images[0]]*3)
            for pattern,stack,mode in itertools.product((0,1,3),(0,8),(0,1)):
                memory,args=fixture(pattern,symbols=symbols)
                self.compare(memory,args,stack,mode,images=images,entry=entry,symbols=symbols);count+=1
        self.receipt('rebases',independent_links=9,three_way_cases=count,bindings=8,signed_low_carry=True)

    def test_06_native32_separate_typed_caller_and_effective_controls(self):
        head='#include <ultra64.h>\nextern f32 D_800BE9A4;\nf32 func_15144B68(f32);\n'
        driver=self.out/'native-driver.c';driver.write_text(head+NATIVE)
        controls={'output':source.SELECTED.replace('(actor + 0x20)','(actor + 0x28)'),
            'rate':source.SELECTED.replace('state[2] *','state[3] *')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(phase.native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=256,profiles=['O2','O0'],UBSan=True,
            separately_typed_caller=True,effective_controls=4,scripted_float_providers_not_retail_math=True,
            valid_nonaliased_objects_only=True)

    def test_07_real_private_home_lifetime_and_compiled_controls(self):
        before=(self.out/'before-fixed_owner').read_text()
        controls={'early-S0':source.SELECTED.replace('u8 *actor)','u8 *volatile actor)'),
            'clock-cache':source.SELECTED.replace('    f32 *state =','    f32 clock = D_800BE9A4;\n    f32 *state =').replace('* D_800BE9A4','* clock')}
        compiled={}
        for label,body in controls.items():
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'control-'+label);self.assertFalse(diag)
            with self.assertRaises(ValueError):source.checked_parts(*source.parts(obj))
            data,fs=source.build.link_owner(self.root,self.out,obj,source.OWNER);f=fs[source.FUNCTION]
            compiled[label]=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
        private=public=0
        for home,stack in itertools.product((1,2),(0,8)):
            memory,args=fixture()
            machines=[Oracle(w,memory,args,stack,home_mutation=home).run() for w in (self.truth,*self.images)]
            for m in machines[1:]:self.assertEqual(state(m),state(machines[0]))
            wrong=Oracle(compiled['early-S0'],memory,args,stack,home_mutation=home).run()
            self.assertNotEqual(wrong.observations,machines[0].observations);private+=1
            if phase.public(wrong.memory)!=phase.public(machines[0].memory):public+=1
        self.assertGreater(public,0)
        memory,args=fixture();good=Oracle(self.truth,memory,args,mode=1).run()
        wrong=Oracle(compiled['clock-cache'],memory,args,mode=1).run()
        self.assertNotEqual(phase.public(good.memory),phase.public(wrong.memory))
        self.receipt('controls',real_home_three_way_cases=private,early_S0_private_counterexamples=private,
            early_S0_public_counterexamples=public,effective_clock_cache_control=True,
            private_home_mutation_is_guest_only_not_portable_C=True)

    def test_08_complete_actual_actor_dispatcher_slot_sixteen(self):
        caller=list(struct.unpack_from('>119I',self.rom,0x15F680));count=0
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22E3B0)[0],source.ENTRY)
        for flags,selector,counter,tick,stack,bound in itertools.product(
                (0,0x80000,0x80010,0x80080,0x280080),(0,16),(-1,0,3),(0,1,3),(0,8),(0,1)):
            memory,args=fixture();actor=args[0]
            for offset,value,size in ((0x60,flags,4),(0x64,counter,2),(0x71,selector,1),
                    (0x72,0,1),(0x76,0,1),(0x148,0,1)):
                put(memory,actor+offset,value,size)
            put(memory,TICK,tick);put(memory,TABLE+64,source.ENTRY);want=dict(memory);calls=[]
            flags&=0xFFDFFFFF;put(want,actor+0x60,flags)
            if selector:
                result,math_calls=reference(want,args);want.update(result);calls=[(source.ENTRY,(actor,)),*math_calls]
            stop=False
            if flags&0x80:
                put(want,actor+0x64,counter-tick,2);stop=point.half(read(want,actor+0x64,2))<0
            if not stop and not flags&0x80000:calls.append((BOUNDS,(actor+0x38,)));stop=not bound
            if stop:put(want,actor+0x60,0);calls.append((FREE,(actor,)))
            machines=[]
            for words in (self.truth,*self.images):
                connected=dict(self.connected);connected.update({source.ENTRY+i*4:w for i,w in enumerate(words)})
                machines.append(Oracle(caller,memory,args,stack,CALLER,connected,bound=bound).run())
            for m in machines:
                self.assertEqual((phase.public(m.memory),m.calls),(phase.public(want),calls));self.assertEqual(state(m),state(machines[0]))
            count+=1
        self.receipt('caller',complete_caller_words=119,three_way_cases=count,table_slot=16,
            actual_retail_sine_and_wrap=True,scripted_bounds_and_free=True,
            alternate_secondary_clamp_paths_and_gameplay_not_claimed=True)

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
                    with self.assertRaisesRegex(ValueError,'Changed fixed-sine '+kind+' input'):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),effective_controls=count)

    def test_10_entire_first_image_and_fail_closed_checkpoint(self):
        from tools.experiments import game_fixed_sine_update_installation as install
        from tools.tests import fixed_sine_update_checkpoint as checkpoint
        from tools.match_progress import load_elf_functions
        from tools.tests.test_game_one_shot_timer_match import symbol_rows
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        if not (out/'after-elf').exists():
            self.receipt('installation',installed=False,first_image_qualified=True);return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            from tools.tests import selector_point_checkpoint as latest
            self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.AFTER[key])
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                target=out/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed fixed-sine checkpoint fixture'):
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
        owned={source.PATHS[k] for k in expected}
        for key,path in source.PATHS.items():
            if path not in owned:
                from tools.tests import selector_point_checkpoint as latest
                self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(out/('before-'+key)).read_bytes())
        self.receipt('installation',installed=True,entire_first_image_exact=True,metadata_exclusions=0,
            checkpoint_controls=count,game_data=report,compared_function_bodies=len(old),
            only_target_changed=True,all_function_addresses_unchanged=True,
            symbol_definitions_unchanged_except_target_extent=True,all_other_protected_inputs_unchanged=True)


NATIVE=r'''
s32 func_150F23E0(u8 *);
typedef struct {u8 pad00[32];f32 x;u8 pad24[4];f32 z;u8 pad2C[324];f32 phases[6];} Actor;
static Actor actor;
static int ordinal;
f32 D_800BE9A4;
f32 sinf(f32 angle){ordinal++;return angle*.5f+1.f;}
f32 func_15144B68(f32 angle){ordinal++;if(ordinal==3){D_800BE9A4=2.;actor.phases[1]=-3.;actor.phases[3]=.75f;}return angle-.25f;}
static int run(void){int i,j;
if(sizeof(void*)!=4||__builtin_offsetof(Actor,x)!=32||__builtin_offsetof(Actor,z)!=40||__builtin_offsetof(Actor,phases)!=368)return 20;
for(i=0;i<256;i++){f32 a,b,r0,out0,out1;ordinal=0;D_800BE9A4=1.;actor.x=99.;actor.z=-99.;
for(j=0;j<6;j++)actor.phases[j]=(f32)(j+i%7)*.25f;
a=actor.phases[0];b=actor.phases[1];r0=actor.phases[2];
out0=(a*.5f+1.f)*actor.phases[4];out1=(b*.5f+1.f)*actor.phases[5];
a=(a+r0)-.25f;b=(-3.f+.75f*2.f)-.25f;
if(func_150F23E0((u8 *)&actor)!=1||ordinal!=4||actor.phases[0]!=a||actor.phases[1]!=b||actor.x!=out0||actor.z!=out1)return 22;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
