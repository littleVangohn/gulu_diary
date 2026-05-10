# 此测试用例程序可用来测试《数据服务器性能测试大赛规则》中描述的数据上传协议规范。
import base64
import hashlib
import hmac
import json
import time
import unittest
from hashlib import sha256

import requests


class TestDataServer(unittest.TestCase):
    # 初始化测试
    def setUp(self):
        self.base_url = "http://47.97.245.213:5000"
        self.device_id = "CQU0000000"
        self.secret = "SmnT8UyI3gqmhMc9"
        self.timeout = 10

    def get_ticket(self, device_id=None):
        return requests.get(
            f"{self.base_url}/getTicket",
            params={"deviceId": device_id or self.device_id},
            timeout=self.timeout,
        )

    def get_token(self, device_id=None, secret=None):
        device_id = device_id or self.device_id
        secret = secret or self.secret
        ticket_response = self.get_ticket(device_id)
        self.assertEqual(ticket_response.status_code, 200)
        self.assertEqual(ticket_response.json()["code"], 200)
        ticket = ticket_response.json()["data"]["ticket"]
        signature = hashlib.md5((ticket + device_id + secret).encode("utf-8")).hexdigest()
        response = requests.post(
            f"{self.base_url}/getToken",
            json={"deviceId": device_id, "signature": signature, "ticket": ticket},
            timeout=self.timeout,
        )
        return ticket, response

    def make_expired_jwt(self, device_id=None, secret=None):
        device_id = device_id or self.device_id
        secret = secret or self.secret
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {"deviceId": device_id, "expiredTime": int(time.time()) - 120}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        ).rstrip(b"=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ).rstrip(b"=")
        signing_input = header_b64 + b"." + payload_b64
        signature = base64.urlsafe_b64encode(
            hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
        ).rstrip(b"=")
        return b".".join([header_b64, payload_b64, signature]).decode("utf-8")

    ############################测试：1.取Ticket票##############################################
    def test_get_ticket_missing_device_id(self):
        response = requests.get(f"{self.base_url}/getTicket", timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 201)

    def test_get_ticket_unknown_device_id(self):
        response = self.get_ticket("unknown_device_999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 202)

    def test_get_ticket_success(self):
        response = self.get_ticket()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 200)
        self.assertIn("ticket", response.json()["data"])

    ############################测试：2.取Token##############################################
    def test_get_token_missing_parameters(self):
        response = requests.post(f"{self.base_url}/getToken", json={}, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 201)

    def test_get_token_unknown_device_id(self):
        data = {"deviceId": "unknown_device_999", "signature": "test", "ticket": "test"}
        response = requests.post(f"{self.base_url}/getToken", json=data, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 202)

    def test_get_token_invalid_signature(self):
        ticket_response = self.get_ticket()
        ticket = ticket_response.json()["data"]["ticket"]
        data = {"deviceId": self.device_id, "signature": "invalid_signature", "ticket": ticket}
        response = requests.post(f"{self.base_url}/getToken", json=data, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 203)

    def test_get_token_success(self):
        _, response = self.get_token()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 200)
        self.assertIn("token", response.json()["data"])

    ############################测试：3.上传血压数据##############################################
    def test_upload_data_missing_parameters(self):
        response = requests.post(f"{self.base_url}/uploadData", json={}, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 201)

    def test_upload_data_unknown_device_id(self):
        data = {
            "deviceId": "unknown_device_999",
            "token": "test",
            "data": {"time": int(time.time()), "high": 120, "low": 80},
        }
        response = requests.post(f"{self.base_url}/uploadData", json=data, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 202)

    def test_upload_data_invalid_token(self):
        data = {
            "deviceId": self.device_id,
            "token": "invalid_token",
            "data": {"time": int(time.time()), "high": 120, "low": 80},
        }
        response = requests.post(f"{self.base_url}/uploadData", json=data, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 204)

    def test_upload_data_expired_token(self):
        expired_token = self.make_expired_jwt()
        data = {
            "deviceId": self.device_id,
            "token": expired_token,
            "data": {"time": int(time.time()), "high": 120, "low": 80},
        }
        response = requests.post(f"{self.base_url}/uploadData", json=data, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 206)

    def test_upload_data_invalid_blood_pressure(self):
        _, token_response = self.get_token()
        token = token_response.json()["data"]["token"]
        data = {
            "deviceId": self.device_id,
            "token": token,
            "data": {"time": int(time.time()), "high": 80, "low": 120},
        }
        response = requests.post(f"{self.base_url}/uploadData", json=data, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 205)

    def test_upload_data_success(self):
        _, token_response = self.get_token()
        token = token_response.json()["data"]["token"]
        data = {
            "deviceId": self.device_id,
            "token": token,
            "data": {"time": int(time.time()), "high": 120, "low": 80},
        }
        response = requests.post(f"{self.base_url}/uploadData", json=data, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 200)
        self.assertIn("receivedTime", response.json()["data"])

    ############################测试：4.刷新Token##############################################
    def test_refresh_token_missing_parameters(self):
        response = requests.post(f"{self.base_url}/refreshToken", json={}, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 201)

    def test_refresh_token_unknown_device_id(self):
        data = {"deviceId": "unknown_device_999", "signature": "test", "token": "test"}
        response = requests.post(f"{self.base_url}/refreshToken", json=data, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 202)

    def test_refresh_token_invalid_signature(self):
        _, token_response = self.get_token()
        token = token_response.json()["data"]["token"]
        data = {"deviceId": self.device_id, "signature": "invalid_signature", "token": token}
        response = requests.post(f"{self.base_url}/refreshToken", json=data, timeout=self.timeout)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 203)

    def test_refresh_token_max_refresh(self):
        _, token_response = self.get_token()
        token = token_response.json()["data"]["token"]

        signature = hashlib.md5((token + self.device_id + self.secret).encode("utf-8")).hexdigest()
        refresh_response = requests.post(
            f"{self.base_url}/refreshToken",
            json={"deviceId": self.device_id, "signature": signature, "token": token},
            timeout=self.timeout,
        )
        self.assertEqual(refresh_response.status_code, 200)
        self.assertEqual(refresh_response.json()["code"], 200)

        refreshed_token = refresh_response.json()["data"]["token"]
        second_signature = hashlib.md5(
            (refreshed_token + self.device_id + self.secret).encode("utf-8")
        ).hexdigest()
        second_refresh_response = requests.post(
            f"{self.base_url}/refreshToken",
            json={
                "deviceId": self.device_id,
                "signature": second_signature,
                "token": refreshed_token,
            },
            timeout=self.timeout,
        )
        self.assertEqual(second_refresh_response.status_code, 200)
        self.assertEqual(second_refresh_response.json()["code"], 207)

    def test_refresh_token_success(self):
        _, token_response = self.get_token()
        token = token_response.json()["data"]["token"]
        signature = hashlib.md5((token + self.device_id + self.secret).encode("utf-8")).hexdigest()
        refresh_response = requests.post(
            f"{self.base_url}/refreshToken",
            json={"deviceId": self.device_id, "signature": signature, "token": token},
            timeout=self.timeout,
        )
        self.assertEqual(refresh_response.status_code, 200)
        self.assertEqual(refresh_response.json()["code"], 200)
        self.assertIn("token", refresh_response.json()["data"])


if __name__ == "__main__":
    unittest.main()
