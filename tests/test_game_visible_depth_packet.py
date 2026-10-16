"""Unsigned depth, visibility ABI, closed guards and complete pre-install image."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_visible_depth_packet as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import game_visible_depth_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_one_shot_timer_match import canonical_symbols

DECLARATIONS='''#include <ultra64.h>
extern f32 D_8009DEC0;
s32 func_1509563C(f32,f32,f32,f32*,f32*,f32*,f32*,f32);
s32 func_15095B08(s32,f32,f32,f32,s32,s32*);
'''


def controls():
    body=source.SELECTED
    return {
        'unsigned-coordinate':body.replace('packet[0], packet[1], packet[2]','(u16)packet[0], packet[1], packet[2]'),
        'wrong-coordinate-stride':body.replace('packet[0], packet[1], packet[2]','packet[0], packet[1], packet[4]'),
        'byte-clear':body.replace('*visible = 0;','*(u8 *)visible = 0;'),
        'byte-gate':body.replace('if (*visible != 0)','if (*(u8 *)visible != 0)'),
        'wrong-provider-flag':body.replace('divisor, 1, visible','divisor, 0, visible'),
        'wrong-scale':body.replace('scale = D_8009DEC0;','scale = 32767.0f;'),
        'wrong-depth-component':body.replace('(depth / divisor)','(screenX / divisor)'),
        'ignored-rejection':body.replace('4000.0f) == 0','4000.0f) == 7'),
    }


def native_harness():
    return r'''#include <ultra64.h>
f32 D_8009DEC0;
static s16 packet[24];static Gfx output[16],expected[2];static s32 visible,decision,active;
static u32 calls,error,mode;static f32 z,w;static s32 providerResult;
Gfx *func_150958B0(Gfx*,s16*,s32*);
s32 func_1509563C(f32 x,f32 y,f32 q,f32*a,f32*b,f32*d,f32*v,f32 maximum){
 if(x!=-32768.f||y!=-12345.f||q!=32767.f||maximum!=4000.f)error=20;
 *a=17.25f;*b=-91.5f;*d=z;*v=w;calls++;return active;}
s32 func_15095B08(s32 p,f32 x,f32 y,f32 v,s32 flag,s32*s){
 if(!active||p!=(s32)packet||x!=17.25f||y!=-91.5f||v!=w||flag!=1||s!=&visible)error=21;
 *s=decision;if(mode)D_8009DEC0=32704.f;calls++;return providerResult;}
static int run(void){u32 a,d,m,i,j,k;Gfx*end;f32 value;static const f32 zs[]={0.f,.25f,100.f,190000.f};
 static const s32 ds[]={0,1,0x100,-1};
 if(sizeof(void*)!=4||sizeof(Gfx)!=8)return 29;
 for(a=0;a<2;a++)for(d=0;d<4;d++)for(m=0;m<2;m++)for(j=0;j<4;j++)for(k=0;k<2;k++){
 active=(s32)a;decision=ds[d];mode=m;z=zs[j];w=k?2.f:1.5f;visible=0x12345678;
 providerResult=k?0:0x12345678;calls=error=0;D_8009DEC0=16352.f;
 for(i=0;i<24;i++)packet[i]=(s16)0xA5A5;packet[0]=-32768;packet[1]=-12345;packet[2]=32767;
 for(i=0;i<16;i++)output[i].words.w0=output[i].words.w1=0xA5A5A5A5u;
 end=func_150958B0(output,packet,&visible);if(error)return error;
 if(calls!=1+a||visible!=(a?decision:0))return 22;
 if(end!=output+(a&&decision?2:0))return 23;
 if(a&&decision){value=(z/w)*D_8009DEC0+D_8009DEC0;
 gDPPipeSync(expected);gDPSetPrimDepth(expected+1,(u32)value,0);
 for(i=0;i<2;i++)if(output[i].words.w0!=expected[i].words.w0||output[i].words.w1!=expected[i].words.w1)return 24;}
 for(i=a&&decision?2:0;i<16;i++)if(output[i].words.w0!=0xA5A5A5A5u||output[i].words.w1!=0xA5A5A5A5u)return 25;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class VisibleDepthPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>102I',cls.rom,source.ROM))
        cls.projection=list(struct.unpack_from('>73I',cls.rom,0xC2AEC))
        cls.connected=dict(zip(range(source.PROJECT,source.PROJECT+292,4),cls.projection))

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_shape_eighteen_neighbors_and_closed_scratch_roles(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['guards']),(102,72,4))
        self.assertEqual(self.words[0xDC//4:0x178//4],self.truth[0xDC//4:0x178//4])
        obj,diag=source.build.compile_owner(self.root,self.out,(self.out/'before-packet_owner').read_text(),'neighbor-baseline')
        self.assertFalse(diag)
        old,new=parse_object(obj),parse_object(self.obj)
        self.assertEqual(set(old[1]),set(new[1]))
        for name,f in old[1].items():
            if name==source.FUNCTION:
                continue
            g=new[1][name]
            self.assertEqual(old[0][f['value']:f['value']+f['size']],new[0][g['value']:g['value']+g['size']],name)
            relative=lambda o,f:{a-f['value']:v for a,v in o[2].items() if f['value']<=a<f['value']+f['size']}
            self.assertEqual(relative(old,f),relative(new,g),name)
        self.assertEqual(len(old[1])-1,18)
        bad=list(self.words)
        bad[0xDC//4]=0x00400025
        with self.assertRaisesRegex(ValueError,'not closed'):
            source.closed_roles(bad)
        self.receipt('shape',words=102,frame=72,guards=4,neighbors=18,raw_FP_FCSR_sequence_exact=True,
            closed_roles=source.closed_roles(self.words),forbidden_register_control_fired=True)

    def test_02_native32_real_SDK_O2_O0_UBSan_and_negatives(self):
        harness=self.out/'native-harness.c'
        harness.write_text(native_harness())
        exits={}
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (n,'-O2',b,False) for n,b in controls().items()]:
            path=self.out/'native-selected.c'
            path.write_text(DECLARATIONS+body)
            exe=self.out/('native-'+label)
            result=subprocess.run([*native_command(opt,valid),str(path),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr[:3000])
            result=subprocess.run([str(exe)],timeout=30)
            self.assertIn(result.returncode,(0,) if valid else tuple(range(20,26)),label)
            exits[label]=result.returncode
        self.receipt('native',cases_per_selected=128,real_SDK_reference=True,separate_translation_units=True,
            O2_O0_UBSan=True,only_defined_float_to_unsigned_domain=True,exits=exits)

    def test_03_connected_projection_visibility_fullwords_aliases_and_live_provider(self):
        count=0
        visits=set()
        for coords,w,z,decision,phase,mode,alias in itertools.product(
                ((-32768,0,32767),(32767,-12345,-32768)),(1.,1.5,2.,4000.),(.25,200000.),
                (None,0,1,0x100,0xFFFFFFFF),(0,8),(0,1,2),(0,1,2)):
            memory,args,transformed=guest.fixture(coords,(17.25,-91.5,z,w),alias=alias)
            expected,result,calls=guest.reference(memory,args,transformed,phase,decision,mode)
            for words in (self.truth,self.words):
                m=guest.VisibleDepthOracle(words,memory,args,transformed,phase=phase,decision=decision,
                    mode=mode,provider_result=0 if count%2 else 0x12345678,connected=self.connected).run()
                self.assertEqual((guest.previous.public(m.memory),m.r[2],m.calls),
                    (guest.previous.public(expected),result,calls))
                self.assertEqual(m.fcsr,0)
                visits.update(m.visits)
            count+=1
        self.receipt('sequences',paired_cases=count,target_words_visited=len(set(range(source.ENTRY,source.ENTRY+408,4))&visits),
            provider_return_ignored=True,word_clear_and_word_gate=True,packet_output_status_aliases_guest_only=True,
            private_depth_mutation_guest_only=True,real_projector_bounded_matrix_and_visibility_providers=True,
            natural_gameplay_and_complete_FCSR_not_claimed=True)

    def test_04_bounded_unsigned_conversion_fragment_and_restore(self):
        fragment=self.truth[0xFC//4:0x178//4]+[0x03E00008,0]
        values=(0,0x80000000,guest.bits(-.75),guest.bits(-1.),guest.bits(.5),guest.bits(16352.),
            guest.bits(2**31-128),guest.bits(2**31),guest.bits(2**32-256),guest.bits(2**32),
            guest.bits(-2**31),0x7F800000,0xFF800000,0x7FC12345)
        visits=set()
        for value,fcsr,phase in itertools.product(values,(0,3,0x123456),(0,8)):
            memory,_,_=guest.fixture()
            m=guest.previous.edge.EdgeOracle(fragment,memory,(),phase=phase,entry=source.ENTRY+0xFC)
            m.fcsr=m.initial_fcsr=fcsr
            m.f[8]=value
            m.r[1],m.r[8]=0x4F000000,1
            m.run()
            self.assertEqual((m.r[8],m.fcsr),(guest.unsigned(guest.floating(value)),fcsr))
            visits.update(m.visits)
        self.receipt('conversion',cases=len(values)*6,fragment_words=31,
            visited_fragment_words=len(visits)-2,saved_snapshot_restored=True,
            bounded_truncation_only=True,full_hardware_flags_rounding_traps_and_portable_invalid_C_cast_not_claimed=True)

    def test_05_raw_words_bindings_guards_pools_and_metadata_fail_closed(self):
        text,funcs,rel=parse_object(self.obj)
        f=funcs[source.FUNCTION]
        for i in range(102):
            bad=bytearray(text)
            bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),funcs,rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for at in source.RELOCATIONS:
            bad=dict(rel)
            bad[f['value']+at]=[(rel[f['value']+at][0][0],'wrong')]
            with patch.object(source,'parse_object',return_value=(text,funcs,bad)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):
                source.checked_object(self.obj)
        guards=(self.out/'proposed-guards.csv').read_bytes()
        for at,(expected,replacement) in source.GUARDS.items():
            bad=guards.replace(('%s,0x%X,0x%08X'%(source.FUNCTION,at,expected)).encode(),
                ('%s,0x%X,0x%08X'%(source.FUNCTION,at,expected^1)).encode())
            self.assertNotEqual(bad,guards)
            path=self.out/'bad-guard.csv'
            path.write_bytes(bad)
            with self.assertRaises(ValueError):
                emit_padded_assembly(self.obj,self.root/source.PATHS['packet_original'],filename=source.OWNER,word_patches_path=path)
        structural=source.slot_expected_image((self.out/'before-elf').read_bytes(),self.rom)
        for at in (0,2803616+4,2950336+4):
            bad=bytearray(structural)
            bad[at]^=1
            with self.assertRaises(ValueError):
                source.serialize_symbols(bytes(bad))
        self.receipt('corruptions',raw_words=102,bindings=4,guards=4,pool_control=True,metadata_controls=3)

    def test_06_full_first_prediction_and_all_97_frozen_inputs(self):
        row=source.prelink_prediction(self.root,self.out)
        self.assertEqual((row['changed_ELF_bytes'],row['metadata_exclusions'],row['metadata_serialization_bytes']),(317,0,32))
        expected=source.expected_inputs(self.root,self.out)
        self.assertEqual(row['after'],{k:hashlib.sha256(v).hexdigest() for k,v in expected.items()})
        structural=source.slot_expected_image((self.out/'before-elf').read_bytes(),self.rom)
        self.assertEqual(canonical_symbols(structural),canonical_symbols(expected['elf']))
        self.assertEqual((self.out/'slot-only-rejected.elf').read_bytes(),structural)
        self.assertEqual(len(source.PATHS),97)
        rb=Path.read_bytes
        for key in source.PATHS:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)
        self.receipt('scope',inputs=97,unchanged_inputs=94,prediction=row)

    def test_07_independent_original_assembly_three_rebases(self):
        original=(self.out/'before-packet_original').read_text()
        inner=original.split('glabel '+source.FUNCTION+'\n',1)[1].split('endlabel '+source.FUNCTION,1)[0]
        path=self.out/'original.s'
        path.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+
            '.type '+source.FUNCTION+', @function\nglabel '+source.FUNCTION+'\n'+inner+
            '\n.size '+source.FUNCTION+', . - '+source.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        for number,delta in enumerate((0,0x10000,0x20000)):
            links=dict(func_1509563C=0x15200000+delta,func_15095B08=0x15210000+delta,D_8009DEC0=0x80227FF8+delta)
            streams=[]
            for variant,obj in enumerate((path.with_suffix('.o'),self.padded)):
                data,funcs,rel=parse_object(obj)
                f=funcs[source.FUNCTION]
                bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
                asm,missing=emit_function(data[f['value']:f['value']+f['size']],dict(value=0,size=f['size']),bindings,source.FUNCTION,links)
                self.assertFalse(missing)
                file=self.out/('rebase-%d-%d.s'%(number,variant))
                file.write_text(asm)
                file.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x15220000+delta))
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(file.with_suffix('.o')),str(file)],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(file.with_suffix('.ld')),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in links.items()],'-o',str(file.with_suffix('.elf')),str(file.with_suffix('.o'))],check=True,capture_output=True)
                streams.append(sections(file.with_suffix('.elf'))['.text'][1][:408])
            self.assertEqual(*streams)
        self.receipt('rebases',independent_original_sets=3,all_three_bindings_and_entry_changed=True)

    def test_08_aligned_ROM_reference_audit_and_unrestored_provider(self):
        jal=(3<<26)|((source.ENTRY>>2)&0x3FFFFFF)
        references=[(at,word) for at,(word,) in enumerate(struct.iter_unpack('>I',self.rom)) if word in (source.ENTRY,jal)]
        self.assertEqual(references,[])
        before=(self.out/'before-packet_owner').read_text()
        lo,hi=source.build.function_span(before,'func_15095B08')
        self.assertIn('return 0;',before[lo:hi])
        self.receipt('references',aligned_US_ROM_pointer_or_JAL_words=references,provider_still_placeholder=True,
            computed_references_dead_code_and_natural_gameplay_not_claimed=True)

    def test_09_effective_compiled_guest_controls(self):
        cases=list(itertools.product((1.,1.5,2.,4000.),(.25,190000.),(0,1,0x100,0xFFFFFFFF),(0,1)))
        rejected=[]
        variants=dict(controls(),signed_conversion=source.SELECTED.replace('(u32)((depth / divisor)',
            '(u32)(s32)((depth / divisor)'))
        for label,body in variants.items():
            obj,words,_=source.measure(self.root,self.out,'negative-'+label,body)
            pools={name:value for name,value in sections(obj.with_suffix('.elf')).items()
                if name.startswith(('.rodata','.rdata','.data','.sdata','.lit'))}
            for w,z,decision,mode in cases:
                memory,args,transformed=guest.fixture(transformed=(17.25,-91.5,z,w))
                for address,data in pools.values():
                    memory.update({address+i:v for i,v in enumerate(data)})
                expected,result,calls=guest.reference(memory,args,transformed,decision=decision,mode=mode)
                model=guest.VisibleDepthOracle(words,memory,args,transformed,decision=decision,
                    mode=mode,connected=self.connected).run()
                if (guest.previous.public(model.memory),model.r[2],model.calls)!=(guest.previous.public(expected),result,calls):
                    rejected.append(label)
                    break
            else:
                self.fail('Ineffective compiled guest control: '+label)
        self.receipt('negatives',compiled_observable_rejections=rejected,
            no_compile_failures_or_unsupported_instructions_accepted=True)


if __name__=='__main__':
    unittest.main()
