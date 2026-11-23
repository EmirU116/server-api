# Ubuntu developer accounts (Bash, SSH, ACL)

Run the account script from the reviewed deployment checkout as the EC2
administrator. Install the Ubuntu `acl` package if it is missing:

```bash
sudo apt-get install -y acl
sudo bash scripts/setup/provision_ubuntu_user.sh Emir "senior developer"
sudo bash scripts/setup/provision_ubuntu_user.sh Alice "junior developer"
```

The script creates the Linux logins `emir` and `alice` with private home
directories, locked passwords and the selected project groups. You can rerun
the same command for an account in the same role. If a login already belongs
to another role or an unrelated account, the script stops. Ask the server
administrator to review an existing account before making a role change.

| Role | `/srv/serverwatch/dev` | `/srv/serverwatch/prod` |
| --- | --- | --- |
| Junior developer | Read and write | Read and traverse |
| Senior developer | Read and write | Read and write |

The managed directories inherit their group and access rules for new files.
Use `prod` for approved project files only. Verify the resulting permissions
after moving existing files or copying files while preserving their modes.
The script leaves the deployment checkout, services and private configuration
in the original setup account's home. System administration, sudo, Docker
and access to deployment credentials remain with the server administrator.
Launch an agent under its own junior account if it needs these same group
permissions. The ACLs govern these two workspaces. System-wide confinement
requires an operating system sandbox or a separate instance.

## Give each student SSH access

Each student keeps their private key on their computer and gives the EC2
administrator only their public key. Repeat these steps for each account,
substituting the correct login and adding only that student's public key:

```bash
sudo install -d -o alice -g alice -m 700 /home/alice/.ssh
sudo -u alice nano /home/alice/.ssh/authorized_keys
sudo chmod 600 /home/alice/.ssh/authorized_keys
```

In a separate local terminal, connect using the matching private key:

```bash
ssh -i ~/.ssh/your-key alice@EC2_PUBLIC_IP
id
```

## Verify effective access

From the administrator's SSH session, inspect group membership and run
permission checks as the new users. Each `test` command exits successfully
when the expected access matches.

```bash
id alice
id emir
getfacl /srv/serverwatch/dev /srv/serverwatch/prod
sudo -u alice test -w /srv/serverwatch/dev
sudo -u alice test -r /srv/serverwatch/prod
sudo -u alice test ! -w /srv/serverwatch/prod
sudo -u emir test -w /srv/serverwatch/prod
```

For the assignment, also show both students connecting from their computers.
Explain how giving each person a distinct account allows the OS to apply the
correct project group. [EC2 rehearsal guide](ec2-manual-setup.md)
