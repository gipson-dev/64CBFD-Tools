"""Menu scene callback: direct C, signed records, callers and literal whole image."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_menu_scene_choice_match as source
from tools.tests import game_menu_scene_choice_oracle as oracle
from tools.tests.game_menu_scene_choice_oracle import Case,fixture,reference,public,MenuSceneOracle,put,read,faults,u32
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
    return dict(unsigned_choice=b.replace('choiceIndex = D_','choiceIndex = (u8)D_'),
        wrong_menu_stride=b.replace('* 10','* 9'),wrong_record=b.replace('[choiceIndex]','[choiceIndex + 1]'),
        positive_mode=b.replace('if (D_800E0C00[0])','if (D_800E0C00[0] > 0)'),
        swapped_sequence=b.replace('sequence = choice->alternateSequence','sequence = choice->sequence'),
        unsigned_scene=b.replace('choice->scene,','(u16)choice->scene,'),
        unsigned_sequence=b.replace('sequence = choice->','sequence = (u8)choice->'),
        wrong_fifth=b.replace('sequence, 0, 0, 0','sequence, 0, 0, 1'),
        omitted_fallback=b.replace('func_151E2834();',';'),
        wrong_state=b.replace('D_800E0B94 = 5','D_800E0B94 = 4'),
        missing_flag=b.replace('        D_8008FD90 = 1;',''),
        early_flags=b.replace('        func_1501D348(choice->scene, sequence, 0, 0, 0);\n','').replace('        D_8008FD90 = 1;','        D_8008FD90 = 1;\n        func_1501D348(choice->scene, sequence, 0, 0, 0);'))


def native_harness():
    t=source.HEADERS
    for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,'test_'+n)+'\n'
    t+=r"""
typedef char ABI[(sizeof(s32)==4&&sizeof(void*)==4&&sizeof(MenuSceneChoice20AE20)==4&&((s8)255)==-1)?1:-1];
s8 D_800AB692[130],D_800E0C00[1],D_8008FD8C,D_8008FD90;
u8 D_8008FD80,D_800E0B94;MenuSceneChoice20AE20 D_800AB7A4[256];
static s8 state[128],other[128];s8 *D_8008FDD4=state;static s32 calls,kind,args[5],mutation;
static void effect(void){if(mutation){state[0x42]=-1;D_8008FDD4=other;D_800AB692[0]=-1;D_800E0C00[0]=-128;D_800AB7A4[0].scene=-1;D_800AB7A4[0].sequence=-1;D_800AB7A4[0].alternateSequence=-1;D_8008FD80=D_800E0B94=204;D_8008FD8C=D_8008FD90=-52;}}
__attribute__((noinline,noclone)) void func_1501D348(s32 a,s32 b,s32 c,s32 d,s32 e){calls++;kind=1;args[0]=a;args[1]=b;args[2]=c;args[3]=d;args[4]=e;effect();}
__attribute__((noinline,noclone)) s32 func_151E2834(void){calls++;kind=2;effect();return -123;}
typedef void(*Fn)(void);
static const s16 scenes[]={-32768,-1,0,32767};static const s8 modes[]={0,1,-128,-1};
static int check(Fn fn){int i,j,k,mi,ci,idx,scene,normal,alt,selected;
for(idx=0;idx<13;idx+=6)for(ci=0;ci<256;ci++)for(mi=0;mi<4;mi++)for(k=0;k<4;k++)for(mutation=0;mutation<2;mutation++){
for(i=0;i<130;i++)D_800AB692[i]=-91;for(i=0;i<128;i++)state[i]=other[i]=-91;
scene=scenes[k];normal=(s8)(ci+128);alt=(s8)(127-ci);
for(i=0;i<256;i++){D_800AB7A4[i].scene=(s16)(scene+i);D_800AB7A4[i].sequence=(s8)(normal+i);D_800AB7A4[i].alternateSequence=(s8)(alt-i);}
D_8008FDD4=state;state[0x42]=(s8)idx;D_800AB692[idx*10]=(s8)ci;selected=(s8)ci;
D_800AB7A4[ci].scene=(s16)scene;D_800AB7A4[ci].sequence=(s8)normal;D_800AB7A4[ci].alternateSequence=(s8)alt;
D_800E0C00[0]=modes[mi];D_8008FD80=D_800E0B94=165;D_8008FD8C=D_8008FD90=-91;calls=kind=0;
for(j=0;j<5;j++)args[j]=123;fn();if(calls!=1||kind!=(selected<0?2:1))return 1;
if(selected>=0){if(args[0]!=scene||args[1]!=(modes[mi]?alt:normal)||args[2]||args[3]||args[4])return 2;
if(D_8008FD80!=1||D_800E0B94!=5||D_8008FD8C!=1||D_8008FD90!=1)return 3;
}else{int expected=mutation?204:165;if(D_8008FD80!=expected||D_800E0B94!=expected||(u8)D_8008FD8C!=expected||(u8)D_8008FD90!=expected)return 4;}
if(mutation&&D_8008FDD4!=other)return 5;
}return 0;}
static int run(void){if(check(test_selected))return 10;
"""
    for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class MenuSceneChoiceTests(unittest.TestCase):
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

    def compare(self,c=Case(),images=None,entry=None,s=None):
        initial=fixture(c,s);wanted=reference(initial,c,s);pair=[]
        for words in images or(self.truth,self.words,self.raw):
            m=MenuSceneOracle(words,initial,c,entry=entry,s=s).run();self.assertEqual((public(m.memory),m.calls,m.observations),(public(wanted[0]),wanted[1],wanted[2]),c);pair.append(m)
        for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
        return pair[0]
    def test_01_complete_owner_Make_bindings_and_caller_census(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),60)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),59);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertFalse(source.NEW_GUARDS)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertFalse(any(w==jal for w in ws));self.assertFalse(any(w==source.ENTRY for w in ws))
        text=self.values[source.ASM].decode();self.assertEqual(text.count('%hi(func_151E4314)'),2);self.assertEqual(text.count('%lo(func_151E4314)'),2)
        self.assertEqual(self.rom[0x250264:0x25027C].hex(),'001a010100240101002d0103002b010200300304003f0103')
        # Original callee saves the scene and sequence and homes the fourth argument.
        provider=struct.unpack_from('>18I',self.rom,0x4A7F8)
        self.assertEqual(provider[0],0x27BDFF88);self.assertIn(0x00A08025,provider);self.assertIn(0x00808825,provider)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(body_words=50,frame=32,bindings=20,guards=0,neighbors=59,compact_functions=60,Make_commands=3,new_diagnostics=0,original_direct_calls=0,aligned_pointer_uses=0,registration_routes=2,indirect_invocation_windows=1,signature_arguments=0,return_contract='void',provider_arguments=5)
    def test_02_guest_signed_bytes_fields_aliases_and_callback_effects(self):
        cases=[]
        for byte in range(256):
            cases.extend((Case(choice=byte),Case(index=byte),Case(mode=byte),Case(sequence=byte),Case(mode=1,alternate=byte)))
        cases.extend(Case(choice=ch,mode=mo,scene=sc,mutation=mu,phase=ph,alias=a)for ch,mo,sc,mu,ph,a in itertools.product((-128,-1,0,5,127),(0,128),(-32768,-1,0,32767),(0,1),(0,8),range(3)))
        visited=set()
        for c in cases:
            m=self.compare(c);visited.update(m.visits)
            if oracle.signed8(c.choice)<0:
                self.assertFalse(any(t[0]=='R'and t[1]==0x800E0C00 for t in m.trace))
            else:
                writes=[(t[1],t[3])for t in m.trace if t[0]=='W'and t[1]in(0x8008FD80,0x800E0B94,0x8008FD8C,0x8008FD90)]
                self.assertEqual(writes,[(0x8008FD80,1),(0x800E0B94,5),(0x8008FD8C,1),(0x8008FD90,1)])
        self.assertEqual(len(visited),50)
        self.receipt['guest']=dict(cases=len(cases),covered_words=len(visited),all_byte_patterns_in_five_fields=True,guest_alias_forms=3,callback_effects=True,saved_registers_and_full_private_state=True,synthetic_backing_not_retail_table_extent=True)
    def test_03_original_registration_and_indirect_invocation(self):
        registrations=dispatches=0
        for window in(0,1):
            for choice,selector,buttons,mode,mutation in itertools.product((-1,0,5),(-1,0,5),(0,16,32,48),(0,128),(0,1)):
                c=Case(choice=choice,mode=mode,mutation=mutation);pair=[]
                for words in(self.truth,self.words):
                    m,wanted=oracle.window_machine(self.rom,words,c,window,selector,buttons)
                    with self.assertRaises(WindowBoundary):m.run()
                    self.assertEqual(public(m.memory),public(wanted));pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));registrations+=1
                initial=pair[0].memory;called=read(initial,oracle.CALLBACK);expected=reference(initial,c)if called==source.ENTRY else None
                pair=[]
                for words in(self.truth,self.words):
                    m,_=oracle.window_machine(self.rom,words,c,2,initial=initial)
                    with self.assertRaises(WindowBoundary):m.run()
                    if expected is not None:
                        self.assertEqual(public(m.memory),public(expected[0]));self.assertEqual(m.calls,[(source.ENTRY,())]+expected[1])
                    else:
                        wanted=dict(initial);oracle.effect(wanted,c,oracle.symbols());self.assertEqual(public(m.memory),public(wanted));self.assertEqual(m.calls,[(source.FALLBACK,())])
                    pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));dispatches+=1
        self.receipt['callers']=dict(registrations=registrations,dispatches=dispatches,window_words=[20,21,4],original_installers_and_indirect_invocation=True,return_value_unused=True,full_parent_or_gameplay=False)
    def test_04_native32_SDK_optimizations_and_effective_controls(self):
        p=self.fresh/'native.c';p.write_text(native_harness());logs={}
        for opt in('-O0','-O2','-O3'):
            exe=self.fresh/('native'+opt);r=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=r.stderr)
        self.receipt['native']=dict(optimizations=logs,cases_per_optimization=3*256*4*4*2,controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,synthetic_defined_table_backing=True,guest_aliases_not_portable_C_claim=True)
    def test_05_direct_and_caller_access_fault_prefixes(self):
        direct=callers=delay=0
        for c in(Case(choice=-128),Case(mode=0,mutation=1),Case(mode=128,alias=2,mutation=1)):
            initial=fixture(c);full=MenuSceneOracle(self.truth,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words,self.raw):
                    m=MenuSceneOracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(m.current_pc,m.delay_of,cut))
                direct+=1;delay+=pair[0].delay_of is not None
        for window in range(3):
            c=Case(mode=128,mutation=1);initial=fixture(c);put(initial,oracle.CALLBACK,source.ENTRY);full,_=oracle.window_machine(self.rom,self.truth,c,window,buttons=16,initial=initial)
            with self.assertRaises(WindowBoundary):full.run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m,_=oracle.window_machine(self.rom,words,c,window,buttons=16,initial=initial);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));callers+=1
        self.receipt['faults']=dict(direct_prefixes=direct,caller_prefixes=callers,delay_slot_cuts=delay,complete_state_PC_and_trace=True,portable_C_fault_claimed=False)
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
            paths=(self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_20AE20.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for ch,mo,mu,ph in itertools.product((-128,-1,0,5,127),(0,128),(0,1),(0,8)):self.compare(Case(choice=ch,mode=mo,mutation=mu,phase=ph),images,entry,s);count+=1
        self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,bindings=20,all_three_objects_linked=True,no_guards=True,padded_object_reproduced=True)
    def test_07_compiled_and_terminating_semantic_counterexamples(self):
        evidence={};witnesses=[Case(choice=ch,mode=mo,mutation=mu)for ch,mo,mu in itertools.product((-128,-1,0,5),(0,128),(0,1))]
        for name,body in controls().items():
            self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name);effective=False
            for c in witnesses:
                initial=fixture(c);m=MenuSceneOracle(words,initial,c).run();wanted=reference(initial,c)
                if(public(m.memory),m.calls)!=(public(wanted[0]),wanted[1]):effective=True;evidence[name]=dict(choice=c.choice,mode=c.mode,mutation=c.mutation);break
            self.assertTrue(effective,name)
        self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True)
    def test_08_strict_entire_image_and_frozen_inputs(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);named={n:(p,f,st)for p,n,f,st in source.symbol_rows(before)}
        positions=[20,at,at+source.SIZE,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.WINDOWS[0][0],32)]
        for first,names,_ in source.METADATA_GROUPS:
            positions.extend(range(first,first+16*len(names)));start=named[names[0]][2];positions.extend(range(start,start+sum(len(n)+1 for n in names)))
        for pos in positions:
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),244)
        self.receipt['image']=dict(changed_bytes=244,code_bytes=159,extent_bytes=1,closed_metadata_bytes=84,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v),caller_and_all_other_bodies_unchanged=True)
