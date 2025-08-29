-- Создание таблицы users
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Создание таблицы containers
CREATE TABLE containers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    container_number CHAR(11) NOT NULL UNIQUE,
    cost DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_container_number (container_number),
    INDEX idx_cost (cost)
);
DELIMITER $$
-- Тригера на валидацию данных
CREATE TRIGGER before_container_insert
    BEFORE INSERT ON containers
    FOR EACH ROW
BEGIN
    -- Проверяем формат: 3 буквы + 'U' + 7 цифр (всего 11 символов)
    IF NOT (NEW.container_number REGEXP '^[A-Z]{3}U[0-9]{7}$') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid container number format. Expected: AAAU1234567 (3 uppercase letters + U + 7 digits)';
    END IF;
END$$

DELIMITER ;
DELIMITER $$
CREATE TRIGGER before_container_update
    BEFORE UPDATE ON containers
    FOR EACH ROW
BEGIN
    IF NOT (NEW.container_number REGEXP '^[A-Z]{3}U[0-9]{7}$') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid container number format. Expected: AAAU1234567 (3 uppercase letters + U + 7 digits)';
    END IF;
END$$
DELIMITER ;

-- Хэши паролей для user1, user2, user3 (пароль: password)
INSERT INTO users (username, password_hash) VALUES
('user1', '$2y$10$ACNCN1YDl2umGEd.gnpEFOKSYT1/bY687oIlZrga4MAyqq4qsFnca'),
('user2', '$2y$10$ACNCN1YDl2umGEd.gnpEFOKSYT1/bY687oIlZrga4MAyqq4qsFnca'),
('user3', '$2y$10$ACNCN1YDl2umGEd.gnpEFOKSYT1/bY687oIlZrga4MAyqq4qsFnca');

-- Вставка 10 валидных контейнеров
INSERT INTO containers (container_number, cost) VALUES
('CXXU7788345', 15000.00),
('VTYU8765678', 18500.50),
('ABCU1234567', 20000.75),
('DEEU9876543', 17300.25),
('FGHU5556667', 19200.00),
('JKLU4443332', 21000.99),
('NOPU1234567', 16700.40),
('RSTU7778889', 18000.33),
('UVWU1112223', 22000.00),
('YZBU4445556', 19999.99),
('MNOU3334445', 17500.80);