"""Descriptor representation, relocated schedule and original constructor bounds."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_owner_descriptor_preset as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,RECORD=0x28000,0x30000
SYMBOLS={'D_800A8D5C':0x800A8D5C,'func_1513418C':0x1513418C}
FACTORY,COPY,DELETE=0x15167A68,0x10022EC0,0x1516972C
BITS=(0,0x80000000,0x3F800001,0x7F800000,0x7FC12345,0x7FA12345,0xFFFFFFFF,0x00800000)


@dataclass(frozen=True)
class Case:
    variant:int=255
    bits:int=0x3F800000
    byte:int=0xA7
    null:bool=False
    effects:int=0
    alias:int=0
    global_alias:int=-1
    allocated:bool=True
    valid:bool=True


def descriptor(phase):return STACK+phase-48
def actor(case,phase):return 0 if case.null else OWNER if not case.alias else descriptor(phase)+{1:12,2:0,3:9}[case.alias]-0x3B
def symbols(case,phase):return dict(SYMBOLS,D_800A8D5C=SYMBOLS['D_800A8D5C']if case.global_alias<0 else descriptor(phase)+case.global_alias)
def public(m):return {a:v for a,v in m.items()if not STACK-0x600<=a<STACK+0x308}


def fixture(case,phase=0,s=None):
    s=symbols(case,phase)if s is None else s
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x600,0x300)}
    for base in(OWNER,RECORD):m.update({base+i:(i*13+0x5A)&255 for i in range(-16,0x220)})
    put(m,OWNER,1 if case.valid else 0);m[OWNER+0x3B]=case.byte;put(m,OWNER+0x1D4,0)
    for i in range(-8,12):m.setdefault(s['D_800A8D5C']+i,0xA5)
    put(m,s['D_800A8D5C'],case.bits)
    return m


def packet_reference(m,case,phase,s):
    m=dict(m);owner=actor(case,phase);base=descriptor(phase)
    put(m,STACK+phase,owner);put(m,STACK+phase+4,case.variant)
    if not owner:return None
    put(m,base,0);put(m,base+4,0)
    captured=m[owner+0x3B];constant=read(m,s['D_800A8D5C'])
    put(m,base+12,owner);m[base+8]=captured;m[base+16]=1
    for off in(20,24,28):put(m,base+off,0)
    put(m,base+32,constant);put(m,base+36,0x40400000);put(m,base+40,100,2)
    for off,value in((42,10),(43,1),(44,255),(45,0)):m[base+off]=value
    return bytes(m[base+i]for i in range(48))


class PresetOracle(TimingOracle):
    def __init__(self,words,memory,case=Case(),phase=0,s=None,entry=source.ENTRY,connected=None):
        self.preset_case=case;self.preset_symbols=symbols(case,phase)if s is None else s
        self.preset_owner=actor(case,phase);self.packets=[];self.trace=[]
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(self.preset_owner,case.variant),connected=connected)
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        counts={source.ENTRY:2,self.preset_symbols['func_1513418C']:4,FACTORY:6,COPY:3,DELETE:1}
        args=self.arguments(counts[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==self.preset_symbols['func_1513418C']:self.packets.append(bytes(self.memory[args[0]+i]for i in range(48)))
    def hook(self,target):
        c=self.preset_case;s=self.preset_symbols
        if target==s['func_1513418C']:
            if c.effects&1:self.put(self.preset_owner+0x3B,0x5A,1)
            if c.effects&2:self.put(s['D_800A8D5C'],0x87654321,4)
            value=RECORD if c.variant&1 else 0
        elif target==FACTORY:value=RECORD if c.allocated else 0
        elif target==COPY:
            dst,src,n=self.arguments(3)
            for i in range(n):self.put(dst+i,self.get(src+i,1),1)
            value=dst
        else:
            assert target==DELETE;value=0x87654321
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=value


def controls():
    b=source.SELECTED
    return {'selected':b,'skipVariant':b.replace('owner != NULL','owner != NULL && variant != 255'),
        'wrongByte':b.replace('[0x3B]','[0x3A]'),'wrongVector':b.replace('vector[1] = 0.0f','vector[1] = 1.0f'),
        'fixedConstant':b.replace('= D_800A8D5C','= 1.0f'),'wrongScalar':b.replace('= 3.0f','= 2.0f'),
        'wrongShort':b.replace('= 100','= 101'),'wrongFlags':b.replace('flags = 10','flags = 11'),
        'wrongSentinel':b.replace('value2C = -1','value2C = 0'),
        'wrongVariant':b.replace('&descriptor, 0, variant, 0','&descriptor, 0, variant ^ 1, 0')}


def native_harness():
    bodies='\n'.join(b.replace(source.FUNCTION,n)for n,b in controls().items())
    return '#include <ultra64.h>\n'+source.DECLARATIONS+r'''
f32 D_800A8D5C;
typedef char correct_size[sizeof(OwnerPresetDescriptor1D0840)==48?1:-1];
static union{u32 align[128];u8 bytes[512];}ownerBlock;
static u8 expectedOwner[512];static u32 expectVariant,expectBits,expectByte,calls,error;
__attribute__((noinline,noclone)) void *func_1513418C(OwnerPresetDescriptor1D0840 *p,s32 size,u8 variant,s32 parameter){
 const u8 *b=(const u8*)p;const u32 *w=(const u32*)p;u32 i;
 calls++;if(size||parameter||variant!=expectVariant||calls!=1||w[0]||w[1]||b[8]!=expectByte||w[3]!=(u32)ownerBlock.bytes||b[16]!=1)error=1;
 if(w[5]||w[6]||w[7]||w[8]!=expectBits||w[9]!=0x40400000||*(const s16*)(b+40)!=100||b[42]!=10||b[43]!=1||b[44]!=255||b[45])error=2;
 for(i=0;i<512;i++)if(ownerBlock.bytes[i]!=expectedOwner[i])error=3;
 ownerBlock.bytes[0x3B]=expectedOwner[0x3B]=0x5A;*(u32*)&D_800A8D5C=0x87654321;
 return variant&1?(void*)ownerBlock.bytes:NULL;
}
'''+bodies+r'''
static int variant(void(*fn)(u8*,u8)){
 const u32 values[]={0,0x80000000,0x3F800001,0x7F800000,0x7FC12345,0x7FA12345,0xFFFFFFFF,0x00800000};
 u32 v,p,n,i,count=0;
 for(v=0;v<256;v++)for(p=0;p<8;p++)for(n=0;n<2;n++){
  for(i=0;i<512;i++)ownerBlock.bytes[i]=expectedOwner[i]=(u8)(i*13+v+0x5A);
  expectVariant=v;expectBits=values[p];expectByte=ownerBlock.bytes[0x3B];*(u32*)&D_800A8D5C=expectBits;calls=error=0;
  fn(n?NULL:ownerBlock.bytes,(u8)v);
  if(error||calls!=!n||*(u32*)&D_800A8D5C!=(n?expectBits:0x87654321))return 20;
  for(i=0;i<512;i++)if(ownerBlock.bytes[i]!=expectedOwner[i])return 21;
  count++;
 }
 return count==4096?0:22;
}
static int run(void){
 if(variant(selected))return 30;
 if(!variant(skipVariant))return 31;if(!variant(wrongByte))return 32;if(!variant(wrongVector))return 33;
 if(!variant(fixedConstant))return 34;if(!variant(wrongScalar))return 35;if(!variant(wrongShort))return 36;
 if(!variant(wrongFlags))return 37;if(!variant(wrongSentinel))return 38;if(!variant(wrongVariant))return 39;
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class OwnerDescriptorPresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True);cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>42I',cls.rom,source.ROM))
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        raw,rs=source.payload(cls.obj);source.normalized(raw,rs)
        linked,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER);raw=linked[fs[source.FUNCTION]['value']:fs[source.FUNCTION]['value']+168]
        cls.raw=list(struct.unpack('>42I',raw));cls.words=list(struct.unpack('>42I',source.patch_schedule(raw)));cls.receipt=dict(installed=cls.installed)
        cls.original=source.original(ROOT,cls.out);cls.alias_images={}
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,case=Case(),phase=0,s=None,images=None,entry=source.ENTRY):
        s=symbols(case,phase)if s is None else s;m=fixture(case,phase,s);expected=packet_reference(m,case,phase,s)
        if images is None and case.global_alias>=0:
            key=s['D_800A8D5C']
            if key not in self.alias_images:
                a=self.link_words(self.original,entry,s,'alias-original-%X'%key)
                b=self.link_words(self.obj,entry,s,'alias-C-%X'%key,True)
                self.assertEqual(a,b);self.alias_images[key]=(a,b)
            images=self.alias_images[key]
        models=[PresetOracle(w,m,case,phase,s,entry).run()for w in images or(self.truth,self.words)]
        for a in models:
            self.assertEqual(a.packets,[]if case.null else[expected])
            self.assertEqual(a.calls,[]if case.null else[(s['func_1513418C'],(descriptor(phase),0,case.variant&255,0))])
            changed=dict(m)
            if not case.null:
                if case.effects&1:changed[actor(case,phase)+0x3B]=0x5A
                if case.effects&2:put(changed,s['D_800A8D5C'],0x87654321)
            self.assertEqual(public(a.memory),public(changed))
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
        return models
    def test_01_owner_Make_guarded_schedule_and_effective_stub(self):
        self.assertEqual(self.words,self.truth);q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['relocations'],q['new_guards'],q['preserved_neighbors']),(42,72,3,18,22))
        self.assertEqual(source.normalized(*source.payload(self.obj)),source.payload(source.original(ROOT,self.out)))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,168)
        stub=PresetOracle(struct.unpack_from('>42I',old,at),fixture(Case())).run();self.assertFalse(stub.calls);self.assertTrue(self.compare()[0].calls)
        self.receipt.update(words=42,frame=72,bindings=3,new_guards=18,neighbors=22,old_stub_effectively_rejected=True)
    def test_02_packet_bytes_holes_word_inputs_aliases_and_raw_bounds(self):
        count=raw_count=0;seen=set()
        cases=itertools.chain((Case(variant=v,bits=BITS[v%8],byte=v^0xA5,null=n,effects=v%4)for v,n in itertools.product(range(256),(False,True))),
            (Case(variant=v,bits=b,effects=3)for v,b in itertools.product((0,1,255,256,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678),BITS)),
            (Case(alias=a,global_alias=g,effects=e)for a,g,e in itertools.product((1,2,3),(-1,4,12,32,36),(0,3))))
        for c in cases:
            for phase in(0,8):
                a=self.compare(c,phase)[0];seen.update(a.visits);count+=1
                if not c.alias and c.global_alias<0:
                    raw=PresetOracle(self.raw,fixture(c,phase),c,phase).run()
                    self.assertEqual((public(raw.memory),raw.calls,raw.packets),(public(a.memory),a.calls,a.packets));raw_count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+168,4)))
        alias=Case(alias=1);m=fixture(alias);a=PresetOracle(self.truth,m,alias).run();b=PresetOracle(self.raw,m,alias).run()
        self.assertNotEqual(a.packets,b.packets)
        self.receipt.update(guest_phases=count,raw_disjoint_public_phases=raw_count,alias_independent_GNU_links=2*len(self.alias_images),all_words_visited=42,all_variant_bytes=True,
            all_descriptor_bytes_and_reserved_holes=True,guarded_local_global_aliases=True,raw_local_alias_difference_effective=True,
            raw_private_fault_and_local_alias_identity_claimed=False)
    def test_03_native32_and_effective_defined_wrong_C(self):
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(native_harness())
            built=subprocess.run([*native_command(opt),'-fno-strict-aliasing',str(c),'-o',str(p)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native'+opt+'-diagnostics.txt')).write_text(built.stdout+built.stderr)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr);subprocess.run([str(p)],capture_output=True,check=True)
        self.receipt.update(native32_selected_cases_per_optimization=4096,native_optimizations=['O0','O2','O3'],effective_defined_wrong_C_controls=9,
            trap_UBSan=True,raw_float_transport_not_general_FCSR=True,native_reserved_bytes_not_assigned_portable_values=True)
    def link_words(self,obj,entry,s,label,guarded=False):
        text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,s);self.assertFalse(unknown)
        p=self.out/label;ap=p.with_suffix('.s');op=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        ap.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+''.join('%s = 0x%X;\n'%x for x in s.items()))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,'-o',str(elf),str(op)],capture_output=True,check=True)
        raw=sections(elf)['.text'][1][:168]
        return list(struct.unpack('>42I',source.patch_schedule(raw)if guarded else raw))
    def test_04_independent_signed_low_links_and_fired_fault_prefixes(self):
        count=cuts=0;original=source.original(ROOT,self.out)
        for i,(entry,global_)in enumerate(((0x17001000,0x81007FFC),(0x17108000,0x81108000),(0x1720FFFC,0x8120FFFC))):
            s=dict(D_800A8D5C=global_,func_1513418C=0x17300000+i*0x100)
            a=self.link_words(original,entry,s,'original-rebase'+str(i));b=self.link_words(self.obj,entry,s,'C-rebase'+str(i),True);self.assertEqual(a,b)
            for null,phase,variant in itertools.product((False,True),(0,8),(0,0xFFFFFFFF)):
                self.compare(Case(null=null,variant=variant,effects=3),phase,s,(a,b),entry);count+=1
        for null,phase,effects in itertools.product((False,True),(0,8),(0,3)):
            c=Case(null=null,effects=effects);m=fixture(c,phase);good=PresetOracle(self.truth,m,c,phase).run()
            for cut in range(good.root_accesses):
                models=[PresetOracle(w,m,c,phase)for w in(self.truth,self.words)]
                for a in models:
                    a.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):a.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=6,rebase_phases=count,fired_guarded_root_fault_prefixes=cuts,portable_C_fault_MMU_or_hardware_claimed=False)
    def test_05_actual_caller_window_and_static_references(self):
        ptr=struct.pack('>I',source.ENTRY);jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x1D08FC])
        start,stop=0x151A3448,0x151A3458;window=list(struct.unpack_from('>5I',self.rom,0x1D08F8));count=0
        for v,phase,null in itertools.product((0,1,128,255),(0,8),(False,True)):
            c=Case(variant=v,null=null,effects=3);m=fixture(c,phase);m[STACK+phase+0x9F]=v;models=[]
            for leaf in(self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(leaf)}
                a=PresetOracle(window,m,c,phase,entry=start,connected=connected);a.r[16]=actor(c,phase)
                a.code=StopCode(a.code,a,stop)
                with self.assertRaises(WindowEnd):a.run()
                models.append(a)
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].calls[0],(source.ENTRY,(actor(c,phase),v)));count+=1
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,0x151A3390,12)
        self.assertEqual(struct.unpack_from('>3I',old,at),(0x00001025,0x03E00008,0))
        self.receipt.update(actual_caller_window_phases=count,actual_S0_owner_and_delay_slot_variant=True,stop_before_following_extended_effect_call=True,parent_151A3390_still_stub=True,full_caller_or_gameplay_claimed=False)
    def test_06_guard_bindings_corruptions_and_suppressed_null_reads(self):
        raw,rs=source.payload(self.obj);patches=source.schedule_patches();self.assertEqual(len(patches),18)
        self.assertEqual(sorted(a for a,b in patches.values()),sorted(b for a,b in patches.values()))
        self.assertEqual(source.scheduled_bindings(rs),{28:rs[28],60:rs[64],144:rs[144]})
        for off in patches:
            bad=bytearray(raw);bad[off]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
        with self.assertRaises(ValueError):source.normalized(raw,{})
        malformed=dict(source.SCHEDULE_LAYOUT);malformed[13]=13
        with patch.object(source,'SCHEDULE_LAYOUT',malformed):
            with self.assertRaises(ValueError):source.schedule_patches()
        for code in(self.truth,self.words,self.raw):
            c=Case(null=True);m=fixture(c)
            for at in range(SYMBOLS['D_800A8D5C']-8,SYMBOLS['D_800A8D5C']+12):m.pop(at,None)
            for at in range(OWNER-16,OWNER+0x220):m.pop(at,None)
            a=PresetOracle(code,m,c).run();self.assertFalse(a.calls)
        self.receipt.update(guard_corruption_controls=20,closed_word_and_relocation_permutation=True,null_unbacked_owner_and_global_reads_suppressed=True)
    def test_07_original_constructor_allocation_copy_and_owner_gate(self):
        entry,size=0x1513418C,304;raw=self.rom[0x16163C:0x16163C+size];old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,entry,size)
        self.assertEqual(old[at:at+size],raw);code={entry+i*4:w for i,w in enumerate(struct.unpack('>76I',raw))};count=0
        for null,allocated,valid,v,phase,bits in itertools.product((False,True),(False,True),(False,True),(0,255),(0,8),(0x3F800000,0x40000000)):
            c=Case(null=null,allocated=allocated,valid=valid,variant=v,bits=bits);m=fixture(c,phase)
            models=[PresetOracle(w,m,c,phase,connected=code).run()for w in(self.truth,self.words)]
            self.assertEqual(complete(models[0]),complete(models[1]));a=models[0]
            if null:self.assertFalse(a.calls)
            else:
                self.assertEqual(a.calls[1],(FACTORY,(0x28,0,0x58,1,v,1)))
                if allocated:
                    self.assertEqual(a.calls[2],(COPY,(RECORD+16,descriptor(phase),48)))
                    if not valid:self.assertEqual(a.calls[3],(DELETE,(RECORD,)));self.assertEqual(a.r[2],0)
                    else:self.assertEqual(a.r[2],RECORD);self.assertEqual(read(a.memory,RECORD+0x4C),0x3F000000 if bits==0x3F800000 else 0x3E800000);self.assertEqual(read(a.memory,RECORD+0x50),0)
                else:self.assertEqual(a.r[2],0)
            count+=1
        self.receipt.update(original_constructor_words=76,current_constructor_byte_exact=True,actual_constructor_phases=count,
            original_allocation_copy_owner_gate_and_finite_reciprocal_paths=True,matrix_branch_and_general_FCSR_not_claimed=True)
    def test_08_pins_installed_identity_and_whole_image_controls(self):
        for name,old in self.values.items():
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.predicted_image(old,self.rom[source.ROM:source.ROM+168])if self.installed and name=='conker/build/conker.us.elf'else source.guard_bytes(old)if self.installed and name=='conker/retail_word_patches.us.csv'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name);self.assertEqual(source.digest(old),source.INPUTS[name])
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+168];pred=source.predicted_image(before,truth)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,168),source.elf_slot_offset(pred,0x151A499C,4),source.elf_slot_offset(pred,0x80082B20,4)):
            wrong=bytearray(pred);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        self.receipt.update(pinned_inputs=len(self.values),whole_image_corruption_controls=5,old_guard_prefix_and_conversion_rows_preserved=True,metadata_exclusions=0)


if __name__=='__main__':unittest.main()
