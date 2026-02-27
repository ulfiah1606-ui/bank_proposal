-- =====================================================
-- MIGRASI: Gabungkan semua login ke tabel `users`
-- Jalankan di phpMyAdmin atau MySQL CLI
-- =====================================================

-- 1. Tambah kolom baru ke tabel users
ALTER TABLE `users`
  MODIFY `role` enum('admin','penyuluh','kelompok_tani') NOT NULL,
  ADD COLUMN `nip` varchar(50) DEFAULT NULL AFTER `role`,
  ADD COLUMN `id_penyuluh` int DEFAULT NULL AFTER `nip`,
  ADD COLUMN `id_kelompok` int DEFAULT NULL AFTER `id_penyuluh`;

-- 2. Migrasikan data penyuluh ke tabel users
INSERT INTO `users` (`nama`, `username`, `password`, `role`, `nip`, `id_penyuluh`, `wilayah_binaan`)
SELECT
  `nama_lengkap`,
  `username`,
  `password`,
  'penyuluh',
  `nip_penyuluh`,
  `id_penyuluh`,
  `kecamatan`
FROM `penyuluh`;

-- 3. Migrasikan data kelompok_tani ke tabel users
-- Username = id_kelompok (dikonversi ke string)
INSERT INTO `users` (`nama`, `username`, `password`, `role`, `id_kelompok`, `wilayah_binaan`)
SELECT
  `nama_kelompok`,
  CAST(`id_kelompok` AS CHAR),
  `password`,
  'kelompok_tani',
  `id_kelompok`,
  `kecamatan`
FROM `kelompok_tani`;

-- =====================================================
-- SELESAI! Sekarang semua login baca dari tabel users
-- =====================================================
