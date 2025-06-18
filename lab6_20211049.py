#!/usr/bin/env python3
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

# ============================================================================
# FUNCIONES DE INTERACCIÓN CON FLOODLIGHT CONTROLLER
# ============================================================================

class FloodlightController:
    """Clase para manejar la comunicación con el controlador Floodlight"""
    
    def __init__(self, controller_ip: str = "127.0.0.1", controller_port: int = 8080):
        self.base_url = f"http://{controller_ip}:{controller_port}"
        self.session = requests.Session()
    
    def get_switches(self) -> List[Dict]:
        """Obtiene la lista de switches conectados al controlador"""
        try:
            response = self.session.get(f"{self.base_url}/wm/core/controller/switches/json")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error obteniendo switches: {e}")
            return []
    
    def get_devices(self) -> List[Dict]:
        """Obtiene la lista de dispositivos conectados"""
        try:
            response = self.session.get(f"{self.base_url}/wm/device/")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error obteniendo dispositivos: {e}")
            return []
    
    def get_topology_links(self) -> List[Dict]:
        """Obtiene los enlaces de la topología"""
        try:
            response = self.session.get(f"{self.base_url}/wm/topology/links/json")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error obteniendo topología: {e}")
            return []
    
    def push_flow(self, dpid: str, flow_entry: Dict) -> bool:
        """Instala un flow entry en un switch específico"""
        try:
            url = f"{self.base_url}/wm/staticentrypusher/json"
            response = self.session.post(url, json=flow_entry)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error instalando flow en switch {dpid}: {e}")
            return False
    
    def delete_flow(self, dpid: str, flow_name: str) -> bool:
        """Elimina un flow entry de un switch específico"""
        try:
            url = f"{self.base_url}/wm/staticentrypusher/json"
            delete_entry = {
                "switch": dpid,
                "name": flow_name
            }
            response = self.session.delete(url, json=delete_entry)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error eliminando flow {flow_name} del switch {dpid}: {e}")
            return False

def get_attachment_point(controller: FloodlightController, mac_address: str) -> Optional[Dict]:
    """
    Encuentra el punto de conexión (switch y puerto) de un dispositivo por su MAC
    """
    devices = controller.get_devices()
    
    mac_normalized = mac_address.replace(":", "").replace("-", "").upper()
    
    for device in devices:
        if 'mac' in device:
            device_mac = device['mac'][0].replace(":", "").replace("-", "").upper()
            if device_mac == mac_normalized:
                if 'attachmentPoint' in device and device['attachmentPoint']:
                    ap = device['attachmentPoint'][0]
                    return {
                        'dpid': ap['switchDPID'],
                        'port': ap['port']
                    }
    return None

def get_route(controller: FloodlightController, src_dpid: str, dst_dpid: str) -> List[Dict]:
    """
    Calcula la ruta entre dos switches usando el algoritmo de shortest path
    """
    try:
        url = f"{controller.base_url}/wm/topology/route/{src_dpid}/{dst_dpid}/json"
        response = controller.session.get(url)
        response.raise_for_status()
        route_data = response.json()
        
        if route_data and len(route_data) > 0:
            return route_data[0]['path'] if 'path' in route_data[0] else []
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error calculando ruta entre {src_dpid} y {dst_dpid}: {e}")
        return []

def build_route(controller: FloodlightController, alumno: Alumno, servidor: Servidor, 
                servicio: Servicio, handler: str) -> bool:
    """
    Construye e instala los flows necesarios para habilitar la conectividad
    entre un alumno y un servicio específico del servidor
    """
    print(f"Construyendo ruta para {handler}: {alumno.codigo} -> {servidor.nombre}:{servicio.nombre}")
    
    # 1. Encontrar puntos de conexión
    src_ap = get_attachment_point(controller, alumno.mac)
    dst_ap = get_attachment_point(controller, "dummy")  # Necesitaremos la MAC del servidor
    
    if not src_ap:
        print(f"Error: No se pudo encontrar el punto de conexión para {alumno.mac}")
        return False
    
    # Para este laboratorio, asumiremos que conocemos la conexión del servidor
    # En un entorno real, necesitaríamos un mecanismo para descubrir esto
    
    # 2. Calcular la ruta entre switches
    if src_ap['dpid'] == dst_ap['dpid'] if dst_ap else False:
        # Mismo switch, solo necesitamos flows en un switch
        route = [{'switch': src_ap['dpid'], 'port': src_ap['port']}]
    else:
        route = get_route(controller, src_ap['dpid'], dst_ap['dpid'] if dst_ap else src_ap['dpid'])
    
    # 3. Instalar flows para el tráfico del alumno al servidor
    success = True
    
    # Flow para ARP requests (necesario para resolución de direcciones)
    arp_flow = {
        "switch": src_ap['dpid'],
        "name": f"{handler}_arp_request",
        "cookie": "0",
        "priority": "32768",
        "in_port": str(src_ap['port']),
        "eth_type": "0x0806",
        "arp_tpa": servidor.ip,
        "active": "true",
        "actions": "output=flood"
    }
    
    if not controller.push_flow(src_ap['dpid'], arp_flow):
        success = False
    
    # Flow para ARP replies
    arp_reply_flow = {
        "switch": src_ap['dpid'],
        "name": f"{handler}_arp_reply",
        "cookie": "0",
        "priority": "32768",
        "eth_type": "0x0806",
        "arp_spa": servidor.ip,
        "arp_tha": alumno.mac,
        "active": "true",
        "actions": f"output={src_ap['port']}"
    }
    
    if not controller.push_flow(src_ap['dpid'], arp_reply_flow):
        success = False
    
    # Flow para tráfico del alumno al servidor (outbound)
    outbound_flow = {
        "switch": src_ap['dpid'],
        "name": f"{handler}_outbound",
        "cookie": "0",
        "priority": "32768",
        "in_port": str(src_ap['port']),
        "eth_src": alumno.mac,
        "eth_type": "0x0800",
        "ipv4_dst": servidor.ip,
        "ip_proto": "6" if servicio.protocolo == "TCP" else "17",
        "tcp_dst": str(servicio.puerto) if servicio.protocolo == "TCP" else "",
        "udp_dst": str(servicio.puerto) if servicio.protocolo == "UDP" else "",
        "active": "true",
        "actions": "output=flood"  # En un entorno real, sería el puerto específico
    }
    
    # Limpiar campos vacíos
    outbound_flow = {k: v for k, v in outbound_flow.items() if v != ""}
    
    if not controller.push_flow(src_ap['dpid'], outbound_flow):
        success = False
    
    # Flow para tráfico del servidor al alumno (inbound)
    inbound_flow = {
        "switch": src_ap['dpid'],
        "name": f"{handler}_inbound",
        "cookie": "0",
        "priority": "32768",
        "eth_dst": alumno.mac,
        "eth_type": "0x0800",
        "ipv4_src": servidor.ip,
        "ip_proto": "6" if servicio.protocolo == "TCP" else "17",
        "tcp_src": str(servicio.puerto) if servicio.protocolo == "TCP" else "",
        "udp_src": str(servicio.puerto) if servicio.protocolo == "UDP" else "",
        "active": "true",
        "actions": f"output={src_ap['port']}"
    }
    
    # Limpiar campos vacíos
    inbound_flow = {k: v for k, v in inbound_flow.items() if v != ""}
    
    if not controller.push_flow(src_ap['dpid'], inbound_flow):
        success = False
    
    if success:
        print(f"Ruta creada exitosamente para {handler}")
    else:
        print(f"Error creando ruta para {handler}")
    
    return success

# ============================================================================
# CLASE PRINCIPAL DE LA APLICACIÓN SDN
# ============================================================================

class SDNApplication:
    """Clase principal de la aplicación SDN para control de acceso basado en roles"""
    
    def __init__(self, controller_ip: str = "127.0.0.1", controller_port: int = 8080):
        self.controller = FloodlightController(controller_ip, controller_port)
        self.alumnos: Dict[str, Alumno] = {}  # código -> Alumno
        self.cursos: Dict[str, Curso] = {}    # código -> Curso
        self.servidores: Dict[str, Servidor] = {}  # nombre -> Servidor
        self.conexiones: Dict[str, Conexion] = {}  # handler -> Conexion
        self.connection_counter = 1
    
    def importar_datos(self, archivo_yaml: str) -> bool:
        """Importa datos desde un archivo YAML"""
        try:
            with open(archivo_yaml, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
            
            # Importar alumnos
            if 'alumnos' in data:
                for alumno_data in data['alumnos']:
                    alumno = Alumno(
                        alumno_data['nombre'],
                        alumno_data['codigo'],
                        alumno_data['mac']
                    )
                    self.alumnos[alumno.codigo] = alumno
            
            # Importar servidores
            if 'servidores' in data:
                for servidor_data in data['servidores']:
                    servidor = Servidor(servidor_data['nombre'], servidor_data['ip'])
                    
                    for servicio_data in servidor_data['servicios']:
                        servicio = Servicio(
                            servicio_data['nombre'],
                            servicio_data['protocolo'],
                            servicio_data['puerto']
                        )
                        servidor.agregar_servicio(servicio)
                    
                    self.servidores[servidor.nombre] = servidor
            
            # Importar cursos
            if 'cursos' in data:
                for curso_data in data['cursos']:
                    curso = Curso(
                        curso_data['codigo'],
                        curso_data['nombre'],
                        curso_data.get('estado', 'INACTIVO')
                    )
                    
                    # Agregar alumnos al curso
                    if 'alumnos' in curso_data:
                        for codigo_alumno in curso_data['alumnos']:
                            curso.agregar_alumno(codigo_alumno)
                    
                    # Agregar servidores permitidos
                    if 'servidores' in curso_data:
                        for servidor_data in curso_data['servidores']:
                            servidor_permitido = ServidorPermitido(
                                servidor_data['nombre'],
                                servidor_data['servicios_permitidos']
                            )
                            curso.agregar_servidor(servidor_permitido)
                    
                    self.cursos[curso.codigo] = curso
            
            print(f"Datos importados exitosamente desde {archivo_yaml}")
            return True
            
        except Exception as e:
            print(f"Error importando datos: {e}")
            return False
    
    def exportar_datos(self, archivo_yaml: str) -> bool:
        """Exporta datos a un archivo YAML"""
        try:
            data = {
                'alumnos': [alumno.to_dict() for alumno in self.alumnos.values()],
                'servidores': [servidor.to_dict() for servidor in self.servidores.values()],
                'cursos': [curso.to_dict() for curso in self.cursos.values()]
            }
            
            with open(archivo_yaml, 'w', encoding='utf-8') as file:
                yaml.dump(data, file, default_flow_style=False, allow_unicode=True)
            
            print(f"Datos exportados exitosamente a {archivo_yaml}")
            return True
            
        except Exception as e:
            print(f"Error exportando datos: {e}")
            return False
    
    def verificar_autorizacion(self, codigo_alumno: str, nombre_servidor: str, nombre_servicio: str) -> bool:
        """Verifica si un alumno está autorizado para acceder a un servicio"""
        for curso in self.cursos.values():
            if curso.alumno_tiene_acceso_servicio(codigo_alumno, nombre_servidor, nombre_servicio):
                return True
        return False
    
    def crear_conexion(self, codigo_alumno: str, nombre_servidor: str, nombre_servicio: str) -> Optional[str]:
        """Crea una conexión entre un alumno y un servicio"""
        
        # Verificar que el alumno existe
        if codigo_alumno not in self.alumnos:
            print(f"Error: Alumno {codigo_alumno} no encontrado")
            return None
        
        # Verificar que el servidor existe
        if nombre_servidor not in self.servidores:
            print(f"Error: Servidor {nombre_servidor} no encontrado")
            return None
        
        servidor = self.servidores[nombre_servidor]
        servicio = servidor.obtener_servicio(nombre_servicio)
        
        if not servicio:
            print(f"Error: Servicio {nombre_servicio} no encontrado en {nombre_servidor}")
            return None
        
        # Verificar autorización
        if not self.verificar_autorizacion(codigo_alumno, nombre_servidor, nombre_servicio):
            print(f"Error: Alumno {codigo_alumno} no tiene autorización para acceder a {nombre_servidor}:{nombre_servicio}")
            return None
        
        # Generar handler único
        handler = f"conn_{self.connection_counter:04d}"
        self.connection_counter += 1
        
        # Crear la ruta en el controlador
        alumno = self.alumnos[codigo_alumno]
        if build_route(self.controller, alumno, servidor, servicio, handler):
            # Crear objeto conexión
            conexion = Conexion(handler, codigo_alumno, nombre_servidor, nombre_servicio)
            self.conexiones[handler] = conexion
            print(f"Conexión creada exitosamente: {handler}")
            return handler
        else:
            print(f"Error creando la ruta para la conexión")
            return None
    
    def eliminar_conexion(self, handler: str) -> bool:
        """Elimina una conexión existente"""
        if handler not in self.conexiones:
            print(f"Error: Conexión {handler} no encontrada")
            return False
        
        conexion = self.conexiones[handler]
        alumno = self.alumnos[conexion.codigo_alumno]
        
        # Encontrar el switch donde está conectado el alumno
        attachment_point = get_attachment_point(self.controller, alumno.mac)
        if attachment_point:
            if delete_route(self.controller, handler, attachment_point['dpid']):
                del self.conexiones[handler]
                print(f"Conexión {handler} eliminada exitosamente")
                return True
        
        print(f"Error eliminando la conexión {handler}")
        return False

def delete_route(controller: FloodlightController, handler: str, dpid: str) -> bool:
    """
    Elimina los flows asociados a una conexión específica
    """
    flows_to_delete = [
        f"{handler}_arp_request",
        f"{handler}_arp_reply", 
        f"{handler}_outbound",
        f"{handler}_inbound"
    ]
    
    success = True
    for flow_name in flows_to_delete:
        if not controller.delete_flow(dpid, flow_name):
            success = False
    
    return success


# ============================================================================
# INTERFAZ DE USUARIO - MENÚS INTERACTIVOS
# ============================================================================

def menu_principal():
    """Muestra el menú principal"""
    print("\n" + "="*50)
    print("     SISTEMA SDN - CONTROL DE ACCESO")
    print("="*50)
    print("1) Importar")
    print("2) Exportar") 
    print("3) Cursos")
    print("4) Alumnos")
    print("5) Servidores")
    print("6) Políticas")
    print("7) Conexiones")
    print("0) Salir")
    print("="*50)

def menu_cursos():
    """Menú para gestión de cursos"""
    print("\n--- GESTIÓN DE CURSOS ---")
    print("1) Crear curso")
    print("2) Listar cursos")
    print("3) Mostrar detalle")
    print("4) Actualizar curso")
    print("5) Borrar curso")
    print("0) Volver")

def menu_alumnos():
    """Menú para gestión de alumnos""" 
    print("\n--- GESTIÓN DE ALUMNOS ---")
    print("1) Crear alumno")
    print("2) Listar alumnos")
    print("3) Mostrar detalle")
    print("4) Actualizar alumno")
    print("5) Borrar alumno")
    print("0) Volver")

def menu_servidores():
    """Menú para gestión de servidores"""
    print("\n--- GESTIÓN DE SERVIDORES ---")
    print("1) Crear servidor")
    print("2) Listar servidores")
    print("3) Mostrar detalle de un servidor")
    print("0) Volver")


if __name__ == "__main__":
    app = SDNApplication()

    while True:
        menu_principal()
        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            nombre_archivo = input("Ingrese el nombre del archivo YAML a importar: ")
            app.importar_datos(nombre_archivo)

        elif opcion == "2":
            nombre_archivo = input("Ingrese el nombre del archivo YAML a exportar: ")
            app.exportar_datos(nombre_archivo)

        elif opcion == "3":
            while True:
                menu_cursos()
                subop = input("Seleccione una opción: ")

                if subop == "1":
                    codigo = input("Código del curso: ")
                    nombre = input("Nombre del curso: ")
                    estado = input("Estado (DICTANDO o INACTIVO): ")
                    if codigo in app.cursos:
                        print("⚠️ Ya existe un curso con ese código.")
                    else:
                        nuevo = Curso(codigo, nombre, estado)
                        app.cursos[codigo] = nuevo
                        print(f"Curso {nombre} agregado con éxito.")

                elif subop == "2":
                    print("\nLista de cursos:")
                    for curso in app.cursos.values():
                        print(f" - {curso}")

                elif subop == "3":
                    codigo = input("Ingrese el código del curso: ")
                    if codigo in app.cursos:
                        curso = app.cursos[codigo]
                        print(curso)
                        print("Alumnos:")
                        for cod in curso.alumnos:
                            alumno = app.alumnos.get(cod)
                            if alumno:
                                print(f" - {alumno}")
                            else:
                                print(f" - Código {cod} (no encontrado)")
                        print("Servidores permitidos:")
                        for srv in curso.servidores:
                            print(f" - {srv.nombre}: {', '.join(srv.servicios_permitidos)}")
                    else:
                        print("❌ Curso no encontrado.")

                elif subop == "0":
                    break

                else:
                    print("Opción inválida.")

        elif opcion == "4":
            while True:
                menu_alumnos()
                subop = input("Seleccione una opción: ")
                
                if subop == "1":
                    nombre = input("Nombre del alumno: ")
                    codigo = input("Código PUCP: ")
                    mac = input("Dirección MAC (ej. 00:11:22:33:44:55): ")
                    if codigo in app.alumnos:
                        print("⚠️ Ya existe un alumno con ese código.")
                    else:
                        nuevo = Alumno(nombre, codigo, mac)
                        app.alumnos[codigo] = nuevo
                        print(f"Alumno {nombre} agregado con éxito.")
                
                elif subop == "2":
                    print("\nLista de alumnos:")
                    for alumno in app.alumnos.values():
                        print(f" - {alumno}")
                
                elif subop == "3":
                    codigo = input("Ingrese el código del alumno: ")
                    if codigo in app.alumnos:
                        print(app.alumnos[codigo])
                    else:
                        print("❌ Alumno no encontrado.")
                
                elif subop == "0":
                    break
                
                else:
                    print("Opción inválida.")
        
        elif opcion == "5":
            while True:
                menu_servidores()
                subop = input("Seleccione una opción: ")

                if subop == "1":
                    nombre = input("Nombre del servidor: ")
                    ip = input("Dirección IP: ")
                    if nombre in app.servidores:
                        print("⚠️ Ya existe un servidor con ese nombre.")
                    else:
                        nuevo = Servidor(nombre, ip)
                        app.servidores[nombre] = nuevo
                        print(f"Servidor {nombre} agregado con éxito.")
                
                elif subop == "2":
                    print("\nLista de servidores:")
                    for servidor in app.servidores.values():
                        print(f" - {servidor}")
                
                elif subop == "3":
                    nombre = input("Nombre del servidor: ")
                    if nombre in app.servidores:
                        srv = app.servidores[nombre]
                        print(f"{srv}")
                        print("Servicios:")
                        for s in srv.servicios:
                            print(f" - {s}")
                    else:
                        print("❌ Servidor no encontrado.")
                
                elif subop == "0":
                    break
                
                else:
                    print("Opción inválida.")

        elif opcion == "6":
            print("\nCursos que tienen acceso a SSH en el Servidor 1:")
            for curso in app.cursos.values():
                if curso.estado == "DICTANDO":
                    for servidor in curso.servidores:
                        if servidor.nombre == "Servidor 1" and "ssh" in servidor.servicios_permitidos:
                            print(f" - {curso.codigo}: {curso.nombre}")

        elif opcion == "0":
            print("Saliendo del sistema...")
            break

        else:
            print("Opción no válida.")
