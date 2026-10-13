"""Qualify the complete command stream, alias reloads, and derived guarded match."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_stream_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.pad_generated_object import emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_attachment_update_match import AttachmentOracle,AccessFault
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests.test_game_one_shot_timer_match import symbol_rows,canonical_symbols

ACTORS,SELECTOR,SCALE=screen.SYMBOLS.values()
OUTPUT,ATTACHED,SELECTED_ATTACHED,ALT=0x20000,0x90000,0xB0000,0x80000
FLOATS=(0.0,-0.0,1.0,-1.0,1.75,-2.75,180.0,-180.0,1000.125)
VALUES=(-32768,-1,0,1,255,32767)


def apply_stream_symbol_serialization(expected):
    names=('func_1514E7C8','func_1506FC1C','D_800A5EFC')
    rows={name:(offset,fields,string) for offset,name,fields,string in symbol_rows(expected) if name in names}
    assert set(rows)==set(names)
    definitions=((0x1514E7C8,92,18,0,5),(0x1506FC1C,52,18,0,5),(0x800A5EFC,0,16,0,6))
    first=rows[names[0]]
    cursor=first[2]
    for i,(name,definition) in enumerate(zip(names,definitions)):
        offset,fields,string=rows[name]
        assert offset==first[0]+i*16 and fields[1:]==definition
        assert string==cursor and expected[string:string+len(name)+1]==name.encode()+b'\0'
        cursor+=len(name)+1
    string_base=first[2]-first[1][0]
    cursor=first[2]
    for i,name in enumerate((names[2],names[0],names[1])):
        fields=list(rows[name][1])
        fields[0]=cursor-string_base
        struct.pack_into('>IIIBBH',expected,first[0]+i*16,*fields)
        expected[cursor:cursor+len(name)+1]=name.encode()+b'\0'
        cursor+=len(name)+1
    pair={'D_80097D14':0x80097D14,'D_80096338':0x80096338}
    rows={name:(offset,fields,string) for offset,name,fields,string in symbol_rows(expected) if name in pair}
    assert set(rows)==set(pair)
    first,second=(rows[name] for name in pair)
    for name,value in pair.items():
        _,fields,string=rows[name]
        assert fields[1:]==(value,0,16,0,65521)
        assert expected[string:string+11]==name.encode()+b'\0'
    assert second[0]-first[0]==16 and second[2]-first[2]==11
    struct.pack_into('>I',expected,first[0]+4,second[1][1])
    struct.pack_into('>I',expected,second[0]+4,first[1][1])
    expected[first[2]:first[2]+11]=b'D_80096338\0'
    expected[second[2]:second[2]+11]=b'D_80097D14\0'


def signed16(value):
    return (value&65535)-65536 if value&32768 else value&65535


def fixture(slot=0,kind=0,flag=0,enabled=True,byte=0,attachment_type=0,selected_value=1,
            selected_present=True,angle=1.75,output=OUTPUT,symbols=screen.SYMBOLS):
    actors,selector,scale=symbols.values()
    actor=(actors+slot*0x32C)&0xFFFFFFFF
    memory={STACK+i:165 for i in range(-0x100,0x80)}
    for base,length in ((actor,0x32C),(actors,0x32C),(actors+0x32C,0x32C),(actors+8*0x32C,0x32C),
                        (OUTPUT,32),(ATTACHED,0xA0),(SELECTED_ATTACHED,0xA0),(ALT,0xA0),(selector,16)):
        memory.update({(base+i)&0xFFFFFFFF:(i*13+19)&255 for i in range(length)})
    for base in (actors,actors+0x32C,actors+8*0x32C):
        put(memory,base+0x31C,0)
    for offset,value,size in ((0x31C,ATTACHED if enabled else 0,4),(0x2F8,flag,2),
            (0x84,kind,2),(0x54,bits(angle),4),(0x1D1,byte,1)):
        put(memory,actor+offset,value,size)
    put(memory,ATTACHED+0x78,attachment_type,1)
    put(memory,ATTACHED+0x12,-32768,2)
    put(memory,ALT+0x12,1234,2)
    put(memory,SELECTED_ATTACHED+0x12,selected_value,2)
    put(memory,actors+0x32C+0x31C,SELECTED_ATTACHED if selected_present else 0)
    put(memory,actors+8*0x32C+0x31C,ALT)
    put(memory,selector,1,1)
    put(memory,scale,0x43360B61)
    return memory,actor,output


def reference(memory,slot=0,output=OUTPUT,symbols=screen.SYMBOLS):
    memory=memory.copy()
    actors,selector,scale=symbols.values()
    actor=(actors+slot*0x32C)&0xFFFFFFFF
    attached=read(memory,actor+0x31C)
    if attached and not read(memory,actor+0x2F8,2)&0x80:
        value=signed16(math.trunc(floating(bits(floating(read(memory,actor+0x54))*floating(read(memory,scale))))))
        kind=read(memory,actor+0x84,2)
        if kind in (0x42,0x14,0x76):
            for tag,amount in ((10,value),(4,-value)):
                put(memory,output,tag,2)
                put(memory,output+2,amount,2)
                output+=4
        else:
            tag=6 if read(memory,attached+0x78,1)==10 else 10
            put(memory,output,tag,2)
            put(memory,output+2,value,2)
            output+=4
    if read(memory,actor+0x1D1,1):
        put(memory,output,6,2)
        byte=read(memory,actor+0x1D1,1)
        put(memory,output+2,(byte-256 if byte&128 else byte)*200,2)
        output+=4
    attached=read(memory,(actors+read(memory,selector,1)*0x32C+0x31C)&0xFFFFFFFF)
    if attached and read(memory,attached+0x12,2):
        put(memory,output,8,2)
        attached=read(memory,(actors+read(memory,selector,1)*0x32C+0x31C)&0xFFFFFFFF)
        put(memory,output+2,-signed16(read(memory,attached+0x12,2)),2)
        output+=4
    return memory,output


class StreamOracle(AttachmentOracle):
    def __init__(self,words,memory,slot=0,output=OUTPUT,phase=0,entry=screen.ENTRY,connected=None):
        super().__init__(words,memory,arguments=(output,slot),phase=phase,entry=entry,connected=connected)
    def execute(self,word):
        if word>>26==32:
            rs,rt=word>>21&31,word>>16&31
            immediate=(word&65535)^0x8000
            address=(self.r[rs]+immediate-0x8000)&0xFFFFFFFF
            value=self.get(address,1)
            self.r[rt]=(value-256 if value&128 else value)&0xFFFFFFFF
            self.r[0]=0
        else:
            super().execute(word)


class WindowDone(Exception):
    pass


class CallerWindow(StreamOracle):
    def __init__(self,words,memory,slot,output,actor,window):
        super().__init__(window,memory,slot,output,entry=0x15034050,
            connected={screen.ENTRY+i*4:w for i,w in enumerate(words)})
        self.r[6],self.r[17]=output,actor
    def record_call(self,target):
        assert target==screen.ENTRY
        self.calls.append((target,self.r[4],self.r[5]))
    def execute(self,word):
        super().execute(word)
        if word==0x92240004:
            raise WindowDone()


class GameActorCommandStreamMatchTests(unittest.TestCase):
    run_native=native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-stream-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',layout='conker/retail_layout.us.txt',makefile='conker/Makefile',
            rodata='conker/asm/data/23C630.rodata.s')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.owner_before=(cls.out/'before-source').read_text()
        cls.owner_after=screen.recovered_owner(cls.owner_before)
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.words=screen.normalize(cls.raw)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>97I',cls.rom,screen.ROM))
        cls.guard_before=(cls.out/'before-guards').read_bytes()
        cls.guard_after=screen.guard_bytes(cls.guard_before,cls.out/'selected.o')
        cls.guards=cls.out/'qualified-guards.csv'
        cls.guards.write_bytes(cls.guard_after)
        cls.window=list(struct.unpack_from('>5I',cls.rom,0x61500))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_full_guarded_match_and_source_derived_controls(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(96,0,62,0))
        self.assertEqual(self.words,self.retail)
        rows=screen.guard_rows(self.out/'selected.o')
        self.assertEqual(len(rows),52)
        self.assertEqual([r['offset'] for r in rows if r['insert_after']],['0xD4'])
        self.assertEqual(self.meta['relocations'],{0:[('R_MIPS_HI16','D_800CC2D0')],4:[('R_MIPS_LO16','D_800CC2D0')],
            0x44:[('R_MIPS_HI16','D_80097D14')],0x58:[('R_MIPS_LO16','D_80097D14')],
            0xE8:[('R_MIPS_HI16','D_800C3E78')],0xF4:[('R_MIPS_LO16','D_800C3E78')]})
        for offset in (0x2C,0xD4,0xD8,0xDC,0xE0):
            bad=self.raw.copy()
            bad[offset//4]^=1
            with self.assertRaises(AssertionError):
                screen.normalize(bad)
        with self.assertRaisesRegex(ValueError,'already installed'):
            screen.guard_bytes(self.guard_after,self.out/'selected.o')
        original=(self.root/'conker/asm/61490.s').read_text().split('glabel '+screen.FUNCTION+'\n',1)[1]
        slot=self.out/'guard-slot.s'
        slot.write_text('glabel '+screen.FUNCTION+'\n'+original.split('endlabel '+screen.FUNCTION,1)[0]+'endlabel '+screen.FUNCTION+'\n')
        isolated=self.out/'isolated-guards.csv'
        with isolated.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=next(csv.reader(self.guard_before.decode().splitlines())))
            writer.writeheader()
            writer.writerows(rows)
        emit_padded_assembly(self.out/'selected.o',slot,word_patches_path=isolated,filename='generated_61490')
        text,functions,relocations=parse_object(self.out/'selected.o')
        for row in rows:
            bad=bytearray(text)
            bad[functions[screen.FUNCTION]['value']+int(row['offset'],0)+3]^=1
            with patch('tools.pad_generated_object.parse_object',return_value=(bytes(bad),functions,relocations)):
                with self.assertRaises(ValueError):
                    emit_padded_assembly(self.out/'selected.o',slot,word_patches_path=isolated,filename='generated_61490')
        self.assertEqual(self.before[elf_slot_offset(self.before,SCALE,4):][:4],self.rom[0x23C7D4:0x23C7D8])
        self.receipt('shape',raw_words=96,slot_words=97,guard_rows=52,inserted_cursor_word=1,direct=False)

    def compare(self,memory,slot=0,output=OUTPUT,phase=0):
        expected,cursor=reference(memory,slot,output)
        models=[StreamOracle(w,memory,slot,output,phase).run() for w in (self.retail,self.raw,self.words)]
        for model in models:
            self.assertEqual(model.memory,expected)
            self.assertEqual(model.r[2],cursor)
            self.assertEqual(model.calls,[])
        self.assertEqual(models[0].events,models[1].events)
        self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f,models[0].visits),
                         (models[2].memory,models[2].events,models[2].r,models[2].f,models[2].visits))
        return models[0].visits

    def test_02_guest_gates_widths_signed_values_and_aliases(self):
        count,coverage=0,set()
        kinds=(0,0x14,0x42,0x76,0x8042,0xFF14,0xFFFF,0x100,0x77,0x43)
        for kind,flag,enabled,attached_kind,present,value,phase in itertools.product(kinds,(0,1,0x80,0xFFFF),
                (False,True),(0,10,255),(False,True),VALUES,(0,8)):
            slot=(0,2,25,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[count%6]
            memory,_,out=fixture(slot,kind,flag,enabled,byte=(0,1,127,128,255)[count%5],
                attachment_type=attached_kind,selected_value=value,selected_present=present,angle=FLOATS[count%len(FLOATS)])
            coverage.update(self.compare(memory,slot,out,phase))
            count+=1
        signed_cases=0
        for byte,kind,phase in itertools.product(range(256),(0,0x14,0x42,0x76,0x8042,0xFFFF),(0,8)):
            memory,_,out=fixture(kind=kind,byte=byte,angle=FLOATS[byte%len(FLOATS)])
            self.compare(memory,output=out,phase=phase)
            signed_cases+=1
        aliases=0
        for alias,kind,phase in itertools.product(range(8),(0,0x42),(0,8)):
            memory,actor,out=fixture(kind=kind,byte=128)
            out=(actor+0x54,actor+0x84,actor+0x1D0,ATTACHED+0x78,SELECTED_ATTACHED+0x12,
                 SELECTOR,ACTORS+0x32C+0x31C,OUTPUT)[alias]
            if alias in (5,6):
                put(memory,actor+0x2F8,0x80,2)
                put(memory,actor+0x1D1,0,1)
                if alias==6:
                    put(memory,ACTORS+0x32C+0x31C,ATTACHED)
            self.compare(memory,output=out,phase=phase)
            aliases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+388,4)))
        self.receipt('guest',matrix_cases=count,signed_byte_cases=signed_cases,alias_cases=aliases,covered_words=97,
            raw_public_RAM_and_events=True,fitted_literal_registers=True)

    def test_03_fired_literal_faults_and_skipped_invalid_float_inputs(self):
        pairs=0
        for kind,byte,enabled,flag in ((0,0,False,0),(0,1,True,0),(0x42,128,True,0),(0x76,255,True,0),(0x8042,0,True,0x80)):
            memory,_,out=fixture(kind=kind,byte=byte,enabled=enabled,flag=flag)
            for phase in (0,8):
                complete=StreamOracle(self.retail,memory,output=out,phase=phase).run()
                for cut in range(complete.accesses):
                    models=[]
                    for words in (self.retail,self.words):
                        model=StreamOracle(words,memory,output=out,phase=phase)
                        model.fault=cut
                        with self.assertRaises(AccessFault):
                            model.run()
                        self.assertEqual(model.accesses,cut)
                        models.append(model)
                    self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
                                     (models[1].memory,models[1].events,models[1].r,models[1].f))
                    pairs+=1
        for present,flag in ((False,0),(True,0x80)):
            memory,actor,out=fixture(enabled=present,flag=flag,selected_present=False)
            for address in (actor+0x54,actor+0x84,SCALE):
                for i in range(4 if address!=actor+0x84 else 2):
                    memory.pop(address+i,None)
            for words in (self.retail,self.raw,self.words):
                self.assertEqual(StreamOracle(words,memory,output=out).run().r[2],out)
        self.receipt('faults',fired_pairs=pairs,literal_prefix_state=True,hardware_PC_FCSR_not_claimed=True)

    def native_source(self,body):
        return r'''#define NULL ((void*)0)
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
u8 D_800CC2D0[26*0x32C] __attribute__((aligned(4))),wanted[26*0x32C] __attribute__((aligned(4)));
u8 D_800C3E78[16] __attribute__((aligned(4))),selectedWanted[16] __attribute__((aligned(4)));
u8 output[32] __attribute__((aligned(4))),outputWanted[32] __attribute__((aligned(4)));
f32 D_80097D14;union {u32 word;f32 value;} scale;
u8 *mapped(u8 *p){u32 address=(u32)p,base=(u32)D_800CC2D0;
 if(address>=base && address-base<sizeof(D_800CC2D0)){return wanted+(address-base);}return p;}
u8 *model(u8 *p,s32 slot){u8 *a=wanted+(u32)slot*0x32C,*t=mapped(*(u8**)(a+0x31C));s16 v;u16 k;
 if(t && !(*(u16*)(a+0x2F8)&128)){v=(s32)(*(f32*)(a+0x54)*D_80097D14);k=*(u16*)(a+0x84);
  if(k==66 || k==20 || k==118){*(s16*)p=10;*(s16*)(p+2)=v;p+=4;*(s16*)p=4;*(s16*)(p+2)=-v;p+=4;}
  else{*(s16*)p=t[0x78]==10?6:10;*(s16*)(p+2)=v;p+=4;}}
 if(*(s8*)(a+0x1D1)){*(s16*)p=6;*(s16*)(p+2)=*(s8*)(a+0x1D1)*200;p+=4;}
 t=mapped(*(u8**)(wanted+selectedWanted[0]*0x32C+0x31C));
 if(t && *(s16*)(t+0x12)){*(s16*)p=8;t=mapped(*(u8**)(wanted+selectedWanted[0]*0x32C+0x31C));*(s16*)(p+2)=-*(s16*)(t+0x12);p+=4;}
 return p;}
''' + body + r'''
int check(void){u32 c,i,mode;u8 *a,*t,*p,*expected,*returned;int slot,kinds[]={0,20,66,118,0x8042,0xFF14,65535};
 f32 angles[]={0.0f,-0.0f,1.0f,-1.0f,1.75f,-2.75f,180.0f,-180.0f,1000.125f};
 if(sizeof(void*)!=4 || sizeof(s16)!=2)return 9;
 scale.word=0x43360B61;D_80097D14=scale.value;
 for(c=0;c<65536;c++){
  for(i=0;i<sizeof(D_800CC2D0);i++)D_800CC2D0[i]=(u8)(i*13+19);
  for(i=0;i<26;i++)*(u8**)(D_800CC2D0+i*0x32C+0x31C)=0;
  slot=(c%24)+2;a=D_800CC2D0+slot*0x32C;t=D_800CC2D0+0x32C;
  *(u8**)(a+0x31C)=(c&1)?t:0;*(u16*)(a+0x2F8)=(c&2)?128:1;
  *(u16*)(a+0x84)=(u16)kinds[c%7];*(f32*)(a+0x54)=angles[c%9];a[0x1D1]=(u8)c;t[0x78]=(c&4)?10:255;
  *(u8**)(D_800CC2D0+0x31C)=t;*(u8**)(D_800CC2D0+8*0x32C+0x31C)=D_800CC2D0+24*0x32C;
  *(s16*)(D_800CC2D0+24*0x32C+0x12)=(s16)(c+1234);
  *(s16*)(t+0x12)=(s16)c;D_800C3E78[0]=0;
  for(i=1;i<16;i++)D_800C3E78[i]=(u8)(i+19);
  for(i=0;i<32;i++)output[i]=outputWanted[i]=(u8)(i*13+19);
  mode=c%4;p=mode==0?output:mode==1?a+0x1D0:mode==2?t+0x12:D_800C3E78;
  if(mode==3){*(u16*)(a+0x2F8)=128;a[0x1D1]=0;}
  for(i=0;i<sizeof(wanted);i++)wanted[i]=D_800CC2D0[i];
  for(i=0;i<16;i++)selectedWanted[i]=D_800C3E78[i];
  expected=mode==0?outputWanted:mode==1?wanted+slot*0x32C+0x1D0:mode==2?wanted+0x32C+0x12:selectedWanted;
  returned=model(expected,slot);returned=p+(returned-expected);expected=func_150341BC(p,slot);
  if(returned!=expected)return 1;
  for(i=0;i<sizeof(wanted);i++)if(wanted[i]!=D_800CC2D0[i])return 2;
  for(i=0;i<16;i++)if(selectedWanted[i]!=D_800C3E78[i])return 3;
  for(i=0;i<32;i++)if(outputWanted[i]!=output[i])return 4;
 }
 return 0;}
void _start(void){int r=check();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");for(;;){}}
'''

    def test_04_native32_source_and_effective_signed_gate_controls(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(screen.SELECTED),profile),(0,''))
        selected_expression='*(u8 **)(D_800CC2D0 + D_800C3E78[0] * 0x32C + 0x31C)'
        cached=screen.SELECTED.replace('        *(s16 *)cursor = 8;',
            '        u8 *chosen = '+selected_expression+';\n        *(s16 *)cursor = 8;').replace(
            '= -*(s16 *)('+selected_expression+' + 0x12);','= -*(s16 *)(chosen + 0x12);')
        negatives={'unsigned-byte':screen.SELECTED.replace('*(s8 *)(actor + 0x1D1)','*(u8 *)(actor + 0x1D1)'),
            'wrong-tag':screen.SELECTED.replace('*(s16 *)cursor = 8;','*(s16 *)cursor = 9;'),
            'wrong-flag':screen.SELECTED.replace('& 0x80','& 0x40'),
            'wrong-polarity':screen.SELECTED.replace('= -amount;','= amount;'),
            'narrow-type':screen.SELECTED.replace('*(u16 *)(actor + 0x84)','*(u8 *)(actor + 0x84)'),
            'cached-selected':cached}
        for name,body in negatives.items():
            self.assertNotEqual(body,screen.SELECTED)
            self.assertIn(self.run_native('negative-'+name,self.native_source(body))[0],(1,2,3,4))
        self.receipt('native',cases_per_profile=65536,profiles=['O2','O0'],effective_negatives=6,
            valid_actor_backing=True,native_aliases=True,invalid_FP_conversion_not_claimed=True)

    def test_05_owner_neighbors_pools_and_both_full_padders(self):
        objects=[screen.compile_owner(self.root,self.out,s,'owner-'+name) for name,s in
            (('before',self.owner_before),('after',self.owner_after))]
        self.assertEqual(objects[0][1],objects[1][1])
        before,after=[parse_object(o) for o,_ in objects]
        self.assertEqual(before[1].keys(),after[1].keys())
        for name in before[1]:
            a,b=before[1][name],after[1][name]
            if name!=screen.FUNCTION:
                self.assertEqual(before[0][a['value']:a['value']+a['size']],after[0][b['value']:b['value']+b['size']],name)
                self.assertEqual({o-a['value']:r for o,r in before[2].items() if a['value']<=o<a['value']+a['size']},
                    {o-b['value']:r for o,r in after[2].items() if b['value']<=o<b['value']+b['size']},name)
        self.assertEqual(normalized_pools(objects[0][0]),normalized_pools(objects[1][0]))
        self.assertEqual(screen.guard_rows(objects[1][0]),screen.guard_rows(self.out/'selected.o'))
        padded=[]
        for script in ('pad_c_object.py','pad_generated_object.py'):
            asm=self.out/(script+'.s')
            args=[str(objects[1][0]),str(self.root/'conker/retail_layout.us.txt'),'generated_61490',str(asm)] if script=='pad_c_object.py' else [
                str(objects[1][0]),str(self.root/'conker/asm/61490.s'),str(asm),'--filename','generated_61490']
            result=subprocess.run([sys.executable,str(self.root/'tools'/script),*args,'--word-patches',str(self.guards),
                '--rodata-symbol','jtbl_80097D20_game'],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
            obj=asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(self.root/'conker'),'-o',str(obj),str(asm)],check=True,capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0],padded[1])
        self.receipt('owner',unchanged_neighbors=len(after[1])-1,both_full_padders=True,pools_and_relocations_fixed=True)

    def test_06_independent_rebases_preserve_all97_words(self):
        original=(self.root/'conker/asm/61490.s').read_text().split('glabel '+screen.FUNCTION+'\n',1)[1]
        asm=self.out/'original.s'
        asm.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\nglabel '+screen.FUNCTION+'\n'+
            original.split('endlabel '+screen.FUNCTION,1)[0]+'endlabel '+screen.FUNCTION+'\n')
        obj=asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        for i,entry,symbols in ((0,screen.ENTRY,screen.SYMBOLS),
            (1,0x152341BC,dict(D_800CC2D0=0x80107FFC,D_800C3E78=0x80218004,D_80097D14=0x80307FFC)),
            (2,0x153341BC,dict(D_800CC2D0=0x80418004,D_800C3E78=0x80517FFC,D_80097D14=0x80618004))):
            with patch.multiple(screen,ENTRY=entry,SYMBOLS=symbols):
                _,raw=screen.compile_candidate(self.root,self.out,'rebase-'+str(i))
            ld=self.out/('original-'+str(i)+'.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            elf=ld.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            self.assertEqual(screen.normalize(raw),list(struct.unpack_from('>97I',sections(elf)['.text'][1])))

    def test_07_real_five_word_caller_window(self):
        count=0
        for kind,byte,out_kind in itertools.product((0,0x42,0x76),(0,128),(0,1)):
            memory,actor,out=fixture(kind=kind,byte=byte)
            if out_kind:
                out=actor+4
            expected,cursor=reference(memory,output=out)
            models=[]
            for words in (self.retail,self.words):
                model=CallerWindow(words,memory,0,out,actor,self.window)
                with self.assertRaises(WindowDone):
                    model.run()
                self.assertEqual(model.r[16],cursor)
                self.assertEqual(model.r[4],read(expected,actor+4,1))
                self.assertEqual(model.memory,expected)
                models.append(model)
            self.assertEqual((models[0].events,models[0].r,models[0].f),(models[1].events,models[1].r,models[1].f))
            count+=1
        self.receipt('caller',cases=count,actual_caller_words=5,full119_word_caller_not_exercised=True)

    def test_08_literal_image_guard_history_and_protected_data(self):
        current=(self.root/self.paths['elf']).read_bytes()
        source=(self.root/screen.SOURCE).read_text()
        expected=bytearray(self.before)
        installed=source==self.owner_after
        offset=elf_slot_offset(self.before,screen.ENTRY,388)
        self.assertEqual(offset,elf_slot_offset(current,screen.ENTRY,388))
        if installed:
            expected[offset:offset+388]=struct.pack('>97I',*self.words)
            with patch.multiple(descriptor.screen,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
                size_offset=descriptor.size_field(self.before)
            struct.pack_into('>I',expected,size_offset,388)
            self.assertEqual(canonical_symbols(bytes(expected)),canonical_symbols(current))
            before_serialization=bytes(expected)
            apply_stream_symbol_serialization(expected)
            serialization_bytes=sum(a!=b for a,b in zip(before_serialization,expected))
            self.assertEqual(serialization_bytes,66)
        else:
            self.assertEqual(source,self.owner_before)
            serialization_bytes=0
        self.assertEqual(current,bytes(expected))
        if installed:
            for corrupt_offset in (0,0x2B7D20+13,0x2C8890+13):
                corrupt=bytearray(current)
                corrupt[corrupt_offset]^=1
                self.assertNotEqual(bytes(corrupt),bytes(expected))
        self.assertEqual((self.root/self.paths['guards']).read_bytes(),self.guard_after if installed else self.guard_before)
        for name in ('progress','layout','makefile','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('linked-audit',installed=installed,matching_credit=int(installed),guard_rows_added=52,
            changed_bytes=sum(a!=b for a,b in zip(self.before,current)),data=data,
            closed_symbol_serialization_bytes=serialization_bytes,named_definitions_unchanged_except_target_size=True,
            target_changed_bytes=sum(a!=b for a,b in zip(self.before[offset:offset+388],current[offset:offset+388])))


if __name__=='__main__':
    unittest.main()
