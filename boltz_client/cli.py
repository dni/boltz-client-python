import asyncio
import sys

import click

from boltz_client.boltz import BoltzClient, BoltzConfig

# disable tracebacks on exceptions
sys.tracebacklimit = 0

config = BoltzConfig()


@click.group()
def command_group():
    """
    Python CLI of boltz-client-python, enjoy submarine swapping. :)
    Uses mempool.space for retrieving onchain data"""


@click.command()
@click.argument("payment_request", type=str)
def create_swap(payment_request):
    """
    create a swap
    boltz will pay your invoice after you paid the onchain address

    SATS you want to swap, has to be the same as in PAYMENT_REQUEST
    PAYMENT_REQUEST with the same amount as specified in SATS
    """
    client = BoltzClient(config)
    refund_privkey_wif, swap = client.create_swap(payment_request)

    click.echo()
    click.echo(f"boltz_id: {swap.id}")
    click.echo()
    click.echo(
        f"mempool.space url: {config.mempool_url.replace('/api', '')}/address/{swap.address}"
    )
    click.echo()
    click.echo(f"refund privkey in wif: {refund_privkey_wif}")
    click.echo(f"redeem_script_hex: {swap.redeemScript}")
    click.echo()
    click.echo(f"onchain address: {swap.address}")
    click.echo(f"expected amount: {swap.expectedAmount}")
    click.echo(f"bip21 address: {swap.bip21}")


@click.command()
@click.argument("privkey_wif", type=str)
@click.argument("lockup_address", type=str)
@click.argument("receive_address", type=str)
@click.argument("redeem_script_hex", type=str)
@click.argument("timeout_block_height", type=int)
def refund_swap(
    privkey_wif: str,
    lockup_address: str,
    receive_address: str,
    redeem_script_hex: str,
    timeout_block_height: int,
):
    """
    refund a swap
    """
    client = BoltzClient(config)
    txid = asyncio.run(
        client.refund_swap(
            privkey_wif,
            lockup_address,
            receive_address,
            redeem_script_hex,
            timeout_block_height,
        )
    )
    click.echo(f"swap refunded!")
    click.echo(f"TXID: {txid}")


@click.command()
@click.argument("sats", type=int)
def create_reverse_swap(sats: int):
    """
    create a reverse swap
    """
    client = BoltzClient(config)
    claim_privkey_wif, preimage_hex, swap = client.create_reverse_swap(sats)

    click.echo("reverse swap created!")
    click.echo()
    click.echo(f"claim privkey in wif: {claim_privkey_wif}")
    click.echo(f"preimage hex: {preimage_hex}")
    click.echo(f"lockup_address: {swap.lockupAddress}")
    click.echo(f"redeem_script_hex: {swap.redeemScript}")
    click.echo()
    click.echo(f"boltz_id: {swap.id}")
    click.echo(
        f"mempool.space url: {config.mempool_url.replace('/api', '')}/address/{swap.lockupAddress}"
    )
    click.echo()
    click.echo("invoice:")
    click.echo(swap.invoice)


@click.command()
@click.argument("receive_address", type=str)
@click.argument("sats", type=int)
@click.argument("zeroconf", type=bool, default=False)
def create_reverse_swap_and_claim(
    receive_address: str, sats: int, zeroconf: bool = False
):
    """
    create a reverse swap and claim
    """
    client = BoltzClient(config)
    claim_privkey_wif, preimage_hex, swap = client.create_reverse_swap(sats)

    click.echo("reverse swap created!")
    click.echo()
    click.echo(f"claim privkey in wif: {claim_privkey_wif}")
    click.echo(f"preimage hex: {preimage_hex}")
    click.echo(f"lockup_address: {swap.lockupAddress}")
    click.echo(f"redeem_script_hex: {swap.redeemScript}")
    click.echo()
    click.echo(f"boltz_id: {swap.id}")
    click.echo(f"mempool.space url: {config.mempool_url}/address/{swap.lockupAddress}")
    click.echo()
    click.echo("invoice:")
    click.echo(swap.invoice)
    click.echo()
    click.echo("1. waiting until you paid the invoice...")
    click.echo("2. waiting for boltz to create the lockup transaction...")
    if not zeroconf:
        click.echo("3. waiting for lockup tx confirmation...")

    txid = asyncio.run(
        client.claim_reverse_swap(
            swap.lockupAddress,
            receive_address,
            claim_privkey_wif,
            preimage_hex,
            swap.redeemScript,
            zeroconf,
        )
    )

    click.echo(f"reverse swap claimed!")
    click.echo(f"TXID: {txid}")


@click.command()
@click.argument("lockup_address", type=str)
@click.argument("receive_address", type=str)
@click.argument("privkey_wif", type=str)
@click.argument("preimage_hex", type=str)
@click.argument("redeem_script_hex", type=str)
@click.argument("zeroconf", type=bool, default=False)
def claim_reverse_swap(
    lockup_address: str,
    receive_address: str,
    privkey_wif: str,
    preimage_hex: str,
    redeem_script_hex: str,
    zeroconf: bool = False,
):
    """
    claims a reverse swap
    """
    client = BoltzClient(config)

    txid = asyncio.run(
        client.claim_reverse_swap(
            lockup_address,
            receive_address,
            privkey_wif,
            preimage_hex,
            redeem_script_hex,
            zeroconf,
        )
    )

    click.echo(f"reverse swap claimed!")
    click.echo(f"TXID: {txid}")


@click.command()
@click.argument("id", type=str)
def swap_status(id):
    """
    get swap status
    retrieves the status of your boltz swap from the api

    ID is the id of your boltz swap
    """
    client = BoltzClient(config)
    data = client.swap_status(id)
    click.echo(data)


def main():
    command_group.add_command(swap_status)
    command_group.add_command(create_swap)
    command_group.add_command(refund_swap)
    command_group.add_command(create_reverse_swap)
    command_group.add_command(create_reverse_swap_and_claim)
    command_group.add_command(claim_reverse_swap)
    command_group()


if __name__ == "__main__":
    main()
