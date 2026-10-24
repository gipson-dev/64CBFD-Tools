"""Pending-record loop, helper mutation contracts and exact build boundaries."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_pending_record_drain as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
PENDING,DEST,SCRATCH=0x800DDA90,0x800DD478,0x8003809C
PROCESS,FREE=0x10006240,0x10004074
SYMBOLS=dict(D_800DDA90=PENDING,D_800DD478=DEST,D_8003809C=SCRATCH,func_10006240=PROCESS,func_10004074=FREE)

@dataclass(frozen=True)
class Case:
    pattern:int=1
    index:int=0
    mode:int=0
    phase:int=0
    alias:int=0


def fixture(c,s=SYMBOLS):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-256,128)}
    for base,size in((s['D_800DDA90'],240),(s['D_800DD478'],1560),(s['D_8003809C'],4)):
        m.update({base+i:(i*29+0x5A)&255 for i in range(size)})
    for i in range(15):
        active=(False,True,True,i%2==0,i==c.index,i!=c.index)[c.pattern]
        ready=(False,True,False,i%3!=0,True,i%3==0)[c.pattern]
        put(m,s['D_800DDA90']+16*i+8,0x200000+32*i if active else 0)
        put(m,s['D_800DD478']+104*i,0x300000+64*i if ready else 0)
    put(m,s['D_8003809C'],0x807FE000)
    if c.alias==1:
        for i in range(15):put(m,s['D_800DD478']+104*i,s['D_800DDA90']+16*i+8)
    if c.alias==2:
        for i in range(15):put(m,s['D_800DD478']+104*i,s['D_800DDA90']+16*((i+1)%15)+8)
    return m


def effect(memory,target,args,count,c,s,current):
    pending=s['D_800DDA90'];scratch=s['D_8003809C']
    if target==s['func_10006240']:
        if c.mode==1:put(memory,pending+16*current+8,0x400000+count*32)
        elif c.mode==2 and current<14:put(memory,pending+16*(current+1)+8,0)
        elif c.mode==3:put(memory,scratch,0x803FE000+count*4)
        elif c.mode==4 and current<14:put(memory,s['D_800DD478']+104*(current+1),0)
        elif c.mode==5:put(memory,args[1],0x500000+count*32)
    elif c.mode==6:
        # A free callback can change the field; the caller must still clear it.
        put(memory,pending+16*current+8,0x600000+count*32)


def helper(memory,target,args,count,c,s,current):
    effect(memory,target,args,count,c,s,current)
    home=STACK+c.phase-48
    for i in range(4):put(memory,home+i*4,0xB5000000+i)


def reference(initial,c,s=SYMBOLS):
    m=dict(initial);calls=[];counts={s['func_10006240']:0,s['func_10004074']:0}
    for i in range(15):
        ptr=s['D_800DDA90']+16*i+8;pending=read(m,ptr)
        if not pending:continue
        dest=read(m,s['D_800DD478']+104*i)
        if dest:
            for target,args in((s['func_10006240'],(pending,dest,read(m,s['D_8003809C']))),):
                calls.append((target,args));counts[target]+=1;helper(m,target,args,counts[target],c,s,i)
            target=s['func_10004074'];args=(read(m,ptr),)
            calls.append((target,args));counts[target]+=1;helper(m,target,args,counts[target],c,s,i)
        put(m,ptr,0)
    return m,calls


def public(m):return {a:b for a,b in m.items()if not STACK-256<=a<STACK+128}


class DrainOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),s=SYMBOLS,entry=source.ENTRY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(0x12345678,),connected=connected)
        self.case,self.names=c,s
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def record_call(self,target):
        if target==source.ENTRY:
            self.calls.append((target,()));self.events.append(('CALL',target,()));return
        self.assert_target(target)
        args=self.arguments(3 if target==self.names['func_10006240']else 1)
        self.calls.append((target,args));self.events.append(('CALL',target,args));self.counts[target]+=1
    def assert_target(self,target):
        assert target in(self.names['func_10006240'],self.names['func_10004074']),hex(target)
    def hook(self,target):
        self.assert_target(target);args=self.calls[-1][1]
        current=(self.r[16]-self.names['D_800DDA90'])//16
        helper(self.memory,target,args,self.counts[target],self.case,self.names,current)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.r[2]=0x87654321
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x76543210,0x89ABCDEF


def controls():
    b=source.SELECTED
    return dict(short_loop=b.replace('index != 15','index != 14'),stride=b.replace('index * 26','index * 25'),
        skipped_clear=b.replace('            record->pending = NULL;',''),
        skipped_free=b.replace('                func_10004074(record->pending);',''),
        wrong_free=b.replace('func_10004074(record->pending)','func_10004074(destination)'),
        wrong_scratch=b.replace('destination, D_8003809C','destination, D_8003809C + 4'),
        cached_scratch=b.replace('    s32 index;','    s32 index;\n    u32 savedScratch;').replace(
            '    record =','    savedScratch = D_8003809C;\n    record =').replace('destination, D_8003809C','destination, savedScratch'),
        cached_pending=b.replace('    void *destination;','    void *destination, *saved;').replace(
            '                func_10006240(record->pending,','                saved = record->pending;\n                func_10006240(record->pending,').replace('func_10004074(record->pending)','func_10004074(saved)'),
        cleared_before_free=b.replace('                func_10004074(record->pending);','                record->pending = NULL;\n                func_10004074(record->pending);'))


class PendingRecordDrainTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.truth=list(struct.unpack_from('>44I',cls.values['conker/conker.us.bin'],source.ROM))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.raw=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
    def compare(self,c=Case(),images=None,s=SYMBOLS,entry=source.ENTRY):
        initial=fixture(c,s);expected,calls=reference(initial,c,s);models=[]
        for words in images or(self.truth,self.words):
            m=DrainOracle(words,initial,c,s,entry);saved=tuple(m.r[16:24])+tuple(m.r[28:32]);m.run()
            self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.calls,calls,c)
            self.assertEqual(tuple(m.r[16:24])+tuple(m.r[28:32]),saved);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]
    def test_01_full_owner_caller_and_actual_Make(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.normalized(*source.payload(self.out/'after-owner.o',source.FUNCTION)),source.payload(source.original(ROOT,self.out),source.FUNCTION))
        q=json.loads((self.out/'qualification.json').read_text());mk=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['new_guards'],q['preserved_neighbors'],q['caller_functions_identical']),(44,48,3,13,16))
        self.assertEqual([(x['commands'],x['compact_functions_equal'])for x in mk],[(3,14),(3,16)])
        self.assertTrue(all(x['complete_padded_object_equal']for x in mk))
        caller=self.values[source.CALLER].decode();updated=source.recovered_caller(caller)
        self.assertEqual(updated.replace('void func_1517CFC4(void);','s32 func_1517CFC4(void);'),caller)
        self.assertIn('            func_1517CFC4();\n            func_1501C880(0, 1);',caller)
        self.receipt['owner']=dict(words=44,frame=48,bindings=8,guards=3,neighbors=13,caller_functions_identical=16,Make_commands=[3,3])
    def test_02_guest_loops_helpers_reloads_and_aliases(self):
        count=0;visits=set()
        cases=[Case(pattern,index,mode,phase,alias)for pattern,index,mode,phase,alias in itertools.product(
            range(6),range(15),range(7),(0,8),range(3))]
        for c in cases:
            m=self.compare(c);visits.update(m.visits)
            raw=DrainOracle(self.raw,fixture(c),c).run();self.assertEqual(complete(raw),complete(m));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+176,4)))
        self.receipt['guest']=dict(cases=count,all_15_positions=True,helper_mutation_modes=7,alias_layouts=3,
            raw_C_complete_state_equal=True,all_44_words_visited=True,helpers_are_contracts_not_full_implementations=True)
    def test_03_guards_bindings_and_real_padder_controls(self):
        raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        for index in range(44):
            bad=bytearray(raw);bad[index*4+3]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
        for at in rs:
            bad=dict(rs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalized(raw,bad)
        old=self.values['conker/retail_word_patches.us.csv']
        with self.assertRaises(ValueError):source.guard_bytes(old+b'\n',raw,rs)
        with self.assertRaises(ValueError):source.guard_bytes(old,raw[:-4],rs)
        from tools.pad_generated_object import emit_padded_assembly
        text=(self.out/'qualified-guards.csv').read_text()
        for label,a,b in(('word','0x26100000','0x26100001'),('binding','R_MIPS_LO16:D_800DDA90','R_MIPS_LO16:wrong')):
            rows=text.rsplit('\n',4);tail='\n'.join(rows[1:]);self.assertIn(a,tail)
            path=self.out/('negative-'+label+'.csv');path.write_text(rows[0]+'\n'+tail.replace(a,b,1))
            with self.assertRaises((ValueError,RuntimeError)):
                emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
        self.receipt['guards']=dict(raw_words_rejected=44,binding_controls=8,extent_controls=1,history_controls=1,real_padder_controls=2)
    def test_04_fault_prefixes_and_no_eager_destination_load(self):
        count=0
        for c in(Case(0),Case(1,0,1),Case(2),Case(3),Case(4,14,6,8),Case(1,0,5,0,2)):
            initial=fixture(c);m=self.compare(c)
            for fault in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=DrainOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        initial=fixture(Case(0));initial={a:b for a,b in initial.items()if not DEST<=a<DEST+1560}
        for words in(self.truth,self.words):DrainOracle(words,initial,Case(0)).run()
        c=Case(4,14);initial=fixture(c);del initial[SCRATCH]
        for words in(self.truth,self.words):
            with self.assertRaisesRegex(AssertionError,'unmapped read'):DrainOracle(words,initial,c).run()
        bad=list(self.words);bad[29]=0
        c=Case(4,14,1);good=self.compare(c);broken=DrainOracle(bad,fixture(c),c).run()
        self.assertNotEqual(broken.calls,good.calls)
        self.receipt['faults']=dict(prefix_pairs=count,empty_does_not_read_destinations=True,missing_scratch_faults=True,
            skipped_reload_negative_effective=True,emitted_guest_order_only=True)
    def test_05_independent_GNU_rebases(self):
        fitted,bindings=source.normalized(*source.payload(self.out/'after-owner.o',source.FUNCTION))
        asm,missing=emit_function(fitted,dict(value=0,size=176),bindings,source.FUNCTION,SYMBOLS)
        self.assertFalse(missing);p=self.out/'independent-fitted.s';p.write_text(asm);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
        links=0
        for i,(entry,s)in enumerate(((source.ENTRY,SYMBOLS),(source.ENTRY+0x200000,dict(zip(SYMBOLS,(0x80107FF0,0x80127FF8,0x80148000,0x10206240,0x10204074)))),
                (source.ENTRY+0x500000,dict(zip(SYMBOLS,(0x80218010,0x80238000,0x80257FFC,0x10506240,0x10504074)))),
                (source.ENTRY+0x700000,dict(SYMBOLS,D_8003809C=STACK-48)),
                (source.ENTRY+0x900000,dict(SYMBOLS,D_800DD478=PENDING+8)))):
            images=[]
            for j,object_ in enumerate((source.original(ROOT,self.out),obj)):
                p=self.out/('rebase-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%(n,v)for n,v in s.items()],'-o',str(elf),str(object_)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>44I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for pattern in range(6):self.compare(Case(pattern,14,1),images,s,entry)
        self.receipt['links']=dict(independent_GNU_links=links,layouts=5,all_8_bindings=True,HI_LO_carry_boundaries=True,
            scratch_helper_home_alias=True,overlapping_pending_destination_tables=True)
    def test_06_native32_actual_C_and_effective_controls(self):
        variants=dict(selected=source.SELECTED,**controls())
        declarations=source.DECLARATIONS.replace('extern s32 D_800DDA90;','').replace('extern s32 D_800DD478;','').replace('extern u32 D_8003809C;','')
        text=source.HEADERS+declarations+'''
static union {s32 opaque;PendingRecord1A89B0 records[15];} pending;
static union {s32 opaque;void *cells[390];} destinationStorage;
#define D_800DDA90 pending.opaque
#define D_800DD478 destinationStorage.opaque
u32 D_8003809C;
typedef char ABI[(sizeof(void*)==4&&sizeof(PendingRecord1A89B0)==16&&__builtin_offsetof(PendingRecord1A89B0,pending)==8)?1:-1];
static u32 expected[90],observed[90],expectedCount,observedCount,currentIndex,mutationMode;
static void logword(u32 v){if(observedCount<90)observed[observedCount++]=v;}
s32 func_10006240(void *p,void *d,u32 s){
 logword(1);logword((u32)p);logword((u32)d);logword(s);
 if(mutationMode==1)pending.records[currentIndex].pending=(void*)(0x400000+32*currentIndex);
 if(mutationMode==2)D_8003809C=0x803FE000+4*currentIndex;
 return (s32)0x87654321u;
}
void func_10004074(void *p){logword(2);logword((u32)p);currentIndex++;}
'''
        for name,b in variants.items():text+=b.replace(source.FUNCTION,name)+'\n'
        text+='''
typedef void(*Drain)(void);
static int variant(Drain fn){
 u32 pattern,index,mode,i,n,p,d,s,k;u8 beforePending[240],beforeDest[1560];
 for(pattern=0;pattern<5;pattern++)for(index=0;index<15;index++)for(mode=0;mode<3;mode++){
  for(i=0;i<sizeof(pending);i++)((u8*)&pending)[i]=(u8)(i*29+0x5A);
  for(i=0;i<sizeof(destinationStorage);i++)((u8*)&destinationStorage)[i]=(u8)(i*13+0xA5);
  for(i=0;i<15;i++){
   pending.records[i].pending=(void*)((pattern==0||(pattern!=4&&i!=index))?0:0x200000+32*i);
   destinationStorage.cells[i*26]=(void*)(pattern==2?0:0x300000+64*i);
  }
  for(i=0;i<240;i++)beforePending[i]=((u8*)&pending)[i];
  for(i=0;i<1560;i++)beforeDest[i]=((u8*)&destinationStorage)[i];
  D_8003809C=0x807FE000;mutationMode=mode;currentIndex=pattern==4?0:index;
  observedCount=expectedCount=0;s=D_8003809C;
  for(k=0;k<15;k++)if(pattern&&pattern!=2&&(pattern==4||k==index)){
   p=0x200000+32*k;d=0x300000+64*k;
   expected[expectedCount++]=1;expected[expectedCount++]=p;expected[expectedCount++]=d;expected[expectedCount++]=s;
   expected[expectedCount++]=2;expected[expectedCount++]=mode==1?0x400000+32*k:p;
   if(mode==2)s=0x803FE000+4*k;
  }
  fn();
  if(observedCount!=expectedCount||D_8003809C!=s)return 23;
  for(n=0;n<expectedCount;n++)if(observed[n]!=expected[n])return 23;
  for(i=0;i<240;i++){
   k=i/16;n=i%16;
   if(pattern&&(pattern==4||k==index)&&n>=8&&n<12){if(((u8*)&pending)[i])return 23;}
   else if(((u8*)&pending)[i]!=beforePending[i])return 23;
  }
  for(i=0;i<1560;i++)if(((u8*)&destinationStorage)[i]!=beforeDest[i])return 23;
 }
 return 0;
}
int run(void){
'''
        for i,name in enumerate(variants):text+='if(variant(%s)!=%d)return %d;\n'%(name,0 if name=='selected'else 23,10+i)
        text+='return 0;}\n'+START
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(binary)],timeout=60).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=225,effective_controls=len(variants)-1,
            trap_UBSan=True,actual_semantic_C=True,private_backing_unions=True,shared_headers_unchanged=True)
    def test_07_strict_full_image_and_frozen_inputs(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+176]
        pred=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        report=json.loads((self.out/'first-link.json').read_text());self.assertEqual(report['changed_bytes'],136)
        symbol=next(at for at,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,176),symbol+8,source.elf_slot_offset(pred,0x1501878C,4)):
            bad=bytearray(pred);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        installed=(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE];source.check_inputs(ROOT,self.out,installed)
        self.receipt['strict']=dict(changed_bytes=136,code_bytes=135,metadata_bytes=1,exclusions=0,corruptions=5,focused_inputs=len(self.values))

    def test_08_original_caller_boundary_and_compiled_reload_negative(self):
        rom=self.values['conker/conker.us.bin'];call=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        direct=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==call]
        literal=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
        self.assertEqual(direct,[0x46184]);self.assertEqual(literal,[])
        entry=0x15018CD4;window=list(struct.unpack_from('>5I',rom,direct[0]))
        self.assertEqual(window,[call,0,0x00002025,0x0D407220,0x24050001])
        class Boundary(Exception):pass
        class Caller(DrainOracle):
            def record_call(self_,target):
                if target==0x1501C880:
                    args=self_.arguments(2);self_.calls.append((target,args));self_.events.append(('CALL',target,args))
                    if args!=(0,1):raise AssertionError(args)
                    raise Boundary
                super().record_call(target)
        count=0
        for pattern,mode,phase in itertools.product(range(6),range(7),(0,8)):
            c=Case(pattern,14,mode,phase);initial=fixture(c);pair=[]
            for words in(self.truth,self.words):
                m=Caller(window,initial,c,entry=entry,connected={source.ENTRY+4*i:w for i,w in enumerate(words)})
                with self.assertRaises(Boundary):m.run()
                expected,calls=reference(initial,c)
                self.assertEqual(m.calls,[(source.ENTRY,()),*calls,(0x1501C880,(0,1))])
                self.assertEqual(public(m.memory),public(expected));pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+source.DECLARATIONS+controls()['cached_pending'],'negative-cached-pending')
        self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);info=fs[source.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        c=Case(4,14,1);m=DrainOracle(words,fixture(c),c).run()
        self.assertNotEqual(m.calls,reference(fixture(c),c)[1])
        self.receipt['caller']=dict(cases=count,original_words=5,direct_sites=direct,literal_sites=literal,
            ignored_return_and_next_arguments_checked=True,compiled_MIPS_cached_pending_negative_effective=True,
            whole_parent_gameplay_acceptance_claimed=False)

if __name__=='__main__':unittest.main()
