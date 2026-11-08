"""Record plane callback: typed C and closed callback-setup scheduling."""
import csv,hashlib,io,json,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-record-plane-callback-151319C4-match'
SOURCE='conker/src/game/generated_15D730.c'
OBJECT='conker/build/src/game/generated_15D730.c.o'
OWNER='generated_15D730'
FUNCTION='func_151319C4'
ENTRY=353573316
ROM=1437300
WORDS=78
FRAME=64
ELF='conker/build/conker.us.elf'
GUARDS='conker/retail_word_patches.us.csv'
BEFORE_SHA='9a71b3f84b94c16f0f4d2985292e944dc46cbf102b1ce9c4119442ca3ec24712'
GUARD_SHA='c6df151d01ea4238ab959fea60f128e34533c8ad715b8686b6abe98bc9143179'
STUB='s32 func_151319C4() {\n    return 0;\n}'
OWNER_FUNCTIONS=31
METADATA_GROUPS=()
ISOLATED_HEADER='#include <ultra64.h>\n#include "structs.h"\n\ntypedef struct {\n    u8 reserved[0x3C];\n    f32 extent;\n    f32 position[3];\n    u8 reserved4C[0xC];\n    f32 velocity[3];\n    f32 verticalAcceleration;\n    u32 flags;\n} BounceRecord15D730;\n\ntypedef struct {\n    u8 flags;\n    s8 kind;\n    u8 reserved[2];\n    f32 damping;\n} BounceResponse15D730;\n\ntypedef struct HeightResult71820 {\n    f32 height;\n    s16 vertices[9];\n    s16 pad16;\n    u32 metadata;\n    u8 flags;\n    u8 state;\n    u16 pad1E;\n    s32 value;\n} HeightResult71820;\nextern f32 D_800A3844;\ns32 func_1514672C(struct17 *);\ns32 func_15046C80(f32 *, u16, f32, HeightResult71820 *);\nextern s32 (*D_80089874[])(BounceRecord15D730 *, void *, f32 *, BounceResponse15D730 *);\n'
BINDINGS={44: [('R_MIPS_HI16', 'D_80089874')], 60: [('R_MIPS_LO16', 'D_80089874')], 132: [('R_MIPS_26', 'func_1514672C')], 156: [('R_MIPS_HI16', 'D_800A3844')], 160: [('R_MIPS_LO16', 'D_800A3844')], 200: [('R_MIPS_26', 'func_15046C80')], 240: [('R_MIPS_HI16', 'D_80089874')], 272: [('R_MIPS_LO16', 'D_80089874')]}
RAW_SHA='742a850fc7258921e26896504b66064cedf427e6717dba1e1b5036d70b6e4469'
SELECTED='/* Probe the response plane and dispatch its live collision callback. */\ns32 func_151319C4(BounceRecord15D730 *record, void *surface, BounceResponse15D730 *response) {\n    u8 result = 1;\n    f32 point[3];\n    f32 contact[3];\n\n    if (response->flags & 1) {\n        if (response->kind != -1 && D_80089874[response->kind] != NULL &&\n            record->position[1] < ((f32 *)surface)[1]) {\n            point[0] = record->position[0];\n            point[1] = ((f32 *)surface)[1];\n            point[2] = record->position[2];\n            if (!func_1514672C((struct17 *)point)) {\n                return 0;\n            }\n            if (func_15046C80(point, 0,\n                             record->position[1] - record->extent * D_800A3844,\n                             (HeightResult71820 *)((u8 *)record + 0x80))) {\n                contact[0] = point[0];\n                contact[2] = point[2];\n                contact[1] = ((HeightResult71820 *)((u8 *)record + 0x80))->height;\n                result = D_80089874[response->kind](record, surface, contact, response);\n            }\n        }\n    }\n    return result;\n}'
REGISTER_INPUTS=((2734817278, 0, 999415, 0, 0, 32752), (2734801918, 0, 331216, 0, 0, 32752))
FROZEN={'conker/src/game/generated_15D730.c': 'ee8401b62fbfa561bc05e45114efc937297775c4c6cc020ac1fc29e969553e60', 'conker/build/src/game/generated_15D730.c.o': '67b7fc5aa47f2222175c8272ba3e0320fc356cc8066bfe1b6e00823b7e5008c4', 'conker/asm/15D730.s': '8fb9c9a1f9f8670726ba0ac21a52478813ca25903b7432146ec952d7b5062657', 'conker/build/conker.us.elf': '9a71b3f84b94c16f0f4d2985292e944dc46cbf102b1ce9c4119442ca3ec24712', 'conker/retail_word_patches.us.csv': 'c6df151d01ea4238ab959fea60f128e34533c8ad715b8686b6abe98bc9143179', 'conker/Makefile': '8e676e04318f8645e6b277ed60ed9f221d8901a5e6a02efd279d478d46a615f8', 'conker/progress.csv': '7658d1ff6c2e3ae94567606200fcae0b7d08f5752a9ec0484108dc8056c8bdc0', 'conker/retail_layout.us.txt': 'eb8145837da425d7a55080459d22f11e21e1ac69e8b9d8ad5100ed5750d814f1', 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382', 'conker/include/structs.h': 'e97e1a98ebcc522d82b52215078780102e0dd5e47d614bb3a4d4f3bbc94b9653', 'conker/include/variables.h': '02650aa4bf9fd66156f4e2cbd1e49156b9655eed68c3fae1cab15b1f99063a7d', 'conker/include/functions.h': 'f01a41af0bdb2caaaeb2c198be68d91515efb39de98a34ba190e090503d5f10b', 'conker/build/conker.ld': '6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5', 'conker/symbol_addrs.us.txt': '1e59d193c5aefcc13d14b5083ee80ee977a4a9dcf54b75db8595b192a223bafa', 'conker/undefined_syms.us.txt': 'd678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e', 'conker/undefined_funcs.us.txt': '92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a', 'conker/undefined_syms_auto.txt': 'a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd', 'conker/undefined_funcs_auto.txt': 'e2090d98c3a5450afc4a78aafd1a7f1f5114bd43c7bddecb6e79434f20955329', 'conker/include/asm_processor_prelude.inc': 'c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d', 'conker/include/macro.inc': 'd7366200752da1051aba7bf98e361ca4af662fb5e22c7107455fc06a34969f1e', 'conker/conker.us.yaml': 'd31a14128e74793a2cc5fcb7ca3a65abefc7cafe01528268b0e0af76f94bff1f', 'conker/asm/data/2482B0.rodata.s': '202e51f573918fd45ccfc822369f57642e96f9c4d51fc7e8c8e2a72199b3b662', 'conker/asm/data/22E220.rodata.s': 'a6726700c15ce0ede735ac2cf240510daa6317bac16391c4680cebec4595ddec', 'conker/src/game_16EE20.c': 'c4f99269b6081edd3315823178e7fe015597175d71874f36c7bc745b07a1e9c0', 'conker/asm/nonmatchings/game_16EE20/func_1514672C.s': '3f0ad394038dd40ab6c4dbc996d4a0ce2c6417a17ffc2f28ef6193d1b618e6a9', 'conker/src/game/generated_71820.c': '1654f635094ebfe1cf465dd69945a4b747d422ec5e090881a8ba44e6da876fe4', 'conker/asm/71820.s': 'dad3e6265a0b9d616da5b73bb78f2484995251e8ad6a5d8788fd5251fd078585', 'conker/asm/nonmatchings/generated_15D730/func_15130280.s': '16b035eba19d6a6da8908bbd030c22d05d16350b9ef626094402bcb668b5765d', 'conker/asm/nonmatchings/generated_15D730/func_15131D9C.s': 'beb657462ed933dc01e783d74a3840dc493244aa0448582047c855853fa5bc03', 'conker/include/macros.h': 'dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769', 'conker/include/magic.h': '92d976e6596839e490234cb4f827f3d1156a1d535c3022c7152162ed11d08eea', 'conker/include/2.0L/assert.h': '99d2e0c96e7453fae576f879b64ac1bd9ea5c031541c041ee6111bdacbefb844', 'conker/include/2.0L/ultra64.h': '334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d', 'conker/include/libc/math.h': 'e13f7c37cc5ea7cf75a93c4b45c6b96f321d67a70e8cdbfbba0edb7de0c3e226', 'conker/include/libc/stdarg.h': '759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4', 'conker/include/libc/stddef.h': 'e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721', 'conker/include/libc/stdio.h': '060f3f7b91cde2ab969d3d04b40ed57ff2b61167ece52309b64f4c6ab9ebfae1', 'conker/include/libc/stdlib.h': '181e9dc382377ed777654ddbf8393f9244ac9dcee66f58e78b43d0dea53ebbe9', 'conker/include/libc/string.h': 'ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5', 'conker/include/2.0L/PR/abi.h': '9efe7ee3c940ff96d46f936ad95e9cc52b879ee8c4b5c264cb8f42e1cf1ce1bf', 'conker/include/2.0L/PR/gbi.h': '155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6', 'conker/include/2.0L/PR/gs2dex.h': 'e9d3519bb328f9ac60b60d119650e1e4d652eaaddcd9db009f9cbd44daecb398', 'conker/include/2.0L/PR/gt.h': '05e50d177fe2ae42b02bcb384452317029b919f53403a5be1a3d64d47f2e1296', 'conker/include/2.0L/PR/gu.h': 'bc7761b1d0688b009d82a17776e21782842b652eb5b257088458b9fee8c63cff', 'conker/include/2.0L/PR/leo.h': 'e8ad69061d2fb4ee2acbd4c48184b6cebb05b0f3e56087d18d92c3061c0b0b47', 'conker/include/2.0L/PR/leoappli.h': '902916bad5d2056117570acebaa28cf57c46c2a22bb7cdd111d48ccacc249532', 'conker/include/2.0L/PR/libaudio.h': '53a127fef608e66f7883fc1d76c6eab609c27a127aebc89e89c87757a9ef97b9', 'conker/include/2.0L/PR/mbi.h': '8a0b32eb3cc7844a38b1b3ed1b160036b203efac0dc3c0275c53354423e40960', 'conker/include/2.0L/PR/n_libaudio.h': '223f1db0cf93edeb1e1f03af299eb7aeab8c619e78111d2f59dba31280d6a618', 'conker/include/2.0L/PR/n_libaudio_s_to_n.h': '6cad54fa2252fad7cb476882c819515ccec2d4120c94f6488f052cfdf261fddf', 'conker/include/2.0L/PR/os.h': 'e0af7328cadb2164b18c61717d916396741cf053d32b96b0dea06f6d664ff7e2', 'conker/include/2.0L/PR/os_ai.h': '933e7fe35c87702a2137b9c575022e18bd72e6ce11d8a44035a7ffbddf71aeb6', 'conker/include/2.0L/PR/os_cache.h': 'a9455e20523c6915f26c05d5d399763f1e051c01eac85c10911b7b3a65c0d5c9', 'conker/include/2.0L/PR/os_cont.h': '8b486936ae60b8a486e87489e77f40f557a0bf59fddf9c1adc5c97aa18388c0b', 'conker/include/2.0L/PR/os_convert.h': '6d98f19765d055a7857398cc6d7bd7a2ac2e93a4a858f1c27aa22361e4f892f1', 'conker/include/2.0L/PR/os_debug.h': '260815777abca616a9783db7a57cd94881586c84ef0adcce26516ba50476a523', 'conker/include/2.0L/PR/os_eeprom.h': 'f1f0f50895c4505c3420674504b7868ff85fe08df42433389deeb407e68c5163', 'conker/include/2.0L/PR/os_error.h': 'eae3744bf9ee921d089714e81590226b56fca5ca2f0ef866532eb788e829b120', 'conker/include/2.0L/PR/os_exception.h': '953bf8361f5e756010c45dc5f823c12183838bd723ec691a99a9fcf682e0698c', 'conker/include/2.0L/PR/os_flash.h': '7206e87e62400994347ff2d84bd5f563894c9c18cdbe34c0c5dd9fb2bcfa758f', 'conker/include/2.0L/PR/os_gbpak.h': 'c13616c011c214aef601f6249ae12465dcb8a6edfe68df27aaf6d086e09bbc8f', 'conker/include/2.0L/PR/os_gio.h': 'c0197b2afd220c07028a972ca0d5903af3064d48d8657935e3c57fc9a55f3b92', 'conker/include/2.0L/PR/os_host.h': '3b990c99a18cba34c3d8a856e3e99691125ec8338df42198fe469ee7bb9f9bcc', 'conker/include/2.0L/PR/os_internal.h': '0103aa8359ff23c9ef0b248b0721ea9df0c4557271e4146ac264d0d998b7280d', 'conker/include/2.0L/PR/os_internal_debug.h': '3e4f1baa87602ad77163c15990625e1fd3b9ae6cffcaabb3424dafec6d638bd0', 'conker/include/2.0L/PR/os_internal_error.h': 'ab7537aef80c392dcf0010bde8078f1b5d1973740bc6d51e1f4df3d757e28356', 'conker/include/2.0L/PR/os_internal_exception.h': 'b8124a51000cb0608a34c56d0242e0373d845f0bd28b6fb9b95f7dd21cf9ea65', 'conker/include/2.0L/PR/os_internal_gio.h': '032d50b58fd0f3d8831430a7125cd039efd1f56affdd8cbeb8777ab464ecba15', 'conker/include/2.0L/PR/os_internal_host.h': '83dda0b09da200ab1be91aeda90c2d0f52b7a282979391e05a9f4feeff1fffd1', 'conker/include/2.0L/PR/os_internal_reg.h': 'bbfe19f64f9383dfbd4d2ee17d2556ad8e3ae29f0803580637d0df59aa110f39', 'conker/include/2.0L/PR/os_internal_rsp.h': '77f2c0f58ebe5384970a553cabf850841a679e97dbd049926d13b0cb29f18c58', 'conker/include/2.0L/PR/os_internal_si.h': '2d88a8388c9211646c446bcd936606b038f80f53c10b9674f48ad6f6dede5acc', 'conker/include/2.0L/PR/os_internal_thread.h': 'f7700e0bd2c22fb6716d656435b7431c6701cbfd518f2908d13845d11be5ddd9', 'conker/include/2.0L/PR/os_internal_tlb.h': 'e67bca1ce07a917679abb4094b087ee70bd01399576fe9d7c4e85c82f642ccf8', 'conker/include/2.0L/PR/os_libc.h': 'fb2f4e113eee01c1953aee8efea3b6eb450ea97e2a5af23ba868ca1059d26b6e', 'conker/include/2.0L/PR/os_message.h': '241238eea37d71382b7a3c994d5837e4482d77548a4cbdaeb30b9f67013cdfb7', 'conker/include/2.0L/PR/os_motor.h': '68103a1c114bc7e7c6decf847a5ec3c346e23e9de9c7488ca6bbedc39dae8ec4', 'conker/include/2.0L/PR/os_pfs.h': '6b14a950c344f7396bc1e58c9b6612f061053bd41b868dba32e13d904a3effd7', 'conker/include/2.0L/PR/os_pi.h': '3e29b28b596036ffbe86afa8bcec1126511b78fe862297c48061f97d42b747ea', 'conker/include/2.0L/PR/os_rdp.h': 'a85b9def6f64bf25e6aeb064e1f2626f7b2d4d0ef0821d21844a9eefb19f6e21', 'conker/include/2.0L/PR/os_reg.h': '2a14f15494cf3754f1fe0149a8c8cab4806e843f3be6a30ad0c726443edef52d', 'conker/include/2.0L/PR/os_rsp.h': 'ede13674c9af25912778dd077c3dd709929d43fcb9f135f6465553d0f9e8fa26', 'conker/include/2.0L/PR/os_si.h': 'ffd228b5b0e450efcf1756d778d701be958cce724d1912792c31b3cac26f74b9', 'conker/include/2.0L/PR/os_system.h': 'bc8afaa3362ff4851feee1feed818dd009a13c3de19435a2e09656a64bf531d8', 'conker/include/2.0L/PR/os_thread.h': 'b7c244ead94962a0ebcb0787a589e7b398eaf02d8fc6538698c7353b08dcbf7d', 'conker/include/2.0L/PR/os_time.h': '21bd983fa7b11daa6a06c053b5e9cd7c08420dd20657c4fd61be434389af3342', 'conker/include/2.0L/PR/os_tlb.h': '9bbb49127e7e2600f6dcceffe4a1d38f31d463327cfa384ce930ddfa63223893', 'conker/include/2.0L/PR/os_version.h': '66c2147d22b8ccf5b2eb4967c90b27dfb8c83ce07e08382fcd408c8ca0bc3873', 'conker/include/2.0L/PR/os_vi.h': 'f59a0d52ab0e2bc2ca0b8226bc9b9c1e58d3a9eb8df8c4e6d45aaa6ac51fb2b6', 'conker/include/2.0L/PR/os_voice.h': 'c0fb2f6f8eb68a6608a2401f6a2f4a38d1c65b5d1ae944d0b5999502a9cc432f', 'conker/include/2.0L/PR/PRimage.h': '25bac64b4d176598cedb468b437b8ac7c13c4f255b8573d6aa60058f0b86be1c', 'conker/include/2.0L/PR/R4300.h': 'bb8a7702ef8dfe94c389f0c411a4f2346c506ea8766e85c332a44486a97b7b44', 'conker/include/2.0L/PR/ramrom.h': 'fa009dd8676f0af0ed0f0339dfe6ac2f67ad1a1b8675bdff42f71b937608a370', 'conker/include/2.0L/PR/rcp.h': '61e531c5c93e7b71c167ac1d3d08254f67e5009408defa4fe5b941674c5a6b8e', 'conker/include/2.0L/PR/rdb.h': 'ce4b388d5bf24b869eaee1919fd81a0655006b2327a6f521d954cfc0e546dfeb', 'conker/include/2.0L/PR/region.h': 'd1f523d36ab27f28eea0ffa0d87875661c14844d12c9bf0142932aa38af5869f', 'conker/include/2.0L/PR/rmon.h': 'b646e7e7febea89d9bfed1c1b58ebbe40a7d5378ccb50a1063cc1de5e8d3d07a', 'conker/include/2.0L/PR/sched.h': '40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572', 'conker/include/2.0L/PR/sp.h': '6d4dd33330efa090dcf438a5a05b82a8fa54e94db78bc7c8f4d32f16a638de18', 'conker/include/2.0L/PR/sptask.h': '12b0a593a7013076fb60cf7224f0bdf25da554076e8b6f2ffe3999769e737dc5', 'conker/include/2.0L/PR/ucode.h': '50201220d2f811d64e5e11611ec835f0c3bf1a79c3045a2dc40f7e46012765a4', 'conker/include/2.0L/PR/ucode_debug.h': '715bccc464d8dbaa1a421007b6bab49a303bf5d8eb75ed74c184dddf59e67661', 'conker/include/2.0L/PR/ultraerror.h': '979fbca1aee61876a524ff3825cfb9c6a18ef28c99eb100e8b9b751b5c266b86', 'conker/include/2.0L/PR/ultralog.h': '52564b52560297920881f56e81894cfd9d9ed22b4cba1f9298eb1e10b1cda449', 'conker/include/2.0L/PR/ultratypes.h': '1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd', 'conker/include/2.0L/PR/uportals.h': '76548ed2614bedba9c9236883ab236251a30995b12f96da1e7a8eee8cb1eca4e', 'ido/ido5.3_recomp/cc': 'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a', 'ido/ido5.3_recomp/cfe': 'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9', 'ido/ido5.3_recomp/uopt': '23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d', 'ido/ido5.3_recomp/ugen': 'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d', 'conker/assets/249F40.bin': 'b67eaeec5b5f460dea1daa4fb55f017e351c6d41d03477f6654a4afd4db08910'}
sha=lambda b:hashlib.sha256(b).hexdigest()

PROTOTYPE='s32 func_151319C4(BounceRecord15D730 *, void *, BounceResponse15D730 *);'
OLD_PROTO='s32 func_151319C4();'
RECORD_TYPE='typedef struct {\n    u8 reserved[0x3C];\n    f32 extent;\n    f32 position[3];\n    u8 reserved4C[0xC];\n    f32 velocity[3];\n    f32 verticalAcceleration;\n    u32 flags;\n} BounceRecord15D730;'
RESPONSE_TYPE='typedef struct {\n    u8 flags;\n    s8 kind;\n    u8 reserved[2];\n    f32 damping;\n} BounceResponse15D730;'
DECLARATIONS='#include "structs.h"\n\ntypedef struct {\n    u8 reserved[0x3C];\n    f32 extent;\n    f32 position[3];\n    u8 reserved4C[0xC];\n    f32 velocity[3];\n    f32 verticalAcceleration;\n    u32 flags;\n} BounceRecord15D730;\n\ntypedef struct {\n    u8 flags;\n    s8 kind;\n    u8 reserved[2];\n    f32 damping;\n} BounceResponse15D730;\n\ntypedef struct HeightResult71820 {\n    f32 height;\n    s16 vertices[9];\n    s16 pad16;\n    u32 metadata;\n    u8 flags;\n    u8 state;\n    u16 pad1E;\n    s32 value;\n} HeightResult71820;\nextern f32 D_800A3844;\ns32 func_1514672C(struct17 *);\ns32 func_15046C80(f32 *, u16, f32, HeightResult71820 *);\nextern s32 (*D_80089874[])(BounceRecord15D730 *, void *, f32 *, BounceResponse15D730 *);\n'
CALLS=[('    func_151319C4(arg0, arg1, arg0 + '+off+');','    func_151319C4((BounceRecord15D730 *)arg0, (void *)arg1, (BounceResponse15D730 *)(arg0 + '+off+'));')for off in('0xA8','0xB0')]
def changed_source(before,fragment):
 assert before.count(RECORD_TYPE)==before.count(RESPONSE_TYPE)==before.count(OLD_PROTO)==1
 after=before.replace(RECORD_TYPE+'\n','',1).replace(RESPONSE_TYPE+'\n','',1).replace(OLD_PROTO,DECLARATIONS+'\n'+PROTOTYPE,1).replace(STUB,fragment,1)
 for old,new in CALLS:after=after.replace(old,new)
 return after

def source_states(live):
 before=(ROOT/BUILD/'frozen'/SOURCE).read_text()
 if sha((ROOT/BUILD/'frozen'/SOURCE).read_bytes())!=FROZEN[SOURCE]:raise ValueError('Plane callback predecessor source changed')
 after=changed_source(before,SELECTED)
 if live==before:return before,after,False
 if live==after:return before,after,True
 raise ValueError('Plane callback source is neither frozen predecessor nor proposal')
ORDER=(2,0,1,6,3,5,4,7,8)
def fp_swap(word):
 if word>>26 in(49,57):
  reg=word>>16&31
  if reg in(4,18):word=word&~(31<<16)|((18 if reg==4 else 4)<<16)
 return word
def effects(word):
 op,rs,rt,rd=word>>26,word>>21&31,word>>16&31,word>>11&31
 imm=((word&65535)^32768)-32768;memory=None
 if op in(49,57):r,v={('g',rs)},{('f',rt)};memory=('R'if op==49 else'W',rs,imm)
 elif op==35:r,v={('g',rs)},{('g',rt)};memory=('R',rs,imm)
 elif op==15:r,v=set(),{('g',rt)}
 elif op==0 and word&63==37:r,v={('g',rs),('g',rt)},{('g',rd)}
 else:raise ValueError(('Unsupported plane callback setup word',hex(word)))
 if op==57:r,v=r|v,set()
 return r-{('g',0)},v-{('g',0)},memory
def certificate(raw):
 w=struct.unpack('>78I',raw);block=[fp_swap(v)for v in w[54:63]]
 assert [(v>>26,v>>21&31,v&65535)for v in(w[54],w[55],w[56],w[57],w[58],w[59],w[60],w[62])]==[(49,29,48),(49,29,56),(35,29,72),(57,29,36),(57,29,44),(49,16,128),(15,0,0),(57,29,40)]
 assert BINDINGS[240]==[('R_MIPS_HI16','D_80089874')]
 current=list(range(9));swaps=0
 for destination,index in enumerate(ORDER):
  at=current.index(index)
  while at>destination:
   a,b=current[at-1],current[at];ar,av,am=effects(block[a]);br,bv,bm=effects(block[b])
   assert not(av&(br|bv)or bv&(ar|av)),('Dependent plane setup registers',a,b)
   if am and bm and'W'in(am[0],bm[0]):
    # Private contact words cannot overlap each other or SP+0x48. The one
    # public read uses a valid incoming record disjoint from this new frame.
    assert(am[1]==bm[1]==29 and abs(am[2]-bm[2])>=4)or{am[1],bm[1]}=={16,29}
   current[at-1],current[at]=b,a;at-=1;swaps+=1
 return dict(start_word=54,stop_word=63,independent_adjacent_swaps=swaps,FP_scratch_swap=[4,18],
  valid_record_disjoint_from_private_frame_required_for_raw_equivalence=True,private_contacts_not_exposed_before_callback=True,
  frame=64,all_homes_saved_registers_public_access_order_and_branches_fixed=True,raw_private_fault_or_scratch_identity_not_claimed=True,insertions=0,omissions=0)
def normalize(raw,refs):
 if len(raw)!=312 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Plane callback raw words or bindings changed')
 certificate(raw);words=list(struct.unpack('>78I',raw));block=[fp_swap(v)for v in words[54:63]]
 words[54:63]=[block[i]for i in ORDER];newrefs={p:r for p,r in refs.items()if not 216<=p<252}
 for destination,index in enumerate(ORDER):
  if(54+index)*4 in refs:newrefs[(54+destination)*4]=refs[(54+index)*4]
 return struct.pack('>78I',*words),newrefs
def guard_rows(raw,refs):
 normal,nrefs=normalize(raw,refs);spec=lambda rs:';'.join(k+':'+n for k,n in rs)or'-'
 return [[OWNER,FUNCTION,hex(i*4),'0x%08X'%a,'0x%08X'%b,spec(refs.get(i*4,[])),spec(nrefs.get(i*4,[])),'Normalize closed plane callback setup schedule and float scratch roles','','','false']for i,(a,b)in enumerate(zip(struct.unpack('>78I',raw),struct.unpack('>78I',normal)))if a!=b or refs.get(i*4,[])!=nrefs.get(i*4,[])]
def guard_manifest(before,raw,refs):
 if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Inherited plane callback guards changed')
 stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs));return before+stream.getvalue().encode()

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        for name,wanted in FROZEN.items():
            data=(root/name).read_bytes()
            if sha(data)!=wanted:raise ValueError('Plane callback baseline changed: '+name)
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        receipt.write_text(json.dumps(FROZEN,indent=2)+'\n')
    hashes=json.loads(receipt.read_text())
    if hashes!=FROZEN:raise ValueError('Plane callback frozen manifest changed')
    allowed={SOURCE,OBJECT,ELF,GUARDS}
    for n,h in hashes.items():
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Plane callback input changed: '+n)
    return hashes

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=312:raise ValueError('Plane callback predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,312);wanted[at:at+312]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Plane callback predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,312)
    # Only the target body and its 12-to-312-byte extent may change. Every
    # symbol/string row and every other byte must remain literally identical.
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b]
        raise ValueError('Literal plane callback entire image differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b,isolated):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Plane callback owner pools changed')
    old,new,single=(sections(p)['.reginfo']for p in(a,b,isolated))
    before,result,alone=(struct.unpack('>6I',v[1])for v in(old,new,single))
    if (before,alone)!=REGISTER_INPUTS or result!=tuple(before[i]|alone[i]if i<5 else before[i]for i in range(6)):raise ValueError('Plane callback register union changed')
    return dict(before=list(before),isolated=list(alone),exact_register_union=True)

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Plane callback predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    if diagnostic_rows(old_diag)!=diagnostic_rows(new_diag)or sum(diagnostic_rows(new_diag).values())!=0:raise ValueError('Plane callback owner diagnostics changed')
    isolated,diag=compile_owner(root,out,ISOLATED_HEADER+SELECTED,'qualified-isolated')
    if diag or function_blob(isolated)!=function_blob(new):raise ValueError('Plane callback isolated body changed')
    neighbors=same_functions(old,new,(FUNCTION,));metadata=owner_pools(old,new,isolated)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+312]
    symbols={name:0x15047D60 if name=='sinf'else 0x15047C00 if name=='cosf'else int(name.split('_')[1],16)for rows in refs.values()for _,name in rows}
    if struct.pack('>78I',*bound_blob(normal,nrefs,symbols))!=truth:raise ValueError('Plane callback normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Plane callback live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=padded(root,out,new,guards,'independent-qualified-padded',True)
    if same_functions(new_pad,strict)!=OWNER_FUNCTIONS or normalized_pools(new_pad)!=normalized_pools(strict):raise ValueError('Plane callback strict padder differs')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Plane callback padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Plane callback live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);make=make_shadow(root,out,proposal,guards,new_pad,new)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Plane callback live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Plane callback linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Plane callback protected data changed')
    generated={n:tuple(f[1:])for _,n,f,_ in symbol_rows(new_pad.read_bytes())};strict_names={n:tuple(f[1:])for _,n,f,_ in symbol_rows(strict.read_bytes())}
    start,_,_,jumps=pad_generated_object.parse_retail_slice(root/'conker/asm/15D730.s');labels={n:(a-start,0,16,0,1)for a,ns in jumps.items()for n in ns}
    if set(generated)-set(strict_names)!=set(labels)or generated!={**strict_names,**labels}:raise ValueError('Plane callback case labels changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=78,raw_words=78,frame=FRAME,guards=8,direct_C=False,register_metadata=metadata,
      preserved_labels=len(labels),raw_neighbors=neighbors,padded_neighbors=padded_neighbors,diagnostics=sum(diagnostic_rows(new_diag).values()),
      named_metadata_groups=len(METADATA_GROUPS),named_metadata_rows=sum(len(names)for names,_ in METADATA_GROUPS),
      actual_Make=make,strict_changed_bytes=changed,exclusions=0,functions=len(a),all_addresses_fixed=True,
      changed_bodies=[FUNCTION],protected_data=data,owner_sha256=sha(new_pad.read_bytes()),ELF_sha256=sha(new_image.read_bytes()),guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,raw=raw,refs=refs,normal=normal,normal_refs=nrefs,predecessor_elf=old_image,qualified_elf=new_image,qualified_object=new_pad)

def link(root, out, owner, label):
    staged=out/(label+'-objects')/Path(OBJECT).name
    staged.parent.mkdir(parents=True,exist_ok=True);staged.write_bytes(owner.read_bytes());owner=staged
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Plane callback linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination

def make_shadow(root,out,proposal,guards,wanted,compact):
    shadow=out/'make-shadow';conker=root/'conker'
    target=shadow/'src/game/generated_15D730.c.o';target.parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()],cwd=conker,capture_output=True,text=True,check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands=[];compiler_diagnostics=None
    expected=diagnostic_rows((out/'qualified-owner-diagnostics.txt').read_text())
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown plane callback Make command: '+repr(args))
        args=[proposal.relative_to(conker).as_posix()if a==SOURCE.removeprefix('conker/')else guards.relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
        redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown plane callback Make redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        result=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        is_cc=args[0]=='../ido/ido5.3_recomp/cc'
        if result.returncode or diagnostic_rows(result.stderr)!=(expected if is_cc else Counter())or(redirect is None and result.stdout):raise ValueError(result.stdout+result.stderr)
        if is_cc:
            if compiler_diagnostics is not None or '-Wo,-loopunroll,0'in args or args.count('-O2')!=1 or args.count('-g3')!=1:raise ValueError('Plane callback compiler profile changed')
            compiler_diagnostics=result.stderr
        if redirect is not None:redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands)!=5 or compiler_diagnostics is None:raise ValueError('Plane callback actual Make recipe changed')
    if target.read_bytes()!=wanted.read_bytes():raise ValueError('Plane callback actual Make owner differs')
    count=same_functions(compact,Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    return dict(commands=len(commands),functions=count,padded_object_equal=True,inherited_Make_warnings=plan.stderr,diagnostics=sum(expected.values()))

def padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    if strict:
        from tools import pad_c_object
        assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', OWNER, word_patches_path=guards)
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/15D730.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
