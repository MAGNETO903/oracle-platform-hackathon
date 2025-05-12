// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol"; // Для управления владельцем
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol"; // Для EIP-712 подписей (более безопасный способ)
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol"; // Для проверки подписи
import "./KYCWhitelist.sol"; // Импортируем интерфейс или контракт KYC

/**
 * @title SimpleOracle
 * @dev Oracle contract that allows requesting on-chain price validation
 * and fulfills requests using signatures from a trusted oracle signer.
 * Utilizes EIP-712 for safer signature handling.
 */
contract SimpleOracle is Ownable, EIP712 {

    // Адрес кошелька (бэкенда), чья подпись считается валидной
    address private _oracleSigner;
    // Адрес контракта KYC
    KYCWhitelist private _kycContract;

    // Хранение валидированных цен: id актива => таймстемп => цена
    mapping(bytes32 => mapping(uint256 => uint256)) private _validatedPrices;

    // --- EIP-712 ---
    // Типы данных, которые мы будем подписывать
    // bytes32 constant PRICE_VALIDATION_TYPEHASH = keccak256("PriceValidation(bytes32 assetId,uint256 timestamp,uint256 price)");

    // --- События ---
    event PriceValidationRequested(bytes32 indexed assetId, uint256 timestamp, address indexed requester);
    event PriceValidationFulfilled(bytes32 indexed assetId, uint256 timestamp, uint256 price, address indexed signer);
    event OracleSignerUpdated(address indexed oldSigner, address indexed newSigner);
    event KYCContractUpdated(address indexed oldContract, address indexed newContract);

    // --- Ошибки ---
    error InvalidSignature();
    error InvalidKYCContractAddress();
    error AddressNotWhitelisted(address account);
    error InvalidSignerAddress();
    error NoValidatedPriceFound(bytes32 assetId, uint256 timestamp);

    /**
     * @dev Конструктор
     * @param initialOwner Адрес владельца контракта
     * @param initialOracleSigner Адрес доверенного подписанта оракула
     * @param initialKycContract Адрес развернутого KYCWhitelist контракта
     */
    constructor(
        address initialOwner,
        address initialOracleSigner,
        address initialKycContract
    )
        Ownable(initialOwner)
        EIP712("SimpleOracle", "1") // EIP-712 домен
    {
        if (initialOracleSigner == address(0)) revert InvalidSignerAddress();
        if (initialKycContract == address(0)) revert InvalidKYCContractAddress();

        _oracleSigner = initialOracleSigner;
        _kycContract = KYCWhitelist(initialKycContract);

        emit OracleSignerUpdated(address(0), initialOracleSigner);
        emit KYCContractUpdated(address(0), initialKycContract);
    }

    // --- Функции Владельца ---

    /**
     * @dev Обновляет адрес доверенного подписанта оракула.
     * Только владелец.
     */
    function setOracleSigner(address newOracleSigner) public onlyOwner {
        if (newOracleSigner == address(0)) revert InvalidSignerAddress();
        address oldSigner = _oracleSigner;
        _oracleSigner = newOracleSigner;
        emit OracleSignerUpdated(oldSigner, newOracleSigner);
    }

    /**
     * @dev Обновляет адрес KYC контракта.
     * Только владелец.
     */
    function setKYCContract(address newKycContract) public onlyOwner {
         if (newKycContract == address(0)) revert InvalidKYCContractAddress();
        address oldContract = address(_kycContract);
        _kycContract = KYCWhitelist(newKycContract);
        emit KYCContractUpdated(oldContract, newKycContract);
    }

    // --- Публичные Функции ---

    /**
     * @dev Запрашивает ончейн-валидацию цены для актива на определенный таймстемп.
     * Требует, чтобы вызывающий был в KYC белом списке.
     * @param assetId Идентификатор актива (например, keccak256("BTC/USDT")).
     * @param timestamp Таймстемп, для которого нужна цена.
     */
    function requestPriceValidation(bytes32 assetId, uint256 timestamp) public {
        // Проверяем KYC вызывающего
        if (!_kycContract.isWhitelisted(msg.sender)) {
            revert AddressNotWhitelisted(msg.sender);
        }
        // Просто эмитим событие, на которое будет реагировать оффчейн сервис
        emit PriceValidationRequested(assetId, timestamp, msg.sender);
    }

    /**
     * @dev Предоставляет валидированную цену от оракула.
     * Проверяет подпись доверенного подписанта (_oracleSigner).
     * Можно вызвать кем угодно, но подпись должна быть валидной.
     * @param assetId Идентификатор актива.
     * @param timestamp Таймстемп цены.
     * @param price Цена.
     * @param signature Подпись EIP-712 от _oracleSigner.
     */
    function fulfillPriceValidation(
        bytes32 assetId,
        uint256 timestamp,
        uint256 price,
        bytes calldata signature
    ) public {
        // 1. Построить хэш сообщения EIP-712
        bytes32 structHash = keccak256(abi.encode(
            keccak256("PriceValidation(bytes32 assetId,uint256 timestamp,uint256 price)"), // TYPEHASH
            assetId,
            timestamp,
            price
        ));
        bytes32 digest = _hashTypedDataV4(structHash);

        // 2. Восстановить адрес подписанта из подписи и хэша
        address signer = ECDSA.recover(digest, signature);

        // 3. Проверить, совпадает ли подписант с доверенным _oracleSigner
        if (signer != _oracleSigner) {
            revert InvalidSignature();
        }

        // 4. Сохранить валидированную цену
        _validatedPrices[assetId][timestamp] = price;
        emit PriceValidationFulfilled(assetId, timestamp, price, signer);
    }

    // --- View Функции ---

    /**
     * @dev Возвращает адрес текущего доверенного подписанта оракула.
     */
    function getOracleSigner() public view returns (address) {
        return _oracleSigner;
    }

     /**
     * @dev Возвращает адрес текущего KYC контракта.
     */
    function getKYCContractAddress() public view returns (address) {
        return address(_kycContract);
    }

    /**
     * @dev Возвращает валидированную цену для актива и таймстемпа.
     * Возвращает 0, если цена для данной пары (assetId, timestamp) не была валидирована.
     */
    function getValidatedPrice(bytes32 assetId, uint256 timestamp) public view returns (uint256) {
        return _validatedPrices[assetId][timestamp];
    }

     /**
     * @dev Проверяет, была ли цена валидирована для актива и таймстемпа.
     */
    function hasValidatedPrice(bytes32 assetId, uint256 timestamp) public view returns (bool) {
        return _validatedPrices[assetId][timestamp] > 0; // Считаем, что цена не может быть 0
    }

    /**
     * @dev Возвращает EIP-712 доменный сепаратор для этого контракта.
     * Может быть полезно для оффчейн-сервиса при формировании подписи.
     */
    function DOMAIN_SEPARATOR() external view returns (bytes32) {
        return _domainSeparatorV4();
    }
}