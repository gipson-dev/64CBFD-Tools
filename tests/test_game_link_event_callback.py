"""Full callback, typed native ABI, aliases, fault prefixes and exact installed image."""
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_link_event_callback as source
from tools.experiments import game_link_event_installation as install
from tools.tests import link_event_checkpoint as checkpoint
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string

STACK=point.STACK
RECORD,PACKET,HELPER,CALLER,TABLE=0x20000,0x30000,0x1516972C,0x15149434,0x8008A8D8


def fixture(event=0,word=0x12345678,tag=0x80,match=0,alias=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    for base,length in ((RECORD-16,160),(PACKET-16,64)):
        memory.update({base+i:(i*13+0x57)&255 for i in range(length)})
    packet=(PACKET,RECORD+0x20,RECORD+0x24,RECORD+0x28,RECORD+0x2C,RECORD+0x30,RECORD+0x34,RECORD+0x40)[alias]
    put(memory,packet,word);put(memory,packet+4,word^0xA5010203)
    put(memory,packet+8,0x19,1);put(memory,packet+9,0xE7,1)
    put(memory,RECORD+0x28,word if match==0 else word^0xA5010203 if match==1 else word^0x01010101)
    put(memory,RECORD+0x2C,tag,1)
    if match==3:put(memory,packet+4,tag,1)
    return memory,(RECORD,packet,event)


def cases():
    for event,upper,word,match,alias,phase,mode in itertools.product(
            (0,1,0x2C,0x2D,0x2E,255),(0,0x100,0xFFFFFF00),(0,0x80000001,0xFFFFFFFF),
            range(4),range(8),(0,8),(0,1)):
        memory,args=fixture(event|upper,word,(0,0x80,255)[word%3],match,alias)
        yield memory,args,phase,mode


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x100}


def reference(initial,args,mode=0):
    memory=dict(initial);record,packet,event=args;link=record+0x28;calls=[];event&=255
    if event==0:
        if read(memory,packet)==read(memory,link) or read(memory,link+4,1)==read(memory,packet+4,1):
            calls.append((HELPER,(record,)))
            if mode:put(memory,link,0xDEADC0DE);put(memory,link+4,0x3C,1)
    elif event==0x2D:
        current,first=read(memory,link),read(memory,packet)
        if first==current:
            put(memory,link,read(memory,packet+4));put(memory,link+4,read(memory,packet+9,1),1)
        elif read(memory,packet+4)==current:
            put(memory,link,first);put(memory,link+4,read(memory,packet+8,1),1)
    return public(memory),calls


class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,mode=0,entry=source.ENTRY,helper=HELPER,connected=None):
        self.io=[];self.helper,self.helper_mode=helper,mode
        super().__init__(words,memory,args,[],phase,entry,connected)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording:self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        count=1 if target==self.helper else 3
        self.calls.append((target,self.arguments(count)))

    def hook(self,target):
        if target!=self.helper:raise AssertionError('Unexpected link-event provider')
        record=self.calls[-1][1][0]
        if self.helper_mode:self.put(record+0x28,0xDEADC0DE,4);self.put(record+0x2C,0x3C,1)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]


def state(m):return point.state(m),m.io,m.condition


class LinkEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-link',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_words_binding_guard_and_all_owner_neighbors(self):
        self.assertEqual(self.row,dict(words=43,frame=24,bindings=1,new_guards=1,raw_differences=1,unchanged_raw_padded_neighbors=24))
        self.assertEqual(self.images[1],self.truth)
        a,b=self.images[0][34],self.truth[34]
        self.assertEqual((a>>26,a&65535),(b>>26,b&65535))
        self.assertEqual(((a>>21)&31,(a>>16)&31),((b>>16)&31,(b>>21)&31))
        raw,bindings=source.parts(self.obj)
        for i in range(43):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        with self.assertRaises(ValueError):source.checked_parts(raw,{68:[('R_MIPS_26','func_1516979C')]})
        data,fs,rs=source.parse_object(self.obj);f=fs[source.FUNCTION];wrong=bytearray(self.obj.read_bytes())
        # Mutate the actual object text, not a separately invented expected-word check.
        header=ELF_HEADER.unpack_from(wrong)
        sections=[SECTION_HEADER.unpack_from(wrong,header[6]+i*header[11]) for i in range(header[12])]
        names=sections[header[13]];strings=wrong[names[4]:names[4]+names[5]]
        text=next(s for s in sections if read_c_string(strings,s[0])=='.text')
        at=text[4]+f['value']+136
        wrong[at+3]^=1;path=self.out/'wrong-expected.o';path.write_bytes(wrong)
        with self.assertRaises((ValueError,AssertionError)):
            source.padded_object(self.root,self.out,path,'wrong-expected',self.out/'candidate-guards.csv')
        self.receipt('emission',**self.row,raw_word_controls=43,binding_controls=1,actual_padder_control=1)

    def test_02_guest_full_memory_state_aliases_and_access_order(self):
        count=0;seen=set()
        for memory,args,phase,mode in cases():
            expected,calls=reference(memory,args,mode)
            machines=[Oracle(words,memory,args,phase,mode).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual((public(m.memory),m.calls),(expected,calls))
                self.assertEqual(state(m),state(machines[0]))
            seen.update(machines[0].visits);count+=1
        self.assertEqual({pc-source.ENTRY for pc in seen},set(range(0,172,4))-{132})
        # Inactive events must not read either incoming pointer.
        for event in (1,44,46,255,0xFFFFFF01):
            memory,args=fixture(event);memory={a:v for a,v in memory.items() if STACK-0x400<=a<STACK+0x100}
            for words in (self.truth,*self.images):Oracle(words,memory,(0,0,event)).run()
        self.receipt('guest',three_way_cases=count,naturally_executed_target_words=42,unreachable_duplicate_load_word=33,full_memory_registers_and_ISA_access_order=True,
            aliases=8,phases=2,not_real_destructor_or_hardware=True)

    def test_03_all_access_fault_prefixes(self):
        count=0;pcs=set()
        for event,match,alias,phase in itertools.product((0,0x2D,1),range(4),(0,3,4),(0,8)):
            memory,args=fixture(event,match=match,alias=alias)
            good=Oracle(self.truth,memory,args,phase,1).run()
            for fault in range(good.all_accesses):
                machines=[Oracle(words,memory,args,phase,1) for words in (self.truth,*self.images)]
                for m in machines:
                    m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);self.assertEqual(state(m),state(machines[0]))
                    pcs.add(m.current_pc)
                count+=1
        self.receipt('faults',three_way_prefixes=count,positively_fired_instances=count*3,faulting_words=len(pcs))

    def test_04_independent_original_raw_padded_relocations(self):
        count=0
        for index,(entry,helper) in enumerate(((source.ENTRY,HELPER),(0x18018000,0x18167FFC),(0x1A027FFC,0x1BFF8000))):
            images=[]
            for label,obj in (('original',self.original),('raw',self.obj),('padded',self.padded)):
                data,fs,rs=source.parse_object(obj);f=fs[source.FUNCTION]
                text,unresolved=emit_function(data,f,rs,source.FUNCTION,{'func_1516972C':helper})
                self.assertEqual(unresolved,[])
                stem=self.out/('rebase-%d-%s'%(index,label));asm=stem.with_suffix('.s');asm.write_text(text)
                compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=func_1516972C=0x%X'%helper,'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>43I',source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[2])
            self.assertEqual((images[1][17]&0x3FFFFFF)<<2,helper&0xFFFFFFF)
            for event,match,alias in itertools.product((0,0x2D,255),range(4),(0,3,4)):
                memory,args=fixture(event,match=match,alias=alias)
                machines=[Oracle(words,memory,args,entry=entry,helper=helper).run() for words in images]
                for m in machines:self.assertEqual(state(m),state(machines[0]))
                expected,calls=reference(memory,args)
                self.assertEqual(public(machines[0].memory),expected)
                self.assertEqual(machines[0].calls,[(helper,a) for _,a in calls]);count+=1
        self.receipt('rebase',independent_links=9,symbol_sets=3,three_way_cases=count,actual_R_MIPS_26=True)

    def test_05_actual_full_dispatcher_and_table_slot(self):
        at=CALLER-0x15000000+0x2D4B0
        caller=list(struct.unpack_from('>23I',self.rom,at));count=0
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22F444)[0],source.ENTRY)
        self.assertEqual((0x8008A984-TABLE)//4,43)
        for slot,event,match in itertools.product((0,1,42,43,44,73,74,127,128,255),(0,0x2D,0xFFFFFF2D),range(4)):
            memory,args=fixture(event,match=match);put(memory,RECORD+0x13,slot,1)
            for i in range(74):put(memory,TABLE+i*4,source.ENTRY if i==43 else 0)
            machines=[Oracle(caller,memory,args,entry=CALLER,
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}).run() for words in (self.truth,*self.images)]
            for m in machines:self.assertEqual(state(m),state(machines[0]))
            expected,calls=reference(memory,args) if slot==43 else (public(memory),[])
            self.assertEqual(public(machines[0].memory),expected)
            self.assertEqual([c for c in machines[0].calls if c[0]==HELPER],calls);count+=1
        self.receipt('caller',full_actual_dispatcher_words=23,three_way_cases=count,slot=43,void_return_ignored=True)

    def test_06_native_separate_typed_caller_and_effective_controls(self):
        body='#include <ultra64.h>\nvoid func_1516972C(u8 *);\n'+source.TYPE+source.SELECTED+'\n'
        driver=r'''#include <ultra64.h>
typedef struct { s32 value; u8 tag; } LinkStateFC5F0;
typedef struct { u8 prefix[40]; LinkStateFC5F0 link; u8 suffix[8]; } Record;
typedef struct { s32 first,second; u8 tag0,tag1; } Packet;
void func_150CF484(u8 *,u8 *,u8);
static Record record;static Packet packet;static u32 calls,error;
void func_1516972C(u8 *p){if(p!=(u8 *)&record)error=21;calls++;}
static int run(void){u32 i,j,k,e,count=0;u32 events[]={0,1,44,45,46,255};
u32 words[]={0,0x80000001u,0xFFFFFFFFu,0x12345678u};
if(sizeof(LinkStateFC5F0)!=8||sizeof(Record)!=56||__builtin_offsetof(Record,link)!=40)return 20;
for(e=0;e<6;e++)for(i=0;i<4;i++)for(j=0;j<4;j++)for(k=0;k<3;k++){
u32 current,first,second,want,expectedCalls=0;u8 tag,expectedTag;
packet.first=(s32)words[i];packet.second=(s32)(words[i]^0xA5010203u);packet.tag0=0x19;packet.tag1=0xE7;
current=j==0?(u32)packet.first:j==1?(u32)packet.second:words[i]^0x01010101u;
tag=k==0?0:k==1?0x80:255;if(j==3)((u8 *)&packet)[4]=tag;
record.link.value=(s32)current;record.link.tag=tag;first=(u32)packet.first;second=(u32)packet.second;
want=current;expectedTag=tag;calls=0;
if(events[e]==0)expectedCalls=first==current||tag==((u8 *)&packet)[4];
if(events[e]==45){if(first==current){want=second;expectedTag=packet.tag1;}
else if(second==current){want=first;expectedTag=packet.tag0;}}
func_150CF484((u8 *)&record,(u8 *)&packet,(u8)events[e]);
if(error||calls!=expectedCalls||(u32)record.link.value!=want||record.link.tag!=expectedTag)return 22;
count++;}return count==288?0:23;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
        path=self.out/'native-driver.c';path.write_text(driver);receipts={}
        controls={'wrong-event':source.SELECTED.replace('event == 0x2D','event == 0x2C'),
            'wrong-byte':source.SELECTED.replace('packet[9]','packet[8]'),
            'wrong-identity':source.SELECTED.replace('first == link->value ||','first != link->value ||')}
        for opt in ('-O2','-O0'):
            for label,selected in (('selected',source.SELECTED),*controls.items()):
                c=self.out/('native-'+label+'.c');c.write_text(body.replace(source.SELECTED,selected))
                exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-fno-builtin','-mstackrealign',str(c.relative_to(self.root)),str(path.relative_to(self.root)),'-o',str(exe)],
                    cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
            receipts[opt]=288
        self.receipt('native',cases_per_profile=receipts,effective_controls=6,separate_typed_caller=True,
            freestanding_UBSan=True,alias_and_big_endian_order_qualified_by_guest_not_native=True)

    def test_07_protected_live_and_frozen_inputs(self):
        source.freeze(self.root,self.out);real=hashlib.sha256;cache={};original_read=Path.read_bytes
        for key,path in source.PATHS.items():
            current=self.root/path;frozen=self.out/('before-'+key)
            cache[current]=current.read_bytes();cache[frozen]=frozen.read_bytes()
        if (self.root/install.BUILD/'after-elf').exists():
            for key in checkpoint.AFTER:
                for stage in ('before','after'):
                    path=self.root/install.BUILD/(stage+'-'+key);cache[path]=path.read_bytes()
        @lru_cache(None)
        def digest(data):return real(data)
        count=0
        for key,path in source.PATHS.items():
            for target,message in ((self.root/path,'Unknown link-event input'),(self.out/('before-'+key),'Changed link-event fixture')):
                wrong=bytearray(cache[target]);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def read_bytes(path):return wrong if path==target else cache[path] if path in cache else original_read(path)
                with patch.object(Path,'read_bytes',read_bytes),patch.object(Path,'exists',lambda path:path in cache),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,message):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),fired_controls=count)

    def test_08_first_installed_image_data_and_exact_checkpoint(self):
        expected=install.expected_inputs(self.root,self.root/install.BUILD)
        self.assertEqual(json.loads((self.root/install.BUILD/'initial-prediction.json').read_text()),checkpoint.AFTER)
        if not (self.root/install.BUILD/'after-elf').exists():return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.AFTER[key])
            for stage in ('before','after'):
                target=self.root/install.BUILD/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed link-event checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
            wrong=bytearray(data);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong);count+=1
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        self.receipt('installed',first_complete_image_exact=True,metadata_exclusions=0,checkpoint_controls=count,all_data=report)

    def test_09_effective_big_endian_width_and_event_controls(self):
        before=(self.out/'before-tile_owner').read_text();controls={
            'wide-event':source.SELECTED.replace('u8 event','s32 event'),
            'wide-tag':source.SELECTED.replace('link->tag == packet[4]',
                '*(s32 *)((u8 *)link + 4) == *(s32 *)(packet + 4)')}
        fired=[]
        for label,body in controls.items():
            self.assertNotEqual(body,source.SELECTED)
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'control-'+label)
            self.assertFalse(diag)
            with self.assertRaises(ValueError):source.checked_parts(*source.parts(obj))
            linked,fs=source.build.link_owner(self.root,self.out,obj,source.OWNER);f=fs[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),linked,f['value']))
            for event,match in itertools.product((0,0x100,0xFFFFFF00,0x2D,0x12D),range(4)):
                memory,args=fixture(event,match=match)
                expected,calls=reference(memory,args)
                m=Oracle(words,memory,args).run()
                if (public(m.memory),m.calls)!=(expected,calls):fired.append(label);break
            else:self.fail('Ineffective emitted width control: '+label)
        self.assertEqual(fired,list(controls))
        self.receipt('semantic-controls',positively_fired_controls=fired,real_IDO_big_endian_words=True)


if __name__=='__main__':unittest.main()
