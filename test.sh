#!/bin/bash
#SBATCH --job-name=test
#SBATCH --partition=defq
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=10:00
#SBATCH --mem-per-cpu=100

srun hostname
echo ARCH = $CPU_ARCH
echo TMPDIR = $TMPDIR

echo OMP_NUM_THREADS $OMP_NUM_THREADS
echo SLURM_CPUS_PER_TASK $SLURM_CPUS_PER_TASK
echo SLURM_CPUS_ON_NODE $SLURM_CPUS_ON_NODE

module load miniconda
cd $TMPDIR

#Copy input data to scratch and create output directory
#cp -r $HOME/Documents/RGCPD "$TMPDIR"

#Run program
#python Code_Lennart/call_cts.py cluster

#Copy output data from scratch to home
#cp -r "$TMPDIR"/RGCPD/Code_Lennart/results $HOME/Documents/RGCPD_output