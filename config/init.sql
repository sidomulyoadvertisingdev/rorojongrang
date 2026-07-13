CREATE DATABASE IF NOT EXISTS gmaps_scraper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE gmaps_scraper;

CREATE TABLE IF NOT EXISTS businesses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    address TEXT,
    city VARCHAR(100),
    district VARCHAR(100),
    regency VARCHAR(100),
    province VARCHAR(100),
    postal_code VARCHAR(10),
    phone VARCHAR(50),
    website VARCHAR(255),
    email VARCHAR(255),
    rating DECIMAL(2,1),
    review_count INT DEFAULT 0,
    google_maps_url TEXT,
    place_id VARCHAR(255),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    operating_hours TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    source_keyword VARCHAR(255),
    source_location VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    UNIQUE KEY unique_place (place_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS search_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending',
    total_results INT DEFAULT 0,
    scraped_results INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS scraping_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT,
    action VARCHAR(100),
    message TEXT,
    level ENUM('INFO', 'WARNING', 'ERROR') DEFAULT 'INFO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES search_tasks(id)
) ENGINE=InnoDB;
