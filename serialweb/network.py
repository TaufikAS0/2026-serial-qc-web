"""Explicit per-machine LAN opt-in; portable installation defaults to loopback."""
import ipaddress
import json


def validate_network(host, subnet):
    address = ipaddress.IPv4Address(host)
    network = ipaddress.IPv4Network(subnet, strict=False)
    private_ranges = [ipaddress.IPv4Network(cidr) for cidr in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')]
    if not any(address in item and network.subnet_of(item) for item in private_ranges) or address not in network or network.prefixlen < 16:
        raise ValueError('LAN harus IPv4 privat RFC1918 dengan subnet /16 atau lebih kecil')
    return {'host': str(address), 'subnet': str(network)}


def load_network(directory):
    path = directory / 'network.json'
    if not path.exists():
        return None
    config = json.loads(path.read_text(encoding='utf-8'))
    return validate_network(config['host'], config['subnet'])


def save_network(directory, host, subnet):
    config = validate_network(host, subnet)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / 'network.tmp'
    temporary.write_text(json.dumps(config), encoding='utf-8')
    temporary.replace(directory / 'network.json')
    return config


def allowed_peer(address, network):
    try:
        peer = ipaddress.ip_address(address)
        return peer.is_loopback or (network is not None and peer in ipaddress.ip_network(network['subnet']))
    except ValueError:
        return False
