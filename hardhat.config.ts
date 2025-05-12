 import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import "dotenv/config"; // Добавили импорт dotenv

// Проверяем наличие переменных окружения
const sepoliaRpcUrl = process.env.SEPOLIA_RPC_URL;
if (!sepoliaRpcUrl) {
  console.error("Missing SEPOLIA_RPC_URL in .env file");
  // process.exit(1); // Можно раскомментировать, чтобы прервать выполнение, если URL нет
}

const privateKey = process.env.TESTNET_PRIVATE_KEY;
if (!privateKey) {
  console.error("Missing TESTNET_PRIVATE_KEY in .env file");
  // process.exit(1); // Можно раскомментировать
}

const config: HardhatUserConfig = {
  solidity: "0.8.24", // Убедись, что версия совпадает или совместима с той, что в контрактах
  networks: {
    hardhat: {
      // Конфигурация для локальной сети hardhat (если нужна)
    },
    sepolia: {
      url: sepoliaRpcUrl || "", // Используем переменную или пустую строку
      accounts: privateKey ? [privateKey] : [], // Используем ключ или пустой массив
    },
    // Можно добавить другие сети по аналогии
  },
  // Можно добавить другие настройки: etherscan, gasReporter и т.д.
};

export default config;