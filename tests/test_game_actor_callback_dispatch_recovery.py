"""Semantic callback recovery; eight frame words remain deliberately unmatched."""
import hashlib
import csv
import itertools
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_callback_dispatch_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests import test_game_actor_renderer_install_match as native
from tools.check_game_data_layout import audit_layout

ACTORS, DISABLED, DISPATCH, COMMAND, ADJUST, OTHER, POSITION = screen.SYMBOLS.values()
ALT, BUFFER, BIG = 0x20000, 0x30000, 0x1503B9BC
COUNTS = {DISPATCH:1, COMMAND:4, ADJUST:3, OTHER:1, POSITION:1, BIG:1}


def fixture(index=0, state=1, kind=0, flag=0, enabled=1, disabled=0):
    memory = {STACK+i:165 for i in range(-0x800,0x100)}
    actor = (ACTORS+index*0x32C)&0xFFFFFFFF
    for base in (actor,ALT):
        memory.update({(base+i)&0xFFFFFFFF:(i*13+165)&255 for i in range(0x32C)})
        put(memory,base,state)
        put(memory,base+4,kind,1)
        put(memory,base+5,flag,1)
        put(memory,base+0x1D4,enabled)
    memory[DISABLED] = disabled
    return memory,actor


def mutation(memory,target,args,actor,mode,initial_sp,frame,dispatch_count):
    if target == DISPATCH and mode in (1,2):
        put(memory,actor,0x22 if mode==1 else 0)
        put(memory,actor+4,4 if mode==1 else 0x7B,1)
        if mode==2:
            put(memory,actor+0x1D4,0)
    if target == DISPATCH and mode==4 and dispatch_count==1:
        put(memory,initial_sp,0x80000001)
        put(memory,initial_sp-frame+0x18,ALT)
        put(memory,ALT,0)
        put(memory,ALT+4,0x60,1)
    if target == COMMAND and args[2]==9 and mode==3:
        memory[DISABLED]=255
        put(memory,initial_sp,0xFFFFFFFF)
    if target in (ADJUST,OTHER,POSITION,COMMAND):
        put(memory,actor+0xA0, read(memory,actor+0xA0,1)+1,1)


def reference(memory,index,mode=0,phase=0):
    memory = memory.copy()
    actor = (ACTORS+index*0x32C)&0xFFFFFFFF
    calls,number = [],0
    initial_sp = STACK+phase
    put(memory,initial_sp,index)
    def call(target,args):
        nonlocal number
        calls.append((target,args))
        if target==DISPATCH:
            number += 1
        mutation(memory,target,args,actor,mode,initial_sp,32,number)
    if read(memory,actor+0x1D4):
        if read(memory,actor)==1 or read(memory,actor+5,1)==7:
            call(DISPATCH,(index,))
            if mode==4:
                actor=ALT
        if read(memory,actor)==0x22:
            call(DISPATCH,(read(memory,initial_sp),))
        kind=read(memory,actor+4,1)
        if kind==4 and memory[DISABLED]==0:
            call(COMMAND,(0,read(memory,initial_sp),9,0))
            call(COMMAND,(0,read(memory,initial_sp),4,0))
        elif kind==0x70:
            call(ADJUST,(actor,10,11))
        elif kind==0x7B:
            call(OTHER,(actor,))
        elif kind==0x60:
            call(POSITION,(actor,))
    return memory,calls


class AccessFault(Exception):
    pass


class DispatchOracle(TriangleOracle):
    def __init__(self,words,memory,index=0,mode=0,phase=0,raw=False,connected=None):
        self.fault,self.accesses,self.in_hook = None,0,False
        super().__init__(words,memory,phase=phase,entry=screen.ENTRY,arguments=(index,),connected=connected)
        self.index,self.mode,self.raw = index,mode,raw
        self.actor=(ACTORS+index*0x32C)&0xFFFFFFFF
        self.dispatch_count=0

    def gate(self):
        if self.recording and not self.in_hook:
            if self.fault==self.accesses:
                raise AccessFault()
            self.accesses += 1

    def get(self,address,size):
        self.gate()
        return super().get(address,size)

    def put(self,address,value,size):
        self.gate()
        return super().put(address,value,size)

    def record_call(self,target):
        args=tuple(self.r[4:4+COUNTS[target]])
        self.calls.append((target,args))
        self.events.append(('CALL',target,args))
        if target==DISPATCH:
            self.dispatch_count += 1

    def hook(self,target):
        self.in_hook=True
        try:
            args=self.calls[-1][1]
            addresses={self.actor+4,self.actor+0xA0,DISABLED,ALT+4}
            for base in (self.actor,self.actor+0x1D4,self.before[29],
                         self.before[29]-(40 if self.raw else 32)+0x18,ALT):
                addresses.update(range(base,base+4))
            before={a:self.memory.get(a) for a in addresses}
            mutation(self.memory,target,args,self.actor,self.mode,self.before[29],40 if self.raw else 32,self.dispatch_count)
            for address in sorted(addresses):
                value=self.memory.get(address)
                if before[address]!=value:
                    self.events.append(('PROVIDER-BYTE',address,value))
            if target==DISPATCH and self.mode==4:
                self.actor=ALT
            for register in (1,2,3,*range(4,16),24,25):
                self.r[register]=0xA5000000+register
            self.f[:20]=[0xA5000000+i for i in range(20)]
        finally:
            self.in_hook=False


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x800<=a<STACK+0x100}


def logical_events(model):
    result=[]
    for event in model.events:
        if event[0] in ('R','W','PROVIDER-BYTE'):
            address=event[1]
            if model.raw and STACK-0x800<=address<model.before[29]:
                address += 8
            event=(event[0],address,*event[2:])
        result.append(event)
    return result


class GameActorCallbackDispatchRecoveryTests(unittest.TestCase):
    run_native=native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-callback-dispatch-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,caller=screen.CALLER_SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt',makefile='conker/Makefile')
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
        cls.caller_before=(cls.out/'before-caller').read_text()
        cls.caller_after=screen.recovered_caller(cls.caller_before)
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>81I',cls.rom,screen.ROM))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_complete_shape_exact_eight_frame_words_no_matching_claim(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(81,40,8,0,''))
        differences={i*4:(a,b) for i,(a,b) in enumerate(zip(self.words,self.retail)) if a!=b}
        self.assertEqual(differences,screen.FRAME_WORDS)
        for i,(before,after) in enumerate(zip(self.words,self.retail)):
            if i*4 not in screen.FRAME_WORDS:
                self.assertEqual(before,after)
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse([r for r in csv.DictReader(stream) if r['function']==screen.FUNCTION])

    def compare_case(self,memory,index,mode=0,phase=0):
        expected,calls=reference(memory,index,mode,phase)
        pair=[DispatchOracle(w,memory,index,mode,phase,raw=bool(i)).run() for i,w in enumerate((self.retail,self.words))]
        for model in pair:
            self.assertEqual(public(model.memory),public(expected))
            self.assertEqual(model.calls,calls)
            self.assertEqual(read(model.memory,STACK+phase),read(expected,STACK+phase))
        self.assertEqual(logical_events(pair[0]),logical_events(pair[1]))
        self.assertEqual((pair[0].r,pair[0].f,pair[0].visits),(pair[1].r,pair[1].f,pair[1].visits))
        return pair[0].visits

    def test_02_guest_all_types_live_mutations_and_incoming_home_contract(self):
        cases,coverage=0,set()
        for i,state,flag,enabled,disabled,mode,phase in itertools.product(range(256),
            (0,1,0x22,0x10000001),(0,7),(0,1),(0,255),range(4),(0,8)):
            index=(0,1,25,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[i%6]
            memory,_=fixture(index,state,i,flag,enabled,disabled)
            coverage.update(self.compare_case(memory,index,mode,phase))
            cases += 1
        homes=0
        for kind,index,phase in itertools.product((0,4,0x80,0xB0),(0,1,0xFFFFFFFF),(0,8)):
            memory,_=fixture(index,1,kind)
            self.compare_case(memory,index,4,phase)
            homes += 1
        self.assertEqual(cases,65536)
        self.assertEqual(homes,24)
        flag_cases=0
        for state,flag,kind,phase in itertools.product((0,0x22),(1,0x87,255),(4,0x70,0x7B),(0,8)):
            memory,_=fixture(state=state,kind=kind,flag=flag)
            self.compare_case(memory,0,phase=phase)
            flag_cases += 1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+324,4)))
        self.receipt('guest',cases=cases,guest_home_cases=homes,nonseven_flag_cases=flag_cases,covered_words=81,
            private_accesses_logically_rebased=True,hardware_frame_parity=False)

    def test_03_fired_access_cuts_preserve_public_prefixes_not_physical_frame(self):
        cuts=0
        for state,kind,flag,mode in ((0,4,0,3),(1,0,0,1),(0x22,0x70,0,0),(0,0x7B,7,2),(0,0x60,0,0)):
            memory,_=fixture(state=state,kind=kind,flag=flag)
            complete=DispatchOracle(self.retail,memory,mode=mode).run()
            for cut in range(complete.accesses):
                pair=[]
                for i,words in enumerate((self.retail,self.words)):
                    model=DispatchOracle(words,memory,mode=mode,raw=bool(i))
                    model.fault=cut
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses,cut)
                    pair.append(model)
                self.assertEqual((public(pair[0].memory),logical_events(pair[0]),pair[0].calls,pair[0].f),
                    (public(pair[1].memory),logical_events(pair[1]),pair[1].calls,pair[1].f))
                source=pair[1].r.copy()
                if source[29]<pair[1].before[29]:
                    source[29] += 8
                self.assertEqual(source,pair[0].r)
                cuts += 1
        memory,actor=fixture(enabled=0)
        for a in range(actor,actor+0x32C):
            if not actor+0x1D4<=a<actor+0x1D8:
                del memory[a]
        del memory[DISABLED]
        for words in (self.retail,self.words):
            self.assertEqual(DispatchOracle(words,memory).run().calls,[])
        self.receipt('faults',fired_pairs=cuts,provider_accesses_excluded=True,
            raw_SP_and_private_addresses_affinely_compared=True,physical_frame_not_exact=True)

    def native_source(self,body):
        return '''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
u8 D_800CC2D0[26*0x32C] __attribute__((aligned(4))),wanted[26*0x32C],D_800BE616;
int trace[16][5],expected[16][5],calls,wantCount,error,mode,current,dispatches,disabledWanted;
void record(int t,int a,int b,int c,int d){if(calls>=16){error=1;return;}trace[calls][0]=t;trace[calls][1]=a;
 trace[calls][2]=b;trace[calls][3]=c;trace[calls][4]=d;calls++;}
void mutate(u8 *data,int t,int cmd,int m,int n){u8 *a=data+current*0x32C;
 if(t==1 && (m==1 || m==2)){*(u32*)a=(m==1)?34:0;a[4]=(u8)((m==1)?4:123);if(m==2)*(u32*)(a+0x1D4)=0;}
 if(t==2 && cmd==9 && m==3){if(data==D_800CC2D0)D_800BE616=255;else disabledWanted=255;}
 if(t>=2)a[0xA0]++;
}
void func_1503453C(s32 x){record(1,x,0,0,0);dispatches++;mutate(D_800CC2D0,1,0,mode,dispatches);}
s32 func_15036310(s32 a,s32 b,s32 c,s32 d){record(2,a,b,c,d);mutate(D_800CC2D0,2,c,mode,dispatches);return 0;}
void func_15034EB4(u8 *a,s32 b,s32 c){record(3,(s32)a,b,c,0);mutate(D_800CC2D0,3,0,mode,dispatches);}
s32 func_150F1A00(u8 *a){record(4,(s32)a,0,0,0);mutate(D_800CC2D0,4,0,mode,dispatches);return 0;}
void func_150DFDA4(u8 *a){record(5,(s32)a,0,0,0);mutate(D_800CC2D0,5,0,mode,dispatches);}
void want(int t,int a,int b,int c,int d){expected[wantCount][0]=t;expected[wantCount][1]=a;expected[wantCount][2]=b;
 expected[wantCount][3]=c;expected[wantCount][4]=d;wantCount++;}
''' + body + '''
int check(void){int i,j,k,kind,state,flag,enabled,disabled,m,n;u8 *a;int states[]={0,1,34,0x10000001};int flagValues[]={7,1,0x87,255};
 if(sizeof(void*)!=4)return 9;
 for(kind=0;kind<256;kind++)for(state=0;state<4;state++)for(flag=0;flag<2;flag++)
 for(enabled=0;enabled<2;enabled++)for(disabled=0;disabled<2;disabled++)for(m=0;m<4;m++){
  current=(kind+state+flag)%26;mode=m;calls=wantCount=error=dispatches=0;disabledWanted=disabled?255:0;D_800BE616=(u8)disabledWanted;
  for(i=0;i<26*0x32C;i++)D_800CC2D0[i]=wanted[i]=(u8)(i*13+165);
  a=D_800CC2D0+current*0x32C;*(u32*)a=(u32)states[state];a[4]=(u8)kind;a[5]=(u8)(flag?flagValues[(kind+state+m)%4]:0);*(u32*)(a+0x1D4)=(u32)enabled;
  for(i=0;i<0x32C;i++){wanted[current*0x32C+i]=a[i];}
  a=wanted+current*0x32C;n=0;
  if(*(u32*)(a+0x1D4)){
   if(*(u32*)a==1 || a[5]==7){want(1,current,0,0,0);mutate(wanted,1,0,m,++n);}
   if(*(u32*)a==34){want(1,current,0,0,0);mutate(wanted,1,0,m,++n);}
   if(a[4]==4 && !disabledWanted){want(2,0,current,9,0);mutate(wanted,2,9,m,n);want(2,0,current,4,0);mutate(wanted,2,4,m,n);}
   else if(a[4]==112){want(3,(s32)(D_800CC2D0+current*0x32C),10,11,0);mutate(wanted,3,0,m,n);}
   else if(a[4]==123){want(4,(s32)(D_800CC2D0+current*0x32C),0,0,0);mutate(wanted,4,0,m,n);}
   else if(a[4]==96){want(5,(s32)(D_800CC2D0+current*0x32C),0,0,0);mutate(wanted,5,0,m,n);}
  }
  func_150345E4(current);
  if(error || calls!=wantCount || D_800BE616!=disabledWanted)return 1;
  for(i=0;i<calls;i++)for(j=0;j<5;j++)if(trace[i][j]!=expected[i][j])return 2;
  for(k=0;k<26*0x32C;k++)if(D_800CC2D0[k]!=wanted[k])return 3;
 }
 return 0;
}
void _start(void){int r=check();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");for(;;){}}
'''

    def test_04_native_actual_source_and_effective_semantic_negatives(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(screen.SELECTED),profile),(0,''))
        negatives={'cached-type':screen.SELECTED.replace('    type = actor[4];\n','').replace(
                '    if (*(s32 *)actor == 1','    type = actor[4];\n    if (*(s32 *)actor == 1'),
            'mutually-exclusive-state':screen.SELECTED.replace('    if (*(s32 *)actor == 0x22)','    else if (*(s32 *)actor == 0x22)'),
            'nonzero-flag':screen.SELECTED.replace('actor[5] == 7','actor[5] != 0'),
            'recheck-disable':screen.SELECTED.replace('                func_15036310(0, index, 4, 0);',
                '                if (D_800BE616 == 0) func_15036310(0, index, 4, 0);')}
        for name,body in negatives.items():
            self.assertNotEqual(body,screen.SELECTED)
            self.assertIn(self.run_native('negative-'+name,self.native_source(body))[0],(1,2,3))
        self.receipt('native',cases_per_profile=32768,profiles=['O2','O0'],effective_negatives=4,all_valid_indices=True)

    def test_05_both_owners_neighbors_pools_and_original_padders(self):
        counts=[]
        for filename,asm_file,before_source,after_source,anchor in (
            ('generated_61490','61490',self.owner_before,self.owner_after,'jtbl_80097D20_game'),
            ('generated_58F80','58F80',self.caller_before,self.caller_after,'jtbl_80096DF8_game')):
            objects=[screen.compile_owner(self.root,self.out,source,filename+'-'+name) for name,source in
                (('before',before_source),('after',after_source))]
            self.assertEqual(objects[0][1],objects[1][1])
            before,after=[parse_object(obj) for obj,_ in objects]
            self.assertEqual(before[1].keys(),after[1].keys())
            for name in before[1]:
                a,b=before[1][name],after[1][name]
                if name!=screen.FUNCTION:
                    self.assertEqual(before[0][a['value']:a['value']+a['size']],after[0][b['value']:b['value']+b['size']],name)
                    self.assertEqual({o-a['value']:r for o,r in before[2].items() if a['value']<=o<a['value']+a['size']},
                        {o-b['value']:r for o,r in after[2].items() if b['value']<=o<b['value']+b['size']},name)
            self.assertEqual(normalized_pools(objects[0][0]),normalized_pools(objects[1][0]))
            counts.append(len(after[1])-(filename=='generated_61490'))
            padded=[]
            for script in ('pad_c_object.py','pad_generated_object.py'):
                asm=self.out/(filename+'-'+script+'.s')
                args=[str(objects[1][0]),str(self.root/'conker/retail_layout.us.txt'),filename,str(asm)] if script=='pad_c_object.py' else [
                    str(objects[1][0]),str(self.root/'conker/asm'/(asm_file+'.s')),str(asm),'--filename',filename]
                result=subprocess.run([sys.executable,str(self.root/'tools'/script),*args,'--word-patches',
                    str(self.root/self.paths['guards']),'--rodata-symbol',anchor],capture_output=True,text=True)
                self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
                obj=asm.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(self.root/'conker'),'-o',str(obj),str(asm)],check=True,capture_output=True)
                padded.append(parse_object(obj))
            self.assertEqual(padded[0],padded[1])
        self.receipt('owner',unchanged_functions_per_owner=counts,both_full_padders=True,prototype_only_caller_change=True)

    def test_06_original_symbol_rebases_retain_only_eight_frame_differences(self):
        original=(self.root/'conker/asm/61490.s').read_text().split('glabel '+screen.FUNCTION+'\n',1)[1]
        asm=self.out/'original.s'
        asm.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\nglabel '+screen.FUNCTION+'\n'+
            original.split('endlabel '+screen.FUNCTION,1)[0]+'endlabel '+screen.FUNCTION+'\n')
        obj=asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        for i,entry,symbols in ((0,screen.ENTRY,screen.SYMBOLS),
            (1,0x152345E4,dict(screen.SYMBOLS,D_800CC2D0=0x80107FFC,D_800BE616=0x80218004)),
            (2,0x153345E4,dict(screen.SYMBOLS,D_800CC2D0=0x80318004,D_800BE616=0x80417FFC))):
            with patch.multiple(screen,ENTRY=entry,SYMBOLS=symbols):
                _,candidate=screen.compile_candidate(self.root,self.out,'rebase-'+str(i))
            ld=self.out/('original-'+str(i)+'.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            elf=ld.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            retail=struct.unpack_from('>81I',sections(elf)['.text'][1])
            self.assertEqual({j*4:(a,b) for j,(a,b) in enumerate(zip(candidate,retail)) if a!=b},screen.FRAME_WORDS)

    def test_07_whole_image_protected_inputs_and_no_new_credit(self):
        current=(self.root/self.paths['elf']).read_bytes()
        source=(self.root/screen.SOURCE).read_text()
        expected=bytearray(self.before)
        installed=source==self.owner_after
        if installed:
            offset=elf_slot_offset(self.before,screen.ENTRY,324)
            self.assertEqual(offset,elf_slot_offset(current,screen.ENTRY,324))
            expected[offset:offset+324]=struct.pack('>81I',*self.words)
            with patch.multiple(descriptor.screen,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
                size_offset=descriptor.size_field(self.before)
            struct.pack_into('>I',expected,size_offset,324)
        else:
            self.assertEqual(source,self.owner_before)
        self.assertEqual(current,bytes(expected))
        self.assertEqual((self.root/screen.CALLER_SOURCE).read_text(),self.caller_after if installed else self.caller_before)
        for name in ('guards','progress','layout','makefile'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('linked-audit',installed=installed,raw_still_different=8,new_matching_credit=0,
            changed_bytes=sum(a!=b for a,b in zip(self.before,current)),data=data)


if __name__=='__main__':
    unittest.main()
