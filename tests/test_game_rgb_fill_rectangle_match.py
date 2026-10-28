"""RGB fill: byte homes, authentic helper chain/caller, bounded native C and exact image."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_rgb_fill_rectangle_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_category_frame_fill import fixture as category_fixture,packet as category_packet
ROOT=Path(__file__).resolve().parents[2]
CURSOR=0x50000
MASK=0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    rgb:tuple=(0x12,0xAB,0xEF)
    coords:tuple=(2,0,290,216)
    phase:int=0
    mode:int=0
    alias:bool=False

def fixture(c):
    sp=STACK+c.phase;cursor=sp+4 if c.alias else CURSOR
    m={sp+i:(i*17+0xA5)&255 for i in range(-256,256)}
    m.update({CURSOR+i:(i*13+0x59)&255 for i in range(-16,160)})
    for i,v in enumerate((c.coords[3],*c.rgb)):put(m,sp+16+i*4,v)
    return m,cursor

def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
def packed(rgb):
    r,g,b=(x&255 for x in rgb);v=((r<<8)&0xF800)|((g<<3)&0x7C0)|((b>>2)&0x3E)|1
    return(v<<16)|v

def provider_effect(m,p,sp,mode,first):
    put(m,p,0xAABBCCDD if first else 0x11223344);put(m,p+4,0x12345678 if first else 0x87654321)
    for i in range(4):put(m,sp-32+i*4,0xB5000000+i)
    if first and mode==2:
        put(m,sp+4,0x87654321);put(m,sp+16,0xABCDEF01)
        for i,v in enumerate((0xFF,0x80,7)):m[sp+23+i*4]=v
    return p+(24 if mode==(1 if first else 3)else 8)

def reference(initial,c,cursor,helpers=None):
    m=dict(initial);sp=STACK+c.phase;hs=helpers or(source.COLOR_IMAGE,source.RECTANGLE)
    for i,v in enumerate(c.coords[:3]):put(m,sp+4+i*4,v)
    for p,a,b in((cursor,0xE7000000,0),(cursor+8,0xEF302C0F,4)):put(m,p,a);put(m,p+4,b)
    calls=[(hs[0],(cursor+16,))];p=provider_effect(m,cursor+16,sp,c.mode,True)
    put(m,p,0xF7000000);put(m,p+4,packed(tuple(m[sp+23+i*4]for i in range(3))))
    args=(p+8,read(m,sp+4),read(m,sp+8),read(m,sp+12),read(m,sp+16));put(m,sp-16,args[4]);calls.append((hs[1],args));result=provider_effect(m,p+8,sp,c.mode,False)
    return m,calls,result

class RectangleOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),cursor=CURSOR,entry=source.ENTRY,connected=None,helpers=None,arguments=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=arguments or(cursor,*c.coords[:3]),connected=connected)
        self.c=c;self.helpers=helpers or(source.COLOR_IMAGE,source.RECTANGLE);self.trace=[]
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
    def record_call(self,target):
        if target==self.helpers[0]:count=1
        elif target==self.helpers[1]:count=5
        else:assert target==source.ENTRY,hex(target);count=8
        args=self.arguments(count);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in self.helpers,hex(target)
        value=provider_effect(self.memory,self.r[4],STACK+self.c.phase,self.c.mode,target==self.helpers[0])
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.r[2]=value;self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0x87654321,0x12345678,True

def controls():
    b=source.SELECTED
    return dict(swapped_rgb=b.replace('red, green, blue, 1','blue, green, red, 1'),zero_alpha=b.replace('blue, 1','blue, 0'),missing_low=b.replace('GPACK_RGBA5551(red, green, blue, 1));','0);'),wrong_mode=b.replace('G_ZS_PRIM','G_ZS_PIXEL'),discard_color_cursor=b.replace('commands = func_1501A680(commands);','(void)func_1501A680(commands);'),wrong_bottom=b.replace('right, bottom);','right, bottom + 1);'),discard_result=b.replace('return func_1501A6CC(commands, left, top, right, bottom);','func_1501A6CC(commands, left, top, right, bottom);\n    return commands;'))

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
static Gfx buffer[32],expected[32];static s32 expectedCoords[4];static u32 mode,error,called;
typedef Gfx*(*Handler)(Gfx*,s32,s32,s32,s32,u8,u8,u8);
typedef char ABI[(sizeof(void*)==4&&sizeof(Gfx)==8&&sizeof(s32)==4&&sizeof(u8)==1)?1:-1];
__attribute__((noinline,noclone)) Gfx*func_1501A680(Gfx*p){
 called++;if(p!=buffer+2||called!=1||buffer[0].words.w0!=0xE7000000||buffer[0].words.w1||buffer[1].words.w0!=0xEF302C0F||buffer[1].words.w1!=4)error=1;
 p->words.w0=0xAABBCCDD;p->words.w1=0x12345678;return p+(mode==1?3:1);
}
__attribute__((noinline,noclone)) Gfx*func_1501A6CC(Gfx*p,s32 x,s32 y,s32 r,s32 b){
 s32 a[4]={x,y,r,b};u32 i;called++;if(called!=2||p!=buffer+(mode==1?6:4))error=2;
 for(i=0;i<4;i++)if(a[i]!=expectedCoords[i])error=3;
 p->words.w0=0x11223344;p->words.w1=0x87654321;return p+(mode==2?3:1);
}
'''
    variants=dict(selected=source.SELECTED,**controls())
    for name,body in variants.items():t+=body.replace(source.FUNCTION,name)+'\n'
    t+=r'''
static int check(Handler h){
 const s32 c[5][4]={{2,0,290,216},{-1,-2,0,1},{3,1,293,217},{-2147483647-1,2147483647,-77,1024},{0,0,4096,-1}};
 u32 byte,p,k,i,j,color,r,g,b,at;
 for(byte=0;byte<256;byte++)for(p=0;p<5;p++)for(k=0;k<3;k++){
  mode=k;error=called=0;r=byte;g=(byte*73+p*17)&255;b=(byte*151+p*109)&255;
  for(i=0;i<32;i++)buffer[i].words.w0=buffer[i].words.w1=expected[i].words.w0=expected[i].words.w1=0xA5A5A5A5;
  for(i=0;i<4;i++)expectedCoords[i]=c[p][i];
  expected[0].words.w0=0xE7000000;expected[0].words.w1=0;expected[1].words.w0=0xEF302C0F;expected[1].words.w1=4;
  expected[2].words.w0=0xAABBCCDD;expected[2].words.w1=0x12345678;
  at=mode==1?5:3;color=((r>>3)<<11)|((g>>3)<<6)|((b>>3)<<1)|1;
  expected[at].words.w0=0xF7000000;expected[at].words.w1=(color<<16)|color;
  expected[at+1].words.w0=0x11223344;expected[at+1].words.w1=0x87654321;
  if(h(buffer,c[p][0],c[p][1],c[p][2],c[p][3],(u8)r,(u8)g,(u8)b)!=buffer+at+1+(mode==2?3:1)||error||called!=2)return 1;
  for(i=0;i<32;i++)for(j=0;j<2;j++)if(((u32*)buffer)[i*2+j]!=((u32*)expected)[i*2+j])return 2;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class RGBFillRectangleTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']));cls.helpers={};cls.retained={};old=cls.values['conker/build/conker.us.elf']
        for entry,n in((source.COLOR_IMAGE,19),(source.RECTANGLE,38)):
            cls.helpers[entry]=list(struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0));cls.retained[entry]=list(struct.unpack_from('>%dI'%n,old,source.elf_slot_offset(old,entry,4*n)))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=source.ENTRY,helpers=None):
        initial,cursor=fixture(c);expected,calls,result=reference(initial,c,cursor,helpers);pair=[]
        for words in images or(self.truth,self.words):
            m=RectangleOracle(words,initial,c,cursor,entry,helpers=helpers).run();self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.calls,calls,c);self.assertEqual(m.r[2],result,c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_complete_owner_actual_Make_ABI_and_reference_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFE0);self.assertEqual(self.helpers,self.retained)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),34)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),33);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_13D350.c.o.compact'),34);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
        rom=self.values['conker/conker.us.bin'];ws=struct.unpack('>%dI'%(len(rom)//4),rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[]);self.assertEqual([4*i for i,w in enumerate(ws)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF)],[0x127004,0x13D47C,0x13D698,0x13D908,0x13DB38,0x13F168]);self.assertFalse(any(w==0x08000000|(source.ENTRY>>2&0x3FFFFFF)for w in ws))
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=32,guards=0,bindings=2,neighbors=33,compact_functions=34,Make_commands=5,diagnostics_empty=True,ABI='Gfx*(Gfx*,s32,s32,s32,s32,u8,u8,u8)',direct_callers=6,pointer_literals=0,stack_color_offsets=[23,27,31])
    def test_02_rgb_bytes_argument_words_aliases_and_private_state(self):
        count=0;visits=set();coords=((2,0,290,216),(0x80000000,0x7FFFFFFF,0xFFFFFFFF,0),(3,1,1024,0x80000000))
        for byte,channel,high,p,phase in itertools.product(range(256),range(3),(0,0xABCDEF00),range(3),(0,8)):
            rgb=[17,128,255];rgb[channel]=byte|high;c=Case(tuple(rgb),coords[p],phase);visits.update(self.compare(c).visits);count+=1
        for mode,alias,phase in itertools.product(range(4),(False,True),(0,8)):self.compare(Case(phase=phase,mode=mode,alias=alias));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4)));self.receipt['guest']=dict(cases=count,all_47_words_visited=True,all_three_color_bytes=True,full_stack_word_noise_ignored=True,signed_fullword_coordinates=True,stack_home_aliases_and_post_helper_reloads=True,four_effectful_provider_modes=True,complete_private_state_equal=True)
    def real_chain(self,words,initial,c,cursor,entry=source.ENTRY):
        connected={a+4*i:w for a,body in self.helpers.items()for i,w in enumerate(body)};return RectangleOracle(words,initial,c,cursor,entry,connected).run()
    def test_03_authentic_category_caller_and_real_graphics_helpers(self):
        rom=self.values['conker/conker.us.bin'];caller=list(struct.unpack_from('>42I',rom,0x13DAB0));count=0;visited=set()
        for category,state,phase,page,p in itertools.product((0,27,30,49),(2,3),(0,8),(0,1),range(3)):
            initial=category_fixture(category,state,p,phase);width,height=((292,216),(640,480),(1024,1024))[p];put(initial,0x800BE620,width);put(initial,0x800BE624,height);initial[0x800BE9C0]=page
            for i in range(2):put(initial,0x8002AAE8+4*i,0x80200000+i*0x100000)
            wanted=category_packet(initial);pair=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)}|{a+4*i:w for a,body in self.helpers.items()for i,w in enumerate(body)}
                m=RectangleOracle(caller,initial,Case(phase=phase),CURSOR,0x15110600,connected,arguments=(CURSOR,0x7F800001,0x80000000,0x12345678)).run();pair.append(m);visited.update(m.visits)
            self.assertEqual(complete(pair[0]),complete(pair[1]));m=pair[0];expected=dict(initial)
            if wanted:
                self.assertEqual(m.calls[0],(source.ENTRY,wanted));color=packed(wanted[5:]);pairs=((0xE7000000,0),(0xEF302C0F,4),(0xFF100000|((width-1)&0xFFF),0x80200000+page*0x100000),(0xF7000000,color),(0xF6000000|((width-2)&0x3FF)<<14|(height&0x3FF)<<2,2<<14))
                for i,(a,b)in enumerate(pairs):put(expected,CURSOR+8*i,a);put(expected,CURSOR+8*i+4,b)
                self.assertEqual(m.r[2],CURSOR+40);self.assertEqual([t for t,a in m.calls],[source.ENTRY,source.COLOR_IMAGE,source.RECTANGLE])
            else:self.assertEqual(m.r[2],CURSOR);self.assertFalse(m.calls)
            self.assertEqual(public(m.memory),public(expected));count+=1
        self.receipt['caller_helpers']=dict(cases=count,complete_original_42_word_category_caller=True,original_and_retained_helpers_equal=[19,38],actual_five_command_payload_and_return_verified=True,caller_words_visited=len(set(range(0x15110600,0x151106A8,4))&visited),helper_words_visited=[len(set(range(a,a+4*len(b),4))&visited)for a,b in self.helpers.items()],other_five_callers_static_envelopes_only=True,no_gameplay_claim=True)
    def test_04_native32_typed_calls_and_effective_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=3840,effective_controls=7,trapping_UBSan=True,all_red_bytes_and_varied_green_blue=True,typed_eight_arguments_and_pointer_return=True,helper_cursor_redirect_and_return_verified=True,bounded_helper_contracts=True)
    def test_05_fired_fault_prefixes_and_real_rectangle_boundaries(self):
        cuts=0
        for c in(Case(),Case(mode=1),Case(mode=2),Case(mode=3),Case(alias=True),Case(alias=True,mode=2)):
            initial,cursor=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=RectangleOracle(words,initial,c,cursor);x.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,cut);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        n=0
        for x,y,r,b,page in itertools.product((-2147483648,-1,2,3,500),(-1,0,1,217),(-1,289,290,291,2147483647),(-1,215,216,217),(0,1)):
            c=Case(coords=(x,y,r,b));initial,cursor=fixture(c);put(initial,0x800BE620,292);put(initial,0x800BE624,216);initial[0x800BE9C0]=page
            for i in range(2):put(initial,0x8002AAE8+4*i,0x80200000+i*0x100000)
            pair=[self.real_chain(w,initial,c,cursor)for w in(self.truth,self.words)];self.assertEqual(complete(pair[0]),complete(pair[1]));m=pair[0];l=max(2,x);t=max(0,y);rr=min(290,r);bb=min(216,b);self.assertEqual(read(m.memory,CURSOR+32),0xF6000000|((rr&0x3FF)<<14)|((bb&0x3FF)<<2));self.assertEqual(read(m.memory,CURSOR+36),((l&0x3FF)<<14)|((t&0x3FF)<<2));self.assertEqual(m.r[2],CURSOR+40);n+=1
        self.receipt['faults_boundaries']=dict(fired_prefix_pairs=cuts,real_helper_boundary_cases=n,negative_and_full_signed_coordinates_guest_only=True,guest_fault_semantics_only=True)
    def test_06_actual_padder_raw_controls_and_independent_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'))
        for b,bindings in((raw[:-4],rs),(bytes([raw[0]^1])+raw[1:],rs),(raw,rs|{68:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        links=0;cases=0
        for i,delta in enumerate((0,0x200000,0x10000000)):
            entry=source.ENTRY+delta;hs=(source.COLOR_IMAGE+delta,source.RECTANGLE+delta);symbols={'func_%08X'%a:b for a,b in zip((source.COLOR_IMAGE,source.RECTANGLE),hs)};asm,missing=emit_function(raw,dict(value=0,size=188),rs,source.FUNCTION,symbols);self.assertFalse(missing);p=self.fresh/('rebase-%d.s'%i);p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True);images=[]
            for j,obj_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('link-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for mode in range(4):self.compare(Case(mode=mode),images,entry,hs);cases+=1
        self.receipt['rebases']=dict(GNU_links=links,layouts=3,guest_cases=cases,different_JAL_region=True,two_bindings_preserved=True,raw_negative_controls=3,guards=0)
    def test_07_compiled_post_helper_color_reload_negative(self):
        b=source.SELECTED;bad=b.replace('    gDPPipeSync(commands++);','    volatile u32 cachedColor = ((u32)GPACK_RGBA5551(red, green, blue, 1) << 16) | GPACK_RGBA5551(red, green, blue, 1);\n    gDPPipeSync(commands++);');start=bad.index('    gDPSetFillColor(');end=bad.index(';',start)+1;bad=bad[:start]+'    gDPSetFillColor(commands++, cachedColor);'+bad[end:];obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+bad,'negative-early-colors');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(mode=2);initial,cursor=fixture(c);expected,_,_=reference(initial,c,cursor);m=RectangleOracle(words,initial,c,cursor).run();self.assertNotEqual(public(m.memory),public(expected));self.receipt['negative_order']=dict(actual_compiled_early_color_capture_rejected=True,post_helper_stack_color_reload_observable=True)
    def test_08_strict_full_image_inputs_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(140,139,1,0));self.receipt['strict']=dict(changed_bytes=140,code_bytes=139,metadata_bytes=1,exclusions=0,corruptions=7,wrong_inputs=3,focused_inputs=len(v))
if __name__=='__main__':unittest.main()
