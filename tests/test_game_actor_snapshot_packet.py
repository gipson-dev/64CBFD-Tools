"""Snapshot lifetimes, complete inherited bytes, real copy and bounded callers."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_snapshot_packet as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
ACTOR,CREATED=0x21000,0x25000
PADDING=(5,6,7,25,26,27)
FACTORY_ARGS=(60,0xFFFFFFFF,14,1,9,28,255,0)
CALLER=0x1506FF50


def fixture(slot=255,value=65535,seed=0,phase=0,high=0,alias=0,coefficient=0x3ECCCCCD):
    actor=(ACTOR+(0x80000000 if high else 0)) if not alias else STACK+phase-(0x5A if alias==1 else 0x5C)
    memory={STACK+i:(i*17+seed*31+0xA5)&255 for i in range(-0x180,0x180)}
    for start,size in ((actor-32,0x100),(CREATED-32,0x120)):
        for i in range(size):memory.setdefault(start+i,(i*13+seed*11+0xA5)&255)
    put(memory,actor+0x3B,slot,1);put(memory,actor+0x84,value,2)
    put(memory,source.COEFFICIENT,coefficient)
    return memory,(actor,)


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x180<=a<STACK+0x180}


def effects(memory,actor,mode,role):
    if mode==role:
        put(memory,actor+0x3B,42,1);put(memory,actor+0x84,0x1234,2)
        put(memory,source.COEFFICIENT,0x3F800000)


def reference(initial,args,phase=0,outcome=1,selector=0x123456AB,mode=0,coefficient=source.COEFFICIENT):
    memory=dict(initial);actor=args[0];packet=STACK+phase-0x20
    # The retail prologue can itself change an explicitly stack-aliased input.
    put(memory,STACK+phase-0x24,0xDEAD0000)
    put(memory,packet,actor)
    slot=read(memory,actor+0x3B,1);scale=read(memory,coefficient)
    put(memory,packet+4,slot,1)
    value=read(memory,actor+0x84,2)
    for offset,data in ((16,scale),(8,value),(12,0),(20,0x40400000)):put(memory,packet+offset,data)
    effects(memory,actor,mode,1)
    put(memory,packet+24,selector,1)
    effects(memory,actor,mode,2)
    if outcome:
        for i in range(28):put(memory,CREATED+outcome-1+40+i,read(memory,packet+i,1),1)
    return public(memory),bytes(read(memory,packet+i,1) for i in range(28))


class PacketOracle(base.PointProjectionOracle):
    def __init__(self,words,memory,args,copy,phase=0,outcome=1,selector=0x123456AB,mode=0,
            entry=source.ENTRY,connected=None,provider=source.PROVIDER,allocator=source.ALLOCATOR,
            memcpy=source.MEMCPY):
        self.actor,self.outcome,self.selector,self.effect_mode=args[0],outcome,selector,mode
        self.provider,self.allocator,self.memcpy=provider,allocator,memcpy
        code=dict(zip(range(memcpy,memcpy+44,4),copy));code.update(connected or {})
        self.packets,self.copies=[],[]
        super().__init__(words,memory,args,[],phase,entry,code)

    def record_call(self,target):
        if target==source.ENTRY:
            args=self.arguments(1)
        elif target==self.provider:args=()
        elif target==self.allocator:
            args=self.arguments(8)
            self.packets.append(bytes(read(self.memory,self.r[29]+0x28+i,1) for i in range(28)))
        elif target==self.memcpy:
            args=self.arguments(3)
            self.copies.append(bytes(read(self.memory,args[1]+i,1) for i in range(args[2])))
        else:raise AssertionError('Unexpected snapshot helper '+hex(target))
        self.calls.append((target,args))

    def hook(self,target):
        if target==self.provider:
            effects(self.memory,self.actor,self.effect_mode,1);result=self.selector
        elif target==self.allocator:
            effects(self.memory,self.actor,self.effect_mode,2)
            result=CREATED+self.outcome-1 if self.outcome else 0
        else:raise AssertionError('Actual byte copy must execute')
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result&0xFFFFFFFF


def controls():
    body=source.SELECTED
    fields='    packet.slot = actor[0x3B];\n    packet.value = *(u16 *)(actor + 0x84);\n'
    live=body.replace(fields,'').replace('    packet.selector = func_151D8E20();',
        '    packet.selector = func_151D8E20();\n'+fields.rstrip())
    scale='    packet.scale = D_800A9014;\n'
    return {'signed-half':body.replace('*(u16 *)','*(s16 *)'),
        'live-fields':live,'live-scale':body.replace(scale,'').replace(
            '    packet.selector = func_151D8E20();','    packet.selector = func_151D8E20();\n'+scale.rstrip()),
        'short-copy':body.replace('&packet, 0x1C','&packet, 0x18')}


ZERO_PADDING=source.SELECTED.replace('    packet.actor = actor;',
    ''.join('    ((u8 *)&packet)[%d] = 0;\n'%i for i in PADDING)+'    packet.actor = actor;')

NATIVE=r'''#include <ultra64.h>
struct Actor { u8 pad0[0x3B],slot,pad3C[0x48];u16 value; };
static struct Actor actor;
static u8 output[128],expected[128];
static u32 outcome,mode,selector,misaligned,calls,copies;
f32 D_800A9014;
void func_151AB930(u8*);
static void word(u8*p,u32 v){u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(i*8));}
static void change(u32 role){if(mode==role){actor.slot=42;actor.value=0x1234;D_800A9014=1.0f;}}
u8 func_151D8E20(void){calls++;change(1);return (u8)selector;}
void *func_151491F4(s16 a,s8 b,s8 c,u8 d,u8 e,s32 f,u8 g,s32 h){
 if(a!=60||b!=-1||c!=14||d!=1||e!=9||f!=28||g!=255||h!=0)calls+=100;
 calls++;change(2);return outcome?output+misaligned:0;}
void *memcpy(void*d,const void*s,u32 n){u32 i;u8*o=d;const u8*p=s;
 copies++;for(i=0;i<n;i++)o[i]=p[i];return d;}
static int run(void){u32 a,b,c,o,m,k,i,at,total=0;
 static const u32 bytes[]={0,1,127,128,254,255},halves[]={0,1,32767,32768,65534,65535};
 if(sizeof(void*)!=4||__builtin_offsetof(struct Actor,value)!=0x84)return 29;
 for(a=0;a<6;a++)for(b=0;b<6;b++)for(c=0;c<6;c++)for(o=0;o<2;o++)for(m=0;m<3;m++)for(k=0;k<2;k++){
 actor.slot=(u8)bytes[a];actor.value=(u16)halves[b];D_800A9014=0.4f;
 selector=bytes[c];outcome=o;mode=m;misaligned=k;calls=copies=0;
 for(i=0;i<128;i++)output[i]=expected[i]=(u8)(i*13+0xA5);
 at=40+k;
 if(o){word(expected+at,(u32)&actor);expected[at+4]=(u8)bytes[a];word(expected+at+8,halves[b]);
 word(expected+at+12,0);word(expected+at+16,0x3ECCCCCDu);word(expected+at+20,0x40400000u);expected[at+24]=(u8)selector;}
 func_151AB930((u8*)&actor);
 if(calls!=2||copies!=o)return 23;
 for(i=0;i<128;i++){
 if(o&&((i>=at+5&&i<at+8)||(i>=at+25&&i<at+28)))continue;
 if(output[i]!=expected[i])return 23;}
 total++;}return total==2592?0:29;}
void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class SnapshotPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=struct.unpack_from('>38I',cls.rom,source.ROM)
        cls.copy=list(struct.unpack_from('>11I',cls.rom,0x22EC0))

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_complete_guest_fields_lifetimes_failure_and_six_inherited_bytes(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(38,72,0,40))
        seen=set();padding=set();count=0
        for slot,value,selector,outcome,mode,phase,high in itertools.product(
                (0,1,127,128,255),(0,1,32767,32768,65535),(0,1,128,255,0x123456AB),
                (0,1,2,4),range(3),(0,8),(0,1)):
            memory,args=fixture(slot,value,count%7,phase,high)
            expected,packet=reference(memory,args,phase,outcome,selector,mode)
            models=[PacketOracle(w,memory,args,self.copy,phase,outcome,selector,mode).run() for w in (self.words,self.truth)]
            for m in models:
                self.assertEqual(public(m.memory),expected)
                self.assertEqual(m.packets,[packet]);self.assertEqual(len(m.copies),bool(outcome))
                self.assertEqual(m.calls[:2],[(source.PROVIDER,()),(source.ALLOCATOR,FACTORY_ARGS)])
                if outcome:self.assertEqual(m.copies,[packet])
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual((models[0].memory,models[0].r,models[0].f),(models[1].memory,models[1].r,models[1].f))
            seen.update(models[0].visits);padding.add(bytes(packet[i] for i in PADDING));count+=1
        self.assertEqual(count,6000)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+152,4))<=seen)
        self.assertTrue(set(range(source.MEMCPY,source.MEMCPY+44,4))<=seen)
        self.assertGreater(len(padding),1)
        # These are explicit guest stack-alias/bit-copy probes, not native C padding guarantees.
        extra=0
        for phase,alias,coefficient,mode in itertools.product((0,8),(0,1,2),
                (0,0x80000000,0x3ECCCCCD,0x7F800000,0x7FC12345),range(3)):
            if alias==2 and mode:continue  # Mutating this input would overwrite the saved return address.
            memory,args=fixture(128,0xFEDC,3,phase,alias=alias,coefficient=coefficient)
            expected,packet=reference(memory,args,phase,1,0xFFFFFFAB,mode)
            m=PacketOracle(self.words,memory,args,self.copy,phase,1,0xFFFFFFAB,mode).run()
            self.assertEqual((public(m.memory),m.copies),(expected,[packet]));extra+=1
        self.receipt('guest',paired_cases=count,extra_stack_alias_bitcopy_cases=extra,
            six_padding_bytes_included=True,actual_memcpy_words=11,all38_target_words_visited=True)

    def test_02_native32_fields_controls_and_explicit_padding_limit(self):
        harness=self.out/'native-driver.c';harness.write_text(NATIVE)
        cases=[('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0),
            ('zero-padding','-O2',ZERO_PADDING,0)]+[(n,'-O2',b,23) for n,b in controls().items()]
        for label,opt,body,status in cases:
            unit=self.out/('native-'+label+'.c');unit.write_text('#include <ultra64.h>\n'+body)
            exe=unit.with_suffix('')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(subprocess.run([str(exe)],timeout=30).returncode,status,label)
        self.receipt('native',cases_per_profile=2592,O2_O0_UBSan=True,effective_controls=4,
            six_padding_bytes_excluded_only=True,zero_padding_also_passes_native=True)

    def test_03_compiled_guest_controls_include_zero_padding(self):
        with source.historical_view(self.root,self.out):
            for name,body in {**controls(),'zero-padding':ZERO_PADDING,'shifted-home':source.INITIAL}.items():
                _,words,row=source.measure(self.root,self.out,'negative-'+name,body)
                self.assertEqual(row['diagnostics'],'')
                memory,args=fixture(255,65535,2)
                expected,packet=reference(memory,args,mode=1)
                m=PacketOracle(words,memory,args,self.copy,mode=1).run()
                self.assertNotEqual(public(m.memory),expected,name)

    def test_04_rebased_independent_original_and_C_links(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-snapshot',
            source.raw_text(self.root/'conker/asm/1D6E80.s'),source.FUNCTION)
        raw,bindings=source.checked_object(self.obj);count=0
        for i,(entry,coefficient,provider,allocator,copy) in enumerate((
                (0x15507FFC,0x12347FFC,0x17127FFC,0x18218004,0x15518004),
                (0x16218004,0x12348000,0x18227FFC,0x15528004,0x17117FFC),
                (0x18FFF000,0x800A8000,0x15508004,0x17128004,0x18228004))):
            anchors=dict(D_800A9014=coefficient,func_151D8E20=provider,func_151491F4=allocator,memcpy=copy)
            text,unresolved=emit_function(raw,dict(value=0,size=len(raw)),bindings,source.FUNCTION,anchors)
            self.assertFalse(unresolved)
            path=self.out/('rebase-C-%d.s'%i);path.write_text(text);obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True)
            bodies=[]
            for label,target in (('original',original),('C',obj)):
                script=self.out/('rebase-%d-%s.ld'%(i,label))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(target)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>38I',sections(elf)['.text'][1])))
            self.assertEqual(*bodies)
            for outcome,mode,phase in itertools.product((0,1,2),range(3),(0,8)):
                memory,args=fixture(128,0xFEDC,4,phase);put(memory,coefficient,0x3ECCCCCD)
                expected,packet=reference(memory,args,phase,outcome,mode=mode,coefficient=coefficient)
                for words in bodies:
                    m=PacketOracle(words,memory,args,self.copy,phase,outcome,mode=mode,
                        entry=entry,provider=provider,allocator=allocator,memcpy=copy).run()
                    self.assertEqual((public(m.memory),m.packets),(expected,[packet]))
                count+=1
        self.receipt('rebases',independent_original_C_links=6,paired_sequences=count,five_bindings=True)

    def test_05_actual_caller_provider_and_allocator_wrapper(self):
        spans=((CALLER,40),(source.PROVIDER,76),(source.ALLOCATOR,112),(source.MEMCPY,44))
        elf=source.raw_read(self.root/'conker/build/conker.us.elf');connected={}
        for address,size in spans:
            offset=address-0x15000000+0x2D4B0 if address>=0x15000000 else address-0x10000000
            raw=self.rom[offset:offset+size];at=source.elf_slot_offset(elf,address,size)
            self.assertEqual(elf[at:at+size],raw)
            connected.update(zip(range(address,address+size,4),struct.unpack('>%dI'%(size//4),raw)))
        class Chain(PacketOracle):
            def record_call(self,target):
                if target==0x150A29C8:
                    self.calls.append((target,self.arguments(2)))
                elif target==0x15149130:
                    self.calls.append((target,self.arguments(9)))
                else:super().record_call(target)
            def hook(self,target):
                if target==0x150A29C8:
                    self.assert_query=self.arguments(2);result=self.query_result
                    effects(self.memory,self.actor,1,1)
                elif target==0x15149130:result=CREATED if self.outcome else 0
                else:raise AssertionError('Actual helper unexpectedly opaque '+hex(target))
                for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
                self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result
        count=0
        for gate,query,selector,outcome,phase in itertools.product((0,1),(0,1),(0,128,255),(0,1),(0,8)):
            memory,args=fixture(255,65535,3,phase)
            put(memory,0x800D154C,args[0]);put(memory,0x800BE9F0,gate);put(memory,0x800E0A10,selector,1)
            code=dict(connected);code.update(zip(range(source.ENTRY,source.ENTRY+152,4),self.words))
            # The ROM offset follows the same explicit Game mapping used above.
            caller=list(struct.unpack_from('>10I',self.rom,CALLER-0x15000000+0x2D4B0))
            m=Chain(caller,memory,args,self.copy,phase,outcome,entry=CALLER,connected=code)
            m.query_result=query;m.run()
            wanted=10 if gate==0 and query==0 else selector
            packet=bytearray(read(memory,STACK+phase-0x38+i,1) for i in range(28))
            for offset,value in ((0,args[0]),(8,65535),(12,0),(16,0x3ECCCCCD),(20,0x40400000)):
                struct.pack_into('>I',packet,offset,value)
            packet[4],packet[24]=255,wanted
            self.assertEqual(len([t for t,a in m.calls if t==0x150A29C8]),int(gate==0))
            self.assertIn((source.ENTRY,args),m.calls)
            self.assertIn((0x15149130,(60,0xFFFFFFFF,14,0xFFFFFFFF,1,9,28,255,0)),m.calls)
            self.assertEqual(m.packets,[bytes(packet)])
            self.assertEqual(len(m.copies),outcome)
            if outcome:self.assertEqual(m.copies,[m.packets[0]])
            if not gate:self.assertEqual(m.assert_query,(0,28))
            for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            count+=1
        self.receipt('actual-chain',sequences=count,caller_words=10,provider_words=19,wrapper_words=28,
            memcpy_words=11,inner_query_and_allocator_are_scripted=True,not_full_gameplay=True)

    def test_06_all_target_and_copy_fault_prefixes(self):
        count=states=0
        for outcome,mode,phase,seed in itertools.product((0,1,2),range(3),(0,8),(0,3)):
            memory,args=fixture(128,0xFFFF,seed,phase)
            complete=PacketOracle(self.words,memory,args,self.copy,phase,outcome,mode=mode).run()
            for fault in range(complete.all_accesses):
                pairs=[]
                for words in (self.words,self.truth):
                    m=PacketOracle(words,memory,args,self.copy,phase,outcome,mode=mode);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault)
                    pairs.append((m.memory,m.r,m.f,m.events,m.calls,m.current_pc,m.delay_of,m.all_accesses))
                self.assertEqual(*pairs);count+=1
            states+=1
        self.receipt('fault-prefixes',states=states,equal_prefixes=count,includes_actual_memcpy=True)

    def test_07_words_bindings_inputs_and_actual_image(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION]
        raw,bindings=source.checked_object(self.obj)
        for i in range(38):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with source.historical_view(self.root,self.out):
            values=source.freeze(self.root,self.out)
            caller=source.qualify_caller(self.root,self.out,values)
            self.assertEqual(caller['functions'],328)
            self.assertTrue(caller['whole_object_identical'])
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
