# Visão geral

## Peças e o que cada uma faz

| Peça | Onde | Para quê |
|---|---|---|
| munge | todos | autentica mensagens entre os daemons do Slurm (mesma chave em todos) |
| NFS | headnode exporta `/home` | o job enxerga os arquivos do usuário em qualquer nó |
| slurmctld | headnode | agenda os jobs |
| slurmd | nós | executa os jobs |
| MariaDB + slurmdbd | headnode | guarda o histórico (`sacct`), contas e limites |
| driver NVIDIA + CUDA | nós com GPU | permite usar a GPU |
| OpenMPI + PMIx | todos | `srun --mpi=pmix` lança ranks MPI |

## Decisões

- **Ansible**, rodando do headnode via SSH: sem agente nos nós, re-executar é seguro, e nó novo é uma linha no inventário.
- **Só `/home` por NFS**; driver, CUDA e OpenMPI instalados localmente em cada nó; scratch local.
- **UID/GID idênticos** em todas as máquinas (senão o NFS mostra donos errados).
- **GPU antiga demais** para o driver escolhido: o nó fica só com CPU e um aviso é exibido.
- **Rede** assumida 1 GbE; sem ajuste fino de MPI/NFS por enquanto.
