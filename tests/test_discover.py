import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import discover  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


def test_parse_slurmd_c():
    hw = discover.parse_slurmd_c((FIX / "slurmd_c.txt").read_text())
    assert hw["cpus"] == 16
    assert hw["sockets"] == 1
    assert hw["cores_per_socket"] == 8
    assert hw["threads_per_core"] == 2
    assert hw["real_memory_mb"] == 64000


def test_gpu_type_normalizado():
    gpus = discover.parse_gpus("NVIDIA GeForce RTX 3090, 8.6\n")
    assert gpus == [{"model": "NVIDIA GeForce RTX 3090", "type": "rtx_3090", "compute_cap": 8.6}]


def test_duas_gpus_mesmo_modelo():
    gpus = discover.parse_gpus("NVIDIA GeForce RTX 3090, 8.6\nNVIDIA GeForce RTX 3090, 8.6\n")
    assert len(gpus) == 2
    assert gpus[0]["type"] == gpus[1]["type"] == "rtx_3090"


def test_sem_gpu():
    assert discover.parse_gpus("") == []
    hw = discover.parse_slurmd_c((FIX / "slurmd_c.txt").read_text())
    out = yaml.safe_load(discover.render_host_vars("node01", hw, [], 6.0))
    assert out["gpus"] == []
    assert out["gpu_supported"] is False


def test_gpu_antiga_nao_suportada():
    hw = discover.parse_slurmd_c((FIX / "slurmd_c.txt").read_text())
    gpus = discover.parse_gpus("NVIDIA GeForce GTX 970, 5.2\n")
    out = yaml.safe_load(discover.render_host_vars("node01", hw, gpus, 6.0))
    assert out["gpu_supported"] is False


def test_gpu_suportada():
    hw = discover.parse_slurmd_c((FIX / "slurmd_c.txt").read_text())
    gpus = discover.parse_gpus("NVIDIA GeForce RTX 3090, 8.6\n")
    out = yaml.safe_load(discover.render_host_vars("node01", hw, gpus, 6.0))
    assert out["gpu_supported"] is True
    assert out["cpus"] == 16
