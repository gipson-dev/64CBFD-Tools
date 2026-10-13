"""Full dispatcher, provider lifetimes, table translation and literal image audit."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_dispatch_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_command_stream_match as stream
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout

ACTORS=screen.SYMBOLS['D_800CC2D0']
OUTPUT,ALT,STACK=stream.OUTPUT,0x24000,stream.STACK
LOOKUP,FINALIZER=0x1503DA3C,0x15034860
PRIMARY=0x150341BC
WRITERS={0x2B:0x150D8590,0x28:0x150344A0,0x77:0x150344A0,0x4B:0x150B58F0,
    0x7B:0x150F1B48,0x8A:0x15034420,0x21:0x150BE438,0x98:0x15034340,
    0x5A:0x150343B0,0x74:0x150343B0,0x7A:0x150343B0,0x8D:0x150343B0}
IDS={PRIMARY:1,0x150D8590:2,0x150344A0:3,0x150B58F0:4,0x150F1B48:5,
    0x15034420:6,0x150BE438:7,0x15034340:8,0x150343B0:9}
OLD_ANCHOR,NEW_ANCHOR='jtbl_80097D20_game','jtbl_80097C80_game'


def fixture(table,slot=0,state=0,kind=0,enabled=True):
    memory,actor,_=stream.fixture(slot=slot)
    memory.update({ALT+i:(i*13+19)&255 for i in range(128)})
    memory.update({OUTPUT+i:(i*13+19)&255 for i in range(128)})
    for offset,value,size in ((0,state,4),(4,kind,1),(0x1D4,int(enabled),4)):
        stream.put(memory,actor+offset,value,size)
    memory.update({screen.TABLE+i:byte for i,byte in enumerate(table)})
    return memory,actor


def provider(memory,target,args,actor,mode,phase=0):
    if target in IDS:
        cursor,slot=args
        stream.put(memory,cursor,0x200+IDS[target],2)
        stream.put(memory,cursor+2,slot,2)
        if mode==1:
            stream.put(memory,actor+4,0x70,1)
            stream.put(memory,actor+0x1D4,0)
        return ALT if mode==3 else (cursor+4)&0xFFFFFFFF
    if target==LOOKUP:
        kind,index=args
        if index==0 and mode==1:
            stream.put(memory,actor+4,0x7B,1)
        if index==1 and mode==4:
            stream.put(memory,STACK+phase-8,0x89ABCDEF)
        return (kind*3+index*29)&255
    assert target==FINALIZER
    cursor,_,first,second=args
    stream.put(memory,cursor,0x400,2)
    stream.put(memory,cursor+2,first^second,2)
    return ALT+16 if mode in (2,3) else (cursor+4)&0xFFFFFFFF


def reference(memory,slot=0,output=OUTPUT,mode=0,phase=0):
    memory=memory.copy()
    actor=(ACTORS+slot*0x32C)&0xFFFFFFFF
    calls=[]
    if not stream.read(memory,actor+0x1D4):
        stream.put(memory,output,0x1000,2)
        return memory,calls
    target=PRIMARY if stream.read(memory,actor)==1 else WRITERS.get(stream.read(memory,actor+4,1))
    cursor=output
    if target is not None:
        args=(output,slot)
        calls.append((target,args))
        cursor=provider(memory,target,args,actor,mode,phase)
    args=(stream.read(memory,actor+4,1),0)
    calls.append((LOOKUP,args))
    first=provider(memory,LOOKUP,args,actor,mode,phase)
    args=(stream.read(memory,actor+4,1),1)
    calls.append((LOOKUP,args))
    second=provider(memory,LOOKUP,args,actor,mode,phase)
    if mode==4:
        first=0x89ABCDEF
    args=(cursor,actor,first,second)
    calls.append((FINALIZER,args))
    cursor=provider(memory,FINALIZER,args,actor,mode,phase)
    stream.put(memory,cursor,0x1000,2)
    return memory,calls


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x800<=a<STACK+0x100}


class DispatchOracle(stream.StreamOracle):
    def __init__(self,words,memory,slot=0,output=OUTPUT,mode=0,phase=0,connected=None):
        self.in_provider=False
        super().__init__(words,memory,slot,output,phase,entry=screen.ENTRY,connected=connected)
        self.actor=(ACTORS+slot*0x32C)&0xFFFFFFFF
        self.mode,self.phase=mode,phase
    def gate(self):
        if not self.in_provider:
            super().gate()
    def record_call(self,target):
        count=4 if target==FINALIZER else 2
        assert target in (*IDS,LOOKUP,FINALIZER)
        args=tuple(self.r[4:4+count])
        self.calls.append((target,args))
        self.events.append(('CALL',target,args))
    def hook(self,target):
        self.in_provider=True
        try:
            before=self.memory.copy()
            result=provider(self.memory,target,self.calls[-1][1],self.actor,self.mode,self.phase)
            for address in sorted(before.keys()|self.memory.keys()):
                if before.get(address)!=self.memory.get(address):
                    self.events.append(('PROVIDER-BYTE',address,self.memory.get(address)))
            for register in (1,2,3,*range(4,16),24,25):
                self.r[register]=0xA5000000+register
            self.f[:20]=[0xA5000000+i for i in range(20)]
            self.r[2]=result
        finally:
            self.in_provider=False


class GameActorCommandDispatchMatchTests(unittest.TestCase):
    run_native=native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-dispatch-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',layout='conker/retail_layout.us.txt',makefile='conker/Makefile',
            rodata='conker/asm/data/23C630.rodata.s',symbols='conker/undefined_syms_auto.txt')
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
        cls.make_before=(cls.out/'before-makefile').read_text()
        old='game/generated_61490.c.o: RETAIL_RODATA_SYMBOL := '+OLD_ANCHOR
        assert cls.make_before.count(old)==1
        cls.make_after=cls.make_before.replace(old,'game/generated_61490.c.o: RETAIL_RODATA_SYMBOL := '+NEW_ANCHOR)
        cls.meta,cls.words,cls.pool=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>119I',cls.rom,screen.ROM))
        cls.table=cls.rom[screen.TABLE_ROM:screen.TABLE_ROM+148]
        cls.after_object,cls.after_diagnostics=screen.compile_owner(cls.root,cls.out,cls.owner_after,'prepared-owner-after')
        cls.guard_after=screen.guard_bytes((cls.out/'before-guards').read_bytes(),cls.after_object)
        cls.guards=cls.out/'qualified-guards.csv'
        cls.guards.write_bytes(cls.guard_after)

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_direct_words_table_and_frame_allocation_evidence(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(119,40,0,160))
        self.assertEqual(self.words,self.retail)
        self.assertEqual(self.pool[:148],self.table)
        self.assertEqual(self.pool[148:],bytes(12))
        with (self.root/self.paths['guards']).open(newline='') as data:
            self.assertFalse([r for r in csv.DictReader(data) if r['function']==screen.FUNCTION])
        for name,body,frame,home in (('old-frame',dict(screen.candidates())['signed-type-local'],48,-16),
                                   ('matched-frame',screen.SELECTED,40,-8)):
            record=screen.trace_frame(self.root,self.out,name,body)
            self.assertTrue(record['code_unchanged'])
            end=record['events'][-1]
            self.assertEqual((end['frame'],end['saved'],end['outgoing'],end['locals'],end['temporary']),(frame,16,16,frame-32,0))
            self.assertEqual([r['offset'] for r in record['records']['optimizer'] if r['name']=='vreg' and r['storage']=='M'],[home])

    def compare(self,memory,slot=0,output=OUTPUT,mode=0,phase=0):
        expected,calls=reference(memory,slot,output,mode,phase)
        pair=[DispatchOracle(w,memory,slot,output,mode,phase).run() for w in (self.retail,self.words)]
        for model in pair:
            self.assertEqual(public(model.memory),public(expected))
            self.assertEqual(model.calls,calls)
        self.assertEqual((pair[0].memory,pair[0].events,pair[0].r,pair[0].f,pair[0].visits),
                         (pair[1].memory,pair[1].events,pair[1].r,pair[1].f,pair[1].visits))
        return pair[0].visits

    def test_02_all_type_bytes_gates_mutations_and_aliases(self):
        count,coverage=0,set()
        for kind,state,enabled,mode,phase in itertools.product(range(256),(0,1,0x22,0x10000001),(False,True),range(4),(0,8)):
            slot=(0,2,25,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[count%6]
            memory,_=fixture(self.table,slot,state,kind,enabled)
            coverage.update(self.compare(memory,slot,mode=mode,phase=phase))
            count+=1
        home_cases=0
        for state,kind,phase in itertools.product((0,1),(0x21,0x42,0x7B,0x98),(0,8)):
            memory,_=fixture(self.table,state=state,kind=kind)
            self.compare(memory,mode=4,phase=phase)
            home_cases+=1
        aliases=0
        for state,kind,phase in itertools.product((0,1),(0x21,0x28,0x2B,0x4B,0x5A,0x7B,0x8A,0x98),(0,8)):
            memory,actor=fixture(self.table,state=state,kind=kind)
            self.compare(memory,output=actor+4,mode=1,phase=phase)
            aliases+=1
        reachable=set(range(screen.ENTRY,screen.ENTRY+476,4))-{screen.ENTRY+0x60,screen.ENTRY+0x84}
        self.assertEqual(coverage,reachable)
        self.receipt('guest',cases=count,home_cases=home_cases,alias_cases=aliases,visited_words=len(coverage),
            literal_RAM_events_registers=True,providers_opaque=True)

    def test_03_own_access_fault_prefixes_and_null_buffer_minimal_backing(self):
        cuts=0
        for state,kind,enabled in ((0,0,False),(1,0,True),(0,0x77,True),(0,0x7B,True),(0,255,True)):
            memory,_=fixture(self.table,state=state,kind=kind,enabled=enabled)
            for mode,phase in itertools.product((0,1,4),(0,8)):
                complete=DispatchOracle(self.retail,memory,mode=mode,phase=phase).run()
                for cut in range(complete.accesses):
                    pair=[]
                    for words in (self.retail,self.words):
                        model=DispatchOracle(words,memory,mode=mode,phase=phase)
                        model.fault=cut
                        with self.assertRaises(stream.AccessFault):
                            model.run()
                        self.assertEqual(model.accesses,cut)
                        pair.append(model)
                    self.assertEqual((pair[0].memory,pair[0].events,pair[0].r,pair[0].f),(pair[1].memory,pair[1].events,pair[1].r,pair[1].f))
                    cuts+=1
        memory,actor=fixture(self.table,enabled=False)
        for i in range(0x32C):
            if not 0x1D4<=i<0x1D8:
                memory.pop(actor+i,None)
        for i in range(148):
            memory.pop(screen.TABLE+i,None)
        self.compare(memory)
        self.receipt('faults',fired_pairs=cuts,provider_accesses_excluded=True,hardware_PC_FCSR_not_claimed=True)

    def native_source(self,body):
        return r'''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;
u8 D_800CC2D0[26*0x32C] __attribute__((aligned(4))),wanted[26*0x32C] __attribute__((aligned(4)));
u8 output[128] __attribute__((aligned(4))),expectedOut[128] __attribute__((aligned(4)));
u8 alternate[128] __attribute__((aligned(4))),expectedAlt[128] __attribute__((aligned(4)));
s32 seen[8][5],expected[8][5],seenCount,wantCount,mode,current;
u32 translated(u8 *p){u32 n=(u32)p,b=(u32)wanted;
 if(n>=b && n-b<sizeof(wanted)){return (u32)D_800CC2D0+n-b;}
 b=(u32)expectedOut;if(n>=b && n-b<128){return (u32)output+n-b;}
 b=(u32)expectedAlt;if(n>=b && n-b<128){return (u32)alternate+n-b;}return n;}
void record(int actual,int id,s32 a,s32 b,s32 c,s32 d){s32 (*t)[5]=actual?seen:expected;int *n=actual?&seenCount:&wantCount;
 t[*n][0]=id;t[*n][1]=a;t[*n][2]=b;t[*n][3]=c;t[*n][4]=d;(*n)++;}
u8 *writeCommand(int actual,int id,u8 *p,s32 slot){u8 *a=(actual?D_800CC2D0:wanted)+current*0x32C;
 record(actual,id,(s32)translated(p),slot,0,0);*(s16*)p=(s16)(0x200+id);*(s16*)(p+2)=(s16)slot;
 if(mode==1){a[4]=112;*(u32*)(a+0x1D4)=0;}return mode==3?(actual?alternate:expectedAlt):p+4;}
s32 lookup(int actual,s32 kind,u32 index){u8 *a=(actual?D_800CC2D0:wanted)+current*0x32C;
 record(actual,10,kind,(s32)index,0,0);if(index==0 && mode==1)a[4]=123;return (kind*3+index*29)&255;}
u8 *finish(int actual,u8 *p,u8 *actor,s32 a,s32 b){record(actual,11,(s32)translated(p),(s32)translated(actor),a,b);
 *(s16*)p=0x400;*(s16*)(p+2)=(s16)(a^b);return mode==2 || mode==3?(actual?alternate:expectedAlt)+16:p+4;}
u8 *func_150341BC(u8 *p,s32 s){return writeCommand(1,1,p,s);}
u8 *func_150D8590(u16 *p,s32 s){return writeCommand(1,2,(u8*)p,s);}
u8 *func_150344A0(u8 *p,s32 s){return writeCommand(1,3,p,s);}
u8 *func_150B58F0(u8 *p,s32 s){return writeCommand(1,4,p,s);}
s32 func_150F1B48(u8 *p,s32 s){return (s32)writeCommand(1,5,p,s);}
u8 *func_15034420(u8 *p,s32 s){return writeCommand(1,6,p,s);}
u8 *func_150BE438(u8 *p,s32 s){return writeCommand(1,7,p,s);}
u8 *func_15034340(u8 *p,s32 s){return writeCommand(1,8,p,s);}
u8 *func_150343B0(u8 *p,s32 s){return writeCommand(1,9,p,s);}
s32 func_1503DA3C(s32 k,u32 i){return lookup(1,k,i);}
s32 func_15034860(u8 *p,u8 *a,s32 x,s32 y){return (s32)finish(1,p,a,x,y);}
void model(u8 *p,s32 slot){u8 *a=wanted+(u32)slot*0x32C;int id=0,k,x,y;
 if(!*(u32*)(a+0x1D4)){*(s16*)p=0x1000;return;}
 k=a[4];if(*(u32*)a==1)id=1;
 else if(k==43)id=2;else if(k==40 || k==119)id=3;else if(k==75)id=4;else if(k==123)id=5;
 else if(k==138)id=6;else if(k==33)id=7;else if(k==152)id=8;else if(k==90 || k==116 || k==122 || k==141)id=9;
 if(id){p=writeCommand(0,id,p,slot);}x=lookup(0,a[4],0);y=lookup(0,a[4],1);p=finish(0,p,a,x,y);*(s16*)p=0x1000;}
''' + body + r'''
int check(void){int kind,state,gate,m,alias,i,j,k;u8 *a,*p,*q;u32 states[]={0,1,34,0x10000001};
 if(sizeof(void*)!=4)return 9;
 for(kind=0;kind<256;kind++)for(state=0;state<4;state++)for(gate=0;gate<2;gate++)for(m=0;m<4;m++)for(alias=0;alias<2;alias++){
 current=(kind+state)%26;mode=m;seenCount=wantCount=0;
 for(i=0;i<(int)sizeof(wanted);i++)D_800CC2D0[i]=wanted[i]=(u8)(i*13+19);
 for(i=0;i<128;i++){output[i]=expectedOut[i]=(u8)(i*13+19);alternate[i]=expectedAlt[i]=(u8)(i*19+13);}
 a=D_800CC2D0+current*0x32C;*(u32*)a=states[state];a[4]=(u8)kind;*(u32*)(a+0x1D4)=(u32)gate;
 for(i=0;i<0x32C;i++)wanted[current*0x32C+i]=a[i];
 p=alias?a+4:output;q=alias?wanted+current*0x32C+4:expectedOut;
 model(q,current);func_15033FE0(p,current);
 if(seenCount!=wantCount)return 1;
 for(i=0;i<seenCount;i++)for(j=0;j<5;j++)if(seen[i][j]!=expected[i][j])return 2;
 for(k=0;k<(int)sizeof(wanted);k++)if(wanted[k]!=D_800CC2D0[k])return 3;
 for(k=0;k<128;k++)if(output[k]!=expectedOut[k] || alternate[k]!=expectedAlt[k])return 4;
 }return 0;}
void _start(void){int r=check();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");for(;;){}}
'''

    def test_04_native32_actual_source_and_effective_negatives(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(screen.SELECTED),profile),(0,''))
        cached=screen.SELECTED.replace('    first = func_1503DA3C(actor[4], 0);','    type = actor[4];\n    first = func_1503DA3C(type, 0);').replace(
            '    second = func_1503DA3C(actor[4], 1);','    second = func_1503DA3C(type, 1);')
        negatives={'cached-type':cached,'wrong-state':screen.SELECTED.replace('*(s32 *)actor == 1','*(s32 *)actor != 0'),
            'wrong-channel':screen.SELECTED.replace('actor[4], 1)','actor[4], 0)'),
            'wrong-terminator':screen.SELECTED.replace('= 0x1000;','= 0x2000;'),
            'ignored-final-cursor':screen.SELECTED.replace('    cursor = (u8 *)func_15034860','    (void)func_15034860')}
        for name,body in negatives.items():
            self.assertNotEqual(body,screen.SELECTED)
            self.assertIn(self.run_native('negative-'+name,self.native_source(body))[0],(1,2,3,4))
        self.receipt('native',cases_per_profile=16384,profiles=['O2','O0'],effective_negatives=5,
            synthetic26_record_backing=True,provider_calls_opaque=True)

    def test_05_owner_pool_translation_and_both_padders(self):
        objects=[screen.compile_owner(self.root,self.out,self.owner_before,'owner-before'),
                 (self.after_object,self.after_diagnostics)]
        self.assertEqual(objects[0][1],objects[1][1])
        before,after=[parse_object(obj) for obj,_ in objects]
        self.assertEqual(before[1].keys(),after[1].keys())
        for name in before[1]:
            if name==screen.FUNCTION:
                continue
            a,b=before[1][name],after[1][name]
            left=before[0][a['value']:a['value']+a['size']]
            right=bytearray(after[0][b['value']:b['value']+b['size']])
            relocations={o-b['value']:r for o,r in after[2].items() if b['value']<=o<b['value']+b['size']}
            old_relocations={o-a['value']:r for o,r in before[2].items() if a['value']<=o<a['value']+a['size']}
            self.assertEqual(relocations,old_relocations,name)
            if name=='func_1503453C':
                lo=[o for o,r in relocations.items() if ('R_MIPS_LO16','.rodata') in r]
                self.assertEqual(len(lo),1)
                offset=lo[0]
                word=struct.unpack_from('>I',right,offset)[0]
                self.assertEqual(word&65535,148)
                struct.pack_into('>I',right,offset,word&~65535)
            self.assertEqual(left,bytes(right),name)
        old,new=[normalized_pools(o) for o,_ in objects]
        self.assertEqual(old['.data'],new['.data'])
        self.assertEqual(new['.rodata'][0],bytes(176))
        suffix=tuple((o-148,name,delta) for o,name,delta in new['.rodata'][1] if o>=148)
        self.assertEqual(new['.rodata'][0][148:168],old['.rodata'][0][:20])
        self.assertEqual(suffix,old['.rodata'][1])
        self.assertEqual(len([r for r in new['.rodata'][1] if r[0]<148]),37)
        row=screen.neighbor_table_guard(objects[1][0])
        with self.assertRaisesRegex(ValueError,'already installed'):
            screen.guard_bytes(self.guard_after,objects[1][0])
        only=self.out/'table-only.csv'
        with only.open('w',newline='') as data:
            writer=csv.DictWriter(data,fieldnames=next(csv.reader((self.out/'before-guards').read_text().splitlines())))
            writer.writeheader()
            writer.writerow(row)
        emit_padded_assembly(objects[1][0],self.root/'conker/asm/61490.s',word_patches_path=only,
            filename='generated_61490',rodata_symbol=NEW_ANCHOR)
        offset=after[1][row['function']]['value']+int(row['offset'],0)
        bad=bytearray(after[0])
        bad[offset+3]^=1
        with patch('tools.pad_generated_object.parse_object',return_value=(bytes(bad),after[1],after[2])):
            with self.assertRaisesRegex(ValueError,'stale word'):
                emit_padded_assembly(objects[1][0],self.root/'conker/asm/61490.s',word_patches_path=only,
                    filename='generated_61490',rodata_symbol=NEW_ANCHOR)
        bad_relocations=dict(after[2])
        bad_relocations[offset]=[('R_MIPS_LO16','D_800CC2D0')]
        with patch('tools.pad_generated_object.parse_object',return_value=(after[0],after[1],bad_relocations)):
            with self.assertRaisesRegex(ValueError,'stale relocations'):
                emit_padded_assembly(objects[1][0],self.root/'conker/asm/61490.s',word_patches_path=only,
                    filename='generated_61490',rodata_symbol=NEW_ANCHOR)
        padded=[]
        for script in ('pad_c_object.py','pad_generated_object.py'):
            asm=self.out/(script+'.s')
            args=[str(objects[1][0]),str(self.root/'conker/retail_layout.us.txt'),'generated_61490',str(asm)] if script=='pad_c_object.py' else [
                str(objects[1][0]),str(self.root/'conker/asm/61490.s'),str(asm),'--filename','generated_61490']
            result=subprocess.run([sys.executable,str(self.root/'tools'/script),*args,'--word-patches',str(self.guards),
                '--rodata-symbol',NEW_ANCHOR],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
            obj=asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(self.root/'conker'),'-o',str(obj),str(asm)],check=True,capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0],padded[1])
        self.receipt('owner',neighbors=len(after[1])-1,both_full_padders=True,compiler_table_shift=148,retail_table_shift=160,
            new_table_entries=37,existing_table_suffix_fixed=True)

    def test_06_original_code_table_rebases_and_carry_sensitive_neighbor(self):
        original=(self.root/'conker/asm/61490.s').read_text().split('glabel '+screen.FUNCTION+'\n',1)[1]
        asm=self.out/'original.s'
        asm.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\nglabel '+screen.FUNCTION+'\n'+
            original.split('endlabel '+screen.FUNCTION,1)[0]+'endlabel '+screen.FUNCTION+'\n')
        obj=asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        for i,entry,table,actor in ((0,screen.ENTRY,screen.TABLE,ACTORS),(1,0x15233FE0,0x90007FFC,0x80118004),
                                   (2,0x15333FE0,0x90018004,0x80217FFC)):
            symbols=dict(screen.SYMBOLS,D_800CC2D0=actor)
            with patch.multiple(screen,ENTRY=entry,TABLE=table,SYMBOLS=symbols):
                _,candidate,pool=screen.compile_candidate(self.root,self.out,'rebase-'+str(i))
            ld=self.out/('original-'+str(i)+'.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            elf=ld.with_suffix('.elf')
            labels={'.L15034114_game_data':entry+0x134,'.L15034128_game_data':entry+0x148,
                    '.L15034150_game_data':entry+0x170,'jtbl_80097C80':table}
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%x for x in dict(symbols,**labels).items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            self.assertEqual(candidate,list(struct.unpack_from('>119I',sections(elf)['.text'][1])))
            expected=struct.pack('>37I',*[entry+x-screen.ENTRY for x in struct.unpack('>37I',self.table)])
            self.assertEqual(pool[:148],expected)
        before_object,_=screen.compile_owner(self.root,self.out,self.owner_before,'neighbor-owner-before')
        neighbor='func_1503453C'
        isolated=[]
        for side,object_path,anchor,guards in (
                ('before',before_object,OLD_ANCHOR,self.out/'before-guards'),
                ('after',self.after_object,NEW_ANCHOR,self.guards)):
            padded=self.out/('neighbor-'+side+'.s')
            padded.write_text(emit_padded_assembly(object_path,self.root/'conker/asm/61490.s',
                word_patches_path=guards,filename='generated_61490',rodata_symbol=anchor))
            padded_object=padded.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded_object),str(padded)],check=True,capture_output=True)
            text,functions,relocations=parse_object(padded_object)
            meta=functions[neighbor]
            output=['.text','.set noat','.set noreorder','.globl '+neighbor,'.type '+neighbor+',@function',neighbor+':']
            for relative in range(0,meta['size'],4):
                address=meta['value']+relative
                for kind,symbol in relocations.get(address,[]):
                    output.append('.reloc ., %s, %s'%(kind,symbol))
                output.append('.word 0x%08X'%struct.unpack_from('>I',text,address)[0])
            output.append('.size '+neighbor+',.-'+neighbor)
            asm=self.out/('isolated-neighbor-'+side+'.s')
            asm.write_text('\n'.join(output)+'\n')
            obj=asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
            isolated.append((obj,anchor))
        for i,entry,table,actor in ((0,0x1503453C,screen.TABLE,ACTORS),(1,0x1523453C,0x90007FFC,0x80118004),
                                   (2,0x1533453C,0x90018004,0x80217FFC)):
            linked=[]
            for side,(obj,anchor) in enumerate(isolated):
                ld=self.out/('neighbor-rebase-%d-%d.ld'%(i,side))
                ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=ld.with_suffix('.elf')
                symbols={'D_800CC2D4':actor+4,'func_1503B9BC':0x1503B9BC,anchor:table+(160 if side==0 else 0)}
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',neighbor,
                    *['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                linked.append(sections(elf)['.text'][1][:168])
            self.assertEqual(linked[0],linked[1])
        self.receipt('rebases',parent_links=3,neighbor_before_after_links=6,HI_LO_carry=True,
            original_table_bytes_stable=True)

    def test_07_connected_original_child_writer(self):
        child=list(struct.unpack_from('>97I',self.rom,0x6166C))
        count=0
        for kind,byte,phase in itertools.product((0,0x14,0x42,0x70,0x7B,255),(0,128,255),(0,8)):
            memory,actor=fixture(self.table,state=1,kind=kind)
            stream.put(memory,actor+0x1D1,byte,1)
            child_result=stream.StreamOracle(child,memory).run()
            expected=child_result.memory.copy()
            cursor=child_result.r[2]
            calls=[(PRIMARY,(OUTPUT,0))]
            first=provider(expected,LOOKUP,(kind,0),actor,0,phase)
            second=provider(expected,LOOKUP,(kind,1),actor,0,phase)
            calls.extend(((LOOKUP,(kind,0)),(LOOKUP,(kind,1)),(FINALIZER,(cursor,actor,first,second))))
            cursor=provider(expected,FINALIZER,(cursor,actor,first,second),actor,0,phase)
            stream.put(expected,cursor,0x1000,2)
            pair=[]
            for words in (self.retail,self.words):
                model=DispatchOracle(words,memory,phase=phase,connected={PRIMARY+i*4:w for i,w in enumerate(child)}).run()
                self.assertEqual(public(model.memory),public(expected))
                self.assertEqual(model.calls,calls)
                pair.append(model)
            self.assertEqual((pair[0].memory,pair[0].events,pair[0].r,pair[0].f),(pair[1].memory,pair[1].events,pair[1].r,pair[1].f))
            count+=1
        self.receipt('connected',cases=count,actual_child_words=97,parent_words=119,
            lookup_and_finalizer_opaque=True,full_gameplay_not_claimed=True)

    def test_08_literal_image_and_immutable_data_tables(self):
        current=(self.root/self.paths['elf']).read_bytes()
        source=(self.root/screen.SOURCE).read_text()
        expected=bytearray(self.before)
        installed=source==self.owner_after
        offset=elf_slot_offset(self.before,screen.ENTRY,476)
        self.assertEqual(offset,elf_slot_offset(current,screen.ENTRY,476))
        if installed:
            expected[offset:offset+476]=struct.pack('>119I',*self.words)
            with patch.multiple(descriptor.screen,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
                size_offset=descriptor.size_field(self.before)
            struct.pack_into('>I',expected,size_offset,476)
        else:
            self.assertEqual(source,self.owner_before)
        self.assertEqual(current,bytes(expected))
        self.assertEqual((self.root/self.paths['makefile']).read_text(),self.make_after if installed else self.make_before)
        self.assertEqual((self.root/self.paths['guards']).read_bytes(),self.guard_after if installed else (self.out/'before-guards').read_bytes())
        for name in ('progress','layout','rodata','symbols'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        for address,length in ((screen.TABLE,148),(0x80097D14,8),(0x80097D20,20)):
            off=elf_slot_offset(self.before,address,length)
            self.assertEqual(current[off:off+length],self.before[off:off+length])
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('linked-audit',installed=installed,matching_credit=int(installed),target_guard_rows_added=0,neighbor_guard_rows_added=1,
            changed_bytes=sum(a!=b for a,b in zip(self.before,current)),data=data)


if __name__=='__main__':
    unittest.main()
