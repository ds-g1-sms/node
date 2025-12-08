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

Access points are ready at:
- http://192.168.56.101:8081
- http://192.168.56.102:8082
- http://192.168.56.103:8083

From project root, run the client:

```bash
poetry run chat-client
```

Connect to `192.168.56.101:8081` (or any of the IPs above).

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

**VMs won't start?**
- Check VirtualBox is installed: `VBoxManage --version`
- Ensure you have 8GB RAM available

**Services not deploying?**
- Check Swarm: `vagrant ssh node1 -c "docker node ls"`
- Check logs: `vagrant ssh node1 -c "docker service logs chat-demo_node1"`

**Can't connect?**
- Verify VMs are running: `vagrant status`
- Check services: `vagrant ssh node1 -c "docker stack services chat-demo"`
- Ensure using correct IP:port in client

## Help

Full documentation: [README.md](README.md)
