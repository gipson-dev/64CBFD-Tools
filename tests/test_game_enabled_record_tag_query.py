"""Read-only query results, exact access order and closed register normalization."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_enabled_record_tag_query as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
FLAGS,DESC,RECORD,ALT_FLAGS,ALT_DESC,ALT_RECORD=0x20000,0x22000,0x26000,0x28000,0x2A000,0x2E000
SYMBOLS=(source.COUNT,source.ENABLED,source.DESCRIPTORS,source.RECORDS)
HEADER='''#include <ultra64.h>
extern u8 D_800C363A[];
extern u16 *D_800C35C8[];
extern u8 *D_800C35F0[],*D_800DBEF4;
'''


def address(a,b):return (a+b)&0xFFFFFFFF


def fixture(n=3,pattern=1,match=3,tag=128,recordIndex=0,category=0,phase=0,high=0,symbols=SYMBOLS):
    shift=0x80000000 if high else 0
    f,d,r,af,ad,ar=(x+shift for x in (FLAGS,DESC,RECORD,ALT_FLAGS,ALT_DESC,ALT_RECORD))
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x100,0x200)}
    for p,size in ((f,512),(d,2048),(r,640),(af,512),(ad,2048),(ar,640)):
        memory.update({p+i:0xA5 for i in range(size)})
    c,e,descriptors,records=symbols
    for i in range(4):
        put(memory,c+i,n,1);put(memory,e+i*4,f);put(memory,descriptors+i*4,d)
    put(memory,records,r)
    for i in range(256):
        enabled=(0,1,(1 if i%2 else 0),0x8000)[pattern]
        put(memory,f+i*2,enabled,2);put(memory,af+i*2,0,2)
        put(memory,d+i*8+2,tag^255,1);put(memory,ad+i*8+2,tag if i==1 else tag^255,1)
    for i in range(4):
        put(memory,r+i*160+0x72,(tag+i*37+1)&255,1)
        put(memory,ar+i*160+0x72,tag^255,1)
    put(memory,r+recordIndex*160+0x72,tag,1)
    pos={0:None,1:0,2:n//2,3:n-1}[match]
    if pos is not None and n:put(memory,d+pos*8+2,tag,1)
    return memory,(recordIndex,category)


def effect(memory,ordinal,mode,symbols,args,high=0):
    shift=0x80000000 if high else 0;c,e,d,r=symbols;category=args[1]
    if ordinal==3:
        if mode==1:put(memory,c+category,0,1)
        elif mode==2:put(memory,e+category*4,ALT_FLAGS+shift)
        elif mode==3:put(memory,d+category*4,ALT_DESC+shift)
    if ordinal==7 and mode==4:put(memory,r,ALT_RECORD+shift)


def reference(initial,args,symbols=SYMBOLS,mode=0,high=0):
    memory=dict(initial);io=[];recordIndex,category=args;c,e,d,r=symbols
    def get(a,size):
        v=read(memory,a,size);io.append((a,size,v));effect(memory,len(io),mode,symbols,args,high);return v
    n=get(address(c,category),1)
    if n:
        enabled=get(address(e,(category*4)&0xFFFFFFFF),4)
        for i in range(n):
            if get(address(enabled,i*2),2):
                descriptor=get(address(d,(category*4)&0xFFFFFFFF),4)
                records=get(r,4)
                tag=get(address(descriptor,i*8+2),1)
                actual=get(address(records,((recordIndex*160)&0xFFFFFFFF)+0x72),1)
                if tag==actual:return memory,1,io
    return memory,0,io


class QueryOracle(base.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,query_entry=None,symbols=SYMBOLS,
            mode=0,high=0,connected=None):
        self.query_entry=source.ENTRY if query_entry is None else query_entry
        self.query_symbols,self.query_mode,self.query_high=symbols,mode,high
        self.query_args=tuple(args);self.io=[];self.forwarded=[];self.external=[]
        super().__init__(words,memory,args,[],phase,entry,connected)

    def get(self,a,size):
        value=super().get(a,size)
        if self.own_instruction and self.query_entry<=self.current_pc<self.query_entry+156:
            self.io.append((a,size,value))
            effect(self.memory,len(self.io),self.query_mode,self.query_symbols,self.query_args,self.query_high)
        return value

    def record_call(self,target):
        if target==self.query_entry:
            self.forwarded.append(self.arguments(2));return
        if target not in (0x151162D4,0x1511A494):raise AssertionError('Unexpected query caller helper '+hex(target))
        self.external.append((target,self.arguments(1 if target==0x151162D4 else 3)))

    def hook(self,target):
        if target not in (0x151162D4,0x1511A494):raise AssertionError('Query must execute its actual body')
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0


def controls():
    body=source.SELECTED
    return {'only-enable-one':body.replace('*enabled != 0','*enabled == 1'),
        'ignore-enables':body.replace('*enabled != 0','1'),
        'descriptor-stride':body.replace('i * 8 + 2','i * 4 + 2'),
        'descriptor-field':body.replace('i * 8 + 2','i * 8 + 3'),
        'record-stride':body.replace('u8 (*)[0xA0]','u8 (*)[0x9C]'),
        'record-field':body.replace('[recordIndex][0x72]','[recordIndex][0x73]'),
        'false-positive':body.replace('    return 0;','    return 1;')}


NATIVE=HEADER+r'''
u8 D_800C363A[4],*D_800C35F0[4],*D_800DBEF4;
u16 *D_800C35C8[4];
static u16 flags[256];static u8 descriptors[256*8],records[4][160];
s32 func_15022B08(s32,s32);
static u32 hash(const void*p,u32 size,u32 h){const u8*b=p;u32 i;for(i=0;i<size;i++)h=(h^b[i])*16777619u;return h;}
static u32 image(void){u32 h=hash(flags,sizeof flags,2166136261u);h=hash(descriptors,sizeof descriptors,h);
 h=hash(records,sizeof records,h);h=hash(D_800C363A,sizeof D_800C363A,h);
 h=hash(D_800C35C8,sizeof D_800C35C8,h);h=hash(D_800C35F0,sizeof D_800C35F0,h);
 return hash(&D_800DBEF4,sizeof D_800DBEF4,h);}
static int check(u32 n,u32 pattern,u32 match,u32 layout){u32 i,k,before,tag=(n+layout*73)&255;int expected=0,actual;
 for(i=0;i<256;i++){flags[i]=pattern==0?0:pattern==1?1:pattern==2?(i&1):0x8000;
 for(k=0;k<8;k++)descriptors[i*8+k]=0xA5;descriptors[i*8+2]=(u8)(tag^255);}
 for(i=0;i<4;i++){for(k=0;k<160;k++)records[i][k]=0xA5;records[i][0x72]=(u8)(tag+i*37+1);
 D_800C363A[i]=(u8)n;D_800C35C8[i]=flags;D_800C35F0[i]=descriptors;}
 records[layout][0x72]=(u8)tag;D_800DBEF4=records[0];
 if(n&&match)descriptors[(match==1?0:match==2?n/2:n-1)*8+2]=(u8)tag;
 for(i=0;i<n;i++)if(flags[i]&&descriptors[i*8+2]==records[layout][0x72]){expected=1;break;}
 before=image();actual=func_15022B08((s32)layout,(s32)layout);if(actual!=expected||image()!=before)return 23;
 for(i=0;i<256;i++)if(flags[i]!=(pattern==0?0:pattern==1?1:pattern==2?(i&1):0x8000))return 23;
 return 0;}
static int run(void){u32 n,p,m,l,total=0;int status;if(sizeof(void*)!=4||sizeof(s32)!=4)return 29;
 for(n=0;n<256;n++)for(p=0;p<4;p++)for(m=0;m<4;m++)for(l=0;l<4;l++){
 status=check(n,p,m,l);if(status)return status;total++;}return total==16384?0:29;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class RecordTagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=list(struct.unpack_from('>39I',cls.rom,source.ROM));cls.normal=source.normalized(cls.raw)

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_results_exact_read_order_and_complete_slot(self):
        self.assertEqual((self.row['words'],self.row['differences'],self.row['neighbors']),(39,9,56))
        self.assertEqual(self.normal,self.truth);count=0;seen=set()
        for n,pattern,match,tag,layout,phase in itertools.product((0,1,2,3,127,128,255),range(4),range(4),
                (0,127,128,255),range(3),(0,8)):
            memory,args=fixture(n,pattern,match,tag,layout,layout,phase)
            expected,result,io=reference(memory,args)
            for words in (self.raw,self.normal,self.truth):
                m=QueryOracle(words,memory,args,phase).run()
                self.assertEqual((m.memory,m.r[2],m.io),(expected,result,io))
                self.assertFalse(m.calls)
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
                seen.update(m.visits)
            count+=1
        self.assertEqual(count,2688)
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+156,4))-seen,{source.ENTRY+128})
        self.assertEqual((self.raw[32],self.normal[32],self.truth[32]),(0x24420001,)*3)
        self.receipt('guest',three_way_cases=count,reachable_words=38,dead_increment_bytes_checked=True,
            exact_read_traces_and_boolean_results=True,no_writes_or_calls=True)

    def test_02_native32_O2_O0_UBSan_and_result_changing_controls(self):
        harness=self.out/'native-driver.c';harness.write_text(NATIVE)
        cases=[('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
            (n,'-O2',b,23) for n,b in controls().items()]
        for name,opt,body,status in cases:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(subprocess.run([str(exe)],timeout=60).returncode,status,name)
        self.receipt('native',cases_per_profile=16384,all_count_and_tag_bytes=True,UBSan=True,
            native_record_and_category_indices=[0,1,2,3],effective_result_controls=7,
            flat_descriptor_byte_buffer=True,full_input_image_read_only=True)

    def test_03_emitted_snapshot_and_pointer_reload_lifetimes_and_guest_controls(self):
        count=0
        for mode,high,phase in itertools.product(range(5),(0,1),(0,8)):
            memory,args=fixture(4,1,0,128,1,1,phase,high)
            expected,result,io=reference(memory,args,mode=mode,high=high)
            for words in (self.raw,self.normal,self.truth):
                m=QueryOracle(words,memory,args,phase,mode=mode,high=high).run()
                self.assertEqual((m.memory,m.r[2],m.io),(expected,result,io))
            count+=1
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name)
            self.assertFalse(diagnostics)
            data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            for pattern,match,layout in itertools.product((0,1,3),range(4),range(3)):
                memory,args=fixture(3,pattern,match,128,layout,layout)
                _,wanted,_=reference(memory,args)
                m=QueryOracle(words,memory,args).run()
                if m.r[2]!=wanted:break
            else:self.fail('Ineffective guest return control: '+name)
        self.receipt('lifetimes',three_way_sequences=count,scripted_read_boundaries=True,
            snapshot_count_and_enabled_pointer=True,repeated_descriptor_and_record_bases=True,
            not_native_volatile_or_interrupt_semantics=True,effective_guest_return_controls=7)

    def test_04_original_raw_and_actual_padded_links_rebase_all_eight_bindings(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-tag-query',
            source.raw_text(self.root/'conker/asm/49D30.s'),source.FUNCTION)
        raw,bindings=source.checked_object(self.obj)
        text,functions,rel=source.parse_object(self.padded);f=functions[source.FUNCTION]
        normalized_raw=text[f['value']:f['value']+156]
        normalized_bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+156}
        count=0
        placements=((source.ENTRY,SYMBOLS),(0x16218004,(0x12347FFC,0x12348004,0x800C8000,0x800D7FFC)),
            (0x18FFF000,(0x800C8004,0x800C7FFC,0x12348000,0x12347FFC)))
        for i,(entry,symbols) in enumerate(placements):
            anchors=dict(zip(('D_800C363A','D_800C35C8','D_800C35F0','D_800DBEF4'),symbols));objects=[('original',original)]
            for name,body,binding in (('raw',raw,bindings),('normalized',normalized_raw,normalized_bindings)):
                asm,unresolved=emit_function(body,dict(value=0,size=156),binding,source.FUNCTION,anchors)
                self.assertFalse(unresolved)
                path=self.out/('rebase-%d-%s.s'%(i,name));path.write_text(asm);obj=path.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True)
                objects.append((name,obj))
            bodies={}
            for name,obj in objects:
                script=self.out/('rebase-%d-%s.ld'%(i,name));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                bodies[name]=list(struct.unpack_from('>39I',sections(elf)['.text'][1]))
            self.assertEqual(bodies['original'],bodies['normalized'])
            self.assertEqual(source.normalized(bodies['raw']),bodies['original'])
            for n,pattern,match,layout,phase in itertools.product((0,2,8),(1,3),(0,3),(0,3),(0,8)):
                memory,args=fixture(n,pattern,match,128,layout,layout,phase,symbols=symbols)
                expected,result,io=reference(memory,args,symbols)
                for words in bodies.values():
                    m=QueryOracle(words,memory,args,phase,entry,entry,symbols).run()
                    self.assertEqual((m.memory,m.r[2],m.io),(expected,result,io))
                count+=1
        self.receipt('rebases',independent_links=9,three_way_cases=count,eight_bindings=True,three_LO16_moves_checked=True)

    def test_05_raw_access_prefixes_and_exact_normalized_fault_state(self):
        count=states=0
        for n,pattern,match,layout,phase in itertools.product((0,1,3),(0,1,3),(0,3),(0,3),(0,8)):
            memory,args=fixture(n,pattern,match,128,layout,layout,phase)
            complete=QueryOracle(self.normal,memory,args,phase).run()
            for fault in range(complete.all_accesses):
                models=[]
                for words in (self.raw,self.normal,self.truth):
                    m=QueryOracle(words,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);models.append(m)
                a,b,c=models
                self.assertEqual((a.memory,a.io),(b.memory,b.io))
                for r in (2,3,7,*range(16,24),28,29,30,31):self.assertEqual(a.r[r],b.r[r])
                self.assertEqual((b.memory,b.r,b.f,b.events,b.calls,b.current_pc,b.delay_of),
                    (c.memory,c.r,c.f,c.events,c.calls,c.current_pc,c.delay_of))
                count+=1
            states+=1
        self.receipt('fault-prefixes',states=states,equal_read_prefixes=count,
            raw_saved_and_live_counter_roles=True,normalized_full_state=True,
            raw_dead_scratch_and_scheduled_LW_PC_not_claimed_equal=True)

    def test_06_full_C_caller_and_two_stubbed_parent_return_windows(self):
        elf=source.raw_read(self.root/'conker/build/conker.us.elf');count=0
        callerVA,callerSize=0x1511A738,0x88
        offset=callerVA-0x15000000+0x2D4B0;caller=struct.unpack_from('>34I',self.rom,offset)
        at=source.elf_slot_offset(elf,callerVA,callerSize);self.assertEqual(elf[at:at+callerSize],self.rom[offset:offset+callerSize])
        for n,match,layout,gate,phase in itertools.product((0,1,4),(0,1,3),(0,1,3),(0,1,2),(0,8)):
            memory,args=fixture(n,1,match,128,layout,0,phase);actor=RECORD+layout*160
            put(memory,0x800C35EA,gate,1)
            expected=dict(memory)
            _,result,io=reference(memory,args)
            if gate==1 and result:put(expected,actor+0x7C,0);put(expected,actor+0x18,0)
            for words in (self.raw,self.normal):
                code=dict(zip(range(source.ENTRY,source.ENTRY+156,4),words))
                m=QueryOracle(caller,memory,(actor,),phase,callerVA,connected=code)
                m.query_args=args;m.run()
                public=lambda data:{a:v for a,v in data.items() if not STACK-0x100<=a<STACK+0x200}
                self.assertEqual(public(m.memory),public(expected))
                self.assertEqual(m.forwarded,[args] if gate==1 else [])
                self.assertEqual(m.io,io if gate==1 else [])
                self.assertEqual(m.external,[(0x151162D4,(actor,)),(0x1511A494,(actor,actor+0x80,actor+0x84))])
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            count+=1
        class Boundary(Exception):pass
        class StopCode(dict):
            def __init__(self,code,stops):super().__init__(code);self.inner=code;self.stops=stops;self.stopped=None
            def __getitem__(self,pc):
                if pc in self.stops:self.stopped=pc;raise Boundary
                return self.inner[pc]
        windows=((0x15118DD4,0x15118E14,{0x15118E14}),(0x1511B0B4,0x1511B0EC,{0x1511B0EC,0x1511B508}))
        bounded=0
        for (entry,end,stops),n,match,layout,phase in itertools.product(windows,(0,3),(0,3),(0,1,3),(0,8)):
            memory,args=fixture(n,1,match,128,layout,0,phase);actor=RECORD+layout*160
            _,result,io=reference(memory,args);sp=STACK+phase;put(memory,sp+0x64,0x3F123456)
            offset=entry-0x15000000+0x2D4B0;span=end-entry+4;at=source.elf_slot_offset(elf,entry,span)
            # Other complete parents remain stubs; these are actual retail windows only.
            window=struct.unpack_from('>%dI'%(span//4),self.rom,offset)
            for words in (self.raw,self.normal):
                code=dict(zip(range(source.ENTRY,source.ENTRY+156,4),words))
                m=QueryOracle(window,memory,args,phase,entry,connected=code)
                m.r[16]=actor;m.r[15]=0x800E0000;m.r[8]=0x12345678;m.f[0]=0x3F800000
                m.code=StopCode(m.code,stops)
                with self.assertRaises(Boundary):m.run()
                self.assertEqual((m.forwarded,m.io),([args],io))
                if entry==0x15118DD4:
                    self.assertEqual(read(m.memory,sp+0x64),read(memory,actor+4) if result else 0x3F123456)
                    self.assertEqual(m.r[8],0x12345678)
                else:self.assertEqual(m.code.stopped,0x1511B508 if result else 0x1511B0EC)
            bounded+=1
        self.receipt('callers',full_actual_C_caller_cases=count,retail_stubbed_parent_windows=bounded,
            three_retail_consumers=True,only_two_post_query_helpers_scripted=True,
            two_other_production_parent_bodies_still_stubs=True)

    def test_07_words_bindings_guards_inputs_and_actual_image(self):
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
        guards=source.owner_guards(raw,bindings);self.assertEqual(len(guards),9)
        self.assertTrue(all(not r['insert_after'] and r['omit']=='false' for r in guards))
        with source.historical_view(self.root,self.out):
            prefix=(self.out/'before-02').read_bytes()
            for i in range(9):
                changed=[dict(r) for r in guards];changed[i]['expected']='0x%08X'%(int(changed[i]['expected'],0)^1)
                with patch.object(source,'owner_guards',return_value=changed):data=source.recovered_guards(prefix,raw,bindings)
                path=self.out/'bad-guards.csv';path.write_bytes(data)
                with self.assertRaises(ValueError):source.emit_padded_assembly(self.obj,self.root/'conker/asm/49D30.s',
                    filename=source.OWNER,word_patches_path=path)
            caller=source.qualify_caller(self.root,self.out,source.freeze(self.root,self.out))
            self.assertEqual(caller['functions'],84);self.assertTrue(caller['whole_object_identical'])
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
