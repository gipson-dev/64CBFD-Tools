"""Actor sound teardown: direct C, original callers/helpers, native ABI and strict image."""
from pathlib import Path
from dataclasses import replace
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_audio_release_match as source
from tools.tests import game_actor_audio_release_oracle as oracle
from tools.tests.game_actor_audio_release_oracle import Case,fixture,reference,public,AudioReleaseOracle,put,read,faults,u32
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls(native=False):
    b=source.SELECTED
    rows=dict(reverse_match=b.replace('== actor','!= actor'),
        retain_slot=b.replace('D_800D99D0[slot] = NULL;','D_800D99D0[slot] = (Generated1104D0Actor *)actor;'),
        wrong_handle=b.replace('func_100111C8(*(u16 *)(actor + 0x4A));','func_100111C8(*(u16 *)(actor + 0x4A) + 1);'),
        early_clear=b.replace('func_100111C8(*(u16 *)(actor + 0x4A));','*(u16 *)(actor + 0x4A) = 0;\n        func_100111C8(*(u16 *)(actor + 0x4A));'),
        retain_handle=b.replace('*(u16 *)(actor + 0x4A) = 0;',''),
        wrong_sound=b.replace('0x2D7,','0x2D8,'),wrong_volume=b.replace('0x5DC0,','0x5DC1,'),
        wrong_coordinate=b.replace('(actor + 0x28)','(actor + 0x2C)'),
        reversed_range=b.replace('1000, 6000','6000, 1000'),
        late_clear=b.replace('*(u16 *)(actor + 0x4A) = 0;','').replace('1000, 6000);','1000, 6000);\n        *(u16 *)(actor + 0x4A) = 0;'),
        skip_release=b.replace('func_1516972C((struct102 *)actor);',''))
    cached=b.replace('s32 slot;','s32 slot;\n    f32 x, y, z;').replace('func_100111C8(*(u16 *)(actor + 0x4A));','x = *(f32 *)(actor + 0x28); y = *(f32 *)(actor + 0x2C); z = *(f32 *)(actor + 0x30);\n        func_100111C8(*(u16 *)(actor + 0x4A));')
    for name,at in zip('xyz',('28','2C','30')):cached=cached.replace('(s32)*(f32 *)(actor + 0x'+at+')','(s32)'+name)
    rows['cached_coordinates']=cached
    if not native:rows['signed_slot']=b.replace('slot = *(u8 *)','slot = *(s8 *)')
    return rows

def native_harness():
    t=source.HEADERS+r'''
typedef struct {u8 kind,pad[0x27];f32 x,y,z;u8 pad34[0x14],slot,pad49;u16 handle;u8 tail[0x34];} Actor;
Generated1104D0Actor *D_800D99D0[8];
static Actor actor,other,expected_actor;
static Generated1104D0Actor *expected_table[8];
typedef char ABI[(sizeof(void*)==4&&sizeof(Actor)==128&&__builtin_offsetof(Actor,x)==0x28&&__builtin_offsetof(Actor,y)==0x2C&&__builtin_offsetof(Actor,z)==0x30&&__builtin_offsetof(Actor,slot)==0x48&&__builtin_offsetof(Actor,handle)==0x4A&&(s16)65535==-1)?1:-1];
typedef struct {s32 id,args[10];u16 handle;u8 slot;f32 x,y,z;Generated1104D0Actor *entry;} Event;
static Event events[3],expected_events[3];static s32 count,original_slot,sm,am,rm;
static void log_event(s32 id,s32 *args,s32 n){s32 i;Event *e=&events[count++];e->id=id;for(i=0;i<10;i++)e->args[i]=i<n?args[i]:0;e->handle=actor.handle;e->slot=actor.slot;e->x=actor.x;e->y=actor.y;e->z=actor.z;e->entry=D_800D99D0[original_slot];}
void func_100111C8(u16 handle){s32 a=handle;log_event(1,&a,1);if(sm&1)actor.handle=0x2468;if(sm&2){actor.x=123.75f;actor.y=-234.5f;actor.z=32767.75f;}if(sm&4){actor.slot=255;D_800D99D0[original_slot]=(Generated1104D0Actor*)&other;}}
u16 func_10010F88(s32 a,u16 b,s16 c,u8 d,s32 e,s16 f,s16 g,s16 h,s16 i,s16 j){s32 args[10]={a,b,c,d,e,f,g,h,i,j};log_event(2,args,10);if(am&1)actor.handle=0x1357;if(am&2)D_800D99D0[original_slot]=(Generated1104D0Actor*)&actor;if(am&4)actor.x=-99.5f;return 0x4321;}
void func_1516972C(struct102 *value){s32 a=(s32)value;log_event(3,&a,1);if(rm)actor.handle=0xBEEF;}
'''
    for n,b in dict(selected=source.SELECTED,**controls(True)).items():t+=b.replace(source.FUNCTION,'test_'+n)+'\n'
    t+=r'''
static const f32 points[5][3]={{0,-0.0f,0},{1.75f,-1.75f,17.5f},{32767.75f,-32768.75f,65535.75f},{-65536.75f,65536.75f,123.25f},{1073741824.0f,-1073741824.0f,2147483520.0f}};
static void setup(s32 slot,s32 match,u16 handle,s32 point){s32 i;u8 *p=(u8*)&actor;for(i=0;i<128;i++)p[i]=(u8)(i*29+0xA5);actor.slot=(u8)slot;actor.handle=handle;actor.x=points[point][0];actor.y=points[point][1];actor.z=points[point][2];for(i=0;i<8;i++)D_800D99D0[i]=(Generated1104D0Actor*)&other;D_800D99D0[slot]=(Generated1104D0Actor*)(match?&actor:&other);count=0;original_slot=slot;}
static void model(s32 match,u16 handle){if(match)D_800D99D0[original_slot]=0;if(handle){func_100111C8(handle);actor.handle=0;func_10010F88(727,24000,0,0,0,(s16)(s32)actor.x,(s16)(s32)actor.y,(s16)(s32)actor.z,1000,6000);}func_1516972C((struct102*)&actor);}
typedef void(*Fn)(u8*);
static int check(Fn fn){s32 slot,match,h,p,mode,i,j,n;static const u16 handles[]={0,1,0x8000,0xFFFF};
for(slot=0;slot<8;slot++)for(match=0;match<2;match++)for(h=0;h<4;h++)for(p=0;p<5;p++)for(mode=0;mode<8;mode++){
sm=mode;am=mode;rm=mode&1;setup(slot,match,handles[h],p);model(match,handles[h]);expected_actor=actor;n=count;for(i=0;i<8;i++)expected_table[i]=D_800D99D0[i];for(i=0;i<n;i++)expected_events[i]=events[i];
setup(slot,match,handles[h],p);fn((u8*)&actor);if(count!=n)return 1;
for(i=0;i<128;i++)if(((u8*)&actor)[i]!=((u8*)&expected_actor)[i])return 2;
for(i=0;i<8;i++)if(D_800D99D0[i]!=expected_table[i])return 3;
for(i=0;i<n;i++){Event *a=&events[i],*b=&expected_events[i];if(a->id!=b->id||a->handle!=b->handle||a->slot!=b->slot||a->x!=b->x||a->y!=b->y||a->z!=b->z||a->entry!=b->entry)return 4;for(j=0;j<10;j++)if(a->args[j]!=b->args[j])return 5;}
}return 0;}
static int run(void){if(check(test_selected))return 10;
'''
    for i,n in enumerate(controls(True)):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class ActorAudioReleaseTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>50I',cls.rom,source.ROM))
        cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'selected')
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    @classmethod
    def linked(cls,obj,entry,label,s=None):
        defs=oracle.symbols()if s is None else s
        text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs)
        assert not unknown;p=cls.fresh/label
        p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
    def compare(self,c=Case(),images=None,entry=None,s=None,connected=False):
        initial=fixture(c,s);wanted,calls,observations=reference(initial,c,s,connected);pair=[]
        for words in images or(self.truth,self.words,self.raw):
            m=AudioReleaseOracle(words,initial,c,entry=entry,s=s,connected=oracle.helper_code(self.rom)if connected else None).run()
            self.assertEqual((public(m.memory),m.calls,m.observations),(public(wanted),calls,observations),c);pair.append(m)
        for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
        return pair[0]
    def test_01_owner_Make_census_and_prototypes(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw)
        self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),13)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),12)
        self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()))
        self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertFalse(source.NEW_GUARDS);self.assertEqual(len(source.BINDINGS),5)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
        self.assertEqual([4*i for i,w in enumerate(ws)if w==jal],[0x110B0C,0x110C54,0x110C94,0x110DDC,0x110DF4]);self.assertFalse(any(w==source.ENTRY for w in ws))
        for entry,offset,n in oracle.HELPERS:
            at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],entry,n*4);self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+n*4],self.rom[offset:offset+n*4])
        self.assertIn('void func_1516972C(struct102 *arg0)',self.values['conker/src/game_1944C0.c'].decode())
        self.assertIn('u16 func_10010F88(s32',source.DECLARATIONS)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(body_words=50,frame=56,bindings=5,guards=0,neighbors=12,compact_functions=13,Make_commands=3,new_diagnostics=0,original_direct_calls=5,aligned_pointer_uses=0,void_return=True,typed_providers=True)
    def test_02_unsigned_slots_callback_order_and_coordinates(self):
        cases=[Case(slot=slot,matching=match,handle=handle,phase=phase,position=slot%5)for slot,match,handle,phase in itertools.product(range(256),(False,True),(0,0xFFFF),(0,8))]
        cases += [Case(handle=h,position=p,stop_mode=sm,audio_mode=am,release_mode=rm,phase=phase)for h,p,sm,am,rm,phase in itertools.product((0,1,0x8000),range(5),range(8),(0,7),(0,1),(0,8))]
        cases += [Case(alias=a,handle=h,phase=p)for a,h,p in itertools.product((1,2),(0,1),(0,8))]
        seen=set()
        for c in cases:seen.update(self.compare(c).visits)
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+source.BODY,4)))
        self.receipt['guest']=dict(cases=len(cases),visited_words=50,all_unsigned_slot_bytes=True,complete_state_trace_equal=True,live_coordinates_after_callback=True,clear_before_audio=True,overlapping_headers_guest_only=True,finite_signed32_conversion_domain=True,raw_C_direct_exact=True)
    def test_03_original_helpers_and_all_five_caller_windows(self):
        count=0;seen=set()
        for h,valid,voice,kind,post,destructor,phase,mode in itertools.product((0,1,0xFFFF),(False,True),(False,True),(0,1,2,255),(-1,0,2),(False,True),(0,8),(0,7)):
            c=Case(handle=h,stop_valid=valid,voice=voice,kind=kind,post_kind=post,destructor=destructor,phase=phase,stop_mode=mode,audio_mode=mode,release_mode=1,position=h%5)
            seen.update(self.compare(c,connected=True).visits);count+=1
        for entry,_,n in oracle.HELPERS:self.assertTrue(set(range(entry,entry+n*4,4))<=seen)
        windows=0;visited=set()
        for window in range(5):
            for phase,selector,timer,ticks,flag in itertools.product((0,8),(-1,3,4),(-32768,-99,-1,0,3,32767),(0,1,32768,0xFFFFFFFF),(0,1)):
                c=Case(phase=phase,stop_mode=7,audio_mode=7,release_mode=1,post_kind=255,destructor=True);pair=[]
                for words in(self.truth,self.words,self.raw):
                    m,wanted,called=oracle.caller_machine(self.rom,words,c,window,selector,timer,ticks,flag)
                    with self.assertRaises(WindowBoundary):m.run()
                    self.assertEqual((public(m.memory),m.calls,m.observations),(public(wanted[0]),wanted[1],wanted[2]),(window,selector,timer,ticks,flag));pair.append(m);visited.update(m.visits)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(complete(pair[0]),complete(pair[2]));windows+=1
        for entry,n,_ in oracle.WINDOWS:self.assertTrue(set(range(entry,entry+n*4,4))<=visited)
        self.receipt['integration']=dict(helper_cases=count,helper_words=86,caller_cases=windows,caller_windows=5,window_words=38,all_helper_and_window_words=True,raw_o32_homes_and_signed16_wrapper=True,live_post_unlink_type=True,parent_C_still_placeholder=True,full_gameplay_claimed=False)
    def test_04_native32_objects_and_three_optimizations(self):
        p=self.fresh/'native.c';p.write_text(native_harness());logs={}
        for opt in('-O0','-O2','-O3'):
            exe=self.fresh/('native'+opt);r=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            result=subprocess.run([str(exe)],capture_output=True);self.assertEqual(result.returncode,0,(opt,result.stderr));logs[opt]=dict(exit=0,diagnostics=r.stderr)
        self.receipt['native']=dict(optimizations=logs,cases_per_optimization=2560,controls=len(controls(True)),SDK=True,pointers32=True,trapping_UBSan=True,defined_slots_0_to_7=True,float_to_int_in_range=True,signed16_representation_asserted=True,guest_aliases_excluded=True)
    def test_05_direct_and_connected_access_fault_prefixes(self):
        counts={};delay=0
        for connected in(False,True):
            total=0
            for c in(Case(handle=0),Case(matching=False),Case(stop_mode=7,audio_mode=7,post_kind=255,destructor=True),Case(stop_valid=False),Case(alias=1),Case(alias=2)):
                initial=fixture(c);code=oracle.helper_code(self.rom)if connected else None;full=AudioReleaseOracle(self.truth,initial,c,connected=code).run()
                for cut in range(full.all_accesses):
                    pair=[]
                    for words in(self.truth,self.words):
                        m=AudioReleaseOracle(words,initial,c,connected=code);m.cut=cut
                        with self.assertRaises(faults.AccessBoundary):m.run()
                        pair.append(m)
                    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(pair[1].current_pc,pair[1].delay_of,cut));total+=1;delay+=pair[0].delay_of is not None
            counts[str(connected)]=total
        self.receipt['faults']=dict(prefixes=counts,delay_slot_cuts=delay,complete_state_PC_and_trace=True,portable_C_faults_or_FCSR_claimed=False)
    def test_06_direct_padder_bindings_and_three_rebases(self):
        raw,rs=source.payload(self.out/'selected.o');rejects=0
        for at in range(0,len(raw),4):
            bad=bytearray(raw);bad[at+3]^=1
            with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
            rejects+=1
        for at in rs:
            bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
            with self.assertRaises(ValueError):source.checked_payload(raw,bad)
            rejects+=1
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'))
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True)
        self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
        for j,(entry,table,delta)in enumerate(((source.ENTRY,source.TABLE,0),(0x17007FFC,0x80017FFC,0x100000),(0x2500FFFC,0x8001FFFC,0x10000000))):
            s={n:(table if n=='D_800D99D0'else a+delta)for n,a in oracle.symbols().items()}
            paths=(self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_1104D0.c.o',self.out/'selected.o')
            images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for slot,h,match,phase in itertools.product((0,7,128,255),(0,1,0xFFFF),(False,True),(0,8)):
                self.compare(Case(slot=slot,handle=h,matching=match,phase=phase,stop_mode=7,audio_mode=7),images,entry,s);count+=1
        self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,HI_LO_and_JAL_bindings=5,all_three_objects_linked=True,no_guards=True,padded_object_reproduced=True)
    def test_07_effective_compiled_semantic_controls(self):
        evidence={};witnesses=[Case(slot=slot,matching=match,handle=h,stop_mode=mode,audio_mode=mode,release_mode=1)for slot,match,h,mode in itertools.product((3,255),(False,True),(0,1),(0,7))]
        for name,body in controls().items():
            self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag)
            words=self.linked(obj,source.ENTRY,'negative-link-'+name);effective=False
            for c in witnesses:
                initial=fixture(c);m=AudioReleaseOracle(words,initial,c).run();wanted=reference(initial,c)
                if (public(m.memory),m.calls,m.observations)!=(public(wanted[0]),wanted[1],wanted[2]):effective=True;evidence[name]=dict(slot=c.slot,matching=c.matching,handle=c.handle,mode=c.stop_mode);break
            self.assertTrue(effective,name)
        self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True)
    def test_08_strict_entire_image_and_frozen_inputs(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth)
        source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)}
        positions=[20,at,at+source.SIZE,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,source.RELEASE,112),0x2A0D94,0x2B03D4,0x2CF644,0x2E7160,0x30D508]
        for pos in positions:
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),143)
        self.receipt['image']=dict(changed_bytes=143,code_bytes=142,extent_bytes=1,exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v),caller_provider_and_all_other_bodies_unchanged=True)
