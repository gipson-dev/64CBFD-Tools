"""Ordered stack-byte packets: direct C, original wrappers, caller and image gates."""
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_six_byte_dispatch as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
NAME='func_150B3DD0'
ENTRY,INIT,SUBMIT,LOWER,PARENT=0x150B3DD0,0x15147D64,0x151494E0,0x15169260,0x1509D780
ANCHORS=dict(func_15147D64=INIT,func_151494E0=SUBMIT)
ORDER=(0,2,4,1,3,5)


def fixture(seed=0xA5,phase=0):
    return {STACK+phase+i:(i*17+seed)&255 for i in range(-0x400,0x200)}


class PacketOracle(TimingOracle):
    def __init__(self,words,seed=0xA5,phase=0,mode=0,entry=ENTRY,anchors=None,connected=None,memory=None,arguments=None):
        self.seed,self.mutation,self.anchors=seed,mode,anchors or ANCHORS
        self.trace,self.packets,self.payloads=[],[],[]
        super().__init__(words,fixture(seed,phase)if memory is None else memory,phase=phase,entry=entry,
            arguments=arguments or (seed,~seed&0xFFFFFFFF,seed<<24,0x87654321),connected=connected)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        if self.recording and self.own_instruction:assert all(address+i in self.memory for i in range(size))
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        args=tuple(self.r[4:8]);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        args=self.calls[-1][1]
        if target==LOWER:
            registry,count,pointer,command=args
            self.packets.append((tuple(read(self.memory,registry+i*4)for i in range(count)),count,pointer,command))
            init=registry==0x800A5760
        else:
            assert target in self.anchors.values(),hex(target)
            pointer,command=args[:2];init=target==self.anchors['func_15147D64']
            self.packets.append((target,pointer,command))
        if init:assert (pointer,command)==(0,5)
        else:
            self.payloads.append((pointer,bytes(self.memory[pointer+i]for i in range(4))))
            if self.mutation:
                for i in range(4):self.memory[pointer+i]=(self.seed+len(self.payloads)*13+i)&255
        # A provider may overwrite caller argument homes and all volatile registers.
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=0xCA000000|self.seed<<8|len(self.packets)


def native_harness(body):
    return '#include <ultra64.h>\n'+source.DECLARATIONS+"""
static u32 n,seed,mode,bad;static u8 *saved;
static const u8 wanted[6]={0,2,4,1,3,5};
void func_15147D64(void *p,u8 c){if(n||p||c!=5)bad=1;n=1;}
void func_151494E0(void *p,u8 c){
 u8 *b=p;u32 i,k=n-1;
 if(n<1||n>6||c!=0x18){bad=1;return;}
 if(k==0)saved=b;else if(saved!=b)bad=1;
 if(b[0]!=wanted[k])bad=1;
 /* Tail bytes are read only after this fixture has initialized them. */
 if(k&&mode)for(i=1;i<4;i++)if(b[i]!=(u8)(seed+k*13+i))bad=1;
 if(mode)for(i=0;i<4;i++)b[i]=(u8)(seed+(k+1)*13+i);
 n++;
}
"""+body+"""
static int run(void){for(seed=0;seed<256;seed++)for(mode=0;mode<2;mode++){
 n=bad=0;saved=0;func_150B3DD0();if(bad||n!=7)return 23;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class SixByteDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED[NAME],'fresh-selected')
        if diag:raise ValueError(diag)
        text,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>41I',text,fs[NAME]['value']))
        cls.truth=list(struct.unpack_from('>41I',cls.rom,0xE1280));cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)

    def compare(self,seed,phase,mode,images=None,anchors=None,entry=ENTRY):
        models=[PacketOracle(code,seed,phase,mode,entry,anchors).run()for code in images or (self.truth,self.words)]
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
        for m in models:
            pointer=STACK+phase-4
            self.assertEqual([v[0]for v in m.payloads],[pointer]*6)
            self.assertEqual([v[1][0]for v in m.payloads],list(ORDER))
            self.assertEqual([(v[1],v[2])for v in m.packets],[(0,5)]+[(pointer,0x18)]*6)
            for n,(_,payload)in enumerate(m.payloads):
                expected=bytes((seed+n*13+i)&255 for i in range(1,4))if mode and n else bytes(fixture(seed,phase)[pointer+i]for i in range(1,4))
                self.assertEqual(payload[1:],expected)
            self.assertEqual(m.r[2],0xCA000000|seed<<8|7)
        return models

    def test_01_direct_body_GNU_bindings_owner_and_actual_Make(self):
        self.assertEqual(self.words,self.truth)
        raw,bindings=source.payload(self.obj,NAME)
        self.assertEqual(bindings,source.BINDINGS)
        self.assertEqual(source.payload(source.original(ROOT,self.out,NAME),NAME),(raw,bindings))
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['preserved_neighbors']),(41,9))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],3)
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,ENTRY,164)
        old=PacketOracle(list(struct.unpack_from('>41I',before,at))).run()
        self.assertEqual(old.packets,[]);self.assertNotEqual(old.r[2],0xCA00A507)
        self.receipt.update(body_words=41,slot_words=41,frame=40,bindings=7,new_guards=0,neighbors=9,alignment_filler_words=0)

    def test_02_byte_order_shared_lifetime_clobbers_and_unused_arguments(self):
        visits=set();count=0
        for seed,phase,mode in itertools.product(range(256),(0,8),(0,1)):
            models=self.compare(seed,phase,mode);visits.update(models[0].visits);count+=1
            m=models[0];sp=STACK+phase
            self.assertEqual([(x[1],x[2],x[3])for x in m.trace if x[0]=='W'and x[2]==1],[(sp-4,1,v)for v in ORDER])
            self.assertEqual([(x[1],x[2])for x in m.trace[:2]],[(sp-12,4),(sp-16,4)])
        self.assertEqual(visits,set(range(ENTRY,ENTRY+164,4)))
        self.receipt.update(guest_phases=count,all41_words_visited=True,stack_payload_entry_SP_minus4=True,
            initialized_only_byte0=True,volatile_register_and_home_clobbers=True,incidental_V0_not_semantic_return=True)

    def native(self,body,label,opt='-O2'):
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(body))
        p=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);return subprocess.run([str(exe)],capture_output=True).returncode

    def test_03_native_C_defined_payload_and_effective_wrong_controls(self):
        body=source.SELECTED[NAME]
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(body,'native',opt),0)
        controls=[('init','0, 5','0, 6'),('first','selection[0] = 0','selection[0] = 1'),
            ('second','selection[0] = 2','selection[0] = 3'),('third','selection[0] = 4','selection[0] = 5'),
            ('last','selection[0] = 5','selection[0] = 4'),('command','0x18','0x19'),
            ('count','    selection[0] = 5;\n    func_151494E0(selection, 0x18);',''),
            ('tail','func_151494E0(selection, 0x18);','selection[1] = 0; func_151494E0(selection, 0x18);')]
        for label,a,b in controls:
            wrong=body.replace(a,b);self.assertNotEqual(wrong,body);self.assertEqual(self.native(wrong,'wrong-'+label),23,label)
        self.receipt.update(native_cases_per_optimization=512,native_optimizations=3,trap_UBSan=True,
            native_uninitialized_tail_reads=False,legal_four_byte_storage=True,effective_wrong_C_controls=8)

    def test_04_original_wrapper_packets_and_registry_bounds(self):
        connected={}
        for address,rom in ((INIT,0x175214),(SUBMIT,0x176990)):
            code=list(struct.unpack_from('>13I',self.rom,rom))
            at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],address,52)
            self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+52],self.rom[rom:rom+52])
            connected.update(zip(range(address,address+52,4),code))
        visits=set();count=0
        for seed,phase,mode in itertools.product((0,127,128,255),(0,8),(0,1)):
            models=[]
            for code in (self.truth,self.words):
                memory=fixture(seed,phase)
                for registry,values in ((0x800A5760,(0x4D,0x22,0,0)),(0x800A5770,(0x23,0x5F,0,0))):
                    for n,v in enumerate(values):put(memory,registry+n*4,v)
                m=PacketOracle(code,seed,phase,mode,connected=connected,memory=memory).run()
                self.assertEqual(m.packets,[((0x4D,0x22),2,0,5)]+[((0x23,0x5F),2,STACK+phase-4,0x18)]*6)
                self.assertEqual([p[1][0]for p in m.payloads],list(ORDER))
                visits.update(m.visits);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(connected)<=visits)
        self.receipt.update(original_wrapper_words=26,all26_words_visited=True,wrapper_phases=count,
            registry_count_two=True,lower_dispatcher_bounded_provider_only=True,lower_stub_or_gameplay_execution_claimed=False)

    def test_05_independent_GNU_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.out,NAME);links=count=0
        for i in range(3):
            entry=0x17007FFC+i*0x10000
            syms=dict(func_15147D64=0x17203000+i*0x1000,func_151494E0=0x1730FFFC+i*0x20000);images=[]
            for label,obj in [('original',original),('C',self.obj)]:
                text,fs,rs=source.parse_object(obj);assembly,unknown=emit_function(text,fs[NAME],rs,NAME,syms);self.assertFalse(unknown)
                stem=self.out/('rebase-%d-%s'%(i,label));asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',NAME,*['--defsym=%s=0x%X'%p for p in syms.items()],'-o',str(elf),str(out)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>41I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(images[0],images[1])
            for seed,phase,mode in itertools.product((0,127,128,255),(0,8),(0,1)):
                self.compare(seed,phase,mode,images,syms,entry);count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,all7_R26_bindings=True)

    def test_06_original_caller_command8_and_default_not_current_stub(self):
        parent=list(struct.unpack_from('>95I',self.rom,0xCAC30))
        table=self.rom[0x243C6C:0x243C6C+160]
        self.assertEqual(struct.unpack_from('>I',table,6*4)[0],0x1509D854)
        visits=set();count=0
        for seed,phase,mode,command in itertools.product((0,255),(0,8),(0,1),(8,0,0xFFFFFFFF,42)):
            models=[]
            for code in (self.truth,self.words):
                memory=fixture(seed,phase);memory.update({0x8009F1AC+i:v for i,v in enumerate(table)})
                connected=dict(zip(range(ENTRY,ENTRY+164,4),code))
                m=PacketOracle(parent,seed,phase,mode,entry=PARENT,connected=connected,memory=memory,
                    arguments=(command,0x87654321,0x12345678,0xABCDEF01)).run()
                self.assertEqual(len(m.payloads),6 if command==8 else 0)
                if command==8:self.assertEqual([v[1][0]for v in m.payloads],list(ORDER))
                visits.update(m.visits);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue({0x1509D854,0x1509D858,0x1509D85C,0x1509D860,0x1509D8F0,0x1509D8F4,0x1509D8F8}<=visits)
        self.receipt.update(original_caller_extent_words=95,caller_phases=count,command8_and_unsigned_defaults=True,
            original_selected_paths_only=True,full95word_coverage_or_current_stub_execution_claimed=False)

    def test_07_fired_root_fault_prefixes(self):
        count=0
        for seed,phase,mode in itertools.product((0,255),(0,8),(0,1)):
            good=PacketOracle(self.truth,seed,phase,mode).run()
            for cut in range(good.root_accesses):
                models=[PacketOracle(code,seed,phase,mode)for code in (self.truth,self.words)]
                for m in models:m.root_fault=cut
                for m in models:
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));count+=1
        self.assertGreater(count,40)
        self.receipt.update(fired_root_fault_prefixes=count,portable_fault_or_MMU_claimed=False)

    def test_08_strict_image_32_inputs_and_corruptions(self):
        before=self.values['conker/build/conker.us.elf'];expected=source.predicted_image(before,self.rom)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes());at=source.elf_slot_offset(before,ENTRY,164)
        sym=next(pos for pos,n,f,_ in source.symbol_rows(before)if n==NAME and f[1:3]==(ENTRY,12))
        for pos in (0,len(expected)-1,at,at+159,at+163,at+164,sym+8):
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],self.rom)
        self.assertEqual(len(self.values),32)
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            current=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else expected if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),current)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_corruptions_rejected=8,live_and_historical_inputs=32,old_object_pinned=True,
            metadata_exclusions=0,guard_manifest_unchanged=True)


if __name__=='__main__':
    unittest.main()
