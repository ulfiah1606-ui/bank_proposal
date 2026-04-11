-- Jalankan di database aktif db_bank_proposal_pertanian.
-- Kompatibel untuk MySQL lama yang belum mendukung "ADD COLUMN IF NOT EXISTS".

SET @col_exists := (
	SELECT COUNT(*)
	FROM information_schema.columns
	WHERE table_schema = DATABASE()
	  AND table_name = 'proposal'
	  AND column_name = 'catatan_ocr'
);

SET @ddl := IF(
	@col_exists = 0,
	'ALTER TABLE proposal ADD COLUMN catatan_ocr TEXT NULL AFTER status',
	'SELECT "Kolom catatan_ocr sudah ada" AS info'
);

PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
