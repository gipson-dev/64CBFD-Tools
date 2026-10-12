"""Full SDK command leaf, ordered stores, native32 and frozen linked audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_intensity_texture_setup_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK = guest.STACK
TEXTURE = screen.SYMBOLS['D_80084930']
OUTPUTS = (0, 0x30000, 0x30008, 0x7FFFFFF8, 0x80010000,
    0xFFFFFFC0, TEXTURE, TEXTURE-40)
MASK = 0xFFFFFFFF


def commands(texture=TEXTURE):
    return ((0xD7000002, MASK), (0xE7000000, 0), (0xFCFFFFFF, 0xFFFCF279),
        (0xEF002C0F, 0x0055204C), (0xFD90003F, texture), (0xFD900000, texture),
        (0xF5900000, 0x07000000), (0xE6000000, 0), (0xF3000000, 0x077FF200),
        (0xE7000000, 0), (0xF5800800, 0), (0xF2000000, 0x000FC1FC))


def fixture(output=0x30000, pattern=0):
    memory = {STACK+i:0xA5 for i in range(-128,128)}
    memory.update({(output+i)&MASK:(i*17+53+pattern*19)&255 for i in range(-16,112)})
    return memory


def reference(memory, output, texture=TEXTURE):
    result, events = memory.copy(), []
    for i,pair in enumerate(commands(texture)):
        for j in ((1,0) if i in (0,6) else (0,1)):
            address = (output+i*8+j*4)&MASK
            assert all(address+k in result for k in range(4))
            put(result,address,pair[j])
            events.append(('W',address,4,pair[j]))
    return result,events,(output+96)&MASK


class GameIntensityTextureSetupMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-intensity-texture-setup-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt',
            makefile='conker/Makefile',assembly='conker/asm/6E770.s',
            texture_data='conker/asm/data/2275E0.data.s',
            sdk_gbi='conker/include/2.0L/PR/gbi.h',sdk_mbi='conker/include/2.0L/PR/mbi.h')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name,path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == 'e61b9a95d46df6d94fbf844eba778533559a662425c63b6d6ddfc8d413ee9241'
        assert cls.baseline['elf'] == '4b4bece866646b9f453b958c1dccdd2f37e31f65dc2abaaa810b71f72a5d4071'
        assert cls.baseline['guards'] == '0c28956baf37afeaa5129ad33cb532639375cfbee4fa8a8a6d479d8220adaf52'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes()
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>79I',cls.rom,screen.ROM))
        cls.meta,cls.raw = screen.compile_candidate(cls.root,cls.out,'selected')
        body = (cls.out/'before-assembly').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        slot = cls.out/'slot.s'
        slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_6E770'))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def link(self,name,entry=screen.ENTRY,texture=TEXTURE):
        script = self.out/(name+'-%X-%X.ld'%(entry,texture))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            '--defsym=D_80084930=0x%X'%texture,'-o',str(elf),str(self.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>79I',sections(elf)['.text'][1]))

    def compare(self,output=0x30000,pattern=0,phase=0,texture=TEXTURE,entry=screen.ENTRY,forms=None):
        memory = fixture(output,pattern)
        expected = reference(memory,output,texture)
        models = [guest.AttachmentOracle(words,memory,arguments=(output,),phase=phase,entry=entry).run()
            for words in forms or (self.retail,self.raw,self.link('padded'))]
        for m in models:
            self.assertEqual((m.memory,m.events,m.r[2]),expected)
            self.assertEqual((m.calls,m.accesses),([],24))
        for m in models[1:]:
            self.assertEqual((m.memory,m.events,m.r,m.f),(models[0].memory,models[0].events,models[0].r,models[0].f))
        return models

    def test_01_direct_shape_and_complete_ordered_command_contract(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(79,0,0,0))
        self.assertEqual(self.raw,self.retail)
        self.assertEqual(self.link('original'),self.retail)
        self.assertEqual(self.link('padded'),self.retail)
        _,funcs,relocs = parse_object(self.out/'selected.o')
        self.assertEqual(funcs[screen.FUNCTION]['size'],316)
        self.assertEqual(relocs,{0x78:[('R_MIPS_HI16','D_80084930')],0x7C:[('R_MIPS_LO16','D_80084930')]})
        reached,cases = set(),0
        for output,pattern,phase in itertools.product(OUTPUTS,range(4),(0,8)):
            models = self.compare(output,pattern,phase)
            reached.update(models[0].visits); cases += 1
        self.assertEqual(reached,set(range(screen.ENTRY,screen.ENTRY+316,4)))
        self.receipt('semantic',cases=cases,reached_words=79,writes=24,commands=12,
            exact_write_order_and_all_memory_registers=True,no_reads_calls_frame_guards_or_pool=True,
            output_texture_aliases_and_32bit_wrap_guest_only=True)

    def test_02_independent_rebases_and_texture_pointer_aliases(self):
        cases = 0
        for entry,texture in ((0x15207FFC,0x80107FFC),(0x15308004,0x80218004)):
            forms = tuple(self.link(n,entry,texture) for n in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[1]); self.assertEqual(forms[0],forms[2])
            for output,pattern,phase in itertools.product((0x30000,texture,texture-40),range(3),(0,8)):
                self.compare(output,pattern,phase,texture,entry,forms); cases += 1
        self.receipt('rebases',cases=cases,links=2,HI16_LO16_carries=True,
            texture_address_reused_not_read=True,complete_state_exact=True)

    def test_03_all_fired_write_faults_and_missing_final_byte(self):
        faults = 0
        forms = (self.retail,self.raw,self.link('padded'))
        for output,phase in itertools.product((0x30000,TEXTURE,0xFFFFFFC0),(0,8)):
            for fault in range(24):
                memory = fixture(output)
                models = [guest.AttachmentOracle(w,memory,arguments=(output,),phase=phase,entry=screen.ENTRY) for w in forms]
                for m in models:
                    m.fault = fault
                    with self.assertRaises(guest.AccessFault): m.run()
                    self.assertEqual((m.accesses,len(m.events)),(fault,fault))
                for m in models[1:]:
                    self.assertEqual((m.memory,m.events,m.r,m.f),(models[0].memory,models[0].events,models[0].r,models[0].f))
                faults += 1
        memory = fixture(); del memory[0x30000+95]
        for w in forms:
            m = guest.AttachmentOracle(w,memory,arguments=(0x30000,),entry=screen.ENTRY)
            with self.assertRaisesRegex(AssertionError,'unmapped write'): m.run()
            self.assertEqual(len(m.events),23)
        self.receipt('faults',fired_triplets=faults,all_24_write_boundaries=True,
            missing_final_byte_rejected=True,no_portable_C_fault_or_hardware_claim=True)

    @staticmethod
    def negatives():
        return (
            ('texture-height',screen.SELECTED.replace('G_IM_FMT_I, 64, 128','G_IM_FMT_I, 64, 64')),
            ('initial-width',screen.SELECTED.replace('G_IM_SIZ_16b, 64','G_IM_SIZ_16b, 32')),
            ('combine',screen.SELECTED.replace('G_CC_DECALRGBA','G_CC_PRIMITIVE')),
            ('texture-off',screen.SELECTED.replace('G_TX_RENDERTILE, G_ON','G_TX_RENDERTILE, G_OFF')),
            ('missing-initial-image',screen.SELECTED.replace(
                '    gDPSetTextureImage(displayList++, G_IM_FMT_I, G_IM_SIZ_16b, 64, D_80084930);\n','')),
            ('return-pointer',screen.SELECTED.replace('return displayList;','return displayList-1;')),
        )

    def test_04_freshly_compiled_semantic_and_profile_controls(self):
        for name,body in self.negatives():
            _,words = screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            memory = fixture()
            m = guest.AttachmentOracle(words,memory,arguments=(0x30000,),entry=screen.ENTRY).run()
            self.assertNotEqual((m.memory,m.events,m.r[2]),reference(memory,0x30000),name)
        o1,words = screen.compile_candidate(self.root,self.out,'o1','%s'%screen.SELECTED,'o1g3')
        self.assertEqual((o1['body_words'],o1['frame'],o1['differences']),(107,48,105))
        self.assertNotEqual(words,self.retail)
        self.receipt('controls',semantic=6,all_effective=True,O1_changes_107_frame48_diff105=True)

    def test_05_complete_owner_neighbors_and_both_actual_padders(self):
        before = (self.out/'before-source').read_text(); objects = []
        run = subprocess.run
        def compact(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'):
                command = list(command)+['-Wo,-loopunroll,0']
            return run(command,*args,**kwargs)
        for stage,source in (('before',before),('after',screen.install(before))):
            with patch('subprocess.run',side_effect=compact):
                obj,warnings = compile_owner(self.root,self.out,source,'owner-'+stage)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/('owner-'+stage+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True)
            self.assertEqual(warnings,[]); objects.append(obj)
        def fingerprint(obj,name):
            text,functions,relocs = parse_object(obj); item = functions[name]
            a,b = item['value'],item['value']+item['size']
            return item['size'],text[a:b],{o-a:r for o,r in relocs.items() if a <= o < b}
        names = set(parse_object(objects[0])[1]); self.assertEqual(names,set(parse_object(objects[1])[1]))
        for name in names-{screen.FUNCTION}:
            self.assertEqual(fingerprint(objects[0],name),fingerprint(objects[1],name),name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(fingerprint(objects[1],screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        unrolled,warnings = compile_owner(self.root,self.out,before,'owner-unrolled-control')
        self.assertEqual(warnings,[])
        self.assertEqual(fingerprint(unrolled,'func_15041480')[0],216)
        with self.assertRaisesRegex(ValueError,'patched func_15041480 is 0xD8 bytes'):
            emit_padded_assembly(unrolled,self.root/'conker/asm/6E770.s',
                word_patches_path=self.out/'before-guards',filename='generated_6E770')
        results = []
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed = []
            for stage,obj in zip(('before','after'),objects):
                asm = self.out/(route+'-'+stage+'.s')
                args = [str(obj),str(self.out/'before-layout'),'generated_6E770',str(asm)] if route == 'pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6E770.s'),str(asm),'--filename','generated_6E770']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',str(self.out/'before-guards')],
                    check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            target = parsed[1][1][screen.FUNCTION]; start = target['value']
            expected = bytearray(parsed[0][0]); expected[start:start+316] = parsed[1][0][start:start+316]
            self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not start <= o < start+316},
                {o:r for o,r in parsed[1][2].items() if not start <= o < start+316})
            for name in names-{screen.FUNCTION}:
                self.assertEqual(parsed[0][1][name],parsed[1][1][name])
            results.append(parsed[1])
        self.assertEqual(results[0],results[1])
        self.receipt('owner',neighbors=len(names)-1,pools_and_other_relocations_exact=True,
            both_actual_padders_and_GLOBAL_ASM_processing=True,no_profile_recipe_header_changes=True,
            actual_existing_no_unroll_profile=True,unrolled_neighbor_overflow_control_effective=True)

    def native_source(self,body):
        fixture = '#include <PR/mbi.h>\n#include <PR/gbi.h>\n'+NATIVE+body+NATIVE_MAIN
        return subprocess.run(['cc','-m32','-E','-P','-D_LANGUAGE_C','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32',
            '-I',str(self.root/'conker/include/2.0L'),'-xc','-'],
            input=fixture,check=True,capture_output=True,text=True).stdout

    def test_06_actual_SDK_macros_native32_and_effective_controls(self):
        source = self.native_source(screen.SELECTED)
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],source,profile),(0,''))
        for name,body in self.negatives():
            code,detail = self.run_native('native-negative-'+name,self.native_source(body))
            self.assertEqual(code,1,name); self.assertEqual(len(detail),3,name)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=384,
            actual_full_SDK_headers_not_replacement_macros=True,pointer_bytes=4,Gfx_bytes=8,
            entire_output_and_texture_canaries=True,texture_output_aliases=True,effective_controls=6)

    def test_07_literal_source_whole_ELF_and_eleven_inputs(self):
        before = (self.out/'before-source').read_text(); current = (self.root/screen.SOURCE).read_text()
        changed = current != before
        self.assertEqual(current,screen.install(before) if changed else before)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before,screen.ENTRY,316)
        extent = installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if changed:
            struct.pack_into('>79I',expected,start,*self.retail)
            struct.pack_into('>I',expected,extent,316)
        self.assertEqual(actual,bytes(expected))
        for name,path in self.paths.items():
            old = (self.out/('before-'+name)).read_bytes()
            self.assertEqual(hashlib.sha256(old).hexdigest(),self.baseline[name])
            if name not in ('source','elf'):
                self.assertEqual((self.root/path).read_bytes(),old,name)
        data = audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(data['exact'],data)
        self.receipt('linked',installed=changed,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            target_bytes=sum(a!=b for a,b in zip(self.before[start:start+316],actual[start:start+316])),
            extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            eleven_inputs_exact=True,literal_no_projection_or_metadata_exception=True,protected_data=data)

    def test_08_effective_stale_source_and_literal_integrity_controls(self):
        before = (self.out/'before-source').read_text()
        for source in (screen.install(before),before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(source)
        rt,rb = Path.read_text,Path.read_bytes
        source = self.root/screen.SOURCE; current = source.read_text()
        with patch.object(Path,'read_text',lambda p,*a,**k:current+'\n' if p == source else rt(p,*a,**k)):
            with self.assertRaises(AssertionError): self.test_07_literal_source_whole_ELF_and_eleven_inputs()
        elf = self.root/self.paths['elf']; actual = elf.read_bytes()
        start = elf_slot_offset(actual,screen.ENTRY,316)
        extent = installed.symbol_size_offset(actual,screen.FUNCTION,screen.ENTRY)
        for offset in (start+4,start+316,extent+3):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_07_literal_source_whole_ELF_and_eleven_inputs()
        guard = self.root/self.paths['guards']; wrong = bytearray(guard.read_bytes()); wrong[0] ^= 1
        with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p == guard else rb(p)):
            with self.assertRaises(AssertionError): self.test_07_literal_source_whole_ELF_and_eleven_inputs()
        self.receipt('integrity-controls',source=1,ELF=3,guard=1,stale_source=2,all_effective=True)


NATIVE = r'''
static unsigned char D_80084930[4096] __attribute__((aligned(8))),wantedTexture[4096];
static Gfx output[48],wantedOutput[48];
static int report(unsigned int a,unsigned int b,unsigned int c) {
    unsigned int data[3]={a,b,c};int r;
    __asm__ volatile("int $0x80":"=a"(r):"a"(4),"b"(2),"c"(data),"d"(12):"memory");return 1;
}
static void reset(int pattern) {
    for(unsigned int i=0;i<4096;i++)D_80084930[i]=wantedTexture[i]=(unsigned char)(i*17+53+pattern*19);
    for(unsigned int i=0;i<sizeof(output);i++)((unsigned char *)output)[i]=((unsigned char *)wantedOutput)[i]=
        (unsigned char)(i*13+71+pattern*23);
}
static void expected(Gfx *p) {
    unsigned int pairs[24]={0xD7000002,0xFFFFFFFF,0xE7000000,0,0xFCFFFFFF,0xFFFCF279,
        0xEF002C0F,0x0055204C,0xFD90003F,(unsigned int)D_80084930,
        0xFD900000,(unsigned int)D_80084930,0xF5900000,0x07000000,0xE6000000,0,
        0xF3000000,0x077FF200,0xE7000000,0,0xF5800800,0,0xF2000000,0x000FC1FC};
    for(int i=0;i<12;i++){p[i].words.w0=pairs[i*2];p[i].words.w1=pairs[i*2+1];}
}
'''
NATIVE_MAIN = r'''
static int run(void) {
    unsigned int cases=0;
    if(sizeof(void *)!=4||sizeof(Gfx)!=8||sizeof(output)!=384)return 2;
    for(int p=0;p<16;p++)for(int where=0;where<2;where++)for(int slot=1;slot<=12;slot++,cases++) {
        reset(p);
        Gfx *start=where?(Gfx *)(D_80084930+slot*8):output+slot;
        Gfx *want=where?(Gfx *)(wantedTexture+slot*8):wantedOutput+slot;
        expected(want);
        Gfx *result=func_150412C0(start);
        if(result!=start+12)return report(cases,0,0);
        for(unsigned int i=0;i<sizeof(output);i++)
            if(((unsigned char *)output)[i]!=((unsigned char *)wantedOutput)[i])return report(cases,1,i);
        for(unsigned int i=0;i<4096;i++)
            if(D_80084930[i]!=wantedTexture[i])return report(cases,2,i);
    }
    return cases==384?0:3;
}
void _start(void) {
    int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();
}
'''


if __name__ == '__main__':
    unittest.main()
