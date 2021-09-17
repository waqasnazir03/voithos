""" Manage Arcus-CAPI service """

import click

import voithos.lib.aws.ecr as ecr
import voithos.lib.service.arcus.capi as arcus_capi


@click.option("--release", "-r", required=True, help="Version of Arcus CAPI to run")
@click.command(name="pull")
def pull(release):
    """ Pull Arcus CAPI from Breqwatr's private repository """
    image = f"breqwatr/arcus-capi:{release}"
    ecr.pull(image)


@click.option("--release", "-r", required=True, help="Version of Arcus CAPI to run")
@click.option("--kubeconfig", "-k", required=True, help="Path to kubeconfig file")
@click.option("--openrc", "-o", required=True, help="Path to OpenStack openrc file")
@click.command(name="start")
def start(
    release,
    kubeconfig,
    openrc
):
    """ Launch the arcus-capi service """
    click.echo("starting arcus capi")
    arcus_capi.start(
        release=release,
        kubeconfig_path=kubeconfig,
        openrc_path=openrc
    )


def get_capi_group():
    """ return the arcus group function """

    @click.group(name="capi")
    def capi_group():
        """ Arcus Cluster-API service """

    capi_group.add_command(pull)
    capi_group.add_command(start)
    return capi_group
