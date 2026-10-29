"""Direct bounce sound recovery: original callers/helpers, native ABI and strict image."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_bounce_random_sound_match as source
from tools.tests import game_bounce_random_sound_oracle as oracle
from tools.tests.game_bounce_random_sound_oracle import Case,fixture,reference,public,BounceSoundOracle,put,read,faults,u32
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
    return dict(signed_modulo=b.replace('(u32)func_150ADA20() % 9','func_150ADA20() % 9'),
        wrong_divisor=b.replace('% 9','% 10'),wrong_sound=b.replace('+ 0x2DE','+ 0x2DF'),
        wrong_volume=b.replace('0x2EE0','0x5DC0'),wrong_gate=b.replace('& 1','& 2'),
        inverted_gate=b.replace('if (func_150ADA20() & 1)','if (!(func_150ADA20() & 1))'),
        missing_second_draw=b.replace('(u32)func_150ADA20() % 9','0U % 9'),
        swapped_coordinates=b.replace('(s32)x, (s32)y','(s32)y, (s32)x'),
        wrong_radius=b.replace('500, 1000','501, 1000'),wrong_range=b.replace('500, 1000','500, 1001'),
        missing_bounce=b.replace('    func_15133B98(actor, x, y, z, height, contact);\n',''),
        wrong_return=b.replace('return 1;','return 0;'))

def native_harness():
    t=source.HEADERS
    for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,'test_'+n)+'\n'
    t+=r'''
typedef char ABI[(sizeof(s32)==4&&sizeof(void*)==4&&sizeof(f32)==4&&sizeof(s16)==2&&((s16)65535)==-1)?1:-1];
static u8 actor[512];static u32 gate,sample;static s32 draws,bc,ac;static u32 bounceArgs[6],audioArgs[10];
static u32 raw(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
__attribute__((noinline,noclone)) s32 func_15133B98(u8*a,f32 x,f32 y,f32 z,f32 h,void*p){
bc++;bounceArgs[0]=(u32)a;bounceArgs[1]=raw(x);bounceArgs[2]=raw(y);bounceArgs[3]=raw(z);bounceArgs[4]=raw(h);bounceArgs[5]=(u32)p;actor[128]=71;return -123;}
__attribute__((noinline,noclone)) s32 func_150ADA20(void){u32 v=draws?sample:gate;draws++;actor[129]=(u8)draws;return(s32)v;}
__attribute__((noinline,noclone)) u16 func_10010F88(s32 a,u16 b,s16 c,u8 d,s32 e,s16 f,s16 g,s16 h,s16 i,s16 j){
ac++;audioArgs[0]=a;audioArgs[1]=b;audioArgs[2]=c;audioArgs[3]=d;audioArgs[4]=e;audioArgs[5]=f;audioArgs[6]=g;audioArgs[7]=h;audioArgs[8]=i;audioArgs[9]=j;actor[130]=91;return 0xFFFF;}
typedef s32(*Fn)(u8*,f32,f32,f32,f32,void*);
static const u32 values[]={0,1,2,3,8,9,10,17,18,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF};
static const f32 coords[][3]={{0,-0.0f,0},{1.75f,-1.75f,17.5f},{32767.75f,-32768.75f,65535.75f},{-65536.75f,65536.75f,123.25f},{1073741824.0f,-1073741824.0f,2147483520.0f}};
static int check(Fn fn){int gi,si,pi,i;u32 expected[10];
for(gi=0;gi<13;gi++)for(si=0;si<13;si++)for(pi=0;pi<5;pi++){
gate=values[gi];sample=values[si];draws=bc=ac=0;for(i=0;i<512;i++)actor[i]=0;
if(fn(actor,coords[pi][0],coords[pi][1],coords[pi][2],17.25f,actor+0x114)!=1)return 1;
if(bc!=1||bounceArgs[0]!=(u32)actor||bounceArgs[4]!=raw(17.25f)||bounceArgs[5]!=(u32)(actor+0x114)||actor[128]!=71)return 2;
for(i=0;i<3;i++)if(bounceArgs[1+i]!=raw(coords[pi][i]))return 3;
if(draws!=1+(s32)(gate&1)||ac!=(s32)(gate&1)||actor[129]!=draws)return 4;
if(gate&1){expected[0]=sample%9U+0x2DE;expected[1]=0x2EE0;expected[2]=expected[3]=expected[4]=0;
for(i=0;i<3;i++)expected[5+i]=(s16)(s32)coords[pi][i];expected[8]=500;expected[9]=1000;
for(i=0;i<10;i++)if(audioArgs[i]!=expected[i])return 5;if(actor[130]!=91)return 6;
}else if(actor[130])return 7;
}return 0;}
static int run(void){if(check(test_selected))return 10;
'''
    for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class BounceRandomSoundTests(unittest.TestCase):
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
        initial=fixture(c);wanted=reference(initial,c,s,connected);pair=[];code=oracle.helper_code(self.rom,c.actual_rng)if connected else None
        for words in images or(self.truth,self.words,self.raw):
            m=BounceSoundOracle(words,initial,c,entry=entry,s=s,connected=code).run();self.assertEqual((m.r[2],public(m.memory),m.calls,m.observations),(1,public(wanted[0]),wanted[1],wanted[2]),c);pair.append(m)
        for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
        return pair[0]
    def test_01_complete_owner_Make_bindings_and_caller_census(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),2);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),31)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),30);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertFalse(source.NEW_GUARDS)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertFalse(any(w==jal for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22E424]);self.assertEqual(struct.unpack_from('>I',self.rom,0x22E3F4+12*4)[0],source.ENTRY)
        text=self.values[source.ASM].decode();self.assertEqual(text.count('%lo(D_80089934)'),2)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(body_words=50,frame=48,bindings=4,guards=0,neighbors=30,compact_functions=31,Make_commands=5,new_diagnostics=0,inherited_pointer_warnings=2,original_direct_calls=0,aligned_pointer_uses=1,table_index=12,dispatch_routes=2,signature_arguments=6)
    def test_02_guest_random_choices_float_conversion_and_live_homes(self):
        values=(0,1,2,3,8,9,10,17,18,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF)
        cases=[Case(gate=g,sample=s,position=p,phase=phase,scale=(s+p)%4,velocity=s%5)for g,s,p,phase in itertools.product(values,values,range(5),(0,8))]
        cases += [Case(gate=g,sample=s,mutation=m,phase=phase)for g,s,m,phase in itertools.product((0,1),(0,8,0xFFFFFFFF),(1,2,3),(0,8))]
        seen=set()
        for c in cases:seen.update(self.compare(c).visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+200,4))<=seen)
        self.receipt['guest']=dict(cases=len(cases),all_50_words_visited=True,all_nine_sound_choices=True,unsigned_high_bit_samples=True,complete_register_memory_trace_equal=True,live_coordinate_home_perturbations_guest_only=True)
    def test_03_original_bounce_rng_audio_and_two_dispatch_routes(self):
        count=0;seen=set()
        for scale,velocity,seed,p,phase in itertools.product(range(4),range(5),oracle.SEEDS,range(2),(0,8)):
            c=Case(scale=scale,velocity=velocity,seed=seed,position=p,phase=phase,actual_rng=True);seen.update(self.compare(c,connected=True).visits);count+=1
        for entry,_,n in oracle.HELPERS+((source.RANDOM,0xDAED0,18),):self.assertTrue(set(range(entry,entry+n*4,4))<=seen,(hex(entry),sorted(set(range(entry,entry+n*4,4))-seen)))
        callers=0
        for window,index in((0,0),(0,12),(1,12)):
            for gate,sample,position,phase in itertools.product((0,1),(0,8,0x80000000,0xFFFFFFFF),range(5),(0,8)):
                c=Case(gate=gate,sample=sample,position=position,phase=phase,scale=position%4,velocity=position);pair=[]
                for words in(self.truth,self.words,self.raw):
                    m,wanted,called=oracle.caller_machine(self.rom,words,c,window,index)
                    with self.assertRaises(WindowBoundary):m.run()
                    self.assertEqual((public(m.memory),m.calls,m.observations),(public(wanted[0]),wanted[1],wanted[2]),(window,index,c));pair.append(m)
                    if called:self.assertEqual(m.r[2],1)
                    if window==1:self.assertEqual(m.memory[oracle.STACK+phase+0x4F],1)
                for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m))
                callers+=1
        self.receipt['integration']=dict(connected_cases=count,caller_cases=callers,caller_windows=2,original_helpers_words=[48,18,29],all_helper_words=True,table_index_and_null_gate=True,saved_byte_result_consumed=True,original_rng_seed_effects=True,full_parent_or_gameplay_claimed=False)
    def test_04_native32_typed_forwarding_and_audio_narrowing(self):
        p=self.fresh/'native.c';p.write_text(native_harness());logs={}
        for opt in('-O0','-O2','-O3'):
            exe=self.fresh/('native'+opt);r=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=r.stderr)
        self.receipt['native']=dict(optimizations=logs,cases_per_optimization=845,controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,finite_s32_representable_coordinates=True,typed_s16_audio_parameters=True,guest_home_corruption_not_portable_C_claim=True)
    def test_05_direct_and_caller_access_fault_prefixes(self):
        direct=callers=delay=0
        for c,connected in((Case(gate=0),False),(Case(gate=1,sample=0xFFFFFFFF,mutation=2),False),(Case(gate=1,scale=2,velocity=4),True),(Case(actual_rng=True,seed=1),True)):
            initial=fixture(c);code=oracle.helper_code(self.rom,c.actual_rng)if connected else None;full=BounceSoundOracle(self.truth,initial,c,connected=code).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words,self.raw):
                    m=BounceSoundOracle(words,initial,c,connected=code);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(m.current_pc,m.delay_of,cut))
                direct+=1;delay+=pair[0].delay_of is not None
        for window,index in((0,0),(0,12),(1,12)):
            c=Case(sample=0x80000000,scale=2,velocity=4);full,_,_=oracle.caller_machine(self.rom,self.truth,c,window,index)
            with self.assertRaises(WindowBoundary):full.run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m,_,_=oracle.caller_machine(self.rom,words,c,window,index);m.cut=cut
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
            s=oracle.symbols()if j==0 else dict(zip(oracle.symbols(),(entry+0x1004,entry+0x2134,entry+0x4310)))
            paths=(self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_15F680.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for g,sample,p,phase in itertools.product((0,1),(0,8,9,0x80000000,0xFFFFFFFF),range(5),(0,8)):self.compare(Case(gate=g,sample=sample,position=p,phase=phase),images,entry,s);count+=1
        self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,external_call_bindings=4,all_three_objects_linked=True,no_guards=True,padded_object_reproduced=True)
    def test_07_compiled_and_terminating_semantic_counterexamples(self):
        evidence={};witnesses=[Case(gate=g,sample=s)for g,s in itertools.product((0,1,2,3),(0,1,8,9,0x80000000,0xFFFFFFFF))]
        for name,body in controls().items():
            self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name);effective=False
            for c in witnesses:
                initial=fixture(c);m=BounceSoundOracle(words,initial,c).run();wanted=reference(initial,c)
                if(m.r[2],public(m.memory),m.calls)!=(1,public(wanted[0]),wanted[1]):effective=True;evidence[name]=dict(gate=c.gate,sample=c.sample);break
            self.assertTrue(effective,name)
        self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True)
    def test_08_strict_entire_image_and_frozen_inputs(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)}
        positions=[20,at,at+source.SIZE,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.WINDOWS[0][0],32),0x2A0D94,0x2B03D4,0x2CF644,0x2E7160,0x30D508]
        for pos in positions:
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),146)
        self.receipt['image']=dict(changed_bytes=146,code_bytes=145,extent_bytes=1,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v),caller_and_all_other_bodies_unchanged=True)
