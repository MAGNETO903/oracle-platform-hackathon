// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Определяем интерфейс для SimpleOracle, чтобы не импортировать весь контракт
interface ISimpleOracle {
    function getValidatedPrice(bytes32 assetId, uint256 timestamp) external view returns (uint256);
    function hasValidatedPrice(bytes32 assetId, uint256 timestamp) external view returns (bool);
    // Нам может понадобиться и адрес KYC контракта из оракула
    function getKYCContractAddress() external view returns (address);
}

// Также импортируем интерфейс KYC контракта
interface IKYCWhitelist {
     function isWhitelisted(address account) external view returns (bool);
}

/**
 * @title PriceConsumerExample
 * @dev Example contract demonstrating how to consume validated prices
 * from the SimpleOracle contract.
 */
contract PriceConsumerExample {

    ISimpleOracle private _oracle; // Адрес контракта SimpleOracle
    IKYCWhitelist private _kycContract; // Адрес контракта KYC (получим из оракула)

    // Событие: Действие выполнено на основе полученной цены
    event ActionExecutedBasedOnPrice(
        bytes32 indexed assetId,
        uint256 timestamp,
        uint256 price,
        address indexed performer
    );

    // --- Ошибки ---
    error InvalidOracleAddress();
    error PriceNotValidatedYet(bytes32 assetId, uint256 timestamp);
    error AddressNotWhitelisted(address account);

    /**
     * @dev Конструктор
     * @param oracleAddress Адрес развернутого контракта SimpleOracle.
     */
    constructor(address oracleAddress) {
        if (oracleAddress == address(0)) revert InvalidOracleAddress();
        _oracle = ISimpleOracle(oracleAddress);

        // Получаем и сохраняем адрес KYC контракта из оракула
        address kycAddress = _oracle.getKYCContractAddress();
         if (kycAddress == address(0)) {
             // В реальном сценарии здесь может быть более сложная логика
             // Но для примера пока допустим, что оракул всегда имеет валидный KYC адрес
         }
        _kycContract = IKYCWhitelist(kycAddress);
    }

    /**
     * @dev Пример функции, которая использует цену от оракула.
     * Требует, чтобы цена была предварительно валидирована ончейн.
     * Требует, чтобы вызывающий был в KYC белом списке.
     * @param assetId Идентификатор актива.
     * @param timestamp Таймстемп, для которого нужна цена.
     */
    function executeActionWithPrice(bytes32 assetId, uint256 timestamp) public {
        // 1. Проверяем KYC вызывающего через контракт, указанный в оракуле
        if (!_kycContract.isWhitelisted(msg.sender)) {
            revert AddressNotWhitelisted(msg.sender);
        }

        // 2. Проверяем, была ли цена валидирована в оракуле
        if (!_oracle.hasValidatedPrice(assetId, timestamp)) {
            revert PriceNotValidatedYet(assetId, timestamp);
        }

        // 3. Получаем валидированную цену
        uint256 price = _oracle.getValidatedPrice(assetId, timestamp);

        // 4. Выполняем какое-то действие на основе цены
        // (Здесь просто эмитим событие для примера)
        // В реальном контракте здесь может быть логика расчета, обмена, выпуска и т.д.
        require(price > 0, "Price cannot be zero"); // Доп. проверка

        emit ActionExecutedBasedOnPrice(assetId, timestamp, price, msg.sender);

        // Пример условной логики:
        // if (price > 1000) {
        //     // do something
        // } else {
        //     // do something else
        // }
    }

    /**
    * @dev Возвращает адрес используемого контракта оракула.
    */
    function getOracleAddress() public view returns (address) {
        return address(_oracle);
    }

    /**
    * @dev Возвращает адрес используемого KYC контракта.
    */
    function getKYCWhitelistAddress() public view returns (address) {
         return address(_kycContract);
    }
}