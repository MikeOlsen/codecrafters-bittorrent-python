import hashlib
from inspect import findsource
import logging
import os
import struct
import asyncio
from typing import final
from tqdm.asyncio import tqdm

from app.utils import (
    calculate_piece_length,
    get_piece_hashes,
)

PROTOCOL_HEADER = b"\x13BitTorrent protocol"
RESERVED_BYTES = b"\x00" * 8
PEER_ID = os.urandom(20)

HANDSHAKE_LENGTH = 68
BLOCK_LENGTH = 16 * 1024

PEER_ID_INDEX = 48
MESSAGE_ID_INDEX = 4

UNCHOKE = 1
INTERESTED = 2
BITFIELD = 5
REQUEST = 6
PIECE = 7

MAX_CONCURRENT_TASKS = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)


class AsyncBittorrent:

    def __init__(self):
        self.reader = None
        self.writer = None

    async def connect(self, host: str, port: int):
        self.reader, self.writer = await asyncio.open_connection(host, port)

    async def handshake(self, torrent):
        if not self.reader or not self.writer:
            raise Exception("Not connected")

        self.torrent = torrent
        handshake = PROTOCOL_HEADER + RESERVED_BYTES + torrent["info_hash"] + PEER_ID

        self.writer.write(handshake)
        await self.writer.drain()

        response = await self.reader.read(HANDSHAKE_LENGTH)
        return response[PEER_ID_INDEX:].hex()

    async def init_peer_communication(self):
        await self.wait_for_reply(BITFIELD)
        await self.send(INTERESTED)
        await self.wait_for_reply(UNCHOKE)

    async def send(self, message_id: int, payload=b""):
        if not self.reader or not self.writer:
            raise Exception("Not connected")

        length = len(payload) + 1
        message = struct.pack(">IB", length, message_id) + payload
        self.writer.write(message)
        await self.writer.drain()

    async def receive(self, length):
        if not self.reader or not self.writer:
            raise Exception("Not connected")
        chunks = []
        bytes_recd = 0
        while bytes_recd < length:
            chunk = await self.reader.read(min(length - bytes_recd, 2048))
            chunks.append(chunk)
            bytes_recd += len(chunk)
        return b"".join(chunks)

    async def receive_message(self) -> tuple[int, bytes]:
        header = await self.receive(5)
        length, message_id = struct.unpack(">IB", header)
        payload_length = length - 1

        payload = await self.receive(payload_length) if payload_length > 0 else b""
        return message_id, payload

    async def wait_for_reply(self, desired_message_id: int) -> bytes:
        message_id, message = await self.receive_message()
        while message_id != desired_message_id:
            message_id, message = await self.receive_message()
        return message

    async def download_block(self, index, begin, length):
        await self.send(REQUEST, struct.pack(">III", index, begin, length))
        reply = await self.wait_for_reply(PIECE)
        return reply[8:]

    async def download_piece(self, torrent, piece_index):

        piece_length = calculate_piece_length(torrent, piece_index)
        block_count = piece_length // BLOCK_LENGTH
        last_block_length = piece_length % BLOCK_LENGTH

        data = b""
        for index in range(block_count):
            data += await self.download_block(
                index=piece_index,
                begin=index * BLOCK_LENGTH,
                length=BLOCK_LENGTH,
            )
        if last_block_length > 0:
            data += await self.download_block(
                index=piece_index,
                begin=block_count * BLOCK_LENGTH,
                length=last_block_length,
            )

        # Verify piece hash
        hashes = get_piece_hashes(torrent)
        if hashlib.sha1(data).hexdigest() != hashes[piece_index]:
            raise ConnectionError(f"Incorrect sha1 for piece {piece_index}")

        return data


async def handshake(host: str, port: int, torrent):
    bittorrent = AsyncBittorrent()
    await bittorrent.connect(host, port)
    return await bittorrent.handshake(torrent)


async def download_piece_from_peer(peer, piece_index, torrent) -> bytes:
    bittorrent = AsyncBittorrent()
    async with semaphore:
        await bittorrent.connect(*peer)
        await bittorrent.handshake(torrent)
        await bittorrent.init_peer_communication()

        return await bittorrent.download_piece(torrent, piece_index)


async def download_all_pieces(peers, torrent):
    piece_hashes = get_piece_hashes(torrent)

    tasks = []
    for piece_index in range(0, len(piece_hashes)):
        peer = peers[piece_index % len(peers)]
        tasks.append(
            asyncio.create_task(download_piece_from_peer(peer, piece_index, torrent))
        )

    return await tqdm.gather(*tasks, bar_format="{l_bar}{bar:50}{r_bar}")
