"""Exact gate, ordered callback effects, live byte bounds and preserved caller ABI."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_gated_category_pass as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
LOG=0x60000
SYMBOLS=(source.GATE,source.COUNT,source.CONTEXT,source.FIRST,source.SECOND)
COUNTS=(0,1,2,127,128,254,255)
HEADER='''#include <ultra64.h>
extern u8 D_800C35EA[],D_800C363A[],D_800C3638;
s32 func_15022398(s32,s32);
s32 func_150222E0(s32,s32);
'''


def address(base,index):return (base+index)&0xFFFFFFFF


def fixture(index=0,gate=1,count=3,context=0xA5,phase=0,symbols=SYMBOLS):
    g,c,f,_,_=symbols
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x100,0x120)}
    for i in set((0,1,3,78,255,256,65537,-2,index)):
        for a in (address(g,i),address(c,i)):
            memory.update({a+j:0xA5 for j in range(-2,4)})
    for i in set((0,1,3,78,255,256,65537,-2,index)):
        put(memory,address(g,i),0,1);put(memory,address(c,i),0,1)
    put(memory,address(g,index),gate,1);put(memory,address(c,index),count,1)
    put(memory,f,context,1);put(memory,LOG,0);put(memory,LOG+4,0)
    return memory,(index&0xFFFFFFFF,)


def callback(memory,role,i,index,mode,symbols):
    g,c,f,_,_=symbols
    n=read(memory,LOG)+1
    if n>512:raise AssertionError('Callback count exceeded the byte-bound domain')
    h=((read(memory,LOG+4)*33)^(role<<24)^(i<<8)^index^read(memory,f,1))&0xFFFFFFFF
    put(memory,LOG,n);put(memory,LOG+4,h)
    if mode==1 and role==1:put(memory,address(c,index),0,1)
    elif mode==2 and role==2:put(memory,address(c,index),0,1)
    elif mode==3:put(memory,address(c,index),0 if role==1 else 4,1)
    elif mode==4 and role==2 and i==0:put(memory,address(c,index),3,1)
    elif mode==5 and role==1:
        put(memory,address(g,index),0,1);put(memory,f,0x7B,1)
    elif mode==6 and role==2:
        put(memory,f,0xFE,1);put(memory,address(c,index),2 if i==0 else 1,1)


def reference(initial,args,mode=0,symbols=SYMBOLS):
    memory=dict(initial);g,c,f,first,second=symbols;index=args[0];calls=[]
    if read(memory,address(g,index),1)==1:
        put(memory,f,0,1)
        i=0
        while i<read(memory,address(c,index),1):
            for role,target in ((1,first),(2,second)):
                calls.append((target,(i,index),read(memory,f,1)))
                callback(memory,role,i,index,mode,symbols)
            i+=1
        put(memory,f,1,1)
    return public(memory),calls


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x100<=a<STACK+0x120}


class PassOracle(base.PointProjectionOracle):
    def __init__(self,words,memory,args,mode=0,phase=0,symbols=SYMBOLS,entry=source.ENTRY,connected=None):
        self.pass_mode,self.pass_symbols=mode,symbols;self.forwarded=[]
        super().__init__(words,memory,args,[],phase,entry,connected)

    def record_call(self,target):
        if target==source.ENTRY:
            self.forwarded.append(self.arguments(1));return
        if target not in self.pass_symbols[3:]:raise AssertionError('Unexpected category callback '+hex(target))
        self.calls.append((target,self.arguments(2),read(self.memory,self.pass_symbols[2],1)))

    def hook(self,target):
        role=1 if target==self.pass_symbols[3] else 2
        i,index=self.calls[-1][1]
        callback(self.memory,role,i,index,self.pass_mode,self.pass_symbols)
        for j in range(4):put(self.memory,self.r[29]+j*4,0xB5000000+j)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xA5000000+read(self.memory,LOG)


def controls():
    body=source.SELECTED
    return {
        'truthy-gate':body.replace('D_800C35EA[index] == 1','D_800C35EA[index] != 0'),
        'cached-count':body.replace('    u8 *count;','    u8 *count;\n    s32 limit;').replace(
            '        for (i = 0; i < *count; i++) {','        limit = *count;\n        for (i = 0; i < limit; i++) {'),
        'mid-pair-recheck':body.replace('            func_150222E0(i, index);',
            '            if (i >= *count) break;\n            func_150222E0(i, index);'),
        'reversed-callbacks':body.replace('            func_15022398(i, index);\n            func_150222E0(i, index);',
            '            func_150222E0(i, index);\n            func_15022398(i, index);'),
        'no-clear':body.replace('        D_800C3638 = 0;\n',''),
        'no-final-set':body.replace('        D_800C3638 = 1;\n',''),
        'narrowed-index':body.replace('    if (D_800C35EA[index] == 1)',
            '    index = (u8)index;\n    if (D_800C35EA[index] == 1)'),
    }


NATIVE=HEADER+r'''
u8 D_800C35EA[512],D_800C363A[512],D_800C3638;
static u32 calls,hash,mode;
static void effect(u32 role,s32 i,s32 index){
 calls++;hash=hash*33u^(role<<24)^((u32)i<<8)^(u32)index^D_800C3638;
 if(mode==1&&role==1)D_800C363A[index]=0;
 else if(mode==2&&role==2)D_800C363A[index]=0;
 else if(mode==3)D_800C363A[index]=role==1?0:4;
 else if(mode==4&&role==2&&i==0)D_800C363A[index]=3;
 else if(mode==5&&role==1){D_800C35EA[index]=0;D_800C3638=0x7B;}
 else if(mode==6&&role==2){D_800C3638=0xFE;D_800C363A[index]=i==0?2:1;}}
s32 func_15022398(s32 i,s32 index){effect(1,i,index);return (s32)(0xA5000000u+calls);}
s32 func_150222E0(s32 i,s32 index){effect(2,i,index);return (s32)(0xA5000000u+calls);}
void func_15022848(s32);
static void reference(s32 index){s32 i=0;if(D_800C35EA[index]!=1)return;
 D_800C3638=0;while(i<D_800C363A[index]){effect(1,i,index);effect(2,i,index);i++;}D_800C3638=1;}
static void init(s32 index,u32 gate,u32 count,u32 m){u32 i;
 for(i=0;i<512;i++){D_800C35EA[i]=0;D_800C363A[i]=0;}
 D_800C35EA[index]=(u8)gate;D_800C363A[index]=(u8)count;D_800C3638=0xA5;
 mode=m;calls=hash=0;}
static u8 expectedGate[512],expectedCount[512];
static int check(s32 index,u32 gate,u32 count,u32 m){u32 i,wantedCalls,wantedHash;u8 wantedFlag;
 init(index,gate,count,m);reference(index);wantedCalls=calls;wantedHash=hash;wantedFlag=D_800C3638;
 for(i=0;i<512;i++){expectedGate[i]=D_800C35EA[i];expectedCount[i]=D_800C363A[i];}
 init(index,gate,count,m);func_15022848(index);
 if(calls!=wantedCalls||hash!=wantedHash||D_800C3638!=wantedFlag)return 23;
 for(i=0;i<512;i++)if(D_800C35EA[i]!=expectedGate[i]||D_800C363A[i]!=expectedCount[i])return 23;
 return 0;}
static int run(void){u32 g,c,m,j,n=0;int status;static const s32 indices[]={0,3,255,256};
 static const u32 counts[]={0,1,2,127,128,254,255};
 if(sizeof(void*)!=4||sizeof(s32)!=4)return 29;
 for(g=0;g<256;g++)for(c=0;c<7;c++)for(j=0;j<4;j++){
 status=check(indices[j],g,counts[c],0);if(status)return status;n++;}
 for(c=0;c<256;c++)for(m=0;m<7;m++)for(j=0;j<4;j++){
 status=check(indices[j],1,c,m);if(status)return status;n++;}
 return n==14336?0:29;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class GatedCategoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=struct.unpack_from('>39I',cls.rom,source.ROM)

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_all_gate_bytes_live_counts_order_and_saved_state(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(39,40,0,56))
        def cases():
            for gate,count,index,phase in itertools.product(range(256),(0,1,255),(0,3,256),(0,8)):
                yield index,gate,count,0,phase
            for count,mode,index,phase in itertools.product(COUNTS,range(7),(0,3,256),(0,8)):
                yield index,1,count,mode,phase
        count=0;seen=set()
        for index,gate,n,mode,phase in cases():
            memory,args=fixture(index,gate,n,phase=phase);expected,calls=reference(memory,args,mode)
            models=[PassOracle(w,memory,args,mode,phase).run() for w in (self.words,self.truth)]
            for m in models:
                self.assertEqual((public(m.memory),m.calls),(expected,calls))
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual((models[0].memory,models[0].r,models[0].f),(models[1].memory,models[1].r,models[1].f))
            seen.update(models[0].visits);count+=1
        self.assertEqual(count,4902)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+156,4))<=seen)
        extra=0
        for index,mode,context,phase in itertools.product((-2,78,65537),range(7),(0,1,255),(0,8)):
            memory,args=fixture(index,1,3,context,phase)
            expected,calls=reference(memory,args,mode)
            m=PassOracle(self.words,memory,args,mode,phase).run()
            self.assertEqual((public(m.memory),m.calls),(expected,calls));extra+=1
        self.receipt('guest',paired_cases=count,additional_word_address_alias_cases=extra,
            all_gate_bytes=True,all39_words_visited=True,helper_bodies_scripted=True)

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native-driver.c';harness.write_text(NATIVE)
        cases=[('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
            (n,'-O2',b,23) for n,b in controls().items()]
        for name,opt,body,status in cases:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(subprocess.run([str(exe)],timeout=30).returncode,status,name)
        self.receipt('native',cases_per_profile=14336,all_gate_and_count_bytes=True,UBSan=True,
            native_indices=[0,3,255,256],effective_controls=7)

    def test_03_compiled_guest_memory_controls(self):
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name)
            self.assertFalse(diagnostics)
            data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            for gate,n,index,mode in itertools.product((1,2),(0,1,3,255),(0,256),range(7)):
                memory,args=fixture(index,gate,n);expected,calls=reference(memory,args,mode)
                m=PassOracle(words,memory,args,mode).run()
                if public(m.memory)!=expected:break
            else:self.fail('Ineffective guest memory control: '+name)

    def test_04_independently_linked_original_C_rebases_and_global_aliases(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-category',
            source.raw_text(self.root/'conker/asm/49D30.s'),source.FUNCTION)
        raw,bindings=source.checked_object(self.obj);count=0
        placements=((source.ENTRY,SYMBOLS),(0x16218004,(0x12347FFC,0x800D8004,0x12348000,0x18227FFC,0x15528004)),
            (0x18FFF000,(0x12348000,0x800D7FFC,0x800D7FFC,0x15508004,0x17128004)))
        for i,(entry,symbols) in enumerate(placements):
            anchors=dict(zip(('D_800C35EA','D_800C363A','D_800C3638','func_15022398','func_150222E0'),symbols))
            text,unresolved=emit_function(raw,dict(value=0,size=len(raw)),bindings,source.FUNCTION,anchors)
            self.assertFalse(unresolved)
            path=self.out/('rebase-C-%d.s'%i);path.write_text(text);obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True)
            bodies=[]
            for label,target in (('original',original),('C',obj)):
                script=self.out/('rebase-%d-%s.ld'%(i,label));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(target)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>39I',sections(elf)['.text'][1])))
            self.assertEqual(*bodies)
            for n,mode,phase in itertools.product((0,2,255),range(7),(0,8)):
                memory,args=fixture(0,1,n,phase=phase,symbols=symbols)
                expected,calls=reference(memory,args,mode,symbols)
                for words in bodies:
                    m=PassOracle(words,memory,args,mode,phase,symbols,entry).run()
                    self.assertEqual((public(m.memory),m.calls),(expected,calls))
                count+=1
        self.receipt('rebases',independent_original_C_links=6,paired_sequences=count,
            ten_bindings=True,count_context_alias=True,not_a_portable_C_global_alias_claim=True)

    def test_05_all_target_access_fault_prefixes(self):
        count=states=0
        for gate,n,mode,phase in itertools.product((0,1,255),(0,1,3),(0,1,3,4),(0,8)):
            memory,args=fixture(3,gate,n,phase=phase)
            complete=PassOracle(self.words,memory,args,mode,phase).run()
            for fault in range(complete.all_accesses):
                pairs=[]
                for words in (self.words,self.truth):
                    m=PassOracle(words,memory,args,mode,phase);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault)
                    pairs.append((m.memory,m.r,m.f,m.events,m.calls,m.current_pc,m.delay_of,m.all_accesses))
                self.assertEqual(*pairs);count+=1
            states+=1
        self.receipt('fault-prefixes',states=states,equal_prefixes=count,callback_internals_excluded=True)

    def test_06_actual_bounded_caller_window_and_wide_index_delivery(self):
        entry=0x1501DA54
        offset=entry-0x15000000+0x2D4B0;caller=list(struct.unpack_from('>4I',self.rom,offset))
        elf=source.raw_read(self.root/'conker/build/conker.us.elf');at=source.elf_slot_offset(elf,entry,16)
        self.assertEqual(elf[at:at+16],self.rom[offset:offset+16])
        class Boundary(Exception):pass
        class Caller(PassOracle):
            def record_call(self,target):
                if target==0x15022754:raise Boundary
                super().record_call(target)
        connected=dict(zip(range(source.ENTRY,source.ENTRY+156,4),self.words));count=0
        for n,mode,index,phase in itertools.product((0,2,255),range(7),(0,3,256),(0,8)):
            memory,args=fixture(index,1,n,phase=phase);expected,calls=reference(memory,args,mode)
            m=Caller(caller,memory,args,mode,phase,entry=entry,connected=connected)
            m.r[21]=args[0];m.r[4]=0x12345678
            with self.assertRaises(Boundary):m.run()
            self.assertEqual(m.forwarded,[args]);self.assertEqual((public(m.memory),m.calls),(expected,calls))
            count+=1
        self.receipt('caller-window',sequences=count,actual_call_and_delay=True,whole_parent_not_executed=True,
            helper_bodies_remain_production_stubs=True)

    def test_07_words_bindings_inputs_and_actual_image(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION]
        raw,bindings=source.checked_object(self.obj)
        for i in range(39):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
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
