# Quick Start Guide - VM Demo

Get the distributed chat system running on 3 VMs in under 15 minutes!

## Prerequisites

Install these first:
- [VirtualBox](https://www.virtualbox.org/wiki/Downloads) (6.1+)
- [Vagrant](https://www.vagrantup.com/downloads) (2.3+)

## Steps

### 1. Start VMs (5-10 minutes first time)

```bash
cd deployment/demo
vagrant up
```

Coffee break ☕ - this downloads Ubuntu and sets up 3 VMs with Docker Swarm.

### 2. Deploy Chat System (2-3 minutes)

```bash
./scripts/deploy-demo.sh
```

This builds the image and deploys to the Swarm cluster.

### 3. Connect!

⏱️ **Wait 30-60 seconds** for services to fully start after deployment.

Access points (thanks to Swarm's routing mesh, use ANY IP):
- http://192.168.56.101:8081 ✅ Recommended
- http://192.168.56.102:8081
- http://192.168.56.103:8081

From project root, run the client:

```bash
poetry run chat-client
```

Connect to `192.168.56.101:8081`.

## Verify It's Working

Check all services are running:

```bash
vagrant ssh node1 -c "docker stack ps chat-demo"
```

You should see 3 services, each on a different VM!

## View Logs

```bash
vagrant ssh node1 -c "docker service logs -f chat-demo_node1"
```

## Stop Everything

```bash
vagrant halt
```

## Clean Up Completely

```bash
vagrant destroy -f
```

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Try failure scenarios (stop a VM, see what happens!)
- Review production deployment in `../docs/DEPLOYMENT.md`

## Troubleshooting

**See WebSocket errors in logs?**
Errors like "EOFError", "426 Upgrade Required", or "missing Connection header" are NORMAL. They're from Docker health checks hitting the WebSocket port. Ignore them - the server is working fine!

**Connection refused on port 8081?**
- Wait 30-60 seconds after deployment for services to start
- Run: `./scripts/troubleshoot-connectivity.sh` for detailed diagnostics
- Check logs: `vagrant ssh node1 -c "docker service logs chat-demo_node1"`

**VMs won't start?**
- Check VirtualBox is installed: `VBoxManage --version`
- Ensure you have 8GB RAM available

**Services not deploying?**
- Check Swarm: `vagrant ssh node1 -c "docker node ls"`
- Check tasks: `vagrant ssh node1 -c "docker stack ps chat-demo"`

**Error: "No such image: chat-node:demo"?**
This means images weren't distributed to all nodes.
1. Remove stack: `vagrant ssh node1 -c "docker stack rm chat-demo"`
2. Wait 10 seconds
3. Re-run: `./scripts/deploy-demo.sh` (it will fix the distribution)

**Still having issues?**
Run the troubleshooting script:
```bash
./scripts/troubleshoot-connectivity.sh
```

## Help

Full documentation: [README.md](README.md)
