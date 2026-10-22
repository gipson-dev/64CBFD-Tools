"""Direct motion C, live-step aliases, independent links and bounded callback flow."""
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_five_field_motion as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd

ROOT=Path(__file__).resolve().parents[2]
STEP,ACCEL,ACTOR,TABLE=0x800BE9A4,0x8009FE2C,0x30000,0x80089CB8
FIELDS=(0x114,0x34,0x38,0x3C,0x40,0x44)
VELOCITIES=(0x110,0x114,0x118,0x11C,0x120)
VALUES=(0,0x80000000,bits(1.),bits(-1.),bits(.5),bits(-8.),0x33800000,0x3F800001,0x4B000001,0xCB000001,1,0x80000001)
TIMES=(0,0x80000000,bits(.5),bits(1.),bits(2.),bits(-.5),0x3F800001,1)
SYMBOLS={'D_800BE9A4':STEP,'D_8009FE2C':ACCEL}


def fixture(pattern=0,timestep=bits(1.),phase=0,actor=ACTOR,symbols=None):
    s=SYMBOLS if symbols is None else symbols
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x100,0x100)}
    for i in range(-16,0x140):m[actor+i]=(i*13+0xA5)&255
    for i,off in enumerate((*VELOCITIES,0x34,0x38,0x3C,0x40,0x44)):
        put(m,actor+off,VALUES[(pattern+i*3)%len(VALUES)])
    put(m,s['D_800BE9A4'],timestep);put(m,s['D_8009FE2C'],0xBF19999A)
    return m


def reference(memory,actor=ACTOR,symbols=None):
    s=SYMBOLS if symbols is None else symbols;m=dict(memory)
    def add_product(destination,left,right):
        product=bits(floating(read(m,left))*floating(read(m,right)))
        put(m,destination,bits(floating(read(m,destination))+floating(product)))
    add_product(actor+0x114,s['D_8009FE2C'],s['D_800BE9A4'])
    for dst,vel in zip(FIELDS[1:],VELOCITIES):add_product(actor+dst,actor+vel,s['D_800BE9A4'])
    return m


class MotionOracle(TimingOracle):
    def __init__(self,words,memory,phase=0,actor=ACTOR,entry=source.ENTRY,connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(actor,),connected=connected)
        self.trace=[]
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        assert target==source.ENTRY
        self.calls.append((target,self.arguments(1)));self.events.append(('CALL',target,self.arguments(1)))
    def hook(self,target):
        raise AssertionError(('Unexpected provider',hex(target)))
    def execute(self,word):
        if word>>26==32:
            self.dispatched_word=word;self.own_instruction=True
            try:
                rs,rt,imm=word>>21&31,word>>16&31,word&65535
                address=(self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF
                value=self.get(address,1);self.r[rt]=(value if value<128 else value-256)&0xFFFFFFFF
                self.r[0]=0
            finally:self.own_instruction=False
        else:super().execute(word)


def harness(bodies):
    return '#include <ultra64.h>\n'+source.DECLARATIONS+"""
f32 D_800BE9A4,D_8009FE2C;
typedef union{f32 f;u32 u;}Float;
typedef union{u32 w[88];u8 b[352];}Arena;
static Arena arena,expected;
typedef char Widths[(sizeof(void*)==4&&sizeof(f32)==4)?1:-1];
"""+bodies+"""
static u32 asWord(f32 f){Float v;v.f=f;return v.u;}
static f32 asFloat(u32 u){Float v;v.u=u;return v.f;}
static int runVariant(s32(*target)(u8*)){
 const u32 values[]={0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0xC1000000,0x33800000,0x3F800001,0x4B000001,0xCB000001,1,0x80000001};
 const u32 times[]={0,0x80000000,0x3F000000,0x3F800000,0x40000000,0xBF000000,0x3F800001,1};
 const u32 velocities[]={0x110,0x114,0x118,0x11C,0x120};
 const u32 fields[]={0x110,0x114,0x118,0x11C,0x120,0x34,0x38,0x3C,0x40,0x44};
 const u32 destinations[]={0x34,0x38,0x3C,0x40,0x44};
 u32 p,t,i,j,count=0;f32 product;u8*actor=arena.b+16;
 for(p=0;p<12;p++)for(t=0;t<8;t++){
  for(i=0;i<sizeof(Arena);i++)arena.b[i]=(u8)(i*13+0xA5);
  for(i=0;i<10;i++)arena.w[4+fields[i]/4]=values[(p+i*3)%12];
  for(i=0;i<sizeof(Arena);i++)expected.b[i]=arena.b[i];
  D_800BE9A4=asFloat(times[t]);D_8009FE2C=asFloat(0xBF19999A);
  product=D_8009FE2C*D_800BE9A4;
  expected.w[4+0x114/4]=asWord(asFloat(expected.w[4+0x114/4])+product);
  for(i=0;i<5;i++){
   product=asFloat(expected.w[4+velocities[i]/4])*D_800BE9A4;
   j=4+destinations[i]/4;expected.w[j]=asWord(asFloat(expected.w[j])+product);
  }
  if(target(actor)!=1)return 21;
  for(i=0;i<sizeof(Arena);i++)if(arena.b[i]!=expected.b[i])return 22;
  count++;
 }
 return count==96?0:23;
}
"""+"""
static int run(void){
 if(runVariant(selected))return 30;
 if(!runVariant(wrongGravity))return 31;
 if(!runVariant(wrongVelocity))return 32;
 if(!runVariant(wrongDestination))return 33;
 if(!runVariant(wrongReturn))return 34;
 if(!runVariant(oldVelocity))return 35;
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
"""


class FiveFieldMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True);cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>42I',cls.rom,source.ROM))
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        linked,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER);cls.words=list(struct.unpack_from('>42I',linked,fs[source.FUNCTION]['value']))
        cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,memory,actor=ACTOR,phase=0,symbols=None,images=None,entry=source.ENTRY):
        expected=reference(memory,actor,symbols)
        models=[MotionOracle(code,memory,phase,actor,entry).run()for code in images or (self.truth,self.words)]
        for m in models:
            self.assertEqual(m.memory,expected);self.assertEqual(m.r[2],1);self.assertFalse(m.calls)
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
        return models
    def test_01_direct_C_owner_Make_and_effective_stub(self):
        self.assertEqual(self.truth,self.words)
        self.assertEqual(source.payload(self.obj),source.payload(source.original(ROOT,self.out)))
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['relocations'],q['new_guards'],q['preserved_neighbors']),(42,0,4,0,3))
        self.assertTrue(q['compiler_only'])
        m=fixture();old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,168)
        stub=MotionOracle(struct.unpack_from('>42I',old,at),m).run()
        self.assertNotEqual(stub.memory,reference(m));self.assertEqual(stub.r[2],0)
        self.receipt.update(words=42,frame=0,bindings=4,new_guards=0,neighbors=3,old_stub_effectively_rejected=True)
    def test_02_float_order_aliases_fences_and_ABI(self):
        seen=set();count=0
        for p,t,phase,alias in itertools.product(range(12),TIMES,(0,8),(None,*FIELDS,*VELOCITIES)):
            actor=ACTOR if alias is None else STEP-alias
            m=fixture(p,t,phase,actor);models=self.compare(m,actor,phase);seen.update(models[0].visits);count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+168,4)))
        self.receipt.update(finite_guest_phases=count,all_words_visited=42,live_step_aliases=True,full_memory_fences_and_literal_state=True)
    def test_03_native32_and_effective_defined_controls(self):
        body=source.SELECTED
        variants={'selected':body,'wrongGravity':body.replace('D_8009FE2C *','0.6f *'),
            'wrongVelocity':body.replace('actor + 0x110','actor + 0x118'),
            'wrongDestination':body.replace('actor + 0x44','actor + 0x48'),
            'wrongReturn':body.replace('return 1','return 0'),
            'oldVelocity':body.replace('    *(f32 *)(actor + 0x114) +=','    f32 previous = *(f32 *)(actor + 0x114);\n    *(f32 *)(actor + 0x114) +=').replace('*(f32 *)(actor + 0x38) += *(f32 *)(actor + 0x114)','*(f32 *)(actor + 0x38) += previous')}
        bodies='\n'.join(b.replace(source.FUNCTION,n)for n,b in variants.items())
        for opt in ('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(harness(bodies))
            subprocess.run([*native_command(opt),'-fno-strict-aliasing',str(c),'-o',str(p)],cwd=ROOT,capture_output=True,check=True)
            subprocess.run([str(p)],capture_output=True,check=True)
        self.receipt.update(native32_cases_per_optimization=96,native_optimizations=['O0','O2','O3'],effective_defined_wrong_C_controls=5,trap_UBSan=True)
    def link_words(self,obj,entry,symbols,label):
        text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,symbols)
        self.assertFalse(unknown);p=self.out/label;ap=p.with_suffix('.s');op=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        ap.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+''.join('%s = 0x%X;\n'%x for x in symbols.items()))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,'-o',str(elf),str(op)],capture_output=True,check=True)
        return list(struct.unpack_from('>42I',sections(elf)['.text'][1]))
    def test_04_independent_relocations_and_fired_fault_prefixes(self):
        original=source.original(ROOT,self.out);count=cuts=0
        for i,(entry,step,accel)in enumerate(((0x17001000,0x800B7FFC,0x80097FFC),(0x17108000,0x800B8000,0x80098000),(0x1720FFFC,0x800CFFFC,0x800A0000))):
            s={'D_800BE9A4':step,'D_8009FE2C':accel}
            a=self.link_words(original,entry,s,'original-rebase'+str(i));b=self.link_words(self.obj,entry,s,'C-rebase'+str(i));self.assertEqual(a,b)
            for phase,alias in itertools.product((0,8),(None,0x114,0x34,0x44)):
                actor=ACTOR if alias is None else step-alias;m=fixture(i,TIMES[i+3],phase,actor,s)
                self.compare(m,actor,phase,s,(a,b),entry);count+=1
        for phase,alias in itertools.product((0,8),(None,0x114,0x34,0x44)):
            actor=ACTOR if alias is None else STEP-alias;m=fixture(4,bits(1.),phase,actor)
            good=MotionOracle(self.truth,m,phase,actor).run()
            for cut in range(good.root_accesses):
                models=[MotionOracle(code,m,phase,actor)for code in (self.truth,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=6,rebase_phases=count,fired_root_fault_prefixes=cuts,portable_C_fault_or_MMU_claimed=False)
    def test_05_actual_callback_table_and_continuation(self):
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22E788)[0],source.ENTRY)
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));ptr=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[0x22E788])
        start,stop=0x1513D034,0x1513D070;window=list(struct.unpack_from('>16I',self.rom,0x16A4E4));count=0
        for phase,flag in itertools.product((0,8),(0,1,0x7F,0x80,0xFF)):
            m=fixture(3,bits(.5),phase);m[ACTOR+0x70]=4;put(m,TABLE+16,source.ENTRY)
            models=[]
            for leaf in (self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(leaf)}
                model=MotionOracle(window,m,phase,ACTOR,start,connected);model.r[7]=flag
                model.code=StopCode(model.code,model,stop)
                with self.assertRaises(WindowEnd):model.run()
                models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]))
            a=models[0];self.assertEqual(a.calls,[(source.ENTRY,(ACTOR,))]);self.assertEqual(a.r[4],ACTOR)
            self.assertEqual(a.r[7],(flag if flag<128 else flag-256)&0xFFFFFFFF)
            expected=reference(m)
            for address,value in expected.items():
                if not STACK-0x100<=address<STACK+0x100:self.assertEqual(a.memory[address],value)
            count+=1
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,0x1513CFE4,12)
        self.assertEqual(struct.unpack_from('>3I',old,at),(0x00001025,0x03E00008,0))
        self.receipt.update(actual_callback_slot=4,actual_caller_window_phases=count,return_branch_and_signed_flag_reload_executed=True,current_full_dispatcher_still_stub=True,full_dispatcher_or_gameplay_not_claimed=True)
    def test_06_pinned_inputs_and_strict_image_corruptions(self):
        for name,old in self.values.items():
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.predicted_image(old,self.rom[source.ROM:source.ROM+168])if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name);self.assertEqual(source.digest(old),source.INPUTS[name])
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+168];pred=source.predicted_image(before,truth)
        symbols={n:(at,fields,string)for at,n,fields,string in source.symbol_rows(before)}
        controls=(symbols[source.FUNCTION][0]+8,symbols['D_800D9910'][0]+4,symbols['D_800D1340'][2])
        for at in (0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,168),source.elf_slot_offset(pred,0x150BA424,4),source.elf_slot_offset(pred,0x80082B20,4),*controls):
            wrong=bytearray(pred);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        before_symbols={(n,*fields[1:])for _,n,fields,_ in source.symbol_rows(before)}
        after_symbols={(n,*fields[1:])for _,n,fields,_ in source.symbol_rows(pred)}
        self.assertEqual(before_symbols-after_symbols,{(source.FUNCTION,source.ENTRY,12,18,0,5)})
        self.assertEqual(after_symbols-before_symbols,{(source.FUNCTION,source.ENTRY,168,18,0,5)})
        self.receipt.update(pinned_inputs=len(self.values),whole_image_corruption_controls=8,absolute_symbol_serialization_closed=True,guards_and_conversion_rows_unchanged=True,metadata_exclusions=0)

    def test_07_effective_cached_step_C_control(self):
        body=source.SELECTED.replace('    *(f32 *)(actor + 0x114) +=',
            '    f32 cached = D_800BE9A4;\n    *(f32 *)(actor + 0x114) +=',1)
        body=body.replace('* D_800BE9A4','* cached')
        obj,diag=source.compile_owner(ROOT,self.out,'#include <ultra64.h>\n'+source.DECLARATIONS+body,'wrong-cached-step')
        self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);f=fs[source.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
        actor=STEP-0x114;m=fixture(2,bits(1.),actor=actor)
        wrong=MotionOracle(words,m,actor=actor).run()
        self.assertNotEqual(wrong.memory,reference(m,actor))
        self.receipt.update(effective_cached_step_wrong_C=True,alias_witness_is_bounded_guest_memory_not_portable_C_global_alias_claim=True)


if __name__=='__main__':unittest.main()
