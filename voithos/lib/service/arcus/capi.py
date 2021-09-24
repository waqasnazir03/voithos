""" lib for arcus CAPI """

import click
import os
import re
import requests
import mysql.connector as connector

from voithos.lib.docker import volume_opt
from voithos.lib.system import shell, error, assert_path_exists
from voithos.constants import DEV_MODE


def start(
    release,
    kubeconfig_path,
    openrc_path,
    cacert=None
):
    """ Start the arcus api """
    image = f"breqwatr/arcus-capi:{release}"
    daemon = "-d --restart=always"
    kube_mount = volume_opt(kubeconfig_path, "/root/.kube/config")
    openrc_mount = volume_opt(openrc_path, "/openrc.sh")
    network = "-p 0.0.0.0:8888:80"
    log_mount = "-v /var/log/arcus/:/var/log/arcus/"
    hosts_mount = "-v /etc/hosts:/etc/hosts"
    name = "arcus_capi"
    cacert_vals = ""
    if cacert:
        mount_path = "/etc/certs/cacert"
        cacert_envvar = f"-e CACERT_PATH={mount_path}"
        cacert_vol = volume_opt(cacert, mount_path)
        cacert_vals = f"{cacert_envvar} {cacert_vol}"
    shell(f"docker rm -f {name} 2>/dev/null || true")
    cmd = (
        f"docker run --name {name} {daemon} {network} {cacert_vals} "
        f"{hosts_mount} {log_mount} {kube_mount} {openrc_mount}"
        f"{image}"
    )
    shell(cmd)
