import socket
import pytest
from time import sleep
from librouteros.query import Key
from librouteros import connect, async_connect
from librouteros.exceptions import LibRouterosError


def test_login(routeros_login):
    port, method = routeros_login("sync")
    api = None
    for _ in range(30):
        try:
            api = connect(
                host="127.0.0.1",
                port=port,
                username="admin",
                password="",
                login_method=method,
            )
            break
        except (LibRouterosError, socket.error, socket.timeout):
            sleep(1)

    data = api("/system/identity/print")
    assert tuple(data)[0]["name"] == "MikroTik"


@pytest.mark.asyncio
async def test_login_async(routeros_login):
    port, method = routeros_login("async")
    api = None
    for _ in range(30):
        try:
            api = await async_connect(
                host="127.0.0.1",
                port=port,
                username="admin",
                password="",
                login_method=method,
                timeout=60,
            )
            break
        except (LibRouterosError, socket.error, socket.timeout):
            sleep(1)

    result = [r async for r in api("/system/identity/print")]
    assert result[0]["name"] == "MikroTik"


def test_query(routeros_api):
    new_address = "172.16.1.1/24"
    result = routeros_api(
        "/ip/address/add",
        address=new_address,
        interface="ether1",
    )
    created_id = tuple(result)[0]["ret"]

    _id = Key(".id")
    address = Key("address")
    query = (
        routeros_api.path("/ip/address")
        .select(_id, address)
        .where(
            _id == created_id,
            address == new_address,
        )
    )
    selected_data = tuple(query)
    assert len(selected_data) == 1
    assert selected_data[0][".id"] == created_id
    assert selected_data[0]["address"] == new_address


@pytest.mark.asyncio
async def test_query_async(routeros_api_async):
    new_address = "172.16.1.1/24"
    result = [
        r
        async for r in routeros_api_async(
            "/ip/address/add",
            address=new_address,
            interface="ether1",
        )
    ]
    created_id = result[0]["ret"]

    _id = Key(".id")
    address = Key("address")
    selected_data = [
        r
        async for r in routeros_api_async.path("/ip/address")
        .select(_id, address)
        .where(
            _id == created_id,
            address == new_address,
        )
    ]
    assert len(selected_data) == 1
    assert selected_data[0][".id"] == created_id
    assert selected_data[0]["address"] == new_address


@pytest.mark.parametrize(
    "addresses",
    (
        {"172.16.1.1/24", "172.16.1.2/24"},
        {"172.16.1.1/24", "172.16.1.2/24", "1.1.1.1/24"},
        {"172.16.1.2/24"},
    ),
)
def test_query_In_operator(routeros_api, addresses):
    addr_path = routeros_api.path("/ip/address")
    for addr in addresses:
        addr_path.add(interface="ether1", address=addr)

    address = Key("address")
    query = addr_path.select(address).where(address.In(*addresses))
    assert addresses == set(row["address"] for row in query)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addresses",
    (
        {"172.16.1.1/24", "172.16.1.2/24"},
        {"172.16.1.1/24", "172.16.1.2/24", "1.1.1.1/24"},
        {"172.16.1.2/24"},
    ),
)
async def test_query_In_operator_async(routeros_api_async, addresses):
    addr_path = routeros_api_async.path("/ip/address")
    for addr in addresses:
        await addr_path.add(interface="ether1", address=addr)

    address = Key("address")
    result = [r async for r in addr_path.select(address).where(address.In(*addresses))]
    assert addresses == set(row["address"] for row in result)


def test_long_word(routeros_api):
    r"""
    Assert that when word length is encoded with \x00 in it,
    library should decode this without errors.

    Create a entry with long word length (256)
    resulting in word encoding of \x81\00.
    Check if when reading back, comment is same when set.
    """
    long_value = "a" * (256 - len("=comment="))
    data = routeros_api(
        "/ip/address/add",
        address="172.16.1.1/24",
        interface="ether1",
        comment=long_value,
    )
    _id = tuple(data)[0]["ret"]
    for row in routeros_api("/ip/address/print"):
        if row[".id"] == _id:
            assert row["comment"] == long_value


@pytest.mark.asyncio
async def test_long_word_async(routeros_api_async):
    r"""
    Assert that when word length is encoded with \x00 in it,
    library should decode this without errors.

    Create a entry with long word length (256)
    resulting in word encoding of \x81\00.
    Check if when reading back, comment is same when set.
    """
    long_value = "a" * (256 - len("=comment="))
    data = [
        r
        async for r in routeros_api_async(
            "/ip/address/add",
            address="172.16.1.1/24",
            interface="ether1",
            comment=long_value,
        )
    ]
    _id = data[0]["ret"]
    async for row in routeros_api_async("/ip/address/print"):
        if row[".id"] == _id:
            assert row["comment"] == long_value
