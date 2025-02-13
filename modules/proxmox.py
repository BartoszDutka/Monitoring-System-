import requests
from config import PROXMOX_URL, PROXMOX_TOKEN

def get_node_status():
    headers = {
        "Authorization": PROXMOX_TOKEN,
        "Content-Type": "application/json"
    }

    # Lista ID maszyn wirtualnych
    vm_ids = [100, 101]
    node_name = "proxmox"  # Węzeł, na którym znajdują się maszyny
    node_details = []

    try:
        # Iteruj po maszynach wirtualnych i pobieraj dane
        for vm_id in vm_ids:
            response = requests.get(
                f"{PROXMOX_URL}/nodes/{node_name}/qemu/{vm_id}/status/current",
                headers=headers,
                verify=False
            )
            response.raise_for_status()
            vm_data = response.json().get("data", {})

            # Debug: Wyświetl dane maszyny wirtualnej
            print(f"Debug: VM {vm_id} Data:", vm_data)

            node_details.append({
                "vm_id": vm_id,
                "node": node_name,
                "vm_name": vm_data.get("name", "None"),
                "status": vm_data.get("status", "None"),
                "cpu_load": f"{vm_data.get('cpu', 0) * 100:.2f}%",  # Konwersja na %
                "memory_usage": f"{vm_data.get('mem', 0) / 1024 / 1024:.2f} MiB",
                "max_memory": f"{vm_data.get('maxmem', 0) / 1024 / 1024:.2f} MiB",
                "uptime": vm_data.get("uptime", 0),
                "disk_read": f"{vm_data.get('diskread', 0) / 1024 / 1024:.2f} MiB",
                "disk_write": f"{vm_data.get('diskwrite', 0) / 1024 / 1024:.2f} MiB",
            })

        return {"data": node_details}

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return {"error": str(e)}
    except ValueError:
        print("Response is not JSON")
        return {"error": "Response is not in JSON format"}
