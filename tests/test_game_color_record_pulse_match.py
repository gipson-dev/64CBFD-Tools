"""Color record pulse: canonical callback ABI, ordered guest/native effects and whole image."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_color_record_pulse_match as source
from tools.tests import game_color_record_pulse_oracle as oracle
from tools.tests.game_color_record_pulse_oracle import Case,fixture,reference,public,PulseOracle,WindowCode,WindowBoundary,RECORD,OTHER,NEXT,COUNT,SLOTS,STACK,put,read,faults
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ROOT=Path(__file__).resolve().parents[2]

def controls():
    b=source.SELECTED
    return dict(zero_lifetime_expires=b.replace('if (remaining != 0)','if (remaining >= 0)'),strict_expiry=b.replace('if (remaining <= 0)','if (remaining < 0)'),skip_negative_lifetime=b.replace('if (remaining != 0)','if (remaining > 0)'),eager_expiry_store=b.replace('        if (remaining <= 0)','        record->value = remaining;\n        if (remaining <= 0)'),wrong_mode=b.replace('(s32 *)2','(s32 *)3'),wrong_flag=b.replace('record->callback == 0','record->callback == 1'),cached_clock=b.replace('    s32 step;','    s32 step;\n    s32 captured = D_800BE9E4;').replace('(u32)D_800BE9E4 * 2U','(u32)captured * 2U'),half_step=b.replace('* 2U','* 1U'),inclusive_low=b.replace('shade < 0x90','shade <= 0x90'),strict_high=b.replace('shade >= 0x100','shade > 0x100'),binary_state=b.replace('record->state == 0','record->state != 1'),wrong_output=b.replace('record->red = shade','record->green = shade'))

def native_harness():
    t=source.HEADERS+'#include "structs.h"\n'+source.DECLARATIONS[source.DECLARATIONS.index('typedef struct'):source.DECLARATIONS.index('extern s32')]+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(struct115)==52&&sizeof(Type5AColorRecord)==32&&__builtin_offsetof(Type5AColorRecord,value)==16&&__builtin_offsetof(Type5AColorRecord,red)==21&&__builtin_offsetof(Type5AColorRecord,state)==24&&__builtin_offsetof(Type5AColorRecord,callback)==25)?1:-1];
typedef struct{u32 left[4];Type5AColorRecord record;s32 tickCell;u32 right[4];}Storage;
static Storage actual,expected;
static s32 clockValue,*clockPointer;static u32 mutation,modeCalls,freeCalls,modeValue;
#define D_800BE9E4 (*clockPointer)
void func_10011FA0(s32 *p){modeCalls++;modeValue=(u32)p;if(mutation&1){actual.record.red=255;actual.record.state=3;}if(mutation&2)*clockPointer=-1;}
void func_1516972C(struct102*p){freeCalls++;((u8*)p)[31]^=0xA5;}
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+'\n'
    t+=r'''
typedef void(*Update)(struct102*);
static int check(Update fn){u32 n,pattern,layout,i,wantMode,wantFree,wantValue;u8*p=(u8*)&actual,*q=(u8*)&expected;s32 ticks,remaining,shade,step;struct115 descriptor;
 static u32 lives[8]={0,1,0xFFFFFFFFu,0x80000000u,0x7FFFFFFFu,2,100,0x40000000u};static u32 clocks[8]={0,1,0xFFFFFFFFu,0x80000000u,0x7FFFFFFFu,0x40000000u,56,128};
 descriptor.unk0=fn;
 for(n=0;n<65540;n++)for(pattern=0;pattern<4;pattern++)for(layout=0;layout<3;layout++){
  for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n*3+pattern);
  actual.record.value=lives[(n>>8)&7];actual.record.red=(u8)n;actual.record.state=(u8)(n>>8);actual.record.callback=(u8)(n>>4);mutation=pattern;clockValue=actual.tickCell=(s32)clocks[(n>>3)&7];
  if(n>=65536){actual.record.value=0;actual.record.red=n==65536?146:n==65537?254:n==65538?145:255;actual.record.state=n==65536||n==65538?0:1;actual.record.callback=1;clockValue=actual.tickCell=1;}
  clockPointer=layout==0?&clockValue:layout==1?(s32*)&actual.record.value:&actual.tickCell;
  for(i=0;i<sizeof(actual);i++)q[i]=p[i];ticks=layout==0?clockValue:layout==1?(s32)expected.record.value:expected.tickCell;remaining=(s32)expected.record.value;wantFree=0;wantMode=0;wantValue=0xFEEDFACEu;
  if(remaining){remaining=(s32)((u32)remaining-(u32)ticks);if(remaining<=0){wantFree=1;((u8*)&expected.record)[31]^=0xA5;}else expected.record.value=(u32)remaining;}
  if(!wantFree){
   if(expected.record.callback==0){wantMode=1;wantValue=2;if(mutation&1){expected.record.red=255;expected.record.state=3;}if(mutation&2){ticks=-1;if(layout==1)expected.record.value=0xFFFFFFFFu;else if(layout==2)expected.tickCell=-1;}}
   if(layout==1)ticks=(s32)expected.record.value;else if(layout==2)ticks=expected.tickCell;
   step=(s32)((u32)ticks*2u);shade=expected.record.red;
   if(expected.record.state==0){shade=(s32)((u32)shade-(u32)step);if(shade<144){shade=144;expected.record.state=1;}}
   else{shade=(s32)((u32)shade+(u32)step);if(shade>=256){shade=255;expected.record.state=0;}}
   expected.record.red=(u8)shade;
  }
  modeCalls=freeCalls=0;modeValue=0xFEEDFACEu;descriptor.unk0((struct102*)&actual.record);
  if(modeCalls!=wantMode||freeCalls!=wantFree||modeValue!=wantValue)return 1;for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 1;
 }return 0;}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class ColorRecordPulseTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=source.ENTRY,ticks=None,free=source.FREE,mode=source.MODE):
        initial,clock=fixture(c,ticks);want,calls=reference(initial,c,clock);calls=[(free if t==source.FREE else mode,a)for t,a in calls];pair=[]
        for words in images or(self.truth,self.words):
            m=PulseOracle(words,initial,c,entry,free=free,mode=mode);m.clock=clock;m.run();self.assertEqual((public(m.memory),m.calls),(public(want),calls),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def link_object(self,obj,entry,ticks,free,mode,label):
        p=self.fresh/(label+'.ld');elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_800BE9E4=0x%X'%ticks,'--defsym=func_1516972C=0x%X'%free,'--defsym=func_10011FA0=0x%X'%mode,'-o',str(elf),str(obj)],capture_output=True,check=True)
        raw=sections(elf)['.text'][1];return list(struct.unpack('>%dI'%(len(raw)//4),raw))
    def linked(self,entry,ticks,free,mode):
        if not hasattr(self,'links'):self.links={}
        key=(entry,ticks,free,mode)
        if key in self.links:return self.links[key]
        pair=[self.link_object(obj,entry,ticks,free,mode,'layout-%d-%d'%(len(self.links),j))[:48]for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o'))];self.assertEqual(*pair);self.links[key]=pair;return pair
    def test_01_owner_Make_registration_and_canonical_ABI(self):
        self.assertEqual(self.words,self.truth);source.checked_payload(*source.payload(self.out/'selected.o'))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),23)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),22);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_1D0840.c.o.compact'),23)
        proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),proposed);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),1)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(ws)if w==source.ENTRY],[0x2311B0]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual(source.REGISTRY+0x5A*0x34,0x8008C6F0)
        self.assertIn('void (*unk0)(struct102 *arg0);',self.values['conker/include/structs.h'].decode());self.assertIn('void func_151A5070(struct102 *object)',source.SELECTED);self.assertIn('func_15167A68(0x5A, 0,',proposed)
        self.assertIn('void func_10011FA0(s32 *arg0)',self.values['conker/src/init_11FA0.c'].decode());self.assertIn('D_80042770 = arg0;',self.values['conker/src/init_11FA0.c'].decode());self.assertIn('void func_1516972C(struct102 *);',source.DECLARATIONS)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=48,frame=24,bindings=6,guards=0,neighbors=22,compact_functions=23,GLOBAL_ASM_routines=1,Make_commands=5,diagnostics=0,registered_type=90,descriptor_stride=52,canonical_void_struct102_callback=True,existing_Init_pointer_mode_API_preserved=True)
    def test_02_guest_lifetime_pulse_helper_mutations_and_aliases(self):
        count=0;visits=set()
        for life,ticks,red,state in itertools.product((0,1,2,100,0xFFFFFFFF,0x80000000,0x7FFFFFFF),(0,1,2,56,0xFFFFFFFF,0x80000000,0x7FFFFFFF,0x40000000),(0,143,144,145,146,254,255),(0,1,255)):
            m=self.compare(Case(life,ticks,red,state));visits.update(m.visits);count+=1
        for red,state,callback in itertools.product(range(256),(0,1,128,255),(0,1,255)):
            m=self.compare(Case(lifetime=0,red=red,state=state,callback=callback));visits.update(m.visits);count+=1
        for mutation,redirect,life in itertools.product(range(8),(False,True),(0,1,100)):
            m=self.compare(Case(lifetime=life,callback=0,mutation=mutation,redirect=redirect,phase=(mutation&1)*8));visits.update(m.visits);count+=1
        for off,life,callback,mutation in itertools.product(range(0,32,4),(0,1,100),(0,1),(0,3)):
            images=self.linked(source.ENTRY,RECORD+off,source.FREE,source.MODE);self.compare(Case(lifetime=life,clock_alias=off,callback=callback,mutation=mutation),images);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4))-{source.ENTRY+60})
        self.receipt['guest']=dict(cases=count,visited_words=47,unreachable_lifetime_store_retained=True,all_red_bytes_and_nonbinary_state=True,helper_mutations_and_volatile_clobbers=True,incoming_home_redirect=True,wrapped_signed_countdown_and_clamps=True,eight_aligned_clock_aliases=True,full_private_state_and_trace=True,ABI_home_and_overlapping_byte_clock_probes_guest_only=True)
    def test_03_actual_dispatch_window_Init_and_release_helpers(self):
        before=self.values['conker/build/conker.us.elf'];helpers={};sizes={source.FREE:112,source.SCAN:80,source.ADAPTER:32,source.MODE:16}
        for entry,size in sizes.items():
            rom_at=entry-(0x10000000 if entry==source.MODE else 0x14FD2B50);raw=self.rom[rom_at:rom_at+size];self.assertEqual(before[source.elf_slot_offset(before,entry,size):source.elf_slot_offset(before,entry,size)+size],raw);helpers.update({entry+4*i:w for i,w in enumerate(struct.unpack('>%dI'%(size//4),raw))})
        va=0x15167158;parent=list(struct.unpack_from('>11I',self.rom,va-0x14FD2B50));count=0
        for callback,life,ticks,state in itertools.product((0,1,255),(-1,0,1,100),(0,1,10),(0,1,255)):
            c=Case(callback=callback,lifetime=life,ticks=ticks,state=state);initial,clock=fixture(c);put(initial,COUNT,1,1);put(initial,SLOTS,RECORD);put(initial,SLOTS+4,0xDEADBEEF);put(initial,source.REGISTRY+90*52,source.ENTRY);put(initial,0x8008B4D0+90*52,0);want,calls=reference(initial,c,clock);put(want,SLOTS+4,NEXT);expected=[(source.ENTRY,(RECORD,))]
            for t,a in calls:
                expected.append((t,a))
                if t==source.FREE:expected.extend([(source.SCAN,a),(source.ADAPTER,a),(source.UNLINK,(a[0],1))]);put(want,SLOTS,read(want,a[0]+8))
            pair=[]
            for words in(self.truth,self.words):
                connected={**helpers,**{source.ENTRY+4*i:w for i,w in enumerate(words)}};m=PulseOracle(parent,initial,c,va,connected);m.r[16]=RECORD;m.r[18]=source.REGISTRY+90*52;m.r[19]=COUNT;m.r[20]=SLOTS;m.window_end=va+44;m.code=WindowCode(dict(m.code),m);m.clock=clock
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((public(m.memory),m.calls),(public(want),expected),c);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);count+=1
        self.assertIn('s32 func_151670C0() {\n    return 0;\n}',self.values['conker/src/game_1944C0.c'].decode());self.receipt['caller']=dict(original_dispatch_words=11,connected_cases=count,retained_helper_words=[28,20,8,4],retained_helpers_equal_current_ELF=True,queued_next_before_call_and_release_scan=True,actual_Init_stores_mode_without_dereference=True,current_dispatcher_stub_unchanged=True,bounded_final_unlink_provider_no_full_parent_or_gameplay_claim=True)
    def test_04_native32_canonical_callback_and_effective_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=65540*4*3,effective_controls=len(controls()),trapping_UBSan=True,valid_typed_storage_and_canonical_struct115_callback=True,whole_storage_fences=True,disjoint_or_corresponding_signed_value_or_s32_tick_cell=True,guest_incoming_home_and_byte_overlaps_separate=True)
    def test_05_fired_access_prefixes_lazy_expiry_and_mode(self):
        cuts=0
        for callback,life,mutation,redirect in itertools.product((0,255),(0,1,100),(0,3),(False,True)):
            c=Case(callback=callback,lifetime=life,mutation=mutation,redirect=redirect);initial,_=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=PulseOracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        for words in(self.truth,self.words):
            c=Case(lifetime=0,callback=1);initial,_=fixture(c);m=PulseOracle(words,initial,c).run();self.assertEqual(sum(e[0]=='R'and e[1]==source.TICKS for e in m.trace),1);self.assertFalse(m.calls);self.assertFalse(any(e[0]=='W'and e[1]>=STACK for e in m.trace))
            c=Case(lifetime=1,callback=0);initial,_=fixture(c)
            for off in(0x15,0x18,0x19):del initial[RECORD+off]
            m=PulseOracle(words,initial,c).run();self.assertEqual(m.calls,[(source.FREE,(RECORD,))]);self.assertFalse(any(e[0]=='W'and e[1]==RECORD+0x10 for e in m.trace))
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,zero_lifetime_reads_clock_once=True,nonzero_flag_needs_no_incoming_home_store=True,expiry_needs_no_color_flag_mapping_and_no_result_store=True)
    def test_06_real_padder_raw_controls_and_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{**rs,80:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        for entry,ticks,free,mode in((source.ENTRY,source.TICKS,source.FREE,source.MODE),(0x17007FFC,0x800B7FFC,0x17012340,0x17022340),(0x2500FFFC,0x800C8004,0x25123400,0x25223400)):
            images=self.linked(entry,ticks,free,mode)
            for callback,life,state in itertools.product((0,255),(0,1,100),(0,1)):
                self.compare(Case(callback=callback,lifetime=life,state=state),images,entry,ticks,free,mode);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,four_HI_LO_and_two_J26_bindings=True,signed_low_half_carry=True,GNU_original_and_compiler_objects=True,raw_binding_controls=3,guards=0)
    def test_07_actually_compiled_semantic_controls_fail_by_value(self):
        samples={'cached_clock':Case(lifetime=0,callback=0,mutation=2),'inclusive_low':Case(lifetime=0,red=146,ticks=1),'strict_high':Case(lifetime=0,red=254,state=1,ticks=1),'strict_expiry':Case(lifetime=1,ticks=1)}
        for name,c in samples.items():
            body=controls()[name];obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.link_object(obj,source.ENTRY,source.TICKS,source.FREE,source.MODE,'negative-'+name);initial,clock=fixture(c);want,calls=reference(initial,c,clock);m=PulseOracle(words,initial,c).run();self.assertNotEqual((public(m.memory),m.calls),(public(want),calls),name)
        self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=len(samples),wrong_live_clock_low_clamp_high_clamp_expiry=True,value_failure_not_unmapped_read=True)
    def test_08_strict_entire_image_extent_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        count=sum(x!=y for x,y in zip(before,expected));q=json.loads((self.out/'preparation.json').read_text());self.assertEqual(count,q['changed_bytes']);self.receipt['image']=dict(changed_bytes=count,code_bytes=q['code_bytes'],size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guard_manifest_shared_headers_helpers_and_current_dispatcher_unchanged=True)
