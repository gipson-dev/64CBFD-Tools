"""White-fade public semantics and positive private-lifetime rejection evidence."""
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_white_text_fade as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import test_game_dual_buffer_fade as fade
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command

RECORD,CLOCK,COLOR,TEXT,SUBMIT=fade.RECORD,fade.CLOCK,fade.COLOR,fade.TEXT,fade.SUBMIT


def reference(initial,args,mode=0,symbols=None):
    symbols=symbols or {};memory=dict(initial);record=args[0];calls=[];ordinals={COLOR:0,TEXT:0}
    clock=symbols.get('D_800BE9E4',CLOCK);color=symbols.get('func_1504332C',COLOR);text=symbols.get('func_15042D94',TEXT)
    countdown=read(memory,record+0x48)
    if read(memory,record+0x30,1)&1:put(memory,countdown,20,1)
    count=fade.signed_byte(read(memory,countdown,1));old=0;alpha=255
    if count>0:
        old=(count*12)&255;alpha=255-old
        put(memory,countdown,(count-read(memory,clock))&255,1)
    for weight,other in ((alpha,False),(old,True)):
        if weight:
            calls.append((color,(255,255,255,weight)));ordinals[COLOR]+=1
            fade.effects(memory,COLOR,record,ordinals[COLOR],mode)
            index=read(memory,record+0x3D,1)^(1 if other else 0)
            value=read(memory,record+0x40+index*4)
            calls.append((text,(20,20,128,value)));ordinals[TEXT]+=1
            fade.effects(memory,TEXT,record,ordinals[TEXT],mode)
    return fade.public(memory),calls


class Oracle(fade.Oracle):
    def __init__(self,words,memory,args,mode=0,phase=0,symbols=None,entry=source.ENTRY,connected=None):
        super().__init__(words,memory,args,mode,phase,symbols,entry,connected)

    def record_call(self,target):
        color=self.providers.get('func_1504332C',COLOR);text=self.providers.get('func_15042D94',TEXT)
        if target in (color,text):self.calls.append((target,tuple(self.r[4:8])))
        elif target==SUBMIT:
            pointer=self.r[5]
            self.payloads.append(tuple(read(self.memory,pointer+i*4) for i in range(16)))
        elif target==source.ENTRY:self.calls.append((target,(self.r[4],)))
        else:raise AssertionError('Unexpected white-fade provider '+hex(target))


class WhiteFadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>71I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-white-fade',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_full_candidate_identity_and_unresolved_installation_gates(self):
        self.assertEqual((self.row['candidate_words'],self.row['retail_body_words'],self.row['slot_words'],
            self.row['full_slot_word_differences'],self.row['unchanged_raw_padded_neighbors']),(69,70,71,62,24))
        self.assertEqual(self.images[0],self.images[1]);self.assertEqual(self.images[0][2:4],[0xAFA40030,0x8FAE0030])
        for words in (self.truth,*self.images):
            with self.assertRaisesRegex(ValueError,'S0/private/full-image'):source.require_installable(words)
        raw,bindings=source.parts(self.obj)
        for i in range(69):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'D_800BE9E8')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        self.receipt('emission',**self.row,word_controls=69,binding_controls=6,retail_words_alone_not_qualification=True)

    def test_02_public_reference_signed_byte_exhaustion_aliases_and_callback_mutations(self):
        count=0;seen=set()
        for memory,args,mode,phase in fade.cases():
            want,calls=reference(memory,args,mode)
            for words in (self.truth,*self.images):
                m=Oracle(words,memory,args,mode,phase).run()
                self.assertEqual((fade.public(m.memory),m.calls,m.r[2]),(want,calls,1))
                if words is self.truth:seen.update(m.visits)
            count+=1
        for byte in range(256):
            memory,args=fade.fixture(byte);want,calls=reference(memory,args)
            for words in (self.truth,*self.images):
                m=Oracle(words,memory,args).run();self.assertEqual((fade.public(m.memory),m.calls,m.r[2]),(want,calls,1))
            count+=1
        for byte in (20,21,63,64,65):
            memory,args=fade.fixture(byte);want,calls=reference(memory,args)
            for words in (self.truth,*self.images):
                m=Oracle(words,memory,args).run();self.assertEqual((fade.public(m.memory),m.calls,m.r[2]),(want,calls,1))
            count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+280,4)))
        self.receipt('guest',three_way_public_cases=count,retail_body_words_executed=70,slot_tail_not_executed=True,
            exhaustive_initial_bytes=256,alias_placements=9,scripted_callback_modes=3,phases=2,
            private_lifetime_fault_and_portable_C_alias_parity_not_claimed=True)

    def test_03_actual_color_variadic_wrapper_positive_private_counterexample(self):
        connected={}
        for entry,size in ((COLOR,22),(TEXT,42)):
            rom=entry-0x15000000+0x2D4B0
            connected.update({entry+i*4:w for i,w in enumerate(struct.unpack_from('>%dI'%size,self.rom,rom))})
        count=0;differences=[]
        for byte,flags,phase in itertools.product((0,1,20,64,127,128,255),(0,1),(0,8)):
            memory,args=fade.fixture(byte,flags)
            machines=[Oracle(words,memory,args,phase=phase,connected=connected).run() for words in (self.truth,*self.images)]
            for m in machines:self.assertEqual(m.calls,machines[0].calls);self.assertEqual(m.r[2],1)
            self.assertEqual(machines[1].payloads,machines[2].payloads)
            differing=[(call,i,a,b) for call,(left,right) in enumerate(zip(machines[0].payloads,machines[1].payloads))
                for i,(a,b) in enumerate(zip(left,right)) if a!=b]
            self.assertTrue(differing,'Missing effective actual-helper private-lifetime counterexample')
            differences.append(dict(byte=byte,flags=flags,phase=phase,words=differing));count+=1
        self.receipt('private-counterexample',actual_color_words=22,actual_text_wrapper_words=42,cases=count,
            copied_words_per_call=16,observed_differences=differences,installation_rejected=True,
            snapshot_reads_not_pseudo_instructions=True,real_text_consumer_and_presentation_not_executed=True)

    def test_04_nine_independent_links_and_all_six_relocations(self):
        count=0
        for index,(entry,clock,color,text) in enumerate(((source.ENTRY,CLOCK,COLOR,TEXT),
                (0x18018000,0x80347FFC,0x1814332C,0x18142D94),(0x1A027FFC,0x80418010,0x1B04332C,0x1B042D94))):
            symbols=dict(D_800BE9E4=clock,func_1504332C=color,func_15042D94=text);images=[]
            for label,obj in (('original',self.original),('raw',self.obj),('padded',self.padded)):
                data,fs,rs=source.parse_object(obj);f=fs[source.FUNCTION]
                text_asm,unknown=emit_function(data,f,rs,source.FUNCTION,symbols);self.assertEqual(unknown,[])
                stem=self.out/('rebase-%d-%s'%(index,label));asm=stem.with_suffix('.s');asm.write_text(text_asm)
                compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>%dI'%(f['size']//4),source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images[1],images[2])
            for byte,mode,alias in itertools.product((0,1,20,64,128),range(4),(0,2,7)):
                memory,args=fade.fixture(byte,alias=alias,symbols=symbols);want,calls=reference(memory,args,mode,symbols)
                for words in images:
                    m=Oracle(words,memory,args,mode,symbols=symbols,entry=entry).run()
                    self.assertEqual((fade.public(m.memory),m.calls,m.r[2]),(want,calls,1))
                count+=1
        self.receipt('rebases',independent_links=9,three_way_public_cases=count,all_six_bindings=True,
            signed_low_carries=True,not_private_lifetime_or_actual_helper_rebase_parity=True)

    def test_05_native_separate_typed_caller_and_effective_semantic_controls(self):
        head='#include <ultra64.h>\nextern s32 D_800BE9E4;\n'+source.fade.PROTOTYPES
        path=self.out/'native-driver.c';path.write_text(NATIVE)
        controls={'unsigned-count':source.SELECTED.replace('count = *countdown;','count = *(u8 *)countdown;'),
            'wrong-factor':source.SELECTED.replace('count * 12','count * 13'),
            'wrong-buffer':source.SELECTED.replace('(state[0x15] ^ 1)','state[0x15]')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                c=self.out/('native-'+label+'.c');c.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(c.relative_to(self.root)),
                    str(path.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=6144,profiles=['O2','O0'],UBSan=True,effective_controls=6,
            separately_typed_caller=True,variadic_stub_does_not_read_missing_arguments=True,
            aliases_full_byte_indices_and_actual_wrapper_qualified_only_in_guest=True)

    def test_06_every_live_frozen_corruption_and_unchanged_production(self):
        source.freeze(self.root,self.out);real=hashlib.sha256;original=Path.read_bytes;cache={}
        for key,path in source.PATHS.items():
            for p in (self.root/path,self.out/('before-'+key)):cache[p]=p.read_bytes()
        @lru_cache(None)
        def digest(data):return real(data)
        count=0
        for key,path in source.PATHS.items():
            for target,kind in ((self.root/path,'live'),(self.out/('before-'+key),'frozen')):
                wrong=bytearray(cache[target]);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else cache[path] if path in cache else original(path)
                with patch.object(Path,'read_bytes',altered),patch.object(Path,'exists',lambda p:p in cache),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,'Changed white-fade '+kind+' input'):source.freeze(self.root,self.out)
                count+=1
        for key,path in source.PATHS.items():
            from tools.tests import actor_counter_motion_checkpoint as latest
            self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(self.out/('before-'+key)).read_bytes())
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),
            effective_controls=count,all_production_and_normal_image_inputs_unchanged=True)

    def test_07_source_discriminators_reject_equal_length_and_wrong_s0_role(self):
        expected={'normal':(66,48,'450a9b5736b83a326c71d96e676b7a740b3cfb91084ceeb7a24d7a06b14dfafd'),
            'argument-home':(69,48,source.RAW_SHA),
            'staged-byte':(68,48,'2d73b086406cdce307a37a4737b5f587c4c974742523285be43816421a4cd81e'),
            'staged-array':(69,48,'601665edc74cd030a97122281cd31e8d58385ea53a090b057c7a63daa9f48684'),
            'branch-staged-array':(70,48,'de1ea59bea97f79fd38e708973aea0eade05fa0b7a9841a6b55390679de7a2ae'),
            'weight-byte':(69,48,'088cf9408b1be4b18ec4532553b98545378ab6969be0a39822a3384ad164cb0c'),
            'both-byte':(67,40,'8d53fc4e72a81dd8ba736be184278dd19b76864f5ded21697ddf407c1297590b'),
            'staged-byte-weight':(69,40,'cfc475cb35e35fc9c3cd607ce36f15c03fe64c80cc2dd31f705598b4b9a674e2')}
        rows=[];before=(self.out/'before-tile_owner').read_text()
        for label,body in source.variants().items():
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'screen-'+label);self.assertFalse(diag)
            raw,_=source.parts(obj);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
            self.assertEqual((len(words),(-words[0])&65535,hashlib.sha256(raw).hexdigest()),expected[label])
            if label=='normal':self.assertEqual(words[2],0x00808025)
            else:self.assertNotIn(0xAFB00018,words)
            with self.assertRaises(ValueError):source.require_installable(words+[0]*(71-len(words)))
            rows.append(dict(label=label,words=len(words),frame=(-words[0])&65535,sha256=hashlib.sha256(raw).hexdigest(),installed=False))
        self.receipt('screens',variants=rows,normal_s0_is_record_not_weight=True,equal_length_not_literal_match=True,no_profile_changes=True)

    def test_08_complete_actual_dispatcher_slot_two(self):
        caller=0x150D0034;words=list(struct.unpack_from('>35I',self.rom,0xFD4E4));count=0
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22D368)[0],source.ENTRY)
        for byte,flags,kind,mode,phase in itertools.product((0,20,64,128),(0,1,128,255),(2,255),range(4),(0,8)):
            memory,args=fade.fixture(byte,flags);put(memory,RECORD+0x4C,kind,1);put(memory,fade.TABLE+8,source.ENTRY)
            want,calls=reference(memory,args,mode) if kind==2 else (fade.public(memory),[])
            want=dict(want);put(want,RECORD+0x30,read(want,RECORD+0x30,1)&254,1)
            for body in (self.truth,*self.images):
                m=Oracle(words,memory,(fade.CURSOR,RECORD,0xABCDEF00),mode,phase,entry=caller,
                    connected={source.ENTRY+i*4:w for i,w in enumerate(body)})
                m.record=RECORD;m.run()
                self.assertEqual((fade.public(m.memory),[c for c in m.calls if c[0]!=source.ENTRY],m.r[2]),(want,calls,fade.CURSOR))
            count+=1
        self.receipt('caller',actual_words=35,three_way_public_cases=count,table_slot=2,
            success_retains_cursor_and_clears_flag=True,not_private_caller_payload_parity=True)


NATIVE=r'''#include <ultra64.h>
s32 D_800BE9E4;s32 func_150D0534(u8 *);
typedef struct {u8 pad[0x30];u8 flags;u8 pad31[12];u8 index;u8 pad3E[2];s32 buffers[2];s8 *count;} Record;
static Record r;static s8 countdown;static u32 calls,error;static u8 alphas[2];static s32 values[2];
void func_1504332C(u8 a,u8 b,u8 c,u8 d){if(a!=255||b!=255||c!=255||calls>=4||calls&1)error=20;alphas[calls/2]=d;calls++;}
void func_15042D94(s32 a,s32 b,u8 c,s32 d,...){if(a!=20||b!=20||c!=128||calls>=4||!(calls&1))error=21;values[calls/2]=d;calls++;}
static int run(void){u32 byte,flag,clock,index,n,expectedCalls;u32 clocks[]={0,1,20,255,0xFFFFFFFFu,0x80000000u};
if(sizeof(void*)!=4||__builtin_offsetof(Record,count)!=72||__builtin_offsetof(Record,index)!=61)return 23;
for(byte=0;byte<256;byte++)for(flag=0;flag<2;flag++)for(clock=0;clock<6;clock++)for(index=0;index<2;index++){
s32 count;u32 old=0,alpha=255;u8 final;
r.flags=(u8)flag;r.index=(u8)index;r.buffers[0]=0x12345678;r.buffers[1]=(s32)0xABCDEF01u;r.count=&countdown;
countdown=(s8)byte;D_800BE9E4=(s32)clocks[clock];calls=0;error=0;
count=flag?20:(s8)byte;final=(u8)count;
if(count>0){old=((u32)count*12)&255;alpha=255-old;final=(u8)((u32)count-clocks[clock]);}
expectedCalls=(alpha?2:0)+(old?2:0);n=0;
if(func_150D0534((u8 *)&r)!=1||error||calls!=expectedCalls||(u8)countdown!=final)return 22;
if(alpha){if(alphas[n]!=alpha||values[n]!=r.buffers[index])return 22;n++;}
if(old){if(alphas[n]!=old||values[n]!=r.buffers[index^1])return 22;}}
return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
