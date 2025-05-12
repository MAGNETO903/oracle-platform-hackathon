// scripts/requestOldPrice.ts
import { ethers } from "hardhat";
import { config as dotenvConfig } from "dotenv";
import { resolve } from "path";

dotenvConfig({ path: resolve(__dirname, "../.env") });

const simpleOracleAddress = process.env.SIMPLE_ORACLE_ADDRESS; // Адрес оракула из .env
const assetPair = "BTC/USDT"; // Какую пару запрашиваем
const minutesAgo = 5; // На сколько минут назад сдвинуть timestamp

async function main() {
  if (!simpleOracleAddress) {
    throw new Error("Missing SIMPLE_ORACLE_ADDRESS in root .env file");
  }

  const [signer] = await ethers.getSigners();
  console.log(`Requesting price using account: ${signer.address}`);

  const oracleContract = await ethers.getContractAt("SimpleOracle", simpleOracleAddress);

  // Получаем bytes32 ID актива (убедись, что метод совпадает с бэкендом!)
  const assetIdBytes32_keccak = ethers.keccak256(ethers.toUtf8Bytes(assetPair));

  // Вычисляем старый timestamp
  const currentTimestamp = Math.floor(Date.now() / 1000);
  const oldTimestamp = currentTimestamp - (minutesAgo * 60); // Сдвигаем на N минут назад

  console.log(`Requesting price validation for asset: ${assetPair} (ID: ${assetIdBytes32_keccak})`);
  console.log(`Using OLD timestamp: ${oldTimestamp} (${minutesAgo} minutes ago)`);
  console.log(`(Current timestamp is: ${currentTimestamp})`);


  // Проверяем KYC перед отправкой (хорошая практика)
  const kycAddress = await oracleContract.getKYCContractAddress();
  const kycContract = await ethers.getContractAt("KYCWhitelist", kycAddress);
  const isWhitelisted = await kycContract.isWhitelisted(signer.address);
  if (!isWhitelisted) {
       console.error(`Error: Address ${signer.address} is NOT in the KYC whitelist at ${kycAddress}`);
       console.error(`Run 'npx hardhat run scripts/addToWhitelist.ts --network sepolia' first (adjust address if needed).`);
       return; // Прерываем выполнение
  }
  console.log(`Address ${signer.address} is whitelisted.`);

  // Вызываем функцию контракта со старым timestamp'ом
  // Убедись, что имя функции и тип assetId совпадают с контрактом!
  // Если контракт ожидает string pair, а не bytes32 assetId:
  // const tx = await oracleContract.requestPriceValidation(assetPair, oldTimestamp);
  // Если контракт ожидает bytes32 assetId:
  const tx = await oracleContract.requestPriceValidation( // Или requestPrice, если имя другое
      assetIdBytes32_keccak,
      oldTimestamp
  );

  console.log(`Transaction sent: ${tx.hash}`);
  await tx.wait();
  console.log(`Price validation requested successfully with OLD timestamp! Check oracle backend logs.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});