# --- START OF FILE main.py ---

# --- START OF FILE main.py ---

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import asyncio
import logging
from pydantic import BaseModel
from typing import Optional, Union

import config # Наша конфигурация
import oracle_service # Наш сервис получения цен

# Настройка базового логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic Модели для ответов ---

class PriceResponse(BaseModel):
    """Response model for the /price/{asset_pair} endpoint."""
    assetPair: str
    price: str # Keeping as string as returned by the function
    timestamp: int

class PriceData(BaseModel):
    """Nested model for price data within the status response."""
    price: float # Assuming price in latest_prices is float/Decimal
    timestamp: int

class EventListenerStatus(BaseModel):
     """Nested model for event listener status."""
     active: bool
     web3_connected: bool
     chain_id: Optional[int] # Chain ID can be None if not connected
     contract_address: Optional[str] # Address from config
     signer_address: Optional[str] # Signer address can be None if init failed

class StatusResponse(BaseModel):
    """Response model for the /status endpoint."""
    tracked_pairs: list[str]
    latest_prices: dict[str, Optional[PriceData]] # Use Optional[PriceData] for values
    binance_polling_interval_seconds: int
    event_listener: EventListenerStatus # Use the nested model

# --- ИЗМЕНЕНО ЗДЕСЬ: Added new Pydantic model ---
class SignedPriceResponse(BaseModel):
    assetPair: str
    assetId: str # hex string
    price: str   # float as string
    priceUint256: str # uint256 as string
    timestamp: int
    signature: str # hex string
# --- КОНЕЦ ИЗМЕНЕНИЯ ---

# --- Жизненный цикл FastAPI приложения ---

price_poller_task: Optional[asyncio.Task] = None # Added type hint
event_listener_active = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global price_poller_task, event_listener_active
    logger.info("Application startup...")

    # Инициализация Web3 и контракта (асинхронно)
    logger.info("Initializing Web3 and Contract...")
    try:
        await oracle_service.init_web3_and_contract() # This function is now async
        if not oracle_service.w3 or not oracle_service.simple_oracle_contract: # Check correct contract variable name
            logger.error("Web3/Contract object not available after initialization.")
            # Decide if the app should stop here or continue degraded
        else:
            logger.info("Web3 and Contract initialized successfully.")
    except Exception as init_e:
        logger.error(f"Fatal error during Web3/Contract initialization: {init_e}", exc_info=True)
        # App might not be able to function, consider raising or exiting
        # For now, log the error and let it continue (listener won't start)

    # Запускаем фоновую задачу опроса цен Binance
    logger.info("Starting price polling task...")
    price_poller_task = asyncio.create_task(oracle_service.price_polling_loop())
    app.state.price_poller_task = price_poller_task # Store if needed elsewhere
    logger.info("Price polling task started.")

    # Запускаем прослушивание событий контракта
    # Only if Web3 init was successful and contract object exists
    if oracle_service.w3 and oracle_service.simple_oracle_contract: # Check correct name
        logger.info("Starting event listener...")
        try:
            # Start listener and check return value (now returns bool)
            listener_started = await oracle_service.event_listener_startup() # This is async now
            event_listener_active = listener_started # Set flag based on success
            if listener_started:
                logger.info("Event listener started successfully.")
            else:
                logger.error("Event listener startup returned failure.")
        except Exception as e:
            logger.error(f"Failed to start event listener: {e}", exc_info=True)
            event_listener_active = False
    else:
         logger.warning("Skipping event listener startup (Web3/Contract init failed or objects missing).")
         event_listener_active = False

    yield # Application runs here

    # Shutdown logic
    logger.info("Application shutting down...")
    # Cancel price poller task
    if price_poller_task and not price_poller_task.done():
        logger.info("Cancelling price polling task...")
        price_poller_task.cancel()
        try:
            await asyncio.wait_for(price_poller_task, timeout=5.0)
        except asyncio.CancelledError: logger.info("Price polling task cancelled.")
        except asyncio.TimeoutError: logger.warning("Price polling task did not finish cancellation in time.")
        except Exception as e: logger.error(f"Error during price poller task shutdown: {e}", exc_info=True)

    # Shutdown event listener
    if event_listener_active: # Only shutdown if it was successfully started
        logger.info("Attempting to shut down event listener...")
        try:
            await oracle_service.event_listener_shutdown() # This is async now
            logger.info("Event listener shutdown completed.")
        except Exception as e:
            logger.error(f"Error during event listener shutdown: {e}", exc_info=True)

    logger.info("Shutdown complete.")

# Create FastAPI app instance
app = FastAPI(lifespan=lifespan, title="Simple Oracle Backend")

# --- API эндпоинты ---

@app.get("/", summary="Root", tags=["General"])
async def read_root():
    """Returns a welcome message."""
    return {"message": "Simple Oracle Backend is running"}

@app.get("/price/{asset_pair}", summary="Get Asset Price", tags=["Price Data"], response_model=PriceResponse)
async def get_price(asset_pair: str):
    """
    Returns the latest price data for the specified asset pair.
    Use '-' as separator, e.g., /price/BTC-USDT
    """
    formatted_pair = asset_pair.upper().replace('-', '/')
    logger.info(f"Received price request for {asset_pair} (formatted: {formatted_pair})")

    if formatted_pair not in config.ASSET_PAIRS:
         logger.warning(f"Asset pair '{formatted_pair}' not tracked.")
         raise HTTPException(status_code=404, detail=f"Asset pair '{formatted_pair}' is not tracked.")

    price_data = oracle_service.get_latest_price_data(formatted_pair)

    if price_data is None:
        logger.warning(f"Price data for '{formatted_pair}' not available yet.")
        raise HTTPException(status_code=404, detail=f"Price data for '{formatted_pair}' not available yet.")

    response_data = {
        "assetPair": formatted_pair,
        "price": str(price_data["price"]),
        "timestamp": price_data["timestamp"],
    }
    logger.info(f"Returning price data for {formatted_pair}: {response_data}")
    return response_data


# --- ИЗМЕНЕНО ЗДЕСЬ: Added new endpoint ---
@app.get(
    "/signed_price/{asset_pair}",
    summary="Get Signed Asset Price",
    tags=["Price Data"],
    response_model=SignedPriceResponse # Используем новую модель
)
async def get_signed_price(asset_pair: str):
    """
    Returns the latest price data for the specified asset pair,
    along with an EIP-712 signature from the oracle signer.
    Use '-' as separator, e.g., /signed_price/BTC-USDT
    """
    formatted_pair = asset_pair.upper().replace('-', '/')
    logger.info(f"Received signed price request for {asset_pair} (formatted: {formatted_pair})")

    if formatted_pair not in config.ASSET_PAIRS:
         logger.warning(f"Asset pair '{formatted_pair}' not tracked.")
         raise HTTPException(status_code=404, detail=f"Asset pair '{formatted_pair}' not tracked.")

    # Вызываем новую функцию сервиса (она async)
    signed_data = await oracle_service.get_signed_price_data(formatted_pair)

    if signed_data is None:
        # Log details if possible from service layer, here just report failure
        logger.error(f"Failed to get signed price data for {formatted_pair}.")
        # Use 500 for server-side issue (like signing failure), or 404 if price simply wasn't found?
        # Let's assume 500 if the function was called but failed.
        raise HTTPException(status_code=500, detail=f"Could not retrieve or sign price data for {formatted_pair}.")

    logger.info(f"Returning signed price data for {formatted_pair}")
    # FastAPI/Pydantic преобразует dict в SignedPriceResponse
    return signed_data
# --- КОНЕЦ ИЗМЕНЕНИЯ ---


@app.get("/status", summary="Get Oracle Status", tags=["General"], response_model=StatusResponse)
async def get_status():
    """Returns the current status of the oracle backend."""
    global event_listener_active
    web3_connected = False
    chain_id = None
    signer_address = None
    contract_address = config.SIMPLE_ORACLE_ADDRESS # Get from config

    # Check connection status safely using await
    if oracle_service.w3:
        try:
            # w3.is_connected() is async with AsyncWeb3
            web3_connected = await oracle_service.w3.is_connected()
            if web3_connected:
                 # w3.eth.chain_id is async
                 chain_id = await oracle_service.w3.eth.chain_id
            else: # Ensure chain_id is None if not connected
                 chain_id = None
        except Exception as conn_err:
            logger.error(f"Error checking Web3 connection status: {conn_err}", exc_info=False)
            web3_connected = False
            chain_id = None # Ensure chain_id is None on error

    if oracle_service.oracle_signer_account:
        signer_address = oracle_service.oracle_signer_account.address

    # Prepare latest_prices dictionary for Pydantic validation
    latest_prices_prepared = {}
    for pair, data in oracle_service.latest_prices.items():
        if data:
            try:
                # Validate and convert data using the PriceData model
                latest_prices_prepared[pair] = PriceData(price=float(data['price']), timestamp=int(data['timestamp']))
            except (ValueError, TypeError, KeyError) as e:
                 logger.error(f"Error processing status price data for {pair}: {data}. Error: {e}")
                 latest_prices_prepared[pair] = None # Mark as None if invalid
        else:
            latest_prices_prepared[pair] = None

    status_data = {
        "tracked_pairs": config.ASSET_PAIRS,
        "latest_prices": latest_prices_prepared,
        "binance_polling_interval_seconds": config.ORACLE_POLL_INTERVAL_SECONDS,
        "event_listener": {
             "active": event_listener_active,
             "web3_connected": web3_connected,
             "chain_id": chain_id,
             "contract_address": contract_address, # Use address from config
             "signer_address": signer_address
        }
    }
    return status_data # Return dict, FastAPI converts using response_model

# --- Запуск сервера (если файл запускается напрямую) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, lifespan="on") # Ensure lifespan is enabled

# --- END OF FILE main.py ---