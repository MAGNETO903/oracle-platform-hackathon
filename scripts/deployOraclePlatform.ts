import { ethers } from "hardhat";
import "dotenv/config"; // Убедись, что dotenv настроен для доступа к .env

async function main() {
  console.log("Starting deployment...");

  // Получаем адрес подписанта оракула из .env
  const oracleSignerAddress = process.env.ORACLE_SIGNER_ADDRESS;
  if (!oracleSignerAddress) {
    throw new Error("Missing ORACLE_SIGNER_ADDRESS in .env file");
  }
  console.log(`Using Oracle Signer Address: ${oracleSignerAddress}`);

  // Получаем кошелек деплоера из hardhat config (на основе TESTNET_PRIVATE_KEY)
  const [deployer] = await ethers.getSigners();
  console.log(`Deploying contracts with the account: ${deployer.address}`);
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`Account balance: ${ethers.formatEther(balance)} ETH`);


  // --- 1. Деплой KYCWhitelist ---
  console.log("\nDeploying KYCWhitelist...");
  const KYCWhitelistFactory = await ethers.getContractFactory("KYCWhitelist");
  // Передаем адрес деплоера как initialOwner
  const kycWhitelist = await KYCWhitelistFactory.deploy(deployer.address);
  // Ожидаем подтверждения деплоя
  await kycWhitelist.waitForDeployment();
  const kycWhitelistAddress = await kycWhitelist.getAddress();
  console.log(`KYCWhitelist deployed to: ${kycWhitelistAddress}`);


  // --- 2. Деплой SimpleOracle ---
  console.log("\nDeploying SimpleOracle...");
  const SimpleOracleFactory = await ethers.getContractFactory("SimpleOracle");
  // Передаем initialOwner, initialOracleSigner, initialKycContract
  const simpleOracle = await SimpleOracleFactory.deploy(
    deployer.address,      // initialOwner
    oracleSignerAddress,   // initialOracleSigner
    kycWhitelistAddress    // initialKycContract
  );
  await simpleOracle.waitForDeployment();
  const simpleOracleAddress = await simpleOracle.getAddress();
  console.log(`SimpleOracle deployed to: ${simpleOracleAddress}`);


  // --- 3. Деплой PriceConsumerExample ---
  console.log("\nDeploying PriceConsumerExample...");
  const PriceConsumerExampleFactory = await ethers.getContractFactory("PriceConsumerExample");
  // Передаем адрес развернутого SimpleOracle
  const priceConsumerExample = await PriceConsumerExampleFactory.deploy(
    simpleOracleAddress
  );
  await priceConsumerExample.waitForDeployment();
  const priceConsumerExampleAddress = await priceConsumerExample.getAddress();
  console.log(`PriceConsumerExample deployed to: ${priceConsumerExampleAddress}`);

  console.log("\nDeployment finished successfully!");
  console.log("----------------------------------------------------");
  console.log("Deployed Contract Addresses:");
  console.log(`  KYCWhitelist: ${kycWhitelistAddress}`);
  console.log(`  SimpleOracle: ${simpleOracleAddress}`);
  console.log(`  PriceConsumerExample: ${priceConsumerExampleAddress}`);
  console.log("----------------------------------------------------");
}

// Стандартный паттерн для запуска main и обработки ошибок
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("Deployment failed:", error);
    process.exit(1);
  });