#!/usr/bin/env python3
"""Check network connectivity to Slack."""

import socket
import ssl
import requests


def test_connectivity():
    """Test network connectivity to Slack endpoints."""

    print("Testing Slack connectivity...")

    # Test basic HTTP to Slack
    try:
        response = requests.get("https://slack.com", timeout=5)
        print(f"✓ HTTPS to slack.com: {response.status_code}")
    except Exception as e:
        print(f"✗ HTTPS to slack.com failed: {e}")

    # Test API endpoint
    try:
        response = requests.get("https://slack.com/api/api.test", timeout=5)
        print(f"✓ API test endpoint: {response.status_code}")
    except Exception as e:
        print(f"✗ API test failed: {e}")

    # Test WebSocket connectivity
    try:
        # This is roughly what Socket Mode tries to do
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(("wss-primary.slack.com", 443))
        sock.close()

        if result == 0:
            print("✓ Socket to wss-primary.slack.com:443 works")
        else:
            print(f"✗ Socket connection failed: {result}")
    except Exception as e:
        print(f"✗ Socket test failed: {e}")

    # Check SSL/TLS
    try:
        context = ssl.create_default_context()
        with socket.create_connection(("slack.com", 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname="slack.com") as ssock:
                print(f"✓ SSL/TLS to slack.com works")
    except Exception as e:
        print(f"✗ SSL/TLS test failed: {e}")


if __name__ == "__main__":
    test_connectivity()
