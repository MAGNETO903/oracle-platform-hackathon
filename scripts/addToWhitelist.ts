// scripts/addToWhitelist.ts
import { ethers } from "hardhat";
import { config as dotenvConfig } from "dotenv";
import { resolve } from "path";

// Загружаем .env из корня проекта
dotenvConfig({ path: resolve(__dirname, "../.env") });

const kycWhitelistAddress = process.env.KYC_WHITELIST_ADDRESS; // Берем из .env
const addressToAdd = "0x88F9Dc94C74C71e81695f8B7A8159ae32Fc93fb1"; // <<<=== ВСТАВЬ СЮДА АДРЕС (0x...)

async function main() {
  if (!kycWhitelistAddress) {
    throw new Error("Missing KYC_WHITELIST_ADDRESS in root .env file");
  }
  if (!addressToAdd || !ethers.isAddress(addressToAdd)) {
      throw new Error("Invalid addressToAdd specified in script")
  }

  console.log(`Adding address ${addressToAdd} to KYC Whitelist at ${kycWhitelistAddress}...`);

  const kycContract = await ethers.getContractAt("KYCWhitelist", kycWhitelistAddress);

  // Проверяем, не добавлен ли уже
  const isAlreadyAdded = await kycContract.isWhitelisted(addressToAdd);
  if (isAlreadyAdded) {
      console.log(`Address ${addressToAdd} is already whitelisted.`);
      return;
  }

  // Вызываем функцию addAddress
  const tx = await kycContract.addAddress(addressToAdd);
  console.log(`Transaction sent: ${tx.hash}`);

  // Ждем подтверждения
  await tx.wait();
  console.log(`Address ${addressToAdd} added successfully!`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});