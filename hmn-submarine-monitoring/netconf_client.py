#!/usr/bin/env python3
"""
HMN Submarine Monitoring - NetConf/YANG Client
Implementação para configuração e monitorização via NetConf com YANG models
"""
import ncclient
from ncclient import manager
from ncclient.xml_ import to_xml
from typing import Dict, List, Optional, Any
import xmltodict
from datetime import datetime

class NetConfCredentials:
    """Credenciais NetConf"""
    def __init__(self, username: str = "admin", password: str = "admin", 
                 port: int = 830, hostkey_verify: bool = False):
        self.username = username
        self.password = password
        self.port = port
        self.hostkey_verify = hostkey_verify

class NetConfClient:
    """Cliente NetConf para equipamentos HMN"""
    
    # YANG models padrão para equipamentos de rede
    YANG_NAMESPACES = {
        'ietf-netconf': 'urn:ietf:params:xml:ns:netconf:base:1.0',
        'ietf-interfaces': 'urn:ietf:params:xml:ns:yang:ietf-interfaces',
        'ietf-ip': 'urn:ietf:params:xml:ns:yang:ietf-ip',
        'itu-t-g-8000': 'urn:itu:params:xml:ns:yang:itu-t-g-8000',
    }
    
    def __init__(self, host: str, credentials: Optional[NetConfCredentials] = None):
        self.host = host
        self.credentials = credentials or NetConfCredentials()
        self.connection = None
        
    def connect(self) -> bool:
        """Estabelece ligação NetConf"""
        try:
            self.connection = manager.connect(
                host=self.host,
                port=self.credentials.port,
                username=self.credentials.username,
                password=self.credentials.password,
                hostkey_verify=self.credentials.hostkey_verify,
                device_params={'name': 'default'}
            )
            return True
        except Exception as e:
            print(f"Erro na ligação NetConf: {e}")
            return False
    
    def disconnect(self):
        """Fecha ligação"""
        if self.connection:
            self.connection.close_session()
            self.connection = None
    
    def get_capabilities(self) -> List[str]:
        """Obtém capabilities do dispositivo"""
        if not self.connection:
            self.connect()
        return list(self.connection.server_capabilities) if self.connection else []
    
    def get_config(self, source: str = 'running') -> Optional[Dict]:
        """Obtém configuração atual"""
        if not self.connection:
            self.connect()
        
        try:
            config = self.connection.get_config(source=source)
            return xmltodict.parse(str(config))
        except Exception as e:
            print(f"Erro ao obter config: {e}")
            return None
    
    def get_interfaces(self) -> Optional[Dict]:
        """Obtém estado das interfaces via YANG model"""
        if not self.connection:
            self.connect()
        
        filter_xml = """
        <filter>
          <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface/>
          </interfaces>
        </filter>
        """
        
        try:
            result = self.connection.get(filter=filter_xml)
            return xmltodict.parse(str(result))
        except Exception as e:
            print(f"Erro ao obter interfaces: {e}")
            return None
    
    def edit_config(self, config_xml: str, target: str = 'running') -> bool:
        """Aplica configuração"""
        if not self.connection:
            self.connect()
        
        try:
            self.connection.edit_config(target=target, config=config_xml)
            return True
        except Exception as e:
            print(f"Erro ao aplicar config: {e}")
            return False
    
    def subscribe_to_changes(self, xpath: str, callback):
        """Subscreve notificações de mudanças (se suportado)"""
        # Implementação simplificada - na prática usaria NetConf notifications
        pass

def monitor_hmn_submarine(host: str, username: str = "admin", 
                          password: str = "admin") -> Dict:
    """Monitoriza equipamento submarino via NetConf"""
    creds = NetConfCredentials(username=username, password=password)
    client = NetConfClient(host, creds)
    
    result = {
        'host': host,
        'timestamp': datetime.now().isoformat(),
        'connected': False,
        'capabilities': [],
        'interfaces': None,
        'config': None
    }
    
    if client.connect():
        result['connected'] = True
        result['capabilities'] = client.get_capabilities()
        result['interfaces'] = client.get_interfaces()
        result['config'] = client.get_config()
        client.disconnect()
    
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        host = sys.argv[1]
        username = sys.argv[2] if len(sys.argv) > 2 else "admin"
        password = sys.argv[3] if len(sys.argv) > 3 else "admin"
        
        result = monitor_hmn_submarine(host, username, password)
        print(f"Monitorização NetConf HMN para {host}:")
        print(f"Ligação: {'✓' if result['connected'] else '✗'}")
        print(f"Capabilities: {len(result['capabilities'])} suportadas")
        if result['interfaces']:
            print(f"Interfaces monitorizadas")
    else:
        print("Uso: python netconf_client.py <host> [username] [password]")
