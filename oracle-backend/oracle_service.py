# --- START OF FILE oracle_service.py ---

# --- START OF FILE oracle_service.py ---

import time
import asyncio
import json # Added for ABI loading resilience
import logging # Added for better logging

# --- Imports for web3.py v7 ---
from web3 import AsyncWeb3
# --- ИЗМЕНЕНО ЗДЕСЬ: Added AsyncHTTPProvider import ---
from web3 import AsyncWeb3, AsyncHTTPProvider            # <- ✔ правильный импорт

# --- КОНЕЦ ИЗМЕНЕНИЯ ---
from web3.providers.persistent import WebSocketProvider # Already present in user's file for WS
from web3.middleware import ExtraDataToPOAMiddleware   # renamed PoA helper

# --- ИЗМЕНЕНО ЗДЕСЬ: SyncWeb3 for static helpers, AsyncWeb3 is aliased as Web3 by user further down ---
from web3 import Web3 as SyncWeb3 # Import the synchronous Web3 for static helpers
# --- КОНЕЦ ИЗМЕНЕНИЯ ---

from web3.exceptions import LogTopicError, MismatchedABI, ContractLogicError
from eth_account import Account # Для работы с приватным ключом
# --- ИЗМЕНЕНО ЗДЕСЬ: encode_typed_data import was present in user's new file ---
from eth_account.messages import encode_typed_data      # eth-account ≥ 0.13
# --- КОНЕЦ ИЗМЕНЕНИЯ ---


from binance import AsyncClient # Будем использовать асинхронный клиент
from binance.exceptions import BinanceAPIException
import config # Импортируем нашу конфигурацию
from typing import Union, Optional, Dict # Added Dict for type hint

# Setup logger
# --- ИЗМЕНЕНО ЗДЕСЬ: Logger name matches user's new file ---
logger = logging.getLogger("oracle_service")
# --- КОНЕЦ ИЗМЕНЕНИЯ ---
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Global variables
# --- ИЗМЕНЕНО ЗДЕСЬ: Type hint for latest_prices matches user's new file ---
latest_prices: Dict[str, Optional[dict]] = {}
# --- КОНЕЦ ИЗМЕНЕНИЯ ---
w3: Optional[AsyncWeb3] = None # Explicitly AsyncWeb3
simple_oracle_contract = None
# --- ИЗМЕНЕНО ЗДЕСЬ: Renamed variable to match instructions (already done in user file) ---
# oracle_contract = None -> simple_oracle_contract
# --- КОНЕЦ ИЗМЕНЕНИЯ ---
# event_filter = None # Not used in the new file from user, can be removed if not needed
oracle_signer_account: Optional[Account] = None
_log_loop_task: Optional[asyncio.Task] = None

# --- ИЗМЕНЕНО ЗДЕСЬ: Function signature matches user's new file ---
def get_latest_price_data(asset_pair: str) -> Optional[dict]:
# --- КОНЕЦ ИЗМЕНЕНИЯ ---
    """Возвращает последние данные о цене для API."""
    return latest_prices.get(asset_pair)

async def init_web3_and_contract() -> None: # Added return type hint for clarity
    """Асинхронная инициализация Web3 подключения и экземпляра контракта SimpleOracle (v7 compatible)."""
    global w3, simple_oracle_contract, oracle_signer_account


    logger.info("Initializing Web3 connection...")
    if not config.SEPOLIA_RPC_URL:
        # --- ИЗМЕНЕНО ЗДЕСЬ: Error message matches user's new file ---
        # logger.error("SEPOLIA_RPC_URL is not set in the environment variables.")
        # raise ValueError("SEPOLIA_RPC_URL is not configured.")
        raise ValueError("SEPOLIA_RPC_URL missing in .env")
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    # --- ИЗМЕНЕНО ЗДЕСЬ: ws_rpc_url defined and used correctly ---
    ws_rpc_url = (
        config.SEPOLIA_RPC_URL.replace("https://", "wss://", 1)
        .replace("http://", "ws://", 1)
    )
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    # --- Connection logic matches user's new file (WS preferred, HTTP fallback) ---
    try:
        # --- ИЗМЕНЕНО ЗДЕСЬ: Explicitly call provider.connect() for WebSocketProvider in v7 ---
        logger.info("Attempting WS provider %s", ws_rpc_url)
        provider = WebSocketProvider(
            ws_rpc_url,
            request_timeout=120, 
            websocket_kwargs={
                "open_timeout": 120, 
                "close_timeout": 60,
                "ping_interval": 30, 
                "ping_timeout": 60, 
            },
        )
        logger.info("WebSocketProvider instance created. Explicitly connecting...")
        await provider.connect() # <--- ЭТА СТРОКА УСТРАНЯЕТ ОШИБКУ ProviderConnectionError

        w3 = AsyncWeb3(provider)
        logger.info("Web3 instance created with WebSocketProvider.")
        
        # Теперь проверка is_connected() должна быть более надежной, или chain_id
        if not await w3.is_connected(): # Проверяем после connect()
             # Если connect() не вызвал ошибку, но is_connected все равно False, это странно
             logger.warning("WS provider.connect() succeeded but w3.is_connected() is False. Attempting chain_id.")
             chain_id_val = await w3.eth.chain_id
             logger.info("WebSocket chain_id check successful. Chain ID: %s", chain_id_val)
        else:
            chain_id_val = await w3.eth.chain_id
            logger.info("WebSocket connected successfully. Chain ID: %s", chain_id_val)

        # Инъекция PoA middleware
        logger.info("Injecting PoA middleware...") 
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        logger.info("PoA middleware injected.")
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    except asyncio.TimeoutError: # This specific exception for timeouts
         logger.error(f"Timeout connecting to WebSocket: {ws_rpc_url}", exc_info=True)
         logger.warning("WS failed due to Timeout. Falling back to AsyncHTTPProvider…")
         provider = AsyncHTTPProvider(
            config.SEPOLIA_RPC_URL, request_kwargs={"timeout": 60}
         )
         w3 = AsyncWeb3(provider)
         if not await w3.is_connected(): 
            raise ConnectionError("Both WS (Timeout) and HTTP endpoints unreachable")
         logger.info("HTTP connected (no event subscriptions after WS Timeout).")
         w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    except Exception as e: # Catch other WS connection errors (like ProviderConnectionError if connect() fails)
        logger.error(f"Failed to initialize Web3 via WebSocket: {type(e).__name__} - {e}", exc_info=True)
        logger.warning("WS failed (%s). Falling back to AsyncHTTPProvider…", e)
        provider = AsyncHTTPProvider(
            config.SEPOLIA_RPC_URL, request_kwargs={"timeout": 60}
        )
        w3 = AsyncWeb3(provider)
        if not await w3.is_connected(): 
            raise ConnectionError(f"Both WS ({type(e).__name__}) and HTTP endpoints unreachable")
        logger.info("HTTP connected (no event subscriptions after WS Error).")
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


    # Contract and signer setup matches user's new file
    # This part only runs if w3 was successfully initialized by either WS or HTTP
    abi = config.get_contract_abi("SimpleOracle")
    simple_oracle_contract = w3.eth.contract(
        address=AsyncWeb3.to_checksum_address(config.SIMPLE_ORACLE_ADDRESS),
        abi=abi,
    )
    oracle_signer_account = Account.from_key(config.TESTNET_PRIVATE_KEY)
    logger.info("Signer ready: %s", oracle_signer_account.address)


# --- Binance Functions ---
def _sym(pair: str) -> str: # Helper _sym matches user's new file
    return pair.replace("/", "")

async def _fetch_price(client: AsyncClient, pair: str) -> Optional[float]: # Signature and content matches user's new file
    try:
        ticker = await client.get_symbol_ticker(symbol=_sym(pair))
        return float(ticker["price"])
    except BinanceAPIException as e:
        logger.warning("Binance error for %s: %s", pair, e)
        return None

async def price_polling_loop(): # Price polling logic matches user's new file
    client = await AsyncClient.create()
    while True:
        ts = int(time.time())
        prices = await asyncio.gather(
            *[_fetch_price(client, p) for p in config.ASSET_PAIRS]
        )
        for pair, price in zip(config.ASSET_PAIRS, prices):
            if price is not None:
                latest_prices[pair] = {"price": price, "timestamp": ts}
                logger.info("Price %s → %f", pair, price)
        await asyncio.sleep(config.ORACLE_POLL_INTERVAL_SECONDS)


# --- Event Handling Logic ---

async def _eip712(pair: str, price: float, ts: int) -> dict: # _eip712 function structure and content matches user's new file AND apply chainId fix
    """Готовит структуру данных EIP-712 для подписи."""
    if not w3:
        raise ValueError("Web3 not initialized.")

    current_chain_id = await w3.eth.chain_id # Get current chain_id

    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "Price": [
                {"name": "pair", "type": "string"},
                {"name": "price", "type": "uint256"},
                {"name": "timestamp", "type": "uint256"},
            ],
        },
        "primaryType": "Price",
        "domain": {
            "name": "SimpleOracle",
            "version": "1",
            "chainId": current_chain_id,
            "verifyingContract": SyncWeb3.to_checksum_address(config.SIMPLE_ORACLE_ADDRESS),
        },
        "message": {"pair": pair, "price": int(price * 1e6), "timestamp": ts},
    }
    return typed_data

# _sign_eip712_data is NOT present in user's new file, removed to match.

async def _send_fulfillment_tx(pair: str, price: float, ts: int) -> None:
    """Отправляет транзакцию fulfillPriceRequest в контракт."""
    typed = await _eip712(pair, price, ts)                # <-- NEW
    msg   = encode_typed_data(full_message=typed)         # <-- NEW
    sig   = oracle_signer_account.sign_message(msg).signature

    func = simple_oracle_contract.functions.fulfillPriceRequest(
        pair, int(price * 1e6), ts, sig
    )
    nonce      = await w3.eth.get_transaction_count(oracle_signer_account.address)
    gas_price  = await w3.eth.gas_price
    tx_params  = {
        "from": oracle_signer_account.address,
        "nonce": nonce,
        "gas": 300_000,
        "maxFeePerGas": gas_price,
        "maxPriorityFeePerGas": gas_price,
    }

    tx      = await func.build_transaction(tx_params)
    signed  = oracle_signer_account.sign_transaction(tx)
    tx_hash = await w3.eth.send_raw_transaction(signed.rawTransaction)
    logger.info("Tx sent %s", tx_hash.hex())
    await w3.eth.wait_for_transaction_receipt(tx_hash)

# Separate handle_event removed as logic is in _log_loop in user's new file.

async def get_signed_price_data(asset_pair: str) -> Optional[dict]:
    """
    Возвращает последние данные о цене для asset_pair вместе с подписью EIP-712.
    """
    global ASSET_ID_MAP, w3, oracle_signer_account # Убедимся, что глобальные переменные доступны
    price_data = get_latest_price_data(asset_pair)
    if not price_data:
        logger.warning(f"No price data available for {asset_pair} to sign.")
        return None

    # Проверяем инициализацию Web3 и аккаунта
    if not w3 or not oracle_signer_account:
         logger.error("Web3 or Signer Account not initialized, cannot sign price.")
         return None

    asset_id_bytes = ASSET_ID_MAP.get(asset_pair) # Get bytes32 ID for the pair
    if not asset_id_bytes: # If asset_pair is not in ASSET_ID_MAP (e.g. not tracked)
        logger.error(f"Asset pair {asset_pair} not found in ASSET_ID_MAP for signing or its ID is None.")
        return None

    # Get price and timestamp from stored data
    price_float = price_data['price']
    timestamp = price_data['timestamp']

    # Convert price to uint256
    # Based on _eip712 in the user's file, it uses int(price * 1e6) -> 6 decimals.
    PRICE_DECIMALS = 6 # Match the decimals used in _eip712
    try:
        price_uint256 = int(price_float * (10**PRICE_DECIMALS))
    except (ValueError, TypeError):
        logger.error(f"Cannot convert price {price_float} to uint{PRICE_DECIMALS} for signing {asset_pair}.")
        return None

    try:
        # Готовим данные EIP-712 (используя _eip712)
        # _eip712 function expects (pair: str, price: float, ts: int)
        logger.debug(f"Preparing EIP-712 for off-chain API: {asset_pair}")
        typed_data = await _eip712(asset_pair, price_float, timestamp) # Use _eip712 as defined in user's file

        # Подписываем данные (logic from user's _send_fulfillment_tx)
        msg_hash = encode_typed_data(full_message=typed_data) # Используем encode_typed_data
        signature = oracle_signer_account.sign_message(msg_hash).signature # Подписываем хэш
        logger.debug(f"Signed off-chain price for {asset_pair}")

        # Return data package including signature
        return {
            "assetPair": asset_pair,
            "assetId": asset_id_bytes.hex(),    # <--- ВОЗВРАЩАЕМ assetId в hex
            "price": str(price_float),          # Price as string float
            "priceUint256": str(price_uint256), # Price as string uint256 (with 6 decimals)
            "timestamp": timestamp,
            "signature": signature.hex()        # Signature in hex format
        }
    except Exception as e:
        logger.error(f"Failed to get signed price data for {asset_pair}: {e}", exc_info=True)
        return None


async def _log_loop():
    """Обрабатывает событие PriceRequested."""
    # --- ИЗМЕНЕНО ЗДЕСЬ: Step 2 & 3 - Listen for PriceValidationRequested and adjust fromBlock ---
    event_to_listen = "PriceValidationRequested" # Assuming this is the correct event from contract
    
    if not hasattr(simple_oracle_contract.events, event_to_listen):
        logger.error(f"Event '{event_to_listen}' not found in contract ABI. Available events: {[e.event_name for e in simple_oracle_contract.events if hasattr(e, 'event_name')]}")
        # If the event is critical and not found, we should not proceed with creating a filter for it.
        # Consider how the application should behave. For now, just log and return to prevent crashing the loop.
        logger.info("Cannot start log loop without a valid event to listen to.")
        return # Exit _log_loop if the event is not available

    current_block = await w3.eth.block_number
    # Start listening from current_block - 1 to catch events in the same block as startup
    # or simply current_block. Using current_block might be safer if node has slight delays.
    # Using current_block to be safe, adjust to current_block - 1 if events are missed.
    filter_from_block = current_block 
    logger.info(f"Creating event filter for '{event_to_listen}' from block {filter_from_block}.")

    flt = await simple_oracle_contract.events[event_to_listen].create_filter(
        from_block=filter_from_block 
    )
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    while True:
        try:
            for ev in await flt.get_new_entries():
                # --- ИЗМЕНЕНО ЗДЕСЬ: Step 4 - Add debug log for received event ---
                logger.info("⚡ New event: %s", ev) 
                # --- КОНЕЦ ИЗМЕНЕНИЯ ---
                tx_hash_hex = ev.get('transactionHash', b'').hex()
                block_num = ev.get('blockNumber', 'N/A')
                logger.info(f"\n--- Received event {event_to_listen} (Tx: {tx_hash_hex[:10]}..., Blk: {block_num}) ---")

                try:
                    args = ev['args']
                    # Adapt to 'assetId' (bytes32) from PriceValidationRequested event
                    if 'assetId' in args:
                        asset_id_from_event_bytes = args['assetId']
                        pair_from_event = next((p for p, b_id in ASSET_ID_MAP.items() if b_id == asset_id_from_event_bytes), None)
                        if not pair_from_event:
                            logger.error(f"  Cannot map assetId {asset_id_from_event_bytes.hex()} from event to known pair.")
                            continue
                        logger.info(f"  AssetId from Event: {asset_id_from_event_bytes.hex()} (Mapped to: {pair_from_event})")
                    # Fallback or alternative if event uses 'pair' string (less likely for PriceValidationRequested)
                    elif 'pair' in args: 
                        pair_from_event = args['pair']
                        logger.warning(f"  Event uses 'pair' string: {pair_from_event}. Ensure this matches contract and EIP712 logic if PriceValidationRequested is used.")
                    else:
                        logger.error("  Event args do not contain 'assetId' or 'pair'.")
                        continue
                        
                    timestamp_requested = args['timestamp']
                    requester = args['requester']
                    logger.info(f"  Timestamp Requested: {timestamp_requested}, Requester: {requester}")
                except KeyError as ke: logger.error(f"  Event parse err: {ke}."); continue
                except Exception as parse_e: logger.error(f"  Event parse err: {parse_e}.", exc_info=True); continue

                price_data = get_latest_price_data(pair_from_event)
                if not price_data:
                     logger.warning(f"  No price data found locally for {pair_from_event} to fulfill request.")
                     continue

                last_price_timestamp = price_data['timestamp']
                MAX_TIMESTAMP_DIFF = config.ORACLE_POLL_INTERVAL_SECONDS * 2 + 5

                if abs(last_price_timestamp - timestamp_requested) > MAX_TIMESTAMP_DIFF:
                    logger.warning(f"  Timestamp difference too large for {pair_from_event}. Requested: {timestamp_requested}, Last Available: {last_price_timestamp}. Max diff: {MAX_TIMESTAMP_DIFF}. Skipping fulfillment.")
                    continue

                price_float = price_data['price']
                timestamp_to_fulfill = timestamp_requested
                PRICE_DECIMALS = 6 
                
                logger.info(f"  Fulfilling request for {pair_from_event}")
                logger.info(f"  Using price: {price_float} (uint256 for EIP712: {int(price_float * (10**PRICE_DECIMALS))})")
                logger.info(f"  Using timestamp: {timestamp_to_fulfill} (from request)")
                
                # _send_fulfillment_tx expects 'pair' (string), price (float), ts (int)
                # This matches the current signature of _send_fulfillment_tx
                await _send_fulfillment_tx(
                    pair=pair_from_event, 
                    price=price_float,
                    ts=timestamp_to_fulfill
                )
                logger.info(f"--- Event processing finished for {pair_from_event} (Tx: {tx_hash_hex[:10]}...) ---")
        except LogTopicError as e:
            logger.warning("LogTopicError: %s", e)
        except Exception as exc:
            logger.error("Listener error: %s", exc, exc_info=True)
        await asyncio.sleep(2)


# --- ИЗМЕНЕНО ЗДЕСЬ: Added type hint and robust return logic ---
async def event_listener_startup() -> bool: 
    global _log_loop_task
    try:
        # Ensure WebSocket connection for event listening
        if not (w3 and w3.provider and isinstance(w3.provider, WebSocketProvider) and await w3.is_connected()):
             logger.warning("Cannot start event listener: Web3 not connected via WebSocket.")
             return False

        if _log_loop_task is None or _log_loop_task.done():
            logger.info("Creating and starting new event listener task (_log_loop).")
            _log_loop_task = asyncio.create_task(_log_loop())
            # Add a callback to log when the task finishes, for debugging
            def _task_done_callback(task: asyncio.Task):
                try:
                    task.result() # Raises exception if task failed
                    logger.info(f"Event listener task '{task.get_name()}' completed.")
                except asyncio.CancelledError:
                    logger.info(f"Event listener task '{task.get_name()}' was cancelled.")
                except Exception:
                    logger.exception(f"Event listener task '{task.get_name()}' failed with an exception:")
            _log_loop_task.add_done_callback(_task_done_callback)
        else:
            logger.info("Event listener task already running.")
        logger.info("Event listener startup sequence completed (task created/verified).")
        return True
    except Exception as e:
        logger.error(f"Failed to start event listener task: {e}", exc_info=True)
        return False
# --- КОНЕЦ ИЗМЕНЕНИЯ ---


async def event_listener_shutdown():
    if _log_loop_task and not _log_loop_task.done():
        _log_loop_task.cancel()
        try:
            await _log_loop_task
        except asyncio.CancelledError:
            pass
        logger.info("Event listener stopped")


# --- Asset ID Map ---
ASSET_ID_MAP = {}
try:
    if not config.ASSET_PAIRS or not isinstance(config.ASSET_PAIRS, list):
         logger.warning("ASSET_PAIRS empty/invalid.")
    else:
        ASSET_ID_MAP = {pair: SyncWeb3.keccak(text=pair) for pair in config.ASSET_PAIRS}
        logger.info("Asset ID Map created:")
        for pair, id_bytes in ASSET_ID_MAP.items(): logger.info(f"  '{pair}': {id_bytes.hex()}")
except Exception as e: logger.error(f"Err creating ASSET_ID_MAP: {e}", exc_info=True)


# --- Test Loop (Matches user's new file) ---
async def _main():
    await init_web3_and_contract()
    await event_listener_startup()
    await price_polling_loop()

if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("Interrupted; shutting down")

# --- END OF FILE oracle_service.py ---