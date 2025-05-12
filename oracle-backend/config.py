import os
import json
from dotenv import load_dotenv

# Загружаем переменные из .env файла в текущей директории
# Либо можно указать путь: load_dotenv(dotenv_path='../.env') если .env в корне
load_dotenv()

# Сеть и ключи
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL")
TESTNET_PRIVATE_KEY = os.getenv("TESTNET_PRIVATE_KEY")
ORACLE_SIGNER_ADDRESS = os.getenv("ORACLE_SIGNER_ADDRESS")

# Адреса контрактов
KYC_WHITELIST_ADDRESS = os.getenv("KYC_WHITELIST_ADDRESS")
SIMPLE_ORACLE_ADDRESS = os.getenv("SIMPLE_ORACLE_ADDRESS")

# Настройки получения цен
ORACLE_POLL_INTERVAL_SECONDS = int(os.getenv("ORACLE_POLL_INTERVAL_SECONDS", "10"))
# Загружаем и парсим JSON-массив строк с парами
try:
    ASSET_PAIRS = json.loads(os.getenv("ASSET_PAIRS", '["BTC/USDT", "ETH/USDT"]'))
    if not isinstance(ASSET_PAIRS, list):
        raise ValueError("ASSET_PAIRS should be a list")
except (json.JSONDecodeError, ValueError) as e:
    print(f"Error parsing ASSET_PAIRS from .env: {e}. Using default.")
    ASSET_PAIRS = ["BTC/USDT", "ETH/USDT"] # Значение по умолчанию

# Проверка наличия обязательных переменных
required_vars = [
    "SEPOLIA_RPC_URL",
    "TESTNET_PRIVATE_KEY",
    "ORACLE_SIGNER_ADDRESS",
    "KYC_WHITELIST_ADDRESS",
    "SIMPLE_ORACLE_ADDRESS",
]
missing_vars = [var for var in required_vars if not globals().get(var)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Константы для ABI (пути к файлам) - мы их создадим позже
# Обычно артефакты компиляции Hardhat лежат в папке artifacts
# Путь будет примерно такой, если backend внутри основного проекта
ARTIFACTS_DIR = os.path.join("..", "artifacts", "contracts") # Выходим на уровень выше
SIMPLE_ORACLE_ABI_PATH = os.path.join(ARTIFACTS_DIR, "SimpleOracle.sol", "SimpleOracle.json")
# KYC_WHITELIST_ABI_PATH = os.path.join(ARTIFACTS_DIR, "KYCWhitelist.sol", "KYCWhitelist.json") # Если понадобится

print("Configuration loaded successfully:")
print(f"  RPC URL: {SEPOLIA_RPC_URL[:20]}...") # Печатаем только начало для безопасности
print(f"  Oracle Signer: {ORACLE_SIGNER_ADDRESS}")
print(f"  KYC Whitelist: {KYC_WHITELIST_ADDRESS}")
print(f"  Simple Oracle: {SIMPLE_ORACLE_ADDRESS}")
print(f"  Poll Interval: {ORACLE_POLL_INTERVAL_SECONDS}s")
print(f"  Asset Pairs: {ASSET_PAIRS}")

# Важно: Добавим простую функцию для получения ABI
def get_contract_abi(contract_name: str) -> list:
    """Загружает ABI контракта из артефакта Hardhat."""
    abi_path = os.path.join(ARTIFACTS_DIR, f"{contract_name}.sol", f"{contract_name}.json")
    if not os.path.exists(abi_path):
         raise FileNotFoundError(f"ABI file not found at {abi_path}. Did you compile contracts?")
    try:
        with open(abi_path, 'r') as f:
            artifact = json.load(f)
            return artifact.get("abi")
    except Exception as e:
        print(f"Error loading ABI from {abi_path}: {e}")
        raise