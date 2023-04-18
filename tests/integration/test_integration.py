#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the nms-magmalte rock."""

import unittest
from pathlib import Path
from time import sleep

import docker  # type: ignore[import]
import requests
import yaml

MAGMALTE_DOCKER_URL = "http://localhost"
MAGMALTE_DOCKER_PORT = 8081
MAGMALTE_LOGIN_PAGE = "/user/login"
POSTGRES_USER = "username"
POSTGRES_PASSWORD = "password"
POSTGRES_DB = "magma"


class TestNmsMagmalteRock(unittest.TestCase):
    """Integration tests for the nms-magmalte rock."""

    def setUp(self) -> None:
        """Run containers to test."""
        self.client = docker.from_env()
        self.network = self.client.networks.create(
            "bridge_network",
            driver="bridge",
        )
        self._run_postgres_container()
        self._run_magmalte_container()

    def _run_postgres_container(self):
        postgres_container = self.client.containers.run(
            "postgres",
            detach=True,
            ports={"5432/tcp": 5432},
            environment={
                "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
                "POSTGRES_USER": POSTGRES_USER,
                "POSTGRES_DB": POSTGRES_DB,
            },
            name="postgres_container",
        )
        self.network.connect(postgres_container)

    def _run_magmalte_container(self):
        with open(Path("./../rockcraft.yaml"), "r") as f:
            data = yaml.safe_load(f)

        image_name = data["name"]
        version = data["version"]

        magmalte_container = self.client.containers.run(
            f"ghcr.io/canonical/{image_name}:{version}",
            detach=True,
            ports={"8080/tcp": 8081},
            name="app_container",
            environment={
                "PORT": "8080",
                "HOST": "0.0.0.0",
                "MYSQL_DIALECT": "postgres",
                "MYSQL_PASS": POSTGRES_PASSWORD,
                "MYSQL_USER": POSTGRES_USER,
                "MYSQL_DB": POSTGRES_DB,
                "MYSQL_PORT": "5432",
                "MYSQL_HOST": "postgres_container",
            },
            command="/bin/yarn run start:prod",
        )
        self.network.connect(magmalte_container)

    def test_given_nms_magmalte_container_is_running_when_http_get_then_hello_message_is_returned(  # noqa: E501
        self,
    ):
        """Test to validate that the container is running correctly."""
        url = f"{MAGMALTE_DOCKER_URL}:{MAGMALTE_DOCKER_PORT}{MAGMALTE_LOGIN_PAGE}"  # noqa: E501
        for _ in range(30):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass
            sleep(1)
        else:
            assert False, "Failed to get a 200 response within 10 seconds."
