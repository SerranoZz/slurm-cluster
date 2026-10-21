# Repositório slurm-cluster: design

## Intenção

Repositório público (GitHub) que ensina e automatiza a montagem de um cluster Slurm num laboratório: passo a passo documentado, mais playbooks Ansible que instalam tudo em todas as máquinas da rede. O dono não tem experiência com Ansible; o repo deve ensinar o que cada etapa faz, não só executá-la.

## Contexto (dito pelo usuário)

- 3 PCs de laboratório, Ubuntu (versão mais recente disponível/LTS mais recente, ver "Decisões do builder"), a serem formatados. Mais máquinas serão adicionadas depois.
- Hardware heterogêneo: GPUs NVIDIA de modelos diferentes, CPUs diferentes. Modelos exatos desconhecidos hoje.
- Cargas de trabalho: aplicações MPI em CPU e aplicações CUDA.
- Arquitetura: 1 headnode (controller + login + banco) e demais nós de computação. Usuários logam só no headnode e submetem jobs.
- O headnode já existe e só tem a conta principal do laboratório (`lab-hpc`). O dono criará e propagará as demais contas.
- Nos nós de computação, o `lab-hpc` será criado manualmente, assim como IP fixo, hostnames e SSH por chave a partir do headnode.
- Ubuntu já instalado: instalação do SO **não** entra na documentação.
- slurmdbd (accounting) entra na v1.
- O headnode **não executa jobs**: só login e submissão (e serviços do cluster). Não roda slurmd.
- Máquinas numa rede local, todas com acesso à internet. Velocidade da rede desconhecida.

## Objetivos

1. Um iniciante segue a doc do zero e chega a um cluster funcionando.
2. Adicionar um nó = editar o inventário e rodar um playbook.
3. Re-executar qualquer playbook é seguro (idempotente).
4. Hardware misto tratado sem edição manual de `slurm.conf`/`gres.conf`: specs por nó em `host_vars/`, gerados por script de descoberta.
5. Usuário comum submete `sbatch`/`srun` do headnode para CPU (MPI) e GPU (CUDA) e consulta `sacct`.

## Não-objetivos

- Instalação/particionamento do Ubuntu.
- Alta disponibilidade (controller de backup), multi-cluster, federação.
- LDAP/AD/SSSD (usuários sincronizados por playbook).
- Containers (Apptainer/Docker), módulos Lmod, monitoramento (Prometheus/Grafana). Possíveis extensões futuras.
- Suporte a outras distros.

## Anti-objetivos (seria falha mesmo funcionando)

- Playbooks que só funcionam se executados uma vez, ou que exigem editar arquivos gerados.
- Etapas "mágicas" sem explicação de o que e por que.
- Binários MPI/CUDA que quebram em CPUs/GPUs diferentes (por exemplo `-march=native`).
- Job de usuário rodando no headnode.
- Segredos (chave munge, senha do banco) commitados no repo.

## Arquitetura

| Papel | Serviços |
|---|---|
| Headnode | slurmctld, slurmdbd, MariaDB, munge, servidor NFS, login e submissão dos usuários (sem slurmd) |
| Nós de computação | slurmd, munge, cliente NFS, driver NVIDIA, CUDA, OpenMPI |

- **Armazenamento:** só `/home` exportado pelo headnode via NFS e montado nos nós. Driver, CUDA e OpenMPI instalados localmente em cada nó (decisão do autor). Scratch local por nó, não NFS (decisão do autor).
- **Identidade:** mesmos UID/GID em todas as máquinas. Playbook de usuário cria a conta no headnode e propaga com UID/GID idênticos aos nós.
- **Autenticação do Slurm:** munge, chave única gerada uma vez e distribuída pelo playbook, fora do git.
- **MPI:** OpenMPI com integração Slurm/PMIx, de modo que `srun` lance ranks MPI.
- **GPU:** driver NVIDIA + CUDA em versão única para todos os nós; GRES com autodetecção NVML e `Type=` por modelo (`--gres=gpu:<modelo>:1`). Se uma GPU for antiga demais para o driver escolhido, o preflight avisa, o nó segue só com CPU (sem driver/GRES de GPU) e o dono revê depois (decisão do usuário).
- **Partições:** `cpu` e `gpu`, somente nos nós de computação.
- **Accounting:** slurmdbd + MariaDB, com contas/associações e QOS básicos; `sacct` funcional.

## Estrutura proposta do repo

- `README.md`: visão geral e mapa da doc.
- `docs/`: passo a passo em português, uma página por fase, com a explicação do equivalente manual de cada etapa.
- `ansible/`: `inventory/`, `group_vars/`, `host_vars/`, `playbooks/`, `roles/`.
- `scripts/`: descoberta de hardware (gera `host_vars` a partir de `slurmd -C` e `nvidia-smi -L`) e preflight.
- `examples/`: jobs de teste (MPI hello, `nvidia-smi` via GRES, CUDA simples).

## Fases

0. **Preparo manual (doc):** `lab-hpc`, IP fixo/`/etc/hosts`, SSH por chave do headnode, sudo sem senha, instalação do Ansible no headnode.
1. **Automação (Ansible):** base e chrony, munge, NFS, NVIDIA/CUDA, OpenMPI+PMIx, MariaDB, slurmdbd, slurmctld/slurmd, geração de `slurm.conf`/`gres.conf`.
2. **Operação:** criar/propagar usuário, adicionar nó, jobs de teste, troubleshooting.

## Decisões do usuário

- Ferramenta: Ansible foi proposta e aceita (usuário pediu "a melhor pro meu contexto").
- Doc em português (aceita ao ler o desenho; não contestada).
- slurmdbd na v1.
- Headnode só login/submissão, sem partição própria.
- GPU não suportada: nó segue só com CPU.
- Rede local com internet nos nós; nós podem instalar pacotes direto (apt/repo NVIDIA).
- Caminho local: `~/Documents/slurm-cluster`; destino: GitHub.

## Decisões do autor do design (revisar)

- Slurm do pacote Ubuntu se tiver PMIx e NVML; senão compilar (role separado).
- Ubuntu: versão estável mais recente.
- UID/GID: nós replicam o do `lab-hpc` já existente no headnode.
- Repo público: só `inventory.example` / `host_vars.example` versionados; arquivos reais no `.gitignore`. Segredos em arquivos locais ignorados, sem Vault na v1.
- Banco: `mysqldump` semanal com rotação simples.
- Rede assumida 1 GbE até medir; sem ajuste fino de MPI/NFS na v1.

## Deixado ao builder

- Versão do Slurm (pacote Ubuntu vs. compilação), versões exatas de driver NVIDIA/CUDA/OpenMPI.
- Layout interno de roles, nomes de variáveis, nomes de partições além dos citados.
- Estratégia de segredos (por exemplo Ansible Vault ou arquivos locais ignorados no git).
- Escolha entre `/opt` e scratch via NFS, tamanhos de limites e QOS padrão.
- Testes: lint (ansible-lint/yamllint) e, se possível, verificação em VM/Molecule; testes em hardware real feitos pelo dono.
