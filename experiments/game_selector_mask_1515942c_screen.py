"""Fingerprint-bound private selector-mask screen; never installs a candidate."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-selector-mask-1515942c-screen'
out.mkdir(parents=True,exist_ok=True)
inputs={'conker/Makefile': '8b2e63494fe95f4ce933206e52319ca57022a2adad29272b89eb3aedc0e856af',
 'conker/asm/185560.s': 'b76d13d79f6afb00f9b58d25f85195dd0a02cf4b7ca743e037e46a1e7eb1db57',
 'conker/build/conker.us.elf': '9a39ab23bb50a837c108fd220f338e990d09e852d09f56726b638b9662525dd6',
 'conker/build/src/game/generated_185560.c.o': 'f7a6449424702367696efa56f8adf3a44be9c7fd9cf4945395368b972bf60142',
 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
 'conker/include/2.0L/PR/PRimage.h': '25bac64b4d176598cedb468b437b8ac7c13c4f255b8573d6aa60058f0b86be1c',
 'conker/include/2.0L/PR/R4300.h': 'bb8a7702ef8dfe94c389f0c411a4f2346c506ea8766e85c332a44486a97b7b44',
 'conker/include/2.0L/PR/abi.h': '9efe7ee3c940ff96d46f936ad95e9cc52b879ee8c4b5c264cb8f42e1cf1ce1bf',
 'conker/include/2.0L/PR/gbi.h': '155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6',
 'conker/include/2.0L/PR/gs2dex.h': 'e9d3519bb328f9ac60b60d119650e1e4d652eaaddcd9db009f9cbd44daecb398',
 'conker/include/2.0L/PR/gt.h': '05e50d177fe2ae42b02bcb384452317029b919f53403a5be1a3d64d47f2e1296',
 'conker/include/2.0L/PR/gu.h': 'bc7761b1d0688b009d82a17776e21782842b652eb5b257088458b9fee8c63cff',
 'conker/include/2.0L/PR/leo.h': 'e8ad69061d2fb4ee2acbd4c48184b6cebb05b0f3e56087d18d92c3061c0b0b47',
 'conker/include/2.0L/PR/leoappli.h': '902916bad5d2056117570acebaa28cf57c46c2a22bb7cdd111d48ccacc249532',
 'conker/include/2.0L/PR/libaudio.h': '53a127fef608e66f7883fc1d76c6eab609c27a127aebc89e89c87757a9ef97b9',
 'conker/include/2.0L/PR/mbi.h': '8a0b32eb3cc7844a38b1b3ed1b160036b203efac0dc3c0275c53354423e40960',
 'conker/include/2.0L/PR/n_libaudio.h': '223f1db0cf93edeb1e1f03af299eb7aeab8c619e78111d2f59dba31280d6a618',
 'conker/include/2.0L/PR/n_libaudio_s_to_n.h': '6cad54fa2252fad7cb476882c819515ccec2d4120c94f6488f052cfdf261fddf',
 'conker/include/2.0L/PR/os.h': 'e0af7328cadb2164b18c61717d916396741cf053d32b96b0dea06f6d664ff7e2',
 'conker/include/2.0L/PR/os_ai.h': '933e7fe35c87702a2137b9c575022e18bd72e6ce11d8a44035a7ffbddf71aeb6',
 'conker/include/2.0L/PR/os_cache.h': 'a9455e20523c6915f26c05d5d399763f1e051c01eac85c10911b7b3a65c0d5c9',
 'conker/include/2.0L/PR/os_cont.h': '8b486936ae60b8a486e87489e77f40f557a0bf59fddf9c1adc5c97aa18388c0b',
 'conker/include/2.0L/PR/os_convert.h': '6d98f19765d055a7857398cc6d7bd7a2ac2e93a4a858f1c27aa22361e4f892f1',
 'conker/include/2.0L/PR/os_debug.h': '260815777abca616a9783db7a57cd94881586c84ef0adcce26516ba50476a523',
 'conker/include/2.0L/PR/os_eeprom.h': 'f1f0f50895c4505c3420674504b7868ff85fe08df42433389deeb407e68c5163',
 'conker/include/2.0L/PR/os_error.h': 'eae3744bf9ee921d089714e81590226b56fca5ca2f0ef866532eb788e829b120',
 'conker/include/2.0L/PR/os_exception.h': '953bf8361f5e756010c45dc5f823c12183838bd723ec691a99a9fcf682e0698c',
 'conker/include/2.0L/PR/os_flash.h': '7206e87e62400994347ff2d84bd5f563894c9c18cdbe34c0c5dd9fb2bcfa758f',
 'conker/include/2.0L/PR/os_gbpak.h': 'c13616c011c214aef601f6249ae12465dcb8a6edfe68df27aaf6d086e09bbc8f',
 'conker/include/2.0L/PR/os_gio.h': 'c0197b2afd220c07028a972ca0d5903af3064d48d8657935e3c57fc9a55f3b92',
 'conker/include/2.0L/PR/os_host.h': '3b990c99a18cba34c3d8a856e3e99691125ec8338df42198fe469ee7bb9f9bcc',
 'conker/include/2.0L/PR/os_internal.h': '0103aa8359ff23c9ef0b248b0721ea9df0c4557271e4146ac264d0d998b7280d',
 'conker/include/2.0L/PR/os_internal_debug.h': '3e4f1baa87602ad77163c15990625e1fd3b9ae6cffcaabb3424dafec6d638bd0',
 'conker/include/2.0L/PR/os_internal_error.h': 'ab7537aef80c392dcf0010bde8078f1b5d1973740bc6d51e1f4df3d757e28356',
 'conker/include/2.0L/PR/os_internal_exception.h': 'b8124a51000cb0608a34c56d0242e0373d845f0bd28b6fb9b95f7dd21cf9ea65',
 'conker/include/2.0L/PR/os_internal_gio.h': '032d50b58fd0f3d8831430a7125cd039efd1f56affdd8cbeb8777ab464ecba15',
 'conker/include/2.0L/PR/os_internal_host.h': '83dda0b09da200ab1be91aeda90c2d0f52b7a282979391e05a9f4feeff1fffd1',
 'conker/include/2.0L/PR/os_internal_reg.h': 'bbfe19f64f9383dfbd4d2ee17d2556ad8e3ae29f0803580637d0df59aa110f39',
 'conker/include/2.0L/PR/os_internal_rsp.h': '77f2c0f58ebe5384970a553cabf850841a679e97dbd049926d13b0cb29f18c58',
 'conker/include/2.0L/PR/os_internal_si.h': '2d88a8388c9211646c446bcd936606b038f80f53c10b9674f48ad6f6dede5acc',
 'conker/include/2.0L/PR/os_internal_thread.h': 'f7700e0bd2c22fb6716d656435b7431c6701cbfd518f2908d13845d11be5ddd9',
 'conker/include/2.0L/PR/os_internal_tlb.h': 'e67bca1ce07a917679abb4094b087ee70bd01399576fe9d7c4e85c82f642ccf8',
 'conker/include/2.0L/PR/os_libc.h': 'fb2f4e113eee01c1953aee8efea3b6eb450ea97e2a5af23ba868ca1059d26b6e',
 'conker/include/2.0L/PR/os_message.h': '241238eea37d71382b7a3c994d5837e4482d77548a4cbdaeb30b9f67013cdfb7',
 'conker/include/2.0L/PR/os_motor.h': '68103a1c114bc7e7c6decf847a5ec3c346e23e9de9c7488ca6bbedc39dae8ec4',
 'conker/include/2.0L/PR/os_pfs.h': '6b14a950c344f7396bc1e58c9b6612f061053bd41b868dba32e13d904a3effd7',
 'conker/include/2.0L/PR/os_pi.h': '3e29b28b596036ffbe86afa8bcec1126511b78fe862297c48061f97d42b747ea',
 'conker/include/2.0L/PR/os_rdp.h': 'a85b9def6f64bf25e6aeb064e1f2626f7b2d4d0ef0821d21844a9eefb19f6e21',
 'conker/include/2.0L/PR/os_reg.h': '2a14f15494cf3754f1fe0149a8c8cab4806e843f3be6a30ad0c726443edef52d',
 'conker/include/2.0L/PR/os_rsp.h': 'ede13674c9af25912778dd077c3dd709929d43fcb9f135f6465553d0f9e8fa26',
 'conker/include/2.0L/PR/os_si.h': 'ffd228b5b0e450efcf1756d778d701be958cce724d1912792c31b3cac26f74b9',
 'conker/include/2.0L/PR/os_system.h': 'bc8afaa3362ff4851feee1feed818dd009a13c3de19435a2e09656a64bf531d8',
 'conker/include/2.0L/PR/os_thread.h': 'b7c244ead94962a0ebcb0787a589e7b398eaf02d8fc6538698c7353b08dcbf7d',
 'conker/include/2.0L/PR/os_time.h': '21bd983fa7b11daa6a06c053b5e9cd7c08420dd20657c4fd61be434389af3342',
 'conker/include/2.0L/PR/os_tlb.h': '9bbb49127e7e2600f6dcceffe4a1d38f31d463327cfa384ce930ddfa63223893',
 'conker/include/2.0L/PR/os_version.h': '66c2147d22b8ccf5b2eb4967c90b27dfb8c83ce07e08382fcd408c8ca0bc3873',
 'conker/include/2.0L/PR/os_vi.h': 'f59a0d52ab0e2bc2ca0b8226bc9b9c1e58d3a9eb8df8c4e6d45aaa6ac51fb2b6',
 'conker/include/2.0L/PR/os_voice.h': 'c0fb2f6f8eb68a6608a2401f6a2f4a38d1c65b5d1ae944d0b5999502a9cc432f',
 'conker/include/2.0L/PR/ramrom.h': 'fa009dd8676f0af0ed0f0339dfe6ac2f67ad1a1b8675bdff42f71b937608a370',
 'conker/include/2.0L/PR/rcp.h': '61e531c5c93e7b71c167ac1d3d08254f67e5009408defa4fe5b941674c5a6b8e',
 'conker/include/2.0L/PR/rdb.h': 'ce4b388d5bf24b869eaee1919fd81a0655006b2327a6f521d954cfc0e546dfeb',
 'conker/include/2.0L/PR/region.h': 'd1f523d36ab27f28eea0ffa0d87875661c14844d12c9bf0142932aa38af5869f',
 'conker/include/2.0L/PR/rmon.h': 'b646e7e7febea89d9bfed1c1b58ebbe40a7d5378ccb50a1063cc1de5e8d3d07a',
 'conker/include/2.0L/PR/sched.h': '40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572',
 'conker/include/2.0L/PR/sp.h': '6d4dd33330efa090dcf438a5a05b82a8fa54e94db78bc7c8f4d32f16a638de18',
 'conker/include/2.0L/PR/sptask.h': '12b0a593a7013076fb60cf7224f0bdf25da554076e8b6f2ffe3999769e737dc5',
 'conker/include/2.0L/PR/ucode.h': '50201220d2f811d64e5e11611ec835f0c3bf1a79c3045a2dc40f7e46012765a4',
 'conker/include/2.0L/PR/ucode_debug.h': '715bccc464d8dbaa1a421007b6bab49a303bf5d8eb75ed74c184dddf59e67661',
 'conker/include/2.0L/PR/ultraerror.h': '979fbca1aee61876a524ff3825cfb9c6a18ef28c99eb100e8b9b751b5c266b86',
 'conker/include/2.0L/PR/ultralog.h': '52564b52560297920881f56e81894cfd9d9ed22b4cba1f9298eb1e10b1cda449',
 'conker/include/2.0L/PR/ultratypes.h': '1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd',
 'conker/include/2.0L/PR/uportals.h': '76548ed2614bedba9c9236883ab236251a30995b12f96da1e7a8eee8cb1eca4e',
 'conker/include/2.0L/assert.h': '99d2e0c96e7453fae576f879b64ac1bd9ea5c031541c041ee6111bdacbefb844',
 'conker/include/2.0L/ultra64.h': '334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d',
 'conker/include/asm_processor_prelude.inc': 'c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d',
 'conker/include/functions.h': 'ecfe651a780f5d9471f9483dc4d62cdea930ecf8d366a417765a79642c3eb610',
 'conker/include/libc/math.h': 'e13f7c37cc5ea7cf75a93c4b45c6b96f321d67a70e8cdbfbba0edb7de0c3e226',
 'conker/include/libc/stdarg.h': '759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4',
 'conker/include/libc/stddef.h': 'e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721',
 'conker/include/libc/stdio.h': '060f3f7b91cde2ab969d3d04b40ed57ff2b61167ece52309b64f4c6ab9ebfae1',
 'conker/include/libc/stdlib.h': '181e9dc382377ed777654ddbf8393f9244ac9dcee66f58e78b43d0dea53ebbe9',
 'conker/include/libc/string.h': 'ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5',
 'conker/include/macro.inc': 'd7366200752da1051aba7bf98e361ca4af662fb5e22c7107455fc06a34969f1e',
 'conker/include/macros.h': 'dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769',
 'conker/include/magic.h': '92d976e6596839e490234cb4f827f3d1156a1d535c3022c7152162ed11d08eea',
 'conker/include/structs.h': '0103b809787d88d65a2262cf619aaf537bb85cea25bd2aca5c312f2db28eafde',
 'conker/include/variables.h': '3cd24cd9fea98901536137649368536fbbd56018cac571b6476701802c1bc00c',
 'conker/retail_layout.us.txt': '2e354c2be1de84126bb0d15b716a1af2eb21aea8e5befe669c7c03c1731a3365',
 'conker/retail_word_patches.us.csv': 'b90976a082ffe653b7fff3637256b879b5743ba64eb0f267ee6465313190bcc0',
 'conker/src/game/generated_185560.c': '3ddbc1f32bccf022018ba686e67489ed6847f8748560e07a70155ffcaa88d9c3',
 'ido/ido5.3_recomp/cc': 'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a'}
for name,want in inputs.items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=want:raise ValueError('screen input changed: '+name)
old='s32 func_1515942C() {\n    return 0;\n}'
early='s32 func_1514ECE0(void *, s16, void **);\n/* Test whether the linked selector record fits five allowed masks. */\ns32 func_1515942C(u8 *actor, s16 first, s16 second, s16 third, s16 fourth, s16 fifth) {\n    u8 matched = 0;\n    u8 *node, *data;\n    u32 m0, m1, m2, m3, m4, wanted, actual;\n    if (func_1514ECE0(*(void **)(actor + 0x2F4), 0x13, (void **)&node)) {\n        data = *(u8 **)(node + 0x10);\n        m3 = fourth == -1 ? 0x1E00 : 1U << ((fourth + 9) & 31);\n        m2 = third == -1 ? 0x1C0 : 1U << ((third + 6) & 31);\n        m1 = second == -1 ? 0x38 : 1U << ((second + 3) & 31);\n        m0 = first == -1 ? 0x07 : 1U << (first & 31);\n        m4 = fifth == -1 ? 0x3E000 : 1U << ((fifth + 13) & 31);\n        actual = (1U << (data[0x2C] & 31)) | (1U << ((data[0x2D] + 3) & 31)) |\n                 (1U << ((data[0x2E] + 6) & 31)) | (1U << ((data[0x2F] + 9) & 31)) |\n                 (1U << ((data[0x30] + 13) & 31));\n        wanted = m4 | m0 | m1 | m2 | m3;\n        if ((wanted | actual) == wanted) matched = 1;\n    }\n    return matched;\n}'
selected='s32 func_1514ECE0(void *, s16, void **);\n/* Test whether the linked selector record fits five allowed masks. */\ns32 func_1515942C(u8 *actor, s16 first, s16 second, s16 third, s16 fourth, s16 fifth) {\n    u8 *data;\n    u8 *node;\n    u8 matched = 0;\n    u32 m0, m1, m2, m3, m4, wanted, actual;\n    if (func_1514ECE0(*(void **)(actor + 0x2F4), 0x13, (void **)&node)) {\n        data = *(u8 **)(node + 0x10);\n        m3 = fourth == -1 ? 0x1E00 : 1U << ((fourth + 9) & 31);\n        m2 = third == -1 ? 0x1C0 : 1U << ((third + 6) & 31);\n        m1 = second == -1 ? 0x38 : 1U << ((second + 3) & 31);\n        m0 = first == -1 ? 0x07 : 1U << (first & 31);\n        m4 = fifth == -1 ? 0x3E000 : 1U << ((fifth + 13) & 31);\n        actual = 1U << ((data[0x2D] + 3) & 31);\n        actual |= 1U << (data[0x2C] & 31);\n        actual |= 1U << ((data[0x2E] + 6) & 31);\n        actual |= 1U << ((data[0x2F] + 9) & 31);\n        actual |= 1U << ((data[0x30] + 13) & 31);\n        wanted = m4 | m0 | m1 | m2 | m3;\n        if ((wanted | actual) == wanted) matched = 1;\n    }\n    return matched;\n}'
owner=(root/'conker/src/game/generated_185560.c').read_text();assert owner.count(old)==1
base,bd=compile_owner(root,out,owner,'baseline');early_obj,ed=compile_owner(root,out,owner.replace(old,early),'early');new,nd=compile_owner(root,out,owner.replace(old,selected),'selected')
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};truth=struct.unpack_from('>90I',(root/'conker/conker.us.bin').read_bytes(),0x1868dc)
for obj,diag,label,length,exact in ((early_obj,ed,'early',98,16),(new,nd,'selected',95,18)):
 words=bound_blob(*payload(obj,'func_1515942C'),symbols)
 assert len(words)==length and sum(a==b for a,b in zip(words,truth))==exact and words[0]==0x27bdffc0
 assert same_functions(base,obj,('func_1515942C',))==36 and normalized_pools(base)==normalized_pools(obj)
 assert bd.replace('baseline.c','owner.c')==diag.replace(label+'.c','owner.c')
env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
for label,obj,diffs in (('early',early_obj,2048),('selected',new,0)):
 e=dict(env,SELECTOR_CANDIDATE=str(obj),SELECTOR_EXPECTED_TRACE_DIFFS=str(diffs))
 subprocess.run([sys.executable,'-m','tools.tests.game_selector_mask_1515942c_behavior'],cwd=root,env=e,check=True)
e=dict(env,SELECTOR_CANDIDATE=str(new),SELECTOR_EXPECTED_TRACE_DIFFS='0')
for name in ('connected','caller','controls','stack_alias','native'):
 subprocess.run([sys.executable,'-m','tools.tests.game_selector_mask_1515942c_'+name],cwd=root,env=e,check=True)
print('selector mask screen passed; candidate remains private and uncredited',flush=True)
