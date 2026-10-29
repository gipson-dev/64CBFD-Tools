"""Record position command: direct C, original helpers and caller ABI."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_position_command_match as source
from tools.tests import game_record_position_command_oracle as oracle
from tools.tests.game_record_position_command_oracle import Case,fixture,reference,public,PositionOracle,put,read,faults,u32
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
    b=source.SELECTED
    return dict(wrong_mode=b.replace('case 1:','case 2:'),wrong_actor_mask=b.replace('~0x2000','~0x1000'),wrong_id=b.replace('recordId & 0xFF','(recordId ^ 1) & 0xFF'),wrong_coordinate=b.replace('].x_position','].y_position'),wrong_record=b.replace('D_800CC2D0[objectIndex]','D_800CC2D0[objectIndex + 1]'),wrong_half=b.replace('command->unkC.s.unk2','command->unkC.s.unk0'),unsigned_half=b.replace('command->unkC.s.unk2','(u16)command->unkC.s.unk2'),wrong_height=b.replace('command->unk10, command->unk14','command->unk10, command->unk14 + 1'),wrong_x=b.replace('0xFF, command->unk8,','0xFF, command->unk8 + 1,'),wrong_return=b.replace('return 1;','return 0;'))

# Unsigned-half syntax is converted back to s16 by the declared helper ABI and
# is not a functional negative. Keep only actual semantic differences.
def effective_controls():return{n:b for n,b in controls().items()if n!='unsigned_half'}

def native_harness():
    t=source.HEADERS
    for n,b in dict(selected=source.SELECTED,**effective_controls()).items():t+=b.replace(source.FUNCTION,'test_'+n)+'\n'
    t+=r"""
typedef char ABI[(sizeof(s32)==4&&sizeof(void*)==4&&sizeof(struct127)==0x32C&&sizeof(struct215)==24)?1:-1];
struct127 D_800CC2D0[26];static struct215 command;static s32 index,mutation,calls,resolve_count,masked,kind;static u32 args[5];
__attribute__((noinline,noclone)) s32 func_15084000(s32 a){resolve_count++;masked=a;if(mutation){command.unkC.s.unk2=32767;command.unk8=0x10203040;}return index;}
__attribute__((noinline,noclone)) void func_15178BE4(u8 a,f32*b,s16 c){calls++;kind=0;args[0]=a;args[1]=(u32)b;args[2]=(s32)c;}
__attribute__((noinline,noclone)) void func_15178C34(u8 a,s32 b,s32 c,s32 d,s16 e){calls++;kind=1;args[0]=a;args[1]=b;args[2]=c;args[3]=d;args[4]=(s32)e;}
typedef s32(*Fn)(s32,s32,struct215*);
static const s32 modes[]={0,1,2,-1,0x7FFFFFFF,(s32)0x80000000};static const u32 values[]={0,1,0x2000,0xFFFFDFFF,0x7FFFFFFF,0x80000000,0xFFFFFFFF};
static int check(Fn fn){s32 mi,bi,ii,vi,j,id,mode,first,middle,third,last,half;u32 expected[5];
for(mi=0;mi<6;mi++)for(bi=0;bi<256;bi++)for(ii=0;ii<2;ii++)for(vi=0;vi<7;vi++)for(mutation=0;mutation<2;mutation++){
index=ii?25:0;id=(s32)(0x12345600U+bi);mode=modes[mi];first=values[vi];third=values[(vi+2)%7];last=values[(vi+3)%7];command.unk8=first;command.unkC.s.unk0=-123;command.unkC.s.unk2=(s16)values[(vi+1)%7];middle=command.unkC.i.unk0;half=command.unkC.s.unk2;command.unk10=third;command.unk14=last;
calls=resolve_count=0;kind=-1;masked=0;for(j=0;j<5;j++)args[j]=0xA5;
if(fn(id,mode,&command)!=(mode==0||mode==1))return 1;
if(mode==0){if(resolve_count!=1||(u32)masked!=((u32)first&0xFFFFDFFFU)||calls!=1||kind!=0)return 2;expected[0]=bi;expected[1]=(u32)&D_800CC2D0[index].x_position;expected[2]=mutation?32767:half;for(j=0;j<3;j++)if(args[j]!=expected[j])return 3;
}else if(mode==1){if(resolve_count||calls!=1||kind!=1)return 4;expected[0]=bi;expected[1]=first;expected[2]=middle;expected[3]=third;expected[4]=(s16)last;for(j=0;j<5;j++)if(args[j]!=expected[j])return 5;
}else if(resolve_count||calls)return 6;
}return 0;}
static int run(void){if(check(test_selected))return 10;
"""
    for i,n in enumerate(effective_controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class RecordPositionCommandTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>50I',cls.rom,source.ROM))
        cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'selected')
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    @classmethod
    def linked(cls,obj,entry,label,s=None):
        defs=oracle.symbols()if s is None else s;text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=cls.fresh/label
        p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))


    def compare(self,c=Case(),images=None,entry=None,s=None,connected=False):
        initial=fixture(c);wanted=reference(initial,c,s,connected);pair=[];code=oracle.helper_code(self.rom)if connected else None
        for words in images or(self.truth,self.words,self.raw):
            m=PositionOracle(words,initial,c,entry=entry,s=s,connected=code).run();self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(wanted[0]),wanted[1],wanted[2]),c);pair.append(m)
        for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
        return pair[0]
    def test_01_complete_owner_Make_bindings_and_caller_census(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),8)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),7);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertFalse(source.NEW_GUARDS)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertFalse(any(w==jal for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22CFB0]);self.assertEqual(struct.unpack_from('>I',self.rom,0x22CF94+7*4)[0],source.ENTRY)
        self.assertNotIn('NON-MATCHING:',(self.out/'proposed-owner.c').read_text())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(body_words=50,frame=40,bindings=5,guards=0,neighbors=7,compact_functions=8,Make_commands=3,new_diagnostics=0,original_direct_calls=0,aligned_pointer_uses=1,table_index=7,dispatch_routes=2,signature_arguments=3,return_contract='s32 boolean')
    def test_02_guest_modes_widths_late_reads_and_argument_homes(self):
        cases=[Case(ident=0x12345600+i,mode=m)for i,m in itertools.product(range(256),(0,1,2))]
        cases.extend(Case(mode=m,index=i,first=v,middle=v,last=v,mutation=mu,phase=ph)for m,i,v,mu,ph in itertools.product((0,1,2,0x80000000,0xFFFFFFFF),(-1,0,25),(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,2,3),(0,8)))
        visited=set()
        for c in cases:
            m=self.compare(c);visited.update(m.visits)
            if c.mode not in(0,1):self.assertFalse(m.calls);self.assertFalse(any(t[0]=='R'and oracle.COMMAND<=t[1]<oracle.COMMAND+24 for t in m.trace));self.assertFalse(any(t[0]=='R'and t[1]==oracle.STACK+c.phase for t in m.trace))
        self.assertEqual(len(visited),50)
        self.receipt['guest']=dict(cases=len(cases),covered_words=len(visited),all_ID_bytes=True,full_word_modes=True,actor_stride=0x32C,late_halfword_and_ID_home_reads=True,synthetic_guest_negative_index_not_native_C_domain=True)
    def test_03_original_helpers_and_two_indirect_callers(self):
        visited=set();connected=callers=0
        for c in(Case(mode=m,index=i,nodes=n,mutation=mu,phase=ph)for m,i,n,mu,ph in itertools.product((0,1),(-1,0,25),range(5),range(4),(0,8))):
            machine=self.compare(c,connected=True);visited.update(machine.visits);connected+=1
        coverage={hex(entry):sum(pc in visited for pc in range(entry,entry+4*n,4))for entry,offset,n in oracle.HELPERS}
        self.assertEqual(list(coverage.values()),[17,20,26,18]);self.assertNotIn(oracle.LOOKUP+0x34,visited)
        for window in(0,1):
            for mode,mu,nodes in itertools.product((0,1,2,0xFFFFFFFF),range(4),(0,2)):
                for opcode in((0,8)if window==0 else(8,)):
                    c=Case(mode=mode,mutation=mu,nodes=nodes);pair=[]
                    for words in(self.truth,self.words,self.raw):
                        m,wanted=oracle.caller_machine(self.rom,words,c,window,opcode)
                        with self.assertRaises(WindowBoundary):m.run()
                        self.assertEqual(public(m.memory),public(wanted[0]));self.assertEqual(m.calls,wanted[1])
                        if opcode:self.assertEqual(m.r[2],wanted[2])
                        pair.append(m)
                    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
                    callers+=1
        self.receipt['integration']=dict(connected_cases=connected,caller_cases=callers,caller_windows=2,helper_words=82,reachable_helper_words=81,helper_coverage=coverage,original_unreachable_duplicate_load=hex(oracle.LOOKUP+0x34),original_table_index=7,full_parent_or_gameplay=False)
    def test_04_native32_SDK_optimizations_and_effective_controls(self):
        p=self.fresh/'native.c';p.write_text(native_harness());logs={}
        for opt in('-O0','-O2','-O3'):
            exe=self.fresh/('native'+opt);r=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=r.stderr)
        self.receipt['native']=dict(optimizations=logs,cases_per_optimization=6*256*2*7*2,controls=len(effective_controls()),SDK=True,pointers32=True,trapping_UBSan=True,valid_26_actor_backing=True,host_numeric_union_fields=True,guest_home_perturbation_and_negative_index_not_portable_C_claim=True)
    def test_05_direct_connected_and_caller_fault_prefixes(self):
        direct=callers=delay=0
        for c,connected in((Case(mode=2),False),(Case(mutation=3),False),(Case(mode=1),False),(Case(mutation=3),True),(Case(mode=1,nodes=4),True)):
            initial=fixture(c);code=oracle.helper_code(self.rom)if connected else None;full=PositionOracle(self.truth,initial,c,connected=code).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words,self.raw):
                    m=PositionOracle(words,initial,c,connected=code);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(m.current_pc,m.delay_of,cut))
                direct+=1;delay+=pair[0].delay_of is not None
        for window in(0,1):
            c=Case(mutation=3);full,_=oracle.caller_machine(self.rom,self.truth,c,window)
            with self.assertRaises(WindowBoundary):full.run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m,_=oracle.caller_machine(self.rom,words,c,window);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));callers+=1
        self.receipt['faults']=dict(direct_and_connected_prefixes=direct,caller_prefixes=callers,delay_slot_cuts=delay,complete_state_PC_and_trace=True,portable_C_fault_claimed=False)
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
        for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
            s=oracle.symbols()if j==0 else {n:entry+0x10000+i*0x1000+(0x7FFC if i%2 else 0x8000)for i,n in enumerate(oracle.symbols())}
            paths=(self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game_CB1C0.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for mo,idx,mu,ph in itertools.product((0,1,2),(-1,0,25),(0,3),(0,8)):self.compare(Case(mode=mo,index=idx,mutation=mu,phase=ph),images,entry,s);count+=1
        self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,bindings=5,all_three_objects_linked=True,no_guards=True,padded_object_reproduced=True)
    def test_07_compiled_semantic_negatives_and_scheduling_control(self):
        evidence={};witnesses=[Case(mode=m,first=v,middle=0x12348000,last=0xFFFFFFFF)for m,v in itertools.product((0,1,2),(0,0x2000,0x1000,0xFFFFFFFF))]
        for name,body in effective_controls().items():
            self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name);effective=False
            for c in witnesses:
                initial=fixture(c);m=PositionOracle(words,initial,c).run();wanted=reference(initial,c)
                if(public(m.memory),m.calls,m.r[2])!=(public(wanted[0]),wanted[1],wanted[2]):effective=True;evidence[name]=dict(mode=c.mode,first=c.first);break
            self.assertTrue(effective,name)
        body=source.SELECTED.replace('volatile s32 recordId','s32 recordId');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'order-control');self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'order-control-link');self.assertEqual(len(words),49)
        c=Case(mode=2);initial=fixture(c);original=PositionOracle(self.truth,initial,c).run();control=PositionOracle(words,initial,c).run();self.assertEqual((original.r[2],public(original.memory)),(control.r[2],public(control.memory)));self.assertNotEqual(original.trace,control.trace)
        self.assertFalse(any(t[0]=='R'and t[1]==oracle.STACK for t in original.trace));self.assertTrue(any(t[0]=='R'and t[1]==oracle.STACK for t in control.trace))
        self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,nonvolatile_scheduling_control_words=49,conditional_home_read_difference=True,qualifier_not_historical_source_proof=True)
    def test_08_strict_entire_image_and_frozen_inputs(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)}
        positions=[20,at,at+source.SIZE,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.WINDOWS[0][0],32),0x2BA144,0x2D4E84,0x2FBC30]
        for pos in positions:
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),153)
        self.receipt['image']=dict(changed_bytes=153,code_bytes=152,extent_bytes=1,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v),caller_and_all_other_bodies_unchanged=True)
