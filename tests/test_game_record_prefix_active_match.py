"""Prefix activity: first-read semantics, original caller, native bounds and strict image."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_prefix_active_match as source
from tools.tests import game_record_prefix_active_oracle as oracle
from tools.tests.game_record_prefix_active_oracle import Case,fixture,reference,public,PrefixOracle,put,read,faults,u32
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
def controls(native=False):
    b=source.SELECTED;rows=dict(wrong_stride=b.replace('i * 0x24','i * 0x20'),wrong_field=b.replace('i * 0x24','i * 0x24 + 1'),
        skip_first=b.replace('i = 0','i = 1'),skip_last=b.replace('i < count','i + 1 < count'),
        stop_after_first=b.replace('i < count','i < count && i == 0'),reverse_flag=b.replace('!= 0','== 0'),
        ignore_high_bit=b.replace('D_800D2DC0[i * 0x24] != 0','(s8)D_800D2DC0[i * 0x24] > 0'),wrong_true=b.replace('return 1;','return 2;'),wrong_false=b.replace('return 0;','return 1;'))
    if not native:rows['unsigned_count']=b.replace('i < count','(u32)i < (u32)count')
    return rows
def native_harness():
    t=source.HEADERS+'u8 D_800D2DC0[0x6C];\n'
    for n,b in dict(selected=source.SELECTED,**controls(True)).items():t+=b.replace(source.FUNCTION,'test_'+n)+'\n'
    t+=r'''
typedef char ABI[(sizeof(s32)==4&&sizeof(void*)==4&&sizeof(D_800D2DC0)==108)?1:-1];
typedef s32(*Fn)(s32);
static int check(Fn fn){s32 ci,hit,vi,dup,i,wanted;static const s32 counts[]={(-2147483647-1),-1,0,1,2,3,4,7,1000000,2147483647};static const u8 values[]={1,128,255};u8 before[108];
for(ci=0;ci<10;ci++)for(hit=-1;hit<3;hit++)for(vi=0;vi<3;vi++)for(dup=0;dup<2;dup++){
 if(counts[ci]>3&&hit<0)continue;
 for(i=0;i<108;i++)D_800D2DC0[i]=(u8)(i*29+0xA5);
 for(i=0;i<3;i++)D_800D2DC0[36*i]=(i==hit||(dup&&hit>=0&&i>hit))?values[vi]:0;
 for(i=0;i<108;i++)before[i]=D_800D2DC0[i];
 wanted=counts[ci]>0&&hit>=0&&hit<counts[ci];
 if(fn(counts[ci])!=wanted)return 1;
 for(i=0;i<108;i++)if(before[i]!=D_800D2DC0[i])return 2;
}return 0;}
static int run(void){if(check(test_selected))return 10;
'''
    for i,n in enumerate(controls(True)):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
class RecordPrefixActiveTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>50I',cls.rom,source.ROM))
        cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'selected');cls.caller=list(struct.unpack_from('>8I',cls.rom,oracle.CALLER_ROM))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    @classmethod
    def linked(cls,obj,entry,label,s=None):
        defs=oracle.symbols()if s is None else s;text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=cls.fresh/label
        p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
    def compare(self,c=Case(),images=None,entry=None,s=None):
        initial=fixture(c,s);answer,loads=reference(initial,c,s);pair=[]
        for words in images or(self.truth,self.words,self.raw):
            m=PrefixOracle(words,initial,c,entry=entry,s=s).run();self.assertEqual((m.r[2],m.memory,m.trace,m.calls),(answer,initial,loads,[]),c);pair.append(m)
        for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m))
        return pair[0]
    def test_01_complete_owner_Make_bindings_and_caller_census(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),7)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),6);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertFalse(source.NEW_GUARDS);self.assertEqual(len(source.BINDINGS),4)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([4*i for i,w in enumerate(ws)if w==jal],[oracle.CALLER_ROM]);self.assertFalse(any(w==source.ENTRY for w in ws))
        text=self.values[source.SOURCE].decode();self.assertIn('s32 func_15096D78() {\n    return 0;\n}',text);self.assertIn('bzero(D_800D2DC0, 0x6C);',text);self.assertIn('while (i != 3)',text)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(body_words=50,frame=0,bindings=4,guards=0,neighbors=6,compact_functions=7,Make_commands=3,new_diagnostics=0,original_direct_calls=1,aligned_pointer_uses=0,signed_count_argument=True,boolean_result=True,minimum_initialized_table_bytes=108)
    def test_02_exact_first_read_trace_and_four_way_unrolling(self):
        cases=[Case(count=n,hit=h,value=v,duplicate=d,phase=p)for n in range(38)for h in range(-1,n+1)for v,d,p in itertools.product((1,128,255),(False,True),(0,8))]
        cases += [Case(count=n,hit=h,phase=p)for n,h,p in itertools.product((-2147483648,-1,0),(-1,0,1),(0,8))]
        cases += [Case(count=n,hit=h,phase=p)for n,h,p in itertools.product((1000000,2147483647),(0,1,2,3,4,5),(0,8))]
        cases += [Case(count=9,hit=5,value=v)for v in range(256)]
        seen=set()
        for c in cases:seen.update(self.compare(c).visits)
        unreachable={source.ENTRY+x for x in(0x78,0x8C,0xA0)};self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+source.BODY,4))-unreachable)
        # Remove all bytes except required active flags: early exit must not
        # speculatively read the next flag or padding, including likely slots.
        sparse=0
        for n,h in itertools.product((0,1,2,3,4,5,7,8,9,37),(-1,0,1,2,3,4)):
            if h>=n:continue
            c=Case(count=n,hit=h);initial=fixture(c);answer,loads=reference(initial,c);needed={a for _,a,_,_ in loads};initial={a:b for a,b in initial.items()if oracle.STACK-1024<=a<oracle.STACK+768 or a in needed}
            for words in(self.truth,self.words,self.raw):m=PrefixOracle(words,initial,c).run();self.assertEqual((m.r[2],m.trace,m.memory),(answer,loads,initial))
            sparse+=1
        self.receipt['guest']=dict(cases=len(cases),sparse_cases=sparse,visited_words=47,unreachable_retained_offsets=['0x78','0x8C','0xA0'],all_flag_byte_values=True,all_remainder_classes=True,exact_first_read_trace=True,complete_state_equal=True,no_writes=True,large_backed_prefixes_guest_only=True)
    def test_03_original_caller_gate_and_consumed_result(self):
        count=0;seen=set()
        for n,h,mode,ret,phase in itertools.product((-2147483648,-1,0,1,2,3,4,7,9),(-1,0,1,2,3),(0,7),(0,1,0xFFFFFFFF),(0,8)):
            c=Case(count=n,hit=h,provider_mode=mode,provider_return=ret,phase=phase);pair=[]
            for words in(self.truth,self.words,self.raw):
                m,wanted=oracle.caller_machine(self.caller,words,c)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(wanted[0]),wanted[1],0),c);pair.append(m);seen.update(m.visits)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(complete(pair[0]),complete(pair[2]));count+=1
        self.assertTrue(set(range(oracle.CALLER,oracle.CALLER+32,4))<=seen)
        self.receipt['integration']=dict(caller_cases=count,caller_windows=1,window_words=8,all_window_words=True,branch_likely_result_gate=True,delay_slot_count_load=True,following_provider_bounded=True,provider_return_ignored=True,parent_C_still_placeholder=True,full_parent_or_gameplay_claimed=False)
    def test_04_native32_initialized_records_and_early_large_counts(self):
        p=self.fresh/'native.c';p.write_text(native_harness());logs={}
        for opt in('-O0','-O2','-O3'):
            exe=self.fresh/('native'+opt);r=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=r.stderr)
        self.receipt['native']=dict(optimizations=logs,cases_per_optimization=216,controls=len(controls(True)),SDK=True,pointers32=True,trapping_UBSan=True,table_bytes=108,three_records=True,large_counts_only_with_early_in_bounds_hit=True,all_bytes_unchanged=True)
    def test_05_direct_and_caller_access_fault_prefixes(self):
        direct=connected=delay=0
        for c in(Case(count=0),Case(count=1),Case(count=2,hit=1),Case(count=7,hit=5),Case(count=8),Case(count=9),Case(count=37,hit=31)):
            initial=fixture(c);full=PrefixOracle(self.truth,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words,self.raw):
                    m=PrefixOracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(m.current_pc,m.delay_of,cut))
                direct+=1;delay+=pair[0].delay_of is not None
        for c in(Case(count=-1),Case(count=0),Case(count=3,provider_mode=7),Case(count=7,hit=5),Case(count=8)):
            full,_=oracle.caller_machine(self.caller,self.truth,c)
            with self.assertRaises(WindowBoundary):full.run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m,_=oracle.caller_machine(self.caller,words,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));connected+=1
        self.receipt['faults']=dict(direct_prefixes=direct,caller_prefixes=connected,delay_slot_cuts=delay,complete_state_PC_and_trace=True,portable_C_fault_claimed=False)
    def test_06_padder_binding_rejections_and_three_GNU_layouts(self):
        raw,rs=source.payload(self.out/'selected.o');rejects=0
        for at in range(0,len(raw),4):
            bad=bytearray(raw);bad[at+3]^=1
            with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
            rejects+=1
        for at in rs:
            bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
            with self.assertRaises(ValueError):source.checked_payload(raw,bad)
            rejects+=1
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
        for j,(entry,table)in enumerate(((source.ENTRY,source.TABLE),(0x17007FFC,0x80017FFC),(0x2500FFFC,0x8001FFFC))):
            s=dict(D_800D2DC0=table);paths=(self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_C3E20.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for n,h,phase in itertools.product((-2147483648,-1,0,1,2,3,4,7,8,9,37),(-1,0,1,2,3,4,5),(0,8)):self.compare(Case(count=n,hit=h,phase=phase),images,entry,s);count+=1
        self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,HI_LO_bindings=4,all_three_objects_linked=True,no_guards=True,padded_object_reproduced=True)
    def test_07_compiled_and_terminating_semantic_counterexamples(self):
        evidence={};witnesses=[Case(count=n,hit=h,value=v)for n,h,v in itertools.product((1,2,3,4,7),(-1,0,1,2,3),(1,128,255))]
        for name,body in controls().items():
            self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name);effective=False
            for c in([Case(count=-1,hit=0)]if name=='unsigned_count'else witnesses):
                initial=fixture(c);m=PrefixOracle(words,initial,c).run();answer,_=reference(initial,c)
                if m.r[2]!=answer or m.memory!=initial:effective=True;evidence[name]=dict(count=c.count,hit=c.hit,value=c.value);break
            self.assertTrue(effective,name)
        self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True)
    def test_08_strict_entire_image_and_frozen_inputs(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)}
        positions=[20,at,at+source.SIZE,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.CALLER,32),0x2A0D94,0x2B03D4,0x2CF644,0x2E7160,0x30D508]
        for pos in positions:
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),148)
        self.receipt['image']=dict(changed_bytes=148,code_bytes=147,extent_bytes=1,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v),caller_and_all_other_bodies_unchanged=True)
