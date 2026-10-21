#!/bin/bash
#SBATCH --job-name=cuda_vecadd
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --output=cuda_vecadd-%j.out

# -arch=native compila para a GPU do nó que roda o job (GPUs diferentes entre nós).
export PATH=/usr/local/cuda/bin:$PATH
nvcc -arch=native -o cuda_vecadd cuda_vecadd.cu
./cuda_vecadd
