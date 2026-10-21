# slurm-cluster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repositório com doc em português e playbooks Ansible que montam um cluster Slurm (CPU/MPI + GPU/CUDA, com slurmdbd) em PCs de laboratório com Ubuntu.

**Architecture:** Ansible roda só do headnode via SSH como `lab-hpc`. Um script Python descobre o hardware de cada nó e gera `host_vars/<nó>.yml`; templates Jinja geram `slurm.conf`/`gres.conf` a partir do inventário. Uma role por responsabilidade; `site.yml` as encadeia.

**Tech Stack:** Ansible (core), Python 3 + pytest + jinja2 (script de descoberta e teste de templates), ansible-lint, yamllint, Ubuntu (estável mais recente), Slurm, munge, NFS, MariaDB, OpenMPI+PMIx, driver NVIDIA + CUDA.

**Spec:** `docs/superpowers/specs/2026-10-20-slurm-cluster-design.md`

## Global Constraints

- Ubuntu já instalado; instalação do SO fora da doc.
- Docs, comentários e mensagens em português.
- Headnode: slurmctld, slurmdbd, MariaDB, munge, servidor NFS, login. **Sem slurmd, sem partição própria.**
- Partições `cpu` e `gpu`, somente nos nós de computação.
- Só `/home` via NFS. Driver NVIDIA, CUDA e OpenMPI instalados localmente por nó. Scratch local por nó.
- Mesmo UID/GID em todas as máquinas; os nós replicam o UID/GID do `lab-hpc` do headnode.
- GPU antiga demais para o driver: aviso, nó segue só CPU (sem driver/GRES).
- GRES com autodetecção NVML e `Type=` por modelo (`--gres=gpu:<modelo>:1`).
- Segredos (chave munge, senha do banco) nunca no git. Só `inventory.example` e `host_vars.example` versionados; reais no `.gitignore`.
- Slurm do pacote Ubuntu se tiver PMIx e NVML; senão compilar (role separado).
- Backup de banco: `mysqldump` semanal com rotação simples.
- Playbooks idempotentes. Binários de exemplo sem `-march=native`.
- Rede assumida 1 GbE, sem ajuste fino na v1.

## Review Focus

1. Nó com 0 GPU ou `nvidia-smi` ausente: descoberta gera `gpus: []`, nada de GRES, play de NVIDIA pula.
2. GPU não suportada pelo driver: `gpu_supported: false`, aviso, nó em `cpu` apenas.
3. Dois nós com o mesmo modelo de GPU e nomes com espaços (`NVIDIA GeForce RTX 3090`): `Type=` normalizado sem espaços, único por modelo.
4. Segunda execução de qualquer playbook: zero `changed` (idempotência).
5. Usuário já existente no nó com UID diferente: playbook falha com mensagem clara, não corrompe `/home`.

---

### Task 1: Esqueleto do repo e lint

**Files:**
- Create: `.gitignore`, `README.md`, `Makefile`, `ansible/ansible.cfg`, `ansible/inventory.example/hosts.yml`, `ansible/group_vars/all.yml`, `.yamllint`, `requirements.txt`
- Test: `make lint`

**Interfaces:**
- Produces: grupos de inventário `headnode` e `compute`; variáveis `cluster_name`, `headnode_hostname`, `lab_user`, `lab_uid`, `lab_gid`, `slurm_install_method` (`package|build`), `nvidia_min_compute_cap`; alvo `make lint` e `make test`.

- [ ] **Step 1: Criar a estrutura** com `.gitignore` cobrindo `ansible/inventory/`, `ansible/host_vars/*.yml` (exceto `.example`), `secrets/`, `*.vault`, `.venv/`.
- [ ] **Step 2: `Makefile`** com `lint` (`yamllint .` e `ansible-lint ansible/`) e `test` (`pytest tests/`).
- [ ] **Step 3: Rodar** `make lint`. Esperado: sai com código 0.
- [ ] **Step 4: Commit** `chore: esqueleto do repo e lint`.

### Task 2: Descoberta de hardware

**Files:**
- Create: `scripts/discover.py`, `tests/test_discover.py`, `tests/fixtures/slurmd_c.txt`, `tests/fixtures/nvidia_smi_l.txt`, `tests/fixtures/nvidia_smi_caps.csv`
- Test: `tests/test_discover.py`

**Interfaces:**
- Produces:
  - `parse_slurmd_c(text: str) -> dict` com chaves `cpus, sockets, cores_per_socket, threads_per_core, real_memory_mb` (ints).
  - `parse_gpus(csv_text: str) -> list[dict]` com `model` (original), `type` (normalizado: minúsculas, sem `NVIDIA`/`GeForce`, espaços→`_`), `compute_cap` (float). Entrada: saída de `nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader`.
  - `render_host_vars(node: str, hw: dict, gpus: list[dict], min_cap: float) -> str` (YAML com `gpu_supported: bool`, `gpus:`, specs de CPU).
  - CLI: `discover.py <nó> --min-cap 6.0` imprime YAML no stdout (executado via SSH pelo dono; grava em `ansible/host_vars/<nó>.yml`).

- [ ] **Step 1: Testes que falham:** `test_parse_slurmd_c` (fixture com `NodeName=x CPUs=16 Boards=1 SocketsPerBoard=1 CoresPerSocket=8 ThreadsPerCore=2 RealMemory=64000` → `cpus==16, cores_per_socket==8, threads_per_core==2, real_memory_mb==64000`); `test_gpu_type_normalizado` (`NVIDIA GeForce RTX 3090` → `rtx_3090`); `test_sem_gpu` (entrada vazia → `[]` e `gpu_supported: false`); `test_gpu_antiga_nao_suportada` (cap 5.2 com `min_cap` 6.0 → `gpu_supported: false`); `test_duas_gpus_mesmo_modelo` (ambas com o mesmo `type`).
- [ ] **Step 2: Rodar** `pytest tests/test_discover.py -v`. Esperado: FAIL (módulo inexistente).
- [ ] **Step 3: Implementar** as três funções e a CLI; `gpu_supported` é `true` só se há ≥1 GPU e todas têm `compute_cap >= min_cap`.
- [ ] **Step 4: Rodar** os testes. Esperado: PASS.
- [ ] **Step 5: Commit** `feat: descoberta de hardware por nó`.

### Task 3: Role `common` (base, chrony, hosts)

**Files:**
- Create: `ansible/roles/common/tasks/main.yml`, `ansible/roles/common/templates/hosts.j2`, `ansible/playbooks/common.yml`
- Test: `make lint` + `ansible-playbook --syntax-check`

**Interfaces:**
- Consumes: grupos `headnode`/`compute`, `ansible_host` por nó.
- Produces: `/etc/hosts` gerado do inventário; chrony ativo; pacotes base (`build-essential`, `nfs-common`, `python3`).

- [ ] **Step 1: Escrever a role** (apt, chrony, bloco gerenciado em `/etc/hosts` via `blockinfile` com todos os nós).
- [ ] **Step 2: Rodar** `ansible-playbook ansible/playbooks/common.yml --syntax-check` e `make lint`. Esperado: sem erros.
- [ ] **Step 3: Commit** `feat: role common`.

### Task 4: Role `users` (UID/GID propagados)

**Files:**
- Create: `ansible/roles/users/tasks/main.yml`, `ansible/playbooks/users.yml`, `ansible/group_vars/users.example.yml`
- Test: `make lint`; verificação em hardware (Step 3)

**Interfaces:**
- Consumes: lista `cluster_users: [{name, uid, gid, ssh_pubkey?}]` e `lab_user/lab_uid/lab_gid`.
- Produces: contas com UID/GID idênticos em todos os hosts; no headnode cria a conta e `/home/<user>`; nos nós só a conta (home via NFS). Falha com mensagem se o usuário existe com UID diferente (Review Focus 5).

- [ ] **Step 1: Role** com `ansible.builtin.group`/`user` e uma verificação prévia (`getent passwd`) que aborta se UID divergir.
- [ ] **Step 2: Lint e syntax-check.** Esperado: sem erros.
- [ ] **Step 3: Verificar no cluster:** rodar duas vezes `playbooks/users.yml`; segunda execução com `changed=0`; `id <user>` igual em todos.
- [ ] **Step 4: Commit** `feat: role users`.

### Task 5: Role `munge`

**Files:**
- Create: `ansible/roles/munge/tasks/main.yml`, `ansible/roles/munge/handlers/main.yml`

**Interfaces:**
- Produces: `munge` ativo em todos os hosts com a mesma `/etc/munge/munge.key` (modo 0400, dono `munge`). A chave é gerada uma vez no headnode (`creates:`) e copiada aos nós via `fetch`/`copy`, nunca versionada.

- [ ] **Step 1: Role** com geração idempotente (`dd`/`create-munge-key` com `creates:`) e distribuição.
- [ ] **Step 2: Lint.** Esperado: sem erros.
- [ ] **Step 3: Verificar:** `munge -n | ssh <nó> unmunge` retorna `STATUS: Success`.
- [ ] **Step 4: Commit** `feat: role munge`.

### Task 6: Roles `nfs_server` e `nfs_client`

**Files:**
- Create: `ansible/roles/nfs_server/tasks/main.yml`, `ansible/roles/nfs_client/tasks/main.yml`

**Interfaces:**
- Consumes: variável `nfs_subnet` (CIDR da LAN).
- Produces: headnode exporta `/home` para `nfs_subnet`; nós montam `/home` (mount em `fstab`, `_netdev`). Sem `/opt` nem scratch via NFS.

- [ ] **Step 1: Roles** (`nfs-kernel-server`, `exports` via `lineinfile`, `ansible.posix.mount`).
- [ ] **Step 2: Lint.**
- [ ] **Step 3: Verificar:** arquivo criado no headnode em `/home/lab-hpc` aparece em um nó.
- [ ] **Step 4: Commit** `feat: roles nfs`.

### Task 7: Role `nvidia` (driver + CUDA)

**Files:**
- Create: `ansible/roles/nvidia/tasks/main.yml`, `ansible/roles/nvidia/defaults/main.yml`

**Interfaces:**
- Consumes: `gpu_supported` (de `host_vars`), `nvidia_driver_version`, `cuda_version` (fixos em `group_vars/all.yml`).
- Produces: nos hosts com `gpu_supported: true`, driver + CUDA toolkit via repositório NVIDIA; nos demais, a role faz `debug` de aviso e termina sem alterar nada (Review Focus 1 e 2).

- [ ] **Step 1: Role** com `when: gpu_supported | default(false)`.
- [ ] **Step 2: Lint.**
- [ ] **Step 3: Verificar:** `nvidia-smi` lista as GPUs nos nós suportados; nó sem suporte reporta `skipped`.
- [ ] **Step 4: Commit** `feat: role nvidia`.

### Task 8: Role `openmpi`

**Files:**
- Create: `ansible/roles/openmpi/tasks/main.yml`

**Interfaces:**
- Produces: OpenMPI com PMIx em todos os nós de computação (e no headnode, para compilar). Verificação `ompi_info | grep -i pmix` retornando suporte.

- [ ] **Step 1: Role** (pacote Ubuntu `openmpi-bin libopenmpi-dev`; se `ompi_info` não mostrar PMIx, a task falha com mensagem apontando para compilação).
- [ ] **Step 2: Lint.**
- [ ] **Step 3: Commit** `feat: role openmpi`.

### Task 9: Roles `mariadb` e `slurmdbd`

**Files:**
- Create: `ansible/roles/mariadb/tasks/main.yml`, `ansible/roles/slurmdbd/tasks/main.yml`, `ansible/roles/slurmdbd/templates/slurmdbd.conf.j2`, `ansible/roles/mariadb/tasks/backup.yml`

**Interfaces:**
- Consumes: `slurmdbd_db_password` (de arquivo local ignorado pelo git, ex.: `secrets/slurmdbd.yml`).
- Produces: banco `slurm_acct_db`, usuário `slurm`, `slurmdbd` ativo; cron semanal `mysqldump` com rotação de 4 cópias em `/var/backups/slurm-db/`.

- [ ] **Step 1: Roles** (`mariadb-server`, `community.mysql` para db/usuário, template do slurmdbd.conf 0600).
- [ ] **Step 2: Lint.**
- [ ] **Step 3: Verificar:** `systemctl is-active slurmdbd` = `active`; `ls /var/backups/slurm-db` após rodar o cron manualmente.
- [ ] **Step 4: Commit** `feat: mariadb, slurmdbd e backup`.

### Task 10: Templates do Slurm (`slurm.conf`, `gres.conf`, `cgroup.conf`)

**Files:**
- Create: `ansible/roles/slurm/templates/slurm.conf.j2`, `gres.conf.j2`, `cgroup.conf.j2`, `tests/test_templates.py`, `tests/fixtures/inventory_vars.yml`
- Test: `tests/test_templates.py`

**Interfaces:**
- Consumes: por nó em `compute`: `cpus`, `sockets`, `cores_per_socket`, `threads_per_core`, `real_memory_mb`, `gpus`, `gpu_supported` (Task 2).
- Produces: `slurm.conf` com `SlurmctldHost`=headnode, `AccountingStorageType=accounting_storage/slurmdbd`, `GresTypes=gpu`, uma linha `NodeName=...` por nó (com `Gres=gpu:<type>:<n>` só se `gpu_supported`), `PartitionName=cpu` (todos os nós de computação) e `PartitionName=gpu` (apenas nós com `gpu_supported`); nenhuma linha de nó para o headnode. `gres.conf` com `AutoDetect=nvml` e `Type` por modelo.

- [ ] **Step 1: Testes que falham** (render com `jinja2` e fixture de 3 nós): `test_headnode_fora_dos_nos`; `test_gres_apenas_gpu_suportada`; `test_particao_gpu_so_nos_com_gpu`; `test_type_normalizado_na_linha_gres`; `test_nó_sem_gpu_so_na_particao_cpu`.
- [ ] **Step 2: Rodar** `pytest tests/test_templates.py -v`. Esperado: FAIL.
- [ ] **Step 3: Escrever os templates** a partir dos asserts do Step 1.
- [ ] **Step 4: Rodar** os testes. Esperado: PASS.
- [ ] **Step 5: Commit** `feat: templates do Slurm`.

### Task 11: Role `slurm` (pacote) e `slurm_build` (fallback)

**Files:**
- Create: `ansible/roles/slurm/tasks/main.yml`, `ansible/roles/slurm/handlers/main.yml`, `ansible/roles/slurm_build/tasks/main.yml`, `ansible/playbooks/slurm.yml`

**Interfaces:**
- Consumes: Task 10 (templates), Tasks 5 e 9, `slurm_install_method`.
- Produces: `slurmctld` no headnode, `slurmd` nos nós, comandos cliente no headnode. Passo de checagem: `slurmd -V` e `srun --mpi=list` contendo `pmix`; `slurmd -C` roda sem erro. Se o pacote não tiver PMIx/NVML, a role falha com instrução para `slurm_install_method: build`. `slurm_build` compila (PMIx + NVML), instala em `/usr/local` e cria units systemd.

- [ ] **Step 1: Roles e playbook** (templates com `validate:` quando existir, handlers de restart).
- [ ] **Step 2: Lint e syntax-check.**
- [ ] **Step 3: Verificar no cluster:** `sinfo` mostra `cpu` e `gpu` com nós `idle`; `scontrol show node <nó>` mostra `Gres=`.
- [ ] **Step 4: Commit** `feat: roles slurm`.

### Task 12: `site.yml` e adicionar nó

**Files:**
- Create: `ansible/playbooks/site.yml`, `ansible/playbooks/add-node.yml`, `scripts/preflight.sh`

**Interfaces:**
- Consumes: todas as roles acima.
- Produces: `site.yml` na ordem common → users → nfs → munge → nvidia → openmpi → mariadb → slurmdbd → slurm. `add-node.yml -e node=<nome>` roda o subconjunto para um nó novo e relê a config. `preflight.sh <nó>` checa SSH, sudo sem senha, internet e `nvidia-smi`.

- [ ] **Step 1: Playbooks e script.**
- [ ] **Step 2: Lint e syntax-check** de ambos.
- [ ] **Step 3: Verificar:** segunda execução de `site.yml` com `changed=0` (Review Focus 4).
- [ ] **Step 4: Commit** `feat: site.yml, add-node e preflight`.

### Task 13: Exemplos de jobs

**Files:**
- Create: `examples/mpi_hello.c`, `examples/mpi_hello.sbatch`, `examples/gpu_smoke.sbatch`, `examples/cuda_vecadd.cu`, `examples/cuda_vecadd.sbatch`, `examples/README.md`

**Interfaces:**
- Produces: jobs que rodam por `sbatch` do headnode: MPI com `srun --mpi=pmix`, `nvidia-smi` via `--gres=gpu:1`, soma de vetores CUDA compilada com `-arch` explícito (nunca `-march=native`).

- [ ] **Step 1: Escrever exemplos.**
- [ ] **Step 2: Verificar no cluster:** cada `sbatch` termina com `COMPLETED` em `sacct`.
- [ ] **Step 3: Commit** `docs: exemplos de jobs`.

### Task 14: Documentação em português e publicação

**Files:**
- Create/Modify: `README.md`, `docs/00-visao-geral.md`, `docs/01-preparo-manual.md`, `docs/02-automacao-ansible.md`, `docs/03-operacao.md`, `docs/04-troubleshooting.md`

**Interfaces:**
- Consumes: todas as tasks. Cada etapa Ansible tem o equivalente manual explicado (o dono é iniciante).
- Produces: fase 0 (criar `lab-hpc`, IP fixo/`/etc/hosts`, SSH por chave, sudo sem senha, instalar Ansible), fase 1, fase 2 (criar usuário, adicionar nó com `discover.py` + `add-node.yml`), troubleshooting (munge, relógio, NFS, GRES, `sinfo` com nó `down`).

- [ ] **Step 1: Escrever as páginas** e o mapa no `README.md`.
- [ ] **Step 2: Verificar** links relativos (`grep -r "](" docs README.md`, todos apontando para arquivos existentes).
- [ ] **Step 3: Commit** `docs: guia completo`.
- [ ] **Step 4: Publicar no GitHub** só depois de confirmação explícita do dono (ação externa): `gh repo create slurm-cluster --public --source . --push`.

---

## Self-review

- **Cobertura do spec:** fases 0/1/2 → Tasks 14/3–12/12–14; slurmdbd → 9; headnode sem slurmd → 10/11; só `/home` NFS → 6; GPU não suportada → 2/7/10; descoberta → 2; segredos fora do git → 1/5/9; Slurm pacote ou build → 11; backup → 9; exemplos → 13.
- **Consistência:** `gpu_supported`, `gpus[].type`, `real_memory_mb` e `cores_per_socket` definidos na Task 2 e usados nas 7 e 10; `slurm_install_method` definido na 1 e usado na 11.
- **Proporção:** roles são verificadas por lint, syntax-check e execução real; só descoberta (Task 2) e templates (Task 10) têm testes unitários, por serem lógica pura.
