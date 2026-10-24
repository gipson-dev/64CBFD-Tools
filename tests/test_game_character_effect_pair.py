"""Character-effect pairs: literal o32 calls, defined native C and bounded providers."""
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_character_effect_pair as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
CREATE,ATTACH,EFFECT=0x1518D1C0,0x1514EC1C,0x1515D5F8
BASE_ALLOC,NODE_ALLOC,RELEASE=0x1515D520,0x1514EBA4,0x1516972C
TABLE=0x8008AA70
OWNERS=(0,1,0x30000,0x7FFFFFF0,0x7FFFFFFC,0x80000000,0x8000FFF0,0xFFFFFFFF)
RETURNS=(0,1,0x40000,0x80000000,0xFFFFFFFF)
MUTATED=(0x80007FF0,0x7FFFFFF8,0x8000FFF0,0xFFFFFFFF)
SYMBOLS={'func_1518D1C0':CREATE,'func_1514EC1C':ATTACH,'func_1515D5F8':EFFECT}
SYMBOLS.update({'D_%08X'%t['descriptor']:t['descriptor']for t in source.TARGETS.values()})


def signed(value):
    return value-0x100000000 if value&0x80000000 else value


def fixture():
    return {STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}|{0x60000+i:0xA5 for i in range(16)}


def reference(t,owner,results,mode,entered=STACK,symbols=None):
    s=SYMBOLS if symbols is None else symbols;calls=[];current=owner
    calls.append((s['func_1518D1C0'],(current,5,0,1,255,1,s['D_%08X'%t['descriptor']])))
    if mode&1:current=MUTATED[0]
    calls.append((s['func_1514EC1C'],(results[0],current,t['key'])))
    if mode&2:current=MUTATED[1]
    address=(current+20)&0xFFFFFFFF
    calls.append((s['func_1515D5F8'],(0xFFFF8000,(signed(address)>>16)&0xFFFFFFFF,address&65535,5,255,255,255,255,0,0)))
    if mode&4:current=MUTATED[2]
    calls.append((s['func_1514EC1C'],(results[1],current,24)))
    return calls


class PairOracle(TimingOracle):
    def __init__(self,words,memory,t,owner=0x30000,results=(0x40000,0x50000),mode=0,phase=0,
                 entry=None,connected=None,symbols=None):
        super().__init__(words,memory,phase=phase,entry=t['entry']if entry is None else entry,
                         arguments=(owner,),connected=connected)
        self.t=t;self.entered=STACK+phase;self.results=results;self.mode=mode;self.stage=0
        self.symbols=SYMBOLS if symbols is None else symbols

    def record_call(self,target):
        if target==self.t['entry']:
            self.entered=self.r[29];args=self.arguments(1)
        else:
            counts={self.symbols['func_1518D1C0']:7,self.symbols['func_1514EC1C']:3,
                    self.symbols['func_1515D5F8']:10}
            if target not in counts:raise AssertionError(('Unbounded pair provider',hex(target)))
            args=self.arguments(counts[target])
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        stage=self.stage;self.stage+=1
        if self.mode>>stage&1:put(self.memory,self.entered,MUTATED[stage])
        put(self.memory,0x60000+4*stage,0x12340000+stage)
        value=self.results[0]if stage==0 else self.results[1]if stage==2 else 0xABCDEF02
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=value


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc in self.ends:raise WindowBoundary
        return super().__getitem__(pc)


class HelperOracle(TimingOracle):
    def __init__(self,words,memory,entry,args,answer=0):
        super().__init__(words,memory,entry=entry,arguments=args)
        self.answer=answer

    def record_call(self,target):
        counts={BASE_ALLOC:4,NODE_ALLOC:3,RELEASE:1,0x16000000:1}
        if target not in counts:raise AssertionError(('Unbounded helper service',hex(target)))
        args=self.arguments(counts[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        answer=self.answer if target in(BASE_ALLOC,NODE_ALLOC)else 0xABCDEF00
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.r[2]=answer


def controls(name):
    b=source.SELECTED[name];t=source.TARGETS[name];descriptor='D_%08X'%t['descriptor']
    return dict(selected=b,
        wrong_descriptor=b.replace(descriptor,'D_%08X'%(0x800A58E4 if t['descriptor']==0x800A58D0 else 0x800A58D0)),
        wrong_type=b.replace('owner, 5, 0, 1','owner, 4, 0, 1'),
        wrong_priority=b.replace('0xFF, 1, D_','0xFE, 1, D_'),
        skip_null=b.replace('    func_1514EC1C(result, (s32)owner, 0x%X);'%t['key'],
                            '    if (result) func_1514EC1C(result, (s32)owner, 0x%X);'%t['key']),
        wrong_key=b.replace('(s32)owner, 0x%X)'%t['key'],'(s32)owner, 0xC)'),
        wrong_address=b.replace('owner + 0x14','owner + 0x10'),
        unsigned_high=b.replace('address >> 16','(u32)address >> 16'),
        narrow_low=b.replace('address & 0xFFFF','address & 0xFF'),
        wrong_companion=b.replace('                          5,','                          4,'),
        wrong_color=b.replace('5, 0xFF, 0xFF,','5, 0xFE, 0xFF,'),
        wrong_final=b.replace('0xFF, 0xFF, 0, 0);','0xFF, 0xFF, 0, 1);'),
        missing_attach=b.replace('    func_1514EC1C(result, (s32)owner, 0x18);',''))


def native_harness():
    text=source.HEADERS+source.DECLARATIONS+r'''
u8 D_800A58D0[20],D_800A58E4[20],D_800A58F8[20],D_800A590C[20];
static u8 low[0x20040];static u8 *bases[3],*wantedOwner,*wantedDescriptor;
static u32 stage,error,mode,wantedKey;
__attribute__((noinline,noclone)) s32 func_1518D1C0(void *owner,s32 type,s32 a,s32 b,u8 c,u8 d,void *descriptor){
 if(stage++!=0||owner!=wantedOwner||type!=5||a||b!=1||c!=255||d!=1||descriptor!=wantedDescriptor)error=1;
 wantedOwner[0]^=0x5A;return mode&1?0:(s32)0x87654321u;
}
__attribute__((noinline,noclone)) s32 func_1514EC1C(s32 result,s32 owner,s32 key){
 u32 before=stage++;s32 answer=before==1?(mode&1?0:(s32)0x87654321u):(mode&2?0:(s32)0x80000000u);
 if((before!=1&&before!=3)||result!=answer||(u8*)owner!=wantedOwner||key!=(s32)(before==1?wantedKey:24))error=1;
 wantedOwner[1]^=0x33;return 0x12345678;
}
__attribute__((noinline,noclone)) s32 func_1515D5F8(s32 kind,s32 high,s32 lowWord,s32 type,u8 r,u8 g,u8 b,u8 a,s32 x,s32 y){
 u32 address=(u32)(wantedOwner+20);s32 expectedHigh=(s32)(address>>16);if(address&0x80000000u)expectedHigh-=65536;
 if(stage++!=2||kind!=-32768||high!=expectedHigh||(u32)lowWord!=(address&65535)||type!=5||r!=255||g!=255||b!=255||a!=255||x||y)error=1;
 wantedOwner[2]^=0x77;return mode&2?0:(s32)0x80000000u;
}
static void *map(u32 address){
 u32 args[6]={address,0x20040,3,0x32,0xFFFFFFFFu,0};u32 result;
 __asm__ volatile("int $0x80":"=a"(result):"a"(90),"b"(args):"memory");return(void*)result;
}
typedef void (*Callback)(u8 *);
static int variant(Callback callback,u8 *descriptor,u32 key){
 u32 base,offset;wantedDescriptor=descriptor;wantedKey=key;
 for(base=0;base<3;base++)for(offset=0;offset<65536;offset++)for(mode=0;mode<4;mode++){
  wantedOwner=bases[base]+offset;wantedOwner[0]=0x11;wantedOwner[1]=0x22;wantedOwner[2]=0x33;wantedOwner[31]=0x44;
  stage=error=0;callback(wantedOwner);
  if(error||stage!=4||wantedOwner[0]!=(0x11^0x5A)||wantedOwner[1]!=0x22||wantedOwner[2]!=(0x33^0x77)||wantedOwner[31]!=0x44)return 23;
 }return 0;
}
'''
    for name,t in source.TARGETS.items():
        for label,body in controls(name).items():
            if label!='selected'and body==source.SELECTED[name]:raise ValueError('Ineffective native control '+label)
            text+=body.replace(name,name+'_'+label)+'\n'
    text+='int run(void){bases[0]=low;bases[1]=map(0x7FFF0000u);bases[2]=map(0x88000000u);\n'
    text+='if(bases[1]!=(u8*)0x7FFF0000u||bases[2]!=(u8*)0x88000000u)return 97;\n'
    for name,t in source.TARGETS.items():
        for label in controls(name):
            text+='if(variant(%s_%s,D_%08X,%d)!=%d)return %d;\n'%(name,label,t['descriptor'],t['key'],0 if label=='selected'else 23,11 if label=='selected'else 12)
    return text+'return 0;}\n'+START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')


class CharacterEffectPairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.words={};cls.truth={};cls.receipt={}
        obj=cls.out/'after-owner.o';data,fs=source.link_owner(ROOT,cls.out,obj,source.OWNER)
        for name,t in source.TARGETS.items():
            cls.words[name]=list(struct.unpack_from('>44I',data,fs[name]['value']))
            cls.truth[name]=list(struct.unpack_from('>44I',cls.rom,t['rom']))

    def test_01_direct_words_bindings_owner_and_actual_Make(self):
        for name in source.FUNCTIONS:
            self.assertEqual(self.words[name],self.truth[name]);self.assertEqual(self.words[name][0],0x27BDFFD0)
            self.assertEqual(source.payload(self.out/'after-owner.o',name),source.payload(source.original(ROOT,self.out,name),name))
            self.assertEqual(sum(map(len,source.payload(self.out/'after-owner.o',name)[1].values())),6)
            old,fs=source.link_owner(ROOT,self.out,self.out/'before-owner.o',source.OWNER)
            self.assertNotEqual(list(struct.unpack_from('>44I',old,fs[name]['value'])),self.truth[name])
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],74)
        self.assertTrue(json.loads((self.out/'make-shadow.json').read_text())[0]['complete_padded_object_equal'])
        self.receipt.update(functions=4,total_words=176,frame_each=48,bindings_each=6,new_guards=0,compiler_only=True,preserved_neighbors=74)

    def test_02_order_widths_NULL_and_late_guest_homes(self):
        count=0
        for name,t in source.TARGETS.items():
            visits=set()
            for owner,a,b,mode,phase in itertools.product(OWNERS,RETURNS,RETURNS,(0,1,2,4,8,15),(0,8)):
                memory=fixture();models=[PairOracle(words,memory,t,owner,(a,b),mode,phase).run()for words in(self.truth[name],self.words[name])]
                self.assertEqual(complete(models[0]),complete(models[1]));visits.update(models[0].visits)
                self.assertEqual(models[0].calls,reference(t,owner,(a,b),mode,STACK+phase))
                self.assertEqual(models[0].r[29],STACK+phase)
                self.assertEqual([read(models[0].memory,0x60000+4*i)for i in range(4)],[0x12340000+i for i in range(4)])
                count+=1
            self.assertTrue(set(range(t['entry'],t['entry']+176,4))<=visits)
        self.receipt.update(guest_phases=count,all_176_words_visited=True,unconditional_NULL_attachment=True,
            late_guest_argument_homes=True,portable_native_home_alias_claimed=False)

    def test_03_native32_defined_C_and_twelve_effective_controls(self):
        c=self.out/'native.c';c.write_text(native_harness())
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native-'+opt[1:]);p=subprocess.run(native_command(opt)+[str(c),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),p.stdout+p.stderr)
            p=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),opt)
        self.receipt.update(native_cases_per_function_per_optimization=3*65536*4,native_optimizations=3,
            defined_wrong_C_controls_each=12,trap_UBSan=True,actual_C_indirect_callback=True,
            native_allocated_storage_and_signed_high_addresses=True)

    def test_04_actual_registration_and_three_original_caller_windows(self):
        table=list(struct.unpack_from('>23I',self.rom,0x22F530));before=self.values['conker/build/conker.us.elf']
        at=source.elf_slot_offset(before,TABLE,92);self.assertEqual(before[at:at+92],self.rom[0x22F530:0x22F58C])
        count=0
        windows=((0x1514D230,0x1514D270),(0x1514D270,0x1514D2AC),(0x1514D2AC,0x1514D2F8))
        for name,t in source.TARGETS.items():
            ptr=struct.pack('>I',t['entry']);self.assertEqual(table[t['index']],t['entry'])
            self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[0x22F530+4*t['index']])
            jal=struct.pack('>I',0x0C000000|(t['entry']>>2&0x3FFFFFF))
            self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
            for start,end in windows:
                code=list(struct.unpack_from('>%dI'%((end-start)//4),self.rom,start-0x15000000+0x2D4B0))
                for enabled,selector,phase in itertools.product((0,1),(0,t['index']),(0,8)):
                    memory=fixture();put(memory,STACK+phase+0x48,0x30000);put(memory,STACK+phase+0x3C,0);put(memory,STACK+phase+0x40,0);put(memory,STACK+phase+0x44,0)
                    for i,word in enumerate(table):put(memory,TABLE+4*i,word)
                    memory[0x800A5ED8]=selector;memory[0x800A5EC0]=selector;put(memory,0x8008AB90,0x70000);memory[0x70000]=selector
                    models=[]
                    for words in(self.truth[name],self.words[name]):
                        connected=dict(zip(range(t['entry'],t['entry']+176,4),words))
                        model=PairOracle(code,memory,t,0x30000,phase=phase,entry=start,connected=connected)
                        model.r[2]=7 if enabled else 0;model.r[3]=7 if enabled else 0;model.r[16]=2 if enabled else 0;model.r[17]=1
                        ends=(end,0x1514D2FC)if start==0x1514D2AC else(end,)
                        for boundary in ends:model.code[boundary]=0
                        model.code=WindowCode(model.code,model);model.code.ends=ends
                        with self.assertRaises(WindowBoundary):model.run()
                        models.append(model)
                    self.assertEqual(complete(models[0]),complete(models[1]))
                    selected=[a for target,a in models[0].calls if target==t['entry']]
                    self.assertEqual(selected,[(0x30000,)]if enabled and selector else[]);count+=1
        self.receipt.update(original_caller_windows=3,caller_window_phases=count,actual_registration_indices=[6,4,5,7],table_entries=23,
            parent_is_live_placeholder=True,full_C_parent_or_broadcast_recovery_claimed=False)

    def test_05_original_attachment_and_retained_companion_helpers(self):
        attachment=list(struct.unpack_from('>49I',self.rom,0x17C0CC));effect=list(struct.unpack_from('>41I',self.rom,0x18AAA8))
        at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],EFFECT,164)
        self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+164],self.rom[0x18AAA8:0x18AB4C])
        visits=set();count=0;owner,node,head,record=0x30000,0x70000,0x80000,0x90000
        for value,answer,old_head,key,destructor in itertools.product((0,0x60000),(0,node),(0,head),(13,14,24),(-1,0,2)):
            memory=fixture()
            for base in(owner,node,head,record):memory.update({base+i:0xA5 for i in range(0x340)})
            put(memory,owner+0x2F4,old_head);put(memory,0x8008ABE8+4*key,record);put(memory,record+2,destructor,2)
            if destructor!=-1:put(memory,0x8008AB58+4*destructor,0x16000000)
            model=HelperOracle(attachment,memory,ATTACH,(value,owner,key),answer).run();visits.update(model.visits)
            expected=dict(memory);calls=[]
            if value:
                calls.append((NODE_ALLOC,(value,key,0)))
                if answer:
                    put(expected,node+20,old_head);put(expected,owner+0x2F4,node);put(expected,node+24,0)
                    if old_head:put(expected,old_head+24,node)
                else:calls.append((RELEASE if destructor==-1 else 0x16000000,(value,)))
            public=lambda m:{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
            self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls)
            self.assertEqual(model.r[2],answer if value else 0);count+=1
        self.assertTrue(set(range(ATTACH,ATTACH+196,4))<=visits)
        for answer in(0,node):
            memory=fixture();memory.update({node+i:0xA5 for i in range(64)})
            args=(0xFFFF8000,0xFFFF8001,0xFFF8,5,255,255,255,255,0,0)
            model=HelperOracle(effect,memory,EFFECT,args,answer)
            for i,a in enumerate(args):put(model.memory,STACK+4*i,a)
            model.run();visits.update(model.visits);self.assertEqual(model.calls,[(BASE_ALLOC,args[:4])])
            self.assertEqual(model.r[2],answer)
            if answer:
                self.assertEqual(bytes(model.memory[node+i]for i in range(4,12)),bytes((0,255,255,255,255,0,0,0)))
                self.assertEqual([read(model.memory,node+i,2)for i in(14,16,18)],[0x8000,0x8001,0xFFF8])
                self.assertEqual(bytes(model.memory[node+i]for i in range(44,48)),bytes((127,0,0,5)))
            count+=1
        self.assertTrue(set(range(EFFECT,EFFECT+164,4))<=visits)
        self.receipt.update(original_attachment_words=49,retained_assembly_companion_words=41,helper_phases=count,
            all_90_helper_words_visited=True,live_attachment_and_factory_stubs_uncredited=True,lower_providers_bounded=True)

    def linked(self,name,obj,entry,symbols,label):
        text,functions,bindings=source.parse_object(obj);asm,unknown=emit_function(text,functions[name],bindings,name,symbols);self.assertFalse(unknown)
        p=self.out/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',name,
            *['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>44I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_06_independent_rebases_and_fired_root_fault_prefixes(self):
        links=phases=cuts=0
        for name,t in source.TARGETS.items():
            for i,entry in enumerate((t['entry'],0x18017FFC,0x1A028000)):
                symbols=dict(SYMBOLS)
                if i:
                    symbols.update(dict(zip(('func_1518D1C0','func_1514EC1C','func_1515D5F8'),
                        (0x18207FFC,0x18308000,0x1840FFFC)if i==1 else(0x1B047FFC,0x1B058000,0x1B06FFFC))))
                    for j,t2 in enumerate(source.TARGETS.values()):symbols['D_%08X'%t2['descriptor']]=(0x81017FF0 if i==1 else 0x8200FFF0)+j*20
                objects=(source.original(ROOT,self.out,name),self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_179F30.c.o')
                images=[self.linked(name,obj,entry,symbols,'rebase-'+name+'-%d-%d'%(i,j))for j,obj in enumerate(objects)]
                self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2]);links+=3
                for owner,mode,phase in itertools.product(OWNERS,(0,15),(0,8)):
                    models=[PairOracle(w,fixture(),t,owner,mode=mode,phase=phase,entry=entry,symbols=symbols).run()for w in images]
                    self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]))
                    self.assertEqual(models[0].calls,reference(t,owner,(0x40000,0x50000),mode,STACK+phase,symbols));phases+=1
            for mode,phase in itertools.product((0,15),(0,8)):
                done=PairOracle(self.truth[name],fixture(),t,mode=mode,phase=phase).run()
                for cut in range(done.root_accesses):
                    models=[PairOracle(w,fixture(),t,mode=mode,phase=phase)for w in(self.truth[name],self.words[name])]
                    for model in models:
                        model.root_fault=cut
                        with self.assertRaises(faults.AccessBoundary):model.run()
                    self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,fired_root_fault_prefixes=cuts,portable_C_fault_claimed=False)

    def test_07_strict_image_and_named_metadata_controls(self):
        before=self.values['conker/build/conker.us.elf'];wanted=source.predicted_image(before,source.truths(self.values))
        positions=[0,len(wanted)-1,source.elf_slot_offset(before,0x80082B20,4)]
        positions.extend(source.elf_slot_offset(before,t['entry'],176)for t in source.TARGETS.values())
        positions.extend([at for at,name,_,_ in source.symbol_rows(before)if name in('D_800A58E4','D_800A58F8','D_800A590C')])
        for at in positions:
            wrong=bytearray(wanted);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),source.truths(self.values))
        with self.assertRaises(ValueError):source.check_image(before,wanted[:-1],source.truths(self.values))
        corrupted=bytearray(before);at=next(at for at,name,_,_ in source.symbol_rows(before)if name=='D_800A58E4');corrupted[at]^=1
        with self.assertRaises(ValueError):source.reorder_metadata(bytes(corrupted))
        self.receipt.update(strict_image_negatives=len(positions)+1,metadata_order_negative=True,metadata_exclusions=0,named_definitions_preserved=True)

    def test_08_frozen_current_inputs_and_installed_identity(self):
        source.check_inputs(ROOT,self.out,self.installed)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        self.receipt.update(focused_inputs=33,guard_manifest_byte_identical=True,installed=self.installed)


if __name__=='__main__':unittest.main()
