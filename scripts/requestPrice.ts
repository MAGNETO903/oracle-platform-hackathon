// scripts/requestPrice.ts
import { ethers } from "hardhat";
import { config as dotenvConfig } from "dotenv";
import { resolve } from "path";

dotenvConfig({ path: resolve(__dirname, "../.env") });

const simpleOracleAddress = process.env.SIMPLE_ORACLE_ADDRESS; // Адрес оракула из .env
const assetPair = "BTC/USDT"; // Какую пару запрашиваем

async function main() {
  if (!simpleOracleAddress) {
    throw new Error("Missing SIMPLE_ORACLE_ADDRESS in root .env file");
  }

  const [signer] = await ethers.getSigners(); // Берем дефолтный аккаунт из hardhat (с TESTNET_PRIVATE_KEY)
  console.log(`Requesting price using account: ${signer.address}`);

  const oracleContract = await ethers.getContractAt("SimpleOracle", simpleOracleAddress);

  // Преобразуем пару в bytes32 так же, как в бэкенде
  const assetIdBytes32 = ethers.encodeBytes32String(assetPair); // Используем ethers v6 способ
  // или const assetIdBytes32 = ethers.utils.formatBytes32String(assetPair); // для ethers v5
  // или const assetIdBytes32 = ethers.keccak256(ethers.toUtf8Bytes(assetPair)); // Если в бэкенде keccak

  // Убедись, что метод получения bytes32 совпадает с методом в oracle_service.py (ASSET_ID_MAP)!
  // Сейчас в oracle_service.py используется Web3.keccak(text=pair). Используем его же:
  const assetIdBytes32_keccak = ethers.keccak256(ethers.toUtf8Bytes(assetPair));

  const currentTimestamp = Math.floor(Date.now() / 1000); // Текущий Unix timestamp

  console.log(`Requesting price validation for asset: ${assetPair} (ID: ${assetIdBytes32_keccak}) at timestamp: ${currentTimestamp}`);

  const tx = await oracleContract.requestPriceValidation(
      assetIdBytes32_keccak, // Передаем bytes32
      currentTimestamp
  );
  console.log(`Transaction sent: ${tx.hash}`);
  await tx.wait();
  console.log(`Price validation requested successfully! Check oracle backend logs.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});