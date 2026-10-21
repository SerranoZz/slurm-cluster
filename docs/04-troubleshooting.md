# Troubleshooting

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| nó `down` ou `drain` no `sinfo` | slurmd parado ou config divergente | `ssh nó systemctl status slurmd`; `scontrol show node nó` mostra `Reason`; depois `scontrol update nodename=nó state=resume` |
| `Invalid credential` / erros do munge | chaves diferentes ou relógio fora de hora | `md5sum /etc/munge/munge.key` igual em todos; `chronyc tracking`; `munge -n \| ssh nó unmunge` |
| `/home` vazio no nó | NFS não montou | `showmount -e head01`; `sudo mount -a`; firewall liberando a sub-rede |
| arquivos com dono numérico | UID/GID diferentes entre máquinas | `id <user>` em todas; corrigir e rodar `users.yml` |
| `--gres=gpu` rejeitado | nó sem `gpu_supported` ou driver ausente | `nvidia-smi` no nó; `scontrol show node nó \| grep Gres`; regenere `host_vars` |
| `srun --mpi=pmix` falha | Slurm sem PMIx | `srun --mpi=list`; use `slurm_install_method: build` |
| `sacct` vazio | slurmdbd parado ou sem conta | `systemctl status slurmdbd`; `sacctmgr show cluster` |
