// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20; // Используем актуальную версию Solidity

import "@openzeppelin/contracts/access/Ownable.sol"; // Импортируем Ownable

/**
 * @title KYCWhitelist
 * @dev Manages a whitelist of addresses that have passed KYC.
 * Only the owner can add or remove addresses from the whitelist.
 */
contract KYCWhitelist is Ownable {
    // Mapping для хранения адресов в белом списке
    // address => bool (true если в списке, false если нет)
    mapping(address => bool) private _whitelist;

    // Событие: Адрес добавлен в белый список
    event WhitelistedAddressAdded(address indexed account);
    // Событие: Адрес удален из белого списка
    event WhitelistedAddressRemoved(address indexed account);

    /**
     * @dev Конструктор, передает адрес деплоера контракту Ownable
     * @param initialOwner Адрес, который станет владельцем контракта
     */
    constructor(address initialOwner) Ownable(initialOwner) {}

    /**
     * @dev Проверяет, находится ли адрес в белом списке.
     * @param account Адрес для проверки.
     * @return bool True если адрес в списке, иначе false.
     */
    function isWhitelisted(address account) public view returns (bool) {
        return _whitelist[account];
    }

    /**
     * @dev Добавляет адрес в белый список.
     * Только владелец может вызвать эту функцию.
     * @param account Адрес для добавления.
     */
    function addAddress(address account) public onlyOwner {
        require(!_whitelist[account], "KYCWhitelist: Address already whitelisted");
        _whitelist[account] = true;
        emit WhitelistedAddressAdded(account);
    }

    /**
     * @dev Добавляет несколько адресов в белый список.
     * Только владелец может вызвать эту функцию.
     * @param accounts Массив адресов для добавления.
     */
    function addAddresses(address[] calldata accounts) public onlyOwner {
        for (uint256 i = 0; i < accounts.length; i++) {
            address account = accounts[i];
            if (!_whitelist[account]) {
                _whitelist[account] = true;
                emit WhitelistedAddressAdded(account);
            }
            // Если адрес уже был, просто игнорируем его добавление
        }
    }

    /**
     * @dev Удаляет адрес из белого списка.
     * Только владелец может вызвать эту функцию.
     * @param account Адрес для удаления.
     */
    function removeAddress(address account) public onlyOwner {
        require(_whitelist[account], "KYCWhitelist: Address not whitelisted");
        _whitelist[account] = false;
        emit WhitelistedAddressRemoved(account);
    }
}