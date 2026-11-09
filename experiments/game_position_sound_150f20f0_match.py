"""Position sound: direct C, complete owner and strict linked-image audit."""
import hashlib,json,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_remaining_donor_candidates import compile_owner as compile_default
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments import game_actor_state_tick_integration as metadata
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-position-sound-150F20F0-match'
FUNCTION,OWNER='func_150F20F0','generated_11C2B0'
SOURCE='conker/src/game/generated_11C2B0.c'
OBJECT='conker/build/src/game/generated_11C2B0.c.o'
CALLER_SOURCE='conker/src/game/generated_1A1E50.c'
CALLER_OBJECT='conker/build/src/game/generated_1A1E50.c.o'
ASM='conker/asm/11C2B0.s'
ELF='conker/build/conker.us.elf'
GUARDS='conker/retail_word_patches.us.csv'
ENTRY,ROM,SIZE,SLOT_SIZE=0x150F20F0,0x11F5A0,320,320
STUB='s32 func_150F20F0() {\n    return 0;\n}'
DECLARATIONS='extern struct127 D_800CC2D0[26];\nextern u8 D_800D98F0;\nextern s32 D_800BE9E4;\nextern f32 D_800A191C;\nvoid func_100114D0(s32,s32,s32,s32,s32,s32,s32*,s32*,s32*);\nvoid func_10010F30(s32,u16,u8,s16,u8);\n'
SYMBOL_ORDER=(('D_800D98F0','func_15000000'),('D_800A191C','D_800A154C','func_1519E61C'),('D_80095BD8','D_8009D440'))
HEADER='#include <ultra64.h>\n#include "structs.h"\ns32 func_150ADA20(void);\nextern struct127 D_800CC2D0[26];\nextern u8 D_800D98F0;\nextern s32 D_800BE9E4;\nextern f32 D_800A191C;\nvoid func_100114D0(s32,s32,s32,s32,s32,s32,s32*,s32*,s32*);\nvoid func_10010F30(s32,u16,u8,s16,u8);\n'
SELECTED='/* Preserve the quartic position threshold and the shared byte cooldown. */\nvoid func_150F20F0(s32 index) {\n    f32 x;\n    f32 z;\n    s32 output0;\n    s32 output1;\n    s32 output2;\n    s32 soundId;\n    x = D_800CC2D0[index].x_position;\n    z = D_800CC2D0[index].z_position;\n    x *= x;\n    z *= z;\n    x = x*x + z*z;\n    if (D_800D98F0 != 0) {\n        if (D_800BE9E4 < D_800D98F0) {\n            D_800D98F0 = (u8)((u32)D_800D98F0 - (u32)D_800BE9E4);\n        } else {\n            D_800D98F0 = 0;\n        }\n    } else if (x > D_800A191C) {\n        func_100114D0(0,(s32)D_800CC2D0[index].y_position,0,32767,20000,19000,&output0,&output1,&output2);\n        output0 = (s32)((u32)output0 + 128);\n        D_800D98F0 = (func_150ADA20() & 127) + 128;\n        /* Read the retained output only after the final random draw. */\n        soundId = (u32)func_150ADA20()%3 + 108;\n        func_10010F30(soundId,24000,(u8)output0,0,0);\n    }\n}\n'
FROZEN={'conker/Makefile': '8e676e04318f8645e6b277ed60ed9f221d8901a5e6a02efd279d478d46a615f8', 'conker/asm/11C2B0.s': '064851c4bd1d09f2eec8dc0b3bbfa579b8e028d24e94c8ce4468d5a1732403db', 'conker/asm/1A1E50.s': 'e9e139cbca83c15ad1f2d4147af554c6c140ae5ededc3ee0272008948e3496e9', 'conker/asm/data/231730.rodata.s': '887c6f85ceaa241c4e55cca63b76edcb87af5dd9d04e8a2ae9d292e384421f6c', 'conker/asm/data/246380.rodata.s': 'ef3f7730fa066b24789a06f79ab95c06c289015b6aa4ebec22889c364977e8a5', 'conker/asm/nonmatchings/game_DAE50/func_150ADA20.s': '64b478aa7a866ba3793982326254c86aad25a0e378e364497ea1a32b4eb2f50a', 'conker/asm/nonmatchings/init_EB00/func_100114D0.s': '572245abbf92d869bb1893a2c5e76e9d5419cf1dddefc46a4ff18bd08cdbb6a5', 'conker/build/conker.ld': '6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5', 'conker/build/conker.us.elf': 'e514b506e825ad0332137f8406aad09dbfdb44516b8c2c9b54d5fe4f2a2679e9', 'conker/build/src/game/generated_11C2B0.c.o': 'd7204abd75ee29ebf88c6a0c3677ca9fc584befb7c3076f5600934bd692bb2d6', 'conker/build/src/game/generated_1A1E50.c.o': 'd6f26953bac830554a342a16f33ae4ff5643602f1ac98dc5cf62a767c39423a5', 'conker/build/src/init_EB00.c.o': 'd8eff52ea164c3a6078e5aec0e3544d74cd963876962acf87ad079ab17e47f32', 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382', 'conker/conker.us.yaml': 'd31a14128e74793a2cc5fcb7ca3a65abefc7cafe01528268b0e0af76f94bff1f', 'conker/include/2.0L/PR/PRimage.h': '25bac64b4d176598cedb468b437b8ac7c13c4f255b8573d6aa60058f0b86be1c', 'conker/include/2.0L/PR/R4300.h': 'bb8a7702ef8dfe94c389f0c411a4f2346c506ea8766e85c332a44486a97b7b44', 'conker/include/2.0L/PR/abi.h': '9efe7ee3c940ff96d46f936ad95e9cc52b879ee8c4b5c264cb8f42e1cf1ce1bf', 'conker/include/2.0L/PR/gbi.h': '155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6', 'conker/include/2.0L/PR/gs2dex.h': 'e9d3519bb328f9ac60b60d119650e1e4d652eaaddcd9db009f9cbd44daecb398', 'conker/include/2.0L/PR/gt.h': '05e50d177fe2ae42b02bcb384452317029b919f53403a5be1a3d64d47f2e1296', 'conker/include/2.0L/PR/gu.h': 'bc7761b1d0688b009d82a17776e21782842b652eb5b257088458b9fee8c63cff', 'conker/include/2.0L/PR/leo.h': 'e8ad69061d2fb4ee2acbd4c48184b6cebb05b0f3e56087d18d92c3061c0b0b47', 'conker/include/2.0L/PR/leoappli.h': '902916bad5d2056117570acebaa28cf57c46c2a22bb7cdd111d48ccacc249532', 'conker/include/2.0L/PR/libaudio.h': '53a127fef608e66f7883fc1d76c6eab609c27a127aebc89e89c87757a9ef97b9', 'conker/include/2.0L/PR/mbi.h': '8a0b32eb3cc7844a38b1b3ed1b160036b203efac0dc3c0275c53354423e40960', 'conker/include/2.0L/PR/n_libaudio.h': '223f1db0cf93edeb1e1f03af299eb7aeab8c619e78111d2f59dba31280d6a618', 'conker/include/2.0L/PR/n_libaudio_s_to_n.h': '6cad54fa2252fad7cb476882c819515ccec2d4120c94f6488f052cfdf261fddf', 'conker/include/2.0L/PR/os.h': 'e0af7328cadb2164b18c61717d916396741cf053d32b96b0dea06f6d664ff7e2', 'conker/include/2.0L/PR/os_ai.h': '933e7fe35c87702a2137b9c575022e18bd72e6ce11d8a44035a7ffbddf71aeb6', 'conker/include/2.0L/PR/os_cache.h': 'a9455e20523c6915f26c05d5d399763f1e051c01eac85c10911b7b3a65c0d5c9', 'conker/include/2.0L/PR/os_cont.h': '8b486936ae60b8a486e87489e77f40f557a0bf59fddf9c1adc5c97aa18388c0b', 'conker/include/2.0L/PR/os_convert.h': '6d98f19765d055a7857398cc6d7bd7a2ac2e93a4a858f1c27aa22361e4f892f1', 'conker/include/2.0L/PR/os_debug.h': '260815777abca616a9783db7a57cd94881586c84ef0adcce26516ba50476a523', 'conker/include/2.0L/PR/os_eeprom.h': 'f1f0f50895c4505c3420674504b7868ff85fe08df42433389deeb407e68c5163', 'conker/include/2.0L/PR/os_error.h': 'eae3744bf9ee921d089714e81590226b56fca5ca2f0ef866532eb788e829b120', 'conker/include/2.0L/PR/os_exception.h': '953bf8361f5e756010c45dc5f823c12183838bd723ec691a99a9fcf682e0698c', 'conker/include/2.0L/PR/os_flash.h': '7206e87e62400994347ff2d84bd5f563894c9c18cdbe34c0c5dd9fb2bcfa758f', 'conker/include/2.0L/PR/os_gbpak.h': 'c13616c011c214aef601f6249ae12465dcb8a6edfe68df27aaf6d086e09bbc8f', 'conker/include/2.0L/PR/os_gio.h': 'c0197b2afd220c07028a972ca0d5903af3064d48d8657935e3c57fc9a55f3b92', 'conker/include/2.0L/PR/os_host.h': '3b990c99a18cba34c3d8a856e3e99691125ec8338df42198fe469ee7bb9f9bcc', 'conker/include/2.0L/PR/os_internal.h': '0103aa8359ff23c9ef0b248b0721ea9df0c4557271e4146ac264d0d998b7280d', 'conker/include/2.0L/PR/os_internal_debug.h': '3e4f1baa87602ad77163c15990625e1fd3b9ae6cffcaabb3424dafec6d638bd0', 'conker/include/2.0L/PR/os_internal_error.h': 'ab7537aef80c392dcf0010bde8078f1b5d1973740bc6d51e1f4df3d757e28356', 'conker/include/2.0L/PR/os_internal_exception.h': 'b8124a51000cb0608a34c56d0242e0373d845f0bd28b6fb9b95f7dd21cf9ea65', 'conker/include/2.0L/PR/os_internal_gio.h': '032d50b58fd0f3d8831430a7125cd039efd1f56affdd8cbeb8777ab464ecba15', 'conker/include/2.0L/PR/os_internal_host.h': '83dda0b09da200ab1be91aeda90c2d0f52b7a282979391e05a9f4feeff1fffd1', 'conker/include/2.0L/PR/os_internal_reg.h': 'bbfe19f64f9383dfbd4d2ee17d2556ad8e3ae29f0803580637d0df59aa110f39', 'conker/include/2.0L/PR/os_internal_rsp.h': '77f2c0f58ebe5384970a553cabf850841a679e97dbd049926d13b0cb29f18c58', 'conker/include/2.0L/PR/os_internal_si.h': '2d88a8388c9211646c446bcd936606b038f80f53c10b9674f48ad6f6dede5acc', 'conker/include/2.0L/PR/os_internal_thread.h': 'f7700e0bd2c22fb6716d656435b7431c6701cbfd518f2908d13845d11be5ddd9', 'conker/include/2.0L/PR/os_internal_tlb.h': 'e67bca1ce07a917679abb4094b087ee70bd01399576fe9d7c4e85c82f642ccf8', 'conker/include/2.0L/PR/os_libc.h': 'fb2f4e113eee01c1953aee8efea3b6eb450ea97e2a5af23ba868ca1059d26b6e', 'conker/include/2.0L/PR/os_message.h': '241238eea37d71382b7a3c994d5837e4482d77548a4cbdaeb30b9f67013cdfb7', 'conker/include/2.0L/PR/os_motor.h': '68103a1c114bc7e7c6decf847a5ec3c346e23e9de9c7488ca6bbedc39dae8ec4', 'conker/include/2.0L/PR/os_pfs.h': '6b14a950c344f7396bc1e58c9b6612f061053bd41b868dba32e13d904a3effd7', 'conker/include/2.0L/PR/os_pi.h': '3e29b28b596036ffbe86afa8bcec1126511b78fe862297c48061f97d42b747ea', 'conker/include/2.0L/PR/os_rdp.h': 'a85b9def6f64bf25e6aeb064e1f2626f7b2d4d0ef0821d21844a9eefb19f6e21', 'conker/include/2.0L/PR/os_reg.h': '2a14f15494cf3754f1fe0149a8c8cab4806e843f3be6a30ad0c726443edef52d', 'conker/include/2.0L/PR/os_rsp.h': 'ede13674c9af25912778dd077c3dd709929d43fcb9f135f6465553d0f9e8fa26', 'conker/include/2.0L/PR/os_si.h': 'ffd228b5b0e450efcf1756d778d701be958cce724d1912792c31b3cac26f74b9', 'conker/include/2.0L/PR/os_system.h': 'bc8afaa3362ff4851feee1feed818dd009a13c3de19435a2e09656a64bf531d8', 'conker/include/2.0L/PR/os_thread.h': 'b7c244ead94962a0ebcb0787a589e7b398eaf02d8fc6538698c7353b08dcbf7d', 'conker/include/2.0L/PR/os_time.h': '21bd983fa7b11daa6a06c053b5e9cd7c08420dd20657c4fd61be434389af3342', 'conker/include/2.0L/PR/os_tlb.h': '9bbb49127e7e2600f6dcceffe4a1d38f31d463327cfa384ce930ddfa63223893', 'conker/include/2.0L/PR/os_version.h': '66c2147d22b8ccf5b2eb4967c90b27dfb8c83ce07e08382fcd408c8ca0bc3873', 'conker/include/2.0L/PR/os_vi.h': 'f59a0d52ab0e2bc2ca0b8226bc9b9c1e58d3a9eb8df8c4e6d45aaa6ac51fb2b6', 'conker/include/2.0L/PR/os_voice.h': 'c0fb2f6f8eb68a6608a2401f6a2f4a38d1c65b5d1ae944d0b5999502a9cc432f', 'conker/include/2.0L/PR/ramrom.h': 'fa009dd8676f0af0ed0f0339dfe6ac2f67ad1a1b8675bdff42f71b937608a370', 'conker/include/2.0L/PR/rcp.h': '61e531c5c93e7b71c167ac1d3d08254f67e5009408defa4fe5b941674c5a6b8e', 'conker/include/2.0L/PR/rdb.h': 'ce4b388d5bf24b869eaee1919fd81a0655006b2327a6f521d954cfc0e546dfeb', 'conker/include/2.0L/PR/region.h': 'd1f523d36ab27f28eea0ffa0d87875661c14844d12c9bf0142932aa38af5869f', 'conker/include/2.0L/PR/rmon.h': 'b646e7e7febea89d9bfed1c1b58ebbe40a7d5378ccb50a1063cc1de5e8d3d07a', 'conker/include/2.0L/PR/sched.h': '40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572', 'conker/include/2.0L/PR/sp.h': '6d4dd33330efa090dcf438a5a05b82a8fa54e94db78bc7c8f4d32f16a638de18', 'conker/include/2.0L/PR/sptask.h': '12b0a593a7013076fb60cf7224f0bdf25da554076e8b6f2ffe3999769e737dc5', 'conker/include/2.0L/PR/ucode.h': '50201220d2f811d64e5e11611ec835f0c3bf1a79c3045a2dc40f7e46012765a4', 'conker/include/2.0L/PR/ucode_debug.h': '715bccc464d8dbaa1a421007b6bab49a303bf5d8eb75ed74c184dddf59e67661', 'conker/include/2.0L/PR/ultraerror.h': '979fbca1aee61876a524ff3825cfb9c6a18ef28c99eb100e8b9b751b5c266b86', 'conker/include/2.0L/PR/ultralog.h': '52564b52560297920881f56e81894cfd9d9ed22b4cba1f9298eb1e10b1cda449', 'conker/include/2.0L/PR/ultratypes.h': '1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd', 'conker/include/2.0L/PR/uportals.h': '76548ed2614bedba9c9236883ab236251a30995b12f96da1e7a8eee8cb1eca4e', 'conker/include/2.0L/assert.h': '99d2e0c96e7453fae576f879b64ac1bd9ea5c031541c041ee6111bdacbefb844', 'conker/include/2.0L/ultra64.h': '334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d', 'conker/include/asm_processor_prelude.inc': 'c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d', 'conker/include/functions.h': 'f01a41af0bdb2caaaeb2c198be68d91515efb39de98a34ba190e090503d5f10b', 'conker/include/libc/math.h': 'e13f7c37cc5ea7cf75a93c4b45c6b96f321d67a70e8cdbfbba0edb7de0c3e226', 'conker/include/libc/stdarg.h': '759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4', 'conker/include/libc/stddef.h': 'e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721', 'conker/include/libc/stdio.h': '060f3f7b91cde2ab969d3d04b40ed57ff2b61167ece52309b64f4c6ab9ebfae1', 'conker/include/libc/stdlib.h': '181e9dc382377ed777654ddbf8393f9244ac9dcee66f58e78b43d0dea53ebbe9', 'conker/include/libc/string.h': 'ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5', 'conker/include/macro.inc': 'd7366200752da1051aba7bf98e361ca4af662fb5e22c7107455fc06a34969f1e', 'conker/include/macros.h': 'dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769', 'conker/include/magic.h': '92d976e6596839e490234cb4f827f3d1156a1d535c3022c7152162ed11d08eea', 'conker/include/structs.h': 'e97e1a98ebcc522d82b52215078780102e0dd5e47d614bb3a4d4f3bbc94b9653', 'conker/include/variables.h': '02650aa4bf9fd66156f4e2cbd1e49156b9655eed68c3fae1cab15b1f99063a7d', 'conker/progress.csv': '7658d1ff6c2e3ae94567606200fcae0b7d08f5752a9ec0484108dc8056c8bdc0', 'conker/retail_layout.us.txt': 'eb8145837da425d7a55080459d22f11e21e1ac69e8b9d8ad5100ed5750d814f1', 'conker/retail_word_patches.us.csv': '6a6094f04735cb3127833e50b21f98c3374916605acd7aa79ccdebd80d22dfe7', 'conker/src/game/generated_11C2B0.c': '38a6a3d9ba164b3a1ab4c5e49c6c1b70ae583d38da84bbe33a1015206506ca7a', 'conker/src/game/generated_1A1E50.c': 'b1c4c6ebe87012ff2ad9240ad92adb6ade920e940feaa40edcbec367a3fd19db', 'conker/src/init_EB00.c': 'df10767e2955fc9d3e355712d3c5e8b3bf6fa9681ce79b528c50a689105dfb6e', 'conker/symbol_addrs.us.txt': '1e59d193c5aefcc13d14b5083ee80ee977a4a9dcf54b75db8595b192a223bafa', 'conker/undefined_funcs.us.txt': '92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a', 'conker/undefined_funcs_auto.txt': 'e2090d98c3a5450afc4a78aafd1a7f1f5114bd43c7bddecb6e79434f20955329', 'conker/undefined_syms.us.txt': 'd678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e', 'conker/undefined_syms_auto.txt': 'a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd', 'ido/ido5.3_recomp/cc': 'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a', 'ido/ido5.3_recomp/cfe': 'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9', 'ido/ido5.3_recomp/ugen': 'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d', 'ido/ido5.3_recomp/uopt': '23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d'}
RETAIL_SHA='e8fb83542d43147d798bf3594c7ad8f34cc19f7c84baf7f6361e932222e07f6a'
RAW_SHA='44ff0e87fcfc95fb36d2d319524d047cc711f2f9f85ed956c0df835e5182f16d'
BINDINGS={4: [('R_MIPS_HI16', 'D_800D98F0')], 8: [('R_MIPS_LO16', 'D_800D98F0')], 48: [('R_MIPS_HI16', 'D_800CC2D0')], 52: [('R_MIPS_LO16', 'D_800CC2D0')], 112: [('R_MIPS_HI16', 'D_800BE9E4')], 116: [('R_MIPS_LO16', 'D_800BE9E4')], 80: [('R_MIPS_HI16', 'D_800A191C')], 148: [('R_MIPS_LO16', 'D_800A191C')], 220: [('R_MIPS_26', 'func_100114D0')], 236: [('R_MIPS_26', 'func_150ADA20')], 244: [('R_MIPS_HI16', 'D_800D98F0')], 256: [('R_MIPS_LO16', 'D_800D98F0')], 260: [('R_MIPS_26', 'func_150ADA20')], 296: [('R_MIPS_26', 'func_10010F30')]}
sha=lambda b:hashlib.sha256(b).hexdigest()

def source_states(live):
    old=(ROOT/BUILD/'frozen'/SOURCE).read_text()
    if sha((ROOT/BUILD/'frozen'/SOURCE).read_bytes())!=FROZEN[SOURCE]or old.count(STUB)!=1:raise ValueError('Position-sound predecessor changed')
    new=old.replace(STUB,DECLARATIONS+SELECTED.rstrip())
    if live not in(old,new):raise ValueError('Position-sound live source changed')
    return old,new,live==new

def freeze(root,out):
    allowed={SOURCE,OBJECT,ELF}
    for n,h in FROZEN.items():
        p=out/'frozen'/n
        if not p.exists():
            data=(root/n).read_bytes()
            if sha(data)!=h:raise ValueError('Position-sound initial input changed: '+n)
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        if sha(p.read_bytes())!=h or n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Position-sound frozen input changed: '+n)
    return FROZEN

def payload(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{a-start:v for a,v in rs.items()if start<=a<start+size}

def checked(raw,refs):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Position-sound raw body/bindings changed')
    return raw,refs

def padded(root,out,obj,label,generated=False):
    dest=out/(label+'.o');assembly=out/(label+'.s')
    if generated:text=emit_padded_assembly(obj,root/ASM,filename=OWNER,word_patches_path=root/GUARDS)
    else:
        from tools import pad_generated_object
        sys.modules.setdefault('pad_generated_object',pad_generated_object)
        from tools.pad_c_object import emit_padded_assembly as emit
        text=emit(obj,root/'conker/retail_layout.us.txt',OWNER,word_patches_path=root/GUARDS)
    assembly.write_text(text)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(dest),str(assembly)],check=True,capture_output=True)
    return dest

def strict_image(before,actual,truth):
    if sha(before)!=FROZEN[ELF] or len(truth)!=SLOT_SIZE or sha(truth)!=RETAIL_SHA:raise ValueError('Position-sound strict inputs changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,SLOT_SIZE);wanted[at:at+SLOT_SIZE]=truth
    rows=[(p,f)for p,n,f,_ in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Position-sound predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,SIZE)
    with patch.object(metadata,'SYMBOL_ORDER',SYMBOL_ORDER):wanted=metadata.reorder_symbols(bytes(wanted))
    if actual!=wanted:raise ValueError('Position-sound entire image differs from the body/extent and named-metadata prediction')
    return sum(a!=b for a,b in zip(before,actual))

def make_shadow(root,out,proposal,wanted,compact,source,objname,label,diagnostics,unroll):
    shadow=out/(label+'-shadow');conker=root/'conker';target=shadow/objname.removeprefix('conker/build/');target.parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()],cwd=conker,capture_output=True,text=True,check=True)
    (out/(label+'-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[];cc=0;expected=diagnostic_rows(diagnostics)
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown position-sound Make command')
        args=[proposal.relative_to(conker).as_posix()if a==source.removeprefix('conker/')else a for a in args];redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown position-sound Make redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p=subprocess.run(args,cwd=conker,capture_output=True,text=True);is_cc=args[0]=='../ido/ido5.3_recomp/cc'
        if p.returncode or diagnostic_rows(p.stderr)!=(expected if is_cc else Counter())or(redirect is None and p.stdout):raise ValueError(p.stdout+p.stderr)
        if is_cc:
            cc+=1
            if args.count('-O2')!=1 or args.count('-g3')!=1 or ('-Wo,-loopunroll,0'in args)!=unroll:raise ValueError('Position-sound Make compiler profile changed')
        if redirect is not None:redirect.write_text(p.stdout)
        commands.append(args)
    expected_commands=3
    if len(commands)!=expected_commands or cc!=1 or target.read_bytes()!=wanted.read_bytes():raise ValueError('Position-sound actual Make owner differs: '+repr((len(commands),expected_commands,target.read_bytes()==wanted.read_bytes())))
    count=same_functions(compact,Path(str(target)+'.compact'))
    (out/(label+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n')
    return dict(commands=len(commands),functions=count,padded_object_equal=True,diagnostics=sum(expected.values()),inherited_Make_warnings=plan.stderr)


def census(root):
    data=(root/'conker/conker.us.bin').read_bytes();calls=[];values=[]
    for j,(w,)in enumerate(struct.iter_unpack('>I',data)):
        if w>>26 in(2,3)and ENTRY<=((w&0x3FFFFFF)<<2|0x10000000)<ENTRY+320:calls.append(j*4)
        if ENTRY<=w<ENTRY+320:values.append(j*4)
    if calls or values!=[0x231828]:raise ValueError('Position-sound census changed')
    return dict(direct_calls=[],address_values=values,callback_table='D_8008CD04',callback_index=25,callback_signature='void(s32)',caller='func_151749F8',native_indices=list(range(26)),caller_has_no_view_range_gate=True)

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    old,od=compile_owner(root,out,before,'predecessor-owner');new,nd=compile_owner(root,out,after,'qualified-owner');single,sd=compile_owner(root,out,HEADER+SELECTED,'isolated')
    if od or nd or sd:raise ValueError('Position-sound owner diagnostics changed')
    raw,refs=checked(*payload(new))
    if payload(single)!=(raw,refs):raise ValueError('Position-sound isolated body differs')
    syms={n:int(n.split('_')[1],16)for rows in refs.values()for _,n in rows};truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SLOT_SIZE]
    if struct.pack('>80I',*bound_blob(raw,refs,syms))!=truth[:SIZE]:raise ValueError('Position-sound direct C differs from retail')
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    register_rows=[struct.unpack('>6I',sections(p)['.reginfo'][1])for p in(old,new,single)]
    if register_rows[1]!=tuple(register_rows[0][i]|register_rows[2][i]if i<5 else register_rows[0][i]for i in range(6)):raise ValueError('Position-sound register union changed')
    if normalized_pools(old)!=normalized_pools(new):raise ValueError('Position-sound raw pools changed')
    old_pad=padded(root,out,old,'predecessor-padded');new_pad=padded(root,out,new,'qualified-padded');independent=padded(root,out,new,'independent-padded',True)
    if same_functions(new_pad,independent)!=44 or normalized_pools(new_pad)!=normalized_pools(independent):raise ValueError('Position-sound independent padders differ')
    neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or payload(new_pad)!=(raw,refs):raise ValueError('Position-sound padded pools/body changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Position-sound live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after)
    recipe=make_shadow(root,out,proposal,new_pad,new,SOURCE,OBJECT,'owner-Make',nd,False)
    with patch.multiple(linker,FILENAME=OWNER,OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        old_elf=linker.link_image(root,out,old_pad,'predecessor-image');new_elf=linker.link_image(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_elf if installed else old_elf).read_bytes():raise ValueError('Position-sound live ELF differs')
    delta=strict_image(old_elf.read_bytes(),new_elf.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in b if a[n]!=b[n]]!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>80I',truth)):raise ValueError('Position-sound complete function/address census changed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Position-sound protected data changed')
    report=dict(words=80,slot_words=80,frame=88,guards=0,direct_C=True,raw_neighbors=raw_neighbors,padded_neighbors=neighbors,diagnostics=0,actual_Make=recipe,register_union_exact=True,source_installed=installed,frozen_inputs=len(FROZEN),strict_changed_bytes=delta,exclusions=0,metadata_reorders=len(SYMBOL_ORDER),named_metadata_rows=sum(map(len,SYMBOL_ORDER)),functions=len(a),all_addresses_fixed=True,changed_bodies=[FUNCTION],protected_data=data,ELF_sha256=sha(new_elf.read_bytes()),owner_sha256=sha(new_pad.read_bytes()),guard_sha256=sha((root/GUARDS).read_bytes()),caller_object_sha256=sha((root/CALLER_OBJECT).read_bytes()),registry=census(root))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,raw=raw,refs=refs,qualified_object=new_pad,predecessor_elf=old_elf,qualified_elf=new_elf)

if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
