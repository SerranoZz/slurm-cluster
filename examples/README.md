# Exemplos de jobs

Copie a pasta para o seu `/home` no headnode e rode:

```bash
sbatch mpi_hello.sbatch        # MPI em CPU, 2 nós x 4 tarefas
sbatch gpu_smoke.sbatch        # nvidia-smi via GRES
sbatch cuda_vecadd.sbatch      # soma de vetores em CUDA
squeue                         # fila
sacct -X                       # histórico (slurmdbd)
```

Cada job deve terminar em `COMPLETED` no `sacct`. A saída fica em `*-<jobid>.out`.
