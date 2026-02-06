import pytest
import asyncio


def test_example():
    """Simple example test to verify pytest is working"""
    assert 1 + 1 == 2


async def test_async_example():
    """Simple async example test"""
    await asyncio.sleep(0.1)
    assert True


@pytest.mark.asyncio
async def test_pytest_asyncio():
    """Test that pytest-asyncio is working"""
    await asyncio.sleep(0.1)
    assert True


@pytest.fixture
def sample_data():
    """Sample fixture for tests"""
    return {"key": "value"}


def test_with_fixture(sample_data):
    """Test using fixture"""
    assert sample_data["key"] == "value"
