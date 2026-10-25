"""Record callback loop: live providers, original caller, aliases and literal fault state."""
from pathlib import Path
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch
from tools.experiments import game_record_callback_loop_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
ENTRY=source.ENTRY
COUNT,BASE,TABLE,ACCUM,FLOAT=0x800D3094,0x800D3098,0x80082E30,0x800DCDC4,0x800DCD90
FIRST,SECOND=0x30000,0x31000
actual_table=(0, 0, 0, 352401772, 0, 0, 0, 0, 0, 0, 0, 0, 352401164, 0, 0, 0, 0, 352399540, 352403780, 352404204, 352404664, 352405324, 352406368, 352407404, 0, 0)

def put(m, a, value, size=4):
    for i,b in enumerate((value & ((1 << (8*size))-1)).to_bytes(size, 'big')):
        m[(a+i)&0xFFFFFFFF] = b


def get(m, a, size=4):
    return int.from_bytes(bytes(m[(a+i)&0xFFFFFFFF] for i in range(size)), 'big')


def public(m):
    return {a:b for a,b in m.items() if not STACK-1024 <= a < STACK+512}


def fixture(count, pattern, kind, synthetic):
    m = {STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
    for base in (FIRST,SECOND):
        m.update({base+i:(i*29+pattern*7)&255 for i in range(8*0x34)})
        for index in range(8):
            m[base+index*0x34+0x15] = (kind+index*4)&255 if synthetic else ((kind+index*4)%104)
    table = [0x17010000+4*i if (i+pattern)%3 else 0 for i in range(64)] if synthetic else list(actual_table)
    for i,target in enumerate(table):
        put(m,TABLE+4*i,target)
    put(m,COUNT,count)
    put(m,BASE,FIRST)
    put(m,ACCUM,0xDEADBEEF)
    put(m,FLOAT,0x80000000)
    # Large guest counts are terminated by an effective first callback.
    if count & 0x80000000:
        put(m,TABLE+(m[FIRST+0x15]>>2)*4,0x17010000)
    return m


def mutation(m, argument, mode, number):
    slot = (argument-(FIRST if FIRST<=argument<FIRST+8*0x34 else SECOND))//0x34
    if mode & 1:
        put(m,COUNT,0)
    elif mode & 2 and number==1:
        put(m,COUNT,6)
    if mode & 4:
        put(m,BASE,SECOND if get(m,BASE)==FIRST else FIRST)
    if mode & 8 and slot<7:
        next_base=get(m,BASE)
        m[next_base+(slot+1)*0x34+0x15]=72
    if mode & 16:
        put(m,TABLE+18*4,0)
    if mode & 32:
        put(m,ACCUM,0x12345678+number)
        put(m,FLOAT,0x3F000000+number)


def reference(initial, mode):
    m=dict(initial)
    put(m,ACCUM,0)
    put(m,FLOAT,0)
    index=0
    calls=[]
    while index<get(m,COUNT):
        assert index<8, 'Unbounded fixture'
        argument=get(m,BASE)+index*0x34
        target=get(m,TABLE+(m[argument+0x15]>>2)*4)
        if target:
            calls.append((target,(argument,)))
            mutation(m,argument,mode,len(calls))
        index+=1
    return public(m),calls


class Oracle(RayOracle):
    def __init__(self, words, m, mode, phase):
        TimingOracle.__init__(self,words,m,phase=phase,entry=ENTRY,arguments=())
        self.mode=mode
        self.saved=tuple(self.r[16:24])
        self.saved_sp=self.r[29]
        self.saved_fp=self.r[30]
        self.saved_ra=self.r[31]

    def record_call(self,target):
        self.calls.append((target,self.arguments(1)))
        self.events.append(('CALL',target,self.arguments(1)))

    def hook(self,target):
        argument=self.arguments(1)[0]
        assert FIRST<=argument<FIRST+8*0x34 or SECOND<=argument<SECOND+8*0x34
        mutation(self.memory,argument,self.mode,len(self.calls))
        for i in range(4):
            self.put(self.r[29]+4*i,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x76543210,0x89ABCDEF

def native_harness(body):
    return '#include <ultra64.h>\n'+source.TYPES+'\ns32 D_800D3094, D_800DCDC4;\nf32 D_800DCD90;\nDispatchRecord40490 *D_800D3098;\nRecordCallback40490 D_80082E30[64];\ntypedef char ABI[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(f32)==4 &&\n sizeof(DispatchRecord40490)==0x34 && __builtin_offsetof(DispatchRecord40490,kindFlags)==0x15)?1:-1];\nstatic DispatchRecord40490 actual[2][8], expected[2][8];\nstatic u32 mode, error, calls, wanted, expectedCount, expectedBase, expectedAccum, expectedFloat;\nstatic u32 expectedIDs[8], expectedSlots[8], expectedBases[8], shadowTable[64];\nstatic u32 bits(f32 value){ union{f32 f;u32 u;}v;v.f=value;return v.u; }\nstatic f32 real(u32 value){ union{f32 f;u32 u;}v;v.u=value;return v.f; }\nstatic void mutate_expected(u32 slot,u32 number){\n if(mode&1)expectedCount=0;else if((mode&2)&&number==1)expectedCount=6;\n if(mode&4)expectedBase^=1;\n if((mode&8)&&slot<7)expected[expectedBase][slot+1].kindFlags=72;\n if(mode&16)shadowTable[18]=0;\n if(mode&32){expectedAccum=0x12345678+number;expectedFloat=0x3F000000+number;}\n}\nstatic s32 callback(u32 id,DispatchRecord40490 *record){\n u32 bank,slot,found=0;\n if(calls>=wanted){error=1;return 0;}\n if(id!=expectedIDs[calls] || record!=&actual[expectedBases[calls]][expectedSlots[calls]])error=1;\n calls++;\n for(bank=0;bank<2;bank++)for(slot=0;slot<8;slot++)if(record==&actual[bank][slot]){\n  found=1;\n  if(mode&1)D_800D3094=0;else if((mode&2)&&calls==1)D_800D3094=6;\n  if(mode&4)D_800D3098=(D_800D3098==actual[0])?actual[1]:actual[0];\n  if((mode&8)&&slot<7)D_800D3098[slot+1].kindFlags=72;\n  if(mode&16)D_80082E30[18]=0;\n  if(mode&32){D_800DCDC4=0x12345678+calls;D_800DCD90=real(0x3F000000+calls);}\n }\n if(!found)error=1;\n return (s32)(0xA5000000u|id);\n}\nstatic s32 cb1(DispatchRecord40490 *p){return callback(1,p);}\nstatic s32 cb2(DispatchRecord40490 *p){return callback(2,p);}\nstatic s32 cb3(DispatchRecord40490 *p){return callback(3,p);}\nstatic s32 cb4(DispatchRecord40490 *p){return callback(4,p);}\nstatic RecordCallback40490 callbacks[5]={0,cb1,cb2,cb3,cb4};\n'+body+'\nstatic int one(u32 count,u32 kind,u32 pattern,u32 mut){\n u32 i,j,slot,bank,id;u8 *p=(u8*)actual,*q=(u8*)expected;\n error=calls=wanted=0;mode=mut;\n for(i=0;i<sizeof(actual);i++)p[i]=q[i]=(u8)(i*29+pattern*7);\n for(bank=0;bank<2;bank++)for(slot=0;slot<8;slot++){\n  actual[bank][slot].kindFlags=expected[bank][slot].kindFlags=(u8)(kind+slot*4);\n }\n for(i=0;i<64;i++){shadowTable[i]=(i+pattern)%5;D_80082E30[i]=callbacks[shadowTable[i]];}\n D_800D3094=(s32)count;D_800D3098=actual[0];D_800DCDC4=(s32)0xDEADBEEF;D_800DCD90=real(0x80000000);\n expectedCount=count;expectedBase=expectedAccum=expectedFloat=0;\n slot=0;\n while(slot<expectedCount){\n  if(slot>=8)return 25;\n  id=shadowTable[expected[expectedBase][slot].kindFlags/4];\n  if(id){\n   if(wanted>=8)return 25;\n   j=wanted++;expectedIDs[j]=id;expectedSlots[j]=slot;expectedBases[j]=expectedBase;\n   mutate_expected(slot,wanted);\n  }\n  slot++;\n }\n func_15013000();\n if(error||calls!=wanted||(u32)D_800D3094!=expectedCount||D_800D3098!=actual[expectedBase]||\n    (u32)D_800DCDC4!=expectedAccum||bits(D_800DCD90)!=expectedFloat)return 23;\n for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 23;\n for(i=0;i<64;i++)if(D_80082E30[i]!=callbacks[shadowTable[i]])return 23;\n return 0;\n}\nint run(void){\n static const u32 counts[]={0,1,2,4,6};\n static const u32 modes[]={0,1,2,4,8,16,32,6,12,24,36,63};\n u32 n,k,p,m;int result;\n for(n=0;n<5;n++)for(k=0;k<256;k++)for(p=0;p<5;p++)for(m=0;m<12;m++){\n  result=one(counts[n],k,p,modes[m]);if(result)return result;\n }\n return 0;\n}\n'+START

def controls():
    body=source.SELECTED
    controls={
     'missing_integer_reset':body.replace('D_800DCDC4 = 0;',''),
     'missing_float_reset':body.replace('D_800DCD90 = 0.0f;',''),
     'negative_zero_reset':body.replace('D_800DCD90 = 0.0f;','D_800DCD90 = -0.0f;'),
     'wrong_field':body.replace('kindFlags = D_800D3098[index].kindFlags;',
                               'kindFlags = D_800D3098[index].reserved[0x14];'),
     'wrong_shift':body.replace('kindFlags >> 2','kindFlags >> 3'),
     'wrong_callback_argument':body.replace('callback(&D_800D3098[index]);','callback(&D_800D3098[index + 1]);'),
     'cached_count':body.replace('u32 index;','u32 index;\n    u32 count = (u32)D_800D3094;').replace(
         'index < (u32)D_800D3094','index < count'),
     'cached_base':body.replace('u32 index;','u32 index;\n    DispatchRecord40490 *base = D_800D3098;').replace(
         'D_800D3098[index]','base[index]'),
    }
    return controls


class FaultOracle(Oracle):
    def __init__(self,*args,fault=None,**kwargs):
        self.in_root_instruction=False
        super().__init__(*args,**kwargs)
        self.fault_at=fault;self.own_accesses=0

    def execute(self,word):
        self.dispatched_word=word;self.in_root_instruction=True
        try:return super().execute(word)
        finally:self.in_root_instruction=False

    def access(self):
        if self.in_root_instruction and self.current_pc is not None and ENTRY<=self.current_pc<ENTRY+180:
            if self.own_accesses==self.fault_at:raise faults.AccessBoundary
            self.own_accesses+=1


class WindowBoundary(Exception):pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==0x15008094:raise WindowBoundary
        return super().__getitem__(pc)


class WindowOracle(FaultOracle):
    def __init__(self,window,body,memory,mode,phase):
        self.in_root_instruction=False
        connected={ENTRY+4*i:word for i,word in enumerate(body)}
        TimingOracle.__init__(self,window,memory,phase=phase,entry=0x15008074,arguments=(),connected=connected)
        self.mode=mode;self.fault_at=None;self.own_accesses=0
        self.saved=tuple(self.r[16:24]);self.saved_sp=self.r[29]
        self.code=WindowCode(self.code,self)

    def record_call(self,target):
        count=0 if target==ENTRY else 2 if target==0x1507DFE4 else 1
        args=self.arguments(count)
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target!=0x1507DFE4:
            number=sum(address not in (ENTRY,0x1507DFE4)for address,_ in self.calls)
            mutation(self.memory,self.arguments(1)[0],self.mode,number)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x76543210,0x89ABCDEF


def assemble(root,output,text,label):
    path=output/(label+'.s');obj=path.with_suffix('.o')
    path.write_text('.set noreorder\n.set noat\n.set mips3\n'+text)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(path)],check=True,capture_output=True)
    return obj


def GNU_rebases(root,output,original,candidate):
    symbols={key:int(key.split('_')[1],16)for key in
             ('D_800D3094','D_800D3098','D_80082E30','D_800DCDC4','D_800DCD90')}
    isolated=[]
    for label,obj in (('retail',original),('guarded',candidate)):
        text,functions,bindings=source.parse_object(obj)
        assembly,unresolved=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols)
        if unresolved:raise ValueError(unresolved)
        isolated.append(assemble(root,output,assembly,'rebase-'+label))
    result=[]
    for index in range(9):
        mapped={key:(value+index*0x10000)&0xFFFFFFFF for key,value in symbols.items()}
        if index>=3:
            lows=(0x7FFC,0x8004,0xFFF0,0x7FF8,0x8000)
            mapped={key:0x81200000+j*0x10000+lows[(j+index)%5]for j,key in enumerate(symbols)}
        entry=source.ENTRY+index*0x10000
        link=output/('rebase-%d.ld'%index)
        link.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        spans=[]
        for label,obj in zip(('retail','guarded'),isolated):
            elf=output/('rebase-%d-%s.elf'%(index,label))
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(link),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in mapped.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            spans.append(sections(elf)['.text'][1][:180])
        if spans[0]!=spans[1]:raise ValueError(('Independent rebase mismatch',index))
        result.append((entry,mapped,spans[0]))
    return result


class RecordCallbackLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD
        frozen_source=cls.out/'before-conker_src_game_40490.c'
        cls.installed=frozen_source.exists() and (ROOT/source.SOURCE).read_bytes().decode()==source.recovered_owner(frozen_source.read_bytes().decode())
        if cls.installed:
            cls.installed=True;source.audit_inputs(ROOT,cls.out)
        else:
            cls.installed=False;source.freeze(ROOT,cls.out)
        cls.values=source.snapshot(cls.out)
        cls.rom=cls.values['conker/conker.us.bin']
        cls.truth=struct.unpack_from('>45I',cls.rom,source.ROM)
        linked,functions=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=struct.unpack_from('>45I',linked,functions[source.FUNCTION]['value'])
        linked,functions=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.raw=struct.unpack_from('>45I',linked,functions[source.FUNCTION]['value'])
        cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')

    def test_01_canonical_owner_Make_schedule_and_effective_guards(self):
        raw,bindings=source.payload(self.out/'after-owner.o')
        source.checked_payload(raw,bindings)
        self.assertEqual(self.words,self.truth)
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['raw_differences'],q['new_guards'],q['preserved_neighbors']),
                         (45,40,14,14,31))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],5)
        for index in range(45):
            wrong=bytearray(raw);wrong[index*4]^=1
            with self.assertRaises(ValueError):source.checked_payload(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[('R_MIPS_HI16','UNEXPECTED')]
            with self.assertRaises(ValueError):source.checked_payload(raw,wrong)
        text,functions,relocations=source.parse_object(self.out/'after-owner.o')
        info=functions[source.FUNCTION];guard=self.out/'proposed-word-patches.csv'
        pad=source.ordinary_padder;word_count=binding_count=0
        for at in range(0x18,0x50,4):
            wrong=bytearray(text);wrong[info['value']+at]^=1
            with patch.object(pad,'parse_object',return_value=(bytes(wrong),functions,relocations)):
                with self.assertRaisesRegex(ValueError,'stale word patch'):
                    pad.emit_padded_assembly(self.out/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=guard)
            word_count+=1
            if at in bindings:
                wrong=dict(relocations);wrong[info['value']+at]=[('R_MIPS_HI16','UNEXPECTED')]
                with patch.object(pad,'parse_object',return_value=(text,functions,wrong)):
                    with self.assertRaisesRegex(ValueError,'stale relocations'):
                        pad.emit_padded_assembly(self.out/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=guard)
                binding_count+=1
        self.receipt.update(words=45,frame=40,raw_differences=14,new_guards=14,preserved_neighbors=31,
            raw_word_and_binding_negatives=57,padder_word_negatives=word_count,padder_binding_negatives=binding_count)

    def test_02_guest_live_count_base_flags_and_literal_normalized_state(self):
        cases=list(itertools.product((0,1,2,4,6),(0,1,2,4,8,16,32,6,12,24,36,63),range(4),(12,72),(False,)))
        cases.extend((1,0,pattern,kind,True)for pattern in (0,1)for kind in range(256))
        cases.extend((n,1,0,12,False)for n in (0x7FFFFFFF,0x80000000,0xFFFFFFFF))
        visits=set();count=0
        for n,mode,pattern,kind,synthetic in cases:
            m=fixture(n,pattern,kind,synthetic)
            if n==0x7FFFFFFF:put(m,TABLE+(m[FIRST+0x15]>>2)*4,0x17010000)
            wanted=reference(m,mode)
            for phase in (0,8):
                models=[]
                for words in (self.truth,self.words,self.raw):
                    model=Oracle(words,m,mode,phase).run()
                    self.assertEqual((public(model.memory),model.calls),wanted)
                    self.assertEqual(tuple(model.r[16:24]),model.saved)
                    self.assertEqual((model.r[29],model.r[30],model.r[31]),(model.saved_sp,model.saved_fp,model.saved_ra))
                    visits.update(model.visits);models.append(model)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(ENTRY,ENTRY+180,4))<=visits)
        self.receipt.update(guest_phases=count,instruction_runs=count*3,all45_words_executed=True,
            actual_table_entries=26,actual_nonnull_entries=9,synthetic_table_entries=64,
            exhaustive_synthetic_kind_bytes=256,large_counts_guest_only=True)

    def test_03_SDK_native32_profiles_and_effective_compiled_negatives(self):
        rows=[]
        for name,body,opt in [('selected',source.SELECTED,opt)for opt in ('-O0','-O2','-O3')]+[
                (name,body,'-O2')for name,body in controls().items()]:
            path=self.out/('native-'+name+opt+'.c');exe=path.with_suffix('.elf')
            path.write_text(native_harness(body))
            p=subprocess.run([*native_command(opt),str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True,timeout=120)
            self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''))
            run=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,timeout=120)
            self.assertEqual(run.returncode,0 if name=='selected'else 23,(name,opt,run.stdout,run.stderr))
            rows.append(dict(name=name,profile=opt,exit=run.returncode))
        self.receipt.update(native32_profiles=rows,cases_per_selected_profile=76800,trap_UBSan=True,
            synthetic_native_table=True,guest_aliases_not_portable_C_claims=True)

    def test_04_original_caller_and_actual_void_return_window(self):
        caller='func_15007B3C'
        assembly=self.values['conker/asm/nonmatchings/game_34F20/func_15007B3C.s'].decode()
        assembly=assembly.replace('glabel '+caller,'.globl '+caller+'\n.type '+caller+', @function\n'+caller+':').replace(
            'endlabel '+caller,'.size '+caller+', . - '+caller)
        obj=assemble(ROOT,self.out,'.text\n'+assembly,'original-caller')
        linked,functions=source.link_owner(ROOT,self.out,obj,'game_34F20')
        self.assertEqual(functions[caller]['size'],426*4)
        at=functions[caller]['value']
        self.assertEqual(linked[at:at+426*4],self.rom[0x34FEC:0x34FEC+426*4])
        jal=0x0C000000|((ENTRY>>2)&0x03FFFFFF)
        self.assertEqual([i for i in range(0,len(self.rom),4)if struct.unpack_from('>I',self.rom,i)[0]==jal],[0x35524])
        window=struct.unpack_from('>8I',self.rom,0x35524)
        self.assertEqual(window[:3],(jal,0,0x8FA2002C))
        count=0
        for n,mode,saved,phase in itertools.product((0,2,4),(0,1,6,63),(0,1,2,0x80000000,0xFFFFFFFF),(0,8)):
            m=fixture(n,0,72,False);put(m,STACK+phase+0x2C,saved);put(m,STACK+phase+0x30,0x81234560)
            wanted,calls=reference(m,mode)
            expected=[(ENTRY,())]+calls+([(0x1507DFE4,(0x81234560,(saved-1)&0xFFFFFFFF))]if saved else [])
            models=[]
            for words in (self.truth,self.words):
                model=WindowOracle(window,words,m,mode,phase)
                with self.assertRaises(WindowBoundary):model.run()
                self.assertEqual((public(model.memory),model.calls),(wanted,expected))
                self.assertEqual((tuple(model.r[16:24]),model.r[29]),(model.saved,model.saved_sp))
                models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(original_caller_words_locked=426,actual_caller_window_words=8,caller_window_phases=count,
            caller_return_value_overwritten=True,full_caller_gameplay_claimed=False)

    def test_05_record_global_stack_aliases_and_all_fired_access_prefixes(self):
        alias_count=fault_count=0
        for phase in (0,8):
            bases=[STACK+phase-40+x for x in (-21,0,16,20,24,28,32,36,40)]
            bases += [address-0x15 for address in (COUNT,BASE,TABLE,ACCUM,FLOAT)]
            for base in bases:
                with patch.object(sys.modules[__name__],'FIRST',base):
                    m=fixture(2,1,72,True)
                    models=[FaultOracle(words,m,0,phase).run()for words in (self.truth,self.words)]
                    self.assertEqual(complete(models[0]),complete(models[1]))
                    accesses=models[0].own_accesses
                    self.assertGreater(accesses,10)
                    for cut in range(accesses):
                        pair=[]
                        for words in (self.truth,self.words):
                            model=FaultOracle(words,m,0,phase,fault=cut)
                            with self.assertRaises(faults.AccessBoundary):model.run()
                            self.assertEqual(model.own_accesses,cut)
                            self.assertTrue(ENTRY<=model.current_pc<ENTRY+180)
                            self.assertEqual(model.dispatched_word,words[(model.current_pc-ENTRY)//4])
                            pair.append(model)
                        self.assertEqual((complete(pair[0]),pair[0].current_pc,pair[0].delay_of),
                                         (complete(pair[1]),pair[1].current_pc,pair[1].delay_of))
                        fault_count+=1
                    alias_count+=1
        self.receipt.update(guest_alias_phases=alias_count,fired_access_prefixes=fault_count,
            literal_private_fault_state=True,portable_C_fault_semantics_claimed=False)

    def test_06_independent_GNU_HI_LO_rebases_and_guest_execution(self):
        count=0
        for entry,mapped,span in GNU_rebases(ROOT,self.out,self.out/'original-target.o',self.out/'qualified-padded.o'):
            if entry==source.ENTRY:self.assertEqual(span,self.rom[source.ROM:source.ROM+180])
            with patch.multiple(sys.modules[__name__],ENTRY=entry,COUNT=mapped['D_800D3094'],BASE=mapped['D_800D3098'],
                    TABLE=mapped['D_80082E30'],ACCUM=mapped['D_800DCDC4'],FLOAT=mapped['D_800DCD90']):
                for n,mode,phase in itertools.product((0,2,6),(0,1,6,63),(0,8)):
                    m=fixture(n,1,72,True);wanted=reference(m,mode)
                    model=FaultOracle(struct.unpack('>45I',span),m,mode,phase).run()
                    self.assertEqual((public(model.memory),model.calls),wanted);count+=1
        self.receipt.update(independent_GNU_rebases=9,rebased_guest_phases=count,signed_low_carries=True)

    def test_07_strict_full_image_and_installed_input_negatives(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+180]
        actual=(self.out/'first-linked.elf').read_bytes()
        source.check_image(before,actual,truth)
        for offset in (0,24,100,len(actual)//2,len(actual)-1):
            wrong=bytearray(actual);wrong[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        mapping=dict(self.values)
        mapping[source.SOURCE]=source.recovered_owner(self.values[source.SOURCE].decode()).encode()
        mapping[source.OBJECT]=(self.out/'qualified-padded.o').read_bytes()
        mapping['conker/build/conker.us.elf']=actual
        mapping['conker/retail_word_patches.us.csv']=source.guard_bytes(self.values['conker/retail_word_patches.us.csv'],self.out/'after-owner.o')
        real_read=Path.read_bytes
        def reader(path):
            for name,data in mapping.items():
                if path==ROOT/name:return data
            return real_read(path)
        with patch.object(Path,'read_bytes',reader):source.audit_inputs(ROOT,self.out)
        negatives=[source.SOURCE,source.OBJECT,'conker/build/conker.us.elf','conker/retail_word_patches.us.csv',
            'conker/Makefile','conker/include/variables.h','conker/include/structs.h','conker/include/functions.h',
            'conker/progress.csv','conker/asm/nonmatchings/game_40490/func_15013000.s',source.CALLER_SOURCE,source.CALLER_OBJECT]
        for name in negatives:
            old=mapping[name];wrong=bytearray(old);wrong[0]^=1;mapping[name]=bytes(wrong)
            with patch.object(Path,'read_bytes',reader):
                with self.assertRaises(ValueError):source.audit_inputs(ROOT,self.out)
            mapping[name]=old
        old=mapping[source.OBJECT];mapping[source.OBJECT]=self.values[source.OBJECT]
        with patch.object(Path,'read_bytes',reader):
            with self.assertRaises(ValueError):source.audit_inputs(ROOT,self.out)
        mapping[source.OBJECT]=old
        self.receipt.update(strict_image_negatives=5,installed_input_negatives=len(negatives),
            valid_installed_map_passed=True,stale_object_rejected=True,metadata_exclusions=0)

    def test_08_actual_old_target_stub_is_effectively_wrong(self):
        linked,functions=source.link_owner(ROOT,self.out,self.out/'before-padded.o',source.OWNER)
        old=struct.unpack_from('>45I',linked,functions[source.FUNCTION]['value'])
        m=fixture(2,0,72,False);wanted=reference(m,0)
        model=Oracle(old,m,0,0).run()
        self.assertNotEqual((public(model.memory),model.calls),wanted)
        self.assertEqual(functions[source.FUNCTION]['size'],12)
        self.receipt.update(actual_old_stub_failed=True,old_stub_bytes=12)
