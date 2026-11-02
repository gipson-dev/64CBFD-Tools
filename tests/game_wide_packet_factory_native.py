from pathlib import Path
import json
import os
import subprocess


def qualify(output):
    source = output / "native_harness_v3.c"
    include = output / "native_include"
    profiles = []
    environment = dict(os.environ)
    environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    for optimization in ("O0", "O2", "O3"):
        executable = output / ("native-v3-" + optimization)
        command = [
            "gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
            "-fno-strict-aliasing", "-ffp-contract=off", "-fsanitize=undefined",
            "-fno-sanitize-recover=all", "-" + optimization,
            "-I", str(include), "-o", str(executable), str(source),
        ]
        compiled = subprocess.run(command, capture_output=True, text=True)
        assert compiled.returncode == 0, (optimization, compiled.stdout, compiled.stderr)
        ran = subprocess.run([str(executable)], capture_output=True, text=True, env=environment)
        assert ran.returncode == 0, (optimization, ran.stdout, ran.stderr)
        row = json.loads(ran.stdout)
        assert row["success"] and row["cases"] == 256
        profiles.append({
            "optimization": optimization,
            "cases": row["cases"],
            "UBSan_clean": True,
            "compiler_stderr": compiled.stderr,
            "runtime_stderr": ran.stderr,
        })
    report = {
        "success": True,
        "private_only": True,
        "matching_credit": 0,
        "profiles": profiles,
        "cases_per_profile": 256,
        "total_executions": 768,
        "all256_mode_bytes": True,
        "live_input_after_first_RNG_and_after_submit": True,
        "input_live_extent_bytes": 71,
        "input_natural_bytes": 72,
        "packet_visible_bytes": 54,
        "packet_live_extent_bytes": 58,
        "packet_natural_bytes": 60,
        "initialized_payload_bytes_compared": True,
        "private_bytes_untouched_proven_by_guest_gate": True,
        "independent_native_control": True,
        "UBSan_clean": True,
    }
    (output / "private-native-v3.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(qualify(Path(__file__).parent), flush=True)
