"""Snapshot bits, damping capture, live timestep, copy guards and retail callback."""
import csv,io,itertools,json,struct,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_damped_motion_snapshot as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_five_field_motion import MotionOracle
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
ENTRY,STEP,ACTOR,TABLE=0x1514A4EC,0x800BE9A4,0x30000,0x80089CB8
POS,HISTORY,VEL=(0x34,0x38,0x3C),(0x40,0x44,0x48),(0x130,0x134,0x138)
VALUES=(0,0x80000000,bits(1.),bits(-1.),bits(.5),bits(-8.),bits(2.),bits(16.),0x3F800001,0x3F7FFFFF,1,0x80000001)
TIMES=(0,0x80000000,bits(.5),bits(1.),bits(2.),bits(-.5),0x3F800001,1)


def fixture(pattern=0,timestep=bits(1.),phase=0,actor=ACTOR,step=STEP):
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x500,0x200)}
    for i in range(-16,0x160):m[actor+i]=(i*13+0xA5)&255
    for i,off in enumerate((*POS,*VEL,0x13C,0x140)):put(m,actor+off,VALUES[(pattern+i*3)%12])
    put(m,step,timestep);return m


def reference(memory,actor=ACTOR,step=STEP):
    m=dict(memory);damping=read(m,actor+0x140)
    for dst,src in zip(HISTORY,POS):put(m,actor+dst,read(m,actor+src))
    def multiply(a,b):return bits(floating(a)*floating(b))
    put(m,actor+0x130,multiply(read(m,actor+0x130),damping))
    acceleration=multiply(read(m,actor+0x13C),read(m,step))
    put(m,actor+0x134,bits(floating(read(m,actor+0x134))+floating(acceleration)))
    put(m,actor+0x138,multiply(read(m,actor+0x138),damping))
    for dst,vel in zip(POS,VEL):
        value=multiply(read(m,actor+vel),read(m,step))
        put(m,actor+dst,bits(floating(read(m,actor+dst))+floating(value)))
    return m


class SnapshotOracle(MotionOracle):
    def __init__(self,words,memory,phase=0,actor=ACTOR,entry=ENTRY,connected=None):
        super().__init__(words,memory,phase,actor,entry,connected)
    def record_call(self,target):
        assert target==ENTRY
        self.calls.append((target,self.arguments(1)));self.events.append(('CALL',target,self.arguments(1)))


def native_harness(bodies):
    return '#include <ultra64.h>\n'+source.DECLARATIONS+r'''
f32 D_800BE9A4;
typedef union{u32 word;f32 number;}Float;
typedef union{u32 words[100];u8 bytes[400];}Arena;
static Arena arena,expected;
static f32 asFloat(u32 w){Float f;f.word=w;return f.number;}
static u32 asWord(f32 n){Float f;f.number=n;return f.word;}
'''+bodies+r'''
static int runVariant(s32(*target)(u8*)){
 const u32 values[]={0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0xC1000000,0x40000000,0x41800000,0x3F800001,0x3F7FFFFF,1,0x80000001};
 const u32 times[]={0,0x80000000,0x3F000000,0x3F800000,0x40000000,0xBF000000,0x3F800001,1};
 const u32 fields[]={0x34,0x38,0x3C,0x130,0x134,0x138,0x13C,0x140};
 const u32 positions[]={0x34,0x38,0x3C},history[]={0x40,0x44,0x48},velocities[]={0x130,0x134,0x138};
 u32 p,t,i,j,count=0;f32 damping,product;u8*actor=arena.bytes+16;
 for(p=0;p<12;p++)for(t=0;t<8;t++){
  for(i=0;i<sizeof(Arena);i++)arena.bytes[i]=(u8)(i*13+0xA5);
  for(i=0;i<8;i++)arena.words[4+fields[i]/4]=values[(p+i*3)%12];
  for(i=0;i<sizeof(Arena);i++)expected.bytes[i]=arena.bytes[i];
  D_800BE9A4=asFloat(times[t]);damping=asFloat(expected.words[4+0x140/4]);
  for(i=0;i<3;i++)expected.words[4+history[i]/4]=expected.words[4+positions[i]/4];
  expected.words[4+0x130/4]=asWord(asFloat(expected.words[4+0x130/4])*damping);
  product=asFloat(expected.words[4+0x13C/4])*D_800BE9A4;
  expected.words[4+0x134/4]=asWord(asFloat(expected.words[4+0x134/4])+product);
  expected.words[4+0x138/4]=asWord(asFloat(expected.words[4+0x138/4])*damping);
  for(i=0;i<3;i++){
   product=asFloat(expected.words[4+velocities[i]/4])*D_800BE9A4;
   j=4+positions[i]/4;expected.words[j]=asWord(asFloat(expected.words[j])+product);
  }
  if(target(actor)!=1)return 21;
  for(i=0;i<sizeof(Arena);i++)if(arena.bytes[i]!=expected.bytes[i])return 22;
  count++;
 }
 return count==96?0:23;
}
static int run(void){
 if(runVariant(selected))return 30;
 if(!runVariant(lateSnapshot))return 31;
 if(!runVariant(narrowSnapshot))return 32;
 if(!runVariant(noZDamping))return 33;
 if(!runVariant(dampedY))return 34;
 if(!runVariant(oldY))return 35;
 if(!runVariant(fixedStep))return 36;
 if(!runVariant(wrongReturn))return 37;
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class DampedMotionSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True);cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>42I',cls.rom,source.ROM))
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER);raw=data[fs[source.FUNCTION]['value']:fs[source.FUNCTION]['value']+168]
        cls.raw=list(struct.unpack('>42I',raw));cls.fitted=list(struct.unpack('>42I',source.patch_copy(raw)));cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def relation(self,retail,raw,actor):
        self.assertEqual(retail.memory,raw.memory);self.assertEqual(retail.f,raw.f)
        self.assertEqual((retail.hi,retail.lo,retail.condition),(raw.hi,raw.lo,raw.condition))
        for i in range(32):
            if i not in(1,14,15,24):self.assertEqual(retail.r[i],raw.r[i],i)
        x,y,z=(read(retail.memory,actor+off)for off in HISTORY)
        self.assertEqual((raw.r[14],raw.r[15],raw.r[24]),(x,y,z))
        self.assertEqual((retail.r[1],retail.r[24]),(z,y))
        self.assertEqual(raw.r[1],raw.before[1])
        self.assertEqual(retail.r[14:16],retail.before[14:16])
    def compare(self,memory,actor=ACTOR,phase=0,step=STEP,images=None,entry=ENTRY):
        expected=reference(memory,actor,step)
        models=[SnapshotOracle(code,memory,phase,actor,entry).run()for code in images or(self.truth,self.raw,self.fitted)]
        for m in models:self.assertEqual(m.memory,expected);self.assertEqual(m.r[2],1);self.assertFalse(m.calls)
        self.relation(models[0],models[1],actor);self.assertEqual(complete(models[0]),complete(models[2]))
        self.assertEqual(models[0].trace,models[2].trace)
        return models
    def test_01_owner_Make_guarded_copy_and_effective_stub(self):
        self.assertEqual(self.fitted,self.truth);self.assertEqual(sum(a!=b for a,b in zip(self.raw,self.truth)),7)
        self.assertEqual(source.normalized(*source.payload(self.obj)),source.payload(source.original(ROOT,self.out)))
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['words'],q['frame'],q['relocations'],q['new_guards'],q['preserved_neighbors']),(42,0,2,7,35));self.assertFalse(q['compiler_only'])
        memory=fixture(4);old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,ENTRY,168)
        stub=SnapshotOracle(struct.unpack_from('>42I',old,at),memory).run()
        self.assertEqual(stub.r[2],0);self.assertNotEqual(stub.memory,reference(memory))
        self.receipt.update(words=42,frame=0,bindings=2,new_guards=7,neighbors=35,old_stub_effectively_rejected=True)
    def test_02_finite_values_live_aliases_fences_and_raw_register_relation(self):
        seen=set();count=0
        for p,t,phase,alias in itertools.product(range(12),TIMES,(0,8),(None,*HISTORY,*VEL,*POS,0x13C,0x140)):
            actor=ACTOR if alias is None else STEP-alias
            a=self.compare(fixture(p,t,phase,actor),actor,phase)[0];seen.update(a.visits);count+=1
        self.assertEqual(count,2304);self.assertEqual(seen,set(range(ENTRY,ENTRY+168,4)))
        self.receipt.update(finite_guest_phases=count,all_words_visited=42,live_step_aliases=True,full_memory_fences=True,raw_copy_register_relation_qualified=True)
    def test_03_bit_exact_snapshot_and_effective_cached_step_C(self):
        phases=0
        for values,phase in itertools.product(((0x7FC12345,0x80000000,0x7F800001),(0xFFFFFFFF,0x12345678,0x7FFFFFFF),(1,0x80000001,0),(0x7F800000,0xFF800000,0x7F7FFFFF)),(0,8)):
            memory=fixture(2,phase=phase)
            for off,value in zip(POS,values):put(memory,ACTOR+off,value)
            models=[SnapshotOracle(w,memory,phase).run()for w in(self.truth,self.raw,self.fitted)]
            for m in models:self.assertEqual(tuple(read(m.memory,ACTOR+off)for off in HISTORY),values)
            self.relation(models[0],models[1],ACTOR);self.assertEqual(complete(models[0]),complete(models[2]));phases+=1
        body=source.SELECTED.replace('    f32 damping','    f32 timestep = D_800BE9A4;\n    f32 damping',1).replace('* D_800BE9A4','* timestep')
        obj,diag=source.compile_owner(ROOT,self.out,'#include <ultra64.h>\n'+source.DECLARATIONS+body,'cached-step-control');self.assertFalse(diag)
        data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
        actor=STEP-0x40;memory=fixture(4,bits(1.),actor=actor);wrong=SnapshotOracle(words,memory,actor=actor).run()
        self.assertNotEqual(wrong.memory,reference(memory,actor))
        self.receipt.update(raw_snapshot_bit_pattern_phases=phases,effective_cached_step_wrong_C=True,guest_NaN_transport_not_FCSR_or_hardware_acceptance=True)
    def test_04_native32_and_effective_defined_wrong_C(self):
        b=source.SELECTED
        copy='\n'.join('    *(u32 *)(actor + 0x%X) = *(u32 *)(actor + 0x%X);'%pair for pair in zip(HISTORY,POS))
        self.assertIn(copy,b)
        variants={'selected':b,'lateSnapshot':b.replace(copy+'\n','').replace('    return 1;',copy+'\n    return 1;'),
            'narrowSnapshot':b.replace('*(u32 *)(actor + 0x40) = *(u32 *)(actor + 0x34)','*(u16 *)(actor + 0x40) = *(u16 *)(actor + 0x34)'),
            'noZDamping':b.replace('*(f32 *)(actor + 0x138) *= damping','*(f32 *)(actor + 0x138) *= 1.0f'),
            'dampedY':b.replace('*(f32 *)(actor + 0x134) +=','*(f32 *)(actor + 0x134) = *(f32 *)(actor + 0x134) * damping +'),
            'oldY':b.replace('    f32 damping','    f32 oldVertical = *(f32 *)(actor + 0x134);\n    f32 damping',1).replace('*(f32 *)(actor + 0x38) += *(f32 *)(actor + 0x134)','*(f32 *)(actor + 0x38) += oldVertical'),
            'fixedStep':b.replace('D_800BE9A4','1.0f'),'wrongReturn':b.replace('return 1;','return 0;')}
        self.assertTrue(all(v!=b for n,v in variants.items()if n!='selected'))
        bodies='\n'.join(v.replace(source.FUNCTION,n)for n,v in variants.items())
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(native_harness(bodies))
            subprocess.run([*native_command(opt),'-fno-strict-aliasing',str(c),'-o',str(p)],cwd=ROOT,capture_output=True,check=True);subprocess.run([str(p)],capture_output=True,check=True)
        self.receipt.update(native32_cases_per_optimization=96,native_optimizations=['O0','O2','O3'],effective_defined_wrong_C_controls=7,trap_UBSan=True)
    def link_words(self,obj,entry,step,label):
        text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,{'D_800BE9A4':step});self.assertFalse(unknown)
        p=self.out/label;ap=p.with_suffix('.s');op=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        ap.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\nD_800BE9A4 = 0x%X;\n'%(entry,step))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,'-o',str(elf),str(op)],capture_output=True,check=True)
        return list(struct.unpack_from('>42I',sections(elf)['.text'][1]))
    def test_05_relocations_and_guarded_fault_prefixes(self):
        original=source.original(ROOT,self.out);count=cuts=0
        for i,(entry,step)in enumerate(((0x17001000,0x800B7FFC),(0x17108000,0x800B8000),(0x1720FFFC,0x800CFFFC))):
            a=self.link_words(original,entry,step,'original-rebase'+str(i));b=self.link_words(self.obj,entry,step,'C-rebase'+str(i))
            fitted=list(struct.unpack('>42I',source.patch_copy(struct.pack('>42I',*b))));self.assertEqual(a,fitted)
            for phase,alias in itertools.product((0,8),(None,0x40,0x134,0x34)):
                actor=ACTOR if alias is None else step-alias
                self.compare(fixture(4,bits(1.),phase,actor,step),actor,phase,step,(a,b,fitted),entry);count+=1
        for phase,alias in itertools.product((0,8),(None,0x40,0x134,0x34)):
            actor=ACTOR if alias is None else STEP-alias;memory=fixture(4,bits(1.),phase,actor)
            good=SnapshotOracle(self.truth,memory,phase,actor).run()
            for cut in range(good.root_accesses):
                models=[SnapshotOracle(w,memory,phase,actor)for w in(self.truth,self.fitted)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=6,rebase_phases=count,fired_guarded_root_fault_prefixes=cuts,raw_fault_prefix_identity_not_claimed=True,portable_C_fault_or_MMU_claimed=False)
    def test_06_actual_callback_window(self):
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22E78C)[0],ENTRY)
        ptr=struct.pack('>I',ENTRY);jal=struct.pack('>I',0x0C000000|(ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[0x22E78C]);self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[])
        start,stop=0x1513D034,0x1513D070;window=list(struct.unpack_from('>16I',self.rom,0x16A4E4));count=0
        for phase,flag in itertools.product((0,8),(0,1,127,128,255)):
            memory=fixture(4,phase=phase);memory[ACTOR+0x70]=5;put(memory,TABLE+20,ENTRY);models=[]
            for leaf in(self.truth,self.fitted):
                connected={ENTRY+i*4:w for i,w in enumerate(leaf)}
                m=SnapshotOracle(window,memory,phase,entry=start,connected=connected);m.r[7]=flag;m.code=StopCode(m.code,m,stop)
                with self.assertRaises(WindowEnd):m.run()
                models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));m=models[0]
            self.assertEqual(m.calls,[(ENTRY,(ACTOR,))]);self.assertEqual(m.r[4],ACTOR)
            self.assertEqual(m.r[7],(flag if flag<128 else flag-256)&0xFFFFFFFF)
            expected=reference(memory)
            for at,value in expected.items():
                if not STACK-0x500<=at<STACK+0x208:self.assertEqual(m.memory[at],value)
            count+=1
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,0x1513CFE4,12);self.assertEqual(struct.unpack_from('>3I',old,at),(0x00001025,0x03E00008,0))
        self.receipt.update(actual_callback_slot=5,actual_caller_window_phases=count,return_branch_and_signed_flag_reload_executed=True,current_full_dispatcher_still_stub=True,full_dispatcher_or_gameplay_not_claimed=True)
    def test_07_guard_history_lifetimes_and_image_corruptions(self):
        raw,bindings=source.payload(self.obj);old=self.values['conker/retail_word_patches.us.csv'];new=source.guard_bytes(old);self.assertTrue(new.startswith(old))
        reader=csv.DictReader(io.StringIO(old.decode()));rows=list(csv.DictReader(io.StringIO(new[len(old):].decode()),fieldnames=reader.fieldnames))
        self.assertEqual(len(rows),7);self.assertEqual([int(r['offset'],0)for r in rows],list(source.COPY_LAYOUT))
        for at in(0,*source.COPY_INPUTS,164):
            wrong=bytearray(raw);wrong[at]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(wrong),bindings)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        with self.assertRaises(ValueError):source.guard_bytes(old+b'\n')
        wrong=dict(source.COPY_LAYOUT);wrong[20]=(20,1)
        with patch.object(source,'COPY_LAYOUT',wrong):
            with self.assertRaises(ValueError):source.copy_patches()
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+168];pred=source.predicted_image(before,truth)
        size=next(at+8 for at,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,ENTRY,168),source.elf_slot_offset(pred,0x1514A594,4),source.elf_slot_offset(pred,0x80082B20,4),size):
            wrong=bytearray(pred);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        self.receipt.update(guard_corruption_controls=12,whole_image_corruption_controls=6,only_seven_copy_guards_appended=True,old_guard_prefix_unchanged=True)
    def test_08_pinned_inputs_and_installed_identity(self):
        for name,old in self.values.items():
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.guard_bytes(old)if self.installed and name=='conker/retail_word_patches.us.csv'else source.predicted_image(old,self.rom[source.ROM:source.ROM+168])if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name);self.assertEqual(source.digest(old),source.INPUTS[name])
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(pinned_inputs=len(self.values),old_object_pinned=True)


if __name__=='__main__':unittest.main()
