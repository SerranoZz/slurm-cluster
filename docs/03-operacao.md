# Fase 2: operação

## Criar um usuário

Edite `ansible/group_vars/users.yml` (UID/GID únicos) e rode:

```bash
ansible-playbook playbooks/users.yml
sudo sacctmgr add account lab Description="Laboratório"      # uma vez
sudo sacctmgr add user <nome> Account=lab
```

Se o usuário já existe em algum nó com UID diferente, o playbook para com mensagem clara. Corrija a conta antes.

## Adicionar um nó

1. Faça a [fase 0](01-preparo-manual.md) no nó novo e rode `scripts/preflight.sh <IP>`.
2. Adicione o nó em `ansible/inventory/hosts.yml`, grupo `compute`.
3. Gere `host_vars/<nó>.yml` com `discover.py`.
4. `ansible-playbook playbooks/add-node.yml -e node=<nó>`.
5. `sinfo` deve mostrar o nó em `idle`.

## Testar

Veja [examples/](../examples/README.md).

## Backup do banco

Semanal, domingo 03:00, em `/var/backups/slurm-db/` (4 cópias).
