#!/usr/bin/env python3
"""Descobre o hardware de um nó e imprime o host_vars YAML.

Uso (rode no nó, ou via ssh, e salve em ansible/host_vars/<nó>.yml):
    python3 discover.py <nó> --min-cap 7.5
"""
import argparse
import re
import subprocess

import yaml


def parse_slurmd_c(text: str) -> dict:
    def num(key: str) -> int:
        return int(re.search(rf"\b{key}=(\d+)", text).group(1))

    return {
        "cpus": num("CPUs"),
        "sockets": num("SocketsPerBoard"),
        "cores_per_socket": num("CoresPerSocket"),
        "threads_per_core": num("ThreadsPerCore"),
        "real_memory_mb": num("RealMemory"),
    }


def _gpu_type(model: str) -> str:
    """Mesmo formato do Type do NVML no Slurm: minúsculas, espaços viram _, hífens ficam."""
    name = re.sub(r"\bNVIDIA\b", "", model, flags=re.I).strip()
    return re.sub(r"\s+", "_", name.lower())


def parse_gpus(csv_text: str) -> list[dict]:
    gpus = []
    for line in csv_text.splitlines():
        if not line.strip():
            continue
        model, cap = (p.strip() for p in line.rsplit(",", 1))
        gpus.append({"model": model, "type": _gpu_type(model), "compute_cap": float(cap)})
    return gpus


def parse_lspci(text: str) -> list[dict]:
    """Detecta GPUs NVIDIA pelo PCI (vendor 10de), útil antes de instalar o driver."""
    gpus = []
    for line in text.splitlines():
        if "nvidia" not in line.lower():
            continue
        m = re.search(r"\[([^\]]*(?:GeForce|Quadro|Tesla|RTX|A\d+|H\d+|L\d+)[^\]]*)\]", line)
        model = m.group(1) if m else "nvidia_gpu"
        gpus.append({"model": model, "type": _gpu_type(model), "compute_cap": None})
    return gpus


def render_host_vars(node: str, hw: dict, gpus: list[dict], min_cap: float) -> str:
    supported = bool(gpus) and all(g["compute_cap"] is None or g["compute_cap"] >= min_cap for g in gpus)
    data = {"node_name": node, **hw, "gpus": gpus, "gpu_supported": supported}
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("node")
    ap.add_argument("--min-cap", type=float, default=7.5)
    args = ap.parse_args()
    hw = parse_slurmd_c(_run(["slurmd", "-C"]))
    # Com driver: nvidia-smi dá compute capability. Sem driver: lspci só detecta (cap desconhecida).
    gpus = parse_gpus(_run(["nvidia-smi", "--query-gpu=name,compute_cap", "--format=csv,noheader"])) or parse_lspci(_run(["lspci", "-nn"]))
    print(render_host_vars(args.node, hw, gpus, args.min_cap), end="")


if __name__ == "__main__":
    main()
