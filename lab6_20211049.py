
"""
SDN Network Access Control Application
Aplicación para control de acceso en red SDN basada en roles
"""

import requests
import json
import yaml
from typing import List, Dict, Optional

class Alumno:
    """Clase para representar un alumno en el sistema"""
    
    def __init__(self, nombre: str, codigo: str, mac: str):
        self.nombre = nombre
        self.codigo = codigo
        self.mac = mac.upper()  # Normalizar MAC a mayúsculas
    
    def __str__(self):
        return f"Alumno: {self.nombre} ({self.codigo}) - MAC: {self.mac}"
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'codigo': self.codigo,
            'mac': self.mac
        }

class Servicio:
    """Clase para representar un servicio en un servidor"""
    
    def __init__(self, nombre: str, protocolo: str, puerto: int):
        self.nombre = nombre
        self.protocolo = protocolo.upper()
        self.puerto = puerto
    
    def __str__(self):
        return f"{self.nombre} ({self.protocolo}:{self.puerto})"
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'protocolo': self.protocolo,
            'puerto': self.puerto
        }

class Servidor:
    """Clase para representar un servidor y sus servicios"""
    
    def __init__(self, nombre: str, ip: str):
        self.nombre = nombre
        self.ip = ip
        self.servicios: List[Servicio] = []
    
    def agregar_servicio(self, servicio: Servicio):
        self.servicios.append(servicio)
    
    def obtener_servicio(self, nombre_servicio: str) -> Optional[Servicio]:
        for servicio in self.servicios:
            if servicio.nombre == nombre_servicio:
                return servicio
        return None
    
    def __str__(self):
        return f"Servidor: {self.nombre} ({self.ip}) - {len(self.servicios)} servicios"
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'ip': self.ip,
            'servicios': [s.to_dict() for s in self.servicios]
        }

class ServidorPermitido:
    """Clase para representar un servidor permitido en un curso con servicios específicos"""
    
    def __init__(self, nombre: str, servicios_permitidos: List[str]):
        self.nombre = nombre
        self.servicios_permitidos = servicios_permitidos
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'servicios_permitidos': self.servicios_permitidos
        }

class Curso:
    """Clase para representar un curso con alumnos y servidores permitidos"""
    
    def __init__(self, codigo: str, nombre: str, estado: str = "INACTIVO"):
        self.codigo = codigo
        self.nombre = nombre
        self.estado = estado.upper()
        self.alumnos: List[str] = []  # Lista de códigos de alumnos
        self.servidores: List[ServidorPermitido] = []
    
    def agregar_alumno(self, codigo_alumno: str):
        if codigo_alumno not in self.alumnos:
            self.alumnos.append(codigo_alumno)
    
    def remover_alumno(self, codigo_alumno: str):
        if codigo_alumno in self.alumnos:
            self.alumnos.remove(codigo_alumno)
    
    def agregar_servidor(self, servidor_permitido: ServidorPermitido):
        self.servidores.append(servidor_permitido)
    
    def alumno_tiene_acceso_servicio(self, codigo_alumno: str, nombre_servidor: str, nombre_servicio: str) -> bool:
        """Verifica si un alumno tiene acceso a un servicio específico de un servidor"""
        # Verificar que el alumno esté en el curso
        if codigo_alumno not in self.alumnos:
            return False
        
        # Verificar que el curso esté activo
        if self.estado != "DICTANDO":
            return False
        
        # Buscar el servidor en la lista de servidores permitidos
        for servidor in self.servidores:
            if servidor.nombre == nombre_servidor:
                return nombre_servicio in servidor.servicios_permitidos
        
        return False
    
    def __str__(self):
        return f"Curso: {self.codigo} - {self.nombre} ({self.estado}) - {len(self.alumnos)} alumnos"
    
    def to_dict(self):
        return {
            'codigo': self.codigo,
            'nombre': self.nombre,
            'estado': self.estado,
            'alumnos': self.alumnos,
            'servidores': [s.to_dict() for s in self.servidores]
        }

class Conexion:
    """Clase para representar una conexión activa entre alumno y servicio"""
    
    def __init__(self, handler: str, codigo_alumno: str, nombre_servidor: str, nombre_servicio: str):
        self.handler = handler
        self.codigo_alumno = codigo_alumno
        self.nombre_servidor = nombre_servidor
        self.nombre_servicio = nombre_servicio
        self.activa = True
    
    def __str__(self):
        estado = "ACTIVA" if self.activa else "INACTIVA"
        return f"Conexión {self.handler}: {self.codigo_alumno} -> {self.nombre_servidor}:{self.nombre_servicio} [{estado}]"