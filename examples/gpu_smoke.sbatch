#!/bin/bash
#SBATCH --job-name=gpu_smoke
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --output=gpu_smoke-%j.out

# Para pedir um modelo específico: --gres=gpu:rtx_3090:1
nvidia-smi
