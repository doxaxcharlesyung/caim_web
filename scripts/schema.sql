CREATE TABLE IF NOT EXISTS page_content (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    content_key VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    subtitle TEXT NOT NULL,
    sections JSON NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS content_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    collection_name VARCHAR(100) NOT NULL,
    item_key VARCHAR(191) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    item_data JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_content_item (collection_name, item_key),
    KEY ix_content_collection (collection_name, sort_order)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS courses (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    slug VARCHAR(191) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    image VARCHAR(500) NOT NULL,
    alt VARCHAR(500) NOT NULL,
    href VARCHAR(500) NOT NULL,
    cta_label VARCHAR(100) NOT NULL,
    detail JSON NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_published BOOLEAN NOT NULL DEFAULT TRUE,
    content_type VARCHAR(20) NOT NULL DEFAULT 'course',
    status VARCHAR(20) NOT NULL DEFAULT 'posted',
    scheduled_posting_at DATETIME NULL,
    posted_at DATETIME NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS news (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(191) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    event_date DATE NOT NULL,
    date_label VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(20) NOT NULL DEFAULT 'news',
    status VARCHAR(20) NOT NULL DEFAULT 'posted',
    scheduled_posting_at DATETIME NULL,
    posted_at DATETIME NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_news_status_date (status, event_date)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS articles (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(191) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    excerpt TEXT NOT NULL,
    category VARCHAR(191) NOT NULL,
    image VARCHAR(500) NOT NULL,
    alt VARCHAR(500) NOT NULL,
    published_date DATE NULL,
    href VARCHAR(500) NOT NULL,
    detail JSON NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'posted',
    scheduled_posting_at DATETIME NULL,
    posted_at DATETIME NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_article_status_date (status, published_date)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS admin_users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
