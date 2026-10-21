# Fase 1: automação com Ansible

Rode a partir de `ansible/` no headnode.

## 1. Gerar `host_vars` de cada nó

O Slurm precisa saber CPUs, memória e GPUs de cada nó. O script descobre isso:

```bash
scp ../scripts/discover.py lab-hpc@node01:/tmp/
ssh lab-hpc@node01 'python3 /tmp/discover.py node01 --min-cap 7.5' > host_vars/node01.yml
```

`gpu_supported: false` significa: sem GPU, ou GPU antiga demais. O nó fica só com CPU.

> `discover.py` usa `slurmd -C`. Em um nó novo, rode antes `ansible-playbook playbooks/common.yml` e `sudo apt install slurmd`.

## 2. Segredos e usuários

```bash
cp ../secrets/slurmdbd.example.yml ../secrets/slurmdbd.yml   # troque a senha e apague a linha slurmdbd_example_placeholder; fica fora do git
cp group_vars/users.example.yml group_vars/users.yml         # apague a linha users_example_placeholder e edite a lista
```

Ajuste `lab_uid`, `lab_gid` e `nfs_subnet` em `group_vars/all.yml`.

## 3. Rodar tudo

```bash
ansible-playbook playbooks/site.yml
```

Ordem: base → usuários → NFS → munge → NVIDIA → OpenMPI → banco/slurmdbd → Slurm. Rode de novo: nada deve mudar (`changed=0`).

## O que cada etapa faz na mão

| Playbook | Equivalente manual |
|---|---|
| `common` | `apt install chrony build-essential nfs-common`; entradas em `/etc/hosts` |
| `users` | `groupadd`/`useradd` com UID/GID fixos |
| `storage` | `/etc/exports` + `exportfs -ra` no headnode; `mount -t nfs head01:/home /home` nos nós |
| `munge` | `mungekey --create` no headnode e copiar `/etc/munge/munge.key` (0400) |
| `nvidia` | repositório CUDA da NVIDIA + `apt install nvidia-driver-<v> cuda-toolkit-<v>` |
| `openmpi` | `apt install openmpi-bin libopenmpi-dev`; `ompi_info \| grep pmix` |
| `accounting` | MariaDB, banco `slurm_acct_db`, `slurmdbd.conf` 0600, backup semanal |
| `slurm` | `apt install slurmctld`/`slurmd`; `/etc/slurm/slurm.conf`, `gres.conf`, `cgroup.conf` |

## Se o Slurm do Ubuntu não tiver PMIx

A role `slurm` falha com a checagem de PMIx. Defina `slurm_install_method: build` em `group_vars/all.yml` para compilar (PMIx + NVML).
