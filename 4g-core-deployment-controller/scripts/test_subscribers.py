#!/usr/bin/env python3
"""
Script para probar los endpoints de subscriptores.

Este script realiza las siguientes acciones:
1. Obtiene el conteo inicial de subscriptores
2. Genera y crea un nuevo subscriptor con datos válidos
3. Verifica que el subscriptor se haya creado correctamente
"""

import argparse
import json
import os
import random
import sys
import time
from typing import Dict, Any

import requests


def generate_subscriber(name: str) -> Dict[str, Any]:
    """
    Genera un subscriptor con datos válidos y un IMSI único.
    
    Args:
        name: Nombre del subscriptor
        
    Returns:
        Diccionario con los datos del subscriptor
    """
    # Generar IMSI único: timestamp (10 dígitos) + 5 dígitos aleatorios
    timestamp_part = str(int(time.time() * 1000))[-10:]  # Últimos 10 dígitos del timestamp en ms
    random_part = ''.join([str(random.randint(0, 9)) for _ in range(5)])
    imsi = timestamp_part + random_part
    
    # Generar claves hexadecimales aleatorias de 32 caracteres
    k = ''.join([random.choice('0123456789ABCDEF') for _ in range(32)])
    opc = ''.join([random.choice('0123456789ABCDEF') for _ in range(32)])
    
    subscriber = {
        "imsi": imsi,
        "name": name,
        "slice": [
            {
                "sst": 1,
                "sd": "000001",
                "default_indicator": True,
                "session": [
                    {
                        "name": "internet",
                        "type": 3,
                        "qos": {
                            "index": 9,
                            "arp": {
                                "priority_level": 8,
                                "pre_emption_capability": 1,
                                "pre_emption_vulnerability": 2,
                            },
                        },
                        "ambr": {
                            "downlink": {"value": 1, "unit": 3},
                            "uplink": {"value": 1, "unit": 3},
                        },
                        "pcc_rule": [],
                    }
                ],
            }
        ],
        "security": {
            "k": k,
            "amf": "8000",
            "opc": opc,
        },
        "ambr": {
            "downlink": {"value": 1, "unit": 3},
            "uplink": {"value": 1, "unit": 3},
        },
        "access_restriction_data": 32,
        "network_access_mode": 0,
        "subscriber_status": 0,
        "operator_determined_barring": 0,
        "subscribed_rau_tau_timer": 12,
        "schema_version": 1,
    }
    
    return subscriber


def get_subscribers_count(base_url: str, verbose: bool = False) -> int:
    """
    Obtiene el conteo total de subscriptores.
    
    Args:
        base_url: URL base del API
        verbose: Si True, muestra información detallada
        
    Returns:
        Número de subscriptores registrados
        
    Raises:
        requests.exceptions.RequestException: Si hay un error en la petición
    """
    url = f"{base_url}/core/subscribers"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        subscribers = response.json()
        count = len(subscribers)
        
        if verbose:
            print(f"\n[DEBUG] GET {url}")
            print(f"[DEBUG] Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {json.dumps(subscribers, indent=2)}")
        
        return count
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: No se pudo conectar al servidor en {base_url}")
        print("   Asegúrate de que el servidor esté ejecutándose.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"❌ Error: Timeout al conectar con {base_url}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener subscriptores: {e}")
        sys.exit(1)


def create_subscriber(base_url: str, subscriber_data: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """
    Crea un nuevo subscriptor.
    
    Args:
        base_url: URL base del API
        subscriber_data: Datos del subscriptor a crear
        verbose: Si True, muestra información detallada
        
    Returns:
        Datos del subscriptor creado
        
    Raises:
        requests.exceptions.RequestException: Si hay un error en la petición
    """
    url = f"{base_url}/core/subscribers"
    
    try:
        response = requests.post(url, json=subscriber_data, timeout=10)
        
        if verbose:
            print(f"\n[DEBUG] POST {url}")
            print(f"[DEBUG] Request Body: {json.dumps(subscriber_data, indent=2)}")
            print(f"[DEBUG] Status Code: {response.status_code}")
        
        if response.status_code == 409:
            print(f"❌ Error: Ya existe un subscriptor con IMSI {subscriber_data['imsi']}")
            print("   Intenta ejecutar el script nuevamente para generar un IMSI diferente.")
            sys.exit(1)
        
        response.raise_for_status()
        
        created_subscriber = response.json()
        
        if verbose:
            print(f"[DEBUG] Response: {json.dumps(created_subscriber, indent=2)}")
        
        return created_subscriber
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: No se pudo conectar al servidor en {base_url}")
        print("   Asegúrate de que el servidor esté ejecutándose.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"❌ Error: Timeout al conectar con {base_url}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al crear subscriptor: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Respuesta del servidor: {e.response.text}")
        sys.exit(1)


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Script para probar los endpoints de subscriptores"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra información detallada de las peticiones HTTP"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=os.getenv("API_URL", "http://localhost:8000"),
        help="URL base del API (default: http://localhost:8000 o variable de entorno API_URL)"
    )
    
    args = parser.parse_args()
    base_url = args.url.rstrip('/')  # Eliminar trailing slash si existe
    verbose = args.verbose
    
    print(f"🔗 Conectando al servidor: {base_url}\n")
    
    # Paso 1: Obtener conteo inicial
    print("📊 Paso 1: Obteniendo subscriptores actuales...")
    initial_count = get_subscribers_count(base_url, verbose)
    print(f"✅ Subscriptores registrados: {initial_count}\n")
    
    # Paso 2: Generar y crear nuevo subscriptor
    print("🆕 Paso 2: Generando nuevo subscriptor...")
    timestamp_str = time.strftime("%Y%m%d-%H%M%S")
    subscriber_name = f"Test Subscriber {timestamp_str}"
    subscriber_data = generate_subscriber(subscriber_name)
    
    print(f"   IMSI: {subscriber_data['imsi']}")
    print(f"   Nombre: {subscriber_data['name']}")
    
    if verbose:
        print(f"\n[DEBUG] Datos completos del subscriptor:")
        print(json.dumps(subscriber_data, indent=2))
    
    print("\n📤 Creando subscriptor...")
    created_subscriber = create_subscriber(base_url, subscriber_data, verbose)
    print(f"✅ Subscriptor creado exitosamente\n")
    
    # Paso 3: Verificar que se haya creado
    print("🔍 Paso 3: Verificando creación...")
    final_count = get_subscribers_count(base_url, verbose)
    print(f"✅ Subscriptores registrados: {final_count}\n")
    
    # Validar que el conteo aumentó
    if final_count == initial_count + 1:
        print("✨ ¡Verificación exitosa!")
        print(f"   El subscriptor '{subscriber_data['name']}' se creó correctamente.")
        print(f"   IMSI: {subscriber_data['imsi']}")
        print(f"   Total de subscriptores: {initial_count} → {final_count}")
        
        if verbose:
            print(f"\n[DEBUG] Subscriptor creado completo:")
            print(json.dumps(created_subscriber, indent=2))
    else:
        print("⚠️  Advertencia: El conteo de subscriptores no aumentó como se esperaba.")
        print(f"   Esperado: {initial_count + 1}, Obtenido: {final_count}")
        sys.exit(1)


if __name__ == "__main__":
    main()
