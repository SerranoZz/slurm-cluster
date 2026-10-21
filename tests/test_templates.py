from pathlib import Path

import jinja2
import yaml

ROOT = Path(__file__).parent.parent
TPL = ROOT / "ansible/roles/slurm/templates"
VARS = yaml.safe_load((Path(__file__).parent / "fixtures/inventory_vars.yml").read_text())


def render(name: str, **over) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TPL), trim_blocks=True)
    return env.get_template(name).render(**{**VARS, **over})


def lines(text: str, prefix: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith(prefix)]


def test_headnode_fora_dos_nos():
    conf = render("slurm.conf.j2")
    assert "SlurmctldHost=head01" in conf
    assert not any("head01" in line for line in lines(conf, "NodeName="))
    assert not any("head01" in line for line in lines(conf, "PartitionName="))


def test_gres_apenas_gpu_suportada():
    nodes = {line.split()[0]: line for line in lines(render("slurm.conf.j2"), "NodeName=")}
    assert "Gres=gpu:rtx_3090:2" in nodes["NodeName=node01"]
    assert "Gres=" not in nodes["NodeName=node02"]
    assert "Gres=" not in nodes["NodeName=node03"]


def test_particao_gpu_so_nos_com_gpu():
    parts = {line.split()[0]: line for line in lines(render("slurm.conf.j2"), "PartitionName=")}
    assert "Nodes=node01 " in parts["PartitionName=gpu"] + " "
    assert "node02" not in parts["PartitionName=gpu"]
    assert "node03" not in parts["PartitionName=gpu"]


def test_no_sem_gpu_so_na_particao_cpu():
    parts = {line.split()[0]: line for line in lines(render("slurm.conf.j2"), "PartitionName=")}
    assert "Nodes=node01,node02,node03" in parts["PartitionName=cpu"]


def test_accounting_slurmdbd_e_gres():
    conf = render("slurm.conf.j2")
    assert "AccountingStorageType=accounting_storage/slurmdbd" in conf
    assert "GresTypes=gpu" in conf


def test_gres_conf_autodetect_nvml():
    assert "AutoDetect=nvml" in render("gres.conf.j2")


def test_sem_nos_com_gpu_nao_cria_particao_gpu():
    hv = {k: {**v, "gpu_supported": False} for k, v in VARS["hostvars"].items()}
    conf = render("slurm.conf.j2", hostvars=hv)
    assert not lines(conf, "PartitionName=gpu")
    assert "PartitionName=cpu" in conf
