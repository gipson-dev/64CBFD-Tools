"""Actor branches, ordered event writes, O32 lifetimes and first-image audit."""
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_state_update as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.check_game_data_layout import audit_layout

STACK,ACTOR,STATE,OTHER,PLAYER,PLAYER2=point.STACK,0x20000,0x23000,0x24000,0x26000,0x27000
EVENT,QUERY,CHANGE,FINISH,HEIGHT,STOP=(source.SYMBOLS[n] for n in
    ('func_1509BFB0','func_1509BE40','func_15123934','func_15124B18','func_15128774','func_151239CC'))
LEAF=source.SYMBOLS[source.LEAF];GLOBAL=source.SYMBOLS['D_800D2E4C']
COUNTS={LEAF:2,EVENT:3,QUERY:4,CHANGE:5,FINISH:1,HEIGHT:2,STOP:2}
HEIGHTS=(float('-inf'),0.,299.999969482421875,300.,300.000030517578125,1000.,float('inf'),float('nan'))

def fixture(gate=(1,0),category=0,kind=0,busy=0,stage=1,height=1000.,byte=0,flag=8,phase=0,alias=0,global_address=GLOBAL):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x180)}
    for base,size in ((ACTOR,0x800),(STATE,0x180),(OTHER,0x180),(PLAYER,64),(PLAYER2,64),(global_address-4,12)):
        memory.update({base+i:0xA5 for i in range(size)})
    state=STATE if alias==0 else ACTOR+0x300
    put(memory,ACTOR+0x3D0,state);put(memory,ACTOR+0x2C,kind);put(memory,ACTOR+0x6C8,busy)
    put(memory,ACTOR+0x84,0x5A050017);put(memory,ACTOR+0x1B4,stage&65535,2)
    put(memory,ACTOR+0x370,point.bits(height));put(memory,ACTOR+0x23E,category,1);put(memory,ACTOR+0x3E8,byte,1)
    put(memory,state+0x102,gate[0],1);put(memory,state+0x104,gate[1],1)
    put(memory,global_address,PLAYER);put(memory,PLAYER+0x15,flag,1);put(memory,PLAYER2+0x15,flag^8,1)
    return memory

def public(memory):return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x180}

def effects(memory,target,args,ordinal,mode,global_address=GLOBAL):
    if mode==1 and target==EVENT and ordinal==16:put(memory,global_address,PLAYER2)
    if mode==2 and (target==EVENT and ordinal==1 or target==LEAF):put(memory,ACTOR+0x2C,0x100)
    if mode==3 and target==CHANGE:
        put(memory,ACTOR+0x3D0,OTHER);put(memory,ACTOR+0x370,point.bits(1000.))
    if mode==4 and target==FINISH:put(memory,ACTOR+0x3E8,1,1)
    if mode==5 and target==QUERY:put(memory,ACTOR+0x84,(0xA55A0000^args[1])&0xffffffff)
    if mode==6 and target==STOP:put(memory,ACTOR+0x1B4,1,2)

class Reference:
    def __init__(self,memory,pattern=0,mode=0,connected=False,symbols=None):
        self.memory=dict(memory);self.pattern,self.mode,self.connected=pattern,mode,connected
        self.symbols=symbols or source.SYMBOLS;self.calls=[];self.events=0

    def call(self,name,*args):
        target=self.symbols[name];args=tuple(a&0xffffffff for a in args);self.calls.append((target,args))
        if name==source.LEAF and self.connected:self.leaf(*args)
        else:
            if name=='func_1509BFB0':self.events+=1
            canonical=source.SYMBOLS[name]
            effects(self.memory,canonical,args,self.events,self.mode,self.symbols['D_800D2E4C'])
        if name=='func_15123934':return 0x80000000 if self.pattern&8 else 0
        if name=='func_1509BE40':return 0x80000000 if self.pattern&(1<<{0x405A:0,0x405E:1,0x405F:2}[args[1]]) else 0
        return 0

    def leaf(self,actor,value):
        for selector in (*range(0x4016,0x4024),0x405D,0x405F):self.call('func_1509BFB0',0,selector,value)
        if read(self.memory,read(self.memory,self.symbols['D_800D2E4C'])+0x15,1)&8:
            for selector in (0x4063,0x4064,0x4065):self.call('func_1509BFB0',0,selector,value)

    def main(self):
        m=self.memory;state=read(m,ACTOR+0x3D0)
        if read(m,state+0x102,1) and not read(m,state+0x104,1):
            self.call(source.LEAF,ACTOR,1)
            if read(m,ACTOR+0x2C)!=0x100 and not read(m,ACTOR+0x6C8):
                if self.call('func_15123934',ACTOR,0x80,0,0,3):
                    put(m,ACTOR+0x84,(read(m,ACTOR+0x84)|0x300400)&~6)
                    put(m,ACTOR+0x1B4,1,2);put(m,ACTOR+0x1E0,3,2);self.call('func_15124B18',ACTOR)
                for at,value in ((0x348,29.),(0x34C,29.),(0x374,200.),(0x190,-19.)):put(m,ACTOR+at,point.bits(value))
                if not read(m,ACTOR+0x3E8,1):
                    value=read(m,ACTOR+0x374)
                    if point.floating(point.mul(point.bits(.5),value))<point.floating(point.sub(read(m,ACTOR+0x370),value)):
                        self.call('func_15128774',ACTOR,read(m,ACTOR+0x3D0))
        else:
            put(m,state+7,255,1)
            if read(m,ACTOR+0x23E,1)==0x3B:
                self.call(source.LEAF,ACTOR,1)
                if read(m,ACTOR+0x2C)!=0x100 and not read(m,ACTOR+0x6C8):
                    if self.call('func_15123934',ACTOR,8,0,0,3):
                        put(m,ACTOR+0x84,(read(m,ACTOR+0x84)|0x300000)&~4)
                        put(m,ACTOR+0x1B4,1,2);put(m,ACTOR+0x1E0,3,2)
                    put(m,ACTOR+0x134,0)
                    for at,value in ((0x348,125.),(0x34C,125.),(0x374,220.),(0x190,30.)):put(m,ACTOR+at,point.bits(value))
            else:
                if read(m,ACTOR+0x2C) in (8,0x80) and not read(m,ACTOR+0x6C8):self.call('func_151239CC',ACTOR,3)
                if read(m,ACTOR+0x1B4,2)==1:
                    put(m,ACTOR+0x1B4,2,2);self.call('func_15124B18',ACTOR)
                self.call(source.LEAF,ACTOR,0)
        for selector,mask,limit in ((0x405A,0x80000000,0x9000),(0x405E,0x10000,0x9000),(0x405F,0x10,0x2000)):
            present=self.call('func_1509BE40',1,selector,6,limit);value=read(m,ACTOR+0x84)
            put(m,ACTOR+0x84,(value|mask if present else value&~mask)&0xffffffff)
        return self

class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args=(ACTOR,),pattern=0,mode=0,phase=0,entry=source.ENTRY,connected=None,symbols=None):
        self.io=[];self.targets=symbols or source.SYMBOLS;self.effect_mode=mode;self.event_count=0
        super().__init__(words,memory,args,[],phase,entry,connected);self.pattern=pattern

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def args(self,count):return tuple(self.r[4+i] if i<4 else read(self.memory,self.r[29]+i*4) for i in range(count))

    def record_call(self,target):
        name=next(n for n,v in self.targets.items() if v==target);canonical=source.SYMBOLS[name]
        args=self.args(COUNTS[canonical]);self.calls.append((target,args))
        self.observations.append((target,tuple(self.r[16:24]),self.r[29]))

    def hook(self,target):
        name=next(n for n,v in self.targets.items() if v==target);canonical=source.SYMBOLS[name]
        args=self.args(COUNTS[canonical]);result=0
        if canonical==EVENT:self.event_count+=1
        effects(self.memory,canonical,args,self.event_count,self.effect_mode,self.targets['D_800D2E4C'])
        if canonical==CHANGE:result=0x80000000 if self.pattern&8 else 0
        if canonical==QUERY:result=0x80000000 if self.pattern&(1<<((0x405A,0x405E,0x405F).index(args[1]))) else 0
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result

def state(m):return point.state(m),m.condition,m.io

class ActorStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth={n:list(struct.unpack_from('>%dI'%(size//4),cls.rom,rom)) for n,(_,rom,size) in source.TARGETS.items()}
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out));cls.original={}
        for name in source.TARGETS:
            cls.original[name]=assembly.ViewListSetupTests.original.__func__(context,'original-'+name,
                (cls.out/'before-phase_original').read_text(),name)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,pattern=0,mode=0,phase=0,connected=False,images=None,entry=source.ENTRY,symbols=None):
        expected=Reference(memory,pattern,mode,connected,symbols).main();machines=[]
        for index,words in enumerate(images or [self.truth[source.FUNCTION],*self.images[source.FUNCTION]]):
            code={LEAF+i*4:w for i,w in enumerate([self.truth[source.LEAF],*self.images[source.LEAF]][index])} if connected else None
            machines.append(Oracle(words,memory,pattern=pattern,mode=mode,phase=phase,entry=entry,connected=code,symbols=symbols).run())
        for m in machines:
            self.assertEqual((public(m.memory),m.calls),(public(expected.memory),expected.calls));self.assertEqual(state(m),state(machines[0]))
        return machines[0]

    def test_01_both_complete_words_bindings_pools_and_compiled_controls(self):
        self.assertEqual((self.row['frames'],self.row['new_guards'],self.row['unchanged_raw_padded_neighbors']),([40,40],0,7))
        count=bindings_count=0
        for name in source.TARGETS:
            raw,bindings=source.parts(self.obj,name)
            for i in range(len(raw)//4):
                wrong=bytearray(raw);wrong[i*4]^=1
                with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings,name)
                count+=1
            for at in bindings:
                wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'changed')]
                with self.assertRaises(ValueError):source.checked_parts(raw,wrong,name)
                bindings_count+=1
        before=(self.out/'before-fixed_owner').read_text()
        controls={'main-mask':{source.FUNCTION:source.SELECTED.replace('0x300400','0x300000'),source.LEAF:source.EVENTS},
            'leaf-count':{source.FUNCTION:source.SELECTED,source.LEAF:source.EVENTS.replace('i < 14','i < 13')},
            'leaf-mask':{source.FUNCTION:source.SELECTED,source.LEAF:source.EVENTS.replace('0x15] & 8','0x15] & 4')}}
        for label,bodies in controls.items():
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,bodies),'control-'+label)
            self.assertEqual(diag,'')
            name=source.FUNCTION if label=='main-mask' else source.LEAF
            with self.assertRaises(ValueError):source.checked_parts(*source.parts(obj,name),name)
        self.receipt('emission',**self.row,word_controls=count,binding_controls=bindings_count,compiled_controls=3)

    def test_02_actor_branches_signed_stage_nan_and_mutations(self):
        count=0;seen=set()
        for gate,category,kind,busy,pattern,phase in itertools.product(((0,0),(1,0),(1,1)),(0,0x3B),(0,8,0x80,0x100),(0,1),range(16),(0,8)):
            m=self.compare(fixture(gate,category,kind,busy,phase=phase),pattern,phase=phase);seen.update(m.visits);count+=1
        extra=0
        for stage,height,byte,phase in itertools.product((-32768,-1,0,1,2,32767),HEIGHTS,(0,255),(0,8)):
            for gate in ((0,0),(1,0)):
                m=self.compare(fixture(gate,kind=8,stage=stage,height=height,byte=byte,phase=phase),15,phase=phase)
                seen.update(m.visits);extra+=1
        mutations=0
        for gate,category,mode,phase,alias in itertools.product(((0,0),(1,0)),(0,0x3B),range(1,7),(0,8),(0,1)):
            m=self.compare(fixture(gate,category,kind=8,phase=phase,alias=alias),15,mode,phase)
            seen.update(m.visits);mutations+=1
        unreachable={source.ENTRY+i*4 for i in (70,115,180)}
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen,unreachable)
        self.receipt('guest',three_way_core_cases=count,boundary_cases=extra,mutation_alias_cases=mutations,
            reachable_main_words=186,three_unreachable_original_words_retained=True,NaNs_and_infinities=True,
            signed_halfword_stage=True,short_circuit_access_order=True,full_private_state=True)

    def test_03_event_all_flag_bytes_values_and_connected_main(self):
        count=0;seen=set()
        for flag,value,phase in itertools.product(range(256),(0,1,0xffffffff,0x80000000,0x7fffffff),(0,8)):
            memory=fixture(flag=flag,phase=phase);args=(0xfedcba98,value)
            expected=Reference(memory);expected.leaf(*args)
            machines=[Oracle(w,memory,args,phase=phase,entry=LEAF).run() for w in (self.truth[source.LEAF],*self.images[source.LEAF])]
            for m in machines:
                self.assertEqual((public(m.memory),m.calls),(public(expected.memory),expected.calls));self.assertEqual(state(m),state(machines[0]))
                self.assertEqual(read(m.memory,STACK+phase),args[0]);seen.update(m.visits)
            count+=1
        self.assertEqual(seen,set(range(LEAF,LEAF+192,4)));connected=0
        for gate,category,pattern,mode,phase in itertools.product(((0,0),(1,0)),(0,0x3B),(0,15),range(7),(0,8)):
            self.compare(fixture(gate,category,kind=8,phase=phase),pattern,mode,phase,connected=True);connected+=1
        self.receipt('events',three_way_leaf_cases=count,all_256_flag_bytes=True,full_width_values=True,
            all_48_leaf_words=True,unused_actor_home_full_width=True,connected_main_cases=connected,
            actual_main_to_leaf_instructions=True,event_provider_and_queries_are_scripted=True)

    def test_04_access_fault_prefixes(self):
        count=0
        for gate,category,mode,phase,connected in itertools.product(((0,0),(1,0)),(0,0x3B),(0,1),(0,8),(False,True)):
            memory=fixture(gate,category,kind=8,phase=phase)
            codes=[{LEAF+i*4:w for i,w in enumerate(words)} if connected else None
                for words in (self.truth[source.LEAF],*self.images[source.LEAF])]
            good=Oracle(self.truth[source.FUNCTION],memory,pattern=15,mode=mode,phase=phase,connected=codes[0]).run()
            for at in range(good.all_accesses):
                machines=[Oracle(w,memory,pattern=15,mode=mode,phase=phase,connected=code)
                    for w,code in zip((self.truth[source.FUNCTION],*self.images[source.FUNCTION]),codes)]
                for m in machines:
                    m.access_fault=at
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,at)
                for m in machines[1:]:self.assertEqual(state(m),state(machines[0]))
                count+=1
        self.receipt('faults',three_way_prefixes=count,actual_main_leaf_chain=True,no_observer_accesses=True,
            portable_C_fault_and_hardware_exception_parity_not_claimed=True)

    def test_05_independent_relocations(self):
        cases=links=0
        for index,main_entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            symbols=source.SYMBOLS if index==0 else {name:0x151A7FFC+i*0x20000+index*0x100000
                for i,name in enumerate(source.SYMBOLS)}
            if index:symbols={**symbols,'D_800D2E4C':0x80347FFC+index*0x100004}
            for name,(_,_,size) in source.TARGETS.items():
                entry=main_entry if name==source.FUNCTION else symbols[source.LEAF];images=[]
                for label,obj in (('original',self.original[name]),('raw',self.obj),('padded',self.padded)):
                    data,fs,rs=source.parse_object(obj);text,unknown=emit_function(data,fs[name],rs,name,symbols)
                    self.assertEqual(unknown,[]);stem=self.out/('rebase-%d-%s-%s'%(index,label,name));asm=stem.with_suffix('.s');asm.write_text(text)
                    compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,
                        *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                    images.append(list(struct.unpack_from('>%dI'%(size//4),source.projection.sections(elf)['.text'][1])));links+=1
                self.assertEqual(images,[images[0]]*3)
                for flag,phase,mode in itertools.product((0,8,255),(0,8),(0,1)):
                    memory=fixture(flag=flag,phase=phase,global_address=symbols['D_800D2E4C'])
                    if name==source.FUNCTION:self.compare(memory,15,mode,phase,images=images,entry=entry,symbols=symbols)
                    else:
                        expected=Reference(memory,mode=mode,symbols=symbols);expected.leaf(0,0xfedcba98)
                        machines=[Oracle(w,memory,(0,0xfedcba98),mode=mode,phase=phase,entry=entry,symbols=symbols).run() for w in images]
                        for m in machines:
                            self.assertEqual((public(m.memory),m.calls),(public(expected.memory),expected.calls));self.assertEqual(state(m),state(machines[0]))
                    cases+=1
        self.receipt('rebases',independent_links=links,three_way_cases=cases,bindings=20,global_signed_low_carries=True)

    def test_06_native32_and_effective_controls(self):
        head='#include <ultra64.h>\n'+source.TYPE+'void func_150F26A0(u8 *);\n'
        driver=self.out/'native-driver.c';driver.write_text(head+NATIVE)
        controls={'main-mask':source.SELECTED.replace('0x300400','0x300000')+'\n'+source.EVENTS,
            'leaf-count':source.SELECTED+'\n'+source.EVENTS.replace('i < 14','i < 13')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED+'\n'+source.EVENTS),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=256,profiles=['O2','O0'],UBSan=True,separately_typed_caller=True,
            effective_controls=4,complete_aligned_objects=True,scripted_provider_boundary=True,hardware_or_gameplay_not_claimed=True)

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
                    with self.assertRaisesRegex(ValueError,'Changed actor-state '+kind+' input'):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),effective_controls=count)

    def test_08_entire_first_image_and_checkpoint(self):
        from tools.experiments import game_actor_state_update_installation as install
        from tools.tests import actor_state_checkpoint as checkpoint
        from tools.match_progress import load_elf_functions
        from tools.tests.test_game_one_shot_timer_match import symbol_rows
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out);baseline=(out/'before-elf').read_bytes()
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        if not (out/'after-elf').exists():
            self.receipt('installation',installed=False,first_image_qualified=True);return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.AFTER[key])
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                target=out/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed actor-state checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
            wrong=bytearray(data);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong);count+=1
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        old,_,oa=load_elf_functions(str(out/'before-elf'),'mips-linux-gnu-objdump')
        new,_,na=load_elf_functions(str(out/'after-elf'),'mips-linux-gnu-objdump')
        self.assertEqual(oa,na);self.assertEqual(set(old),set(new))
        self.assertEqual(set(n for n in old if old[n]!=new[n]),set(source.TARGETS))
        old_symbols=[(n,(f[1],source.TARGETS[n][2] if n in source.TARGETS else f[2],*f[3:])) for _,n,f,_ in symbol_rows(baseline)]
        self.assertEqual(sorted(old_symbols),sorted((n,f[1:]) for _,n,f,_ in symbol_rows(expected['elf'])))
        owned={source.PATHS[k] for k in expected}
        for key,path in source.PATHS.items():
            if path not in owned:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())
        self.receipt('installation',installed=True,entire_first_image_exact=True,metadata_exclusions=0,
            checkpoint_controls=count,game_data=report,compared_function_bodies=len(old),only_target_pair_changed=True,
            all_function_addresses_unchanged=True,symbol_definitions_unchanged_except_two_extents=True,
            all_other_protected_inputs_unchanged=True)

NATIVE=r'''
typedef union {f32 align;u8 b[2048];} Actor;
static Actor actor,saved;static union {f32 align;u8 b[512];} state;
static u8 player[64];u8 *D_800D2E4C=player;
static int pattern,mode,error,events,changes,finishes,stops,heights,queries;
static u32 word(int at){return *(u32 *)(actor.b+at);}
static void set(int at,u32 v){*(u32 *)(actor.b+at)=v;}
void func_1509BFB0(s32 a,s32 selector,s32 value){
int expected=events<14?0x4016+events:events==14?0x405D:events==15?0x405F:0x4063+events-16;
if(a||selector!=expected||value!=mode)error=1;events++;
if(events==16&&pattern&128)player[21]^=8;}
s32 func_1509BE40(s32 a,s32 selector,s32 c,s32 limit){int i=queries++;
if(a!=1||c!=6||selector!=(i==0?0x405A:i==1?0x405E:0x405F)||limit!=(i==2?0x2000:0x9000))error=1;
return pattern&(1<<i)?(s32)0x80000000:0;}
s32 func_15123934(u8 *a,s32 kind,s32 c,s32 d,s32 e){changes++;
if(a!=actor.b||kind!=(state.b[0x102]?0x80:8)||c||d||e!=3)error=1;return pattern&8;}
void func_15124B18(u8 *a){if(a!=actor.b)error=1;finishes++;}
void func_151239CC(u8 *a,s32 b){if(a!=actor.b||b!=3)error=1;stops++;}
void func_15128774(u8 *a,u8 *b){if(a!=actor.b||b!=state.b)error=1;heights++;}
static int run(void){int i,active,special,busy,blocked,wantChanges,wantFinish,wantStop,wantHeight,wantEvents;u32 flags;
if(sizeof(void*)!=4)return 20;
for(pattern=0;pattern<256;pattern++){
for(i=0;i<2048;i++)actor.b[i]=0xA5;for(i=0;i<512;i++)state.b[i]=0;
active=!!(pattern&16);special=!!(pattern&32);busy=!!(pattern&64);blocked=0;
state.b[0x102]=active;actor.b[0x23E]=special?0x3B:0;actor.b[0x3E8]=0;
*(u8 **)(actor.b+0x3D0)=state.b;set(0x2C,8);set(0x6C8,busy);set(0x84,0x5A050017);
*(s16 *)(actor.b+0x1B4)=1;*(f32 *)(actor.b+0x370)=1000.f;player[21]=pattern&1?8:0;
error=events=changes=finishes=stops=heights=queries=0;mode=active||special; saved=actor;
func_150F26A0(actor.b);
wantChanges=(active||special)&&!busy&&!blocked;wantFinish=active?(wantChanges&&!!(pattern&8)):special?0:1;
wantStop=!active&&!special&&!busy;wantHeight=active&&!busy;wantEvents=16+((!!(pattern&1)^!!(pattern&128))?3:0);
if(error||events!=wantEvents||changes!=wantChanges||finishes!=wantFinish||stops!=wantStop||heights!=wantHeight||queries!=3)return 22;
flags=0x5A050017;
if(wantChanges&&(pattern&8))flags=(flags|(active?0x300400:0x300000))&~(active?6u:4u);
flags=pattern&1?flags|0x80000000:flags&0x7FFFFFFF;
flags=pattern&2?flags|0x10000:flags&0xFFFEFFFF;flags=pattern&4?flags|16:flags&~16u;
if(word(0x84)!=flags||state.b[7]!=(active?0:255))return 22;
if(wantChanges){if(*(f32 *)(actor.b+0x348)!=(active?29.f:125.f)||*(f32 *)(actor.b+0x374)!=(active?200.f:220.f))return 22;}
if(!active&&!special&&*(s16 *)(actor.b+0x1B4)!=2)return 22;
for(i=0;i<2048;i++)if(!((i>=0x84&&i<0x88)||(i>=0x134&&i<0x138)||(i>=0x190&&i<0x194)||(i>=0x1B4&&i<0x1B6)||(i>=0x1E0&&i<0x1E2)||(i>=0x348&&i<0x350)||(i>=0x374&&i<0x378))&&actor.b[i]!=saved.b[i])return 22;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
