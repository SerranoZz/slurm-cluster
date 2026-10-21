# Fase 0: preparo manual

Pré-requisito: Ubuntu já instalado em todas as máquinas. A instalação do SO não é coberta aqui.

Em **cada máquina nova** (nós de computação):

## 1. Usuário `lab-hpc` com o mesmo UID/GID do headnode

No headnode: `id lab-hpc` (anote `uid` e `gid`). Em cada nó:

```bash
sudo groupadd -g <GID> lab-hpc
sudo useradd -m -u <UID> -g <GID> -s /bin/bash lab-hpc
sudo passwd lab-hpc
```

## 2. IP fixo e hostname

Defina IP fixo no roteador (reserva de DHCP) ou via netplan, e o hostname: `sudo hostnamectl set-hostname node01`.

## 3. sudo sem senha para `lab-hpc`

```bash
echo 'lab-hpc ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/lab-hpc
sudo chmod 440 /etc/sudoers.d/lab-hpc
```

## 4. SSH por chave a partir do headnode

No headnode, como `lab-hpc`:

```bash
ssh-keygen -t ed25519        # só na primeira vez
ssh-copy-id lab-hpc@<IP-do-nó>
```

Faça o mesmo **para o próprio headnode**, porque o Ansible também conecta nele por SSH:

```bash
ssh-copy-id lab-hpc@head01          # a partir do próprio head01
echo 'lab-hpc ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/lab-hpc && sudo chmod 440 /etc/sudoers.d/lab-hpc
```

Isso também evita perder o acesso quando o `/home` do headnode for montado nos nós por NFS: o `authorized_keys` passa a ser o do headnode.

## 5. Ansible no headnode

```bash
sudo apt update && sudo apt install -y pipx git
pipx install --include-deps ansible
git clone <url-deste-repo> && cd slurm-cluster
ansible-galaxy collection install -r ansible/requirements.yml
```

## 6. Inventário e conferência

```bash
cp -r ansible/inventory.example ansible/inventory   # edite IPs e nomes
scripts/preflight.sh <IP-do-nó>                       # tudo deve dar OK
```
