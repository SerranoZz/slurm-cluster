#!/bin/bash
#SBATCH --job-name=mpi_hello
#SBATCH --partition=cpu
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=4
#SBATCH --output=mpi_hello-%j.out

# Compilado sem -march=native: as CPUs dos nós são diferentes.
mpicc -O2 -o mpi_hello mpi_hello.c
srun --mpi=pmix ./mpi_hello
