#!/usr/bin/env python3
"""
HMN Submarine Monitoring - SNMP Poller
Implementação baseada em pysnmp para monitorização de equipamentos submarinos
"""
from pysnmp.hlapi import *
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

class SNMPCredentials:
    """Credenciais SNMP"""
    def __init__(self, community: str = "public", version: int = 2):
        self.community = community
        self.version = version

class SNMPPoller:
    """Poller SNMP para monitorização HMN"""
    
    # OIDs padrão para equipamentos de rede submarina
    OIDS = {
        'sysDescr': '1.3.6.1.2.1.1.1.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysName': '1.3.6.1.2.1.1.5.0',
        'ifNumber': '1.3.6.1.2.1.2.1.0',
        'ifOperStatus': '1.3.6.1.2.1.2.2.1.8',
        'ifInErrors': '1.3.6.1.2.1.2.2.1.14',
        'ifOutErrors': '1.3.6.1.2.1.2.2.1.20',
    }
    
    def __init__(self, host: str, credentials: Optional[SNMPCredentials] = None):
        self.host = host
        self.credentials = credentials or SNMPCredentials()
        
    def get_single(self, oid: str) -> Optional[str]:
        """Get single OID value"""
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(self.credentials.community, mpModel=self.credentials.version-1),
            UdpTransportTarget((self.host, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )
        
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        
        if errorIndication:
            print(f"Error: {errorIndication}")
            return None
        elif errorStatus:
            print(f"Error: {errorStatus.prettyPrint()}")
            return None
        else:
            for varBind in varBinds:
                return str(varBind[1])
        return None
    
    def get_bulk(self, oids: List[str]) -> Dict[str, str]:
        """Get multiple OIDs"""
        results = {}
        for oid_name, oid_value in self.OIDS.items() if oids == ['all'] else {o: self.OIDS[o] for o in oids if o in self.OIDS}.items():
            results[oid_name] = self.get_single(oid_value)
        return results
    
    def check_interface_health(self, if_index: int) -> Dict:
        """Verifica saúde da interface"""
        status_oid = f"1.3.6.1.2.1.2.2.1.8.{if_index}"
        in_errors_oid = f"1.3.6.1.2.1.2.2.1.14.{if_index}"
        out_errors_oid = f"1.3.6.1.2.1.2.2.1.20.{if_index}"
        
        return {
            'interface': if_index,
            'status': self.get_single(status_oid),
            'in_errors': self.get_single(in_errors_oid),
            'out_errors': self.get_single(out_errors_oid),
            'timestamp': datetime.now().isoformat()
        }

def monitor_submarine_equipment(host: str, community: str = "public") -> Dict:
    """Monitoriza equipamento submarino via SNMP"""
    poller = SNMPPoller(host, SNMPCredentials(community))
    
    # Recolhe informações básicas
    basic_info = poller.get_bulk(['all'])
    
    # Verifica interfaces (assumindo índices 1-10 para equipamentos submarinos)
    interfaces = []
    for i in range(1, 11):
        health = poller.check_interface_health(i)
        if health['status'] is not None:
            interfaces.append(health)
    
    return {
        'host': host,
        'timestamp': datetime.now().isoformat(),
        'basic_info': basic_info,
        'interfaces': interfaces
    }

if __name__ == "__main__":
    # Exemplo de uso
    import sys
    if len(sys.argv) > 1:
        host = sys.argv[1]
        result = monitor_submarine_equipment(host)
        print(f"Monitorização HMN para {host}:")
        print(f"Info: {result['basic_info']}")
        print(f"Interfaces: {len(result['interfaces'])} monitorizadas")
    else:
        print("Uso: python snmp_poller.py <host>")
        print("Exemplo: python snmp_poller.py 192.168.1.100")
