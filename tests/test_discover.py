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
    assert gpus == [{"model": "NVIDIA GeForce RTX 3090", "type": "geforce_rtx_3090", "compute_cap": 8.6}]


def test_duas_gpus_mesmo_modelo():
    gpus = discover.parse_gpus("NVIDIA GeForce RTX 3090, 8.6\nNVIDIA GeForce RTX 3090, 8.6\n")
    assert len(gpus) == 2
    assert gpus[0]["type"] == gpus[1]["type"] == "geforce_rtx_3090"


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


def test_gpu_type_mantem_hifen_do_nvml():
    gpus = discover.parse_gpus("NVIDIA A100-SXM4-40GB, 8.0\n")
    assert gpus[0]["type"] == "a100-sxm4-40gb"


def test_lspci_detecta_gpu_sem_driver():
    text = "01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA102 [GeForce RTX 3090] [10de:2204] (rev a1)\n"
    gpus = discover.parse_lspci(text)
    assert gpus == [{"model": "GeForce RTX 3090", "type": "geforce_rtx_3090", "compute_cap": None}]


def test_gpu_sem_driver_conta_como_suportada_ate_medir():
    hw = discover.parse_slurmd_c((FIX / "slurmd_c.txt").read_text())
    gpus = discover.parse_lspci("01:00.0 VGA [0300]: NVIDIA Corporation GA102 [GeForce RTX 3090] [10de:2204]\n")
    out = yaml.safe_load(discover.render_host_vars("node01", hw, gpus, 7.5))
    assert out["gpu_supported"] is True


def test_lspci_ignora_dispositivo_nao_nvidia():
    assert discover.parse_lspci("00:02.0 VGA compatible controller [0300]: Intel Corporation UHD [8086:3e92]\n") == []
