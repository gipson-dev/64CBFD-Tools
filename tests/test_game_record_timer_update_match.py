"""Record timers: packed flags, unsigned counters, original caller and exact image."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_timer_update_match as source
from tools.tests import game_record_timer_update_oracle as oracle
from tools.tests.game_record_timer_update_oracle import Case,fixture,reference,TimerOracle,put,read,faults,u32
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
def controls():
    b=source.SELECTED
    return dict(either_flag=b.replace('active &&','active ||'),missing_gate=b.replace('record->flags.timer.running == 1','1'),strict_threshold=b.replace('record->unk8 >=','record->unk8 >'),signed_threshold=b.replace('record->unk8 >=','(s32)record->unk8 >='),nine_records=b.replace('index < 10','index < 9'),double_increment=b.replace('record->value++;','record->value += 2;'),wrong_kind=b.replace('D_80088510[record->flags.timer.kind]','D_80088510[0]'),narrow_ticks=b.replace('(u32)D_800BE9E4','(u16)D_800BE9E4'),missing_modulo=b.replace('record->value %= limit;','record->value += 0;'))
def native_harness():
    t=source.HEADERS
    for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,'test_'+n)+'\n'
    t+=r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(GeneratedCD5A0Flags)==4&&sizeof(GeneratedCD5A0Record)==12)?1:-1];
GeneratedCD5A0Record D_800D3010[10];u16 D_80088510[16],D_8008851C[16];s32 D_800BE9E4;
typedef void(*Fn)(void);
static const u32 values[]={0,1,65535,0x7FFFFFFF,0x80000000,0xFFFFFFFF};
static int check(Fn fn){u32 f,d,v,p,i,k,a,b,old[10],expected[10][2];
for(f=0;f<256;f++)for(d=0;d<6;d++)for(v=0;v<6;v++)for(p=0;p<3;p++){
for(i=0;i<16;i++){D_80088510[i]=(u16)values[(i+p)%6];D_8008851C[i]=(u16)values[(i+p+1)%6];}
D_800BE9E4=(s32)values[d];
for(i=0;i<10;i++){GeneratedCD5A0Record*r=&D_800D3010[i];k=(f+i*17)&255;r->flags.timer.active=k>>7;r->flags.timer.running=(k>>6)&1;r->flags.timer.kind=(k>>2)&15;r->flags.timer.reserved=0x123456+i;old[i]=r->flags.word;r->value=values[v]+i;r->unk8=values[(v+1)%6]+i;a=r->value;b=r->unk8;
if((k&192)==192){b+=(u32)D_800BE9E4;k=(k>>2)&15;if(b>=D_80088510[k]){b-=D_80088510[k];a++;if(D_8008851C[k])a%=D_8008851C[k];}}expected[i][0]=a;expected[i][1]=b;}
fn();for(i=0;i<10;i++)if(D_800D3010[i].flags.word!=old[i]||D_800D3010[i].value!=expected[i][0]||D_800D3010[i].unk8!=expected[i][1])return 1;
}return 0;}
static int run(void){if(check(test_selected))return 10;
'''
    for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class RecordTimerUpdateTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>50I',cls.rom,source.ROM));cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'raw')
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    @classmethod
    def linked(cls,obj,entry,label,s=None,normalize=False):
        defs=oracle.symbols()if s is None else s
        if defs['D_800D3088']!=u32(defs['D_800D3010']+120):raise ValueError('Timer end alias no longer denotes ten records')
        text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION]
        if normalize:
            text,bindings=source.normalized_payload(*source.payload(obj));f=dict(f,value=0,size=len(text))
        assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=cls.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
    def compare(self,c=Case(),images=None,entry=None,s=None):
        initial,syms=fixture(c,s);wanted=reference(initial,syms);pair=[]
        for words in images or(self.truth,self.words,self.raw):
            m=TimerOracle(words,initial,c,entry=entry).run();self.assertEqual(m.memory,wanted,c);self.assertFalse(m.calls);pair.append(m)
        for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
        return pair[0]
    def test_01_owner_caller_ABI_Make_and_original_census(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),5)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),4);self.assertEqual(source.same_functions(self.out/'caller-before.o',self.out/'caller-after.o'),16);self.assertEqual((self.out/'caller-qualified.o').read_bytes(),self.values[source.CALLER_OBJECT])
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text());self.assertEqual(source.recovered_caller(self.values[source.CALLER_SOURCE].decode()),(self.out/'proposed-caller.c').read_text());self.assertIn('void func_150A019C(void);',(self.out/'proposed-caller.c').read_text())
        olddiag=(self.out/'caller-before-diagnostics.txt').read_text().replace('caller-before','CALLER');newdiag=(self.out/'caller-after-diagnostics.txt').read_text().replace('caller-after','CALLER');self.assertEqual(olddiag,newdiag);self.assertEqual(olddiag.count('Warning 712:'),3)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([i*4 for i,w in enumerate(ws)if w==jal],[0x476B4]);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual(struct.unpack_from('>6H',self.rom,0x22CFD0),(2,6,60,3600,20864,0))
        memory,syms=fixture(Case());self.assertEqual(bytes(memory[syms['D_80088510']+i]for i in range(44)),self.rom[0x22CFD0:0x22CFFC])
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(body_words=50,frame=0,bindings=10,guards=2,alias_only_normalization=True,neighbors=4,compact_functions=5,caller_functions_preserved=16,Make_commands=3,new_diagnostics=0,inherited_caller_warnings=3,original_direct_calls=1,signature_arguments=0,return_contract='void')
    def test_02_guest_flags_unsigned_wrap_thresholds_and_accesses(self):
        cases=[Case(flags=f,ticks=d,value=v,elapsed=e,pattern=p,mixed=True)for f,d,v,e,p in itertools.product(range(256),(0,1,0xFFFFFFFF),(0,0xFFFFFFFF),(0,0x80000000),(0,1))];visited=set()
        for c in cases:visited.update(self.compare(c).visits)
        self.assertEqual(visited,{source.ENTRY+4*i for i in range(50)}-{source.ENTRY+0xB0})
        for flag in(0,0x40,0x80):
            m=self.compare(Case(flags=flag));self.assertEqual(len(m.trace),10);self.assertTrue(all(t[0]=='R'and t[2]==4 for t in m.trace))
        m=self.compare(Case(flags=0xC0,ticks=10,elapsed=0));self.assertEqual(read(m.memory,oracle.symbols()['D_800D3010']+4),1);self.assertFalse(any(t[1]==oracle.symbols()['D_800D3088']for t in m.trace))
        self.receipt['guest']=dict(cases=len(cases)+4,covered_words=len(visited),unreachable_divide_trap=hex(source.ENTRY+0xB0),all_flag_bytes=True,unsigned_wrap=True,one_period_per_update=True,no_one_past_read=True)
    def test_03_original_caller_and_guest_alias_layouts(self):
        callers=aliases=0
        for c in(Case(flags=f,ticks=d,value=0xFFFFFFFF,elapsed=0xFFFFFFFF,pattern=p,phase=ph,mixed=True)for f,d,p,ph in itertools.product((0,0xC0,0xFC),(0,1,0xFFFFFFFF),(0,1),(0,8))):
            pair=[]
            for words in(self.truth,self.words,self.raw):
                m,wanted=oracle.caller_machine(self.rom,words,c);m.run();self.assertEqual(m.memory,wanted);self.assertEqual(m.calls,[(source.ENTRY,())]);self.assertEqual(m.r[29],oracle.STACK+c.phase+24);pair.append(m)
            for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
            callers+=1
        for a in(1,2,3):
            c=Case(flags=0xFC,ticks=0xFFFFFFFF,value=0x80000000,elapsed=3,alias=a,mixed=True);_,s=fixture(c);images=[self.linked(self.out/n,source.ENTRY,'alias-%d-%d'%(a,i),s)for i,n in enumerate(('original-'+source.FUNCTION+'.o','qualified-padded.o','selected.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for p,v in itertools.product((0,1),(0,0xFFFFFFFF)):self.compare(Case(flags=0xFC,value=v,elapsed=3,alias=a,pattern=p,mixed=True),images,s=s);aliases+=1
        self.receipt['callers']=dict(cases=callers,window_words=6,arguments=0,result_ignored=True,full_parent_or_gameplay=False,guest_alias_cases=aliases,guest_aliases_not_portable_C_domain=True)
    def test_04_native32_SDK_defined_arithmetic_and_controls(self):
        p=self.fresh/'native.c';p.write_text(native_harness());logs={}
        for opt in('-O0','-O2','-O3'):
            exe=self.fresh/('native'+opt);q=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(q.returncode,0,q.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=q.stderr)
        self.receipt['native']=dict(optimizations=logs,cases_per_optimization=256*6*6*3,controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,logical_bitfield_initialization=True,bitfield_byte_order_not_portability_claim=True)
    def test_05_direct_and_caller_fault_prefixes(self):
        direct=caller=delay=0
        for c in(Case(flags=0),Case(flags=0xC0,ticks=10),Case(flags=0xC4,ticks=0xFFFFFFFF,elapsed=1),Case(flags=0xFC,mixed=True,pattern=1)):
            initial,_=fixture(c);full=TimerOracle(self.truth,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words,self.raw):
                    m=TimerOracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(m.current_pc,m.delay_of))
                direct+=1;delay+=pair[0].delay_of is not None
        c=Case(flags=0xFC,ticks=17,mixed=True,pattern=1);full,_=oracle.caller_machine(self.rom,self.truth,c);full.run()
        for cut in range(full.all_accesses):
            pair=[]
            for words in(self.truth,self.words):
                m,_=oracle.caller_machine(self.rom,words,c);m.cut=cut
                with self.assertRaises(faults.AccessBoundary):m.run()
                pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));caller+=1
        self.receipt['faults']=dict(direct_prefixes=direct,caller_prefixes=caller,delay_slot_cuts=delay,complete_state_PC_and_trace=True,portable_C_fault_claimed=False)
    def test_06_normalization_guards_padder_and_three_rebases(self):
        raw,rs=source.payload(self.out/'selected.o');rejects=0
        for at in range(0,len(raw),4):
            b=bytearray(raw);b[at+3]^=1
            with self.assertRaises(ValueError):source.normalized_payload(bytes(b),rs)
            rejects+=1
        for at in rs:
            bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
            with self.assertRaises(ValueError):source.normalized_payload(raw,bad)
            rejects+=1
        bad=oracle.symbols();bad['D_800D3088']+=12
        with self.assertRaises(ValueError):self.linked(self.out/'selected.o',source.ENTRY,'wrong-end',bad)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        carry_controls=0
        for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
            s=oracle.symbols()if not j else oracle.symbols(0x88017FF0+j*0x10000,0x8804FFF0+j*0x10000,0x88078000+j*0x10000)
            images=[self.linked(self.out/n,entry,'rebase-%d-%d'%(j,i),s,normalize=i==2)for i,n in enumerate(('original-'+source.FUNCTION+'.o','make-shadow/src/game/generated_CD5A0.c.o','selected.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            unnormalized=self.linked(self.out/'selected.o',entry,'carry-control-%d'%j,s)
            # Confirm the carry control against GNU linking the untouched IDO
            # object, independently of emit_function's assembly reconstruction.
            direct=self.fresh/('direct-IDO-%d.elf'%j)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(self.fresh/('carry-control-%d.ld'%j)),'-e',source.FUNCTION,'-o',str(direct),str(self.out/'selected.o')],capture_output=True,check=True)
            direct_words=list(struct.unpack('>50I',sections(direct)['.text'][1][:200]));self.assertEqual(direct_words,images[0])
            if j:
                # Re-emitting in instruction order loses the original ELF's
                # paired relocation order for two addends of the same symbol.
                # The untouched compiler object above remains correct.
                self.assertNotEqual(unnormalized[0],images[0][0]);self.assertEqual(unnormalized[1:],images[0][1:]);carry_controls+=1
            else:self.assertEqual(unnormalized,images[0])
            for f,d,p in itertools.product((0,0x40,0x80,0xC0,0xFC),(0,1,0xFFFFFFFF),(0,1)):self.compare(Case(flags=f,ticks=d,value=0xFFFFFFFF,elapsed=0x80000000,pattern=p,mixed=True),images,entry,s);cases+=1
        self.receipt['rebases']=dict(layouts=3,cases=cases,raw_rejections=rejects,alias_negative=1,bindings=10,alias_guards=2,original_Make_and_normalized_C_linked=True,raw_fixed_layout_exact=True,assembly_reconstruction_carry_rejections=carry_controls,untouched_IDO_object_GNU_links=3,untouched_IDO_all_rebases_exact=True,padded_object_reproduced=True)
    def test_07_compiled_effective_semantic_negatives(self):
        evidence={};witnesses=[Case(flags=f,ticks=d,value=v,elapsed=e,pattern=p,mixed=True)for f,d,v,e,p in itertools.product((0,0x40,0x80,0xC0,0xC4,0xFC),(0,1,65536,0xFFFFFFFF),(0,0xFFFFFFFF),(0,2,0x80000000),(0,1))]
        for n,b in controls().items():
            self.assertNotEqual(b,source.SELECTED,n);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+b,'negative-'+n);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+n);found=False
            for c in witnesses:
                initial,s=fixture(c);m=TimerOracle(words,initial,c).run()
                if m.memory!=reference(initial,s):found=True;evidence[n]=dict(flags=c.flags,ticks=c.ticks,value=c.value,elapsed=c.elapsed,pattern=c.pattern);break
            self.assertTrue(found,n)
        self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True)
    def test_08_strict_image_metadata_and_all_frozen_inputs(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE)
        literal=b'D_80088510\0D_800D9910\0';pos=before.index(literal);positions=[20,at,at+200,source.elf_slot_offset(before,oracle.CALLER,24)]+list(range(0x2A8B34,0x2A8B54))+list(range(pos,pos+len(literal)))
        for pos in positions:
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        guards=source.guard_manifest(v['conker/retail_word_patches.us.csv']);self.assertTrue(guards.startswith(v['conker/retail_word_patches.us.csv']));self.assertEqual(guards,(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(len(guards[len(v['conker/retail_word_patches.us.csv']):].splitlines()),2);self.assertEqual(sum(a!=b for a,b in zip(before,expected)),167)
        self.receipt['image']=dict(changed_bytes=167,code_bytes=156,extent_bytes=1,metadata_bytes=10,exclusions=0,corruptions=len(positions)+1,inherited_guards_unchanged=True,new_alias_guards=2,protected_Game_bytes=189088,focused_inputs=len(v),caller_and_all_other_bodies_unchanged=True)

if __name__=='__main__':unittest.main()
