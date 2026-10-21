# slurm-cluster

Guia passo a passo e automação (Ansible) para montar um cluster **Slurm** em PCs de laboratório com **Ubuntu**, com jobs MPI (CPU) e CUDA (GPU NVIDIA) e accounting (`slurmdbd`).

## Como o cluster é

- 1 **headnode**: login, submissão, `slurmctld`, `slurmdbd`, MariaDB, servidor NFS. Não roda jobs.
- N **nós de computação**: `slurmd`, driver NVIDIA, CUDA, OpenMPI. Hardware pode ser misto.
- Usuários entram só no headnode; `/home` é compartilhado por NFS.

## Mapa da documentação

1. [Visão geral](docs/00-visao-geral.md)
2. [Preparo manual (fase 0)](docs/01-preparo-manual.md)
3. [Automação com Ansible (fase 1)](docs/02-automacao-ansible.md)
4. [Operação do dia a dia (fase 2)](docs/03-operacao.md)
5. [Troubleshooting](docs/04-troubleshooting.md)
6. [Exemplos de jobs](examples/README.md)

## Estrutura

- `ansible/`: inventário, variáveis, playbooks e roles.
- `scripts/`: `discover.py` (descobre hardware), `preflight.sh` (checa um nó).
- `examples/`: jobs de teste.
- `tests/`: testes do script de descoberta e dos templates (`make test`); `make lint` roda yamllint e ansible-lint.
