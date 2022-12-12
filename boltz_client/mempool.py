import json
import httpx
import websockets

from typing import Optional

from binascii import hexlify
from embit.transaction import Transaction
from loguru import logger

from .helpers import req_wrap


class MempoolApiException(Exception):
    pass


class MempoolClient:
    def __init__(self, url):
        self._api_url = url

        # just check of mempool is available
        print(self.get_blockheight())
        pass

    def request(self, funcname, *args, **kwargs):
        try:
            return req_wrap(funcname, *args, **kwargs)
        except httpx.RequestError as exc:
            msg = f"unreachable: {exc.request.url!r}."
            raise MempoolApiException(f"mempool api connection error: {msg}")
        except httpx.HTTPStatusError as exc:
            msg = f"{exc.response.status_code} while requesting {exc.request.url!r}. message: {exc.response.json()['error']}"
            raise MempoolApiException(f"mempool api status error: {msg}")


    def get_fee_estimation(self) -> Optional[int]:
        # TODO: hardcoded maximum tx size, in the future we try to get the size of the tx via embit
        # we need a function like Transaction.vsize()
        tx_size_vbyte = 200
        mempool_fees = self.get_fees()
        if not mempool_fees:
            return None
        return mempool_fees * tx_size_vbyte


    def get_fees(self) -> Optional[int]:
        data = self.request(
            "get",
            f"{self._api_url}/api/v1/fees/recommended",
            headers={"Content-Type": "application/json"},
        )
        if not data:
            return None
        return int(data["economyFee"])


    def get_blockheight(self) -> Optional[int]:
        data = self.request(
            "get",
            f"{self._api_url}/api/blocks/tip/height",
            headers={"Content-Type": "text/plain"},
        )
        if not data:
            return None
        return int(data)


    def get_txs_from_address(self, address: str):
        data = self.request(
            "get",
            f"{self._api_url}/api/address/{address}/txs",
            headers={"Content-Type": "text/plain"},
        )
        if data:
            return self.get_tx_from_txs(data, address)


    def get_tx_from_txs(self, txs, address):
        if len(txs) == 0:
            return None
        tx = txid = vout_cnt = vout_amount = None
        for a_tx in txs:
            for i, vout in enumerate(a_tx["vout"]):
                if vout["scriptpubkey_address"] == address:
                    tx = a_tx
                    txid = a_tx["txid"]
                    vout_cnt = i
                    vout_amount = vout["value"]

        return tx, txid, vout_cnt, vout_amount


    async def send_onchain_tx(self, tx: Transaction):
        raw = hexlify(tx.serialize())
        self.request(
            "post",
            f"{self._api_url}/api/tx",
            headers={"Content-Type": "text/plain"},
            content=raw,
        )


    async def wait_for_websocket_message(self, send, message_string):
        async for websocket in websockets.connect(websocket_url):
            try:
                await websocket.send(json.dumps({"action": "want", "data": ["blocks"]}))
                await websocket.send(json.dumps(send))
                async for raw in websocket:
                    message = json.loads(raw)
                    if message_string in message:
                        return message.get(message_string)
            except websockets.ConnectionClosed:
                continue


    async def wait_for_onchain_tx(self, lockup_address, callback):
        task, txs = await callback()
        mempool_lockup_tx = self.get_tx_from_txs(txs, lockup_address)
        if mempool_lockup_tx:
            tx, txid, *_ = mempool_lockup_tx
            if swap.instant_settlement or tx["status"]["confirmed"]:
                logger.debug(
                    f"Boltz - reverse swap instant settlement, claiming immediatly..."
                )
                await self.create_claim_tx(swap, mempool_lockup_tx)
            else:
                await self.start_confirmation_listener(swap, mempool_lockup_tx)
            try:
                if task:
                    await task
            except:
                logger.error(
                    f"Boltz - could not await pay_invoice task, but sent onchain. should never happen!"
                )
        else:
            logger.error(f"Boltz - mempool lockup tx not found.")