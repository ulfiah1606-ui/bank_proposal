-- Jalankan di database aktif db_bank_proposal_pertanian.
-- Kompatibel untuk MySQL lama yang belum mendukung "ADD COLUMN IF NOT EXISTS".

SET @col_is_archived_exists := (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'proposal'
      AND column_name = 'is_archived'
);

SET @ddl_is_archived := IF(
    @col_is_archived_exists = 0,
    'ALTER TABLE proposal ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0 AFTER status',
    'SELECT "Kolom is_archived sudah ada" AS info'
);

PREPARE stmt_is_archived FROM @ddl_is_archived;
EXECUTE stmt_is_archived;
DEALLOCATE PREPARE stmt_is_archived;

SET @col_archived_at_exists := (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'proposal'
      AND column_name = 'archived_at'
);

SET @ddl_archived_at := IF(
    @col_archived_at_exists = 0,
    'ALTER TABLE proposal ADD COLUMN archived_at DATETIME NULL AFTER is_archived',
    'SELECT "Kolom archived_at sudah ada" AS info'
);

PREPARE stmt_archived_at FROM @ddl_archived_at;
EXECUTE stmt_archived_at;
DEALLOCATE PREPARE stmt_archived_at;
