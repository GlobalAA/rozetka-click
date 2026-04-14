import requests
from typing import Tuple, Any

API_URL = "http://127.0.0.1:8080/api"

class APIClient:
    @staticmethod
    def get_status() -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{API_URL}/status", timeout=5)
            response.raise_for_status()
            data = response.json()
            return True, {"running": data.get("running", False), "stop_at": data.get("stop_at")}
        except Exception as e:
            return False, {"error": str(e)}

    @staticmethod
    def start_parser(iterations: int = 1, delay_type: str = "none", delay_value: str = "") -> Tuple[bool, str]:
        try:
            payload = {
                "iterations": iterations,
                "delay_type": delay_type,
                "delay_value": delay_value
            }
            response = requests.post(f"{API_URL}/start", json=payload, timeout=5)
            data = response.json()
            if response.status_code == 200:
                return True, data.get("message", "Started")
            return False, data.get("message", "Error")
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def stop_parser(delay_type: str = "none", delay_value: str = "") -> Tuple[bool, str]:
        try:
            payload = {
                "delay_type": delay_type,
                "delay_value": delay_value
            }
            response = requests.post(f"{API_URL}/stop", json=payload, timeout=5)
            data = response.json()
            if response.status_code == 200:
                return True, data.get("message", "Stopped")
            return False, data.get("message", "Error")
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def add_proxy(server: str, username: str, password: str) -> Tuple[bool, str]:
        try:
            payload = {"server": server, "username": username, "password": password}
            response = requests.post(f"{API_URL}/proxy", json=payload, timeout=5)
            data = response.json()
            if response.status_code == 200:
                return True, data.get("message", "Success")
            return False, data.get("message", "Error")
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def add_shop(url: str) -> Tuple[bool, str]:
        try:
            payload = {"url": url}
            response = requests.post(f"{API_URL}/shop", json=payload, timeout=5)
            data = response.json()
            if response.status_code == 200:
                return True, f"Shop added (ID: {data.get('shop_id')})"
            return False, data.get("message", "Error")
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def get_shops() -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{API_URL}/shops", timeout=5)
            response.raise_for_status()
            data = response.json()
            return True, data.get("shops", [])
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def get_proxies() -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{API_URL}/proxies", timeout=5)
            response.raise_for_status()
            data = response.json()
            return True, data.get("proxies", [])
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def get_categories() -> Tuple[bool, Any]:
        try:
            response = requests.get(f"{API_URL}/categories", timeout=5)
            response.raise_for_status()
            data = response.json()
            return True, data.get("categories", [])
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def add_category(target_product: str, target_category: str) -> Tuple[bool, str]:
        try:
            payload = {
                "target_product": target_product,
                "target_category": target_category
            }
            response = requests.post(f"{API_URL}/category", json=payload, timeout=5)
            data = response.json()
            if response.status_code == 200:
                return True, f"Category added (ID: {data.get('category_id')})"
            return False, data.get("message", "Error")
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def delete_shop(shop_id: int) -> Tuple[bool, str]:
        try:
            response = requests.delete(f"{API_URL}/shop/{shop_id}", timeout=5)
            data = response.json()
            if response.status_code == 200:
                return True, data.get("message", "Deleted")
            return False, data.get("message", "Error")
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def delete_proxy(proxy_id: int) -> Tuple[bool, str]:
        try:
            response = requests.delete(f"{API_URL}/proxy/{proxy_id}", timeout=5)
            data = response.json()
            if response.status_code == 200:
                return True, data.get("message", "Deleted")
            return False, data.get("message", "Error")
        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def delete_category(category_id: int) -> Tuple[bool, str]:
        try:
            response = requests.delete(f"{API_URL}/category/{category_id}", timeout=5)
            data = response.json()
            if response.status_code == 200:
                return True, data.get("message", "Deleted")
            return False, data.get("message", "Error")
        except Exception as e:
            return False, f"Connection error: {e}"
